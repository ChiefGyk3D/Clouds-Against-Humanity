"""Stack instances (step 2b of the stage 2 design): a second site of the same
stack code is a data-only manifest the gate prices and reconciles.

Fixtures only. No real instance exists in the repository.
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cost_check

DO_PRICES = {
    "backups_fraction": 0.2,
    "backups_fraction_verified": False,
    "droplets": {"s-1vcpu-1gb": 6},
}
AWS_PRICES = json.loads((ROOT / "docs/cost-prices/aws.json").read_text())
DO_CONNECTOR = (
    'module "c{i}" {{\n  source = "../../modules/twingate-connector"\n'
    "  size = local.c.size\n}}\n"
)
AWS_CONNECTOR = (
    'module "c{i}" {{\n  source = "../../../modules/aws/twingate-connector"\n'
    "  instance_type = local.c.type\n}}\n"
)


def droplets(n):
    return [
        {"name": f"d{i}", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": False}
        for i in range(n)
    ]


def aws_instances(n):
    return [
        {
            "name": f"a{i}",
            "kind": "instance",
            "type": "t4g.micro",
            "root_gb": 8,
            "public_ip": True,
        }
        for i in range(n)
    ]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def build(tmp_path, *, do_cap=12.0, aws=False, extra_providers=None, sites=None):
    """A repo with the base DigitalOcean 10-access stack (two connectors)."""
    do = {
        "approved_monthly_total": do_cap,
        "active": True,
        "allowed_sources": {
            "digitalocean_droplet": ["modules/twingate-connector/main.tf"]
        },
    }
    if sites is not None:
        do["sites"] = sites
    providers = {"digitalocean": do}
    if aws:
        providers["aws"] = {
            "approved_monthly_total": 60.0,
            "active": False,
            "allowed_sources": {
                "aws_instance": ["modules/aws/twingate-connector/main.tf"]
            },
        }
    providers.update(extra_providers or {})
    write_json(tmp_path / "docs/cost-prices.json", DO_PRICES)
    write_json(tmp_path / "docs/cost-prices/aws.json", AWS_PRICES)
    write_json(
        tmp_path / "docs/stages/approved.json",
        {"stage": 1, "ceiling": 30.0, "providers": providers},
    )
    for rel, body in (
        (
            "modules/twingate-connector/main.tf",
            'resource "digitalocean_droplet" "a" {}\n',
        ),
        *(
            [
                (
                    "modules/aws/twingate-connector/main.tf",
                    'resource "aws_instance" "a" {}\n',
                )
            ]
            if aws
            else []
        ),
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    write_json(tmp_path / "stacks/10-access/cost.json", {"resources": droplets(2)})
    (tmp_path / "stacks/10-access/main.tf").write_text(
        "".join(DO_CONNECTOR.format(i=i) for i in range(2))
    )
    if aws:
        write_json(
            tmp_path / "stacks/aws/10-access/cost.json", {"resources": aws_instances(2)}
        )
        (tmp_path / "stacks/aws/10-access/main.tf").write_text(
            "".join(AWS_CONNECTOR.format(i=i) for i in range(2))
        )
    return tmp_path


def add_site(
    root,
    key="tor2",
    stack="10-access",
    machines=2,
    instance_of="stacks/10-access",
    resources=None,
    **extra,
):
    data = {"resources": droplets(machines) if resources is None else resources}
    if instance_of is not None:
        data["instance_of"] = instance_of
    data.update(extra)
    write_json(root / f"stacks/sites/{key}/{stack}/cost.json", data)
    return root / f"stacks/sites/{key}/{stack}"


def add_and_cap(tmp_path, cap, **kw):
    root = build(tmp_path, do_cap=cap)
    add_site(root, **kw)
    return root


def run(root, capsys):
    code = cost_check.main(["--root", str(root)])
    out = capsys.readouterr()
    return code, out.out, out.err


def fails_with(root, capsys, text):
    code, out, err = run(root, capsys)
    assert code == 1, err
    assert text in err + out, err


# ---- pricing ----------------------------------------------------------------


def test_instance_is_priced_into_its_provider(tmp_path, capsys):
    root = add_and_cap(tmp_path, 24.0)
    code, out, err = run(root, capsys)
    assert code == 0, err
    assert "digitalocean: planned $24.00/mo, approved $24.00" in out


def test_a_second_site_over_the_approved_total_fails(tmp_path, capsys):
    root = add_and_cap(tmp_path, 12.0)
    fails_with(root, capsys, "digitalocean: planned $24.00 is above approved $12.00")


def test_instance_provider_comes_from_instance_of_not_its_path(tmp_path):
    root = build(tmp_path, aws=True)
    add_site(
        root,
        key="east",
        stack="aws/10-access",
        instance_of="stacks/aws/10-access",
        resources=aws_instances(2),
    )
    totals = cost_check.provider_totals(root)
    assert totals["digitalocean"] == 12.0
    assert totals["aws"] == pytest.approx(41.69, abs=0.01)


# ---- instance_of validation ---------------------------------------------------


def test_missing_instance_of_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    add_site(root, instance_of=None)
    fails_with(root, capsys, "instance_of is missing")


@pytest.mark.parametrize(
    "bad",
    [
        7,
        "",
        "stacks/10-access/",
        "../stacks/10-access",
        "/stacks/10-access",
        "stacks//10-access",
        "stacks/./10-access",
    ],
)
def test_malformed_instance_of_fails(tmp_path, capsys, bad):
    root = build(tmp_path, do_cap=24.0)
    add_site(root, instance_of=bad)
    fails_with(root, capsys, "instance_of")


def test_instance_of_naming_no_stack_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    add_site(root, stack="20-telemetry", instance_of="stacks/20-telemetry")
    fails_with(root, capsys, "names no stack directory with its own cost.json")


def test_instance_of_naming_a_stack_without_manifest_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    (root / "stacks/20-telemetry").mkdir()
    add_site(root, stack="20-telemetry", instance_of="stacks/20-telemetry")
    fails_with(root, capsys, "names no stack directory with its own cost.json")


def test_instance_of_naming_another_instance_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=36.0)
    add_site(root, key="tor2")
    add_site(root, key="tor3", instance_of="stacks/sites/tor2/10-access")
    fails_with(root, capsys, "must not point into stacks/sites")


def test_instance_path_must_mirror_instance_of(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    write_json(root / "stacks/00-foundation/cost.json", {"resources": []})
    add_site(root, stack="00-foundation", instance_of="stacks/10-access")
    fails_with(root, capsys, "must sit at stacks/sites/<resource_key>/10-access")


def test_instance_of_outside_sites_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=12.0)
    write_json(
        root / "stacks/10-access/cost.json",
        {"resources": droplets(2), "instance_of": "stacks/10-access"},
    )
    fails_with(root, capsys, "instance_of is only allowed under stacks/sites/")


def test_manifest_directly_under_sites_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    write_json(
        root / "stacks/sites/cost.json",
        {"resources": droplets(2), "instance_of": "stacks/10-access"},
    )
    fails_with(root, capsys, "stacks/sites/<resource_key>/")


@pytest.mark.parametrize("key", ["Tor2", "tor_2", "-tor2", "tor 2"])
def test_resource_key_shape_is_enforced(tmp_path, capsys, key):
    root = build(tmp_path, do_cap=24.0)
    add_site(root, key=key)
    code, _out, err = run(root, capsys)
    assert code == 1, err
    assert "resource_key" in err or "stack directory name" in err


# ---- instances carry no code --------------------------------------------------


@pytest.mark.parametrize("name", ["main.tf", "x.tofu", "override.tf"])
def test_instance_with_opentofu_files_fails(tmp_path, capsys, name):
    root = build(tmp_path, do_cap=24.0)
    inst = add_site(root)
    (inst / name).write_text("# empty\n")
    fails_with(root, capsys, "instances carry no code")


def test_opentofu_file_in_a_site_dir_without_manifest_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=12.0)
    d = root / "stacks/sites/tor2"
    d.mkdir(parents=True)
    (d / "x.tf").write_text("# empty\n")
    fails_with(root, capsys, "instances carry no code")


# ---- reconciliation with the stack named in instance_of -----------------------


@pytest.mark.parametrize("machines", [1, 3])
def test_machine_count_must_equal_connector_blocks_of_the_named_stack(
    tmp_path, capsys, machines
):
    root = build(tmp_path, do_cap=40.0)
    add_site(root, machines=machines)
    fails_with(root, capsys, "twingate-connector module block(s)")


def test_instance_count_reconciles_with_matching_machines(tmp_path, capsys):
    root = add_and_cap(tmp_path, 24.0)
    code, _, err = run(root, capsys)
    assert code == 0, err


def test_base_stack_reconciliation_is_unchanged_by_instances(tmp_path, capsys):
    root = build(tmp_path, do_cap=40.0)
    add_site(root)
    write_json(root / "stacks/10-access/cost.json", {"resources": droplets(3)})
    fails_with(
        root, capsys, "stacks/10-access: 2 twingate-connector module block(s) but 3"
    )


# ---- ids and the config.yml mapping -------------------------------------------


def test_stack_id_mapping_rule():
    f = cost_check.stack_id
    assert f("stacks/10-access", None) == "cah-10-access"
    assert f("stacks/00-foundation", None) == "cah-00-foundation"
    assert f("stacks/aws/10-access", None) == "cah-aws-10-access"
    assert f("stacks/sites/tor2/10-access", "stacks/10-access") == "cah-10-access-tor2"
    assert (
        f("stacks/sites/east/aws/10-access", "stacks/aws/10-access")
        == "cah-aws-10-access-east"
    )


def test_two_manifests_for_one_stack_id_fail(tmp_path, capsys):
    root = build(tmp_path, do_cap=40.0)
    add_site(root)
    # A base stack literally named 10-access-tor2 claims the same id.
    write_json(root / "stacks/10-access-tor2/cost.json", {"resources": []})
    fails_with(root, capsys, "duplicate stack id cah-10-access-tor2")


def config_problems(root):
    """The design's test: every config.yml stack id has exactly one manifest."""
    config = yaml.safe_load((root / ".spacelift/config.yml").read_text())
    ids = cost_check.manifest_ids(root)
    problems = []
    for sid in config["stacks"]:
        have = ids.get(sid, [])
        if len(have) != 1:
            problems.append(f"{sid}: {len(have)} manifest(s), expected exactly 1")
    return problems


def write_config(root, *ids):
    p = root / ".spacelift/config.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(
            {"version": "1", "stacks": {i: {"before_init": []} for i in ids}}
        )
    )


def test_every_real_config_stack_has_exactly_one_manifest():
    assert config_problems(ROOT) == []


def test_config_entries_for_a_base_and_an_instance_each_match_one_manifest(tmp_path):
    root = build(tmp_path, do_cap=24.0)
    add_site(root)
    write_config(root, "cah-10-access", "cah-10-access-tor2")
    assert config_problems(root) == []


def test_config_entry_with_no_manifest_fails(tmp_path):
    root = build(tmp_path, do_cap=24.0)
    write_config(root, "cah-10-access", "cah-10-access-tor2")
    assert config_problems(root) == [
        "cah-10-access-tor2: 0 manifest(s), expected exactly 1"
    ]


def test_config_entry_with_two_manifests_fails(tmp_path):
    root = build(tmp_path, do_cap=40.0)
    add_site(root)
    write_json(root / "stacks/10-access-tor2/cost.json", {"resources": []})
    write_config(root, "cah-10-access-tor2")
    assert config_problems(root) == [
        "cah-10-access-tor2: 2 manifest(s), expected exactly 1"
    ]


def test_an_instance_without_instance_of_matches_no_id(tmp_path):
    root = build(tmp_path, do_cap=24.0)
    add_site(root, instance_of=None)
    write_config(root, "cah-10-access-tor2")
    assert config_problems(root) != []


# ---- per-provider sites map ---------------------------------------------------


def sites_repo(tmp_path, cap, sites, *keys):
    root = build(tmp_path, do_cap=cap, sites=sites)
    for k in keys:
        add_site(root, key=k)
    return root


def test_site_missing_from_a_present_map_fails(tmp_path, capsys):
    root = sites_repo(
        tmp_path, 24.0, {"tor3": {"approved_monthly_total": 12.0}}, "tor2"
    )
    fails_with(
        root, capsys, "site tor2 has a manifest but is not in the approved sites map"
    )


def test_site_in_the_map_passes(tmp_path, capsys):
    root = sites_repo(
        tmp_path, 24.0, {"tor2": {"approved_monthly_total": 12.0}}, "tor2"
    )
    code, _, err = run(root, capsys)
    assert code == 0, err


def test_site_over_its_own_approved_total_fails(tmp_path, capsys):
    root = sites_repo(tmp_path, 30.0, {"tor2": {"approved_monthly_total": 6.0}}, "tor2")
    fails_with(
        root,
        capsys,
        "digitalocean: site tor2 planned $12.00 is above its approved $6.00",
    )


def test_sites_summing_above_the_provider_figure_fail(tmp_path, capsys):
    root = sites_repo(
        tmp_path,
        20.0,
        {
            "tor2": {"approved_monthly_total": 12.0},
            "tor3": {"approved_monthly_total": 12.0},
        },
        "tor2",
    )
    fails_with(
        root,
        capsys,
        "approved sites add up to $24.00, above the provider approved $20.00",
    )


def test_base_stack_must_fit_provider_figure_minus_sites(tmp_path, capsys):
    # Provider 20, site tor2 approved 12: the base stack (12) has only 8.
    root = sites_repo(
        tmp_path, 20.0, {"tor2": {"approved_monthly_total": 12.0}}, "tor2"
    )
    fails_with(
        root,
        capsys,
        "base stacks planned $12.00 are above approved $20.00 minus sites $12.00",
    )


def test_without_a_map_behaviour_is_unchanged(tmp_path, capsys):
    root = sites_repo(tmp_path, 24.0, None, "tor2", "tor3")
    fails_with(root, capsys, "planned $36.00 is above approved $24.00")


@pytest.mark.parametrize(
    "sites",
    [
        [],
        {"tor2": 12.0},
        {"tor2": {}},
        {"tor2": {"approved_monthly_total": -1}},
        {"tor2": {"approved_monthly_total": "12"}},
        {"tor2": {"approved_monthly_total": float("nan")}},
        {"Tor 2": {"approved_monthly_total": 1.0}},
    ],
)
def test_malformed_sites_map_fails_closed(tmp_path, capsys, sites):
    root = build(tmp_path, do_cap=24.0, sites=sites)
    add_site(root)
    code, _, err = run(root, capsys)
    assert code == 1, err


def test_active_ceiling_uses_the_provider_figure_not_the_sites(tmp_path, capsys):
    # Provider 24 (sites 12 inside it) + another active provider 12 = 36 > 30.
    root = build(
        tmp_path,
        do_cap=24.0,
        sites={"tor2": {"approved_monthly_total": 12.0}},
        extra_providers={"gcp": {"approved_monthly_total": 12.0, "active": True}},
    )
    add_site(root)
    fails_with(
        root, capsys, "the approved figures of the active providers add up to $36.00"
    )


def test_real_repo_still_passes_with_no_instances(capsys):
    code, out, err = run(ROOT, capsys)
    assert code == 0, err
    assert "digitalocean: planned $12.00/mo, approved $12.00" in out
    assert not (ROOT / "stacks/sites").exists()
