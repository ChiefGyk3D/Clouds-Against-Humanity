#!/usr/bin/env python3
"""Monthly cost gate for Clouds Against Humanity.

Totals every stack's cost.json manifest, per cloud provider, against that
provider's price table and docs/stages/approved.json. It fails when:

- a stack directory has no cost.json (stacks/**/ , found recursively);
- a provider's total is above its approved figure, or the approved figures of
  the active providers together are above the shared ceiling;
- a size or instance type has no price, or backups are priced from an
  unverified fraction;
- a resource type from a provider (digitalocean_, aws_, azurerm_, google_) is
  not on that provider's free list or allowed file, or a rejected type such as
  a NAT gateway appears;
- the number of twingate-connector module blocks in a stack differs from the
  machines in that stack's manifest (or a block uses count/for_each);
- a module source is not local, or a *.tf.json file exists;
- with --plan, the cost of the planned values in an OpenTofu plan (JSON) differs
  from the manifest, or the plan holds a type the gate cannot price.

HCL is parsed with regexes and never executed, so the source scan is a
guardrail, not a proof. The plan check is the stronger one for attributes
(a public address, a disk size, count/for_each) that source cannot show, and it
is only as trustworthy as where the plan came from: a plan produced by the
trusted run, not a file anyone can edit in a pull request.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HOURS_PER_MONTH = 730

# Provider by resource-type prefix, and by stack path (stacks/<provider>/...).
# A stack outside a provider directory is DigitalOcean's, as it always was.
PROVIDER_PREFIXES = {
    "digitalocean_": "digitalocean",
    "aws_": "aws",
    "azurerm_": "azure",
    "google_": "gcp",
}
STACK_PROVIDER_DIRS = frozenset({"aws", "azure", "gcp"})

# Resource types that cost nothing, per provider. Every other type with that
# provider's prefix fails the gate unless approved.json allows it in a file, so
# a new paid type cannot slip in unnoticed.
FREE_TYPES = {
    "digitalocean": frozenset(
        {
            "digitalocean_project",
            "digitalocean_project_resources",
            "digitalocean_tag",
            "digitalocean_vpc",
            "digitalocean_firewall",
            "digitalocean_ssh_key",
        }
    ),
    "aws": frozenset(
        {
            "aws_vpc",
            "aws_subnet",
            "aws_internet_gateway",
            "aws_route_table",
            "aws_route",
            "aws_route_table_association",
            "aws_security_group",
            "aws_vpc_security_group_ingress_rule",
            "aws_vpc_security_group_egress_rule",
            "aws_key_pair",
        }
    ),
    "azure": frozenset(),
    "gcp": frozenset(),
}

# Costed types: allowed only in the files named in approved.json.
COSTED_TYPES = {
    "digitalocean": frozenset({"digitalocean_droplet"}),
    "aws": frozenset({"aws_instance", "aws_eip", "aws_ebs_volume"}),
    "azure": frozenset(),
    "gcp": frozenset(),
}

# Never allowed at the current ceiling, whatever approved.json says.
REJECTED_TYPES = {
    "aws_nat_gateway": "a NAT gateway costs about $36.50 a month before any traffic; "
    "give the machines public addresses and no inbound rule instead",
}

MACHINE_KINDS = frozenset({"droplet", "instance"})
SKIP_DIRS = frozenset({".terraform", ".venv", ".git", ".claude"})
CONNECTOR_SOURCE_SUFFIX = "twingate-connector"
RESOURCE_RE = re.compile(r'^\s*resource\s+"(?P<type>[A-Za-z0-9_]+)"', re.MULTILINE)
MODULE_RE = re.compile(r'^\s*module\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
SOURCE_RE = re.compile(r'^\s*source\s*=\s*"(?P<src>[^"]*)"', re.MULTILINE)
META_RE = re.compile(r"^\s*(?P<key>count|for_each)\s*=", re.MULTILINE)


def load_json(path):
    return json.loads(Path(path).read_text())


def num(value, label):
    """A finite, non-negative number, or ValueError. NaN would make every
    comparison false and silently disable a limit, so it is refused here."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: {value!r} is not a number") from None
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{label}: {value!r} must be a finite number, zero or more")
    return out


def provider_of_type(rtype):
    for prefix, provider in PROVIDER_PREFIXES.items():
        if rtype.startswith(prefix):
            return provider
    return None


def provider_of_stack(rel):
    parts = Path(rel).parts
    if len(parts) >= 2 and parts[0] == "stacks" and parts[1] in STACK_PROVIDER_DIRS:
        return parts[1]
    return "digitalocean"


def price_table_path(root, provider):
    if provider == "digitalocean":
        return Path(root, "docs/cost-prices.json")
    return Path(root, f"docs/cost-prices/{provider}.json")


def load_prices(root, provider):
    path = price_table_path(root, provider)
    if not path.exists():
        raise ValueError(
            f"no price table for provider {provider!r} (expected {path.relative_to(root)})"
        )
    return load_json(path)


# ---- pricing ----------------------------------------------------------------


def droplet_cost(res, prices):
    size = res["size"]
    table = prices["droplets"]
    if size not in table:
        raise ValueError(f"no price for size {size!r} ({res['name']})")
    cost = num(table[size], f"price of {size}")
    if res.get("backups"):
        if not prices.get("backups_fraction_verified"):
            raise ValueError(
                "backups requested but the backup price fraction is unverified"
            )
        cost += cost * num(prices["backups_fraction"], "backups_fraction")
    return cost


def aws_instance_cost(itype, root_gb, public_ip, prices, name="instance"):
    table = prices["instances"]
    if itype not in table:
        raise ValueError(f"no price for instance type {itype!r} ({name})")
    cost = num(table[itype], f"price of {itype}") * HOURS_PER_MONTH
    if public_ip:
        cost += (
            num(prices["public_ipv4_hourly"], "public_ipv4_hourly") * HOURS_PER_MONTH
        )
    cost += num(root_gb, f"root_gb of {name}") * num(
        prices["ebs_gp3_gb_month"], "ebs_gp3_gb_month"
    )
    return cost


def resource_cost(res, prices, provider="digitalocean"):
    kind = res.get("kind")
    if provider == "digitalocean" and kind == "droplet":
        return droplet_cost(res, prices)
    if provider == "aws":
        if kind == "instance":
            if "root_gb" not in res or "public_ip" not in res:
                raise ValueError(
                    f"instance {res.get('name')!r} must state root_gb and public_ip; the AMI default and the subnet default are not known to the gate"
                )
            return aws_instance_cost(
                res["type"], res["root_gb"], res["public_ip"], prices, res["name"]
            )
        if kind == "eip":
            return (
                num(prices["public_ipv4_hourly"], "public_ipv4_hourly")
                * HOURS_PER_MONTH
            )
        if kind == "ebs_volume":
            return num(res["gb"], "gb") * num(
                prices["ebs_gp3_gb_month"], "ebs_gp3_gb_month"
            )
    raise ValueError(
        f"no price model for kind {kind!r} ({res.get('name')}) on {provider}"
    )


def stack_manifests(root):
    """Yield (stack dir relative path, manifest path) for every cost.json under stacks/."""
    for path in sorted(Path(root, "stacks").rglob("cost.json")):
        parts = path.relative_to(root).parts
        if SKIP_DIRS.intersection(parts):
            continue
        yield path.parent.relative_to(root).as_posix(), path


def provider_totals(root):
    """Return {provider: total} summed from the manifests."""
    totals = {}
    cache = {}
    for rel, manifest in stack_manifests(root):
        provider = provider_of_stack(rel)
        if provider not in cache:
            cache[provider] = load_prices(root, provider)
        for res in load_json(manifest)["resources"]:
            totals[provider] = totals.get(provider, 0.0) + resource_cost(
                res, cache[provider], provider
            )
    return {p: round(t, 2) for p, t in totals.items()}


def total_cost(root, prices=None):
    """Sum of every provider's manifests. `prices` overrides the DigitalOcean table (tests)."""
    if prices is not None:
        total = 0.0
        for rel, manifest in stack_manifests(root):
            if provider_of_stack(rel) == "digitalocean":
                for res in load_json(manifest)["resources"]:
                    total += resource_cost(res, prices)
        return round(total, 2)
    return round(sum(provider_totals(root).values()), 2)


# ---- plan JSON --------------------------------------------------------------


def plan_cost(plan, prices):
    """Cost the planned values of an AWS plan (tofu show -json). Returns (total, problems).

    The plan resolves count, for_each and defaults, which the source cannot.
    Anything it cannot price is a problem, never a zero.
    """
    total, problems = 0.0, []
    free = FREE_TYPES["aws"]
    for rc in plan.get("resource_changes", []):
        rtype, addr = rc.get("type", ""), rc.get("address", "?")
        change = rc.get("change", {})
        if rc.get("mode") == "data" or change.get("actions") == ["delete"]:
            continue
        if not rtype.startswith("aws_"):
            continue
        if rtype in REJECTED_TYPES:
            problems.append(f"{addr}: {rtype} is rejected: {REJECTED_TYPES[rtype]}")
            continue
        after, unknown = change.get("after") or {}, change.get("after_unknown") or {}
        if rtype in free:
            continue
        try:
            if rtype == "aws_instance":
                total += plan_instance_cost(addr, after, unknown, prices)
            elif rtype == "aws_eip":
                total += (
                    num(prices["public_ipv4_hourly"], "public_ipv4_hourly")
                    * HOURS_PER_MONTH
                )
            elif rtype == "aws_ebs_volume":
                total += plan_volume_gb(addr, after, unknown, "size") * num(
                    prices["ebs_gp3_gb_month"], "ebs_gp3_gb_month"
                )
            else:
                problems.append(f"{addr}: {rtype} has no price in the gate")
        except ValueError as err:
            problems.append(str(err))
    return round(total, 2), problems


GP3_BASELINE = {"iops": 3000, "throughput": 125}


def check_volume_shape(addr, block, unknown, type_key):
    """The price table is gp3 at baseline performance. Anything else costs
    more or differently, so it is refused until it is modeled."""
    vtype = block.get(type_key)
    if unknown.get(type_key) or vtype not in (None, "gp3"):
        raise ValueError(f"{addr}: volume type {vtype!r} is not priced (only gp3 is)")
    for key, baseline in GP3_BASELINE.items():
        value = block.get(key)
        if unknown.get(key) or value not in (None, 0, baseline):
            raise ValueError(
                f"{addr}: provisioned {key} {value!r} is above the gp3 baseline and is not priced"
            )


def plan_volume_gb(addr, block, unknown, key):
    check_volume_shape(addr, block, unknown, "type" if key == "size" else "volume_type")
    if unknown.get(key) or block.get(key) is None:
        raise ValueError(
            f"{addr}: volume size is not known in the plan; set it explicitly"
        )
    return num(block[key], f"{addr}: {key}")


def plan_instance_cost(addr, after, unknown, prices):
    if unknown.get("instance_type") or not after.get("instance_type"):
        raise ValueError(f"{addr}: instance_type is not known in the plan")
    roots = after.get("root_block_device") or []
    if not roots:
        raise ValueError(
            f"{addr}: no root_block_device.volume_size; the AMI default is not priced, set it explicitly"
        )
    gb = plan_volume_gb(
        addr, roots[0], (unknown.get("root_block_device") or [{}])[0], "volume_size"
    )
    if unknown.get("ebs_block_device"):
        raise ValueError(f"{addr}: ebs_block_device is not fully known in the plan")
    for extra in after.get("ebs_block_device") or []:
        gb += plan_volume_gb(addr, extra, {}, "volume_size")
    # Only an explicit false avoids the address. Unset or unknown is treated as
    # public: the subnet default and the later assignment are not visible here.
    public = after.get("associate_public_ip_address") is not False
    return aws_instance_cost(after["instance_type"], gb, public, prices, addr)


def plan_problems(plan_path, stack, root):
    """Compare the cost of a plan with the same stack's manifest."""
    provider = provider_of_stack(stack)
    if provider != "aws":
        return [f"--plan costing is implemented for aws only, not {provider}"]
    prices = load_prices(root, "aws")
    manifest = Path(root, stack, "cost.json")
    if not manifest.exists():
        return [f"{stack}: no cost.json to reconcile the plan against"]
    declared = round(
        sum(resource_cost(r, prices, "aws") for r in load_json(manifest)["resources"]),
        2,
    )
    planned, problems = plan_cost(load_json(plan_path), prices)
    if abs(planned - declared) > 0.005:
        problems.append(
            f"{stack}: the plan costs ${planned:.2f} but cost.json declares ${declared:.2f}; they must match"
        )
    return problems


# ---- source scan ------------------------------------------------------------


def strip_comments(text):
    """Remove #, // and /* */ comments, leaving string contents alone.

    Without this a commented-out `source = "./x"` before the real, remote
    source is read as the module's source, and a brace inside a comment ends a
    block early.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i : j + 1])
            i = j + 1
        elif c == "#" or text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            out.append(" ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def iter_files(root, pattern):
    """Yield (relative posix path, Path) for files under root, skipping tool caches."""
    root = Path(root)
    for path in sorted(root.rglob(pattern)):
        parts = path.relative_to(root).parts
        if SKIP_DIRS.intersection(parts):
            continue
        yield path.relative_to(root).as_posix(), path


def uncosted_sources(root, allowed, approved_providers=None):
    """Allowlist check over every provider's resource types.

    `allowed` maps a costed type to the files that may contain it. A type with a
    provider prefix that is neither free, nor costed-and-in-its-file fails; a
    rejected type fails whatever `allowed` says. A provider that is not
    approved at all fails every non-free type it uses.
    """
    found = []
    for rel, tf in iter_files(root, "*.tf"):
        for match in RESOURCE_RE.finditer(strip_comments(tf.read_text())):
            kind = match.group("type")
            provider = provider_of_type(kind)
            if provider is None:
                continue
            if kind in REJECTED_TYPES:
                found.append(f"{rel}: {kind} is rejected: {REJECTED_TYPES[kind]}")
                continue
            if kind in FREE_TYPES[provider]:
                continue
            if approved_providers is not None and provider not in approved_providers:
                found.append(
                    f"{rel}: {kind} (provider {provider} is not in approved.json)"
                )
            elif kind not in COSTED_TYPES[provider]:
                # approved.json can place a priced type in a file, but cannot
                # approve a type the gate has no price model for.
                found.append(f"{rel}: {kind} (the gate has no price model for it)")
            elif rel not in allowed.get(kind, []):
                found.append(f"{rel}: {kind}")
    return found


def module_blocks(text):
    """Return (name, body) for each top-level-looking module block.

    Comments are removed first and braces inside quoted strings are not
    counted. Heredocs are not understood.
    """
    text = strip_comments(text)
    blocks = []
    for match in MODULE_RE.finditer(text):
        depth, i = 1, match.end()
        while i < len(text) and depth:
            if text[i] == '"':
                i += 1
                while i < len(text) and text[i] != '"':
                    i += 2 if text[i] == "\\" else 1
            else:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        blocks.append((match.group("name"), text[match.end() : i]))
    return blocks


def module_problems(root):
    """Check module blocks. Returns (problems, {stack dir: connector module count})."""
    problems, connectors = [], {}
    for rel, tf in iter_files(root, "*.tf"):
        for name, body in module_blocks(tf.read_text()):
            src = SOURCE_RE.search(body)
            source = src.group("src") if src else ""
            if not source.startswith(("./", "../")):
                problems.append(
                    f"{rel}: module {name!r} has a non-local source {source!r}"
                )
                continue
            if source.rstrip("/").endswith(CONNECTOR_SOURCE_SUFFIX):
                stack = str(Path(rel).parent.as_posix())
                connectors[stack] = connectors.get(stack, 0) + 1
                meta = META_RE.search(body)
                if meta:
                    problems.append(
                        f"{rel}: module {name!r} uses {meta.group('key')}; the connector is costed as a single instance"
                    )
    return problems, connectors


def stack_dirs(root):
    """Every directory under stacks/ that holds OpenTofu files."""
    dirs = set()
    for rel, _ in iter_files(Path(root, "stacks"), "*.tf"):
        dirs.add(str(Path("stacks", rel).parent.as_posix()))
    return sorted(dirs)


def structure_problems(root):
    """Everything the cost total cannot see: manifests, modules, unreadable HCL.

    Limits: HCL is read with regexes and never executed. This is a guardrail,
    not a proof. Dynamic module sources, string-built resource types and
    files outside *.tf are not understood; *.tf.json is refused outright.
    """
    problems = []
    manifests = dict(stack_manifests(root))
    if not manifests:
        problems.append(
            "no stacks/**/cost.json manifest found; at least one is required"
        )
    for stack in stack_dirs(root):
        if stack not in manifests:
            problems.append(
                f"{stack}: has OpenTofu files but no cost.json; every stack needs a manifest"
            )
    for rel, _ in iter_files(root, "*.tf.json"):
        problems.append(f"{rel}: *.tf.json cannot be read by this gate and is refused")
    mod_problems, connectors = module_problems(root)
    problems += mod_problems
    for stack in sorted(set(connectors) | set(manifests)):
        machines = 0
        if stack in manifests:
            machines = sum(
                1
                for r in load_json(manifests[stack])["resources"]
                if r.get("kind") in MACHINE_KINDS
            )
        have = connectors.get(stack, 0)
        if have != machines:
            problems.append(
                f"{stack}: {have} twingate-connector module block(s) but {machines} machine entr(ies) in its cost.json; they must match"
            )
    return problems


# ---- approval ---------------------------------------------------------------


def approval_problems(approved, totals):
    """Per-provider approval and the shared ceiling."""
    problems = []
    ceiling = num(approved["ceiling"], "ceiling")
    providers = approved["providers"]
    for provider in totals:
        if provider not in providers:
            problems.append(
                f"provider {provider} has a manifest but no entry in approved.json"
            )
    active = 0.0
    for provider, entry in providers.items():
        cap = num(entry["approved_monthly_total"], f"{provider} approved_monthly_total")
        if cap > ceiling:
            problems.append(
                f"{provider}: approved ${cap:.2f} is above the ceiling ${ceiling:.2f}"
            )
        if entry.get("active"):
            active += cap
        planned = totals.get(provider, 0.0)
        if planned > cap:
            problems.append(
                f"{provider}: planned ${planned:.2f} is above approved ${cap:.2f}"
            )
    if active > ceiling:
        problems.append(
            f"the approved figures of the active providers add up to ${active:.2f}, above the shared ceiling ${ceiling:.2f}; "
            "mark one inactive or lower an approval"
        )
    return problems


def allowed_sources(approved):
    merged = {}
    for entry in approved["providers"].values():
        for kind, files in entry.get("allowed_sources", {}).items():
            merged.setdefault(kind, []).extend(files)
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--plan",
        help="OpenTofu plan as JSON (tofu show -json), costed and compared with the manifest",
    )
    parser.add_argument(
        "--stack",
        help="the stack directory the --plan belongs to, for example stacks/aws/10-access",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    approved = load_json(root / "docs/stages/approved.json")
    try:
        totals = provider_totals(root)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as err:
        print(
            f"cost-check: unreadable manifest, price table or plan input: {err!r}",
            file=sys.stderr,
        )
        return 1
    problems = [
        f"resource type not on the free list, not approved, or outside its allowed file: {item}"
        for item in uncosted_sources(
            root, allowed_sources(approved), set(approved["providers"])
        )
    ]
    problems += structure_problems(root)
    try:
        problems += approval_problems(approved, totals)
        if args.plan:
            if not args.stack:
                problems.append("--plan needs --stack")
            else:
                problems += plan_problems(args.plan, args.stack, root)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as err:
        print(
            f"cost-check: unreadable approval or plan input: {err!r}", file=sys.stderr
        )
        return 1
    for provider, total in sorted(totals.items()):
        entry = approved["providers"].get(provider, {})
        state = (
            "active"
            if entry.get("active")
            else "inactive (the maintainer attests it is not applied)"
        )
        print(
            f"cost-check: {provider}: planned ${total:.2f}/mo, approved ${float(entry.get('approved_monthly_total', 0.0)):.2f}, {state}"
        )
    print(f"cost-check: shared ceiling ${float(approved['ceiling']):.2f}")
    for problem in problems:
        print(f"cost-check: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
