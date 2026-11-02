"""The destroy allowlist in plan.rego is pinned, and cannot be left filled.

Issue #450 added two addresses to destroy_allowlist for the cah-10-access
teardown and then emptied it again (the shipped state). plan_test.rego pins the allowlist by test name, in both directions:

  - allowlist filled: plan_test.rego has test_destroy_allowlist_is_exactly_teardown_list
    (matching the shipped entries) and no test_destroy_allowlist_is_empty;
  - allowlist empty: plan_test.rego has test_destroy_allowlist_is_empty
    (asserting count(spacelift.destroy_allowlist) == 0) and no teardown-list test.

The follow-up pull request deletes the teardown-list test, adds the empty test
and sets destroy_allowlist := {}; any other combination fails here. No Rego
test may use the todo_ prefix: `opa test` exits 2 when any test is skipped, and
the shared CI job cannot be told otherwise. OPA is not needed here: this reads
both files as text. Each check also runs on a broken fixture, so a check that
stops biting fails here.
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

EXACT = "test_destroy_allowlist_is_exactly_teardown_list"
EMPTY = "test_destroy_allowlist_is_empty"


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


def has_test(tests: str, name: str) -> bool:
    """True when `name` is defined as a live rule."""
    return re.search(rf"(?m)^{name}\s+if\b", tests) is not None


def body_of(tests: str, name: str) -> str:
    match = re.search(rf"(?ms)^{name}\s+if\s*\{{(.*?)^\}}", tests)
    return strip_comments(match.group(1)) if match else ""


def skipped_tests(tests: str) -> list[str]:
    return re.findall(r"(?m)^(todo_\w+)", tests)


def problems(policy: str, tests: str) -> list[str]:
    found = []
    allowlist = parse_allowlist(policy)
    exact_on, empty_on = has_test(tests, EXACT), has_test(tests, EMPTY)
    if skipped_tests(tests):
        found.append(f"skipped (todo_) tests make opa test exit 2: {skipped_tests(tests)}")
    if allowlist:
        if not exact_on:
            found.append(f"destroy_allowlist is filled, so {EXACT} must exist")
        if empty_on:
            found.append(f"destroy_allowlist is filled, so {EMPTY} must not exist")
        if allowlist != TEARDOWN:
            found.append(f"destroy_allowlist is {allowlist}, expected exactly {TEARDOWN}")
    else:
        if not empty_on:
            found.append(f"destroy_allowlist is empty, so {EMPTY} must exist")
        elif "count(spacelift.destroy_allowlist) == 0" not in body_of(tests, EMPTY):
            found.append(f"{EMPTY} must assert count(spacelift.destroy_allowlist) == 0")
        if exact_on:
            found.append(f"destroy_allowlist is empty, so {EXACT} must not exist")
    return found


# Fixtures: a minimal policy and test file in each state.
POLICY_FILLED = 'destroy_allowlist := {"cah-10-access": [\n\t"twingate_remote_network.this",\n\t"module.connector_firewall.digitalocean_firewall.this",\n]}\n'
POLICY_EMPTY = "destroy_allowlist := {}\n"
TESTS_EXACT = f"{EXACT} if {{\n\ttrue\n}}\n"
TESTS_EMPTY = f"{EMPTY} if {{\n\tcount(spacelift.destroy_allowlist) == 0\n}}\n"


def test_shipped_allowlist_and_tests_agree():
    policy, tests = POLICY.read_text(), POLICY_TESTS.read_text()
    assert parse_allowlist(policy), "no destroy_allowlist entries were parsed"
    assert problems(policy, tests) == []


def test_shipped_policy_tests_have_no_skipped_test():
    assert skipped_tests(POLICY_TESTS.read_text()) == []


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
    assert problems(POLICY_FILLED, TESTS_EXACT) == []


def test_emptied_allowlist_with_empty_test_is_fine():
    assert problems(POLICY_EMPTY, TESTS_EMPTY) == []


def test_guard_bites_when_allowlist_is_left_filled_after_the_flip():
    assert problems(POLICY_FILLED, TESTS_EMPTY)


def test_guard_bites_when_allowlist_is_emptied_without_the_flip():
    assert problems(POLICY_EMPTY, TESTS_EXACT)


def test_guard_bites_when_both_tests_exist():
    assert problems(POLICY_FILLED, TESTS_EXACT + TESTS_EMPTY)
    assert problems(POLICY_EMPTY, TESTS_EXACT + TESTS_EMPTY)


def test_guard_bites_when_neither_test_exists():
    assert problems(POLICY_FILLED, "")
    assert problems(POLICY_EMPTY, "")


def test_guard_bites_when_the_empty_test_does_not_assert_empty():
    weak = f"{EMPTY} if {{\n\ttrue\n}}\n"
    assert problems(POLICY_EMPTY, weak)


def test_guard_bites_on_an_extra_or_missing_address():
    extra = POLICY_FILLED.replace("]}", '\t"module.vpc.digitalocean_vpc.this",\n]}')
    assert problems(extra, TESTS_EXACT)
    missing = 'destroy_allowlist := {"cah-10-access": ["twingate_remote_network.this"]}\n'
    assert problems(missing, TESTS_EXACT)


def test_guard_bites_on_an_address_under_another_stack():
    moved = POLICY_FILLED.replace("cah-10-access", "cah-00-foundation")
    assert problems(moved, TESTS_EXACT)


def test_guard_bites_on_a_todo_prefixed_test():
    skipped = TESTS_EXACT + f"todo_{EMPTY} if {{\n\ttrue\n}}\n"
    assert skipped_tests(skipped) == [f"todo_{EMPTY}"]
    assert problems(POLICY_FILLED, skipped)
