#!/usr/bin/env python3
"""Fail unless a saved OpenTofu plan is a no-op over every known resource.

The stage 2 settings work edits code that two live stacks already run. This
check is the acceptance test for such an edit: with the default values the plan
must change nothing. It reads the JSON of a saved plan (`tofu plan -out=plan`
then `tofu show -json plan`) and a golden file that lists every resource
address the stack has today, and fails when:

- any managed resource change is not exactly ["no-op"] ("update" counts as a
  failure; so do create, delete, replace and anything else), or a data source
  has an action other than "no-op" or "read";
- any output change is not ["no-op"] or has an unknown value;
- an address in the plan is missing from the golden list, or an address in
  the golden list is missing from the plan;
- a force-new attribute differs between before and after, is unknown after
  apply, is missing, or differs from the literal the golden file pins;
- a resource was moved (previous_address) and --allow-moves was not given, or
  was moved from or to an address the golden file does not list under "moves".

It reads files only and never prints an attribute value (user_data holds
connector tokens). A failure names the address and the attribute.

CI cannot run a real plan: that needs the live state and credentials. CI proves
this checker against mocked plan JSON (tests/test_plan_noop_check.py). The real
gate is the tracked-run plan the maintainer reads in Spacelift before
confirming; this script is for a plan JSON that exists (a local saved plan, or
one a run exposes).

Golden file format (docs/golden-addresses/<stack>.json):
  {
    "stack": "stacks/10-access",
    "addresses": {
      "<address>": {"type": "<resource type>", "force_new": {"<attr>": <expected>}}
    },
    "data": ["<data source address>"],
    "moves": {"<previous address>": "<current address>"}
  }
  <expected> is a literal that must equal the attribute, or "@unchanged", which
  only requires before and after to be equal (for ids and sensitive values).
  A list of strings is compared as a set.

Usage:
  python -I scripts/plan_noop_check.py --plan plan.json --golden docs/golden-addresses/10-access.json [--allow-moves]

Exit codes: 0 no-op, 1 the plan changes something or disagrees with the
golden file, 2 an input file is missing or has a shape this script refuses.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

UNCHANGED = "@unchanged"
MAX_BYTES = 256 * 1024 * 1024


class InputError(ValueError):
    """An input file is unreadable or has a shape this script refuses."""


def load_json(path: Path, what: str) -> dict:
    try:
        if path.stat().st_size > MAX_BYTES:
            raise InputError(f"{what}: file is larger than {MAX_BYTES} bytes")
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"{what}: cannot read {path} ({exc.strerror})") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"{what}: {path} is not JSON ({exc.msg})") from exc
    if not isinstance(data, dict):
        raise InputError(f"{what}: the top level must be an object")
    return data


def validate_golden(golden: dict) -> None:
    """Fail closed on a golden file with an unknown shape."""
    allowed = {"stack", "note", "addresses", "data", "moves"}
    extra = set(golden) - allowed
    if extra:
        raise InputError(f"golden: unknown keys {sorted(extra)}")
    if not isinstance(golden.get("stack"), str):
        raise InputError("golden: 'stack' must be a string")
    addresses = golden.get("addresses")
    if not isinstance(addresses, dict) or not addresses:
        raise InputError("golden: 'addresses' must be a non-empty object")
    for address, spec in addresses.items():
        if not isinstance(spec, dict) or set(spec) != {"type", "force_new"}:
            raise InputError(f"golden: {address}: needs exactly 'type' and 'force_new'")
        if not isinstance(spec["type"], str) or not isinstance(spec["force_new"], dict):
            raise InputError(f"golden: {address}: bad 'type' or 'force_new'")
        if not spec["force_new"]:
            raise InputError(f"golden: {address}: 'force_new' lists no attribute")
    data = golden.get("data", [])
    if not isinstance(data, list) or not all(isinstance(a, str) for a in data):
        raise InputError("golden: 'data' must be a list of addresses")
    moves = golden.get("moves", {})
    if not isinstance(moves, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in moves.items()
    ):
        raise InputError("golden: 'moves' must map addresses to addresses")
    for new in moves.values():
        if new not in addresses:
            raise InputError(f"golden: move target {new} is not a listed address")


def validate_plan(plan: dict) -> list[dict]:
    if plan.get("errored") is True:
        raise InputError("plan: the plan is marked errored")
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise InputError("plan: no 'resource_changes' list (not `tofu show -json` of a plan?)")
    for entry in changes:
        if not isinstance(entry, dict):
            raise InputError("plan: a resource change is not an object")
        change = entry.get("change")
        if (
            not isinstance(entry.get("address"), str)
            or not isinstance(change, dict)
            or not isinstance(change.get("actions"), list)
        ):
            raise InputError("plan: a resource change has no address or actions")
    return changes


def normalize(value):
    """Order-insensitive form for lists of strings (tags, sets)."""
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return sorted(value)
    return value


def attribute_problems(address: str, spec: dict, change: dict) -> list[str]:
    problems: list[str] = []
    before = change.get("before")
    after = change.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [f"{address}: the plan has no before and after values to compare"]
    unknown = change.get("after_unknown")
    unknown = unknown if isinstance(unknown, dict) else {}
    for attr, expected in spec["force_new"].items():
        if attr not in before or attr not in after:
            problems.append(f"{address}: force-new attribute {attr} is missing from the plan")
            continue
        if unknown.get(attr):
            problems.append(f"{address}: force-new attribute {attr} is unknown after apply")
            continue
        if normalize(before[attr]) != normalize(after[attr]):
            problems.append(f"{address}: force-new attribute {attr} differs between before and after")
            continue
        if expected != UNCHANGED and normalize(expected) != normalize(after[attr]):
            problems.append(f"{address}: force-new attribute {attr} is not the golden value")
    return problems


def output_problems(plan: dict) -> list[str]:
    """Any output that would change. Stack 10 reads the foundation outputs."""
    outputs = plan.get("output_changes", {})
    if not isinstance(outputs, dict):
        raise InputError("plan: 'output_changes' is not an object")
    problems: list[str] = []
    for name, change in sorted(outputs.items()):
        if not isinstance(change, dict) or not isinstance(change.get("actions"), list):
            raise InputError(f"plan: output {name} has no actions")
        if change["actions"] != ["no-op"]:
            problems.append(f"output {name}: action is {change['actions']}, expected [\"no-op\"]")
        if change.get("after_unknown"):
            problems.append(f"output {name}: value is unknown after apply")
    return problems


def check(plan: dict, golden: dict, allow_moves: bool = False) -> list[str]:
    """Every reason the plan is not a clean no-op over the golden addresses."""
    validate_golden(golden)
    changes = validate_plan(plan)
    addresses = golden["addresses"]
    data = set(golden.get("data", []))
    moves = golden.get("moves", {})
    problems: list[str] = []
    seen: set[str] = set()

    for entry in changes:
        address = entry["address"]
        change = entry["change"]
        actions = change["actions"]
        if address in seen:
            problems.append(f"{address}: appears twice in the plan")
            continue
        seen.add(address)

        previous = entry.get("previous_address")
        if previous and previous != address:
            if not allow_moves:
                problems.append(f"{address}: moved from another address (use --allow-moves for the bootstrap moves)")
            elif moves.get(previous) != address:
                problems.append(f"{address}: moved from an address the golden file does not allow")

        if entry.get("mode") == "data":
            if address not in data:
                problems.append(f"{address}: data source is not in the golden list")
            if actions not in (["no-op"], ["read"]):
                problems.append(f"{address}: data source action is {actions}, expected no-op or read")
            continue

        if address not in addresses:
            problems.append(f"{address}: in the plan but not in the golden list")
            continue
        if actions != ["no-op"]:
            problems.append(f"{address}: action is {actions}, expected [\"no-op\"]")
        spec = addresses[address]
        resource_type = entry.get("type")
        if resource_type is not None and resource_type != spec["type"]:
            problems.append(f"{address}: type is not the golden type")
        problems.extend(attribute_problems(address, spec, change))

    for address in sorted(set(addresses) - seen):
        problems.append(f"{address}: in the golden list but missing from the plan")
    problems.extend(output_problems(plan))
    # A data source read at plan time may be absent from resource_changes. It is
    # not a managed resource, so the golden "data" list is not required to appear.
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True, help="JSON from `tofu show -json <planfile>`")
    parser.add_argument("--golden", required=True, help="docs/golden-addresses/<stack>.json")
    parser.add_argument(
        "--allow-moves",
        action="store_true",
        help="accept the moves listed in the golden file (the bootstrap `moved` blocks)",
    )
    args = parser.parse_args(argv)
    try:
        golden = load_json(Path(args.golden), "golden")
        plan = load_json(Path(args.plan), "plan")
        problems = check(plan, golden, args.allow_moves)
    except InputError as exc:
        print(f"plan no-op check ERROR: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("plan no-op check FAILED (attribute values are never printed):")
        for problem in problems:
            print(f"  {problem}")
        return 1
    count = len(golden["addresses"])
    print(f"plan no-op check passed: {count} addresses, all no-op, force-new attributes unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
