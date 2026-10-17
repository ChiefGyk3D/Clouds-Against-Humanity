"""Cost gate across providers: manifests, plans, approval and the shared ceiling."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check

DO_PRICES = {
    "backups_fraction": 0.2,
    "backups_fraction_verified": False,
    "droplets": {"s-1vcpu-1gb": 6},
}
AWS_PRICES = json.loads(
    (Path(__file__).resolve().parents[1] / "docs/cost-prices/aws.json").read_text()
)
CONNECTOR = (
    'module "c{i}" {{\n  source = "../../../modules/aws/twingate-connector"\n}}\n'
)
DO_CONNECTOR = 'module "c{i}" {{\n  source = "../../modules/twingate-connector"\n}}\n'


def instance(name="connector-a", itype="t4g.micro", root_gb=8, public_ip=True):
    return {
        "name": name,
        "kind": "instance",
        "type": itype,
        "root_gb": root_gb,
        "public_ip": public_ip,
    }


def build(
    tmp_path, *, aws=None, do_droplets=1, aws_cap=21.0, aws_active=False, ceiling=30.0
):
    """A repo with a DigitalOcean stack and (optionally) an AWS stack."""
    (tmp_path / "docs/stages").mkdir(parents=True)
    (tmp_path / "docs/cost-prices").mkdir(parents=True)
    (tmp_path / "docs/cost-prices.json").write_text(json.dumps(DO_PRICES))
    (tmp_path / "docs/cost-prices/aws.json").write_text(json.dumps(AWS_PRICES))
    providers = {
        "digitalocean": {
            "approved_monthly_total": 6.0 * do_droplets,
            "active": True,
            "allowed_sources": {
                "digitalocean_droplet": ["modules/twingate-connector/main.tf"]
            },
        }
    }
    if aws is not None:
        providers["aws"] = {
            "approved_monthly_total": aws_cap,
            "active": aws_active,
            "allowed_sources": {
                "aws_instance": ["modules/aws/twingate-connector/main.tf"]
            },
        }
    (tmp_path / "docs/stages/approved.json").write_text(
        json.dumps({"stage": 1, "ceiling": ceiling, "providers": providers})
    )
    do = tmp_path / "stacks/10-access"
    do.mkdir(parents=True)
    do.joinpath("cost.json").write_text(
        json.dumps(
            {
                "resources": [
                    {
                        "name": f"d{i}",
                        "kind": "droplet",
                        "size": "s-1vcpu-1gb",
                        "backups": False,
                    }
                    for i in range(do_droplets)
                ]
            }
        )
    )
    do.joinpath("m.tf").write_text(
        "".join(DO_CONNECTOR.format(i=i) for i in range(do_droplets))
    )
    for rel in (
        "modules/twingate-connector/main.tf",
        "modules/aws/twingate-connector/main.tf",
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            'resource "digitalocean_droplet" "a" {}\n'
            if "aws" not in rel
            else 'resource "aws_instance" "a" {}\n'
        )
    if aws is not None:
        stack = tmp_path / "stacks/aws/10-access"
        stack.mkdir(parents=True)
        stack.joinpath("cost.json").write_text(json.dumps({"resources": aws}))
        stack.joinpath("m.tf").write_text(
            "".join(
                CONNECTOR.format(i=i)
                for i in range(sum(1 for r in aws if r["kind"] == "instance"))
            )
        )
    return tmp_path


def run(root, capsys, *args):
    code = cost_check.main(["--root", str(root), *args])
    return code, capsys.readouterr()


TWO = [instance("connector-a"), instance("connector-b")]


def test_the_two_connector_aws_stack_costs_the_phase_zero_figure(tmp_path):
    root = build(tmp_path, aws=TWO)
    assert cost_check.provider_totals(root)["aws"] == 20.84


def test_aws_stack_in_a_provider_directory_is_found_and_counted(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    code, out = run(root, capsys)
    assert code == 0, out.err
    assert "aws: planned $20.84/mo" in out.out


def test_aws_manifest_over_its_approved_figure_fails(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, aws_cap=15.0)
    code, out = run(root, capsys)
    assert code == 1 and "aws: planned $20.84 is above approved $15.00" in out.err


def test_aws_approval_above_the_ceiling_fails(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, aws_cap=35.0)
    code, out = run(root, capsys)
    assert code == 1 and "above the ceiling" in out.err


def test_two_active_providers_together_above_the_ceiling_fail(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, do_droplets=2, aws_cap=21.0, aws_active=True)
    code, out = run(root, capsys)
    assert code == 1 and "active providers add up to $33.00" in out.err


def test_the_same_providers_pass_when_aws_is_inactive(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, do_droplets=2, aws_cap=21.0, aws_active=False)
    assert run(root, capsys)[0] == 0


def test_a_stack_directory_without_a_manifest_fails(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/cost.json").unlink()
    code, out = run(root, capsys)
    assert (
        code == 1
        and "stacks/aws/10-access: has OpenTofu files but no cost.json" in out.err
    )


def test_an_unapproved_provider_with_paid_types_fails(tmp_path, capsys):
    root = build(tmp_path, aws=None)
    (root / "stacks/10-access/x.tf").write_text('resource "aws_instance" "x" {}\n')
    code, out = run(root, capsys)
    assert code == 1 and "provider aws is not in approved.json" in out.err


def test_a_provider_with_a_manifest_but_no_approval_fails(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    del approved["providers"]["aws"]
    (root / "docs/stages/approved.json").write_text(json.dumps(approved))
    code, out = run(root, capsys)
    assert code == 1 and "no entry in approved.json" in out.err


def test_a_nat_gateway_is_rejected_even_if_approved_sources_names_it(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "modules/aws/nat.tf").write_text('resource "aws_nat_gateway" "n" {}\n')
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    approved["providers"]["aws"]["allowed_sources"]["aws_nat_gateway"] = [
        "modules/aws/nat.tf"
    ]
    (root / "docs/stages/approved.json").write_text(json.dumps(approved))
    code, out = run(root, capsys)
    assert code == 1 and "aws_nat_gateway is rejected" in out.err


@pytest.mark.parametrize(
    "rtype", ["aws_vpc", "aws_subnet", "aws_internet_gateway", "aws_security_group"]
)
def test_free_aws_types_pass(tmp_path, capsys, rtype):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/x.tf").write_text(f'resource "{rtype}" "x" {{}}\n')
    assert run(root, capsys)[0] == 0


@pytest.mark.parametrize(
    "rtype", ["aws_eip", "aws_lb", "aws_db_instance", "aws_vpc_endpoint"]
)
def test_other_aws_types_fail_unless_listed(tmp_path, capsys, rtype):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/x.tf").write_text(f'resource "{rtype}" "x" {{}}\n')
    code, out = run(root, capsys)
    assert code == 1 and rtype in out.err


def test_connector_reconciliation_is_per_stack_not_repository_wide(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, do_droplets=2)
    assert run(root, capsys)[0] == 0
    # one extra AWS connector block must fail in the AWS stack and not be hidden
    # by the DigitalOcean stack's blocks
    (root / "stacks/aws/10-access/extra.tf").write_text(CONNECTOR.format(i=9))
    code, out = run(root, capsys)
    assert code == 1 and "stacks/aws/10-access: 3 twingate-connector" in out.err


def test_an_instance_must_state_its_disk_and_address(tmp_path):
    bad = [{"name": "a", "kind": "instance", "type": "t4g.micro"}]
    root = build(tmp_path, aws=bad)
    with pytest.raises(ValueError, match="root_gb and public_ip"):
        cost_check.provider_totals(root)


def test_an_unknown_instance_type_has_no_price(tmp_path):
    root = build(tmp_path, aws=[instance(itype="m7g.16xlarge")])
    with pytest.raises(ValueError, match="no price for instance type"):
        cost_check.provider_totals(root)


# ---- plan JSON --------------------------------------------------------------


def change(rtype, name, after, unknown=None, actions=("create",)):
    return {
        "address": f"{rtype}.{name}",
        "type": rtype,
        "change": {
            "actions": list(actions),
            "after": after,
            "after_unknown": unknown or {},
        },
    }


def inst(name="a", itype="t4g.micro", gb=8, public=True, **extra):
    after = {
        "instance_type": itype,
        "root_block_device": [{"volume_size": gb}],
        **extra,
    }
    if public is not None:
        after["associate_public_ip_address"] = public
    return change("aws_instance", name, after)


def plan(*changes):
    return {"resource_changes": list(changes)}


def test_a_plan_of_the_two_connectors_matches_the_manifest():
    total, problems = cost_check.plan_cost(plan(inst("a"), inst("b")), AWS_PRICES)
    assert (total, problems) == (20.84, [])


def test_an_instance_with_the_address_unset_is_priced_as_public():
    total, _ = cost_check.plan_cost(plan(inst(public=None)), AWS_PRICES)
    assert total == round(0.0084 * 730 + 0.005 * 730 + 8 * 0.08, 2)


def test_an_instance_with_the_address_explicitly_off_is_not_charged_for_it():
    total, _ = cost_check.plan_cost(plan(inst(public=False)), AWS_PRICES)
    assert total == round(0.0084 * 730 + 8 * 0.08, 2)


def test_a_large_root_volume_is_priced():
    total, _ = cost_check.plan_cost(plan(inst(gb=500)), AWS_PRICES)
    assert total == round(0.0084 * 730 + 0.005 * 730 + 500 * 0.08, 2)


def test_an_extra_ebs_block_device_is_priced():
    total, _ = cost_check.plan_cost(
        plan(inst(ebs_block_device=[{"volume_size": 100}])), AWS_PRICES
    )
    assert total == round(0.0084 * 730 + 0.005 * 730 + 108 * 0.08, 2)


def test_an_explicit_elastic_address_is_priced():
    total, _ = cost_check.plan_cost(
        plan(inst(public=False), change("aws_eip", "e", {})), AWS_PRICES
    )
    assert total == round(0.0084 * 730 + 8 * 0.08 + 0.005 * 730, 2)


def test_a_nat_gateway_in_a_plan_is_rejected():
    _, problems = cost_check.plan_cost(
        plan(change("aws_nat_gateway", "n", {})), AWS_PRICES
    )
    assert problems and "rejected" in problems[0]


def test_for_each_expands_to_one_change_per_instance():
    plan_json = plan(*(inst(f"web[{k!r}]") for k in ("a", "b", "c")))
    total, _ = cost_check.plan_cost(plan_json, AWS_PRICES)
    assert total == round(3 * (0.0084 * 730 + 0.005 * 730 + 8 * 0.08), 2)


def test_a_destroyed_instance_is_not_charged():
    gone = inst()
    gone["change"]["actions"] = ["delete"]
    assert cost_check.plan_cost(plan(gone), AWS_PRICES) == (0.0, [])


def test_an_unknown_type_is_a_problem_not_a_zero():
    _, problems = cost_check.plan_cost(plan(change("aws_lb", "l", {})), AWS_PRICES)
    assert problems and "no price" in problems[0]


def test_a_missing_root_volume_is_a_problem():
    bare = change("aws_instance", "a", {"instance_type": "t4g.micro"})
    _, problems = cost_check.plan_cost(plan(bare), AWS_PRICES)
    assert problems and "root_block_device" in problems[0]


def test_an_unknown_instance_type_in_the_plan_is_a_problem():
    unk = change("aws_instance", "a", {"instance_type": None}, {"instance_type": True})
    _, problems = cost_check.plan_cost(plan(unk), AWS_PRICES)
    assert problems and "instance_type" in problems[0]


def test_non_aws_resources_in_the_plan_are_ignored():
    assert cost_check.plan_cost(
        plan(change("twingate_group", "g", {})), AWS_PRICES
    ) == (0.0, [])


def test_main_checks_a_plan_against_the_manifest(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    good = tmp_path / "good.json"
    good.write_text(json.dumps(plan(inst("a"), inst("b"))))
    assert (
        run(root, capsys, "--plan", str(good), "--stack", "stacks/aws/10-access")[0]
        == 0
    )
    # the plan has a third instance the manifest does not declare
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(plan(inst("a"), inst("b"), inst("c"))))
    code, out = run(root, capsys, "--plan", str(bad), "--stack", "stacks/aws/10-access")
    assert code == 1 and "plan costs $31.27 but cost.json declares $20.84" in out.err


def test_main_fails_when_the_plan_has_a_nat_gateway(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    bad = tmp_path / "nat.json"
    bad.write_text(
        json.dumps(plan(inst("a"), inst("b"), change("aws_nat_gateway", "n", {})))
    )
    code, out = run(root, capsys, "--plan", str(bad), "--stack", "stacks/aws/10-access")
    assert code == 1 and "rejected" in out.err


def test_plan_needs_a_stack(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    p = tmp_path / "p.json"
    p.write_text("{}")
    code, out = run(root, capsys, "--plan", str(p))
    assert code == 1 and "--plan needs --stack" in out.err


# ---- review findings: each was a way to pass the gate -----------------------


def test_a_commented_local_source_does_not_hide_a_remote_one(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/db.tf").write_text(
        'module "db" {\n  /*\n  source = "./looks-local"\n  */\n  # source = "./also-local"\n  source = "terraform-aws-modules/rds/aws"\n}\n'
    )
    code, out = run(root, capsys)
    assert code == 1 and "non-local source" in out.err


def test_a_brace_in_a_string_or_comment_does_not_end_a_connector_block(
    tmp_path, capsys
):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/m.tf").write_text(
        'module "c" {\n  source = "../../../modules/aws/twingate-connector"\n  note   = "}"\n  # }\n  count  = 100\n}\n'
        + CONNECTOR.format(i=7)
    )
    code, out = run(root, capsys)
    assert code == 1 and "uses count" in out.err


def test_a_commented_out_resource_is_not_flagged(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/x.tf").write_text('# resource "aws_lb" "x" {}\n')
    assert run(root, capsys)[0] == 0


def test_approved_json_cannot_approve_a_type_with_no_price_model(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "modules/aws/lb.tf").write_text('resource "aws_lb" "l" {}\n')
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    approved["providers"]["aws"]["allowed_sources"]["aws_lb"] = ["modules/aws/lb.tf"]
    (root / "docs/stages/approved.json").write_text(json.dumps(approved))
    code, out = run(root, capsys)
    assert code == 1 and "no price model" in out.err


@pytest.mark.parametrize("bad", ["nan", "inf", "-1", "abc", None])
def test_a_non_finite_or_negative_approval_fails(tmp_path, capsys, bad):
    root = build(tmp_path, aws=TWO)
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    approved["providers"]["aws"]["approved_monthly_total"] = bad
    (root / "docs/stages/approved.json").write_text(json.dumps(approved))
    code, out = run(root, capsys)
    assert code == 1 and "cost-check:" in out.err


def test_a_nan_ceiling_fails(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    approved["ceiling"] = "nan"
    (root / "docs/stages/approved.json").write_text(json.dumps(approved))
    assert run(root, capsys)[0] == 1


def test_unknown_extra_disks_are_a_problem_not_zero():
    unk = inst(public=False, ebs_block_device=[])
    unk["change"]["after_unknown"] = {"ebs_block_device": True}
    _, problems = cost_check.plan_cost(plan(unk), AWS_PRICES)
    assert problems and "ebs_block_device" in problems[0]


def test_a_stack_directly_under_stacks_aws_is_aws(tmp_path):
    assert cost_check.provider_of_stack("stacks/aws") == "aws"
    assert cost_check.provider_of_stack("stacks/aws/10-access") == "aws"
    assert cost_check.provider_of_stack("stacks/10-access") == "digitalocean"


def test_a_malformed_manifest_exits_nonzero_instead_of_crashing(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    (root / "stacks/aws/10-access/cost.json").write_text(
        '{"resources": [{"kind": "instance"}]}'
    )
    code, _ = run(root, capsys)
    assert code == 1


def test_malformed_plan_shapes_exit_nonzero(tmp_path, capsys):
    root = build(tmp_path, aws=TWO)
    p = tmp_path / "p.json"
    p.write_text(
        json.dumps(
            {
                "resource_changes": [
                    {
                        "type": "aws_instance",
                        "change": {
                            "actions": ["create"],
                            "after": {
                                "instance_type": "t4g.micro",
                                "root_block_device": ["x"],
                            },
                        },
                    }
                ]
            }
        )
    )
    assert (
        run(root, capsys, "--plan", str(p), "--stack", "stacks/aws/10-access")[0] == 1
    )


def test_inactive_providers_are_reported_as_an_attestation(tmp_path, capsys):
    root = build(tmp_path, aws=TWO, aws_active=False)
    out = run(root, capsys)[1].out
    assert "aws: planned $20.84/mo, approved $21.00, inactive" in out
