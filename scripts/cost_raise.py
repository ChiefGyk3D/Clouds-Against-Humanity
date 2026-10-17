#!/usr/bin/env python3
"""Propose (or make) a change to one phase's cost ceiling in approved.json.

    python3 -I scripts/cost_raise.py --phase stage-3 --ceiling 36 --reason 'why'

By default this is a dry run: it prints the diff of docs/stages/approved.json
that the change would make and the problems the cost gate finds in the result.
With --write it edits the file, but only when the gate's checks pass.

It changes the phase entry (ceiling, reason, decided) and, with --make-current,
which phase is current. It never touches a provider's approved_monthly_total:
raise that separately, in the same pull request, so a reviewer sees both
numbers. A new phase id is appended (or placed with --after). A ceiling lower
than the phase before it needs --lowers. See docs/cost.md, "To raise the
ceiling".
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime
import difflib
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import sys
import tempfile
from pathlib import Path

APPROVED = "docs/stages/approved.json"


def load_gate():
    """The cost gate module, imported by path (the script runs under python -I)."""
    path = Path(__file__).resolve().parent / "cost_check.py"
    spec = importlib.util.spec_from_file_location("cost_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def propose(approved, phase, ceiling, reason, decided, *, make_current=False,
            lowers=False, after=None, cascade=False):  # fmt: skip
    """A new approved.json document with the phase set; the input is untouched."""
    doc = copy.deepcopy(approved)
    if "phases" not in doc:
        raise ValueError(
            "approved.json has no phases map (legacy top-level ceiling); migrate it first"
        )
    phases = doc["phases"]
    entry = {"ceiling": ceiling, "reason": reason, "decided": decided}
    if phase in phases:
        old = phases[phase]
        entry["status"] = old.get("status", "planned")
    else:
        entry["status"] = "planned"
    if lowers:
        entry["lowers"] = True
    if phase in phases:
        phases[phase] = entry
    elif after is not None:
        if after not in phases:
            raise ValueError(f"--after {after}: no such phase")
        rebuilt = {}
        for key, value in phases.items():
            rebuilt[key] = value
            if key == after:
                rebuilt[phase] = entry
        doc["phases"] = rebuilt
    else:
        phases[phase] = entry
    if cascade:
        # Walk the phases after the edited one in order. A phase that would now
        # be a quiet decrease is raised to its predecessor; a deliberate
        # decrease ("lowers") is kept while it still is one, and its flag is
        # dropped only when it no longer goes below its predecessor.
        seen, prev = False, None
        for key, value in doc["phases"].items():
            if key == phase:
                seen, prev = True, ceiling
                continue
            if not seen:
                continue
            own = value.get("ceiling")
            if isinstance(own, bool) or not isinstance(own, (int, float)):
                prev = None
                continue
            if prev is not None:
                if value.get("lowers"):
                    if own >= prev:
                        value.pop("lowers")
                elif own < prev:
                    value["ceiling"] = prev
                    value["reason"] = (
                        f"{str(value.get('reason', '')).rstrip()} "
                        f"Raised to ${prev:.2f} together with {phase}."
                    ).strip()
                    value["decided"] = decided
            prev = value["ceiling"]
    if make_current:
        for key, value in doc["phases"].items():
            if value.get("status") == "current":
                value["status"] = "done"
        doc["phases"][phase]["status"] = "current"
        doc["current_phase"] = phase
    return doc


class Conflict(Exception):
    """approved.json changed between reading it and writing it."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inputs_digest(root):
    """One hash over everything the gate reads besides approved.json: the stacks
    and modules trees (manifests and OpenTofu files), the price tables and the
    Spacelift config. Used to notice that an input changed while a change was
    being validated."""
    root = Path(root)
    h = hashlib.sha256()
    files = []
    for top in ("stacks", "modules", "docs/cost-prices"):
        base = root / top
        if base.is_dir():
            files += [
                f
                for f in base.rglob("*")
                if f.is_file() and ".terraform" not in f.relative_to(root).parts
            ]
    for single in ("docs/cost-prices.json", ".spacelift/config.yml", APPROVED):
        if (root / single).is_file():
            files.append(root / single)
    for f in sorted(set(files)):
        h.update(f.relative_to(root).as_posix().encode() + b"\0")
        h.update(f.read_bytes() + b"\0")
    return h.hexdigest()


@contextlib.contextmanager
def locked(directory):
    """An exclusive advisory lock on a directory, so two cost_raise runs queue."""
    fd = os.open(directory, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def replace_file(path, text, expected_digest, recheck=None):
    """Replace `path` with `text`. The caller holds the directory lock.

    Refuses if the file no longer has the content that was read, or if
    `recheck()` returns a message (a gate input changed). Writes a temporary
    file in the same directory, fsyncs it and renames it over the target."""
    if digest(path.read_bytes()) != expected_digest:
        raise Conflict(
            f"{path.name} changed since it was read; nothing written, run again"
        )
    if recheck is not None:
        message = recheck()
        if message:
            raise Conflict(message)
    mode = path.stat().st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def write_checked(path, text, expected_digest, recheck=None):
    """replace_file() under the directory lock."""
    with locked(path.parent):
        replace_file(path, text, expected_digest, recheck)


def gate_problems(gate, root, doc):
    return gate.gate_problems(root, doc)[0]


def effective(gate, doc):
    try:
        pid, ceiling, _ = gate.current_ceiling(doc)
        return f"phase {pid} ${ceiling:.2f}"
    except (ValueError, KeyError, TypeError):
        return "unreadable"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--phase", required=True, help="phase id, for example stage-3")
    parser.add_argument("--ceiling", required=True, type=float, help="dollars per month")
    parser.add_argument("--reason", required=True, help="why this ceiling")
    parser.add_argument("--decided", help="ISO date of the decision (default: today)")
    parser.add_argument(
        "--make-current",
        action="store_true",
        help="also make this phase the current one (the old current phase becomes done)",
    )
    parser.add_argument(
        "--lowers",
        action="store_true",
        help="this ceiling is deliberately lower than the phase before it",
    )
    parser.add_argument("--after", help="place a new phase after this phase id")
    parser.add_argument(
        "--cascade",
        action="store_true",
        help="also raise every later phase whose ceiling is now lower (each keeps its reason, with a note, and gets the new date); "
        "without it a raise that leaves a later phase lower fails the gate's no-quiet-decrease rule",
    )
    parser.add_argument("--write", action="store_true", help="edit the file (default: dry run)")
    args = parser.parse_args(argv)

    if not math.isfinite(args.ceiling) or args.ceiling < 0:
        print("cost-raise: --ceiling must be a finite number, zero or more", file=sys.stderr)
        return 2
    decided = args.decided or datetime.date.today().isoformat()
    root = Path(args.root)
    path = root / APPROVED
    lock = locked(path.parent) if args.write else contextlib.nullcontext()
    try:
        with lock:
            return run(args, gate_loader=load_gate, root=root, path=path, decided=decided)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as err:
        print(f"cost-raise: cannot propose the change: {err}", file=sys.stderr)
        return 1


def run(args, *, gate_loader, root, path, decided):
    gate = gate_loader()
    raw = path.read_bytes()
    seen_inputs = inputs_digest(root)
    before = gate.parse_json(raw.decode("utf-8"))
    after = propose(
        before,
        args.phase,
        args.ceiling,
        args.reason,
        decided,
        make_current=args.make_current,
        lowers=args.lowers,
        after=args.after,
        cascade=args.cascade,
    )
    # Everything the gate itself checks, not just totals and approvals:
    # allowlist, structure, the config invariant, phases, then lifecycle.
    problems = gate_problems(gate, root, after)
    problems += gate.transition_problems(before, after)

    was, now = effective(gate, before), effective(gate, after)
    print(
        f"EFFECTIVE CEILING: {was} -> {now}"
        if was != now
        else f"EFFECTIVE CEILING: unchanged, {now}"
    )
    diff = "".join(
        difflib.unified_diff(
            render(before).splitlines(keepends=True),
            render(after).splitlines(keepends=True),
            fromfile=f"a/{APPROVED}",
            tofile=f"b/{APPROVED}",
        )
    )
    print(diff or "cost-raise: no change")
    for problem in problems:
        print(f"cost-raise: the gate would fail: {problem}", file=sys.stderr)
    if problems:
        return 1
    if args.write:
        def inputs_unchanged():
            if inputs_digest(root) != seen_inputs:
                return (
                    "a file the cost gate reads changed while the change was being "
                    "checked; nothing written, run again"
                )
            return None

        try:
            replace_file(path, render(after), digest(raw), inputs_unchanged)
        except (Conflict, OSError) as err:
            print(f"cost-raise: {err}", file=sys.stderr)
            return 1
        print(f"cost-raise: wrote {APPROVED}")
    else:
        print("cost-raise: dry run, nothing written (add --write)")
    print(
        "cost-raise: a provider's approved_monthly_total is not changed by this; "
        "raise it separately in the same pull request"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
