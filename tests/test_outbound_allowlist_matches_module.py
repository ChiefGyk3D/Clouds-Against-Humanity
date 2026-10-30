"""The shipped outbound_allowlist matches what the firewall module renders.

The plan policy (.spacelift/policies/plan.rego) allows a world-open outbound
rule only through an exact entry. Each shipped entry exists because the module
renders that rule today (issue #253), so a change to the module defaults or to
a stack's extra_outbound_rules that is not mirrored in the policy would either
be denied at apply time or leave a stale exception behind. This reads the
sources and compares them in both directions. Each check also runs on a broken
fixture, so a check that stops biting fails here.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / ".spacelift/policies/plan.rego"
MODULE = ROOT / "modules/firewall/main.tf"
ACCESS = ROOT / "stacks/10-access/main.tf"

RULE = re.compile(r'protocol\s*=\s*"(\w+)"\s*,\s*port_range\s*=\s*"([^"]+)"')


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", text)


def tf_rules(text: str, header: str) -> set[tuple[str, str]]:
    """(protocol, port_range) pairs in the bracketed list after `header`."""
    start = text.index(header)
    open_at = text.index("[", start)
    depth = 0
    for i in range(open_at, len(text)):
        depth += {"[": 1, "]": -1}.get(text[i], 0)
        if depth == 0:
            return set(RULE.findall(text[open_at : i + 1]))
    raise AssertionError(f"unbalanced list after {header!r}")


def policy_entries(text: str) -> dict[str, set[tuple[str, str]]]:
    """Stack id -> (protocol, port) pairs from outbound_allowlist entries."""
    body = strip_comments(text)
    start = body.index("outbound_allowlist := {")
    end = body.index("address_groups :=", start)
    section = body[start:end]
    result: dict[str, set[tuple[str, str]]] = {}
    for stack in re.finditer(r'"(cah-[\w-]+)":\s*\{', section):
        rest = section[stack.end() :]
        nxt = re.search(r'\n\t"cah-[\w-]+":\s*\{', rest)
        chunk = rest[: nxt.start()] if nxt else rest
        pairs: set[tuple[str, str]] = set()
        for entry in re.finditer(r'"protocol":\s*"(\w+)",\s*"ports":\s*\[([^\]]*)\]', chunk):
            for port in re.findall(r'"([^"]+)"', entry.group(2)):
                pairs.add((entry.group(1), port))
        result[stack.group(1)] = pairs
    return result


def expected(module: str, access: str) -> dict[str, set[tuple[str, str]]]:
    defaults = tf_rules(strip_comments(module), "default_outbound = [")
    extra = tf_rules(strip_comments(access), "extra_outbound_rules = [")
    return {"cah-00-foundation": defaults, "cah-10-access": defaults | extra}


def test_shipped_entries_match_what_the_module_renders():
    got = policy_entries(POLICY.read_text())
    want = expected(MODULE.read_text(), ACCESS.read_text())
    assert want["cah-00-foundation"], "found no default outbound rules"
    assert want["cah-10-access"] > want["cah-00-foundation"], "found no extra rules"
    assert got == want


def test_check_notices_a_rule_missing_from_the_policy():
    module = MODULE.read_text().replace('{ protocol = "udp", port_range = "123" },', "")
    assert policy_entries(POLICY.read_text()) != expected(module, ACCESS.read_text())


def test_check_notices_a_stale_policy_entry():
    stale = POLICY.read_text().replace('"ports": ["53", "123"]', '"ports": ["53", "123", "8443"]', 1)
    assert policy_entries(stale) != expected(MODULE.read_text(), ACCESS.read_text())


def test_check_notices_a_new_extra_rule_in_the_stack():
    access = ACCESS.read_text().replace(
        'port_range = "30000-31000" },', 'port_range = "30000-31000" },\n    { protocol = "tcp", port_range = "8443" },', 1
    )
    assert policy_entries(POLICY.read_text()) != expected(MODULE.read_text(), access)
