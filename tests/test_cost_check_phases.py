"""Per-phase cost ceilings in docs/stages/approved.json."""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check

ROOT = Path(__file__).resolve().parents[1]


def phase(ceiling, status="planned", reason="because", decided="2026-10-10", **extra):
    return {
        "ceiling": ceiling,
        "reason": reason,
        "decided": decided,
        "status": status,
        **extra,
    }


def approved(**overrides):
    out = {
        "stage": 1,
        "current_phase": "stage-1",
        "hard_max": 100.0,
        "hard_max_reason": "test limit",
        "phases": {
            "stage-0": phase(30.0, "done"),
            "stage-1": phase(30.0, "current"),
            "stage-3": phase(36.0),
        },
        "providers": {"digitalocean": {"approved_monthly_total": 12.0, "active": True}},
    }
    out.update(overrides)
    return out


def problems(doc):
    return cost_check.phase_problems(doc)


def test_a_valid_phase_map_has_no_problems():
    assert problems(approved()) == []


def test_current_ceiling_comes_from_the_current_phase():
    doc = approved()
    assert cost_check.current_ceiling(doc) == ("stage-1", 30.0, "because")
    doc["phases"]["stage-1"]["status"] = "done"
    doc["phases"]["stage-3"]["status"] = "current"
    doc["current_phase"] = "stage-3"
    assert cost_check.current_ceiling(doc)[:2] == ("stage-3", 36.0)


def test_legacy_top_level_ceiling_is_read_when_phases_is_absent():
    doc = {"ceiling": 30.0, "providers": {}}
    assert cost_check.current_ceiling(doc)[:2] == ("legacy", 30.0)
    assert problems(doc) == []


def test_legacy_ceiling_beside_phases_is_refused():
    doc = approved(ceiling=30.0)
    assert any("top-level ceiling" in p for p in problems(doc))


def test_no_ceiling_at_all_is_an_error():
    with pytest.raises((ValueError, KeyError)):
        cost_check.current_ceiling({"providers": {}})


def test_current_phase_must_exist():
    doc = approved(current_phase="stage-9")
    assert any("current_phase stage-9 is not in phases" in p for p in problems(doc))


def test_current_phase_missing_is_refused():
    doc = approved()
    del doc["current_phase"]
    assert any("current_phase" in p for p in problems(doc))


def test_exactly_one_phase_is_current():
    doc = approved()
    doc["phases"]["stage-3"]["status"] = "current"
    assert any("exactly one phase" in p for p in problems(doc))
    doc = approved()
    doc["phases"]["stage-1"]["status"] = "planned"
    assert any("exactly one phase" in p for p in problems(doc))


def test_the_current_status_must_be_the_current_phase():
    doc = approved()
    doc["phases"]["stage-1"]["status"] = "done"
    doc["phases"]["stage-3"]["status"] = "current"
    assert any(
        "status current but current_phase is stage-1" in p for p in problems(doc)
    )


@pytest.mark.parametrize(
    "bad", [-1, "nan", float("nan"), float("inf"), "x", None, True]
)
def test_a_bad_ceiling_is_refused(bad):
    doc = approved()
    doc["phases"]["stage-0"]["ceiling"] = bad  # first phase: no neighbour rule applies
    assert any("stage-0" in p and "must be a finite number" in p for p in problems(doc))


@pytest.mark.parametrize("bad", ["", "   ", None, 5])
def test_a_phase_needs_a_reason(bad):
    doc = approved()
    doc["phases"]["stage-3"]["reason"] = bad
    assert any("stage-3" in p and "reason" in p for p in problems(doc))


@pytest.mark.parametrize(
    "bad", ["", "2026-13-01", "2026-02-30", "20261010", "10/10/2026", None, 20261010]
)
def test_a_phase_needs_a_valid_date(bad):
    doc = approved()
    doc["phases"]["stage-3"]["decided"] = bad
    assert any("stage-3" in p and "decided" in p for p in problems(doc))


def test_a_phase_needs_a_known_status():
    doc = approved()
    doc["phases"]["stage-3"]["status"] = "maybe"
    assert any("stage-3" in p and "status" in p for p in problems(doc))


def test_a_phase_that_is_not_an_object_is_refused():
    doc = approved()
    doc["phases"]["stage-3"] = 36
    assert any("stage-3" in p for p in problems(doc))


def test_an_empty_phase_map_is_refused():
    assert any("phases" in p for p in problems(approved(phases={})))


def test_a_bad_phase_id_is_refused():
    doc = approved()
    doc["phases"]["Stage 3!"] = phase(40.0)
    assert any("phase id" in p for p in problems(doc))


def test_ceilings_may_rise_and_stay_equal():
    doc = approved()
    doc["phases"]["stage-3"]["ceiling"] = 30.0
    assert problems(doc) == []
    doc["phases"]["stage-3"]["ceiling"] = 99.0
    assert problems(doc) == []
    assert problems(approved(hard_max=98.0)) == []  # 36 < 98


def test_a_quiet_decrease_is_refused():
    doc = approved()
    doc["phases"]["stage-3"]["ceiling"] = 25.0
    assert any("stage-3" in p and "lowers" in p for p in problems(doc))


def test_an_explicit_decrease_passes():
    doc = approved()
    doc["phases"]["stage-3"] = phase(25.0, lowers=True, reason="cheaper host chosen")
    assert problems(doc) == []


def test_lowers_without_a_decrease_is_refused():
    doc = approved()
    doc["phases"]["stage-3"]["lowers"] = True
    assert any("lowers" in p and "does not" in p for p in problems(doc))


@pytest.mark.parametrize("flag", ["yes", 1, "true"])
def test_lowers_must_be_a_real_boolean(flag):
    doc = approved()
    doc["phases"]["stage-3"] = phase(25.0, lowers=flag)
    assert any("lowers" in p for p in problems(doc))


def test_hard_max_caps_every_phase():
    doc = approved(hard_max=40.0)
    assert problems(doc) == []
    doc["phases"]["stage-3"]["ceiling"] = 40.01
    assert any("hard_max" in p and "stage-3" in p for p in problems(doc))


def test_hard_max_at_the_limit_passes_and_a_bad_one_fails():
    assert problems(approved(hard_max=36.0)) == []
    for bad in ("nan", -1, "x", True):
        assert any("hard_max" in p for p in problems(approved(hard_max=bad)))


def test_hard_max_also_caps_a_legacy_ceiling():
    doc = {"ceiling": 30.0, "hard_max": 20.0, "providers": {}}
    assert any("hard_max" in p for p in problems(doc))


# --- the gate itself ---------------------------------------------------------


def test_approvals_are_checked_against_the_current_phase_ceiling():
    doc = approved()
    doc["providers"]["digitalocean"]["approved_monthly_total"] = 33.0
    got = cost_check.approval_problems(doc, {})
    assert any("above the ceiling $30.00" in p for p in got)
    doc["phases"]["stage-1"]["status"] = "done"
    doc["phases"]["stage-3"]["status"] = "current"
    doc["current_phase"] = "stage-3"
    assert not any("ceiling" in p for p in cost_check.approval_problems(doc, {}))


def test_the_active_sum_uses_the_current_phase_ceiling():
    doc = approved()
    doc["providers"]["aws"] = {"approved_monthly_total": 21.0, "active": True}
    got = cost_check.approval_problems(doc, {})
    assert any("add up to $33.00, above the shared ceiling $30.00" in p for p in got)


def test_phase_problems_flow_through_approval_problems():
    got = cost_check.approval_problems(approved(current_phase="nope"), {})
    assert any("current_phase nope" in p for p in got)


def test_the_real_file_is_valid_and_keeps_todays_behaviour():
    doc = json.loads((ROOT / "docs/stages/approved.json").read_text())
    assert "ceiling" not in doc
    assert problems(doc) == []
    pid, ceiling, _ = cost_check.current_ceiling(doc)
    assert (pid, ceiling) == ("stage-1", 30.0)
    assert doc["providers"]["digitalocean"]["active"] is True
    assert doc["providers"]["aws"]["active"] is False


def run_main(root, capsys):
    code = cost_check.main(["--root", str(root)])
    return code, capsys.readouterr()


def copy_real_repo(tmp_path, mutate=None):
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
    if mutate:
        path = tmp_path / "docs/stages/approved.json"
        doc = json.loads(path.read_text())
        mutate(doc)
        path.write_text(json.dumps(doc))
    return tmp_path


def test_the_real_repo_passes_and_names_the_phase(tmp_path, capsys):
    code, out = run_main(copy_real_repo(tmp_path), capsys)
    assert code == 0, out.err
    assert "cost-check: phase stage-1 ceiling $30.00 (reason: " in out.out
    assert "shared ceiling $" not in out.out


def test_main_fails_on_a_quiet_decrease(tmp_path, capsys):
    def mutate(doc):
        doc["phases"]["stage-3"]["ceiling"] = 1.0

    code, out = run_main(copy_real_repo(tmp_path, mutate), capsys)
    assert code == 1 and "lowers" in out.err


def test_main_fails_when_the_current_phase_is_missing(tmp_path, capsys):
    root = copy_real_repo(tmp_path, lambda d: d.update(current_phase="gone"))
    code, out = run_main(root, capsys)
    assert code == 1 and "current_phase gone" in out.err


def test_main_fails_when_hard_max_is_below_a_ceiling(tmp_path, capsys):
    root = copy_real_repo(tmp_path, lambda d: d.update(hard_max=10.0))
    code, out = run_main(root, capsys)
    assert code == 1 and "hard_max" in out.err


def test_raising_the_current_ceiling_lets_a_bigger_approval_through(tmp_path, capsys):
    def mutate(doc):
        for ph in doc["phases"].values():
            ph["ceiling"] = max(ph["ceiling"], 50.0)
        doc["providers"]["digitalocean"]["approved_monthly_total"] = 40.0

    code, out = run_main(copy_real_repo(tmp_path, mutate), capsys)
    assert code == 0, out.err
    assert "ceiling $50.00" in out.out
