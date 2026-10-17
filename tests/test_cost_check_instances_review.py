"""Review fixes for stack instances: shared-code pricing, zero-cost instances,
cent precision."""

import json

from test_cost_check_instances import (
    DO_PRICES,
    add_site,
    build,
    cost_check,
    droplets,
    fails_with,
    write_json,
)


def cheaper(n):
    return [
        {
            "name": f"d{i}",
            "kind": "droplet",
            "size": "s-1vcpu-512mb-10gb",
            "backups": False,
        }
        for i in range(n)
    ]


def with_cheap_size(root):
    DO_PRICES["droplets"]["s-1vcpu-512mb-10gb"] = 4
    write_json(root / "docs/cost-prices.json", DO_PRICES)
    DO_PRICES["droplets"].pop("s-1vcpu-512mb-10gb")


def test_instance_with_cheaper_sizes_than_the_shared_code_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    with_cheap_size(root)
    assert json.loads((root / "docs/cost-prices.json").read_text())["droplets"][
        "s-1vcpu-512mb-10gb"
    ]
    add_site(root, resources=cheaper(2))
    fails_with(root, capsys, "must equal the base stack's entry")


def test_instance_with_renamed_machines_fails(tmp_path, capsys):
    root = build(tmp_path, do_cap=24.0)
    res = droplets(2)
    res[0]["name"] = "other"
    add_site(root, resources=res)
    fails_with(root, capsys, "resource names must equal the base stack's")


def test_zero_cost_instance_still_needs_a_site_approval(tmp_path, capsys):
    root = build(tmp_path, do_cap=12.0, sites={"tor3": {"approved_monthly_total": 0}})
    write_json(root / "stacks/00-foundation/cost.json", {"resources": []})
    add_site(
        root, stack="00-foundation", instance_of="stacks/00-foundation", resources=[]
    )
    fails_with(
        root, capsys, "site tor2 has a manifest but is not in the approved sites map"
    )


def test_fractional_cents_compare_at_cent_precision():
    parts = {"": 14.712, "tor2": 14.712}
    entry = {"sites": {"tor2": {"approved_monthly_total": 14.71}}}
    assert cost_check.sites_problems("p", entry, 29.42, parts) == []


def test_fractional_cents_still_fail_a_real_overage():
    parts = {"": 14.712, "tor2": 14.72}
    entry = {"sites": {"tor2": {"approved_monthly_total": 14.71}}}
    assert cost_check.sites_problems("p", entry, 29.42, parts)


def test_sites_sum_compares_at_cent_precision():
    entry = {
        "sites": {
            "a": {"approved_monthly_total": 0.1},
            "b": {"approved_monthly_total": 0.2},
        }
    }
    assert cost_check.sites_problems("p", entry, 0.3, {}) == []
