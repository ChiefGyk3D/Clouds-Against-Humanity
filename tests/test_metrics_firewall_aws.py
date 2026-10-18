"""The AWS metrics ports (issue #99, AWS half) are admitted from a security group only.

tofu test proves the rendered rule lists. These tests read the sources, so an
ingress rule that takes an address (cidr_blocks, ipv6_cidr_blocks, cidr_ipv4,
cidr_ipv6, a prefix list) from the metrics inputs cannot appear without a test
failing here. Each check also runs on a broken fixture, so a check that stops
biting fails.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIREWALL = ROOT / "modules/aws/firewall"
ACCESS = ROOT / "stacks/aws/10-access"

INGRESS = "aws_vpc_security_group_ingress_rule"
ADDRESS_ATTRS = re.compile(
    r"(?m)^\s*(cidr_blocks|ipv6_cidr_blocks|cidr_ipv4|cidr_ipv6|prefix_list_id)\s*="
)


def code(text: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", text)


def block(text: str, header: str) -> str:
    """The brace-balanced body that follows `header` (first occurrence)."""
    start = text.index(header)
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1 : i]
    raise AssertionError("unbalanced braces")


def ingress_blocks(text: str) -> dict[str, str]:
    """Every ingress rule resource body in the text, by resource name."""
    out = {}
    for m in re.finditer(rf'(?m)^\s*resource\s+"{INGRESS}"\s+"([A-Za-z0-9_]+)"\s*\{{', text):
        out[m.group(1)] = block(text[m.start() :], "resource")
    return out


def address_sourced(blocks: dict[str, str]) -> list[str]:
    """Names of ingress rules that set any address-type source attribute."""
    return [name for name, body in blocks.items() if ADDRESS_ATTRS.search(body)]


def test_the_firewall_module_has_ingress_rules_and_none_names_an_address():
    text = code((FIREWALL / "main.tf").read_text())
    blocks = ingress_blocks(text)
    assert sorted(blocks) == ["member", "other_group"]
    assert address_sourced(blocks) == []
    for name, body in blocks.items():
        assert re.search(r"(?m)^\s*referenced_security_group_id\s*=", body), name
    # The module as a whole has no way to say "ingress from an address".
    assert not re.search(r"cidr_blocks|ipv6_cidr_blocks|prefix_list", text)
    # The only cidr in the module is the any-address EGRESS rule.
    assert len(re.findall(r"cidr_ipv4", text)) == 1


def test_the_guard_bites_on_an_address_sourced_ingress_rule():
    bad = f"""
resource "{INGRESS}" "metrics" {{
  security_group_id = aws_security_group.this.id
  cidr_ipv4         = var.metrics_source_cidr
  ip_protocol       = "tcp"
}}
resource "{INGRESS}" "ipv6" {{
  security_group_id = aws_security_group.this.id
  ipv6_cidr_blocks  = ["::/0"]
}}
resource "{INGRESS}" "ok" {{
  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = var.source
}}
"""
    blocks = ingress_blocks(bad)
    assert sorted(blocks) == ["ipv6", "metrics", "ok"]
    assert address_sourced(blocks) == ["metrics", "ipv6"]
    for attr in ("cidr_ipv6", "cidr_blocks", "prefix_list_id"):
        assert address_sourced(ingress_blocks(bad.replace("cidr_ipv4", attr)))


def test_the_other_group_variable_has_no_address_field():
    text = code((FIREWALL / "variables.tf").read_text())
    body = block(text, 'variable "inbound_from_other_groups"')
    fields = re.findall(r"(?m)^\s*([a-z_]+)\s*=\s*string\s*$", body)
    assert fields == ["protocol", "port_range", "security_group_id"]
    type_part = body[: body.index("default")]
    assert not re.search(r"cidr|prefix_list|address", type_part)
    pattern = re.search(r'regex\("(\^sg-[^"]+)"', body).group(1)
    ok = re.compile(pattern)
    assert ok.match("sg-0abc1230abc123450")
    for refused in ("192.0.2.10", "0.0.0.0/0", "::/0", "", "sg-", "sg-xyz", "pl-0abc1230abc123450"):
        assert not ok.match(refused), refused


def test_stack_feeds_the_firewall_only_security_group_sourced_metrics_rules():
    text = code((ACCESS / "main.tf").read_text())
    firewall = block(text, 'module "connector_firewall"')
    assert re.search(
        r"(?m)^\s*inbound_from_other_groups\s*=\s*local\.metrics_inbound_rules\s*$", firewall
    )
    # No other input of the firewall module can carry the metrics ports.
    assert "metrics" not in re.sub(r"inbound_from_other_groups\s*=\s*local\.metrics_inbound_rules", "", firewall)
    start = text.index("metrics_inbound_rules =")
    rules = text[start : text.index("\n  ]\n", start) + 5]
    assert 'protocol          = "tcp"' in rules
    assert "security_group_id = var.metrics_source_security_group_id" in rules
    assert not re.search(r"cidr|0\.0\.0\.0|::/0|prefix_list", rules)
    assert 'var.metrics_source_security_group_id == "" ? []' in rules
    # The stack declares no rule resource of its own.
    assert ingress_blocks(text) == {}
    assert not ADDRESS_ATTRS.search(text)


def test_stack_hard_codes_no_metrics_port():
    text = code((ACCESS / "main.tf").read_text())
    assert "9100" not in text and "9999" not in text


def test_the_stack_variable_refuses_addresses():
    text = code((ACCESS / "variables.tf").read_text())
    body = block(text, 'variable "metrics_source_security_group_id"')
    pattern = re.search(r'regex\("(\^sg-[^"]+)"', body).group(1)
    ok = re.compile(pattern)
    assert ok.match("sg-0abc1230abc123450")
    for refused in ("192.0.2.10", "0.0.0.0/0", "::/0", "a b", "sg-0abc/24", "10.0.0.0/8"):
        assert not ok.match(refused), refused
    # The default is empty, which means no rule.
    assert re.search(r'(?m)^\s*default\s*=\s*""\s*$', body)


def test_no_aws_log_shipping_input_yet():
    # Log shipping on AWS waits for its own change (the DigitalOcean one is a
    # separate open PR); this one must not smuggle it in.
    for path in (ACCESS / "variables.tf", ACCESS / "main.tf"):
        assert "log_shipping" not in path.read_text()
    assert "log_shipping" not in (ROOT / "modules/aws/twingate-connector/variables.tf").read_text()
