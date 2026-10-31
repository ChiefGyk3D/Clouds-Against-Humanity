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
    allowed=None,
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
                            "digitalocean_droplet": ["modules/ok/main.tf"],
                            **(allowed or {}),
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


# ---- Spaces: a flat, manifest-priced bucket behind a stack switch (#113) ----

SPACES_PRICES = {**PRICES, "spaces": {"monthly": 5.0}}
SPACES_ALLOWED = {"digitalocean_spaces_bucket": ["modules/spaces-bucket/main.tf"]}
SPACES_MODULE_TF = {
    "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n',
    "modules/spaces-bucket/main.tf": (
        'resource "digitalocean_spaces_bucket" "this" {\n  name = "x"\n}\n'
        'resource "digitalocean_spaces_key" "this" {\n  name = "k"\n}\n'
    ),
}
SPACES_LOCALS = (
    "locals {\n  on = var.spaces_enabled ? 1 : 0\n"
    '  cost = jsondecode(file("${path.module}/cost.json"))\n}\n'
)
SPACES_OUT = (
    'output "spaces_enabled" {\n  value = var.spaces_enabled\n  precondition {\n'
    "    condition = !var.spaces_enabled || (\n"
    '      length([for r in local.cost.resources : r if r.kind == "spaces"]) == 1\n    )\n'
    '    error_message = "price it"\n  }\n}\n'
)
SPACES_CALL = 'module "state" {\n  source = "../../modules/spaces-bucket"\n%s}\n'
SPACES_ENTRY = {"name": "state-bucket", "kind": "spaces"}


def spaces_repo(tmp_path, entries=(), body="  count = local.on\n", locals_=SPACES_LOCALS,
                out=SPACES_OUT, approved_total=6.0, extra=None,
                source="../../modules/spaces-bucket"):
    files = {
        **SPACES_MODULE_TF,
        "stacks/10-access/spaces.tf": locals_ + (SPACES_CALL % body).replace(
            "../../modules/spaces-bucket", source
        ),
        "stacks/10-access/spaces_out.tf": out,
        **(extra or {}),
    }
    return make_repo(
        tmp_path, [droplet(), *entries], approved_total=approved_total,
        tf_files=files, prices=SPACES_PRICES, allowed=SPACES_ALLOWED,
    )


def test_a_spaces_entry_is_priced_flat_from_the_price_table(tmp_path):
    root = make_repo(tmp_path, [droplet(), SPACES_ENTRY], prices=SPACES_PRICES)
    assert cost_check.total_cost(root, SPACES_PRICES) == 11.0


def test_a_spaces_entry_cannot_set_its_own_price(tmp_path):
    root = make_repo(
        tmp_path, [{**SPACES_ENTRY, "monthly": 0.01, "price": 0}], prices=SPACES_PRICES
    )
    assert cost_check.total_cost(root, SPACES_PRICES) == 5.0


def test_a_spaces_entry_without_a_table_price_fails_closed(tmp_path):
    root = make_repo(tmp_path, [SPACES_ENTRY])
    with pytest.raises(ValueError, match="no price for spaces"):
        cost_check.total_cost(root, PRICES)


@pytest.mark.parametrize("bad", [-1, "five", None, float("nan"), True])
def test_a_malformed_spaces_price_fails_closed(tmp_path, bad):
    prices = {**PRICES, "spaces": {"monthly": bad}}
    root = make_repo(tmp_path, [SPACES_ENTRY], prices=prices)
    with pytest.raises(ValueError):
        cost_check.total_cost(root, prices)


def test_spaces_is_not_priced_on_another_cloud(tmp_path):
    with pytest.raises(ValueError, match="no price model"):
        cost_check.resource_cost(SPACES_ENTRY, SPACES_PRICES, provider="aws")


def test_spaces_key_is_a_free_type(tmp_path, capsys):
    root = make_repo(
        tmp_path, [droplet()],
        tf_files={**OK_DROPLET, "stacks/10-access/x.tf": 'resource "digitalocean_spaces_key" "x" {}\n'},
    )
    code, err = run_main(root, capsys)
    assert code == 0, err


def test_spaces_bucket_outside_the_allowed_file_fails(tmp_path, capsys):
    root = make_repo(
        tmp_path, [droplet()],
        tf_files={**OK_DROPLET, "stacks/10-access/x.tf": 'resource "digitalocean_spaces_bucket" "x" {}\n'},
        allowed=SPACES_ALLOWED,
    )
    code, err = run_main(root, capsys)
    assert code == 1
    assert "stacks/10-access/x.tf" in err and "digitalocean_spaces_bucket" in err


def test_spaces_bucket_with_no_allowed_file_at_all_fails(tmp_path, capsys):
    root = make_repo(
        tmp_path, [droplet()],
        tf_files={**OK_DROPLET, "modules/spaces-bucket/main.tf": 'resource "digitalocean_spaces_bucket" "x" {}\n'},
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "digitalocean_spaces_bucket" in err


@pytest.mark.parametrize("meta", ["count = 1", "count = var.n", 'for_each = toset(["a"])'])
def test_count_or_for_each_on_the_bucket_resource_is_refused(tmp_path, capsys, meta):
    root = make_repo(
        tmp_path, [droplet()],
        tf_files={
            **OK_DROPLET,
            "modules/spaces-bucket/main.tf": f'resource "digitalocean_spaces_bucket" "this" {{\n  {meta}\n}}\n',
        },
        allowed=SPACES_ALLOWED,
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "digitalocean_spaces_bucket" in err and ("count" in err or "for_each" in err)


def test_an_inactive_bucket_module_adds_nothing(tmp_path, capsys):
    root = spaces_repo(tmp_path)
    assert cost_check.total_cost(root, SPACES_PRICES) == 6.0
    code, err = run_main(root, capsys)
    assert code == 0, err


def test_an_active_bucket_module_is_priced_and_held_to_the_approved_total(tmp_path, capsys):
    root = spaces_repo(tmp_path, entries=[SPACES_ENTRY], approved_total=6.0)
    code, err = run_main(root, capsys)
    assert code == 1 and "approved" in err
    root = spaces_repo(tmp_path / "ok", entries=[SPACES_ENTRY], approved_total=11.0)
    code, err = run_main(root, capsys)
    assert code == 0, err


@pytest.mark.parametrize(
    "body",
    [
        "  count = 2\n",
        "  count = var.n\n",
        '  for_each = toset(["a"])\n',
        "",
    ],
)
def test_a_bucket_module_call_must_use_the_stack_switch(tmp_path, capsys, body):
    root = spaces_repo(tmp_path, body=body)
    code, err = run_main(root, capsys)
    assert code == 1 and ("spaces-bucket" in err or "state" in err)


def test_the_switch_must_be_a_variable_ternary(tmp_path, capsys):
    root = spaces_repo(tmp_path, locals_=SPACES_LOCALS.replace("var.spaces_enabled ? 1 : 0", "1"))
    code, err = run_main(root, capsys)
    assert code == 1 and "0 spaces" in err


def test_the_switch_needs_the_manifest_precondition(tmp_path, capsys):
    root = spaces_repo(tmp_path, out=SPACES_OUT.replace("!var.spaces_enabled ||", "true ||"))
    code, err = run_main(root, capsys)
    assert code == 1 and "0 spaces" in err


def test_spaces_entries_must_match_the_module_calls(tmp_path, capsys):
    root = spaces_repo(
        tmp_path, entries=[SPACES_ENTRY, {**SPACES_ENTRY, "name": "b"}], approved_total=16.0
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "2 spaces manifest entr" in err


@pytest.mark.parametrize(
    "source",
    [
        "../../modules/./spaces-bucket",
        "../../modules//spaces-bucket",
        "../../modules/spaces-bucket/",
        "../../modules/spaces-bucket/.",
        "../../modules/x/../spaces-bucket",
        "./../../modules/spaces-bucket",
        "../../modules/copy/spaces-bucket",
        "../10-access/../../modules/other/spaces-bucket",
    ],
)
def test_a_bucket_module_source_must_be_the_one_canonical_path(tmp_path, capsys, source):
    root = spaces_repo(tmp_path, source=source)
    assert cost_check.spaces_module_problems(root), source
    code, err = run_main(root, capsys)
    assert code == 1 and "modules/spaces-bucket" in err


def test_the_canonical_source_still_passes(tmp_path):
    assert cost_check.spaces_module_problems(spaces_repo(tmp_path)) == []


def test_a_bucket_call_in_a_wrapper_module_without_a_manifest_is_refused(tmp_path, capsys):
    wrapper = {
        "modules/wrapper/main.tf": (
            'module "state" {\n  source = "../spaces-bucket"\n  count  = local.on\n}\n'
        )
    }
    root = spaces_repo(tmp_path, extra=wrapper)
    problems = cost_check.spaces_module_problems(root)
    assert any("modules/wrapper" in p and "no cost.json" in p for p in problems), problems
    code, err = run_main(root, capsys)
    assert code == 1 and "modules/wrapper" in err


def test_a_switch_proved_for_the_edge_kind_does_not_satisfy_spaces(tmp_path):
    edge_out = SPACES_OUT.replace('r.kind == "spaces"', 'r.kind == "droplet"')
    root = spaces_repo(tmp_path, out=edge_out)
    assert any("0 spaces" in p for p in cost_check.spaces_module_problems(root))
    assert cost_check.edge_switch_verified(root, "stacks/10-access")
    assert not cost_check.edge_switch_verified(root, "stacks/10-access", kind="spaces")


# ---- the committed files carry the Spaces price and approval (#113) ----

REPO = Path(__file__).resolve().parents[1]


def test_committed_spaces_price_is_five_dollars_with_a_source_and_date():
    spaces = json.loads((REPO / "docs/cost-prices.json").read_text())["spaces"]
    assert spaces["monthly"] == 5.0
    assert spaces["source"].startswith("https://docs.digitalocean.com/products/spaces/")
    assert len(spaces["retrieved"]) == 10 and spaces["retrieved"].startswith("2026-")


def test_committed_approval_allows_only_the_bucket_module_for_spaces():
    do = json.loads((REPO / "docs/stages/approved.json").read_text())["providers"]["digitalocean"]
    assert do["allowed_sources"]["digitalocean_spaces_bucket"] == ["modules/spaces-bucket/main.tf"]
    assert "digitalocean_spaces_key" not in do["allowed_sources"]
    assert do["approved_monthly_total"] <= 29.0


# ---- docker-host: the workload droplet behind a stack switch (#111) ----------

DOCKER_PRICES = {**PRICES, "droplets": {**PRICES["droplets"]}}
DOCKER_ALLOWED = {
    "digitalocean_droplet": ["modules/ok/main.tf", "modules/docker-host/main.tf"],
}
DOCKER_MODULE_TF = {
    "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n',
    "modules/docker-host/main.tf": 'resource "digitalocean_droplet" "workload" {\n  name = "x"\n}\n',
}
DOCKER_FILTER = '[for r in local.cost.resources : r if r.name == "workload" && r.kind == "droplet"]'
DOCKER_SIZE_EXPR = (
    "length(local.priced_workload) == 1 ? local.priced_workload[0].size"
    " : local.cost.planned.workload.size"
)
DOCKER_LOCALS = (
    "locals {\n  on = var.workload_enabled ? 1 : 0\n"
    '  cost = jsondecode(file("${path.module}/cost.json"))\n'
    f"  priced_workload = {DOCKER_FILTER}\n"
    f"  workload_size = {DOCKER_SIZE_EXPR}\n}}\n"
)
DOCKER_OUT = (
    'output "workload_enabled" {\n  value = var.workload_enabled\n  precondition {\n'
    "    condition = !var.workload_enabled || (\n"
    '      length([for r in local.cost.resources : r if r.name == "workload" && r.kind == "droplet"]) == 1\n'
    "    )\n"
    '    error_message = "price it"\n  }\n}\n'
)
DOCKER_CALL = (
    'module "workload" {\n  source = "../../modules/docker-host"\n%s'
    "  size   = local.workload_size\n}\n"
)
DOCKER_ENTRY = {"name": "workload", "kind": "droplet", "size": "s-1vcpu-2gb", "backups": False}


def docker_repo(tmp_path, entries=(), body="  count = local.on\n", locals_=DOCKER_LOCALS,
                out=DOCKER_OUT, approved_total=6.0, extra=None,
                source="../../modules/docker-host", call=DOCKER_CALL):
    files = {
        **DOCKER_MODULE_TF,
        "stacks/10-access/docker.tf": locals_ + (call % body).replace(
            "../../modules/docker-host", source
        ),
        "stacks/10-access/docker_out.tf": out,
        **(extra or {}),
    }
    return make_repo(
        tmp_path, [droplet(), *entries], approved_total=approved_total,
        tf_files=files, prices=DOCKER_PRICES, allowed=DOCKER_ALLOWED, connector_modules=1,
    )


def test_an_inactive_docker_host_adds_nothing(tmp_path, capsys):
    root = docker_repo(tmp_path)
    assert cost_check.total_cost(root, DOCKER_PRICES) == 6.0
    assert cost_check.docker_module_problems(root)[0] == []
    code, err = run_main(root, capsys)
    assert code == 0, err


def test_an_active_docker_host_is_priced_from_the_table_and_held_to_the_total(tmp_path, capsys):
    root = docker_repo(tmp_path, entries=[DOCKER_ENTRY])
    assert cost_check.total_cost(root, DOCKER_PRICES) == 18.0
    code, err = run_main(root, capsys)
    assert code == 1 and "approved" in err
    root = docker_repo(tmp_path / "ok", entries=[DOCKER_ENTRY], approved_total=18.0)
    code, err = run_main(root, capsys)
    assert code == 0, err


@pytest.mark.parametrize(
    "body",
    ["  count = 2\n", "  count = var.n\n", '  for_each = toset(["a"])\n', ""],
)
def test_a_docker_host_call_must_use_the_stack_switch(tmp_path, capsys, body):
    root = docker_repo(tmp_path, body=body)
    assert cost_check.docker_module_problems(root)[0]
    code, err = run_main(root, capsys)
    assert code == 1 and ("docker-host" in err or "workload" in err)


@pytest.mark.parametrize("size", ['size   = "s-1vcpu-1gb"', "size   = var.size", "size   = local.a.b.size"])
def test_a_docker_host_size_must_be_a_plain_local_reference(tmp_path, capsys, size):
    call = DOCKER_CALL.replace("size   = local.workload_size", size)
    root = docker_repo(tmp_path, call=call)
    assert any("size" in p for p in cost_check.docker_module_problems(root)[0]), size
    code, err = run_main(root, capsys)
    assert code == 1 and "docker-host" in err


def test_a_docker_host_without_a_size_is_refused(tmp_path):
    root = docker_repo(tmp_path, call=DOCKER_CALL.replace("  size   = local.workload_size\n", ""))
    assert any("size" in p for p in cost_check.docker_module_problems(root)[0])


def test_the_docker_switch_must_be_a_variable_ternary(tmp_path, capsys):
    root = docker_repo(tmp_path, locals_=DOCKER_LOCALS.replace("var.workload_enabled ? 1 : 0", "1"))
    code, err = run_main(root, capsys)
    assert code == 1 and "0 workload" in err


def test_the_docker_switch_needs_the_manifest_precondition(tmp_path, capsys):
    root = docker_repo(tmp_path, out=DOCKER_OUT.replace("!var.workload_enabled ||", "true ||"))
    code, err = run_main(root, capsys)
    assert code == 1 and "0 workload" in err


@pytest.mark.parametrize(
    "swap",
    [
        ('r.name == "workload" && r.kind == "droplet"', 'r.kind == "spaces"'),
        ('r.name == "workload" && r.kind == "droplet"', "true"),
        ('r.name == "workload" && r.kind == "droplet"', 'r.kind == "droplet"'),
        ('r.name == "workload" && r.kind == "droplet"', 'r.name == "workload"'),
    ],
)
def test_a_switch_proved_for_another_kind_does_not_satisfy_docker(tmp_path, swap):
    root = docker_repo(tmp_path, out=DOCKER_OUT.replace(*swap))
    assert any("0 workload" in p for p in cost_check.docker_module_problems(root)[0])
    assert not cost_check.edge_switch_verified(root, "stacks/10-access", kind="docker")


def test_the_docker_proof_is_specific_to_docker_not_to_the_edge_check(tmp_path):
    root = docker_repo(tmp_path)
    assert cost_check.edge_switch_verified(root, "stacks/10-access", kind="docker")
    spaces_out = DOCKER_OUT.replace(
        'r.name == "workload" && r.kind == "droplet"', 'r.kind == "spaces"'
    )
    root = docker_repo(tmp_path / "s", out=spaces_out)
    assert cost_check.edge_switch_verified(root, "stacks/10-access")
    assert not cost_check.edge_switch_verified(root, "stacks/10-access", kind="docker")


def test_docker_entries_must_match_the_module_calls(tmp_path, capsys):
    root = docker_repo(
        tmp_path, entries=[DOCKER_ENTRY, {**DOCKER_ENTRY, "name": "workload"}], approved_total=30.0
    )
    problems = cost_check.docker_module_problems(root)[0]
    assert any("2 workload" in p for p in problems), problems


@pytest.mark.parametrize(
    "source",
    [
        "../../modules/./docker-host",
        "../../modules//docker-host",
        "../../modules/docker-host/",
        "../../modules/docker-host/.",
        "../../modules/x/../docker-host",
        "./../../modules/docker-host",
        "../../modules/copy/docker-host",
        "../10-access/../../modules/other/docker-host",
    ],
)
def test_a_docker_host_source_must_be_the_one_canonical_path(tmp_path, capsys, source):
    root = docker_repo(tmp_path, source=source)
    assert cost_check.docker_module_problems(root)[0], source
    code, err = run_main(root, capsys)
    assert code == 1 and "modules/docker-host" in err


def test_the_canonical_docker_source_still_passes(tmp_path):
    assert cost_check.docker_module_problems(docker_repo(tmp_path))[0] == []


def test_a_docker_host_call_in_a_wrapper_module_without_a_manifest_is_refused(tmp_path, capsys):
    wrapper = {
        "modules/wrapper/main.tf": (
            'module "workload" {\n  source = "../docker-host"\n  count  = local.on\n'
            "  size   = local.workload_size\n}\n"
        )
    }
    root = docker_repo(tmp_path, extra=wrapper)
    problems = cost_check.docker_module_problems(root)[0]
    assert any("modules/wrapper" in p and "no cost.json" in p for p in problems), problems
    code, err = run_main(root, capsys)
    assert code == 1 and "modules/wrapper" in err


def test_the_docker_droplet_is_not_a_connector_machine(tmp_path, capsys):
    # One connector module and one connector entry plus the workload entry:
    # the workload droplet is reconciled by docker_module_problems, not as a connector.
    root = docker_repo(tmp_path, entries=[DOCKER_ENTRY], approved_total=18.0)
    code, err = run_main(root, capsys)
    assert code == 0, err
    # With no docker-host call, the same workload entry would need a connector block.
    root = make_repo(
        tmp_path / "x", [droplet(), DOCKER_ENTRY], approved_total=18.0,
        tf_files=DOCKER_MODULE_TF, prices=DOCKER_PRICES, allowed=DOCKER_ALLOWED,
        connector_modules=1,
    )
    code, err = run_main(root, capsys)
    assert code == 1 and "twingate-connector module block" in err


def test_committed_approval_allows_the_docker_host_droplet_source():
    do = json.loads((REPO / "docs/stages/approved.json").read_text())["providers"]["digitalocean"]
    assert do["allowed_sources"]["digitalocean_droplet"] == [
        "modules/twingate-connector/main.tf",
        "modules/edge-host/main.tf",
        "modules/docker-host/main.tf",
    ]
    assert do["approved_monthly_total"] == 12.0


def test_the_committed_workload_stack_is_off_and_adds_nothing():
    prices = json.loads((REPO / "docs/cost-prices.json").read_text())
    assert prices["droplets"]["s-1vcpu-2gb"] == 12
    assert cost_check.docker_module_problems(REPO)[0] == []
    assert cost_check.edge_switch_verified(REPO, "stacks/30-workloads", kind="docker")


# ---- docker-host review fixes: size from the manifest, exact precondition ----


def _with_locals(**changes):
    text = DOCKER_LOCALS
    for old, new in changes.items():
        text = text.replace(DOCKER_FILTER if old == "filter" else DOCKER_SIZE_EXPR, new, 1)
    return text


@pytest.mark.parametrize(
    "locals_",
    [
        # a literal
        DOCKER_LOCALS.replace(DOCKER_SIZE_EXPR, '"s-1vcpu-2gb"'),
        # a variable
        DOCKER_LOCALS.replace(DOCKER_SIZE_EXPR, "var.size"),
        # derived from the manifest's planned block only (never the priced entry)
        DOCKER_LOCALS.replace(DOCKER_SIZE_EXPR, "local.cost.planned.workload.size"),
        # a literal fallback
        DOCKER_LOCALS.replace("local.cost.planned.workload.size", '"s-1vcpu-2gb"'),
        # wrong entry index or attribute
        DOCKER_LOCALS.replace("priced_workload[0].size", "priced_workload[0].name"),
        # a different local than the filtered manifest list
        DOCKER_LOCALS.replace("length(local.priced_workload) == 1", "length(local.other) == 1"),
        # the filter does not select the workload droplet
        DOCKER_LOCALS.replace('r.name == "workload" && r.kind == "droplet"', "true"),
        DOCKER_LOCALS.replace('r.kind == "droplet"', 'r.kind == "spaces"'),
        # the filter list is not derived from the manifest
        DOCKER_LOCALS.replace("local.cost.resources", "var.resources"),
    ],
)
def test_the_docker_size_must_derive_from_the_manifest_entry(tmp_path, capsys, locals_):
    root = docker_repo(tmp_path, locals_=locals_)
    problems = cost_check.docker_module_problems(root)[0]
    assert any("size" in p and "manifest" in p for p in problems), problems
    code, err = run_main(root, capsys)
    assert code == 1 and "docker-host" in err


def test_a_size_local_defined_only_in_a_comment_does_not_count(tmp_path):
    locals_ = DOCKER_LOCALS.replace(
        f"  workload_size = {DOCKER_SIZE_EXPR}\n",
        f'  workload_size = "s-1vcpu-2gb"\n  # workload_size = {DOCKER_SIZE_EXPR}\n',
    )
    root = docker_repo(tmp_path, locals_=locals_)
    assert any("size" in p for p in cost_check.docker_module_problems(root)[0])


def test_a_size_local_defined_twice_is_refused(tmp_path):
    locals_ = DOCKER_LOCALS + 'locals {\n  workload_size = "s-1vcpu-1gb"\n}\n'
    root = docker_repo(tmp_path, locals_=locals_)
    assert any("size" in p for p in cost_check.docker_module_problems(root)[0])


def test_a_planned_size_missing_from_the_price_table_is_refused(tmp_path, capsys):
    root = docker_repo(tmp_path)
    manifest = root / "stacks/10-access/cost.json"
    data = json.loads(manifest.read_text())
    data["planned"] = {"workload": {"size": "s-99vcpu-1tb"}}
    manifest.write_text(json.dumps(data))
    problems = cost_check.docker_module_problems(root)[0]
    assert any("planned" in p and "s-99vcpu-1tb" in p for p in problems), problems


def test_a_planned_size_in_the_price_table_passes(tmp_path):
    root = docker_repo(tmp_path)
    manifest = root / "stacks/10-access/cost.json"
    data = json.loads(manifest.read_text())
    data["planned"] = {"workload": {"size": "s-1vcpu-2gb"}}
    manifest.write_text(json.dumps(data))
    assert cost_check.docker_module_problems(root)[0] == []


def _out(condition, extra="", where="output"):
    return (
        f'{where} "workload_enabled" {{\n  value = var.workload_enabled\n{extra}'
        f"  precondition {{\n    condition = {condition}\n"
        '    error_message = "price it"\n  }\n}\n'
    )


GOOD_COND = f"!var.workload_enabled || length({DOCKER_FILTER}) == 1"


def test_the_exact_condition_forms_are_accepted(tmp_path):
    for cond in (
        GOOD_COND,
        f"!var.workload_enabled || (\n      length({DOCKER_FILTER}) == 1\n    )",
        (
            '!var.workload_enabled||length( [ for q in local.cost.resources : q if q.name == "workload" '
            '&& q.kind == "droplet" ] )==1'
        ),
    ):
        root = docker_repo(tmp_path / str(abs(hash(cond))), out=_out(cond))
        assert cost_check.docker_module_problems(root)[0] == [], cond


@pytest.mark.parametrize(
    "out",
    [
        # tokens only in an error message or another attribute; condition is true
        _out("true").replace('"price it"', f'"length({DOCKER_FILTER}) == 1 !var.workload_enabled ||"'),
        # tokens only in a comment
        _out("true").replace("value =", f"# !var.workload_enabled || length({DOCKER_FILTER}) == 1\n  value ="),
        # tokens in the value attribute of the output
        _out("true", extra=f"  description = \"!var.workload_enabled || length({DOCKER_FILTER}) == 1\"\n"),
        # the right text, but in a resource lifecycle precondition, not an output
        _out(GOOD_COND, where="resource \"terraform_data\"").replace(
            'resource "terraform_data" "workload_enabled"', 'resource "terraform_data" "x"'
        ),
        # the condition is weakened or reshaped
        _out(GOOD_COND + " || true"),
        _out("true && " + GOOD_COND),
        _out(GOOD_COND.replace("== 1", "== 2")),
        _out(GOOD_COND.replace("== 1", ">= 0")),
        _out(GOOD_COND.replace("!var.workload_enabled", "var.workload_enabled")),
        _out(GOOD_COND.replace("||", "&&")),
        _out(GOOD_COND.replace("!var.workload_enabled", "!var.other")),
        _out(GOOD_COND.replace('&& r.kind == "droplet"', '|| r.kind == "droplet"')),
        _out(GOOD_COND.replace("local.cost.resources", "local.priced_workload")),
        _out(GOOD_COND.replace("[for r in", "[for q in")),
    ],
)
def test_the_docker_precondition_must_be_the_exact_condition(tmp_path, out):
    root = docker_repo(tmp_path, out=out)
    assert any("0 workload" in p for p in cost_check.docker_module_problems(root)[0])
    assert not cost_check.edge_switch_verified(root, "stacks/10-access", kind="docker")


def test_the_precondition_of_another_output_does_not_count_for_the_switch_output(tmp_path):
    other = _out(GOOD_COND).replace('"workload_enabled"', '"somewhere_else"')
    root = docker_repo(tmp_path, out=other)
    # The condition is exact but guards another output, which is still a plan-time check on the
    # same switch variable, so it counts; a condition on a different variable does not.
    assert cost_check.docker_module_problems(root)[0] == []
    bad = other.replace("!var.workload_enabled", "!var.other_flag")
    root = docker_repo(tmp_path / "b", out=bad)
    assert cost_check.docker_module_problems(root)[0]
