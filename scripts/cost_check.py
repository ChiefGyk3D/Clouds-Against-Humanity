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
- a connector module's size is not a plain `local.<name>.size` reference (its
  instance_type likewise), a costed resource uses count or for_each, a resource
  type's provider prefix is neither a known cloud nor in SAFE_PREFIXES, or a
  label holds a backslash;
- a module source is not local or goes through a dot-directory, a stack
  directory is misnamed, a dot-directory exists under stacks/ or modules/, or a
  *.tf.json / *.tofu.json file exists (*.tf and *.tofu are both read);
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
import json
import math
import os
import posixpath
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
# Skipped at the repository top level only: tool state and agent worktrees.
TOP_SKIP_DIRS = frozenset({".git", ".venv", ".claude"})
# Directories whose contents the gate must be able to read in full.
GUARDED_TOP = frozenset({"stacks", "modules"})
HCL_SUFFIXES = (".tf", ".tofu")
JSON_SUFFIXES = (".tf.json", ".tofu.json")
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
# A value that is only known after apply comes from another resource in the plan,
# and that resource is itself an unpriced type the plan check refuses.
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
    for rel in walk_repo(root)[0]:
        if (
            rel.startswith("stacks/")
            and rel.endswith("/cost.json")
            and not is_hidden(rel)
        ):
            yield str(Path(rel).parent.as_posix()), Path(root, rel)


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


def plan_instance_cost(addr, after, unknown, prices):
    extras = unpriced_instance_attrs(after)
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
LABEL = r'"(?:[^"\\\n]|\\.)*"|[^\s"{}]+'
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
            if guarded and Path(dirpath, name).is_symlink():
                problems.append(
                    f"{where}: symlinked directory under {child.parts[0]}/ is refused"
                )
                continue
            if guarded and name.startswith("."):
                problems.append(
                    f"{where}: hidden directory under {child.parts[0]}/ is refused; "
                    "the gate does not scan it, so nothing may live there"
                )
            elif child.parts[0] == "stacks" and not stack_name_ok(child.parts):
                problems.append(
                    f"{where}: stack directory name must be NN-name (digits, a dash, then a name) "
                    f"or one of {', '.join(sorted(STACK_PROVIDER_DIRS))} exactly, lowercase"
                )
            keep.append(name)
        dirnames[:] = keep
        files += [(rel_dir / f).as_posix() for f in sorted(filenames)]
    return sorted(files), problems


def stack_name_ok(parts):
    """Naming rule for stacks/<x> and stacks/<provider>/<x>."""
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
            yield rel, strip_comments(Path(root, rel).read_text()), None
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


def module_source_problem(rel, block):
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
    return source, None


def module_problems(root):
    """Check module blocks. Returns (problems, {stack dir: connector module count})."""
    problems, connectors = [], {}
    for rel, block in file_blocks(root):
        if block.kind != "module" or block.problem:
            continue
        name = block.labels[0]
        source, problem = module_source_problem(rel, block)
        if problem:
            problems.append(problem)
            continue
        if source.rstrip("/").endswith(CONNECTOR_SOURCE_SUFFIX):
            stack = str(Path(rel).parent.as_posix())
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
    if not manifests:
        problems.append(
            "no stacks/**/cost.json manifest found; at least one is required"
        )
    for stack in stack_dirs(root):
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
    problems += block_problems(root)
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
