#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A toy DLP scanner for FAKE data. It teaches the ideas; it is not a product.

Ideas shown: a dictionary (keywords), patterns (regex), a validator (Luhn),
a threshold (how many hits make a finding), an allowlist (false-positive
tuning) and a report that masks what it found.
"""
import argparse
import json
import mailbox
import re
import sys
from pathlib import Path

PATTERNS = {
    "fake_member_id": re.compile(r"\bQX-\d{6}-ZZ\b"),
    "card_candidate": re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
    "email_example": re.compile(r"\b[\w.+-]+@example\.com\b"),
}
DICTIONARY = ["member", "card", "charge", "ssn"]  # words that raise suspicion


def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def mask(value: str) -> str:
    keep = value[-2:] if len(value) > 4 else ""
    return "*" * (len(value) - len(keep)) + keep


def scan_text(text: str, allow: set[str], threshold: int) -> list[dict]:
    """Return masked hits if the text counts as a finding, else an empty list.

    A finding needs `threshold` sensitive hits, or one sensitive hit plus a
    dictionary word. An email address alone is not a finding.
    """
    hits = []
    for name, rx in PATTERNS.items():
        for m in rx.finditer(text):
            val = m.group(0)
            if name == "card_candidate" and not luhn_ok(val):
                continue  # validator: right shape, wrong checksum
            if val in allow:
                continue  # tuning: a known false positive
            hits.append({"type": name, "masked": mask(val)})
    words = [w for w in DICTIONARY if re.search(rf"\b{w}\b", text, re.I)]
    sensitive = [h for h in hits if h["type"] != "email_example"]
    if len(sensitive) >= threshold or (sensitive and words):
        return hits
    return []


def items(path: Path):
    for p in sorted(path.rglob("*")):
        if p.suffix == ".mbox":
            for i, msg in enumerate(mailbox.mbox(str(p))):
                yield f"{p.name}#msg{i + 1}", f"{msg.get('Subject', '')}\n{msg.get_payload()}"
        elif p.is_file():
            for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                yield f"{p.name}:{n}", line


def scan_path(path: Path, allow: set[str], threshold: int) -> dict:
    findings = {}
    for where, text in items(path):
        hits = scan_text(text, allow, threshold)
        if hits:
            findings[where] = hits
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--threshold", type=int, default=2)
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    findings = scan_path(Path(a.path), set(a.allow), a.threshold)
    if a.json:
        print(json.dumps(findings, indent=2))
    else:
        for where, hits in findings.items():
            print(f"FINDING {where}: " + ", ".join(f"{h['type']}={h['masked']}" for h in hits))
        print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
