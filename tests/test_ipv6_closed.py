"""IPv6 stays closed: a static, offline scan of every .tf file in modules/ and stacks/.

"Zero inbound" is only true if IPv6 is closed too. A DigitalOcean droplet made
with `ipv6 = true` gets a public IPv6 address, and an inbound source of `::/0`
would open it. Nothing else fails if a later change flips either, so this does.

The scan reads resource blocks (not prose), so the word "ipv6" or a `::/0` in a
comment or a description never trips it. It reuses the block-skipping helpers
of scripts/hcl_variables.py and fails closed: a file that cannot be read, or a
block that cannot be parsed, is a failure that names its path.

Add a rule by adding one line to RULES (or FORBIDDEN_RESOURCES).

Scope: the rules guard INBOUND sources. The DigitalOcean firewall's outbound
rules list `::/0` as a destination on purpose (egress on ports 443, 80, 53,
123 only); that is not exposure and is not flagged.
Limit: a `::/0` that reaches an inbound rule only through a `locals` value is
not followed. The inbound attribute itself must be a literal, so a reference
there fails as unprovable instead.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hcl_variables import (  # sys.path is set up just above
    NAME_RE,
    OPEN,
    HclError,
    _read_balanced,
    _skip_heredoc,
    _skip_string,
    _skip_ws_comments,
)

IPV6_LITERAL = re.compile(r"^[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*(/[0-9]{1,3})?$")


# ---------------------------------------------------------------- reading ----


def strip_comments(expr: str) -> str:
    """The expression without #, // and /* */ comments; strings are kept whole."""
    out: list[str] = []
    i = 0
    while i < len(expr):
        if expr[i] == '"':
            end = _skip_string(expr, i, lenient=True)
            out.append(expr[i:end])
            i = end
            continue
        j = _skip_ws_comments(expr, i, newlines=False)
        if j != i and expr[i] in "#/":
            i = j
            continue
        out.append(expr[i])
        i += 1
    return "".join(out).strip()


def _expression_end(text: str, i: int) -> int:
    while i < len(text) and text[i] != "\n":
        c = text[i]
        if c == '"':
            i = _skip_string(text, i, lenient=True)
        elif c in OPEN:
            i = _read_balanced(text, i, lenient=True)
        elif c == "#" or text.startswith("//", i) or text.startswith("/*", i):
            i = _skip_ws_comments(text, i, newlines=False)
        elif text.startswith("<<", i):
            i = _skip_heredoc(text, i)
        else:
            i += 1
    return i


@dataclass
class Block:
    kind: str
    labels: list[str]
    attrs: list[tuple[str, str]]
    blocks: list[Block]


def parse_body(text: str, where: str) -> tuple[list[tuple[str, str]], list[Block]]:
    attrs: list[tuple[str, str]] = []
    blocks: list[Block] = []
    i = 0
    while True:
        i = _skip_ws_comments(text, i)
        if i >= len(text):
            return attrs, blocks
        m = NAME_RE.match(text, i)
        if not m:
            raise HclError(f"unexpected text {text[i : i + 30]!r} in {where}")
        name = m.group(0)
        i = _skip_ws_comments(text, m.end(), newlines=False)
        if text.startswith("=", i) and not text.startswith("==", i):
            start = _skip_ws_comments(text, i + 1, newlines=False)
            end = _expression_end(text, start)
            expr = strip_comments(text[start:end])
            if not expr:
                raise HclError(f"{name} has an empty value in {where}")
            attrs.append((name, expr))
            i = end
            continue
        labels: list[str] = []
        while text.startswith('"', i):
            end = _skip_string(text, i, lenient=True)
            labels.append(json.loads(text[i:end]))
            i = _skip_ws_comments(text, end, newlines=False)
        if not text.startswith("{", i):
            raise HclError(f"cannot read {name!r} in {where}")
        end = _read_balanced(text, i, lenient=True)
        inner_attrs, inner_blocks = parse_body(text[i + 1 : end - 1], f"{where}/{name}")
        blocks.append(Block(name, labels, inner_attrs, inner_blocks))
        i = end


def parse_file(text: str, where: str) -> list[Block]:
    """Top-level blocks of one .tf file (a top-level attribute is an HclError)."""
    attrs, blocks = parse_body(text, where)
    if attrs:
        raise HclError(f"top-level attribute {attrs[0][0]} is not understood")
    return blocks


def walk(block: Block, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], str, str]]:
    """(enclosing block names, attribute, expression) at every depth.

    `dynamic "x"` counts as a block named x, and its `content` is transparent.
    """
    for name, expr in block.attrs:
        yield path, name, expr
    for sub in block.blocks:
        if sub.kind == "dynamic" and sub.labels:
            attrs = list(sub.attrs)
            blocks: list[Block] = []
            for inner in sub.blocks:
                if inner.kind == "content":
                    attrs += inner.attrs
                    blocks += inner.blocks
                else:
                    blocks.append(inner)
            sub = Block(sub.labels[0], [], attrs, blocks)
        yield from walk(sub, path + (sub.kind,))


def attr_in(block: Block, name: str) -> str | None:
    return next((e for n, e in block.attrs if n == name), None)


# ------------------------------------------------------------------ rules ----


def is_off(expr: str) -> bool:
    return expr in ("false", "0", "null", "[]")


def is_false(expr: str) -> bool:
    return expr == "false"


def is_null(expr: str) -> bool:
    return expr == "null"


# References that are provably IPv4-only because the variable's own validation
# rejects any ':' and 0.0.0.0/0. Empty today (the edge firewall has no variable
# source; iperf3 stays closed until its own stack). Adding a name here is a
# reviewed decision, and the variable's validation needs a test beside it.
IPV4_ONLY_REFERENCES: frozenset[str] = frozenset()


def literal_without_ipv6(expr: str) -> bool:
    """A literal list of strings, none of them an IPv6 range. A reference is unprovable,
    except the few in IPV4_ONLY_REFERENCES."""
    if expr in IPV4_ONLY_REFERENCES:
        return True
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', expr)
    rest = re.sub(r'"(?:[^"\\]|\\.)*"', "", expr)
    return not re.search(r"[A-Za-z_]", rest) and not any(IPV6_LITERAL.match(s) for s in strings)


@dataclass(frozen=True)
class Rule:
    name: str
    types: tuple[str, ...]  # resource types the rule applies to
    attr: str  # attribute that is checked
    ok: Callable[[str], bool]  # accepts the (comment-free) expression text
    required: bool = False  # absent counts as a failure
    within: str | None = None  # only inside a nested block of this name
    when: Callable[[Block], bool] | None = None  # only for resources where this holds


def _is_ingress_type(block: Block) -> bool:
    return attr_in(block, "type") == '"ingress"'


_MACHINES = ("aws_instance", "aws_launch_template", "aws_network_interface")

# One line per rule: for this resource type, this attribute must satisfy ok.
RULES: tuple[Rule, ...] = (
    # 1. a droplet must state ipv6 = false
    Rule("droplet-ipv6-false", ("digitalocean_droplet",), "ipv6", is_false, required=True),
    # 2. no IPv6 source on an inbound rule
    Rule("do-firewall-inbound-source", ("digitalocean_firewall",), "source_addresses", literal_without_ipv6, within="inbound_rule"),
    Rule("aws-sg-ingress-source", ("aws_security_group",), "ipv6_cidr_blocks", is_off, within="ingress"),
    Rule("aws-ingress-rule-source", ("aws_vpc_security_group_ingress_rule",), "cidr_ipv6", is_null),
    Rule("aws-sg-rule-ingress-source", ("aws_security_group_rule",), "ipv6_cidr_blocks", is_off, when=_is_ingress_type),
    # 3. no IPv6 plumbing in the VPC or a subnet
    Rule("vpc-generated-ipv6", ("aws_vpc",), "assign_generated_ipv6_cidr_block", is_off),
    Rule("vpc-ipv6-cidr", ("aws_vpc", "aws_subnet"), "ipv6_cidr_block", is_null),
    Rule("vpc-ipv6-netmask", ("aws_vpc", "aws_subnet"), "ipv6_netmask_length", is_off),
    Rule("subnet-generated-ipv6", ("aws_subnet",), "assign_ipv6_address_on_creation", is_off),
    Rule("subnet-ipv6-native", ("aws_subnet",), "ipv6_native", is_off),
    # 4. no IPv6 address on a machine
    Rule("machine-ipv6-count", _MACHINES, "ipv6_address_count", is_off),
    Rule("machine-ipv6-addresses", _MACHINES, "ipv6_addresses", is_off),
)

# Resource types that must not exist at all (IPv6 plumbing).
FORBIDDEN_RESOURCES = frozenset(
    {
        "aws_vpc_ipv6_cidr_block_association",
        "aws_egress_only_internet_gateway",
    }
)


def check_block(block: Block, where: str) -> list[str]:
    if block.kind != "resource":
        return []
    if len(block.labels) != 2:
        return [f"{where}: resource block without type and name labels"]
    rtype, rname = block.labels
    out: list[str] = []
    if rtype in FORBIDDEN_RESOURCES:
        out.append(f"{where}: {rtype}.{rname}: IPv6 plumbing must not exist in this repository (forbidden-resource)")
    for rule in RULES:
        if rtype not in rule.types or (rule.when and not rule.when(block)):
            continue
        hits = [e for p, n, e in walk(block) if n == rule.attr and (rule.within is None or rule.within in p)]
        if not hits and rule.required:
            out.append(f"{where}: {rtype}.{rname}: {rule.attr} is not stated, it must be set explicitly (breaks {rule.name})")
        for expr in hits:
            if not rule.ok(expr):
                out.append(f"{where}: {rtype}.{rname}: {rule.attr} = {expr} (breaks {rule.name}; IPv6 must stay closed)")
    return out


def scan_text(text: str, where: str) -> list[str]:
    try:
        blocks = parse_file(text, where)
    except HclError as exc:
        return [f"{where}: cannot parse (fail closed): {exc}"]
    problems: list[str] = []
    for block in blocks:
        problems.extend(check_block(block, where))
    return problems


def tf_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for top in ("modules", "stacks"):
        found.extend(p for p in sorted((root / top).rglob("*.tf")) if ".terraform" not in p.parts)
    return found


def scan_tree(root: Path) -> list[str]:
    problems: list[str] = []
    for tf in tf_files(root):
        rel = tf.relative_to(root).as_posix()
        try:
            text = tf.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(f"{rel}: cannot read (fail closed): {exc}")
            continue
        problems.extend(scan_text(text, rel))
    return problems


def count_resources(root: Path, rtype: str) -> int:
    n = 0
    for tf in tf_files(root):
        for b in parse_file(tf.read_text(encoding="utf-8"), tf.name):
            n += b.kind == "resource" and b.labels[:1] == [rtype]
    return n


# ------------------------------------------------------------- real tree ----


def test_the_repository_keeps_ipv6_closed():
    assert tf_files(ROOT), "no .tf files under modules/ or stacks/: the scan would prove nothing"
    problems = scan_tree(ROOT)
    assert not problems, "IPv6 exposure:\n" + "\n".join(problems)


def test_the_scan_sees_the_resources_it_guards():
    # Guard against a silent no-op: the real tree has these resources.
    for rtype in ("digitalocean_droplet", "digitalocean_firewall", "aws_vpc", "aws_instance", "aws_security_group"):
        assert count_resources(ROOT, rtype) >= 1, f"no {rtype} found: the scan lost its target"


# -------------------------------------------------------------- fixtures ----

BAD = {
    "droplet-ipv6-true": 'resource "digitalocean_droplet" "x" {\n  ipv6 = true\n}\n',
    "droplet-ipv6-absent": 'resource "digitalocean_droplet" "x" {\n  name = "a"\n}\n',
    "droplet-ipv6-reference": 'resource "digitalocean_droplet" "x" {\n  ipv6 = var.v6\n}\n',
    "do-firewall-ipv6-any": 'resource "digitalocean_firewall" "x" {\n  inbound_rule {\n    protocol = "tcp"\n    source_addresses = ["::/0"]\n  }\n}\n',
    "do-firewall-ipv6-cidr-dynamic": 'resource "digitalocean_firewall" "x" {\n  dynamic "inbound_rule" {\n    for_each = []\n    content {\n      source_addresses = ["2001:db8::/32"]\n    }\n  }\n}\n',
    "do-firewall-other-reference-in-dynamic": 'resource "digitalocean_firewall" "x" {\n  dynamic "inbound_rule" {\n    for_each = []\n    content {\n      source_addresses = var.iperf3_allowed_sources_v6\n    }\n  }\n}\n',
    "do-firewall-source-reference": 'resource "digitalocean_firewall" "x" {\n  inbound_rule {\n    source_addresses = var.sources\n  }\n}\n',
    "aws-sg-inline-ingress": 'resource "aws_security_group" "x" {\n  ingress {\n    ipv6_cidr_blocks = ["::/0"]\n  }\n}\n',
    "aws-ingress-rule": 'resource "aws_vpc_security_group_ingress_rule" "x" {\n  cidr_ipv6 = "::/0"\n}\n',
    "aws-sg-rule-ingress": 'resource "aws_security_group_rule" "x" {\n  type = "ingress"\n  ipv6_cidr_blocks = ["::/0"]\n}\n',
    "vpc-generated": 'resource "aws_vpc" "x" {\n  assign_generated_ipv6_cidr_block = true\n}\n',
    "vpc-cidr": 'resource "aws_vpc" "x" {\n  ipv6_cidr_block = "2001:db8::/56"\n}\n',
    "vpc-netmask": 'resource "aws_vpc" "x" {\n  ipv6_netmask_length = 56\n}\n',
    "subnet-cidr": 'resource "aws_subnet" "x" {\n  ipv6_cidr_block = "2001:db8::/64"\n}\n',
    "subnet-on-creation": 'resource "aws_subnet" "x" {\n  assign_ipv6_address_on_creation = true\n}\n',
    "subnet-native": 'resource "aws_subnet" "x" {\n  ipv6_native = true\n}\n',
    "association": 'resource "aws_vpc_ipv6_cidr_block_association" "x" {\n}\n',
    "egress-only-gateway": 'resource "aws_egress_only_internet_gateway" "x" {\n  vpc_id = "v"\n}\n',
    "instance-count": 'resource "aws_instance" "x" {\n  ipv6_address_count = 1\n}\n',
    "instance-addresses": 'resource "aws_instance" "x" {\n  ipv6_addresses = ["2001:db8::1"]\n}\n',
    "template-nested-count": 'resource "aws_launch_template" "x" {\n  network_interfaces {\n    ipv6_address_count = 2\n  }\n}\n',
}

GOOD = {
    "droplet": 'resource "digitalocean_droplet" "x" {\n  ipv6 = false\n}\n',
    "firewall-tags-only": 'resource "digitalocean_firewall" "x" {\n  inbound_rule {\n    source_tags = ["a"]\n  }\n  outbound_rule {\n    destination_addresses = ["0.0.0.0/0", "::/0"]\n  }\n}\n',
    "aws-sg": 'resource "aws_security_group" "x" {\n  description = "no ::/0 and no ipv6 here"\n  ingress {\n    ipv6_cidr_blocks = []\n  }\n}\n',
    "aws-ingress-rule": 'resource "aws_vpc_security_group_ingress_rule" "x" {\n  cidr_ipv4 = "10.0.0.0/8"\n}\n',
    "aws-sg-rule-egress": 'resource "aws_security_group_rule" "x" {\n  type = "egress"\n  ipv6_cidr_blocks = ["::/0"]\n}\n',
    "vpc": 'resource "aws_vpc" "x" {\n  assign_generated_ipv6_cidr_block = false\n}\n',
    "subnet": 'resource "aws_subnet" "x" {\n  ipv6_native = false\n  ipv6_cidr_block = null\n}\n',
    "instance": 'resource "aws_instance" "x" {\n  ipv6_address_count = 0\n}\n',
    "templated-strings": 'resource "digitalocean_droplet" "x" {\n  name = "${var.layer}-a"\n  ipv6 = false\n}\n',
}

PROSE_ONLY = (
    "# an ipv6 = true droplet and a ::/0 source would be bad\n"
    'variable "v" {\n  type = string\n  default = "ipv6 ::/0"\n  description = "never ::/0 or ipv6 = true"\n}\n'
    '/* block comment: ipv6 = true, source_addresses = ["::/0"] */\n'
    'resource "digitalocean_droplet" "x" {\n'
    "  # ipv6 = true is wrong\n"
    "  ipv6 = false // ipv6 = true elsewhere\n"
    '  name = "about ::/0 and ipv6 = true"\n'
    "}\n"
    'resource "digitalocean_firewall" "x" {\n'
    '  description = "source_addresses = [::/0]"\n'
    "  inbound_rule {\n"
    '    # source_addresses = ["::/0"]\n'
    '    source_tags = ["t"]\n'
    "  }\n"
    "}\n"
)


def _write(root: Path, top: str, name: str, text: str) -> None:
    d = root / top / name
    d.mkdir(parents=True)
    (d / "main.tf").write_text(text)


def test_each_hostile_fixture_fails(tmp_path):
    for name, text in BAD.items():
        root = tmp_path / name
        _write(root, "modules", "m", text)
        problems = scan_tree(root)
        assert problems, f"{name}: a violating fixture passed the IPv6 check"
        assert all(p.startswith("modules/m/main.tf") for p in problems), problems


def test_each_compliant_fixture_passes(tmp_path):
    for name, text in GOOD.items():
        root = tmp_path / name
        _write(root, "stacks", "s", text)
        assert scan_tree(root) == [], name


def test_ipv6_only_in_comments_descriptions_and_defaults_passes(tmp_path):
    _write(tmp_path, "modules", "m", PROSE_ONLY)
    assert scan_tree(tmp_path) == []


def test_every_rule_has_a_hostile_fixture():
    # A new rule cannot be added without a fixture that proves it bites.
    hit: set[str] = set()
    for text in BAD.values():
        for problem in scan_text(text, "f.tf"):
            hit.update(re.findall(r"breaks ([a-z0-9-]+)", problem))
    missing = {r.name for r in RULES} - hit
    assert not missing, f"rules without a failing fixture: {sorted(missing)}"
    forbidden = [p for t in BAD.values() for p in scan_text(t, "f.tf") if "forbidden-resource" in p]
    assert len(forbidden) >= len(FORBIDDEN_RESOURCES)


def test_an_unreadable_or_unparsable_file_fails_closed(tmp_path):
    (tmp_path / "modules" / "m").mkdir(parents=True)
    bad = tmp_path / "modules" / "m" / "broken.tf"
    bad.write_text('resource "digitalocean_droplet" "x" {\n  ipv6 = false\n')
    problems = scan_tree(tmp_path)
    assert problems and "modules/m/broken.tf" in problems[0] and "fail closed" in problems[0]
    bad.write_bytes(b"\xff\xfe resource")
    problems = scan_tree(tmp_path)
    assert problems and "modules/m/broken.tf" in problems[0] and "cannot read" in problems[0]
