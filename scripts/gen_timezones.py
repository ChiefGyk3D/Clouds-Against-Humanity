"""Regenerate modules/twingate-bootstrap/timezones.txt from the local tz database.

The bootstrap module accepts only names in that file, so a typo such as
Foo/Bar fails at plan time instead of leaving the machine on UTC. The list
comes from `zoneinfo.available_timezones()`, which depends on the tz database
of the machine that runs this script, and zones are added or renamed over
time. Regenerate it now and then and review the diff; tests check the shape of
the file, not equality with whatever database a CI runner has.

Usage: python -I scripts/gen_timezones.py [--root ROOT]
"""

from __future__ import annotations

import argparse
import zoneinfo
from pathlib import Path

TARGET = Path("modules/twingate-bootstrap/timezones.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    names = sorted(zoneinfo.available_timezones())
    if "UTC" not in names or "America/New_York" not in names:
        raise SystemExit("gen_timezones: the local tz database looks incomplete")
    path = Path(args.root) / TARGET
    path.write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"gen_timezones: wrote {len(names)} zones to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
