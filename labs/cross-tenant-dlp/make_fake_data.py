#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build FAKE sensitive-looking data at run time. Nothing here is real.

Made-up ID format:  QX-######-ZZ   (not any real national ID)
Cards:              Luhn-valid numbers built from the widely published test
                    prefixes 411111 and 555555, never typed into the repo.
Emails:             name@example.com (RFC 2606 reserved domain).
"""
import argparse
import random
from pathlib import Path

from labdir import private_dir


def luhn_check_digit(partial: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(partial)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def fake_card(rng: random.Random, prefix: str) -> str:
    body = prefix + "".join(rng.choice("0123456789") for _ in range(15 - len(prefix)))
    return body + luhn_check_digit(body)


def fake_id(rng: random.Random) -> str:
    return f"QX-{rng.randrange(100000, 999999)}-ZZ"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = private_dir(a.out)
    (out / "batch").mkdir(parents=True, exist_ok=True)
    (out / "mail").mkdir(parents=True, exist_ok=True)
    names = ["alex", "sam", "jo", "kai", "robin", "max"]
    for n in range(1, 4):
        rows = ["name,email,member_id,note"]
        for _ in range(4):
            nm = rng.choice(names)
            rows.append(
                f"{nm},{nm}{rng.randrange(10, 99)}@example.com,{fake_id(rng)},ordinary row"
            )
        (out / "batch" / f"extract-{n}.csv").write_text("\n".join(rows) + "\n")
    # Card numbers (Luhn-valid) and a near miss (right shape, fails the check).
    good = fake_card(rng, "411111")
    good2 = fake_card(rng, "555555")
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    (out / "batch" / "payments.txt").write_text(
        f"order 1 card {good}\n"
        f"order 2 card {good2[:4]} {good2[4:8]} {good2[8:12]} {good2[12:]}\n"
        f"tracking number {bad} (looks like a card, fails the check)\n"
    )
    # A deliberate false positive: a part number shaped like the fake ID.
    (out / "batch" / "parts.txt").write_text(
        "part QX-123456-ZZ is a catalog item, not a person; card stock in aisle 4\n"
    )
    # An mbox-like fake email set.
    msgs = []
    for i in range(1, 6):
        body = "Lunch on Friday?"
        if i == 2:
            body = f"Please update member {fake_id(rng)} and charge {fake_card(rng, '411111')}."
        if i == 4:
            body = f"FYI {fake_id(rng)}, {fake_id(rng)}, {fake_id(rng)} are in the list."
        msgs.append(
            f"From sender{i}@example.com Thu Oct 22 10:0{i}:00 2026\n"
            f"From: sender{i}@example.com\nTo: team@example.com\n"
            f"Subject: note {i}\n\n{body}\n"
        )
    (out / "mail" / "outbox.mbox").write_text("\n".join(msgs))
    print(f"fake data written under {out} (seed {a.seed})")


if __name__ == "__main__":
    main()
