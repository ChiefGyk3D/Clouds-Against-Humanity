"""Codex review of PR 48: instances tied to the shared code, every costed
resource reconciled, --plan on instance paths, config.yml check in the gate."""

import json

from test_cost_check_instances import (
    add_site,
    aws_instances,
    build,
    cost_check,
    droplets,
    fails_with,
    run,
    write_config,
    write_json,
)
from test_cost_check_multicloud import inst, plan

EAST = "stacks/sites/east/aws/10-access"


def aws_site(root, resources=None):
    add_site(
        root,
        key="east",
        stack="aws/10-access",
        instance_of="stacks/aws/10-access",
        resources=aws_instances(2) if resources is None else resources,
    )


def test_instance_cannot_claim_cheaper_resources_than_shared_code(tmp_path, capsys):
    root = build(tmp_path, do_cap=212.0)
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    approved["ceiling"] = 212.0
    write_json(root / "docs/stages/approved.json", approved)
    prices = json.loads((root / "docs/cost-prices.json").read_text())
    prices["droplets"]["expensive"] = 100.0
    write_json(root / "docs/cost-prices.json", prices)
    write_json(
        root / "stacks/10-access/cost.json",
        {
            "resources": [
                {
                    "name": f"d{i}",
                    "kind": "droplet",
                    "size": "expensive",
                    "backups": False,
                }
                for i in range(2)
            ]
        },
    )
    add_site(root, resources=droplets(2))
    fails_with(root, capsys, "must equal the base stack's entry")


def test_instance_must_include_all_paid_resources_of_shared_stack(tmp_path, capsys):
    root = build(tmp_path, aws=True)
    base = json.loads((root / "stacks/aws/10-access/cost.json").read_text())
    base["resources"].append({"name": "data", "kind": "ebs_volume", "gb": 100})
    write_json(root / "stacks/aws/10-access/cost.json", base)
    aws_site(root)
    fails_with(root, capsys, "resource names must equal the base stack's")


def test_instance_volume_size_must_equal_the_base_volume(tmp_path, capsys):
    root = build(tmp_path, aws=True)
    vol = {"name": "data", "kind": "ebs_volume", "gb": 100}
    base = json.loads((root / "stacks/aws/10-access/cost.json").read_text())
    base["resources"].append(vol)
    write_json(root / "stacks/aws/10-access/cost.json", base)
    aws_site(root, aws_instances(2) + [{**vol, "gb": 1}])
    fails_with(root, capsys, "must equal the base stack's entry")


def test_matching_aws_instance_with_volume_passes_reconciliation(tmp_path):
    root = build(tmp_path, aws=True)
    vol = {"name": "data", "kind": "ebs_volume", "gb": 100}
    base = json.loads((root / "stacks/aws/10-access/cost.json").read_text())
    base["resources"].append(vol)
    write_json(root / "stacks/aws/10-access/cost.json", base)
    aws_site(root, aws_instances(2) + [vol])
    assert cost_check.structure_problems(root) == []


def write_plan(root, name, *changes):
    path = root / name
    path.write_text(json.dumps(plan(*changes)))
    return str(path)


def plan_run(root, capsys, plan_path, stack):
    code = cost_check.main(["--root", str(root), "--plan", plan_path, "--stack", stack])
    return code, capsys.readouterr()


def test_plan_check_accepts_an_instance_path(tmp_path, capsys):
    root = build(tmp_path, aws=True)
    aws_site(root)
    good = write_plan(root, "plan.json", inst("a"), inst("b"))
    code, out = plan_run(root, capsys, good, EAST)
    # The fixture's AWS approval is over the ceiling (a different failure); only
    # the plan result is under test here.
    assert "implemented for aws only" not in out.err
    assert "the plan costs" not in out.err
    assert "no cost.json to reconcile" not in out.err


def test_plan_check_compares_with_the_instance_manifest(tmp_path, capsys):
    root = build(tmp_path, aws=True)
    aws_site(root)
    bad = write_plan(root, "plan.json", inst("a"), inst("b"), inst("c"))
    code, out = plan_run(root, capsys, bad, EAST)
    assert code == 1
    assert f"{EAST}: the plan costs" in out.err


def test_config_stack_id_without_a_manifest_fails_the_gate_itself(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    write_config(root, "cah-10-access", "cah-10-access-tor2")
    fails_with(
        root,
        capsys,
        ".spacelift/config.yml stack id cah-10-access-tor2 has 0 manifest(s)",
    )


def test_config_with_every_id_matched_passes_the_gate(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    add_site(root)
    write_config(root, "cah-10-access", "cah-10-access-tor2")
    code, _, err = run(root, capsys)
    assert code == 0, err


def test_unreadable_config_fails_closed(tmp_path, capsys):
    root = build(tmp_path)
    (root / ".spacelift").mkdir()
    (root / ".spacelift/config.yml").write_text("stacks: [not, a, map]\n")
    fails_with(root, capsys, ".spacelift/config.yml is unreadable")
