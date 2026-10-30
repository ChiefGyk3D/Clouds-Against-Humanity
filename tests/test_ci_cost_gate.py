"""scripts/ci_cost_gate.sh and the round-two hardening of the phase lifecycle."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
import cost_raise

ROOT = Path(__file__).resolve().parents[1]
# Tests that need a known lifecycle state (stage-1 current, stage-2 planned) use a frozen
# copy of approved.json, so advancing the real file's current phase does not break them.
FIXTURE_STAGE1 = ROOT / "tests/fixtures/approved_stage1_current.json"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def copy_repo(dest):
    for rel in ("docs/stages/approved.json", "docs/cost-prices.json", "docs/cost-prices"):
        src, dst = ROOT / rel, dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)
    shutil.copy(FIXTURE_STAGE1, dest / "docs/stages/approved.json")
    for rel in ("stacks", "modules", ".spacelift"):
        if (ROOT / rel).exists():
            shutil.copytree(
                ROOT / rel, dest / rel, ignore=shutil.ignore_patterns(".terraform")
            )
    (dest / "scripts").mkdir(exist_ok=True)
    for name in ("cost_check.py", "ci_cost_gate.sh"):
        shutil.copy(ROOT / "scripts" / name, dest / "scripts" / name)


def sh(*cmd, cwd, env=None, check=True):
    full = {**os.environ, **GIT_ENV, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, env=full, capture_output=True, text=True, check=check)


@pytest.fixture
def clones(tmp_path):
    """(base repo = the remote, pr = a clone of it)."""
    base = tmp_path / "base"
    base.mkdir()
    copy_repo(base)
    sh("git", "init", "-q", "-b", "main", cwd=base)
    sh("git", "add", "-A", cwd=base)
    sh("git", "commit", "-q", "-m", "base", cwd=base)
    pr = tmp_path / "pr"
    sh("git", "clone", "-q", "--depth=1", f"file://{base}", str(pr), cwd=tmp_path)
    return base, pr


def run_gate(pr, **env):
    full = {"PYTHON": sys.executable, "GITHUB_EVENT_NAME": "pull_request", "GITHUB_BASE_REF": "main"}
    full.update(env)
    return sh("bash", "scripts/ci_cost_gate.sh", cwd=pr, env=full, check=False)


def edit_approved(pr, mutate):
    path = pr / "docs/stages/approved.json"
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data, indent=2) + "\n")


def test_an_unchanged_pull_request_passes_and_names_the_base(clones):
    _, pr = clones
    out = run_gate(pr)
    assert out.returncode == 0, out.stderr
    assert "comparing with main" in out.stdout


def test_a_pull_request_that_raises_the_effective_ceiling_is_flagged(clones):
    _, pr = clones

    def mutate(d):
        d["phases"]["stage-2"]["status"] = "current"
        d["phases"]["stage-1"]["status"] = "done"
        d["current_phase"] = "stage-2"
        d["phases"]["stage-2"]["ceiling"] = 36.0
        for later in ("stage-3", "stage-4", "aws-twin", "edge", "second-site", "learner-soc"):
            d["phases"][later]["ceiling"] = max(d["phases"][later]["ceiling"], 36.0)

    edit_approved(pr, mutate)
    out = run_gate(pr)
    assert out.returncode == 0, out.stderr
    assert "EFFECTIVE CEILING CHANGED: phase stage-1 $30.00 -> phase stage-2 $36.00" in out.stdout


def test_deleting_the_current_phase_while_raising_later_ones_fails(clones):
    _, pr = clones

    def mutate(d):
        del d["phases"]["stage-1"]
        d["phases"]["stage-2"]["status"] = "current"
        d["current_phase"] = "stage-2"
        for key in ("stage-2", "stage-3", "stage-4", "aws-twin", "edge", "second-site"):
            d["phases"][key]["ceiling"] = 60.0

    edit_approved(pr, mutate)
    out = run_gate(pr)
    assert out.returncode == 1
    assert "stage-1 (current) may not be removed" in out.stderr
    assert "EFFECTIVE CEILING CHANGED: phase stage-1 $30.00 -> phase stage-2 $60.00" in out.stdout


def test_a_planted_done_phase_fails_with_and_without_a_base(clones):
    _, pr = clones

    def mutate(d):
        phases = {}
        for key, value in d["phases"].items():
            if key == "stage-1":
                phases["reserve"] = {
                    "ceiling": 60.0, "reason": "reserve", "decided": "2026-10-10", "status": "done",
                }  # fmt: skip
                value["lowers"] = True
            phases[key] = value
        d["phases"] = phases

    edit_approved(pr, mutate)
    data = json.loads((pr / "docs/stages/approved.json").read_text())
    assert any("above the current ceiling" in p for p in cost_check.phase_problems(data))
    out = run_gate(pr)
    assert out.returncode == 1


def test_a_fetch_failure_fails_closed(clones):
    _, pr = clones
    out = run_gate(pr, CAH_BASE_REMOTE="no-such-remote")
    assert out.returncode == 1 and "FAIL: could not fetch" in out.stderr


def test_a_pull_request_without_a_base_ref_fails_closed(clones):
    _, pr = clones
    out = run_gate(pr, GITHUB_BASE_REF="")
    assert out.returncode == 1 and "GITHUB_BASE_REF" in out.stderr


def test_a_base_without_the_file_fails_closed(clones):
    base, pr = clones
    sh("git", "rm", "-q", "docs/stages/approved.json", cwd=base)
    sh("git", "commit", "-q", "-m", "drop", cwd=base)
    out = run_gate(pr)
    assert out.returncode == 1 and "has no docs/stages/approved.json" in out.stderr


def test_other_events_run_the_plain_gate_and_say_why(clones):
    _, pr = clones
    out = run_gate(pr, GITHUB_EVENT_NAME="push", GITHUB_BASE_REF="")
    assert out.returncode == 0, out.stderr
    assert "lifecycle check skipped" in out.stdout


def test_other_events_still_fail_a_bad_file(clones):
    _, pr = clones
    edit_approved(pr, lambda d: d.update(current_phase="gone"))
    assert run_gate(pr, GITHUB_EVENT_NAME="push").returncode == 1


def test_ci_runs_this_script_not_the_bare_gate():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    line = next(x for x in text.splitlines() if "test-command:" in x)
    assert "bash scripts/ci_cost_gate.sh" in line
    assert "scripts/cost_check.py" not in line


# --- the base-aware rules, in process ---------------------------------------------


def real():
    return json.loads(FIXTURE_STAGE1.read_text())


@pytest.mark.parametrize("key", ["stage-0", "stage-1", "stage-2", "learner-soc"])
def test_no_base_phase_of_any_status_may_be_removed(key):
    new = real()
    del new["phases"][key]
    assert any(f"phase {key}" in p and "may not be removed" in p for p in cost_check.transition_problems(real(), new))


def test_the_base_current_phase_may_only_stay_current_or_become_done():
    for bad in ("planned",):
        new = real()
        new["phases"]["stage-1"]["status"] = bad
        assert cost_check.transition_problems(real(), new)
    new = real()
    new["phases"]["stage-1"]["status"] = "done"
    new["phases"]["stage-2"]["status"] = "current"
    new["current_phase"] = "stage-2"
    assert cost_check.transition_problems(real(), new) == []


def test_a_done_phase_above_the_live_ceiling_fails_on_one_file():
    d = real()
    d["phases"]["stage-0"]["ceiling"] = 31.0
    assert any("stage-0: done at $31.00" in p for p in cost_check.phase_problems(d))


def test_a_done_phase_at_or_below_the_live_ceiling_is_fine():
    assert cost_check.phase_problems(real()) == []


# --- huge integers ----------------------------------------------------------------


@pytest.mark.parametrize("bad", [10**400, -(10**400)])
def test_a_huge_integer_is_a_controlled_rejection(bad):
    with pytest.raises(ValueError):
        cost_check.money(bad, "x")
    with pytest.raises(ValueError):
        cost_check.num(bad, "x")
    d = real()
    d["phases"]["stage-3"]["ceiling"] = bad
    assert any("stage-3" in p for p in cost_check.phase_problems(d))
    assert any("hard_max" in p for p in cost_check.phase_problems({**real(), "hard_max": bad}))


def test_a_huge_integer_approval_fails_the_gate_without_a_traceback(tmp_path, capsys):
    copy_repo(tmp_path)
    path = tmp_path / "docs/stages/approved.json"
    text = path.read_text().replace('"approved_monthly_total": 12.0', '"approved_monthly_total": 1' + "0" * 400)
    path.write_text(text)
    code = cost_check.main(["--root", str(tmp_path)])
    assert code == 1
    assert "Traceback" not in capsys.readouterr().err


def test_cost_raise_survives_a_huge_integer_in_the_file(tmp_path, capsys):
    copy_repo(tmp_path)
    path = tmp_path / "docs/stages/approved.json"
    path.write_text(path.read_text().replace('"approved_monthly_total": 12.0', '"approved_monthly_total": 1' + "0" * 400))
    args = [
        "--root", str(tmp_path), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--cascade", "--write",
    ]  # fmt: skip
    assert cost_raise.main(args) == 1


# --- cost_raise holds the lock across validation and rechecks every input ----------------


def args_for(root):
    return [
        "--root", str(root), "--phase", "stage-3", "--ceiling", "36", "--reason", "r",
        "--decided", "2026-10-17", "--cascade", "--write",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "rel,payload",
    [
        ("stacks/10-access/cost.json", None),
        ("docs/cost-prices.json", None),
        ("stacks/10-access/zz.tf", "# new\n"),
        (".spacelift/config.yml", None),
    ],
)
def test_a_gate_input_changed_during_validation_blocks_the_write(
    tmp_path, capsys, monkeypatch, rel, payload
):
    copy_repo(tmp_path)
    approved = tmp_path / "docs/stages/approved.json"
    before = approved.read_text()
    real_gate = cost_raise.gate_problems

    def touch_while_validating(gate, root, doc):
        out = real_gate(gate, root, doc)
        target = root / rel
        if payload is None:
            target.write_text(target.read_text() + "\n")
        else:
            target.write_text(payload)
        return out

    monkeypatch.setattr(cost_raise, "gate_problems", touch_while_validating)
    assert cost_raise.main(args_for(tmp_path)) == 1
    assert "changed while the change was being checked" in capsys.readouterr().err
    assert approved.read_text() == before


def test_the_directory_lock_is_held_during_validation(tmp_path, monkeypatch):
    import fcntl

    copy_repo(tmp_path)
    real_gate = cost_raise.gate_problems
    seen = {}

    def probe(gate, root, doc):
        fd = os.open(root / "docs/stages", os.O_RDONLY)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                seen["held"] = False
            except BlockingIOError:
                seen["held"] = True
        finally:
            os.close(fd)
        return real_gate(gate, root, doc)

    monkeypatch.setattr(cost_raise, "gate_problems", probe)
    assert cost_raise.main(args_for(tmp_path)) == 0
    assert seen == {"held": True}


def test_a_dry_run_does_not_take_the_lock(tmp_path, monkeypatch):
    copy_repo(tmp_path)
    monkeypatch.setattr(
        cost_raise, "locked", lambda d: (_ for _ in ()).throw(AssertionError("locked"))
    )
    args = args_for(tmp_path)
    args.remove("--write")
    assert cost_raise.main(args) == 0


def test_inputs_digest_changes_with_any_gate_input(tmp_path):
    copy_repo(tmp_path)
    first = cost_raise.inputs_digest(tmp_path)
    assert cost_raise.inputs_digest(tmp_path) == first
    (tmp_path / "modules/zz.tf").write_text("x\n")
    assert cost_raise.inputs_digest(tmp_path) != first
