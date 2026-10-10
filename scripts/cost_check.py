#!/usr/bin/env python3
"""Monthly cost gate for Clouds Against Humanity.

Totals every stacks/*/cost.json manifest against docs/cost-prices.json and
fails when the total is above docs/stages/approved.json, when a size has no
price, when backups are priced from an unverified fraction, when any
digitalocean_* resource type is not on the free list (the droplet is allowed
only in the files in approved.json), when no cost manifest exists, when the
twingate-connector module blocks do not match the manifests' droplet entries
(or use count/for_each), when a module source is not local, or when a
*.tf.json file exists. HCL is parsed with regexes and never executed, so this
is a guardrail, not a proof.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Resource types that cost nothing. Every other digitalocean_* resource type
# fails the gate, so a new paid type cannot slip in unnoticed. The droplet is
# the one costed type and is allowed only in the files named by
# docs/stages/approved.json "allowed_sources".
FREE_TYPES = frozenset({
    "digitalocean_project",
    "digitalocean_project_resources",
    "digitalocean_tag",
    "digitalocean_vpc",
    "digitalocean_firewall",
    "digitalocean_ssh_key",
})
SKIP_DIRS = frozenset({".terraform", ".venv", ".git"})
CONNECTOR_SOURCE_SUFFIX = "twingate-connector"
RESOURCE_RE = re.compile(r'^\s*resource\s+"(?P<type>[A-Za-z0-9_]+)"', re.MULTILINE)
MODULE_RE = re.compile(r'^\s*module\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
SOURCE_RE = re.compile(r'^\s*source\s*=\s*"(?P<src>[^"]*)"', re.MULTILINE)
META_RE = re.compile(r'^\s*(?P<key>count|for_each)\s*=', re.MULTILINE)


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


def iter_files(root, pattern):
    """Yield (relative posix path, Path) for files under root, skipping tool caches."""
    root = Path(root)
    for path in sorted(root.rglob(pattern)):
        parts = path.relative_to(root).parts
        if SKIP_DIRS.intersection(parts):
            continue
        yield path.relative_to(root).as_posix(), path


def uncosted_sources(root, allowed):
    """Allowlist check: any digitalocean_* resource type that is not free fails,
    and the droplet (or any other type listed in `allowed`) only in its files."""
    found = []
    for rel, tf in iter_files(root, "*.tf"):
        for match in RESOURCE_RE.finditer(tf.read_text()):
            kind = match.group("type")
            if not kind.startswith("digitalocean_") or kind in FREE_TYPES:
                continue
            if rel not in allowed.get(kind, []):
                found.append(f"{rel}: {kind}")
    return found


def module_blocks(text):
    """Return (name, body) for each top-level-looking module block.

    The body ends at the matching closing brace, found by counting braces. It
    does not understand strings or comments, so a brace inside a quoted value
    or comment can end a block early; the checks below only read lines near
    the start of the body, which keeps this good enough for a guardrail.
    """
    blocks = []
    for match in MODULE_RE.finditer(text):
        depth, i = 1, match.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        blocks.append((match.group("name"), text[match.end():i]))
    return blocks


def module_problems(root):
    """Check module blocks. Returns (problems, connector_module_count)."""
    problems, connectors = [], 0
    for rel, tf in iter_files(root, "*.tf"):
        for name, body in module_blocks(tf.read_text()):
            src = SOURCE_RE.search(body)
            source = src.group("src") if src else ""
            if not source.startswith(("./", "../")):
                problems.append(f"{rel}: module {name!r} has a non-local source {source!r}")
                continue
            if source.rstrip("/").endswith(CONNECTOR_SOURCE_SUFFIX):
                connectors += 1
                meta = META_RE.search(body)
                if meta:
                    problems.append(f"{rel}: module {name!r} uses {meta.group('key')}; the connector "
                                    "is costed as a single instance")
    return problems, connectors


def manifest_droplets(root):
    manifests = sorted(Path(root, "stacks").glob("*/cost.json"))
    count = sum(1 for m in manifests for r in load_json(m)["resources"] if r.get("kind") == "droplet")
    return len(manifests), count


def structure_problems(root):
    """Everything the cost total cannot see: manifests, modules, unreadable HCL.

    Limits: HCL is read with regexes and never executed. This is a guardrail,
    not a proof. Dynamic module sources, string-built resource types and
    files outside *.tf are not understood; *.tf.json is refused outright.
    """
    problems = []
    manifests, droplets = manifest_droplets(root)
    if manifests == 0:
        problems.append("no stacks/*/cost.json manifest found; at least one is required")
    for rel, _ in iter_files(root, "*.tf.json"):
        problems.append(f"{rel}: *.tf.json cannot be read by this gate and is refused")
    mod_problems, connectors = module_problems(root)
    problems += mod_problems
    if connectors != droplets:
        problems.append(f"{connectors} twingate-connector module block(s) but {droplets} droplet "
                        "entr(ies) in the cost manifests; they must match")
    return problems


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
    problems = [f"resource type not on the free list or outside its allowed file: {item}"
                for item in uncosted_sources(root, approved.get("allowed_sources", {}))]
    problems += structure_problems(root)
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
