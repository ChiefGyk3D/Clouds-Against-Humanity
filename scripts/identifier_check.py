#!/usr/bin/env python3
"""Identifier check for Clouds Against Humanity.

This repository is public. The check scans every tracked text file for cloud
account identifiers written in a structural form (an AWS ARN with an account
id, an account id next to the word "account", an AWS key id, an Azure
subscription or tenant id next to its key, a GCP project id next to its key)
and fails when it finds one.

It never prints the matched value, nor any part of it. A finding is reported
as file:line and the kind, so the CI log does not become a second copy of the
leak.

It does not look for secrets. Secret scanning is Gitleaks' job; this catches
identifiers that are not secrets but that a public repository should still
not publish.

Rules worth knowing:
- Synthetic placeholders are allowed by name (ALLOWED_VALUES), and a value
  containing "example" is allowed. A placeholder like <account-id> is not an
  id-shaped value, so it never matches in the first place. A real id wrapped
  in angle brackets is still a finding.
- A line may end with a comment carrying the ignore marker (see IGNORE_RE);
  the run prints how many were used.
- A file that is not valid UTF-8 is decoded with replacement characters and
  scanned anyway. UTF-16 is decoded when it has a byte order mark. A file with
  NUL bytes and no byte order mark is binary and is counted, not scanned.
- A bad root, or a run that scanned no file, fails.
- docs/superpowers/plans is skipped.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = frozenset({".git", ".terraform", ".venv"})
SKIP_PREFIXES = ("docs/superpowers/plans/",)
# The marker counts only inside a comment at the end of the line.
IGNORE_RE = re.compile(r"(?:#|//|<!--)[ \t]*identifier-check:[ \t]*ignore\b[^\n]*$")
MAX_BYTES = 64_000_000
BOMS = (b"\xff\xfe", b"\xfe\xff")

# Synthetic values that lessons may show. Explicit on purpose: a realistic
# looking 12-digit number is exactly what this check exists to refuse.
ALLOWED_VALUES = frozenset(
    {
        "123456789012",
        "000000000000",
        "111122223333",
        "00000000-0000-0000-0000-000000000000",
        "11111111-1111-1111-1111-111111111111",
        "my-project-id",
        "your-project-id",
        "project-id",
    }
)

UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
GCP_ID = r"[a-z][a-z0-9-]{4,28}[a-z0-9]"
KEYB = r"(?<![A-Za-z0-9])"  # a key may follow "_" (TF_VAR_, ARM_), never a letter
TAIL = r"(?![\w.\[(/$-])"
TAIL_PATH = r"(?![\w.\[($-])"
# Between a key and its value: optional quotes, ONE run of blanks, then an
# optional ":" or "=". Only one blank-run quantifier is adjacent to another
# optional piece, so a long run of spaces cannot cause backtracking blowup.
OPT_SEP = r"[\"']?[ \t]*(?:[:=][ \t]*)?[\"'<]*"
REQ_SEP = r"[\"']?[ \t]*[:=][ \t]*[\"'<]*"
NOT_DIGIT_BEFORE = r"(?<!\d)"
KEYS_PROJECT = r"(?i:" + KEYB + r"project(?:[_-]?id)?)"
PREFIXES = "AKIA|ASIA|AIDA|AGPA|ANPA|ABIA|AROA|AIPA|ANVA|ACCA|APKA|ASCA"

# (kind, compiled regex with the value in group "v")
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "AWS ARN account id",
        re.compile(r"(?i)arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:<?(?P<v>\d{12})(?!\d)"),
    ),
    (
        "AWS account id",
        re.compile(
            r"(?i)" + KEYB + r"(?:aws[_ -]?account(?:[_ -]?(?:id|number))?"
            r"|account[_ -]?(?:id|number)|account(?:[ \t]?#)?)"
            + OPT_SEP
            + NOT_DIGIT_BEFORE
            + r"(?P<v>\d{12})(?!\d)"
        ),
    ),
    (
        "AWS account id",
        re.compile(
            r"(?i)"
            + NOT_DIGIT_BEFORE
            + r"<?(?P<v>\d{12})>?\.(?:dkr\.ecr[a-z0-9.-]*\.amazonaws\.com"
            r"|signin\.aws\.amazon\.com)"
        ),
    ),
    (
        "AWS account id",
        re.compile(
            r"(?i)"
            + KEYB
            + r"[\"']?owner[_-]?id"
            + REQ_SEP
            + NOT_DIGIT_BEFORE
            + r"(?P<v>\d{12})(?!\d)"
        ),
    ),
    (
        "AWS access key id",
        re.compile(
            rf"(?<![A-Za-z0-9])(?P<v>(?:{PREFIXES})[A-Z0-9]{{16}})(?![A-Za-z0-9])"
        ),
    ),
    (
        "Azure subscription or tenant id",
        re.compile(
            r"(?i)"
            + KEYB
            + r"(?:subscription[_-]?id|(?:home[_-]?)?tenant[_-]?id|[\"']id[\"'])"
            + REQ_SEP
            + rf"(?P<v>{UUID})\b"
        ),
    ),
    (
        "Azure subscription id in a resource path",
        re.compile(rf"(?i)/subscriptions/(?P<v>{UUID})\b"),
    ),
    (
        "Azure tenant id in a sign-in URL",
        re.compile(
            r"(?i)(?:login\.microsoftonline\.com|sts\.windows\.net)/"
            + rf"(?P<v>{UUID})\b"
        ),
    ),
    (
        "GCP project id",
        re.compile(
            KEYS_PROJECT + r"[\"']?[ \t]*[:=][ \t]*[\"']?" + rf"(?P<v>{GCP_ID}){TAIL}"
        ),
    ),
    (
        "GCP project id",
        re.compile(
            r"(?:--project(?:=|[ \t]+)|(?<![A-Za-z0-9])set[ \t]+project[ \t]+)[\"']?"
            + rf"(?P<v>{GCP_ID}){TAIL}"
        ),
    ),
    (
        "GCP project id in a resource path",
        re.compile(rf"(?<![A-Za-z0-9])projects/(?P<v>{GCP_ID}){TAIL_PATH}"),
    ),
)


def is_allowed(value: str) -> bool:
    return value.lower() in ALLOWED_VALUES or "example" in value.lower()


def find_kinds(line: str) -> list[str]:
    """Kinds of every unallowed identifier on a line, ignoring any marker."""
    found: list[str] = []
    for kind, pattern in PATTERNS:
        for m in pattern.finditer(line):
            if not is_allowed(m.group("v")) and kind not in found:
                found.append(kind)
    return found


def has_marker(line: str) -> bool:
    return IGNORE_RE.search(line) is not None


def scan_line(line: str) -> list[str]:
    """Kinds found on a line; empty when the line carries a valid marker."""
    if has_marker(line):
        return []
    return find_kinds(line)


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout
        names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        found = [root / n for n in names if (root / n).is_file()]
        if found:
            return found
    except (OSError, subprocess.CalledProcessError):
        pass
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if SKIP_DIRS.intersection(rel.parts) or not path.is_file():
            continue
        files.append(path)
    return files


class Result:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.scanned = 0
        self.binary = 0
        self.ignored = 0


def decode(data: bytes) -> str | None:
    """Text of a file, or None when it is binary."""
    if data.startswith(BOMS):
        return data.decode("utf-16", errors="replace")
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def scan_file(path: Path, rel: str, result: Result) -> None:
    try:
        size = path.stat().st_size
        if size > MAX_BYTES:
            result.problems.append(
                f"{rel}: not scanned, file is larger than {MAX_BYTES} bytes"
            )
            return
        text = decode(path.read_bytes())
    except OSError:
        result.problems.append(f"{rel}: not scanned, could not be read")
        return
    if text is None:
        result.binary += 1
        return
    result.scanned += 1
    for number, line in enumerate(text.splitlines(), start=1):
        kinds = find_kinds(line)
        if not kinds:
            continue
        if has_marker(line):
            result.ignored += 1
            continue
        for kind in kinds:
            result.problems.append(f"{rel}:{number}: {kind}")


def run(root: Path) -> Result:
    result = Result()
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(SKIP_PREFIXES):
            continue
        scan_file(path, rel, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"identifier check FAILED: root is not a directory: {args.root}")
        return 2
    result = run(root)
    summary = (
        f"{result.scanned} files scanned, {result.binary} binary skipped, "
        f"{result.ignored} ignore markers used"
    )
    if result.scanned == 0:
        print(f"identifier check FAILED: no files were scanned ({summary})")
        return 1
    if result.problems:
        print("identifier check FAILED (values are never printed):")
        for p in result.problems:
            print(f"  {p}")
        print(summary)
        print(
            "Use a synthetic placeholder (see ALLOWED_VALUES in "
            "scripts/identifier_check.py) or end the line with a comment "
            "'identifier-check: ignore'."
        )
        return 1
    print(f"identifier check passed ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
