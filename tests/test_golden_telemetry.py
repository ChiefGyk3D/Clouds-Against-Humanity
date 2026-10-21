"""Golden addresses for stack 20 (telemetry), and the per-site split.

The stack uses count and for_each, which tests/test_plan_noop_check.py cannot
derive from source, so this file pins the single-site addresses (flags on, the
tofu-test fixture values) in docs/golden-addresses/20-telemetry.json and ties
them to the sources: the single-site resource blocks are exactly the golden
ones, and every extra-site block is a separate `site_*` resource gated on the
`sites` map, so adding a site cannot move an existing address.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import plan_noop_check as pnc
from test_plan_noop_check import noop_plan
from test_telemetry_stack import resource_blocks

GOLDEN = ROOT / "docs" / "golden-addresses" / "20-telemetry.json"


def golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def block_names(addresses) -> set[str]:
    return {re.sub(r"\[.*$", "", a) for a in addresses}


def test_the_golden_file_is_well_formed_and_a_noop_plan_passes():
    g = golden()
    assert g["stack"] == "stacks/20-telemetry"
    pnc.validate_golden(g)
    assert len(g["addresses"]) == 8  # 2 services, 2 logging, 4 scrape
    assert pnc.check(noop_plan(g), g, False) == []


def test_the_golden_blocks_are_exactly_the_single_site_resources():
    single = {n for n in resource_blocks() if not n.split(".")[1].startswith("site_")}
    assert single, "no single-site resource collected"
    assert block_names(golden()["addresses"]) == single


def test_every_extra_site_resource_is_separate_and_gated_on_sites():
    extra = {n: b for n, b in resource_blocks().items() if n.split(".")[1].startswith("site_")}
    assert sorted(extra) == [
        "twingate_resource.site_logging",
        "twingate_resource.site_scrape",
        "twingate_service_account.site_logging",
        "twingate_service_account.site_scrape",
    ]
    for name, body in extra.items():
        assert re.search(r"(?m)^\s*for_each\s*=\s*local\.extra_", body), name
    text = re.sub(r"(?m)#.*$", "", (ROOT / "stacks/20-telemetry/main.tf").read_text())
    # the sites map is empty by default and both flags gate every extra object
    assert "extra_logging = var.logging_enabled ?" in re.sub(r"\s+", " ", text)
    assert "extra_scrape = var.metrics_enabled ?" in re.sub(r"\s+", " ", text)
    variables = (ROOT / "stacks/20-telemetry/variables.tf").read_text()
    sites = re.search(r'variable "sites" \{\n(.*?)\n\}\n', variables, re.DOTALL).group(1)
    assert re.search(r"(?m)^\s*default\s*=\s*\{\}", sites)


def test_the_guard_bites_on_an_added_or_missing_address():
    g = golden()
    plan = noop_plan(g)
    plan["resource_changes"].append(
        {
            "address": 'twingate_resource.site_scrape["tor2:node-a"]',
            "mode": "managed",
            "type": "twingate_resource",
            "change": {"actions": ["create"], "before": None, "after": {}, "after_unknown": {}},
        }
    )
    problems = "\n".join(pnc.check(plan, g, False))
    assert "site_scrape" in problems
    # a fresh plan, from which an ORIGINAL golden entry is removed by name
    missing = 'twingate_resource.scrape["node-a"]'
    plan = noop_plan(g)
    assert any(e["address"] == missing for e in plan["resource_changes"])
    plan["resource_changes"] = [e for e in plan["resource_changes"] if e["address"] != missing]
    problems = "\n".join(pnc.check(plan, g, False))
    assert missing in problems, problems
