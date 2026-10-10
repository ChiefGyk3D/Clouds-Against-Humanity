#!/usr/bin/env python3
"""Monthly cost gate for Clouds Against Humanity.

Totals every stacks/*/cost.json manifest against docs/cost-prices.json and
fails when the total is above docs/stages/approved.json, when a size has no
price, when backups are priced from an unverified fraction, or when a costed
resource type appears in HCL outside the allowed files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

COSTED_TYPES = (
    "digitalocean_droplet",
    "digitalocean_volume",
    "digitalocean_loadbalancer",
    "digitalocean_kubernetes_cluster",
    "digitalocean_database_cluster",
    "digitalocean_reserved_ip",
    "digitalocean_floating_ip",
    "digitalocean_spaces_bucket",
)
RESOURCE_RE = re.compile(r'^\s*resource\s+"(?P<type>[a-z0-9_]+)"', re.MULTILINE)


def load_json(path):
    return json.loads(Path(path).read_text())


def resource_cost(res, prices):
    if res.get("kind") != "droplet":
        raise ValueError(f"no price model for kind {res.get('kind')!r} ({res.get('name')})")
    size = res["size"]
    table = prices["droplets"]
    if size not in table:
        raise ValueError(f"no price for size {size!r} ({res['name']})")
    cost = float(table[size])
    if res.get("backups"):
        if not prices.get("backups_fraction_verified"):
            raise ValueError("backups requested but the backup price fraction is unverified")
        cost += cost * float(prices["backups_fraction"])
    return cost


def total_cost(root, prices):
    total = 0.0
    for manifest in sorted(Path(root, "stacks").glob("*/cost.json")):
        for res in load_json(manifest)["resources"]:
            total += resource_cost(res, prices)
    return round(total, 2)


def uncosted_sources(root, allowed):
    root = Path(root)
    found = []
    for tf in sorted(root.rglob("*.tf")):
        rel = tf.relative_to(root).as_posix()
        if ".terraform" in tf.relative_to(root).parts:
            continue
        for match in RESOURCE_RE.finditer(tf.read_text()):
            kind = match.group("type")
            if kind in COSTED_TYPES and rel not in allowed.get(kind, []):
                found.append(f"{rel}: {kind}")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    root = Path(parser.parse_args(argv).root)
    prices = load_json(root / "docs/cost-prices.json")
    approved = load_json(root / "docs/stages/approved.json")
    try:
        total = total_cost(root, prices)
    except ValueError as err:
        print(f"cost-check: {err}", file=sys.stderr)
        return 1
    problems = [f"costed resource outside allowed files: {item}"
                for item in uncosted_sources(root, approved.get("allowed_sources", {}))]
    if approved["approved_monthly_total"] > approved["ceiling"]:
        problems.append("approved total is above the ceiling")
    if total > approved["approved_monthly_total"]:
        problems.append(f"planned ${total:.2f} is above approved ${approved['approved_monthly_total']:.2f}")
    print(f"cost-check: planned ${total:.2f}/mo, approved ${approved['approved_monthly_total']:.2f}, "
          f"ceiling ${approved['ceiling']:.2f}")
    for problem in problems:
        print(f"cost-check: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
