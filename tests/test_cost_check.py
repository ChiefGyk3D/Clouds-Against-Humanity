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


def make_repo(tmp_path, resources, approved_total=6.0, tf_files=None, ceiling=30.0, prices=None):
    (tmp_path / "docs/stages").mkdir(parents=True)
    (tmp_path / "stacks/10-access").mkdir(parents=True)
    (tmp_path / "docs/cost-prices.json").write_text(json.dumps(prices or PRICES))
    (tmp_path / "docs/stages/approved.json").write_text(json.dumps({
        "approved_monthly_total": approved_total,
        "ceiling": ceiling,
        "allowed_sources": {"digitalocean_droplet": ["modules/ok/main.tf"]},
    }))
    (tmp_path / "stacks/10-access/cost.json").write_text(
        json.dumps({"stage": 1, "resources": resources}))
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
    root = make_repo(tmp_path, [droplet(backups=True)])
    with pytest.raises(ValueError, match="unverified"):
        cost_check.total_cost(root, PRICES)


def test_backups_priced_once_verified(tmp_path):
    prices = {**PRICES, "backups_fraction_verified": True}
    root = make_repo(tmp_path, [droplet(backups=True)], prices=prices)
    assert cost_check.total_cost(root, prices) == 7.2


def test_non_droplet_kind_has_no_price_model(tmp_path):
    root = make_repo(tmp_path, [{"name": "lb", "kind": "loadbalancer"}])
    with pytest.raises(ValueError, match="no price model"):
        cost_check.total_cost(root, PRICES)


def test_costed_resource_outside_allowed_file_is_flagged(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n',
        "stacks/10-access/sneaky.tf": 'resource "digitalocean_volume" "v" {}\n',
    })
    found = cost_check.uncosted_sources(root, {"digitalocean_droplet": ["modules/ok/main.tf"]})
    assert found == ["stacks/10-access/sneaky.tf: digitalocean_volume"]


def test_provider_cache_directories_are_ignored(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "stacks/10-access/.terraform/x.tf": 'resource "digitalocean_droplet" "a" {}\n',
    })
    assert cost_check.uncosted_sources(root, {}) == []


def test_main_passes_at_approved_total(tmp_path, capsys):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n'})
    assert cost_check.main(["--root", str(root)]) == 0
    assert "planned $6.00/mo" in capsys.readouterr().out


def test_main_fails_over_approved_total(tmp_path):
    root = make_repo(tmp_path, [droplet("s-1vcpu-2gb")], approved_total=6.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_fails_when_approval_exceeds_ceiling(tmp_path):
    root = make_repo(tmp_path, [droplet()], approved_total=40.0, ceiling=30.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_reports_value_errors_as_failure(tmp_path):
    root = make_repo(tmp_path, [droplet("s-99vcpu-1tb")])
    assert cost_check.main(["--root", str(root)]) == 1
