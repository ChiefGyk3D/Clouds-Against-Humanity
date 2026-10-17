"""terraform.tfvars.example for each live stack (stage 2 design, section 2.6).

The example is committed documentation, so it must be complete, readable,
valid and free of anything that looks like a real value:

- every `variable` of the stack appears in the example and nothing else does
  (a new variable without an example fails here);
- every assignment has a comment above it;
- every value has the variable's declared type and the file parses with the
  fail-closed reader (a shape it does not understand is an error);
- the example is planned with mocked providers by a generated tofu test, which
  runs every validation against it (the test file must be current);
- no value looks like a secret or a real identifier: the identifier check's
  patterns, addresses only in documentation or private ranges, no host names
  except example.*, required placeholders that say "example", no long
  token-like strings, no key material.

The reader and the checks are exercised on broken input, so a check that stops
biting fails here.
"""

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_example_tests
import hcl_variables
import identifier_check

STACKS = ("stacks/00-foundation", "stacks/10-access", "stacks/20-telemetry")
EXAMPLE = "terraform.tfvars.example"

DOC_NETS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
]
PRIVATE_NETS = [
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
]
IPV4_RE = re.compile(r"(?<![0-9.])([0-9]{1,3}(?:\.[0-9]{1,3}){3})(?![0-9])")
HOST_RE = re.compile(
    r"\b((?:[a-z0-9-]+\.)+(?:com|net|org|io|dev|cloud|local|lan|internal|home|corp))\b",
    re.IGNORECASE,
)
HOST_OK = re.compile(r"(^|\.)example\.(com|net|org)$", re.IGNORECASE)
LONG_TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
# The prefixes are joined at run time so this file holds no token-shaped text.
TOKEN_PREFIXES = re.compile(
    "("
    + "|".join(
        ["dop" + "_v1_", "doo" + "_v1_", "tf" + "p_", "gh" + "p_", "gh" + "o_",
         "github" + "_pat_", "xox[bap]-", "AK" + "IA", "AS" + "IA", "sk-[A-Za-z0-9]",
         "-----BE" + "GIN"]
    )
    + ")"
)
# Values that are stack wiring or a documented default, not a placeholder for a
# private or secret value, so they need not say "example".
NEED_NOT_SAY_EXAMPLE = {
    "region",
    "vpc_ip_range",
    "project_name",
    "baseline_tag",
    "connector_telemetry",
    "connector_telemetry_instances",
    "connector_telemetry_previous",
    "host_firewall",
    "host_firewall_instances",
    "host_firewall_ssh_sources",
    "metadata_lock",
    "metadata_lock_instances",
    "reboot_times",
    "reserved_ranges",
    "resource_key",
    "site_name",
    "timezone",
    # Stack 20: public configuration, or private values whose example is a
    # documentation-range address (the address check above still applies).
    "logging_servers",
    "scrape_allowlist",
    "wazuh_agent_group",
}


def text_of(stack: str) -> str:
    return (ROOT / stack / EXAMPLE).read_text(encoding="utf-8")


def declared(stack: str) -> dict:
    return hcl_variables.variables_in_dir(ROOT / stack)


def type_ok(type_text: str, value) -> bool:
    if type_text == "string":
        return isinstance(value, str)
    if type_text == "bool":
        return isinstance(value, bool)
    if type_text == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_text == "list(string)":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if type_text == "map(string)":
        return isinstance(value, dict) and all(isinstance(v, str) for v in value.values())
    if type_text.startswith("list(object("):
        return isinstance(value, list) and all(isinstance(v, dict) for v in value)
    if type_text.startswith("object({status_updates_enabled=optional(bool),log_level="):
        # connector_telemetry: an object whose every field is optional.
        allowed = {
            "status_updates_enabled": bool,
            "log_level": (int, float),
            "connection_logs": bool,
            "metrics_port": (int, float),
            "labels": dict,
        }
        return isinstance(value, dict) and all(
            k in allowed and isinstance(v, allowed[k]) for k, v in value.items()
        )
    raise AssertionError(f"the example check does not know the type {type_text}")


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from strings_in(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings_in(v)


def coverage_problems(text: str, variables: dict) -> list[str]:
    """Disagreements between an example's text and the stack's variables."""
    problems: list[str] = []
    try:
        values = hcl_variables.parse_assignments(text, EXAMPLE)
    except hcl_variables.HclError as exc:
        return [f"cannot read the example ({exc})"]
    for name in sorted(set(variables) - set(values)):
        problems.append(f"variable {name} has no entry in the example")
    for name in sorted(set(values) - set(variables)):
        problems.append(f"the example sets {name}, which is not a variable of the stack")
    for name, value in values.items():
        var = variables.get(name)
        if var is not None and not type_ok(var.type, value):
            problems.append(f"{name}: the value does not have the type {var.type}")
    lines = text.splitlines()
    for name in values:
        index = next(
            (i for i, line in enumerate(lines) if re.match(rf"{re.escape(name)}\s*=", line)),
            None,
        )
        if index is None or index == 0 or not lines[index - 1].lstrip().startswith("#"):
            problems.append(f"{name}: no comment on the line above it")
    return problems


def value_problems(text: str) -> list[str]:
    """Anything in the example that looks like a secret or a real identifier."""
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind in identifier_check.find_kinds(line):
            problems.append(f"line {number}: {kind}")
        for m in IPV4_RE.finditer(line):
            try:
                ip = ipaddress.ip_address(m.group(1))
            except ValueError:
                continue
            if not any(ip in n for n in DOC_NETS + PRIVATE_NETS):
                problems.append(f"line {number}: an address outside the documentation and private ranges")
        for m in HOST_RE.finditer(line):
            host = m.group(1)
            if not HOST_OK.search(host) and not host.endswith((".tf", ".json", ".md", ".yml")):
                problems.append(f"line {number}: a host name that is not example.com/net/org")
        if TOKEN_PREFIXES.search(line):
            problems.append(f"line {number}: looks like a token or key material")
    try:
        values = hcl_variables.parse_assignments(text, EXAMPLE)
    except hcl_variables.HclError as exc:
        return problems + [f"cannot read the example ({exc})"]
    for name, value in values.items():
        for s in strings_in(value):
            for m in LONG_TOKEN.finditer(s):
                if "example" not in m.group(0).lower():
                    problems.append(f"{name}: a long token-like string that does not say 'example'")
        needs_example = (
            name not in NEED_NOT_SAY_EXAMPLE
            and isinstance(value, (str, list, dict))
            and value not in ("", [], {})
        )
        if needs_example and not any("example" in s.lower() for s in strings_in(value)):
            problems.append(f"{name}: a placeholder for a private value must say 'example'")
    return problems


@pytest.mark.parametrize("stack", STACKS)
def test_the_example_exists_and_covers_every_variable(stack):
    assert coverage_problems(text_of(stack), declared(stack)) == []


@pytest.mark.parametrize("stack", STACKS)
def test_the_example_holds_nothing_that_looks_real(stack):
    assert value_problems(text_of(stack)) == []


@pytest.mark.parametrize("stack", STACKS)
def test_the_example_has_a_real_number_of_entries(stack):
    # Guards against passing because nothing was read.
    assert len(hcl_variables.parse_assignments(text_of(stack))) >= 5


@pytest.mark.parametrize("stack", STACKS)
def test_the_generated_example_test_is_current(stack):
    path = ROOT / stack / gen_example_tests.TEST
    assert path.read_text(encoding="utf-8") == gen_example_tests.render(stack, ROOT)
    assert (
        subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts" / "gen_example_tests.py"), "--check"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


@pytest.mark.parametrize("stack", STACKS)
def test_the_example_is_committable_and_a_real_tfvars_is_not(stack):
    def ignored(name: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", f"{stack}/{name}"],
            check=False,
        )
        assert result.returncode in (0, 1)
        return result.returncode == 0

    assert not ignored("terraform.tfvars.example")
    assert ignored("terraform.tfvars")
    assert ignored("prod.auto.tfvars.json")


# --- the checks bite ----------------------------------------------------------

GOOD = '# one\na = "x"\n# two\nb = ["y"]\n'
VARS = {
    "a": hcl_variables.Variable(name="a", type="string"),
    "b": hcl_variables.Variable(name="b", type="list(string)"),
}


def test_the_coverage_check_accepts_a_good_example():
    assert coverage_problems(GOOD, VARS) == []


def test_the_coverage_check_bites_on_a_missing_entry():
    problems = coverage_problems('# one\na = "x"\n', VARS)
    assert any("variable b has no entry" in p for p in problems), problems


def test_the_coverage_check_bites_on_an_unknown_entry():
    problems = coverage_problems(GOOD + '# c\nc = 1\n', VARS)
    assert any("c, which is not a variable" in p for p in problems), problems


def test_the_coverage_check_bites_on_a_wrong_type():
    problems = coverage_problems('# one\na = 1\n# two\nb = ["y"]\n', VARS)
    assert any("a: the value does not have the type string" in p for p in problems)


def test_the_coverage_check_bites_on_a_missing_comment():
    problems = coverage_problems('a = "x"\n# two\nb = ["y"]\n', VARS)
    assert any("a: no comment" in p for p in problems), problems
    problems = coverage_problems('# one\na = "x"\n\nb = ["y"]\n', VARS)
    assert any("b: no comment" in p for p in problems), problems


@pytest.mark.parametrize(
    "text",
    [
        '# c\na = "x"\n# c\na = "y"\n',  # assigned twice
        '# c\na = var.x\n',  # not a literal
        '# c\na = "${x}"\n',  # template
        '# c\na = <<EOT\nx\nEOT\n',  # heredoc
        '# c\nresource "x" "y" {\n}\n',  # a block
        '# c\na = "unterminated\n',
        '# c\na = [1, 2\n',
        '# c\na = {x = 1 y = 2}\n',
    ],
)
def test_the_reader_fails_closed_on_shapes_it_does_not_understand(text):
    assert coverage_problems(text, VARS)[0].startswith("cannot read the example")


@pytest.mark.parametrize(
    "line,needle",
    [
        ('a = "8.8.8.8"', "outside the documentation"),
        ('a = "203.0.114.5"', "outside the documentation"),
        ('a = "db.corp-real.com"', "host name"),
        ('a = "account_id = ' + "2109" + '87654321"', "AWS account id"),
        ('a = "AK' + "IA" + "Q7ZXCV" + 'BNMASDFGHJ"', "AWS access key id"),
        ('a = "dop' + '_v1_abcdef"', "token or key material"),
        ('a = "-----BE' + 'GIN OPENSSH PRIVATE KEY-----"', "token or key material"),
        ('a = "tf' + 'p_abcdef"', "token or key material"),
    ],
)
def test_the_value_check_bites(line, needle):
    problems = "\n".join(value_problems(f"# c\n{line}\n"))
    assert needle in problems, problems


def test_the_value_check_bites_on_a_long_token_and_a_placeholder_that_is_not_one():
    token = "A" * 20 + "b" * 20
    problems = "\n".join(value_problems(f'# c\nadmin_ssh_public_key = "ssh-ed25519 {token}"\n'))
    assert "long token-like string" in problems
    problems = "\n".join(value_problems('# c\ntwingate_network = "acme"\n'))
    assert "must say 'example'" in problems


def test_the_value_check_accepts_documentation_and_private_ranges():
    text = '# c\nreserved_ranges = ["192.0.2.10", "198.51.100.1", "203.0.113.9", "10.99.0.0/24", "172.20.0.0/20", "192.168.4.0/24"]\n'
    assert value_problems(text) == []
