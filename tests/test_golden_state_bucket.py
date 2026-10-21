# SPDX-License-Identifier: Apache-2.0
"""Golden address and shape of the stage 3 state bucket (stack 30, module spaces-bucket).

The tofu tests prove the plans with a mocked provider. This file reads the
sources, so a second bucket, a public ACL, a bucket policy, a CORS rule, an
access key created in code, or a bucket the flag does not gate fails here even
if nobody wrote a tofu test for it. docs/golden-addresses/30-state.json pins the
one address the stack plans with the flag on, and the guards are shown to bite.
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

STACK = ROOT / "stacks" / "30-state"
MODULE = ROOT / "modules" / "spaces-bucket"
GOLDEN = ROOT / "docs" / "golden-addresses" / "30-state.json"
BUCKET = "digitalocean_spaces_bucket.this"
CALLED = f"module.state_bucket[0].{BUCKET}"


def code(path: Path) -> str:
    return re.sub(r"(?m)(#|//).*$", "", path.read_text())


def all_code() -> dict[str, str]:
    files = sorted(STACK.glob("*.tf")) + sorted(MODULE.glob("*.tf"))
    return {p.relative_to(ROOT).as_posix(): code(p) for p in files}


def resource_blocks(text: str) -> list[str]:
    return [f"{m.group(1)}.{m.group(2)}" for m in re.finditer(r'(?m)^resource "([^"]+)" "([^"]+)" \{', text)]


def golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def exposure_problems(files: dict[str, str]) -> list[str]:
    """Everything that could make the bucket or an object reachable, or mint a key."""
    problems = []
    for name, text in files.items():
        if re.search(r'(?m)^\s*acl\s*=\s*"(?!private")', text):
            problems.append(f"{name}: an ACL other than private")
        if "spaces_bucket_policy" in text:
            problems.append(f"{name}: a bucket policy")
        if "spaces_bucket_object" in text:
            problems.append(f"{name}: a bucket object (objects carry their own ACL)")
        if "cors_rule" in text or "spaces_bucket_cors" in text:
            problems.append(f"{name}: a CORS rule")
        if "digitalocean_spaces_key" in text:
            problems.append(f"{name}: an access key created in code (keys come from Doppler)")
        if re.search(r"public-read|authenticated-read|\"\*\"", text):
            problems.append(f"{name}: a public principal or ACL")
    return problems


# --- the golden file --------------------------------------------------------


def test_the_golden_file_is_well_formed_and_a_noop_plan_passes():
    g = golden()
    assert g["stack"] == "stacks/30-state"
    pnc.validate_golden(g)
    assert list(g["addresses"]) == [CALLED]
    assert pnc.check(noop_plan(g), g, False) == []


def test_the_golden_name_and_region_are_the_defaults_of_the_sources():
    spec = golden()["addresses"][CALLED]
    assert spec["type"] == "digitalocean_spaces_bucket"
    assert spec["force_new"] == {"name": "cah-tor1-state", "region": "tor1"}
    variables = (STACK / "variables.tf").read_text()
    region = re.search(r'variable "region" \{\n(.*?)\n\}\n', variables, re.DOTALL).group(1)
    assert re.search(r'(?m)^\s*default\s*=\s*"tor1"', region)


def test_the_guard_bites_on_an_added_a_missing_or_a_replaced_address():
    g = golden()
    plan = noop_plan(g)
    plan["resource_changes"].append(
        {
            "address": 'module.state_bucket[1].digitalocean_spaces_bucket.this',
            "mode": "managed",
            "type": "digitalocean_spaces_bucket",
            "change": {"actions": ["create"], "before": None, "after": {}, "after_unknown": {}},
        }
    )
    assert any("state_bucket[1]" in p for p in pnc.check(plan, g, False))
    gone = noop_plan(g)
    gone["resource_changes"] = []
    assert any(CALLED in p for p in pnc.check(gone, g, False))
    renamed = noop_plan(g)
    renamed["resource_changes"][0]["change"]["after"]["name"] = "cah-tor1-other"
    assert pnc.check(renamed, g, False)


# --- exactly one bucket, behind a flag that is off --------------------------


def test_the_module_holds_exactly_the_one_bucket_and_nothing_else():
    texts = [t for n, t in all_code().items() if n.startswith("modules/")]
    assert texts, "no module source collected"
    assert [b for t in texts for b in resource_blocks(t)] == [BUCKET]


def test_the_stack_declares_no_resource_and_calls_the_module_once_behind_the_flag():
    files = {n: t for n, t in all_code().items() if n.startswith("stacks/")}
    assert files, "no stack source collected"
    assert [b for t in files.values() for b in resource_blocks(t)] == []
    main = re.sub(r"\s+", " ", files["stacks/30-state/main.tf"])
    calls = re.findall(r'module "([^"]+)" \{', main)
    assert calls == ["state_bucket"]
    assert 'count = var.state_bucket_enabled ? 1 : 0' in main
    variables = (STACK / "variables.tf").read_text()
    flag = re.search(r'variable "state_bucket_enabled" \{\n(.*?)\n\}\n', variables, re.DOTALL).group(1)
    assert re.search(r"(?m)^\s*type\s*=\s*bool\s*$", flag)
    assert re.search(r"(?m)^\s*default\s*=\s*false\s*$", flag)


def test_the_count_is_on_the_module_call_not_on_the_costed_resource():
    # The cost gate refuses count and for_each on a costed resource.
    module_main = code(MODULE / "main.tf")
    assert not re.search(r"(?m)^\s*(count|for_each)\s*=", module_main)


# --- private, versioned, expiring, never public -----------------------------


def test_the_bucket_is_private_versioned_and_not_force_destroyable():
    text = code(MODULE / "main.tf")
    block = text[text.index('resource "digitalocean_spaces_bucket" "this"') :]
    assert re.search(r'(?m)^\s*acl\s*=\s*"private"\s*$', block)
    assert re.search(r"(?m)^\s*force_destroy\s*=\s*false\s*$", block)
    versioning = re.search(r"(?ms)^\s*versioning \{\n(.*?)\n\s*\}", block).group(1)
    assert re.search(r"(?m)^\s*enabled\s*=\s*true\s*$", versioning)
    assert "noncurrent_version_expiration" in block
    assert "days = var.noncurrent_version_days" in block
    # only noncurrent versions expire: no rule may expire the current version
    assert not re.search(r"(?m)^\s*expiration\s*\{", block)


def test_the_restore_window_defaults_to_90_days():
    text = (MODULE / "variables.tf").read_text()
    block = re.search(r'variable "noncurrent_version_days" \{\n(.*?)\n\}\n', text, re.DOTALL).group(1)
    assert re.search(r"(?m)^\s*default\s*=\s*90\s*$", block)


def test_nothing_makes_the_bucket_public_or_mints_a_key():
    files = all_code()
    assert len(files) >= 8, f"collected too few source files: {sorted(files)}"
    assert exposure_problems(files) == []


def test_the_exposure_guard_bites():
    clean = all_code()
    for needle, label in [
        ('acl = "public-read"', "ACL"),
        ('resource "digitalocean_spaces_bucket_policy" "p" {}', "bucket policy"),
        ('resource "digitalocean_spaces_key" "k" {}', "access key"),
        ("cors_rule {}", "CORS"),
        ('resource "digitalocean_spaces_bucket_object" "o" { acl = "private" }', "bucket object"),
        ('Principal = "*"', "public principal"),
    ]:
        mutated = dict(clean)
        mutated["modules/spaces-bucket/main.tf"] += "\n" + needle + "\n"
        problems = exposure_problems(mutated)
        assert problems, f"the guard missed: {label}"


# --- the cost wiring stays honest -------------------------------------------


def test_this_change_approves_no_money():
    approved = json.loads((ROOT / "docs/stages/approved.json").read_text())
    assert approved["current_phase"] != "stage-3"
    assert approved["phases"]["stage-3"]["status"] == "planned"
    assert approved["phases"]["stage-3"]["ceiling"] == 30.0
    assert approved["providers"]["digitalocean"]["approved_monthly_total"] == 12.0
    manifest = json.loads((STACK / "cost.json").read_text())
    assert manifest["stage"] == 3
    assert manifest["resources"] == []
