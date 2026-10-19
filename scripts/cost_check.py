#!/usr/bin/env python3
"""Monthly cost gate for Clouds Against Humanity.

Totals every stack's cost.json manifest, per cloud provider, against that
provider's price table and docs/stages/approved.json. It fails when:

- a stack directory has no cost.json (stacks/**/ , found recursively);
- a provider's total is above its approved figure, or the approved figures of
  the active providers together are above the current phase's ceiling
  (approved.json `phases` and `current_phase`; see docs/cost.md);
- the per-phase ceilings are malformed, one is lower than the phase before it
  without an explicit `lowers`, or one is above `hard_max`;
- a size or instance type has no price, or backups are priced from an
  unverified fraction;
- a resource type from a provider (digitalocean_, aws_, azurerm_, google_) is
  not on that provider's free list or allowed file, or a rejected type such as
  a NAT gateway appears;
- the number of twingate-connector module blocks in a stack differs from the
  machines in that stack's manifest (or a block uses count/for_each);
- a connector module's size is not a plain `local.<name>.size` reference (its
  instance_type likewise), a costed resource uses count or for_each, a resource
  type's provider prefix is neither a known cloud nor in SAFE_PREFIXES, or a
  label holds a backslash;
- a module source is not local or goes through a dot-directory, a stack
  directory is misnamed, a dot-directory exists under stacks/ or modules/, or a
  *.tf.json / *.tofu.json file exists (*.tf and *.tofu are both read);
- a stack instance manifest (stacks/sites/<resource_key>/<stack>/cost.json with
  instance_of) is malformed, names no stack with its own manifest, carries code,
  does not match the connector modules of the stack it names, or shares a stack
  id with another manifest; or a provider's optional `sites` map does not fit
  (see docs/cost.md, "Stack instances");
- with --plan, the cost of the planned values in an OpenTofu plan (JSON) differs
  from the manifest, or the plan holds a type the gate cannot price.

HCL is scanned (comments, strings and heredocs understood) and never executed,
so the source scan is a guardrail, not a proof; the plan check below is the
guarantee. The plan check is the stronger one for attributes
(a public address, a disk size, count/for_each) that source cannot show, and it
is only as trustworthy as where the plan came from: a plan produced by the
trusted run, not a file anyone can edit in a pull request.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import posixpath
import re
import sys
from decimal import Decimal
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
            "aws_default_security_group",
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
# Skipped at the repository top level only: tool state and agent worktrees.
TOP_SKIP_DIRS = frozenset({".git", ".venv", ".claude"})
# Directories whose contents the gate must be able to read in full.
GUARDED_TOP = frozenset({"stacks", "modules"})
HCL_SUFFIXES = (".tf", ".tofu")
JSON_SUFFIXES = (".tf.json", ".tofu.json")
SITES_DIR = "stacks/sites"
RESOURCE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STACK_NAME_RE = re.compile(r"^[0-9]+-[A-Za-z0-9][A-Za-z0-9_-]*$")
CONNECTOR_SOURCE_SUFFIX = "twingate-connector"
# Connector size attribute -> the manifest key its local must read.
CONNECTOR_SIZE_ATTRS = {"size": "size", "instance_type": "type"}
# Providers that create nothing billable. Any other prefix that is not a known
# cloud fails the gate until it is added here deliberately.
SAFE_PREFIXES = (
    "twingate_",
    "terraform_",
    "null_",
    "random_",
    "time_",
    "tls_",
    "local_",
)

# aws_instance plan attributes that change the bill and that the gate does not
# model. Setting any of them to a non-empty value is a problem, not a zero;
# tenancy and credit_specification have their own rule in unpriced_instance_attrs.
# A value unknown in the plan is refused when the configuration sets the attribute
# (see unknown_unpriced_attrs); an unset computed default is not.
AWS_INSTANCE_UNPRICED_ATTRS = (
    "instance_market_options",
    "placement_group",
    "host_id",
    "host_resource_group_arn",
    "license_specification",
    "network_interface",
    "launch_template",
    "monitoring",
)
# Every attribute the unknown-value rule looks at.
AWS_INSTANCE_CHECKED_ATTRS = AWS_INSTANCE_UNPRICED_ATTRS + (
    "tenancy",
    "credit_specification",
)


def _no_duplicate_keys(pairs):
    """Python keeps the last of a repeated key, so the value enforced would
    differ from the one a reviewer reads first. Refuse the file instead."""
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r} in a JSON object")
        seen.add(key)
    return dict(pairs)


def _no_constant(name):
    raise ValueError(f"{name} is not a JSON number")


def parse_json(text):
    """json.loads that rejects duplicate keys and NaN/Infinity literals."""
    return json.loads(
        text, object_pairs_hook=_no_duplicate_keys, parse_constant=_no_constant
    )


def load_json(path):
    try:
        return parse_json(Path(path).read_text())
    except ValueError as err:
        raise ValueError(f"{path}: {err}") from None


def num(value, label):
    """A finite, non-negative number, or ValueError. NaN would make every
    comparison false and silently disable a limit, so it is refused here."""
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError):
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
    backups = res.get("backups", False)
    if type(backups) is not bool:
        raise ValueError(
            f"{res['name']}: backups must be true or false, not {backups!r}"
        )
    extras = sorted(k for k in res if k.startswith("backup") and k != "backups")
    if not backups:
        if extras:
            raise ValueError(
                f"{res['name']}: {', '.join(extras)} stated while backups is false; "
                "the gate refuses a backup setting it cannot reconcile"
            )
    else:
        plan = res.get("backup_plan")
        if plan == "daily":
            raise ValueError(
                f"{res['name']}: daily backups are not priced or verified (the gate "
                "prices the basic weekly plan only); refused"
            )
        if plan != "weekly":
            raise ValueError(
                f'{res["name"]}: backups need backup_plan "weekly" (the only plan '
                f"the gate prices); got {plan!r}. DigitalOcean defaults to daily "
                "when no plan is stated, so a missing plan is refused"
            )
        other = [k for k in extras if k != "backup_plan"]
        if other:
            raise ValueError(
                f"{res['name']}: backup setting(s) {', '.join(other)} are not "
                "priced (usage-based and other plans are refused)"
            )
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
    for rel in walk_repo(root)[0]:
        if (
            rel.startswith("stacks/")
            and rel.endswith("/cost.json")
            and not is_hidden(rel)
        ):
            yield str(Path(rel).parent.as_posix()), Path(root, rel)


def is_instance_dir(rel):
    """True for a directory at or under stacks/sites/ (data-only stack instances)."""
    return rel == SITES_DIR or rel.startswith(SITES_DIR + "/")


def instance_key(rel):
    """The resource_key of stacks/sites/<resource_key>/..., or None."""
    parts = Path(rel).parts
    return parts[2] if is_instance_dir(rel) and len(parts) >= 3 else None


def declared_instance_of(data):
    return data.get("instance_of") if isinstance(data, dict) else None


def instance_of_problem(value):
    """Why `instance_of` is not a plain stack path, or None."""
    if not isinstance(value, str) or not value:
        return "must be a non-empty string such as stacks/10-access"
    parts = value.split("/")
    if (
        value != posixpath.normpath(value)
        or parts[0] != "stacks"
        or len(parts) < 2
        or "" in parts
        or any(p in (".", "..") for p in parts)
    ):
        return f"{value!r} must be a normalized stack path such as stacks/10-access"
    if is_instance_dir(value):
        return (
            f"{value!r} must not point into stacks/sites (an instance is not a stack)"
        )
    return None


def manifest_provider(rel, data):
    """Provider of a manifest. An instance takes it from the stack it names;
    an unusable instance_of falls back to the path (structure_problems fails it)."""
    if is_instance_dir(rel):
        target = declared_instance_of(data)
        if instance_of_problem(target) is None:
            return provider_of_stack(target)
    return provider_of_stack(rel)


def priced_manifests(root):
    """Yield (rel, provider, site key or None, manifest data) for every manifest."""
    for rel, manifest in stack_manifests(root):
        data = load_json(manifest)
        yield rel, manifest_provider(rel, data), instance_key(rel), data


def site_totals(root):
    """Return {provider: {"": base stacks total, <resource_key>: site total}}."""
    totals, cache = {}, {}
    for rel, provider, key, data in priced_manifests(root):
        if provider not in cache:
            cache[provider] = load_prices(root, provider)
        bucket = totals.setdefault(provider, {})
        bucket.setdefault(key or "", 0.0)
        for res in data["resources"]:
            bucket[key or ""] = bucket.get(key or "", 0.0) + resource_cost(
                res, cache[provider], provider
            )
    return totals


def provider_totals(root):
    """Return {provider: total} summed from the manifests."""
    return {p: round(sum(parts.values()), 2) for p, parts in site_totals(root).items()}


def stack_id(rel, instance_of):
    """The Spacelift stack id a manifest directory answers to.

    stacks/<path>                          -> cah-<path with / as ->
    stacks/sites/<key>/<path> (an instance) -> cah-<path with / as ->-<key>
    """
    if is_instance_dir(rel):
        base = Path(instance_of).parts[1:]
        return "cah-" + "-".join(base) + "-" + instance_key(rel)
    return "cah-" + "-".join(Path(rel).parts[1:])


def manifest_ids(root):
    """{stack id: [manifest directories]} for every manifest with a usable
    instance_of (an instance with a bad one maps to no id)."""
    ids = {}
    for rel, _, _, data in priced_manifests(root):
        target = declared_instance_of(data)
        if is_instance_dir(rel) and (
            instance_key(rel) is None or instance_of_problem(target)
        ):
            continue
        ids.setdefault(stack_id(rel, target), []).append(rel)
    return ids


def total_cost(root, prices=None):
    """Sum of every provider's manifests. `prices` overrides the DigitalOcean table (tests)."""
    if prices is not None:
        total = 0.0
        for _, provider, _, data in priced_manifests(root):
            if provider == "digitalocean":
                for res in data["resources"]:
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
                total += plan_instance_cost(
                    addr, after, unknown, prices, config_expressions(plan, rc)
                )
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


def mask_has_unknown(mask):
    """True when an after_unknown mask marks anything, at any depth, unknown."""
    if isinstance(mask, dict):
        return any(mask_has_unknown(v) for v in mask.values())
    if isinstance(mask, list):
        return any(mask_has_unknown(v) for v in mask)
    return mask is True


def config_expressions(plan, rc):
    """The configuration's `expressions` for a resource change, or None when the
    plan does not carry that configuration (shape unknown, so callers fail closed).

    In `tofu show -json`, configuration.root_module.resources[].expressions lists
    only the attributes the configuration sets; an unset computed attribute is
    absent there while still being unknown in after_unknown. Resources in modules
    sit under module_calls.<name>.module.resources.
    """
    node = (plan.get("configuration") or {}).get("root_module")
    address = rc.get("address", "")
    module_address = rc.get("module_address")
    if module_address is None:
        lead = re.match(r"^((?:module\.[^.\[]+(?:\[[^\]]*\])?\.)*)", address)
        module_address = lead.group(1)
    for name in re.findall(r"module\.([^.\[]+)", module_address or ""):
        if not isinstance(node, dict):
            return None
        node = ((node.get("module_calls") or {}).get(name) or {}).get("module")
    if not isinstance(node, dict):
        return None
    name = rc.get("name") or re.sub(r"\[.*$", "", address.rsplit(".", 1)[-1])
    for res in node.get("resources") or []:
        if (
            res.get("mode", "managed") == "managed"
            and res.get("type") == rc.get("type")
            and res.get("name") == name
        ):
            expr = res.get("expressions")
            return expr if isinstance(expr, dict) else {}
    return None


def unknown_unpriced_attrs(unknown, expressions):
    """Attributes the plan cannot value and that the configuration sets (or that
    cannot be told apart from set, when the configuration is missing).

    Not flagged: an unknown attribute the configuration does not set. That is a
    provider default computed at apply (tenancy, placement_group, ...), which a
    normal plan shows as unknown. Not caught either way: a default that is itself
    priced differently (CPU credits on a T-family type have their own rule in
    require_standard_credits).
    """
    found = []
    for attr in AWS_INSTANCE_CHECKED_ATTRS:
        if mask_has_unknown(unknown.get(attr)):
            if expressions is None:
                found.append(
                    f"{attr} (unknown in the plan and the plan carries no configuration to show it unset)"
                )
            elif attr in expressions:
                found.append(
                    f"{attr} (set by the configuration but unknown in the plan)"
                )
    return found


def unpriced_instance_attrs(after):
    """Names (with values) of aws_instance attributes the gate does not price."""
    found = []
    if after.get("tenancy") not in (None, "default"):
        found.append(f"tenancy={after['tenancy']!r}")
    for spec in after.get("credit_specification") or []:
        if str((spec or {}).get("cpu_credits", "")).lower() == "unlimited":
            found.append("credit_specification.cpu_credits='unlimited'")
    for attr in AWS_INSTANCE_UNPRICED_ATTRS:
        if after.get(attr) not in (None, "", False, [], {}):
            found.append(f"{attr}={after[attr]!r}")
    return found


# Burstable families launch in unlimited CPU-credit mode when nothing is set,
# and surplus credits are billed on top of the hourly price. Fail closed: the
# plan must say "standard" for these, because the omitted default is not priced.
BURSTABLE_FAMILIES = ("t2.", "t3.", "t3a.", "t4g.")


def require_standard_credits(addr, after):
    itype = str(after.get("instance_type") or "")
    if not itype.startswith(BURSTABLE_FAMILIES):
        return
    specs = after.get("credit_specification") or []
    if not any(
        str((spec or {}).get("cpu_credits", "")).lower() == "standard" for spec in specs
    ):
        raise ValueError(
            f"{addr}: {itype} is burstable and credit_specification.cpu_credits is not "
            "'standard' in the plan; the omitted default is unlimited, whose surplus "
            "credits are not priced"
        )


def plan_instance_cost(addr, after, unknown, prices, expressions=None):
    extras = unpriced_instance_attrs(after) + unknown_unpriced_attrs(
        unknown, expressions
    )
    if extras:
        raise ValueError(
            f"{addr}: unpriced attribute {'; '.join(extras)}; the gate prices the "
            "instance type, root disk and public address only"
        )
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
    require_standard_credits(addr, after)
    # Only an explicit false avoids the address. Unset or unknown is treated as
    # public: the subnet default and the later assignment are not visible here.
    public = after.get("associate_public_ip_address") is not False
    return aws_instance_cost(after["instance_type"], gb, public, prices, addr)


def plan_problems(plan_path, stack, root):
    """Compare the cost of a plan with the same stack's manifest."""
    manifest = Path(root, stack, "cost.json")
    if not manifest.exists():
        return [f"{stack}: no cost.json to reconcile the plan against"]
    # An instance (stacks/sites/...) takes its provider from instance_of and is
    # compared with its own manifest, not the base stack's.
    provider = manifest_provider(stack, load_json(manifest))
    if provider != "aws":
        return [f"--plan costing is implemented for aws only, not {provider}"]
    prices = load_prices(root, "aws")
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
#
# The source scan reads HCL with a small tokenizer-aware scanner. It understands
# comments, quoted strings (with ${...} interpolation) and heredocs, so that a
# `/*`, a brace or the word `resource` inside a string or heredoc is text and
# not code. It is still a guardrail, not a parser: see the module docstring.


class HclError(ValueError):
    """The file has a shape this scanner will not guess at (fail closed)."""


HEREDOC_OPEN_RE = re.compile(
    r"<<(?P<dash>-?)(?P<ident>[A-Za-z_][A-Za-z0-9_-]*)[ \t]*\r?\n"
)
# A bare label is an identifier: "=", ":" and braces are not label characters, so
# `module = { ... }` inside an object is an attribute, not a block header.
LABEL = r'"(?:[^"\\\n]|\\.)*"|[^\W\d][\w-]*'
LABEL_RE = re.compile(LABEL)
HEADER_RE = re.compile(
    rf"^[ \t]*(?P<kind>resource|module)(?P<labels>(?:[ \t]+(?:{LABEL}))*)[ \t]*\{{",
    re.MULTILINE,
)
ATTR_RE = re.compile(
    r"\s*(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\s*=(?!=)\s*(?P<value>.*?)\s*$", re.DOTALL
)
STRING_LITERAL_RE = re.compile(r'"(?P<text>[^"\\$%\n]*)"')
# `size = local.<name>.size`: nothing else ties a droplet to cost.json.
LOCAL_REF_RE = r"local\.[A-Za-z_][A-Za-z0-9_-]*\.{key}"


def blank(text):
    """Spaces for every character but newlines, so line numbers survive."""
    return re.sub(r"[^\n]", " ", text)


def skip_interpolation(text, j):
    """j is just after `${` or `%{`; return the index after the matching `}`."""
    depth, n = 1, len(text)
    while j < n:
        c = text[j]
        if c == '"':
            j = skip_string(text, j)
            continue
        if c == "#" or text.startswith("//", j):
            nl = text.find("\n", j)
            j = n if nl == -1 else nl
            continue
        if text.startswith("/*", j):
            end = text.find("*/", j + 2)
            if end == -1:
                raise HclError("unterminated /* comment in an interpolation")
            j = end + 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise HclError("unterminated ${...} interpolation")


def skip_string(text, i):
    """i is at an opening quote; return the index after the closing quote.

    A raw newline ends nothing: HCL quoted strings are single-line, so one that
    runs past the line is refused rather than guessed at.
    """
    j, n = i + 1, len(text)
    while j < n:
        c = text[j]
        if c == '"':
            return j + 1
        if c == "\n":
            break
        if c == "\\":
            j += 2
        elif text.startswith(("$${", "%%{"), j):
            j += 3
        elif text.startswith(("${", "%{"), j):
            j = skip_interpolation(text, j + 2)
        else:
            j += 1
    raise HclError("unterminated string")


def strip_comments(text):
    """Remove comments and heredoc bodies; leave quoted strings alone.

    #, // and /* */ comments become nothing (newlines are kept, so line numbers
    stay true). A heredoc, `<<ID` or `<<-ID` at the end of a line, is string
    content through the line whose stripped text equals ID: its body is blanked,
    so a `/*`, a brace or a `resource` word inside it is never read as code.
    Without this a commented-out `source = "./x"` before the real, remote source
    is read as the module's source, and a brace inside a comment or heredoc ends
    a block early.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = skip_string(text, i)
            out.append(text[i:j])
            i = j
        elif c == "#" or text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                raise HclError("unterminated /* comment")
            out.append(blank(text[i : end + 2]))
            i = end + 2
        elif text.startswith("<<", i):
            match = HEREDOC_OPEN_RE.match(text, i)
            if not match:
                raise HclError("a << that is not a heredoc opener this scanner reads")
            out.append(match.group(0))
            ident, pos = match.group("ident"), match.end()
            while True:
                if pos >= n:
                    raise HclError(f"unterminated heredoc <<{ident}")
                eol = text.find("\n", pos)
                eol = n if eol == -1 else eol
                if text[pos:eol].strip() == ident:
                    out.append(blank(text[match.end() : eol]))
                    i = eol
                    break
                pos = eol + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def block_end(text, i):
    """i is just after a `{`; return the index of its matching `}`."""
    depth, n = 1, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i = skip_string(text, i)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise HclError("unbalanced braces")


class Block:
    """A `resource` or `module` block header and body from comment-free text."""

    def __init__(self, kind, raw_labels, line, body):
        self.kind, self.raw_labels, self.line, self.body = kind, raw_labels, line, body
        self.labels = [
            lab[1:-1] if lab.startswith('"') and lab.endswith('"') else lab
            for lab in raw_labels
        ]
        self.problem = None
        if any("\\" in lab for lab in raw_labels):
            self.problem = (
                f"backslash in a {kind} label {' '.join(raw_labels)}; "
                "the gate does not decode escapes in labels"
            )
        elif len(raw_labels) != (2 if kind == "resource" else 1):
            self.problem = (
                f"{kind} header with labels {' '.join(raw_labels)!r} is not understood"
            )

    def attrs(self):
        return top_level_attrs(self.body)


def find_blocks(text):
    """Every resource/module block in already-stripped text (nested ones too)."""
    blocks = []
    for match in HEADER_RE.finditer(text):
        line = text.count("\n", 0, match.start("kind")) + 1
        try:
            end = block_end(text, match.end())
        except HclError as err:
            raise HclError(f"line {line}: {err}") from None
        blocks.append(
            Block(
                match.group("kind"),
                LABEL_RE.findall(match.group("labels")),
                line,
                text[match.end() : end],
            )
        )
    return blocks


def top_level_attrs(body):
    """[(name, value)] for the attributes written directly in a block body.

    Anything inside a nested {...}, [...] or (...) is not an attribute of the
    block, so a `source = ...` in a tags object cannot stand in for the real one.
    """
    attrs, depth, start, i, n = [], 0, 0, 0, len(body)

    def flush(segment):
        match = ATTR_RE.fullmatch(segment)
        if match:
            attrs.append((match.group("name"), match.group("value")))

    while i < n:
        c = body[i]
        if c == '"':
            i = skip_string(body, i)
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth = max(depth - 1, 0)
        elif c == "\n" and depth == 0:
            flush(body[start:i])
            start = i + 1
        i += 1
    flush(body[start:])
    return attrs


def walk_repo(root):
    """Return (sorted relative file paths, layout problems).

    Skipped: .git, .venv and .claude at the repository top level (tool and
    worktree directories) and a .terraform cache anywhere. Nothing else is
    hidden from the scan. Under stacks/ and modules/ any other directory whose
    name starts with a dot is a failure, a symlinked directory is a failure,
    and a stack directory must be named NN-name or be a provider directory.
    """
    root = Path(root)
    files, problems = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        keep = []
        for name in sorted(dirnames):
            if name == ".terraform" or (not rel_dir.parts and name in TOP_SKIP_DIRS):
                continue
            child = rel_dir / name
            where = child.as_posix()
            guarded = child.parts[0] in GUARDED_TOP
            if Path(dirpath, name).is_symlink():
                problems.append(
                    f"{where}: symlinked directory is refused; the gate does not follow it, OpenTofu does"
                )
                continue
            if guarded and name.startswith("."):
                problems.append(
                    f"{where}: hidden directory under {child.parts[0]}/ is refused; "
                    "the gate does not scan it, so nothing may live there"
                )
            elif (
                child.parts[0] == "stacks"
                and len(child.parts) == 3
                and child.parts[1] == "sites"
                and not RESOURCE_KEY_RE.match(child.parts[2])
            ):
                problems.append(
                    f"{where}: resource_key must be lowercase letters, digits and dashes, "
                    "starting with a letter or digit"
                )
            elif child.parts[0] == "stacks" and not stack_name_ok(child.parts):
                problems.append(
                    f"{where}: stack directory name must be NN-name (digits, a dash, then a name) "
                    f"or one of {', '.join(sorted(STACK_PROVIDER_DIRS))} exactly, lowercase"
                )
            keep.append(name)
        dirnames[:] = keep
        for f in sorted(filenames):
            if f.endswith(HCL_SUFFIXES) and Path(dirpath, f).is_symlink():
                problems.append(
                    f"{(rel_dir / f).as_posix()}: symlinked OpenTofu file is refused"
                )
                continue
            files.append((rel_dir / f).as_posix())
    return sorted(files), problems


def stack_name_ok(parts):
    """Naming rule for stacks/<x>, stacks/<provider>/<x> and the data-only
    stacks/sites/<resource_key>/<stack path> (the key is checked by the caller)."""
    if len(parts) >= 2 and parts[1] == "sites":
        return len(parts) < 4 or stack_name_ok(("stacks", *parts[3:]))
    if len(parts) == 2:
        return parts[1] in STACK_PROVIDER_DIRS or bool(STACK_NAME_RE.match(parts[1]))
    if len(parts) == 3 and parts[1] in STACK_PROVIDER_DIRS:
        return bool(STACK_NAME_RE.match(parts[2]))
    return True


def is_hidden(rel):
    return any(part.startswith(".") for part in Path(rel).parts)


def hcl_files(root):
    """Yield (rel, stripped text, error) for every *.tf and *.tofu file."""
    for rel in walk_repo(root)[0]:
        if not rel.endswith(HCL_SUFFIXES):
            continue
        try:
            yield (
                rel,
                strip_comments(Path(root, rel).read_text(encoding="utf-8-sig")),
                None,
            )
        except (HclError, UnicodeDecodeError) as err:
            yield rel, None, str(err)


def file_blocks(root):
    """Yield (rel, Block) for every readable block; unreadable files are skipped
    here and reported once by block_problems."""
    for rel, text, error in hcl_files(root):
        if error:
            continue
        try:
            blocks = find_blocks(text)
        except HclError:
            continue
        for block in blocks:
            yield rel, block


def provider_prefix(rtype):
    head, sep, _ = rtype.partition("_")
    return head + sep


def uncosted_sources(root, allowed, approved_providers=None):
    """Allowlist check over every provider's resource types.

    `allowed` maps a costed type to the files that may contain it. A type with a
    provider prefix that is neither free, nor costed-and-in-its-file fails; a
    rejected type fails whatever `allowed` says. A provider that is not
    approved at all fails every non-free type it uses. A prefix that is neither
    a known cloud nor in SAFE_PREFIXES fails: an unknown cloud is not "free".
    """
    found = []
    for rel, block in file_blocks(root):
        if block.kind != "resource" or block.problem:
            continue
        kind = block.labels[0]
        provider = provider_of_type(kind)
        if provider is None:
            if not kind.startswith(SAFE_PREFIXES):
                found.append(
                    f"{rel}:{block.line}: {kind} (provider prefix {provider_prefix(kind)!r} "
                    "is not known to the gate; add it deliberately)"
                )
            continue
        if kind in REJECTED_TYPES:
            found.append(f"{rel}: {kind} is rejected: {REJECTED_TYPES[kind]}")
            continue
        if kind in FREE_TYPES[provider]:
            continue
        if approved_providers is not None and provider not in approved_providers:
            found.append(f"{rel}: {kind} (provider {provider} is not in approved.json)")
        elif kind not in COSTED_TYPES[provider]:
            # approved.json can place a priced type in a file, but cannot
            # approve a type the gate has no price model for.
            found.append(f"{rel}: {kind} (the gate has no price model for it)")
        elif rel not in allowed.get(kind, []):
            found.append(f"{rel}: {kind}")
    return found


def module_blocks(text):
    """Return (name, body) for each module block in the text."""
    return [
        (block.labels[0], block.body)
        for block in find_blocks(strip_comments(text))
        if block.kind == "module" and not block.problem
    ]


def module_source_problem(root, rel, block):
    """(source or None, problem or None) for one module block."""
    sources = [v for k, v in block.attrs() if k == "source"]
    if len(sources) > 1:
        return (
            None,
            f"{rel}:{block.line}: module {block.labels[0]!r} has more than one source",
        )
    match = STRING_LITERAL_RE.fullmatch(sources[0]) if sources else None
    source = match.group("text") if match else ""
    if not source.startswith(("./", "../")):
        return (
            None,
            f"{rel}: module {block.labels[0]!r} has a non-local source {source!r}",
        )
    if any(seg.startswith(".") and seg not in (".", "..") for seg in source.split("/")):
        return None, (
            f"{rel}:{block.line}: module {block.labels[0]!r} source {source!r} goes through a hidden "
            "directory (a dot-directory is never scanned, so no module may live there)"
        )
    target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), source))
    if target == ".." or target.startswith("../"):
        return None, (
            f"{rel}:{block.line}: module {block.labels[0]!r} source {source!r} is outside the repository"
        )
    resolved = Path(root, posixpath.dirname(rel), source).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        return None, (
            f"{rel}:{block.line}: module {block.labels[0]!r} source {source!r} is outside the repository "
            "once symlinks are resolved"
        )
    return source, None


def module_problems(root):
    """Check module blocks. Returns (problems, {stack dir: connector module count})."""
    problems, connectors = [], {}
    manifests = dict(stack_manifests(root))
    for rel, block in file_blocks(root):
        if block.kind != "module" or block.problem:
            continue
        name = block.labels[0]
        source, problem = module_source_problem(root, rel, block)
        if problem:
            problems.append(problem)
            continue
        if source.rstrip("/").endswith(CONNECTOR_SOURCE_SUFFIX):
            stack = str(Path(rel).parent.as_posix())
            # Only a stack's own connector blocks reconcile with its manifest; a
            # module directory may compose one without being a stack.
            if stack in manifests or stack.startswith("stacks/"):
                connectors[stack] = connectors.get(stack, 0) + 1
            attrs = block.attrs()
            for key, _ in attrs:
                if key in ("count", "for_each"):
                    problems.append(
                        f"{rel}: module {name!r} uses {key}; the connector is costed as a single instance"
                    )
                    break
            sizes = [(k, v) for k, v in attrs if k in CONNECTOR_SIZE_ATTRS]
            ok = bool(sizes) and all(
                re.fullmatch(LOCAL_REF_RE.format(key=CONNECTOR_SIZE_ATTRS[k]), v)
                for k, v in sizes
            )
            if not ok:
                problems.append(
                    f"{rel}:{block.line}: connector module {name!r} must set size (or instance_type) "
                    "to a plain reference such as local.connector_a.size, read from cost.json; "
                    "a literal or other expression is not tied to the priced manifest (see docs/cost.md)"
                )
    return problems, connectors


BACKUP_POLICY_RE = re.compile(r"(?<![A-Za-z0-9_])backup_policy(?![A-Za-z0-9_])")


def droplet_backup_problems(rel, block):
    """The source must leave droplet backups off. With backups on, DigitalOcean
    defaults to the daily plan, and backup_policy selects daily or weekly; the
    gate prices neither from source, so any way of turning them on is refused
    (the manifest path prices the weekly plan; see droplet_cost)."""
    where = f"{rel}:{block.line}: digitalocean_droplet {block.labels[1]!r}"
    found = []
    if BACKUP_POLICY_RE.search(block.body):
        found.append(
            f"{where} sets backup_policy; backup plans are not priced from source, refused"
        )
    for key, value in block.attrs():
        if key == "backups" and value.strip() != "false":
            found.append(
                f"{where} sets backups to {value.strip()!r}; it must be the literal false "
                "(backups default to the unpriced daily plan)"
            )
    return found


def block_problems(root):
    """Everything wrong with how the files themselves read: unreadable HCL,
    escapes in labels, headers the scanner does not understand, and count or
    for_each on a costed resource (the manifest cannot be reconciled with it
    without a plan)."""
    problems = []
    costed = set().union(*COSTED_TYPES.values())
    for rel, text, error in hcl_files(root):
        if error:
            problems.append(f"{rel}: unreadable HCL, refused: {error}")
            continue
        try:
            blocks = find_blocks(text)
        except HclError as err:
            problems.append(f"{rel}: unreadable HCL, refused: {err}")
            continue
        for block in blocks:
            if block.problem:
                problems.append(f"{rel}:{block.line}: {block.problem}")
            elif block.kind == "resource" and block.labels[0] in costed:
                if block.labels[0] == "digitalocean_droplet":
                    problems += droplet_backup_problems(rel, block)
                for key, _ in block.attrs():
                    if key in ("count", "for_each"):
                        problems.append(
                            f"{rel}:{block.line}: {block.labels[0]} {block.labels[1]!r} uses {key}; "
                            "the manifest cannot be reconciled without a plan, so a costed resource "
                            "may not use it"
                        )
    return problems


def stack_dirs(root):
    """Every directory under stacks/ that holds OpenTofu files."""
    dirs = set()
    for rel in walk_repo(root)[0]:
        if (
            rel.startswith("stacks/")
            and rel.endswith(HCL_SUFFIXES)
            and not is_hidden(rel)
        ):
            dirs.add(str(Path(rel).parent.as_posix()))
    return sorted(dirs)


def structure_problems(root):
    """Everything the cost total cannot see: manifests, modules, unreadable HCL.

    Limits: HCL is read with a scanner and never executed. This is a guardrail,
    not a proof. Dynamic module sources, string-built resource types and
    `dynamic` blocks are not understood; *.tf.json and *.tofu.json are refused
    outright. *.tf and *.tofu (override files included) are read.
    """
    files, problems = walk_repo(root)
    manifests = dict(stack_manifests(root))
    bases = {k: v for k, v in manifests.items() if not is_instance_dir(k)}
    if not manifests:
        problems.append(
            "no stacks/**/cost.json manifest found; at least one is required"
        )
    for stack in stack_dirs(root):
        if is_instance_dir(stack):
            continue
        if stack not in manifests:
            problems.append(
                f"{stack}: has OpenTofu files but no cost.json; every stack needs a manifest"
            )
    for rel in files:
        for suffix in JSON_SUFFIXES:
            if rel.endswith(suffix):
                problems.append(
                    f"{rel}: *{suffix} cannot be read by this gate and is refused"
                )
        if (
            is_instance_dir(str(Path(rel).parent.as_posix()))
            and rel.endswith(HCL_SUFFIXES)
            and not is_hidden(rel)
        ):
            problems.append(
                f"{rel}: instances carry no code; stacks/sites holds data (cost.json) only"
            )
    problems += block_problems(root)
    mod_problems, connectors = module_problems(root)
    problems += mod_problems
    for stack in sorted(set(connectors) | set(bases)):
        machines = 0
        if stack in bases:
            machines = machine_count(bases[stack])
        have = connectors.get(stack, 0)
        if have != machines:
            problems.append(
                f"{stack}: {have} twingate-connector module block(s) but {machines} machine entr(ies) in its cost.json; they must match"
            )
    problems += instance_problems(manifests, bases, connectors)
    problems += config_problems(root)
    return problems


def config_problems(root):
    """Every stack id in .spacelift/config.yml answers to exactly one manifest.

    No config file (a fixture) is not a problem; one that cannot be read is."""
    config = Path(root, ".spacelift/config.yml")
    if not config.exists():
        return []
    try:
        import yaml
    except ImportError:
        return [".spacelift/config.yml exists but PyYAML is not installed to read it"]
    try:
        loaded = yaml.safe_load(config.read_text(encoding="utf-8"))
        stacks = loaded["stacks"]
        if not isinstance(stacks, dict):
            raise TypeError("stacks is not a map")
    except (yaml.YAMLError, OSError, KeyError, TypeError) as err:
        return [f".spacelift/config.yml is unreadable or has no stacks map: {err!r}"]
    ids = manifest_ids(root)
    return [
        f".spacelift/config.yml stack id {sid} has {len(ids.get(sid, []))} manifest(s), expected exactly 1"
        for sid in stacks
        if len(ids.get(sid, [])) != 1
    ]


def machine_count(manifest):
    return sum(
        1 for r in load_json(manifest)["resources"] if r.get("kind") in MACHINE_KINDS
    )


def shared_code_problems(rel, data, base_manifest, target):
    """An instance deploys the base stack's code, which reads its resources from
    the base stack's own cost.json and creates ALL of them again. Until a stack
    can select the instance manifest, the instance's resource list (machines,
    volumes, addresses, every costed entry) must equal the base manifest's,
    entry by entry, matched by name."""
    mine = {r.get("name"): r for r in data["resources"]}
    base = {r.get("name"): r for r in load_json(base_manifest)["resources"]}
    if set(mine) != set(base) or len(mine) != len(data["resources"]):
        return [
            (
                f"{rel}: resource names must equal the base stack's ({target}); "
                "the shared code deploys every resource of the base manifest"
            )
        ]
    return [
        (
            f"{rel}: resource {name!r} is {res!r} but must equal the base stack's entry "
            f"{base[name]!r} in {target}/cost.json (the shared code reads the base manifest; "
            "a site-specific size needs the stack to read the instance manifest)"
        )
        for name, res in sorted(mine.items(), key=lambda kv: str(kv[0]))
        if res != base[name]
    ]


def instance_problems(manifests, bases, connectors):
    """Rules for stacks/sites/<resource_key>/<stack path>/cost.json (data only)."""
    problems, owners = [], {}
    for rel, manifest in sorted(manifests.items()):
        data = load_json(manifest)
        target = declared_instance_of(data)
        if not is_instance_dir(rel):
            if isinstance(data, dict) and "instance_of" in data:
                problems.append(
                    f"{rel}: instance_of is only allowed under stacks/sites/<resource_key>/"
                )
            continue
        key = instance_key(rel)
        if key is None or len(Path(rel).parts) < 4:
            problems.append(
                f"{rel}: an instance manifest must sit at stacks/sites/<resource_key>/<stack path>/cost.json"
            )
            continue
        if target is None:
            problems.append(
                f"{rel}: instance_of is missing; an instance manifest must name the stack whose code it deploys"
            )
            continue
        bad = instance_of_problem(target)
        if bad:
            problems.append(f"{rel}: instance_of {bad}")
            continue
        expected = f"{SITES_DIR}/{key}/{target[len('stacks/') :]}"
        if rel != expected:
            problems.append(
                f"{rel}: must sit at stacks/sites/<resource_key>/{target[len('stacks/') :]} "
                f"to be an instance of {target}"
            )
            continue
        if target not in bases:
            problems.append(
                f"{rel}: instance_of {target!r} names no stack directory with its own cost.json"
            )
            continue
        owners.setdefault(stack_id(rel, target), []).append(rel)
        problems += shared_code_problems(rel, data, bases[target], target)
        machines = machine_count(manifest)
        have = connectors.get(target, 0)
        if have != machines:
            problems.append(
                f"{rel}: {have} twingate-connector module block(s) in {target} but {machines} machine "
                "entr(ies) in this instance manifest; they must match"
            )
    for rel in bases:
        owners.setdefault(stack_id(rel, None), []).append(rel)
    for sid, rels in sorted(owners.items()):
        if len(rels) > 1:
            problems.append(
                f"duplicate stack id {sid}: {', '.join(sorted(rels))}; "
                "every stack id must have exactly one manifest"
            )
    return problems


# ---- approval ---------------------------------------------------------------


def sites_problems(provider, entry, cap, parts):
    """The optional per-site approvals under one provider.

    `parts` is {"": base stacks total, <resource_key>: site total}. With no
    `sites` map nothing here applies. With one, every instance must be named in
    it, each site stays inside its own figure, the sites together stay inside
    the provider figure, and the base stacks get what the sites leave.
    """
    if "sites" not in entry:
        return []
    sites = entry["sites"]
    if not isinstance(sites, dict) or not sites:
        return [
            f"{provider}: sites must be a non-empty map of resource_key to an object"
        ]
    problems, approved_sum = [], 0.0
    for key, site in sites.items():
        if not isinstance(key, str) or not RESOURCE_KEY_RE.match(key):
            problems.append(f"{provider}: site key {key!r} is not a valid resource_key")
            continue
        figure = site.get("approved_monthly_total") if isinstance(site, dict) else None
        if isinstance(figure, bool) or not isinstance(figure, (int, float)):
            problems.append(
                f"{provider}: site {key} needs a numeric approved_monthly_total"
            )
            continue
        site_cap = money(site["approved_monthly_total"], f"{provider} site {key}")
        approved_sum += site_cap
        planned = parts.get(key)
        if planned is not None:
            planned = round(planned, 2)
        site_cap = round(site_cap, 2)
        if planned is not None and planned > site_cap:
            problems.append(
                f"{provider}: site {key} planned ${planned:.2f} is above its approved ${site_cap:.2f}"
            )
    for key in sorted(k for k in parts if k and k not in sites):
        problems.append(
            f"{provider}: site {key} has a manifest but is not in the approved sites map"
        )
    approved_sum = round(approved_sum, 2)
    cap = round(cap, 2)
    if approved_sum > cap:
        problems.append(
            f"{provider}: approved sites add up to ${approved_sum:.2f}, above the provider approved ${cap:.2f}"
        )
    base = round(parts.get("", 0.0), 2)
    if base > round(cap - approved_sum, 2):
        problems.append(
            f"{provider}: base stacks planned ${base:.2f} are above approved ${cap:.2f} minus sites ${approved_sum:.2f}"
        )
    return problems


PHASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PHASE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHASE_STATUSES = ("planned", "current", "done")


def money(value, label):
    """A dollar figure in approved.json: a JSON number (not a string, not a
    bool), finite, zero or more, with at most two decimal places so the
    comparison the gate makes is the one a reviewer reads. Else ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: {value!r} must be a JSON number")  # noqa: TRY004
    if isinstance(value, int) and abs(value) > sys.float_info.max:
        raise ValueError(f"{label}: the number is too large")
    out = num(value, label)
    if Decimal(repr(out)).as_tuple().exponent < -2:
        raise ValueError(f"{label}: {value!r} has more than two decimal places")
    return out


def phase_number(value):
    """money() or None, for the phase checks that report their own message."""
    try:
        return money(value, "value")
    except ValueError:
        return None


def current_ceiling(approved):
    """(phase id, ceiling, reason) the gate enforces.

    With `phases` the ceiling is the `current_phase` entry's. A legacy top-level
    `ceiling` is read only when `phases` is absent. Raises ValueError when no
    usable ceiling can be found; phase_problems() explains why."""
    if "phases" not in approved:
        return "legacy", money(approved["ceiling"], "ceiling"), "legacy top-level ceiling"
    phases, current = approved["phases"], approved.get("current_phase")
    if not isinstance(phases, dict) or current not in phases:
        raise ValueError(f"current_phase {current!r} is not in phases")
    entry = phases[current]
    if not isinstance(entry, dict):
        raise ValueError(f"phase {current}: not an object")  # noqa: TRY004
    ceiling = money(entry.get("ceiling"), f"phase {current} ceiling")
    return current, ceiling, str(entry.get("reason", ""))


def phase_date_ok(value):
    if not isinstance(value, str) or not PHASE_DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


STATUS_RANK = {"done": 0, "current": 1, "planned": 2}


def lifecycle_order_problems(phases):
    """Phases run planned -> current -> done, in declared order: every done phase
    comes before the current one and every planned phase after it. A done phase
    therefore cannot be quietly switched back on without also moving others."""
    problems, last, last_key = [], -1, None
    for key, entry in phases.items():
        rank = STATUS_RANK.get(entry.get("status")) if isinstance(entry, dict) else None
        if rank is None:
            continue
        if rank < last:
            problems.append(
                f"phase {key}: status {entry['status']} comes after {last_key}; phases are done, then current, then planned, in declared order"
            )
        else:
            last, last_key = rank, key
    return problems


def finished_phase_problems(phases, current):
    """A finished phase may not be above the live ceiling.

    One file cannot show that a done phase is genuine, and a large ceiling
    planted in one (followed by a "lowers" on the next phase) could be switched
    on later. So a done phase above the current phase's ceiling is refused
    outright: finished phases are a ratchet, and the ceiling cannot be lowered
    below a phase that already ran. The cost is that a ceiling lower than any
    finished phase is not supported in this file (see docs/cost.md)."""
    entry = phases.get(current) if isinstance(phases, dict) else None
    live = phase_number(entry.get("ceiling")) if isinstance(entry, dict) else None
    if live is None:
        return []
    problems = []
    for key, value in phases.items():
        if not isinstance(value, dict) or value.get("status") != "done":
            continue
        done = phase_number(value.get("ceiling"))
        if done is not None and done > live:
            problems.append(
                f"phase {key}: done at ${done:.2f}, above the current ceiling ${live:.2f}; "
                "a finished phase may not exceed the live ceiling"
            )
    return problems


def transition_problems(old, new):
    """Lifecycle of each phase between two versions of approved.json.

    planned -> current -> done only. A done phase never changes again, so a
    large ceiling planted in one cannot be switched on; a phase that is current
    stops being current only when another becomes current (the new file has
    exactly one). A new phase arrives planned or current. Not used by the
    plain gate (it sees one file); cost_raise runs it, and the gate runs it with
    --base-approved FILE when CI can supply the merge base's copy."""
    old_phases, new_phases = old.get("phases"), new.get("phases")
    if not isinstance(old_phases, dict) or not isinstance(new_phases, dict):
        return []
    problems = []
    for key, was in old_phases.items():
        if not isinstance(was, dict):
            continue
        now = new_phases.get(key)
        if now is None:
            problems.append(
                f"phase {key} ({was.get('status')}) may not be removed; change it instead"
            )
            continue
        if was.get("status") == "done" and now != was:
            problems.append(f"phase {key} is done and may not change")
            continue
        before, after = was.get("status"), (now or {}).get("status")
        if before != after and (before, after) not in (
            ("planned", "current"),
            ("current", "done"),
        ):
            problems.append(
                f"phase {key}: status may not go from {before} to {after} (planned, then current, then done)"
            )
    for key, now in new_phases.items():
        if (
            key not in old_phases
            and isinstance(now, dict)
            and now.get("status") == "done"
        ):
            problems.append(f"phase {key} is new and may not start as done")
    return problems


def effective_change(old, new):
    """(old, new) of (phase id, ceiling), or None where one cannot be read."""
    out = []
    for doc in (old, new):
        try:
            out.append(current_ceiling(doc)[:2])
        except (ValueError, KeyError, TypeError):
            out.append(None)
    return tuple(out)


def phase_problems(approved):
    """Shape of the per-phase ceilings (docs/cost.md, "Ceilings per phase")."""
    hard_max = None
    if "hard_max" in approved:
        hard_max = phase_number(approved["hard_max"])
        if hard_max is None:
            return [
                f"hard_max {approved['hard_max']!r} must be a finite number, zero or more"
            ]
    if "phases" in approved and "hard_max" not in approved:
        hard_problem = [
            "hard_max is required when phases exist (the absolute limit no phase may pass)"
        ]
    else:
        hard_problem = []
    if "phases" not in approved:
        legacy = phase_number(approved.get("ceiling"))
        if legacy is not None and hard_max is not None and legacy > hard_max:
            return [f"ceiling ${legacy:.2f} is above hard_max ${hard_max:.2f}"]
        return []
    problems = list(hard_problem)
    if hard_max is not None:
        why = approved.get("hard_max_reason")
        if not isinstance(why, str) or not why.strip():
            problems.append("hard_max_reason must say why hard_max is that number")
    if "ceiling" in approved:
        problems.append(
            "approved.json has phases and a top-level ceiling; remove the top-level ceiling, the current phase decides"
        )
    phases = approved["phases"]
    if not isinstance(phases, dict) or not phases:
        return problems + ["phases must be a non-empty map of phase id to an object"]
    current = approved.get("current_phase")
    if not isinstance(current, str) or current not in phases:
        problems.append(f"current_phase {current} is not in phases")
    now = [
        k
        for k, v in phases.items()
        if isinstance(v, dict) and v.get("status") == "current"
    ]
    if len(now) != 1:
        found = f" ({', '.join(now)})" if now else ""
        problems.append(
            f"exactly one phase must have status current, found {len(now)}{found}"
        )
    elif now[0] != current:
        problems.append(
            f"phase {now[0]} has status current but current_phase is {current}"
        )
    problems += lifecycle_order_problems(phases)
    previous = None
    for index, (key, entry) in enumerate(phases.items()):
        if not isinstance(key, str) or not PHASE_ID_RE.match(key):
            problems.append(
                f"phase id {key!r} must be lowercase letters, digits and dashes"
            )
            previous = None
            continue
        if not isinstance(entry, dict):
            problems.append(f"phase {key}: must be an object")
            previous = None
            continue
        ceiling = phase_number(entry.get("ceiling"))
        if ceiling is None:
            problems.append(
                f"phase {key}: ceiling {entry.get('ceiling')!r} must be a finite number, zero or more"
            )
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"phase {key}: reason must be a non-empty string")
        if not phase_date_ok(entry.get("decided")):
            problems.append(
                f"phase {key}: decided {entry.get('decided')!r} must be an ISO date (YYYY-MM-DD)"
            )
        if entry.get("status") not in PHASE_STATUSES:
            problems.append(
                f"phase {key}: status {entry.get('status')!r} must be one of {', '.join(PHASE_STATUSES)}"
            )
        lowers = entry.get("lowers", False)
        if not isinstance(lowers, bool):
            problems.append(f"phase {key}: lowers must be true or false")
            lowers = False
        if ceiling is not None and hard_max is not None and ceiling > hard_max:
            problems.append(
                f"phase {key}: ceiling ${ceiling:.2f} is above hard_max ${hard_max:.2f}"
            )
        if lowers and previous is None and index == 0:
            problems.append(
                f"phase {key}: marked lowers but it is the first phase, nothing comes before it"
            )
        if ceiling is not None and previous is not None:
            prev_key, prev_ceiling = previous
            decreased = ceiling < prev_ceiling
            if decreased and not lowers:
                problems.append(
                    f"phase {key}: ceiling ${ceiling:.2f} is below {prev_key} ${prev_ceiling:.2f}; "
                    'a lower ceiling needs "lowers": true and a reason'
                )
            if lowers and not decreased:
                problems.append(
                    f"phase {key}: marked lowers but the ceiling does not go below {prev_key} ${prev_ceiling:.2f}"
                )
        previous = (key, ceiling) if ceiling is not None else None
    problems += finished_phase_problems(phases, current)
    return problems


def approval_problems(approved, totals, parts=None):
    """Per-provider approval and the current phase's ceiling. `parts` is site_totals()."""
    problems = phase_problems(approved)
    parts = parts or {}
    try:
        ceiling = current_ceiling(approved)[1]
    except ValueError:
        return problems or ["approved.json has no usable ceiling"]
    providers = approved["providers"]
    for provider in totals:
        if provider not in providers:
            problems.append(
                f"provider {provider} has a manifest but no entry in approved.json"
            )
    active = 0.0
    for provider, entry in providers.items():
        cap = money(entry["approved_monthly_total"], f"{provider} approved_monthly_total")
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
        problems += sites_problems(provider, entry, cap, parts.get(provider, {}))
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


def fmt_effective(pair):
    return "unreadable" if pair is None else f"phase {pair[0]} ${pair[1]:.2f}"


def gate_problems(root, approved, plan=None, stack=None):
    """Every problem the gate finds and the per-provider totals. Raises
    ValueError/KeyError/TypeError/IndexError/AttributeError on unreadable input."""
    parts = site_totals(root)
    totals = {p: round(sum(v.values()), 2) for p, v in parts.items()}
    problems = [
        f"resource type not on the free list, not approved, or outside its allowed file: {item}"
        for item in uncosted_sources(
            root, allowed_sources(approved), set(approved["providers"])
        )
    ]
    problems += structure_problems(root)
    problems += approval_problems(approved, totals, parts)
    if plan:
        if not stack:
            problems.append("--plan needs --stack")
        else:
            problems += plan_problems(plan, stack, root)
    return problems, totals


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
    parser.add_argument(
        "--base-approved",
        help="the merge base's docs/stages/approved.json; checks the phase lifecycle (planned, current, done) and reports a change of the effective ceiling",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        approved = load_json(root / "docs/stages/approved.json")
        base = load_json(args.base_approved) if args.base_approved else None
    except (OSError, ValueError) as err:
        print(f"cost-check: unreadable approved.json: {err}", file=sys.stderr)
        return 1
    try:
        problems, totals = gate_problems(root, approved, args.plan, args.stack)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError) as err:
        print(
            f"cost-check: unreadable manifest, price table, approval or plan input: {err!r}",
            file=sys.stderr,
        )
        return 1
    if base is not None:
        problems += transition_problems(base, approved)
        was, now = effective_change(base, approved)
        if was != now:
            print(
                f"cost-check: EFFECTIVE CEILING CHANGED: {fmt_effective(was)} -> {fmt_effective(now)}"
            )
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
    try:
        phase_id, phase_ceiling, phase_reason = current_ceiling(approved)
        print(
            f"cost-check: phase {phase_id} ceiling ${phase_ceiling:.2f} (reason: {phase_reason})"
        )
    except ValueError:
        pass  # approval_problems() already reported why
    for problem in problems:
        print(f"cost-check: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
