"""scripts/cost_raise.py: a dry-run-first helper for raising one phase's ceiling."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
import cost_raise

ROOT = Path(__file__).resolve().parents[1]


def repo(tmp_path):
    for rel in ("docs/stages/approved.json", "docs/cost-prices.json", "docs/cost-prices"):
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)
    for rel in ("stacks", "modules", ".spacelift"):
        if (ROOT / rel).exists():
            shutil.copytree(
                ROOT / rel, tmp_path / rel, ignore=shutil.ignore_patterns(".terraform")
            )
    return tmp_path


def raise_cmd(root, *extra):
    extra = extra if "--no-cascade" in extra else ("--cascade", *extra)
    extra = tuple(e for e in extra if e != "--no-cascade")
    return [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36",
        "--reason", "bigger droplet", "--decided", "2026-10-17", *extra,
    ]  # fmt: skip


def read(root):
    return json.loads((root / "docs/stages/approved.json").read_text())


def test_the_real_file_round_trips_through_render():
    text = (ROOT / "docs/stages/approved.json").read_text()
    assert cost_raise.render(json.loads(text)) == text


def test_a_raise_that_leaves_a_later_phase_lower_needs_cascade(tmp_path, capsys):
    root = repo(tmp_path)
    assert cost_raise.main(raise_cmd(root, "--no-cascade", "--write")) == 1
    assert "stage-4" in capsys.readouterr().err
    assert read(root)["phases"]["stage-3"]["ceiling"] == 30.0


def test_cascade_raises_later_phases_and_notes_why(tmp_path):
    root = repo(tmp_path)
    assert cost_raise.main(raise_cmd(root, "--write")) == 0
    phases = read(root)["phases"]
    assert phases["stage-4"]["ceiling"] == 36.0
    assert "together with stage-3" in phases["stage-4"]["reason"]
    assert phases["stage-4"]["decided"] == "2026-10-17"
    assert phases["stage-2"]["ceiling"] == 30.0
    assert phases["edge"]["ceiling"] == 36.0  # edge was 35, now raised with stage-3


def test_dry_run_prints_a_diff_and_writes_nothing(tmp_path, capsys):
    root = repo(tmp_path)
    before = (root / "docs/stages/approved.json").read_text()
    assert cost_raise.main(raise_cmd(root)) == 0
    out = capsys.readouterr().out
    assert '-      "ceiling": 30.0,' in out and '+      "ceiling": 36.0,' in out
    assert "bigger droplet" in out and "2026-10-17" in out
    assert "dry run" in out
    assert (root / "docs/stages/approved.json").read_text() == before


def test_write_edits_the_file_and_the_gate_still_passes(tmp_path, capsys):
    root = repo(tmp_path)
    assert cost_raise.main(raise_cmd(root, "--write")) == 0
    phase = read(root)["phases"]["stage-3"]
    assert (phase["ceiling"], phase["reason"], phase["decided"]) == (
        36.0, "bigger droplet", "2026-10-17",
    )  # fmt: skip
    assert phase["status"] == "planned"
    capsys.readouterr()
    assert cost_check.main(["--root", str(root)]) == 0


def test_a_provider_approval_is_never_touched(tmp_path):
    root = repo(tmp_path)
    before = read(root)["providers"]
    cost_raise.main(raise_cmd(root, "--write"))
    assert read(root)["providers"] == before


def test_make_current_moves_the_current_phase(tmp_path):
    root = repo(tmp_path)
    args = raise_cmd(root, "--make-current", "--write")
    args[args.index("stage-3")] = "stage-2"
    assert cost_raise.main(args) == 0
    doc = read(root)
    assert doc["current_phase"] == "stage-2"
    assert doc["phases"]["stage-2"]["status"] == "current"
    assert doc["phases"]["stage-1"]["status"] == "done"
    assert cost_check.phase_problems(doc) == []


def test_a_lower_ceiling_is_refused_without_lowers(tmp_path, capsys):
    root = repo(tmp_path)
    args = raise_cmd(root, "--write")
    args[args.index("36")] = "20"
    before = (root / "docs/stages/approved.json").read_text()
    assert cost_raise.main(args) == 1
    assert "lowers" in capsys.readouterr().err
    assert (root / "docs/stages/approved.json").read_text() == before


def test_a_lower_ceiling_passes_with_lowers(tmp_path):
    root = repo(tmp_path)
    args = raise_cmd(root, "--lowers", "--write")
    args[args.index("36")] = "20"
    assert cost_raise.main(args) == 0
    assert read(root)["phases"]["stage-3"]["lowers"] is True


def test_a_new_phase_is_added_after_the_named_one(tmp_path):
    root = repo(tmp_path)
    args = [
        "--root", str(root), "--phase", "mid", "--ceiling", "30", "--reason", "r",
        "--decided", "2026-10-17", "--after", "stage-1", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 0
    keys = list(read(root)["phases"])
    assert keys.index("mid") == keys.index("stage-1") + 1


def test_a_new_phase_with_no_after_is_appended(tmp_path):
    root = repo(tmp_path)
    args = [
        "--root", str(root), "--phase", "zeta", "--ceiling", "59", "--reason", "r",
        "--decided", "2026-10-17", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 0
    assert list(read(root)["phases"])[-1] == "zeta"


def test_raising_past_hard_max_is_refused(tmp_path, capsys):
    root = repo(tmp_path)
    path = root / "docs/stages/approved.json"
    doc = read(root)
    doc["hard_max"] = 60.0
    path.write_text(cost_raise.render(doc))
    args = raise_cmd(root, "--write")
    args[args.index("36")] = "70"
    assert cost_raise.main(args) == 1
    assert "hard_max" in capsys.readouterr().err
    assert "70" not in path.read_text()


def test_a_bad_date_or_empty_reason_is_refused(tmp_path, capsys):
    root = repo(tmp_path)
    args = raise_cmd(root)
    args[args.index("2026-10-17")] = "yesterday"
    assert cost_raise.main(args) == 1
    args = raise_cmd(root)
    args[args.index("bigger droplet")] = "  "
    assert cost_raise.main(args) == 1
    capsys.readouterr()


def test_a_nan_ceiling_is_refused(tmp_path):
    root = repo(tmp_path)
    args = raise_cmd(root)
    args[args.index("36")] = "nan"
    assert cost_raise.main(args) == 2


def test_a_legacy_file_has_to_be_migrated_first(tmp_path, capsys):
    root = repo(tmp_path)
    (root / "docs/stages/approved.json").write_text(
        json.dumps({"ceiling": 30.0, "providers": read(root)["providers"]})
    )
    assert cost_raise.main(raise_cmd(root)) == 1
    assert "migrate" in capsys.readouterr().err


def test_the_default_date_is_today(tmp_path, capsys):
    root = repo(tmp_path)
    args = raise_cmd(root)
    del args[args.index("--decided") : args.index("--decided") + 2]
    assert cost_raise.main(args) == 0
    assert "decided" in capsys.readouterr().out
