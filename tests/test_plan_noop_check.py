"""scripts/plan_noop_check.py against mocked plan JSON, and the golden files.

CI cannot run a real plan (that needs the live state and credentials), so the
checker is proved here against plan JSON built from the golden files: a no-op
plan passes, and every kind of change the stage 2 settings work must never
cause (a rename, an update, a replacement, a missing or extra address, a moved
resource, a changed force-new attribute) fails. The real gate is the
tracked-run plan the maintainer reads in Spacelift.

The golden files are also tied to the code: the addresses must equal the ones
derived from the stack sources and module calls, and the bootstrap `moved`
blocks must be the moves the files list.
"""

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import plan_noop_check as pnc

GOLDEN_DIR = ROOT / "docs" / "golden-addresses"
STACKS = ("00-foundation", "10-access")
SECRET_MARKER = "TOKEN-MARKER-must-never-be-printed"


def load_golden(stack: str) -> dict:
    return json.loads((GOLDEN_DIR / f"{stack}.json").read_text(encoding="utf-8"))


def attribute_value(attr: str, expected):
    return f"id-of-{attr}" if expected == pnc.UNCHANGED else copy.deepcopy(expected)


def noop_plan(golden: dict) -> dict:
    """A plan JSON shaped like `tofu show -json`, where nothing changes."""
    changes = []
    for address, spec in golden["addresses"].items():
        values = {a: attribute_value(a, v) for a, v in spec["force_new"].items()}
        values["some_other_attribute"] = "x"
        changes.append(
            {
                "address": address,
                "mode": "managed",
                "type": spec["type"],
                "change": {
                    "actions": ["no-op"],
                    "before": dict(values),
                    "after": dict(values),
                    "after_unknown": {},
                },
            }
        )
    for address in golden.get("data", []):
        changes.append(
            {
                "address": address,
                "mode": "data",
                "type": "digitalocean_ssh_key",
                "change": {"actions": ["read"], "before": None, "after": {}},
            }
        )
    return {"format_version": "1.2", "resource_changes": changes}


def entry(plan: dict, address: str) -> dict:
    return next(e for e in plan["resource_changes"] if e["address"] == address)


def run(plan: dict, golden: dict, allow_moves: bool = False) -> list[str]:
    return pnc.check(plan, golden, allow_moves)


# --- a no-op plan passes ----------------------------------------------------


@pytest.mark.parametrize("stack", STACKS)
def test_a_noop_plan_passes(stack):
    golden = load_golden(stack)
    assert run(noop_plan(golden), golden) == []


@pytest.mark.parametrize("stack", STACKS)
def test_a_noop_plan_passes_with_allow_moves(stack):
    golden = load_golden(stack)
    assert run(noop_plan(golden), golden, allow_moves=True) == []


def test_tag_order_does_not_matter():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    droplet = entry(plan, "module.connector_a.digitalocean_droplet.connector")["change"]
    droplet["after"]["tags"] = list(reversed(droplet["after"]["tags"]))
    assert run(plan, golden) == []


def test_a_data_source_read_at_plan_time_may_be_absent():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["resource_changes"] = [
        e for e in plan["resource_changes"] if e.get("mode") != "data"
    ]
    assert run(plan, golden) == []


# --- what must fail -----------------------------------------------------------


def test_renaming_the_remote_network_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    change = entry(plan, "twingate_remote_network.this")["change"]
    change["before"]["name"] = "access-tor1"
    change["after"]["name"] = "access-site-tor1"
    change["actions"] = ["update"]
    problems = "\n".join(run(plan, golden))
    assert "twingate_remote_network.this" in problems
    assert "action is ['update']" in problems
    assert "attribute name differs" in problems


def test_a_rename_hidden_behind_a_noop_action_still_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    change = entry(plan, "twingate_remote_network.this")["change"]
    change["after"]["name"] = "access-site-tor1"
    problems = run(plan, golden)
    assert any("attribute name differs" in p for p in problems), problems


def test_a_rename_present_on_both_sides_is_not_the_golden_value():
    # What a changed default does to a brand new stack: before and after agree,
    # but they are not the names the live stack has.
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    change = entry(plan, "twingate_remote_network.this")["change"]
    change["before"]["name"] = change["after"]["name"] = "access-site-tor1"
    problems = run(plan, golden)
    assert any("not the golden value" in p for p in problems), problems


@pytest.mark.parametrize("stack", STACKS)
def test_an_update_fails(stack):
    golden = load_golden(stack)
    for address in golden["addresses"]:
        plan = noop_plan(golden)
        entry(plan, address)["change"]["actions"] = ["update"]
        problems = run(plan, golden)
        assert any(address in p and "action is ['update']" in p for p in problems), (
            address,
            problems,
        )


@pytest.mark.parametrize(
    "actions", [["create"], ["delete"], ["delete", "create"], ["create", "delete"], []]
)
def test_create_delete_and_replace_fail(actions):
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    entry(plan, "module.connector_a.digitalocean_droplet.connector")["change"][
        "actions"
    ] = actions
    assert run(plan, golden)


@pytest.mark.parametrize("stack", STACKS)
def test_a_missing_address_fails(stack):
    golden = load_golden(stack)
    for address in golden["addresses"]:
        plan = noop_plan(golden)
        plan["resource_changes"] = [
            e for e in plan["resource_changes"] if e["address"] != address
        ]
        problems = run(plan, golden)
        assert any(
            address in p and "missing from the plan" in p for p in problems
        ), (address, problems)


def test_an_address_not_in_the_golden_list_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["resource_changes"].append(
        {
            "address": "digitalocean_droplet.surprise",
            "mode": "managed",
            "type": "digitalocean_droplet",
            "change": {"actions": ["no-op"], "before": {}, "after": {}},
        }
    )
    problems = run(plan, golden)
    assert any("digitalocean_droplet.surprise" in p and "not in the golden" in p for p in problems)


def test_a_data_source_not_in_the_golden_list_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["resource_changes"].append(
        {
            "address": "data.digitalocean_ssh_key.other",
            "mode": "data",
            "type": "digitalocean_ssh_key",
            "change": {"actions": ["read"], "before": None, "after": {}},
        }
    )
    assert any("data.digitalocean_ssh_key.other" in p for p in run(plan, golden))


def test_a_data_source_that_would_be_created_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    entry(plan, "data.digitalocean_ssh_key.admin")["change"]["actions"] = ["create"]
    assert run(plan, golden)


def test_the_same_address_twice_fails():
    golden = load_golden("00-foundation")
    plan = noop_plan(golden)
    plan["resource_changes"].append(copy.deepcopy(plan["resource_changes"][0]))
    assert any("appears twice" in p for p in run(plan, golden))


def force_new_cases():
    for stack in STACKS:
        golden = load_golden(stack)
        for address, spec in golden["addresses"].items():
            for attr in spec["force_new"]:
                yield stack, address, attr


@pytest.mark.parametrize("stack,address,attr", list(force_new_cases()))
def test_every_force_new_attribute_is_compared(stack, address, attr):
    golden = load_golden(stack)
    plan = noop_plan(golden)
    change = entry(plan, address)["change"]
    value = change["after"][attr]
    if isinstance(value, bool):
        change["after"][attr] = not value
    elif isinstance(value, list):
        change["after"][attr] = [*value, "extra"]
    else:
        change["after"][attr] = f"{value}-changed"
    problems = run(plan, golden)
    assert any(address in p and attr in p for p in problems), problems


@pytest.mark.parametrize("stack,address,attr", list(force_new_cases()))
def test_every_force_new_attribute_must_be_present_and_known(stack, address, attr):
    golden = load_golden(stack)
    plan = noop_plan(golden)
    del entry(plan, address)["change"]["before"][attr]
    assert any(address in p and attr in p for p in run(plan, golden))
    plan = noop_plan(golden)
    entry(plan, address)["change"]["after_unknown"] = {attr: True}
    assert any(address in p and attr in p for p in run(plan, golden))


def test_a_changed_user_data_fails_without_printing_it(tmp_path, capsys):
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    change = entry(plan, "module.connector_a.digitalocean_droplet.connector")["change"]
    change["before"]["user_data"] = f"before {SECRET_MARKER}"
    change["after"]["user_data"] = f"after {SECRET_MARKER}"
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    code = pnc.main(
        ["--plan", str(tmp_path / "plan.json"), "--golden", str(GOLDEN_DIR / "10-access.json")]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "user_data" in captured.out
    assert SECRET_MARKER not in captured.out + captured.err


# --- moves -------------------------------------------------------------------


def moved_plan():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    for new, old in (
        (
            "module.connector_a.module.bootstrap.twingate_connector.this",
            "module.connector_a.twingate_connector.this",
        ),
    ):
        entry(plan, new)["previous_address"] = old
    return golden, plan


def test_a_moved_resource_fails_without_allow_moves():
    golden, plan = moved_plan()
    assert any("moved" in p for p in run(plan, golden))


def test_a_moved_resource_passes_with_allow_moves_when_listed():
    golden, plan = moved_plan()
    assert run(plan, golden, allow_moves=True) == []


def test_a_move_from_an_unlisted_address_fails_even_with_allow_moves():
    golden, plan = moved_plan()
    entry(plan, "module.connector_a.module.bootstrap.twingate_connector.this")[
        "previous_address"
    ] = "twingate_connector.elsewhere"
    assert any("does not allow" in p for p in run(plan, golden, allow_moves=True))


def test_allow_moves_does_not_excuse_a_changed_attribute():
    golden, plan = moved_plan()
    change = entry(plan, "module.connector_a.module.bootstrap.twingate_connector.this")["change"]
    change["after"]["name"] = "access-site-tor1-connector-a"
    assert run(plan, golden, allow_moves=True)


# --- the files it reads ------------------------------------------------------


def write(tmp_path, plan, golden=None):
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "golden.json").write_text(json.dumps(golden or load_golden("00-foundation")))
    return ["--plan", str(tmp_path / "plan.json"), "--golden", str(tmp_path / "golden.json")]


def test_main_exit_codes(tmp_path, capsys):
    golden = load_golden("00-foundation")
    assert pnc.main(write(tmp_path, noop_plan(golden))) == 0
    bad = noop_plan(golden)
    entry(bad, "digitalocean_tag.baseline")["change"]["actions"] = ["update"]
    assert pnc.main(write(tmp_path, bad)) == 1


def test_main_refuses_unusable_input(tmp_path, capsys):
    golden = load_golden("00-foundation")
    args = write(tmp_path, noop_plan(golden))
    assert pnc.main(["--plan", str(tmp_path / "nope.json"), "--golden", args[3]]) == 2
    (tmp_path / "plan.json").write_text("{not json")
    assert pnc.main(args) == 2
    (tmp_path / "plan.json").write_text("[]")
    assert pnc.main(args) == 2
    # a plan with no resource_changes is not a plan we can judge: fail, never pass
    (tmp_path / "plan.json").write_text(json.dumps({"format_version": "1.2"}))
    assert pnc.main(args) == 2
    (tmp_path / "plan.json").write_text(
        json.dumps({"errored": True, "resource_changes": []})
    )
    assert pnc.main(args) == 2
    (tmp_path / "plan.json").write_text(json.dumps({"resource_changes": ["x"]}))
    assert pnc.main(args) == 2
    capsys.readouterr()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g.update(addresses={}),
        lambda g: g.update(extra=1),
        lambda g: g["addresses"]["digitalocean_tag.baseline"].update(force_new={}),
        lambda g: g["addresses"]["digitalocean_tag.baseline"].pop("type"),
        lambda g: g.update(moves={"a": "not.listed"}),
        lambda g: g.update(data="x"),
        lambda g: g.pop("stack"),
    ],
)
def test_a_malformed_golden_file_is_refused(tmp_path, mutate):
    golden = load_golden("00-foundation")
    mutate(golden)
    args = write(tmp_path, noop_plan(load_golden("00-foundation")), golden)
    assert pnc.main(args) == 2


def test_running_as_a_script_with_isolated_mode(tmp_path):
    golden = load_golden("00-foundation")
    args = write(tmp_path, noop_plan(golden))
    result = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "plan_noop_check.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "passed" in result.stdout


# --- the golden files match the code -------------------------------------------


def top_level_blocks(text: str):
    """(kind, labels, body) for each top-level block; blocks end at a line '}'."""
    for m in re.finditer(r'(?ms)^(\w+)((?:\s+"[^"]+")*)\s*\{\n(.*?)^\}\n', text):
        yield m.group(1), re.findall(r'"([^"]+)"', m.group(2)), m.group(3)


def derive(directory: Path, prefix: str = "") -> tuple[set[str], set[str]]:
    """Resource and data addresses a directory creates, including its modules."""
    resources: set[str] = set()
    data: set[str] = set()
    for tf in sorted(directory.glob("*.tf")):
        for kind, labels, body in top_level_blocks(tf.read_text(encoding="utf-8")):
            if kind == "resource":
                if re.search(r"(?m)^  (count|for_each)\s*=", body):
                    raise AssertionError(f"{tf}: count/for_each is not understood here")
                resources.add(f"{prefix}{labels[0]}.{labels[1]}")
            elif kind == "data":
                data.add(f"{prefix}data.{labels[0]}.{labels[1]}")
            elif kind == "module":
                if re.search(r"(?m)^  (count|for_each)\s*=", body):
                    raise AssertionError(f"{tf}: count/for_each is not understood here")
                source = re.search(r'(?m)^\s*source\s*=\s*"([^"]+)"', body).group(1)
                sub_r, sub_d = derive(
                    (directory / source).resolve(), f"{prefix}module.{labels[0]}."
                )
                resources |= sub_r
                data |= sub_d
    return resources, data


@pytest.mark.parametrize("stack", STACKS)
def test_the_golden_addresses_are_exactly_what_the_sources_create(stack):
    golden = load_golden(stack)
    resources, data = derive(ROOT / "stacks" / stack)
    assert set(golden["addresses"]) == resources
    assert set(golden["data"]) == data
    assert golden["stack"] == f"stacks/{stack}"


@pytest.mark.parametrize("stack", STACKS)
def test_golden_types_match_the_address(stack):
    for address, spec in load_golden(stack)["addresses"].items():
        assert address.split(".")[-2] == spec["type"], address


def test_the_golden_moves_are_the_moved_blocks_of_the_connector_module():
    text = (ROOT / "modules" / "twingate-connector" / "main.tf").read_text()
    pairs = re.findall(
        r"(?ms)^moved\s*\{\s*from\s*=\s*(\S+)\s*to\s*=\s*(\S+)\s*\}", text
    )
    assert pairs, "no moved blocks found"
    expected = {}
    for module in ("connector_a", "connector_b"):
        for old, new in pairs:
            expected[f"module.{module}.{old}"] = f"module.{module}.{new}"
    assert load_golden("10-access")["moves"] == expected
    assert load_golden("00-foundation")["moves"] == {}


def test_the_golden_droplet_size_is_the_costed_size():
    cost = json.loads((ROOT / "stacks" / "10-access" / "cost.json").read_text())
    sizes = {r["size"] for r in cost["resources"]}
    golden = load_golden("10-access")["addresses"]
    for x in ("a", "b"):
        spec = golden[f"module.connector_{x}.digitalocean_droplet.connector"]
        assert {spec["force_new"]["size"]} == sizes


@pytest.mark.parametrize("stack", STACKS)
def test_every_golden_name_is_asserted_by_the_stack_tests(stack):
    # The golden file and the stack's own golden-name test must agree, so one
    # cannot be edited without the other.
    tests = "\n".join(
        p.read_text() for p in (ROOT / "stacks" / stack / "tests").glob("*.tftest.hcl")
    )
    for address, spec in load_golden(stack)["addresses"].items():
        name = spec["force_new"].get("name")
        if name:
            assert f'"{name}"' in tests, f"{address}: {name} is not asserted in the tests"


# --- outputs and data sources (review findings) -----------------------------------


@pytest.mark.parametrize("stack", STACKS)
def test_a_changed_output_fails_even_when_every_resource_is_noop(stack):
    golden = load_golden(stack)
    plan = noop_plan(golden)
    plan["output_changes"] = {
        "region": {"actions": ["update"], "before": "tor1", "after": "fra1"}
    }
    problems = run(plan, golden)
    assert any("output region" in p for p in problems), problems
    assert not any("tor1" in p or "fra1" in p for p in problems)


@pytest.mark.parametrize("actions", [["create"], ["delete"], ["update"], []])
def test_any_output_action_but_noop_fails(actions):
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["output_changes"] = {"connector_tag": {"actions": actions}}
    assert run(plan, golden)


def test_an_unknown_output_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["output_changes"] = {
        "connector_private_ips": {"actions": ["no-op"], "after_unknown": True}
    }
    assert any("unknown" in p for p in run(plan, golden))


@pytest.mark.parametrize("stack", STACKS)
def test_unchanged_outputs_pass(stack):
    golden = load_golden(stack)
    plan = noop_plan(golden)
    plan["output_changes"] = {
        "region": {"actions": ["no-op"], "before": "tor1", "after": "tor1"}
    }
    assert run(plan, golden) == []


def test_a_malformed_output_changes_block_is_refused(tmp_path):
    golden = load_golden("00-foundation")
    for bad in ([], {"region": "x"}, {"region": {}}):
        plan = noop_plan(golden)
        plan["output_changes"] = bad
        with pytest.raises(pnc.InputError):
            run(plan, golden)


def test_a_moved_data_source_fails_without_allow_moves():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    entry(plan, "data.digitalocean_ssh_key.admin")["previous_address"] = "data.digitalocean_ssh_key.old"
    assert any("moved" in p for p in run(plan, golden))
    # not excused by --allow-moves either: the golden file lists no such move
    assert any("does not allow" in p for p in run(plan, golden, allow_moves=True))


@pytest.mark.parametrize("actions", [["update"], ["delete"], ["delete", "create"]])
def test_a_data_source_may_not_update_or_delete(actions):
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    entry(plan, "data.digitalocean_ssh_key.admin")["change"]["actions"] = actions
    assert run(plan, golden)


def test_an_updated_baseline_tag_output_on_stack_00_fails():
    golden = load_golden("00-foundation")
    plan = noop_plan(golden)
    plan["output_changes"] = {
        "baseline_tag": {"actions": ["update"], "before": "cah-baseline-tor1", "after": "x"}
    }
    problems = run(plan, golden)
    assert any("output baseline_tag" in p for p in problems), problems


def test_an_updated_connector_output_on_stack_10_fails():
    golden = load_golden("10-access")
    plan = noop_plan(golden)
    plan["output_changes"] = {
        "connector_tag": {"actions": ["update"], "before": "a", "after": "b"}
    }
    assert any("output connector_tag" in p for p in run(plan, golden))
    plan["output_changes"] = {
        "connector_private_ips": {"actions": ["create"], "before": None, "after": {}}
    }
    assert any("output connector_private_ips" in p for p in run(plan, golden))


def test_the_command_line_fails_on_an_output_only_change(tmp_path):
    golden = load_golden("00-foundation")
    plan = noop_plan(golden)
    plan["output_changes"] = {"baseline_tag": {"actions": ["update"]}}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    code = pnc.main(
        ["--plan", str(tmp_path / "plan.json"), "--golden", str(GOLDEN_DIR / "00-foundation.json")]
    )
    assert code == 1
