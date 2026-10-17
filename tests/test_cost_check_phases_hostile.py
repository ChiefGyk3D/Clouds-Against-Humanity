"""Hostile inputs for the per-phase ceilings and for scripts/cost_raise.py."""

import fcntl
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
import cost_raise

ROOT = Path(__file__).resolve().parents[1]


def phase(ceiling, status="planned", reason="because", decided="2026-10-10", **extra):
    return {
        "ceiling": ceiling,
        "reason": reason,
        "decided": decided,
        "status": status,
        **extra,
    }


def doc(**overrides):
    out = {
        "current_phase": "b",
        "hard_max": 100.0,
        "hard_max_reason": "test limit",
        "phases": {
            "a": phase(30.0, "done"),
            "b": phase(30.0, "current"),
            "c": phase(50.0),
            "d": phase(20.0, lowers=True),
        },
        "providers": {"digitalocean": {"approved_monthly_total": 12.0, "active": True}},
    }
    out.update(overrides)
    return out


def repo(tmp_path, mutate=None, raw=None):
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
    path = tmp_path / "docs/stages/approved.json"
    if mutate:
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data, indent=2) + "\n")
    if raw:
        path.write_text(raw(path.read_text()))
    return tmp_path


def gate(root, capsys, *extra):
    code = cost_check.main(["--root", str(root), *extra])
    return code, capsys.readouterr()


# (1) duplicate keys -----------------------------------------------------------


def test_parse_json_rejects_duplicate_keys_anywhere():
    for text in ('{"a": 1, "a": 2}', '{"x": {"a": 1, "a": 2}}', '[{"a": 1, "a": 1}]'):
        with pytest.raises(ValueError, match="duplicate key"):
            cost_check.parse_json(text)


def test_parse_json_rejects_nan_literals():
    with pytest.raises(ValueError):
        cost_check.parse_json('{"ceiling": NaN}')


@pytest.mark.parametrize(
    "old,new",
    [
        ('"current_phase": "stage-1",', '"current_phase": "stage-1",\n  "current_phase": "stage-3",'),
        ('"hard_max": 60.0,', '"hard_max": 60.0,\n  "hard_max": 6000.0,'),
        ('"status": "current"', '"status": "current",\n      "status": "done"'),
        ('"active": true', '"active": true,\n      "active": false'),
        ('"approved_monthly_total": 12.0', '"approved_monthly_total": 12.0,\n      "approved_monthly_total": 1.0'),
    ],
)
def test_a_duplicate_key_in_approved_json_fails_the_gate(tmp_path, capsys, old, new):
    root = repo(tmp_path, raw=lambda t: t.replace(old, new, 1))
    code, out = gate(root, capsys)
    assert code == 1 and "duplicate key" in out.err


def test_a_duplicate_key_in_a_manifest_or_price_table_fails(tmp_path, capsys):
    root = repo(tmp_path)
    manifest = root / "stacks/10-access/cost.json"
    manifest.write_text(manifest.read_text().replace("{", '{"stage": 1, "stage": 2,', 1))
    code, out = gate(root, capsys)
    assert code == 1 and "duplicate key" in out.err
    root2 = repo(tmp_path / "two")
    prices = root2 / "docs/cost-prices.json"
    prices.write_text(prices.read_text().replace("{", '{"retrieved": "x", "retrieved": "y",', 1))
    code, out = gate(root2, capsys)
    assert code == 1 and "duplicate key" in out.err


# (2) lifecycle ------------------------------------------------------------------


def test_done_phases_come_first_and_planned_phases_last():
    d = doc()
    d["phases"]["a"]["status"] = "planned"
    assert any("phase b" in p and "comes after" in p for p in cost_check.phase_problems(d))
    d = doc()
    d["phases"]["c"]["status"] = "done"
    assert any("phase c" in p and "comes after" in p for p in cost_check.phase_problems(d))


def test_the_ordered_lifecycle_passes():
    assert cost_check.phase_problems(doc()) == []


@pytest.mark.parametrize(
    "key,status",
    [("a", "current"), ("a", "planned"), ("b", "planned"), ("c", "done")],
)
def test_transitions_other_than_planned_current_done_are_refused(key, status):
    new = doc()
    new["phases"][key]["status"] = status
    assert cost_check.transition_problems(doc(), new)


def test_a_done_phase_may_not_change_or_vanish():
    new = doc()
    new["phases"]["a"]["ceiling"] = 99.0
    assert any("may not change" in p for p in cost_check.transition_problems(doc(), new))
    new = doc()
    del new["phases"]["a"]
    assert any("may not be removed" in p for p in cost_check.transition_problems(doc(), new))


def test_a_new_phase_may_not_start_done_but_may_start_planned():
    new = doc()
    new["phases"]["e"] = phase(50.0, "done")
    assert cost_check.transition_problems(doc(), new)
    new["phases"]["e"] = phase(50.0)
    assert cost_check.transition_problems(doc(), new) == []


def test_the_normal_step_planned_current_done_is_allowed():
    new = doc(current_phase="c")
    new["phases"]["b"]["status"] = "done"
    new["phases"]["c"]["status"] = "current"
    assert cost_check.transition_problems(doc(), new) == []


def test_base_approved_fails_a_reactivated_done_phase_and_shows_the_change(
    tmp_path, capsys
):
    base = tmp_path / "base.json"
    base.write_text((ROOT / "docs/stages/approved.json").read_text())

    def mutate(d):
        d["phases"]["stage-0"]["status"] = "current"
        d["phases"]["stage-0"]["ceiling"] = 55.0
        d["phases"]["stage-1"]["status"] = "done"
        d["current_phase"] = "stage-0"

    root = repo(tmp_path / "r", mutate)
    code, out = gate(root, capsys, "--base-approved", str(base))
    assert code == 1
    assert "EFFECTIVE CEILING CHANGED: phase stage-1 $30.00 -> phase stage-0 $55.00" in out.out
    assert "stage-0 is done and may not change" in out.err


def test_base_approved_passes_when_nothing_changed(tmp_path, capsys):
    base = tmp_path / "base.json"
    base.write_text((ROOT / "docs/stages/approved.json").read_text())
    code, out = gate(repo(tmp_path / "r"), capsys, "--base-approved", str(base))
    assert code == 0 and "EFFECTIVE" not in out.out


def test_cost_raise_refuses_to_reactivate_a_done_phase(tmp_path, capsys):
    root = repo(tmp_path)
    before = (root / "docs/stages/approved.json").read_text()
    args = [
        "--root", str(root), "--phase", "stage-0", "--ceiling", "55", "--reason", "r",
        "--decided", "2026-10-17", "--make-current", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert (root / "docs/stages/approved.json").read_text() == before
    assert "done" in capsys.readouterr().err


def test_cost_raise_refuses_to_edit_a_done_phase_ceiling(tmp_path, capsys):
    root = repo(tmp_path)
    args = [
        "--root", str(root), "--phase", "stage-0", "--ceiling", "55", "--reason", "r",
        "--decided", "2026-10-17",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert "may not change" in capsys.readouterr().err


def test_cost_raise_shows_old_and_new_effective_ceiling(tmp_path, capsys):
    root = repo(tmp_path)
    args = [
        "--root", str(root), "--phase", "stage-2", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--make-current", "--cascade",
    ]  # fmt: skip
    assert cost_raise.main(args) == 0
    assert "EFFECTIVE CEILING: phase stage-1 $30.00 -> phase stage-2 $36.00" in capsys.readouterr().out
    args.remove("--make-current")
    assert cost_raise.main(args) == 0
    assert "EFFECTIVE CEILING: unchanged, phase stage-1 $30.00" in capsys.readouterr().out


def test_cost_raise_make_current_may_not_skip_a_planned_phase(tmp_path, capsys):
    root = repo(tmp_path)
    args = [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--make-current", "--cascade",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert "stage-2" in capsys.readouterr().err


# (4) types, (5) decimals ---------------------------------------------------------


@pytest.mark.parametrize("bad", ["1e6", " 1000000 ", "30", "nan", True, None, [30], {}])
def test_ceiling_and_hard_max_must_be_json_numbers(bad):
    d = doc()
    d["phases"]["c"]["ceiling"] = bad
    assert any("phase c" in p and "ceiling" in p for p in cost_check.phase_problems(d))
    assert any("hard_max" in p for p in cost_check.phase_problems(doc(hard_max=bad)))


@pytest.mark.parametrize("bad", ["12", "1e1", " 12 ", True])
def test_approved_monthly_total_must_be_a_json_number(tmp_path, capsys, bad):
    root = repo(
        tmp_path, lambda d: d["providers"]["digitalocean"].update(approved_monthly_total=bad)
    )
    code, out = gate(root, capsys)
    assert code == 1 and "cost-check:" in out.err


def test_approved_site_figure_must_be_a_json_number():
    with pytest.raises(ValueError):
        cost_check.money("5", "site")


@pytest.mark.parametrize("bad", [29.999, 30.001, 0.001, 1e-7])
def test_more_than_two_decimals_is_refused(bad):
    d = doc()
    d["phases"]["c"]["ceiling"] = bad
    assert any("two decimal places" in p or "finite number" in p for p in cost_check.phase_problems(d))
    assert cost_check.phase_problems(doc(hard_max=bad))


def test_two_decimals_and_integers_pass():
    d = doc()
    d["phases"]["c"]["ceiling"] = 50.25
    d["phases"]["d"]["ceiling"] = 20
    assert cost_check.phase_problems(d) == []


def test_a_provider_approval_with_three_decimals_fails(tmp_path, capsys):
    root = repo(
        tmp_path,
        lambda d: d["providers"]["digitalocean"].update(approved_monthly_total=12.001),
    )
    assert gate(root, capsys)[0] == 1


def test_a_cent_below_the_previous_ceiling_is_a_decrease():
    d = doc()
    d["phases"]["c"]["ceiling"] = 29.99
    assert any("lowers" in p for p in cost_check.phase_problems(d))


# (6) hard_max required, (8) first phase lowers -------------------------------------


def test_hard_max_is_required_with_phases():
    d = doc()
    del d["hard_max"]
    assert any("hard_max is required" in p for p in cost_check.phase_problems(d))


def test_hard_max_needs_a_reason():
    for value in (None, "", "  ", 5):
        d = doc(hard_max_reason=value)
        assert any("hard_max_reason" in p for p in cost_check.phase_problems(d))
    d = doc()
    del d["hard_max_reason"]
    assert any("hard_max_reason" in p for p in cost_check.phase_problems(d))


def test_hard_max_still_uses_greater_than():
    d = doc(hard_max=50.0)
    assert cost_check.phase_problems(d) == []


def test_the_real_file_has_a_hard_max_above_every_phase():
    real = json.loads((ROOT / "docs/stages/approved.json").read_text())
    assert real["hard_max"] >= max(p["ceiling"] for p in real["phases"].values())
    assert real["hard_max_reason"].strip()


def test_the_first_phase_may_not_claim_lowers():
    d = doc()
    d["phases"]["a"]["lowers"] = True
    assert any("phase a" in p and "first phase" in p for p in cost_check.phase_problems(d))


# (7) readers of the ceiling ---------------------------------------------------------


def test_the_lessons_test_resolves_the_current_phase_not_a_top_level_ceiling():
    text = (ROOT / "tests/test_telemetry_lessons.py").read_text()
    assert "current_phase" in text
    assert '_APPROVED["ceiling"]' not in text


# (3) atomic, locked write ------------------------------------------------------------


def test_write_checked_refuses_a_stale_digest(tmp_path):
    target = tmp_path / "approved.json"
    target.write_text("one\n")
    stale = cost_raise.digest(b"one\n")
    target.write_text("two\n")
    with pytest.raises(cost_raise.Conflict):
        cost_raise.write_checked(target, "three\n", stale)
    assert target.read_text() == "two\n"
    assert [p.name for p in tmp_path.iterdir()] == ["approved.json"]


def test_write_checked_writes_atomically_and_keeps_the_mode(tmp_path):
    target = tmp_path / "approved.json"
    target.write_text("one\n")
    target.chmod(0o640)
    cost_raise.write_checked(target, "two\n", cost_raise.digest(b"one\n"))
    assert target.read_text() == "two\n"
    assert target.stat().st_mode & 0o777 == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["approved.json"]


def test_write_checked_holds_an_exclusive_directory_lock(tmp_path, monkeypatch):
    target = tmp_path / "approved.json"
    target.write_text("one\n")
    seen = {}
    real_replace = cost_raise.os.replace

    def probe(src, dst):
        fd = cost_raise.os.open(tmp_path, cost_raise.os.O_RDONLY)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                seen["locked"] = False
            except BlockingIOError:
                seen["locked"] = True
        finally:
            cost_raise.os.close(fd)
        real_replace(src, dst)

    monkeypatch.setattr(cost_raise.os, "replace", probe)
    cost_raise.write_checked(target, "two\n", cost_raise.digest(b"one\n"))
    assert seen == {"locked": True}


def test_a_failed_write_leaves_no_temp_file(tmp_path, monkeypatch):
    target = tmp_path / "approved.json"
    target.write_text("one\n")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(cost_raise.os, "replace", boom)
    with pytest.raises(OSError):
        cost_raise.write_checked(target, "two\n", cost_raise.digest(b"one\n"))
    assert [p.name for p in tmp_path.iterdir()] == ["approved.json"]
    assert target.read_text() == "one\n"


def test_a_concurrent_edit_between_read_and_write_is_not_overwritten(
    tmp_path, capsys, monkeypatch
):
    root = repo(tmp_path)
    path = root / "docs/stages/approved.json"
    real = cost_raise.gate_problems

    def edit_while_validating(gate, r, d):
        out = real(gate, r, d)
        other = json.loads(path.read_text())
        other["phases"]["stage-2"]["reason"] = "someone else edited this"
        path.write_text(cost_raise.render(other))
        return out

    monkeypatch.setattr(cost_raise, "gate_problems", edit_while_validating)
    args = [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--cascade", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert "changed since it was read" in capsys.readouterr().err
    final = json.loads(path.read_text())
    assert final["phases"]["stage-2"]["reason"] == "someone else edited this"
    assert final["phases"]["stage-3"]["ceiling"] == 30.0


# (9) cascade keeps a legitimate decrease ----------------------------------------------


def test_cascade_keeps_a_later_deliberate_decrease():
    base = doc()
    base["phases"] = {
        "a": phase(30.0, "current"),
        "b": phase(50.0),
        "c": phase(20.0, lowers=True, reason="cheaper host"),
    }
    base["current_phase"] = "a"
    new = cost_raise.propose(base, "a", 40.0, "r", "2026-10-17", cascade=True)
    assert new["phases"]["b"]["ceiling"] == 50.0
    assert new["phases"]["c"]["ceiling"] == 20.0 and new["phases"]["c"]["lowers"] is True
    assert cost_check.phase_problems(new) == []


def test_cascade_drops_lowers_that_became_stale():
    base = doc()
    base["phases"] = {"a": phase(30.0, "current"), "b": phase(20.0, lowers=True)}
    base["current_phase"] = "a"
    new = cost_raise.propose(base, "a", 10.0, "r", "2026-10-17", cascade=True)
    assert "lowers" not in new["phases"]["b"]
    assert cost_check.phase_problems(new) == []


def test_cascade_raises_a_quiet_decrease_and_notes_it():
    base = doc()
    base["phases"] = {"a": phase(30.0, "current"), "b": phase(30.0)}
    base["current_phase"] = "a"
    new = cost_raise.propose(base, "a", 40.0, "r", "2026-10-17", cascade=True)
    assert new["phases"]["b"]["ceiling"] == 40.0
    assert "together with a" in new["phases"]["b"]["reason"]


# (10) cost_raise runs every gate check before writing ------------------------------------


def test_cost_raise_refuses_to_write_when_an_unapproved_resource_exists(tmp_path, capsys):
    root = repo(tmp_path)
    (root / "stacks/10-access/extra.tf").write_text(
        'resource "digitalocean_loadbalancer" "x" {}\n'
    )
    path = root / "docs/stages/approved.json"
    before = path.read_text()
    args = [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--cascade", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert path.read_text() == before
    assert "digitalocean_loadbalancer" in capsys.readouterr().err


def test_cost_raise_refuses_to_write_when_the_structure_is_wrong(tmp_path, capsys):
    root = repo(tmp_path)
    (root / "stacks/not-a-stack").mkdir()
    path = root / "docs/stages/approved.json"
    before = path.read_text()
    args = [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--cascade", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert path.read_text() == before


def test_cost_raise_refuses_an_approved_file_with_duplicate_keys(tmp_path, capsys):
    root = repo(
        tmp_path,
        raw=lambda t: t.replace('"hard_max": 60.0,', '"hard_max": 60.0,\n  "hard_max": 90.0,'),
    )
    args = [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1
    assert "duplicate key" in capsys.readouterr().err
