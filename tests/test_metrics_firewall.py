"""The metrics ports on the connector firewall (issue #99) are tag-sourced only.

tofu test proves the rendered rule lists. These tests read the sources, so an
address-sourced inbound rule cannot appear without a test failing here, and they
keep stack 10 and stack 20 agreeing about the metrics ports. Each check is run
on a broken fixture too, so a check that stops biting fails.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIREWALL = ROOT / "modules/firewall/main.tf"
ACCESS = ROOT / "stacks/10-access"
TELEMETRY = ROOT / "stacks/20-telemetry"


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


def inbound_blocks(text: str) -> list[str]:
    """Every inbound_rule body (static or dynamic content) in the text."""
    out = []
    for m in re.finditer(r'(?m)^\s*(?:dynamic\s+")?inbound_rule"?\s*\{', text):
        out.append(block(text[m.start() :], "inbound_rule"))
    return out


def address_sources(text: str) -> list[str]:
    """Inbound rule bodies that name an address source."""
    return [b for b in inbound_blocks(text) if "source_addresses" in b]


def test_the_firewall_module_has_inbound_rules_and_none_names_an_address():
    text = code(FIREWALL.read_text())
    assert len(inbound_blocks(text)) == 2  # own-tag rules and other-tag rules
    assert address_sources(text) == []
    assert "source_addresses" not in text
    assert "source_load_balancer_uids" not in text


def test_the_guard_bites_on_an_address_sourced_inbound_rule():
    bad = """
resource "digitalocean_firewall" "this" {
  inbound_rule {
    protocol         = "tcp"
    port_range       = "9100"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
}
"""
    assert len(inbound_blocks(bad)) == 1
    assert len(address_sources(bad)) == 1
    dynamic_bad = bad.replace("inbound_rule {", 'dynamic "inbound_rule" {\n content {', 1)
    assert address_sources(dynamic_bad + "}")


def test_stack_10_feeds_the_firewall_only_tag_sourced_metrics_rules():
    text = code((ACCESS / "main.tf").read_text())
    firewall = block(text, 'module "connector_firewall"')
    assert re.search(r"(?m)^\s*inbound_from_other_tags\s*=\s*local\.metrics_inbound_rules\s*$", firewall)
    rules = text[text.index("metrics_inbound_rules =") :]
    rules = rules[: rules.index("\n  ]\n") + 4]
    # protocol is fixed to tcp, the tag is the one variable, and no address key.
    assert 'protocol   = "tcp"' in rules
    assert "tag        = var.metrics_source_tag" in rules
    assert "source_addresses" not in rules and "0.0.0.0" not in rules
    assert 'var.metrics_source_tag == "" ? []' in rules
    assert address_sources(text) == []


def test_stack_10_hard_codes_no_metrics_port():
    text = code((ACCESS / "main.tf").read_text())
    assert "9100" not in text and "9999" not in text


def variable_default_port(variables_tf: str, name: str) -> int:
    body = block(variables_tf, f'variable "{name}"')
    found = re.search(r"optional\(number,\s*(\d+)\)", body) or re.search(
        r"(?m)^\s*default\s*=\s*(\d+)\s*$", body
    )
    assert found, f"no numeric default for {name}"
    return int(found.group(1))


def test_stack_10_and_stack_20_agree_on_the_node_exporter_port_default():
    access = code((ACCESS / "variables.tf").read_text())
    telemetry = code((TELEMETRY / "variables.tf").read_text())
    assert variable_default_port(access, "node_exporter") == 9100
    assert variable_default_port(telemetry, "node_exporter_port") == 9100


def test_both_stacks_keep_9100_for_the_node_exporter():
    # Stack 10 refuses 9100 as the connector metrics port (its variable
    # validation); stack 20 must refuse it too, whatever node_exporter_port is.
    access = code((ACCESS / "variables.tf").read_text())
    assert "connector_telemetry.metrics_port != 9100" in access
    telemetry = code((TELEMETRY / "main.tf").read_text())
    assert "var.metrics_port_connector != 9100" in telemetry


def test_the_tag_variable_refuses_addresses():
    access = code((ACCESS / "variables.tf").read_text())
    body = block(access, 'variable "metrics_source_tag"')
    pattern = re.search(r'regex\("([^"]+)"', body).group(1)
    ok = re.compile(pattern)
    assert ok.match("cah-telemetry-tor1")
    for refused in ("192.0.2.10", "0.0.0.0/0", "::/0", "a b", "tag/x"):
        assert not ok.match(refused), refused
