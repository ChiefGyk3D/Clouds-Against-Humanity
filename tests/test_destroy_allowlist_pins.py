"""The destroy allowlist in plan.rego is pinned, and cannot be left filled.

Issue #450 adds two addresses to destroy_allowlist for the cah-10-access
teardown. plan_test.rego carries a pair of tests, and exactly one is enabled:

  test_destroy_allowlist_is_exactly_teardown_list   (while the teardown runs)
  test_destroy_allowlist_is_empty                   (after it; off by default)

The disabled one is spelled with a todo_ prefix, which makes OPA skip it. OPA
is not needed here: this reads both files as text. It fails when both tests are
on or both are off, when the enabled test does not match the shipped
allowlist, and when the allowlist is not the exact teardown list while the
"exactly" test is on. The follow-up pull request flips the pair and empties the
allowlist; any other combination fails. Each check also runs on a broken
fixture, so a check that stops biting fails here.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / ".spacelift/policies/plan.rego"
POLICY_TESTS = ROOT / ".spacelift/policies/plan_test.rego"

TEARDOWN = {
    "cah-10-access": [
        "twingate_remote_network.this",
        "module.connector_firewall.digitalocean_firewall.this",
    ]
}

EXACT = "destroy_allowlist_is_exactly_teardown_list"
EMPTY = "destroy_allowlist_is_empty"


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)#.*$", "", text)


def parse_allowlist(policy: str) -> dict[str, list[str]]:
    """Stack id -> addresses from the destroy_allowlist assignment."""
    body = strip_comments(policy)
    start = body.index("destroy_allowlist := {")
    open_at = body.index("{", start)
    depth = 0
    for i in range(open_at, len(body)):
        depth += {"{": 1, "}": -1}.get(body[i], 0)
        if depth == 0:
            literal = body[open_at : i + 1]
            break
    else:
        raise AssertionError("unbalanced destroy_allowlist")
    result: dict[str, list[str]] = {}
    for stack in re.finditer(r'"([^"]+)":\s*\[(.*?)\]', literal, re.DOTALL):
        result[stack.group(1)] = re.findall(r'"([^"]+)"', stack.group(2))
    return result


def enabled(tests: str, name: str) -> bool:
    """True when `test_<name>` is a live rule; `todo_test_<name>` is skipped."""
    return re.search(rf"(?m)^test_{name}\s+if\b", tests) is not None


def disabled(tests: str, name: str) -> bool:
    return re.search(rf"(?m)^todo_test_{name}\s+if\b", tests) is not None


def problems(policy: str, tests: str) -> list[str]:
    found = []
    allowlist = parse_allowlist(policy)
    exact_on, empty_on = enabled(tests, EXACT), enabled(tests, EMPTY)
    if exact_on == empty_on:
        found.append(f"exactly one of {EXACT} and {EMPTY} must be enabled (exact={exact_on}, empty={empty_on})")
    if exact_on and not disabled(tests, EMPTY):
        found.append(f"todo_test_{EMPTY} must exist while {EXACT} is on")
    if empty_on and not disabled(tests, EXACT):
        found.append(f"todo_test_{EXACT} must exist while {EMPTY} is on")
    if exact_on and allowlist != TEARDOWN:
        found.append(f"destroy_allowlist is {allowlist}, expected exactly {TEARDOWN}")
    if empty_on and allowlist:
        found.append(f"destroy_allowlist must be empty after the teardown, found {allowlist}")
    return found


# Fixtures: a minimal policy and test file in each state.
POLICY_FILLED = 'destroy_allowlist := {"cah-10-access": [\n\t"twingate_remote_network.this",\n\t"module.connector_firewall.digitalocean_firewall.this",\n]}\n'
POLICY_EMPTY = "destroy_allowlist := {}\n"
TESTS_EXACT_ON = f"test_{EXACT} if {{\n\ttrue\n}}\n\ntodo_test_{EMPTY} if {{\n\ttrue\n}}\n"
TESTS_EMPTY_ON = f"todo_test_{EXACT} if {{\n\ttrue\n}}\n\ntest_{EMPTY} if {{\n\ttrue\n}}\n"


def test_shipped_allowlist_and_tests_agree():
    policy, tests = POLICY.read_text(), POLICY_TESTS.read_text()
    assert parse_allowlist(policy), "no destroy_allowlist entries were parsed"
    assert problems(policy, tests) == []


def test_allowlist_names_each_address_once():
    allowlist = parse_allowlist(POLICY.read_text())
    for addresses in allowlist.values():
        assert len(addresses) == len(set(addresses))


def test_the_policy_test_file_names_the_same_addresses():
    tests = POLICY_TESTS.read_text()
    for addresses in TEARDOWN.values():
        for address in addresses:
            assert f'"{address}"' in tests


def test_filled_allowlist_with_exact_test_is_fine():
    assert problems(POLICY_FILLED, TESTS_EXACT_ON) == []


def test_emptied_allowlist_with_empty_test_is_fine():
    assert problems(POLICY_EMPTY, TESTS_EMPTY_ON) == []


def test_guard_bites_when_allowlist_is_left_filled_after_the_flip():
    assert problems(POLICY_FILLED, TESTS_EMPTY_ON)


def test_guard_bites_when_allowlist_is_emptied_without_the_flip():
    assert problems(POLICY_EMPTY, TESTS_EXACT_ON)


def test_guard_bites_when_both_tests_are_on():
    both = TESTS_EXACT_ON + f"\ntest_{EMPTY} if {{\n\ttrue\n}}\n"
    assert problems(POLICY_FILLED, both)


def test_guard_bites_when_both_tests_are_off():
    neither = f"todo_test_{EXACT} if {{\n\ttrue\n}}\n\ntodo_test_{EMPTY} if {{\n\ttrue\n}}\n"
    assert problems(POLICY_EMPTY, neither)


def test_guard_bites_on_an_extra_or_missing_address():
    extra = POLICY_FILLED.replace("]}", '\t"module.vpc.digitalocean_vpc.this",\n]}')
    assert problems(extra, TESTS_EXACT_ON)
    missing = 'destroy_allowlist := {"cah-10-access": ["twingate_remote_network.this"]}\n'
    assert problems(missing, TESTS_EXACT_ON)


def test_guard_bites_on_an_address_under_another_stack():
    moved = POLICY_FILLED.replace("cah-10-access", "cah-00-foundation")
    assert problems(moved, TESTS_EXACT_ON)
