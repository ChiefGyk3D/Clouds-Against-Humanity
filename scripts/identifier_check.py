#!/usr/bin/env python3
"""Identifier check for Clouds Against Humanity.

This repository is public. The check scans every tracked text file for cloud
account identifiers written in a structural form (an AWS ARN with an account
id, an account id next to the word "account", an AWS access key id, an Azure
subscription or tenant id next to its key, a GCP project id next to its key)
and fails when it finds one.

It never prints the matched value. A finding is reported as file:line, the
kind, and a masked form (the first two characters and an ellipsis), so the
CI log does not become a second copy of the leak.

It does not look for secrets. Secret scanning is Gitleaks' job; this catches
identifiers that are not secrets but that a public repository should still
not publish. Synthetic placeholders are allowed by name (see ALLOWED_VALUES),
a line may carry the marker below to opt out, and docs/superpowers/plans is
skipped.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = frozenset({".git", ".terraform", ".venv"})
SKIP_PREFIXES = ("docs/superpowers/plans/",)
IGNORE_MARKER = "identifier-check: ignore"
MAX_BYTES = 1_000_000

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
TAIL = r"(?![\w.\[(/$-])"
TAIL_PATH = r"(?![\w.\[($-])"

# (kind, compiled regex with the value in group "v")
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "AWS ARN account id",
        re.compile(r"arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:(?P<v>\d{12}):"),
    ),
    (
        "AWS account id",
        re.compile(
            r"(?i)\b(?:aws[_ -]?account(?:[_ -]?id)?|account[_ -]?id|account)"
            r"[\"']?\s*[:=]?\s*[\"']?(?P<v>\d{12})(?!\d)"
        ),
    ),
    (
        "AWS access key id",
        re.compile(r"\b(?P<v>(?:AKIA|ASIA)[A-Z0-9]{16})\b"),
    ),
    (
        "Azure subscription or tenant id",
        re.compile(
            r"(?i)\b(?:subscription[_-]?id|tenant[_-]?id)\b[\"']?\s*[:=]\s*[\"']?"
            rf"(?P<v>{UUID})\b"
        ),
    ),
    (
        "Azure subscription id in a resource path",
        re.compile(rf"/subscriptions/(?P<v>{UUID})\b"),
    ),
    (
        "GCP project id",
        re.compile(
            r"(?i:\bproject[_-]?id)\b[\"']?\s*[:=]\s*[\"']?"
            rf"(?P<v>{GCP_ID}){TAIL}"
        ),
    ),
    (
        "GCP project id",
        re.compile(rf"\bproject:\s*[\"']?(?P<v>{GCP_ID}){TAIL}"),
    ),
    (
        "GCP project id in a resource path",
        re.compile(rf"\bprojects/(?P<v>{GCP_ID}){TAIL_PATH}"),
    ),
)


def mask(value: str) -> str:
    return value[:2] + "..."


def is_allowed(value: str, line: str, start: int, end: int) -> bool:
    if value in ALLOWED_VALUES or value.lower() in ALLOWED_VALUES:
        return True
    if "example" in value.lower():
        return True
    # Anything written inside <...> is a placeholder the reader fills in.
    return line.rfind("<", 0, start) > line.rfind(">", 0, start) and ">" in line[end:]


def scan_line(line: str) -> list[tuple[str, str]]:
    """Return (kind, masked value) for each unallowed identifier on a line."""
    if IGNORE_MARKER in line:
        return []
    found: list[tuple[str, str]] = []
    for kind, pattern in PATTERNS:
        for m in pattern.finditer(line):
            value = m.group("v")
            if is_allowed(value, line, m.start("v"), m.end("v")):
                continue
            found.append((kind, mask(value)))
    return found


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout
        names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        return [root / n for n in names if (root / n).is_file()]
    except (OSError, subprocess.CalledProcessError):
        pass
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if SKIP_DIRS.intersection(rel.parts) or not path.is_file():
            continue
        files.append(path)
    return files


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    try:
        if path.stat().st_size > MAX_BYTES:
            return []
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind, masked in scan_line(line):
            hits.append((number, kind, masked))
    return hits


def run(root: Path) -> list[str]:
    problems = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(SKIP_PREFIXES):
            continue
        for number, kind, masked in scan_file(path):
            problems.append(f"{rel}:{number}: {kind} ({masked})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)
    problems = run(Path(args.root).resolve())
    if problems:
        print("identifier check FAILED (values are never printed in full):")
        for p in problems:
            print(f"  {p}")
        print(
            "Use a synthetic placeholder (see ALLOWED_VALUES in "
            "scripts/identifier_check.py) or add '# identifier-check: ignore'."
        )
        return 1
    print("identifier check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
