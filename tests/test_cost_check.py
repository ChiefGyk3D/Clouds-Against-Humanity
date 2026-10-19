import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check

PRICES = {
    "backups_fraction": 0.2,
    "backups_fraction_verified": False,
    "droplets": {"s-1vcpu-1gb": 6, "s-1vcpu-2gb": 12},
}


CONNECTOR_MODULE = (
    'module "connector" {\n  source = "../../modules/twingate-connector"\n'
    "  size   = local.connector.size\n}\n"
)


def make_repo(
    tmp_path,
    resources,
    approved_total=6.0,
    tf_files=None,
    ceiling=30.0,
    prices=None,
    connector_modules=None,
):
    (tmp_path / "docs/stages").mkdir(parents=True)
    (tmp_path / "stacks/10-access").mkdir(parents=True)
    (tmp_path / "docs/cost-prices.json").write_text(json.dumps(prices or PRICES))
    (tmp_path / "docs/stages/approved.json").write_text(
        json.dumps(
            {
                "ceiling": ceiling,
                "providers": {
                    "digitalocean": {
                        "approved_monthly_total": approved_total,
                        "active": True,
                        "allowed_sources": {
                            "digitalocean_droplet": ["modules/ok/main.tf"]
                        },
                    }
                },
            }
        )
    )
    (tmp_path / "stacks/10-access/cost.json").write_text(
        json.dumps({"stage": 1, "resources": resources})
    )
    # Fixture helper: the cost gate now reconciles twingate-connector module
    # blocks against kind=droplet manifest entries, so write one block per
    # droplet unless a test overrides the count.
    if connector_modules is None:
        connector_modules = sum(1 for r in resources if r.get("kind") == "droplet")
    (tmp_path / "stacks/10-access/modules.tf").write_text(
        "".join(
            CONNECTOR_MODULE.replace('"connector"', f'"connector{i}"')
            for i in range(connector_modules)
        )
    )
    for rel, text in (tf_files or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def droplet(size="s-1vcpu-1gb", backups=False):
    return {"name": "connector", "kind": "droplet", "size": size, "backups": backups}


def test_total_sums_manifests(tmp_path):
    root = make_repo(tmp_path, [droplet(), droplet("s-1vcpu-2gb")], approved_total=18)
    assert cost_check.total_cost(root, PRICES) == 18.0


def test_unknown_size_fails_closed(tmp_path):
    root = make_repo(tmp_path, [droplet("s-99vcpu-1tb")])
    with pytest.raises(ValueError, match="no price for size"):
        cost_check.total_cost(root, PRICES)


def test_backups_refused_while_fraction_unverified(tmp_path):
    res = droplet(backups=True)
    res["backup_plan"] = "weekly"
    root = make_repo(tmp_path, [res])
    with pytest.raises(ValueError, match="unverified"):
        cost_check.total_cost(root, PRICES)


def test_backups_priced_once_verified(tmp_path):
    prices = {**PRICES, "backups_fraction_verified": True}
    res = droplet(backups=True)
    res["backup_plan"] = "weekly"
    root = make_repo(tmp_path, [res], prices=prices)
    assert cost_check.total_cost(root, prices) == 7.2


def test_non_droplet_kind_has_no_price_model(tmp_path):
    root = make_repo(tmp_path, [{"name": "lb", "kind": "loadbalancer"}])
    with pytest.raises(ValueError, match="no price model"):
        cost_check.total_cost(root, PRICES)


def test_costed_resource_outside_allowed_file_is_flagged(tmp_path):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n',
            "stacks/10-access/sneaky.tf": 'resource "digitalocean_volume" "v" {}\n',
        },
    )
    found = cost_check.uncosted_sources(
        root, {"digitalocean_droplet": ["modules/ok/main.tf"]}
    )
    assert found == [
        "stacks/10-access/sneaky.tf: digitalocean_volume (the gate has no price model for it)"
    ]


def test_provider_cache_directories_are_ignored(tmp_path):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            "stacks/10-access/.terraform/x.tf": 'resource "digitalocean_droplet" "a" {}\n',
        },
    )
    assert cost_check.uncosted_sources(root, {}) == []


def test_main_passes_at_approved_total(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={"modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n'},
    )
    assert cost_check.main(["--root", str(root)]) == 0
    assert "digitalocean: planned $6.00/mo" in capsys.readouterr().out


def test_main_fails_over_approved_total(tmp_path):
    root = make_repo(tmp_path, [droplet("s-1vcpu-2gb")], approved_total=6.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_fails_when_approval_exceeds_ceiling(tmp_path):
    root = make_repo(tmp_path, [droplet()], approved_total=40.0, ceiling=30.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_reports_value_errors_as_failure(tmp_path):
    root = make_repo(tmp_path, [droplet("s-99vcpu-1tb")])
    assert cost_check.main(["--root", str(root)]) == 1


# ---- allowlist, manifest and module reconciliation (probe-style repos) ----

OK_DROPLET = {"modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n'}


def run_main(root, capsys):
    code = cost_check.main(["--root", str(root)])
    return code, capsys.readouterr().err


@pytest.mark.parametrize(
    "rtype",
    [
        "digitalocean_vpc_nat_gateway",
        "digitalocean_app",
        "digitalocean_container_registry",
        "digitalocean_kubernetes_node_pool",
        "digitalocean_cdn",
    ],
)
def test_unlisted_digitalocean_type_fails_naming_file_and_type(tmp_path, capsys, rtype):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/x.tf": f'resource "{rtype}" "x" {{}}\n',
        },
    )
    code, err = run_main(root, capsys)
    assert code == 1
    assert "stacks/10-access/x.tf" in err and rtype in err


@pytest.mark.parametrize(
    "rtype",
    [
        "digitalocean_project",
        "digitalocean_project_resources",
        "digitalocean_tag",
        "digitalocean_vpc",
        "digitalocean_firewall",
        "digitalocean_ssh_key",
    ],
)
def test_free_types_pass(tmp_path, capsys, rtype):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/x.tf": f'resource "{rtype}" "x" {{}}\n',
        },
    )
    assert run_main(root, capsys)[0] == 0


def test_non_digitalocean_types_are_not_this_gates_business(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/x.tf": 'resource "twingate_group" "g" {}\n',
        },
    )
    assert run_main(root, capsys)[0] == 0


def test_droplet_outside_the_allowed_file_fails(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/d.tf": 'resource "digitalocean_droplet" "b" {}\n',
        },
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "stacks/10-access/d.tf" in err


def test_zero_manifests_fails(tmp_path, capsys):
    root = make_repo(tmp_path, [])
    (root / "stacks/10-access/cost.json").unlink()
    code, err = run_main(root, capsys)
    assert code == 1 and "manifest" in err


def test_second_connector_module_fails(tmp_path, capsys):
    root = make_repo(tmp_path, [droplet()], connector_modules=2, tf_files=OK_DROPLET)
    code, err = run_main(root, capsys)
    assert code == 1 and "twingate-connector" in err


def test_missing_connector_module_for_manifest_droplet_fails(tmp_path, capsys):
    root = make_repo(tmp_path, [droplet()], connector_modules=0, tf_files=OK_DROPLET)
    assert run_main(root, capsys)[0] == 1


@pytest.mark.parametrize("meta", ["count = 5", 'for_each = toset(["a", "b"])'])
def test_connector_module_with_count_or_for_each_fails(tmp_path, capsys, meta):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/modules.tf": f'module "connector" {{\n  source = "../../modules/twingate-connector"\n  size = local.c.size\n  {meta}\n}}\n',
        },
    )
    code, err = run_main(root, capsys)
    assert code == 1 and ("count" in err or "for_each" in err)


@pytest.mark.parametrize(
    "source",
    [
        "git::https://example.invalid/x.git//modules/twingate-connector",
        "registry.example.invalid/acme/thing/digitalocean",
        "acme/thing/digitalocean",
    ],
)
def test_non_local_module_source_fails(tmp_path, capsys, source):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/m.tf": f'module "far" {{\n  source = "{source}"\n}}\n',
        },
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "stacks/10-access/m.tf" in err


def test_local_module_sources_pass(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            "stacks/10-access/m.tf": 'module "a" {\n  source = "./x"\n}\nmodule "b" {\n  source = "../../modules/vpc"\n}\n',
        },
    )
    assert run_main(root, capsys)[0] == 0


def test_tf_json_files_fail(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={**OK_DROPLET, "stacks/10-access/x.tf.json": "{}"},
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "x.tf.json" in err


def test_tf_json_in_cache_dirs_is_ignored(tmp_path, capsys):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={
            **OK_DROPLET,
            ".venv/lib/x.tf.json": "{}",
            "stacks/10-access/.terraform/y.tf.json": "{}",
        },
    )
    assert run_main(root, capsys)[0] == 0


def test_venv_directories_are_skipped(tmp_path):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={".venv/lib/x.tf": 'resource "digitalocean_app" "a" {}\n'},
    )
    assert cost_check.uncosted_sources(root, {}) == []


def test_committed_backups_fraction_is_verified_with_its_source():
    # Issue 117: the committed table carries the DigitalOcean basic weekly
    # backup fraction as verified, with a source URL and a retrieval date.
    table = json.loads((Path(__file__).resolve().parents[1] / "docs/cost-prices.json").read_text())
    assert table["backups_fraction"] == 0.2
    assert table["backups_fraction_verified"] is True
    assert table["backups_source"].startswith("https://docs.digitalocean.com/products/backups/")
    assert table["backups_retrieved"] == "2026-10-19"


# ---- backup plans the gate cannot price -------------------------------------

VERIFIED = {**PRICES, "backups_fraction_verified": True}


def planned(plan="weekly", **extra):
    res = droplet(backups=True)
    if plan is not None:
        res["backup_plan"] = plan
    res.update(extra)
    return res


def test_weekly_backups_still_price_at_twenty_percent(tmp_path):
    root = make_repo(tmp_path, [planned("weekly")], prices=VERIFIED)
    assert cost_check.total_cost(root, VERIFIED) == 7.2


def test_daily_backups_are_refused(tmp_path):
    root = make_repo(tmp_path, [planned("daily")], prices=VERIFIED)
    with pytest.raises(ValueError, match="daily"):
        cost_check.total_cost(root, VERIFIED)


@pytest.mark.parametrize(
    "plan", [None, "", "hourly", "usage", "usage-based", "Weekly", 7, True, ["weekly"]]
)
def test_missing_or_unknown_backup_plan_is_refused(tmp_path, plan):
    # With backups on, DigitalOcean defaults to daily when no plan is stated,
    # so a missing plan is never read as weekly.
    root = make_repo(tmp_path, [planned(plan)], prices=VERIFIED)
    with pytest.raises(ValueError, match="backup_plan"):
        cost_check.total_cost(root, VERIFIED)


@pytest.mark.parametrize(
    "extra",
    [
        {"backup_policy": {"plan": "weekly"}},
        {"backup_usage": {"gib": 10}},
        {"backup_hours": 12},
    ],
)
def test_usage_based_or_unknown_backup_shapes_are_refused(tmp_path, extra):
    root = make_repo(tmp_path, [planned("weekly", **extra)], prices=VERIFIED)
    with pytest.raises(ValueError, match="backup"):
        cost_check.total_cost(root, VERIFIED)


@pytest.mark.parametrize("flag", ["true", "yes", 1, None, "false"])
def test_backups_flag_must_be_a_boolean(tmp_path, flag):
    res = droplet()
    res["backups"] = flag
    root = make_repo(tmp_path, [res], prices=VERIFIED)
    with pytest.raises(ValueError, match="backups"):
        cost_check.total_cost(root, VERIFIED)


def test_backup_plan_with_backups_off_is_refused(tmp_path):
    res = droplet()
    res["backup_plan"] = "daily"
    root = make_repo(tmp_path, [res], prices=VERIFIED)
    with pytest.raises(ValueError, match="backup"):
        cost_check.total_cost(root, VERIFIED)


def droplet_tf(body):
    return {
        "modules/twingate-connector/main.tf": 'resource "digitalocean_droplet" "connector" {\n'
        + body
        + "}\n"
    }


@pytest.mark.parametrize(
    "body",
    [
        "  backups = true\n",
        "  backups = var.backups\n",
        '  backup_policy {\n    plan = "daily"\n  }\n',
        '  backups = false\n  backup_policy {\n    plan = "weekly"\n  }\n',
    ],
)
def test_source_enabling_backups_is_refused(tmp_path, body):
    root = make_repo(tmp_path, [droplet()], tf_files=droplet_tf(body))
    found = cost_check.block_problems(root)
    assert any("backup" in p for p in found), found


@pytest.mark.parametrize("body", ["  backups = false\n", '  size = "s-1vcpu-1gb"\n'])
def test_source_with_backups_off_or_unset_is_not_flagged(tmp_path, body):
    root = make_repo(tmp_path, [droplet()], tf_files=droplet_tf(body))
    assert [p for p in cost_check.block_problems(root) if "backup" in p] == []


# ---- source scan matches HCL syntax, not text -------------------------------

HEREDOC_WORD = '  user_data = <<-EOT\n    backup_policy {\n    backups = true\n  EOT\n'


@pytest.mark.parametrize(
    "body",
    [
        '  tags = ["backup_policy"]\n  backups = false\n',
        '  name = "backup_policy"\n',
        '  description = "uses backup_policy { plan = daily } and backups = true"\n',
        '  name = "x-${var.backup_policy}"\n',
        HEREDOC_WORD,
        "  # backup_policy { plan = \"daily\" }\n  // backups = true\n  /* backup_policy */\n",
        "  backups_enabled = true\n  backups = false\n",
        '  tags = { backups = "true", backup_policy = "x" }\n',
        '  tags = [\n    "backup_policy",\n  ]\n',
    ],
)
def test_backup_words_in_strings_comments_heredocs_are_not_flagged(tmp_path, body):
    root = make_repo(tmp_path, [droplet()], tf_files=droplet_tf(body))
    assert [p for p in cost_check.block_problems(root) if "backup" in p] == []


def test_backup_names_in_a_non_droplet_block_are_not_flagged(tmp_path):
    files = droplet_tf("  backups = false\n")
    files["modules/other/main.tf"] = (
        'resource "twingate_resource" "r" {\n  backups = true\n'
        "  backup_policy {\n    plan = \"daily\"\n  }\n}\n"
    )
    root = make_repo(tmp_path, [droplet()], tf_files=files)
    assert [p for p in cost_check.block_problems(root) if "backup" in p] == []


@pytest.mark.parametrize(
    "body",
    [
        '  backup_policy {\n    plan = "weekly"\n  }\n',
        '  backup_policy{\n    plan = "weekly"\n  }\n',
        '  tags = ["a"]\n\n    backup_policy   {\n    plan = "daily"\n  }\n',
        '  backup_policy = { plan = "daily" }\n',
        '  backup_policy   =   {}\n',
        "  backups   =   true\n",
        "  backups=true\n",
        "  backups = (\n    true\n  )\n",
        "  backups = var.x\n",
        "  backups = \"true\"\n",
    ],
)
def test_real_backup_syntax_is_still_refused(tmp_path, body):
    root = make_repo(tmp_path, [droplet()], tf_files=droplet_tf(body))
    found = cost_check.block_problems(root)
    assert any("backup" in p for p in found), found
