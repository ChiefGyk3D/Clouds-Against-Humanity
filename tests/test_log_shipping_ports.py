"""Stack 10's log_shipping ports agree with stack 20's logging resources.

The Wazuh agent talks to the manager on 1514 and enrolls on 1515. Stack 10 sets
those two ports on the agent (log_shipping.manager_port and .enroll_port); stack
20 creates one Twingate resource per port from `logging_servers`, with the purpose
`wazuh-agent` and `wazuh-enroll`. The two stacks are separate, so nothing links
the values in OpenTofu: this test is the link. A Twingate resource for another
port would leave the agent unable to connect (or, worse, an unlisted port open),
so a disagreement fails here.

The check reads defaults from the variable declarations and the ports from the
committed example and the stack 20 tests' fixtures, and it is exercised on broken
input so a check that stops biting fails too.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import hcl_variables

STACK10 = ROOT / "stacks/10-access"
STACK20 = ROOT / "stacks/20-telemetry"
MODULES = (
    ROOT / "modules/twingate-bootstrap",
    ROOT / "modules/twingate-connector",
)
WAZUH_PURPOSE = {"manager_port": "wazuh-agent", "enroll_port": "wazuh-enroll"}


def declared_defaults(variables_tf: str) -> dict[str, int]:
    """The optional() defaults of log_shipping's two port attributes."""
    block = re.search(r'(?s)variable "log_shipping" \{(.*?)\n\}\n', variables_tf)
    assert block, "no log_shipping variable"
    found = {}
    for name in WAZUH_PURPOSE:
        m = re.search(rf"{name}\s*=\s*optional\(number,\s*(\d+)\)", block.group(1))
        assert m, f"log_shipping.{name} has no numeric default"
        found[name] = int(m.group(1))
    return found


def logging_ports(servers: list[dict]) -> dict[str, set[int]]:
    """purpose -> ports of the tcp logging_servers entries."""
    out: dict[str, set[int]] = {}
    for s in servers:
        if s["protocol"] == "tcp":
            out.setdefault(s["purpose"], set()).add(int(s["port"]))
    return out


def disagreements(defaults: dict[str, int], servers: list[dict]) -> list[str]:
    ports = logging_ports(servers)
    problems = []
    for attr, purpose in WAZUH_PURPOSE.items():
        got = ports.get(purpose, set())
        if got != {defaults[attr]}:
            problems.append(
                f"stack 10 log_shipping.{attr} is {defaults[attr]} but stack 20 has "
                f"{purpose} on {sorted(got) or 'no port'}"
            )
    return problems


def example_servers() -> list[dict]:
    text = (STACK20 / "terraform.tfvars.example").read_text(encoding="utf-8")
    assignments = hcl_variables.parse_assignments(text, "stack 20 example")
    return assignments["logging_servers"]


def test_stack_10_defaults_are_1514_and_1515():
    defaults = declared_defaults((STACK10 / "variables.tf").read_text(encoding="utf-8"))
    assert defaults == {"manager_port": 1514, "enroll_port": 1515}


def test_the_modules_use_the_same_defaults_as_the_stack():
    expected = declared_defaults((STACK10 / "variables.tf").read_text(encoding="utf-8"))
    for module in MODULES:
        got = declared_defaults((module / "variables.tf").read_text(encoding="utf-8"))
        assert got == expected, module.name


def test_stack_20_example_logging_resources_agree_with_stack_10():
    defaults = declared_defaults((STACK10 / "variables.tf").read_text(encoding="utf-8"))
    servers = example_servers()
    assert servers, "the stack 20 example has no logging_servers"
    assert disagreements(defaults, servers) == []


def test_stack_20_tests_use_the_same_wazuh_ports():
    # Every wazuh-agent / wazuh-enroll fixture in the stack 20 tests uses the port
    # stack 10 sets, except the validation tests that exercise a bad value.
    defaults = declared_defaults((STACK10 / "variables.tf").read_text(encoding="utf-8"))
    seen = {"wazuh-agent": set(), "wazuh-enroll": set()}
    for path in sorted((STACK20 / "tests").glob("*.tftest.hcl")):
        for m in re.finditer(
            r'port\s*=\s*(\d+),\s*protocol\s*=\s*"tcp",\s*purpose\s*=\s*"(wazuh-agent|wazuh-enroll)"',
            path.read_text(encoding="utf-8"),
        ):
            if 1 <= int(m.group(1)) <= 65535:  # a bad-port validation fixture is not a Wazuh port
                seen[m.group(2)].add(int(m.group(1)))
    assert seen["wazuh-agent"] == {defaults["manager_port"]}
    assert seen["wazuh-enroll"] == {defaults["enroll_port"]}


def test_stack_20_builds_each_logging_resource_from_the_server_port():
    # One resource per logging_servers element, its port taken from that element:
    # the port is not hard-coded in the resource.
    main = (STACK20 / "main.tf").read_text(encoding="utf-8")
    block = re.search(r'(?s)resource "twingate_resource" "logging" \{(.*?)\n\}\n', main)
    assert block
    assert "local.logging_by_name[each.key].port" in block.group(1)
    assert not re.search(r'ports\s*=\s*\["\d+"\]', block.group(1))


def test_stack_20_accepts_the_two_wazuh_purposes():
    text = (STACK20 / "variables.tf").read_text(encoding="utf-8")
    assert '"wazuh-agent"' in text and '"wazuh-enroll"' in text


# --- the check bites ---------------------------------------------------------


GOOD = {"manager_port": 1514, "enroll_port": 1515}
SERVERS = [
    {"name": "a", "address": "192.0.2.10", "port": 1514, "protocol": "tcp", "purpose": "wazuh-agent"},
    {"name": "b", "address": "192.0.2.10", "port": 1515, "protocol": "tcp", "purpose": "wazuh-enroll"},
]


def test_negative_agreeing_input_passes():
    assert disagreements(GOOD, SERVERS) == []


@pytest.mark.parametrize("changed", ["manager_port", "enroll_port"])
def test_negative_a_changed_stack_10_default_is_caught(changed):
    defaults = dict(GOOD, **{changed: 1600})
    assert len(disagreements(defaults, SERVERS)) == 1


def test_negative_a_changed_stack_20_port_is_caught():
    servers = [dict(SERVERS[0], port=1600), SERVERS[1]]
    assert len(disagreements(GOOD, servers)) == 1


def test_negative_a_missing_or_udp_logging_entry_is_caught():
    assert len(disagreements(GOOD, SERVERS[:1])) == 1
    udp = [SERVERS[0], dict(SERVERS[1], protocol="udp")]
    assert len(disagreements(GOOD, udp)) == 1


def test_negative_a_second_port_for_the_same_purpose_is_caught():
    extra = SERVERS + [dict(SERVERS[0], name="c", port=1999)]
    assert len(disagreements(GOOD, extra)) == 1


def test_negative_the_reader_refuses_a_missing_default():
    with pytest.raises(AssertionError):
        declared_defaults('variable "log_shipping" {\n  type = object({})\n}\n')
