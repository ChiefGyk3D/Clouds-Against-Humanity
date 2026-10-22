# SPDX-License-Identifier: Apache-2.0
"""Option L1: the cost gate's narrow exemption for the top-level labs/ directory.

labs/ is still parsed for syntax, but the type allowlist, count/for_each and
module-source rules do not apply there. stacks/ and modules/ are unchanged.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
from test_cost_check import droplet, make_repo

ROOT = Path(__file__).resolve().parent.parent
COSTED = 'resource "digitalocean_droplet" "lab" {}\n'
VOLUME = 'resource "digitalocean_volume" "v" {}\n'
LOOPED = 'resource "digitalocean_droplet" "lab" {\n  count = 2\n}\n'


def problems_for(tmp_path, files):
    root = make_repo(tmp_path, [droplet()], tf_files=files)
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    problems, _ = cost_check.gate_problems(root, approved)
    return problems


def mentions(problems, needle):
    return any(needle in p for p in problems)


def test_costed_type_under_labs_passes(tmp_path):
    files = {"labs/vm/main.tf": COSTED, "labs/vm/vol.tf": VOLUME, "labs/vm/loop.tf": LOOPED}
    assert problems_for(tmp_path, files) == []


@pytest.mark.parametrize("where", ["stacks/10-access/extra.tf", "modules/other/main.tf"])
def test_same_file_outside_labs_fails(tmp_path, where):
    problems = problems_for(tmp_path, {where: VOLUME})
    assert mentions(problems, where)


@pytest.mark.parametrize("where", ["stacks/10-access/loop.tf", "modules/ok/main.tf"])
def test_count_on_costed_resource_outside_labs_fails(tmp_path, where):
    problems = problems_for(tmp_path, {where: LOOPED})
    assert mentions(problems, "uses count")


def test_syntax_error_under_labs_fails(tmp_path):
    problems = problems_for(tmp_path, {"labs/vm/bad.tf": 'resource "x" "y" {\n  a = "unterminated\n'})
    assert mentions(problems, "labs/vm/bad.tf") and mentions(problems, "unreadable HCL")


def test_tf_json_under_labs_still_refused(tmp_path):
    problems = problems_for(tmp_path, {"labs/vm/main.tf.json": "{}"})
    assert mentions(problems, "labs/vm/main.tf.json")


@pytest.mark.parametrize(
    "where",
    [
        "Labs/vm/main.tf",
        "LABS/vm/main.tf",
        "labs2/vm/main.tf",
        "lab/vm/main.tf",
        "docs/labs/vm/main.tf",
        "stacks/labs/main.tf",
        "modules/labs/main.tf",
        "stacks/10-access/labs/main.tf",
    ],
)
def test_lookalike_paths_are_not_exempt(tmp_path, where):
    root = make_repo(tmp_path, [droplet()], tf_files={where: VOLUME})
    assert not cost_check.lab_file(root, where)
    found = cost_check.uncosted_sources(root, {})
    assert mentions(found, where)


@pytest.mark.parametrize(
    "rel",
    ["labs/../stacks/10-access/x.tf", "labs/a/../../modules/x.tf", "/etc/x.tf", "labs", "labs/"],
)
def test_traversal_and_bare_paths_are_not_exempt(tmp_path, rel):
    root = make_repo(tmp_path, [droplet()])
    (root / "labs").mkdir()
    assert not cost_check.lab_file(root, rel)


def test_real_lab_file_is_exempt(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={"labs/a/b/main.tf": COSTED})
    assert cost_check.lab_file(root, "labs/a/b/main.tf")


def test_symlink_from_labs_into_stacks_is_not_exempt(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={"stacks/10-access/extra.tf": VOLUME})
    (root / "labs").mkdir()
    (root / "labs/link").symlink_to(root / "stacks/10-access", target_is_directory=True)
    assert not cost_check.lab_file(root, "labs/link/extra.tf")
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    problems, _ = cost_check.gate_problems(root, approved)
    assert mentions(problems, "labs/link: symlinked directory is refused")


def test_symlinked_file_under_labs_is_not_exempt(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={"stacks/10-access/extra.tf": VOLUME})
    (root / "labs").mkdir()
    (root / "labs/x.tf").symlink_to(root / "stacks/10-access/extra.tf")
    assert not cost_check.lab_file(root, "labs/x.tf")
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    problems, _ = cost_check.gate_problems(root, approved)
    assert mentions(problems, "labs/x.tf: symlinked OpenTofu file is refused")


def test_symlinked_labs_directory_is_not_exempt(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={"stacks/10-access/extra.tf": VOLUME})
    os.symlink(root / "stacks/10-access", root / "labs", target_is_directory=True)
    assert not cost_check.lab_file(root, "labs/extra.tf")
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    problems, _ = cost_check.gate_problems(root, approved)
    assert mentions(problems, "labs: symlinked directory is refused")


def labs_registration_problems(approved, spacelift_dir, root):
    """Every way labs/ could be approved or handed to Spacelift."""
    found = []
    for provider, entry in approved["providers"].items():
        for kind, files in entry.get("allowed_sources", {}).items():
            for f in files:
                if "labs" in [part.lower() for part in Path(f).parts]:
                    found.append(f"approved.json {provider} {kind}: {f}")
    for path in sorted(p for p in Path(spacelift_dir).rglob("*") if p.is_file()):
        text = path.read_text(encoding="utf-8").lower()
        if "labs/" in text or "/labs" in text:
            found.append(f"{path.name} refers to labs/")
    config = Path(spacelift_dir, "config.yml")
    if config.exists():
        import yaml

        loaded = yaml.safe_load(config.read_text(encoding="utf-8"))
        ids = cost_check.manifest_ids(root)
        for sid in loaded["stacks"]:
            for manifest in ids.get(sid, []):
                if str(manifest).startswith("labs/"):
                    found.append(f"stack {sid} is backed by {manifest}")
    return found


def test_nothing_under_labs_is_approved_or_a_spacelift_stack():
    """The exemption is not an approval and Spacelift never applies labs/."""
    approved = json.loads((ROOT / "docs/stages/approved.json").read_text())
    assert labs_registration_problems(approved, ROOT / ".spacelift", ROOT) == []


def test_guard_catches_allowed_source_and_spacelift_reference(tmp_path):
    approved = {
        "providers": {"digitalocean": {"allowed_sources": {"digitalocean_droplet": ["Labs/vm/main.tf"]}}}
    }
    sl = tmp_path / ".spacelift"
    sl.mkdir()
    (sl / "config.yml").write_text("stacks:\n  cah-x:\n    project_root: labs/vm\n")
    found = labs_registration_problems(approved, sl, tmp_path)
    assert any("approved.json" in f for f in found)
    assert any("refers to labs/" in f for f in found)
