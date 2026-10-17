"""Stack 20 (telemetry) is a skeleton that creates nothing until a flag is true.

The tofu tests prove the plans. These tests read the sources, so a new resource
or a resource without a flag gate fails here even if nobody wrote a tofu test
for it, and they keep the secret and cost wiring honest.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STACK = ROOT / "stacks" / "20-telemetry"


def code(path: Path) -> str:
    return re.sub(r"(?m)(#|//).*$", "", path.read_text())


def resource_blocks() -> dict[str, str]:
    """{type.name: body} for every resource block in the stack's .tf files."""
    found = {}
    for path in sorted(STACK.glob("*.tf")):
        text = code(path)
        for m in re.finditer(r'(?m)^resource "([^"]+)" "([^"]+)" \{\n', text):
            end = text.index("\n}\n", m.end())
            found[f"{m.group(1)}.{m.group(2)}"] = text[m.end() : end]
    return found


def test_the_stack_has_exactly_the_expected_resources():
    # A new resource must be added here on purpose, with its flag gate.
    assert sorted(resource_blocks()) == [
        "twingate_resource.logging",
        "twingate_resource.scrape",
        "twingate_service_account.logging",
        "twingate_service_account.scrape",
    ]


def test_every_resource_is_gated_on_a_flag():
    for name, body in resource_blocks().items():
        gate = "logging" if name.endswith(".logging") else "metrics"
        assert re.search(
            rf"(?m)^\s*(count|for_each)\s*=.*(var\.{gate}_enabled|local\.(logging_names|scrape_pairs))",
            body,
        ), f"{name} is not gated on {gate}_enabled"
    text = code(STACK / "main.tf")
    assert "var.logging_enabled ? toset(" in text
    assert "var.metrics_enabled ? nonsensitive(" in text


def test_only_the_twingate_provider_is_used():
    versions = code(STACK / "versions.tf")
    assert re.findall(r'(?m)^provider "([^"]+)"', versions) == ["twingate"]
    for path in STACK.glob("*.tf"):
        assert not re.search(r"digitalocean_|aws_", code(path)), path.name


def test_no_service_key_is_created():
    # Keys are issued out of band, one per host (design section 2.8).
    for path in STACK.glob("*.tf"):
        assert "service_account_key" not in code(path), path.name


def test_private_variables_are_sensitive_and_flags_default_false():
    text = (STACK / "variables.tf").read_text()
    for name in (
        "logging_servers",
        "connector_private_ips",
        "home_remote_network_id",
        "cloud_remote_network_id",
    ):
        body = re.search(rf'variable "{name}" \{{\n(.*?)\n\}}\n', text, re.DOTALL).group(1)
        assert re.search(r"(?m)^\s*sensitive\s*=\s*true", body), name
    for name in ("logging_enabled", "metrics_enabled"):
        body = re.search(rf'variable "{name}" \{{\n(.*?)\n\}}\n', text, re.DOTALL).group(1)
        assert re.search(r"(?m)^\s*default\s*=\s*false", body), name
    body = re.search(r'variable "metrics_port_connector" \{\n(.*?)\n\}\n', text, re.DOTALL).group(1)
    assert re.search(r"(?m)^\s*default\s*=\s*null", body), "no default port for the unverified bind port"


def test_the_scrape_targets_output_is_sensitive_and_the_logging_list_is_not_output():
    outputs = code(STACK / "outputs.tf")
    scrape = re.search(r'output "scrape_targets" \{\n(.*?)\n\}\n', outputs, re.DOTALL).group(1)
    assert re.search(r"(?m)^\s*sensitive\s*=\s*true", scrape)
    assert "logging_servers" not in outputs
    assert "remote_network_id" not in outputs


def test_the_cost_manifest_is_empty():
    manifest = json.loads((STACK / "cost.json").read_text())
    assert manifest["resources"] == []
