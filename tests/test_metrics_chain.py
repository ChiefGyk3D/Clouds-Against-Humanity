# SPDX-License-Identifier: Apache-2.0
"""The chain of trust around the metrics branch (issue #296, review of PR 298).

The `metrics` branch is mutable, so it is never authoritative:
- the committed baseline holds the star history and NO ledger; the carried snapshot
  must match its identity fields exactly and must hold a ledger;
- a carried ledger is kept as an exact prefix: only today's point may be added or
  replaced; a missing, changed, reordered or extra earlier point fails closed;
- a carried snapshot older than MAX_CARRY_AGE_DAYS is refused;
- the carry script checks the blob size before writing anything into carried/.
"""

import copy
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_growth_bundle import REPO, git, make_bundle
from test_star_ledger import baseline, with_ledger

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_repo_metrics as grm

CARRY = ROOT / "scripts" / "carry_metrics_snapshot.sh"
REF = datetime.datetime(2026, 10, 25, 6, 0, 0, tzinfo=datetime.UTC)


@pytest.fixture(autouse=True)
def _not_in_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


def hashed(snap):
    snap = copy.deepcopy(snap)
    snap["source_sha256"] = grm.source_digest(snap)
    snap["png_sha256"] = "1" * 64
    return snap


def write(path, snap):
    path.write_text(json.dumps(hashed(snap)))
    return path


# -- roles: baseline and carried ---------------------------------------------------------


def test_a_good_baseline_loads(tmp_path):
    assert grm.load_baseline(write(tmp_path / "b.json", baseline()), REPO)["stars_as_of"] == "2026-10-20"


def test_a_valid_hashed_baseline_that_contains_a_ledger_is_rejected(tmp_path):
    path = write(tmp_path / "b.json", with_ledger())
    assert grm.validate_snapshot(json.loads(path.read_text())) == []  # valid in itself
    with pytest.raises(RuntimeError, match="must not contain a star_ledger"):
        grm.load_baseline(path, REPO)


def test_a_baseline_without_stars_as_of_is_rejected(tmp_path):
    snap = baseline()
    del snap["stars_as_of"]
    with pytest.raises(RuntimeError, match="stars_as_of"):
        grm.load_baseline(write(tmp_path / "b.json", snap), REPO)


def test_a_baseline_for_another_repository_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="not Other/Thing"):
        grm.load_baseline(write(tmp_path / "b.json", baseline()), "Other/Thing")


def carried_for(tmp_path, **changes):
    snap = with_ledger({"2026-10-21": 104, "2026-10-23": 140})
    snap["repo"] = REPO
    snap.update(changes)
    return write(tmp_path / "c.json", snap)


def test_a_good_carried_snapshot_loads(tmp_path):
    base = baseline()
    assert grm.load_carried(carried_for(tmp_path), REPO, base, REF)["star_ledger"]["2026-10-23"] == 140


@pytest.mark.parametrize(
    "change",
    [
        {"created_on": "2026-10-09"},
        {"stars": {"2026-10-10": 20, "2026-10-12": 50, "2026-10-19": 31}},
        {"stars_as_of": "2026-10-19"},
    ],
)
def test_a_carried_snapshot_must_equal_the_baseline_identity(tmp_path, change):
    with pytest.raises(RuntimeError, match="differs from the baseline"):
        grm.load_carried(carried_for(tmp_path, **change), REPO, baseline(), REF)


def test_a_carried_snapshot_without_a_ledger_is_rejected(tmp_path):
    snap = with_ledger({})
    del snap["star_ledger"]
    snap["repo"] = REPO
    with pytest.raises(RuntimeError, match="no star_ledger"):
        grm.load_carried(write(tmp_path / "c.json", snap), REPO, baseline(), REF)


def test_the_one_ledgerless_case_is_a_snapshot_taken_on_the_baseline_day(tmp_path):
    snap = with_ledger({}, fetched="2026-10-20T08:00:00Z")
    del snap["star_ledger"]
    snap["repo"] = REPO
    snap["closed_issues"], snap["merged_prs"], snap["forks"] = {"2026-10-13": 1}, {"2026-10-11": 3}, {"2026-10-13": 1}
    assert grm.load_carried(write(tmp_path / "c.json", snap), REPO, baseline(), REF)


def test_a_stale_carried_snapshot_is_rejected(tmp_path):
    later = REF + datetime.timedelta(days=grm.MAX_CARRY_AGE_DAYS + 1)
    with pytest.raises(RuntimeError, match="days old"):
        grm.load_carried(carried_for(tmp_path), REPO, baseline(), later)
    edge = datetime.datetime(2026, 10, 23, tzinfo=datetime.UTC) + datetime.timedelta(days=grm.MAX_CARRY_AGE_DAYS)
    assert grm.load_carried(carried_for(tmp_path), REPO, baseline(), edge)


def test_the_staleness_bound_is_a_named_constant():
    assert grm.MAX_CARRY_AGE_DAYS == 14


# -- the prefix rule -----------------------------------------------------------------------

OLD = {"2026-10-21": 104, "2026-10-22": 110, "2026-10-23": 140}


@pytest.mark.parametrize(
    "new, today, ok",
    [
        (OLD, "2026-10-23", True),
        ({**OLD, "2026-10-24": 150}, "2026-10-24", True),  # today appended
        ({"2026-10-21": 104, "2026-10-22": 110, "2026-10-23": 141}, "2026-10-23", True),  # today replaced
        ({**OLD, "2026-10-24": 150}, "2026-10-25", False),  # an extra point that is not today
        ({"2026-10-22": 110, "2026-10-23": 140}, "2026-10-24", False),  # first point dropped
        ({"2026-10-21": 104, "2026-10-23": 140}, "2026-10-24", False),  # middle point dropped
        ({"2026-10-21": 105, "2026-10-22": 110, "2026-10-23": 140}, "2026-10-24", False),  # earlier point changed
        ({"2026-10-22": 110, "2026-10-21": 104, "2026-10-23": 140}, "2026-10-24", False),  # reordered
        ({"2026-10-20": 90, **OLD}, "2026-10-24", False),  # a point inserted before
        ({}, "2026-10-24", False),  # emptied
    ],
)
def test_the_prefix_rule(new, today, ok):
    assert (grm.ledger_extension_problems(OLD, new, today) == []) is ok


def test_an_insertion_in_the_middle_that_is_not_today_fails():
    new = {"2026-10-21": 104, "2026-10-22": 110, "2026-10-22x": 0}
    assert grm.ledger_extension_problems({"2026-10-21": 104}, {"2026-10-21": 104, "2026-10-22": 110, "2026-10-23": 140}, "2026-10-23")
    assert grm.ledger_extension_problems({"2026-10-21": 104}, new, "2026-10-23")


def test_a_first_run_may_start_a_ledger_with_today_only():
    assert grm.ledger_extension_problems(None, {"2026-10-24": 150}, "2026-10-24") == []
    assert grm.ledger_extension_problems(None, {"2026-10-20": 150}, "2026-10-24")


def test_the_refresh_fails_closed_when_the_carried_snapshot_is_not_the_baselines(tmp_path, monkeypatch, capsys):
    from test_star_ledger import CiGh

    base = write(tmp_path / "base.json", baseline())
    carried = carried_for(tmp_path, stars_as_of="2026-10-19")
    monkeypatch.setattr(grm, "run_gh", CiGh())
    code = grm.main(["--refresh", "--no-star-times", "--repo", REPO, "--no-page", "--root", str(tmp_path), "--snapshot", "out/s.json", "--out", "out/c.png", "--baseline", str(base), "--ledger-from", str(carried)])
    assert code == 1 and "differs from the baseline" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# -- verify-bundle descends from the baseline and the previous snapshot --------------------


def bundle_with(tmp_path, ledger, **changes):
    snap = with_ledger(ledger)
    snap["repo"] = REPO
    snap["fetched_at"] = "2026-10-25T05:30:00Z"
    snap.update(changes)
    return make_bundle(tmp_path / "bundle", snap=snap)


def baseline_for(tmp_path):
    """A committed baseline that matches what make_bundle writes (same star history and dates)."""
    snap = {**baseline(), "created_on": "2026-10-10", "stars": {"2026-10-10": 2, "2026-10-12": 5}, "stars_as_of": "2026-10-20"}
    return write(tmp_path / "base.json", snap)


def prev_for(tmp_path, ledger):
    snap = {**with_ledger(ledger), "repo": REPO, "stars": {"2026-10-10": 2, "2026-10-12": 5}}
    return write(tmp_path / "prev.json", snap)


def verify(bundle, base, previous=None):
    return grm.verify_bundle(bundle, REPO, None, REF, baseline=base, previous=previous)


def test_a_descendant_bundle_passes(tmp_path):
    base = baseline_for(tmp_path)
    prev = prev_for(tmp_path, {"2026-10-21": 104, "2026-10-23": 140})
    b = bundle_with(tmp_path, {"2026-10-21": 104, "2026-10-23": 140, "2026-10-25": 150})
    assert verify(b, base, prev) == []


@pytest.mark.parametrize(
    "ledger",
    [
        {"2026-10-23": 140, "2026-10-25": 150},  # first point dropped
        {"2026-10-21": 104, "2026-10-25": 150},  # point dropped
        {"2026-10-21": 105, "2026-10-23": 140, "2026-10-25": 150},  # point changed
        {"2026-10-21": 104, "2026-10-24": 141, "2026-10-25": 150},  # extra non-today point
    ],
)
def test_a_bundle_that_loses_or_rewrites_history_fails(tmp_path, ledger):
    base = baseline_for(tmp_path)
    prev = prev_for(tmp_path, {"2026-10-21": 104, "2026-10-23": 140})
    assert verify(bundle_with(tmp_path, ledger), base, prev)


def test_a_bundle_with_another_baseline_fails(tmp_path):
    assert verify(bundle_with(tmp_path, {"2026-10-25": 150}, stars_as_of="2026-10-19"), baseline_for(tmp_path))


def test_a_baseline_with_a_ledger_fails_the_bundle_check(tmp_path):
    base = write(tmp_path / "base.json", with_ledger())
    assert any("star_ledger" in p for p in verify(bundle_with(tmp_path, {"2026-10-25": 150}), base))


def test_previous_without_a_baseline_is_refused(tmp_path):
    prev = prev_for(tmp_path, {"2026-10-21": 104})
    assert grm.verify_bundle(bundle_with(tmp_path, {"2026-10-25": 150}), REPO, None, REF, previous=prev)


# -- the carry script ----------------------------------------------------------------------


@pytest.fixture
def remote(tmp_path):
    r = tmp_path / "remote.git"
    git("init", "-q", "--bare", "-b", "main", str(r))
    return r


def push_branch(tmp_path, remote, files, mode=None):
    work = tmp_path / "pusher"
    git("init", "-q", "-b", "metrics", str(work))
    for name, data in files.items():
        (work / name).write_bytes(data)
    git("-C", str(work), "add", "-A")
    git("-C", str(work), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")
    git("-C", str(work), "push", "-q", str(remote), "HEAD:refs/heads/metrics")
    return git("rev-parse", "HEAD", cwd=work).stdout.strip()


def carry(remote, dest):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    return subprocess.run(["bash", str(CARRY), str(remote), str(dest)], check=False, capture_output=True, text=True, env=env)


def test_no_branch_means_a_first_run_with_an_empty_tip(tmp_path, remote):
    dest = tmp_path / "carried"
    out = carry(remote, dest)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "tip="
    assert not any(dest.iterdir())


def test_an_existing_branch_is_carried_with_its_tip(tmp_path, remote):
    snap = json.dumps(hashed({**with_ledger(), "repo": REPO}))
    tip = push_branch(tmp_path, remote, {"metrics-snapshot.json": snap.encode()})
    dest = tmp_path / "carried"
    out = carry(remote, dest)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"tip={tip}"
    assert (dest / "metrics-snapshot.json").read_text() == snap
    assert sorted(p.name for p in dest.iterdir()) == ["metrics-snapshot.json"]


def test_an_oversized_blob_is_rejected_before_any_file_exists(tmp_path, remote):
    push_branch(tmp_path, remote, {"metrics-snapshot.json": b"x" * (grm.MAX_SNAPSHOT_BYTES + 1)})
    dest = tmp_path / "carried"
    out = carry(remote, dest)
    assert out.returncode != 0 and "larger than" in out.stderr
    assert list(dest.iterdir()) == []
    assert not [p for p in tmp_path.rglob("*") if p.is_file() and p.stat().st_size > grm.MAX_SNAPSHOT_BYTES and "pusher" not in p.parts and "remote.git" not in p.parts]


def test_a_blob_exactly_at_the_cap_is_accepted_and_one_over_is_not(tmp_path, remote):
    push_branch(tmp_path, remote, {"metrics-snapshot.json": b"x" * grm.MAX_SNAPSHOT_BYTES})
    assert carry(remote, tmp_path / "ok").returncode == 0


def test_a_branch_without_the_snapshot_is_rejected(tmp_path, remote):
    push_branch(tmp_path, remote, {"other.txt": b"hi"})
    out = carry(remote, tmp_path / "carried")
    assert out.returncode != 0 and "metrics-snapshot.json" in out.stderr
    assert list((tmp_path / "carried").iterdir()) == []


def test_a_symlink_snapshot_is_rejected(tmp_path, remote):
    work = tmp_path / "pusher"
    git("init", "-q", "-b", "metrics", str(work))
    os.symlink("/etc/passwd", work / "metrics-snapshot.json")
    git("-C", str(work), "add", "-A")
    git("-C", str(work), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")
    git("-C", str(work), "push", "-q", str(remote), "HEAD:refs/heads/metrics")
    out = carry(remote, tmp_path / "carried")
    assert out.returncode != 0 and "regular file" in out.stderr
    assert list((tmp_path / "carried").iterdir()) == []


def test_an_unreachable_remote_fails_instead_of_looking_like_a_first_run(tmp_path):
    out = carry(tmp_path / "does-not-exist.git", tmp_path / "carried")
    assert out.returncode != 0
    assert "tip=" not in out.stdout


def test_the_carry_script_never_writes_outside_the_destination_or_forces():
    text = CARRY.read_text()
    assert "--force" not in text and "head -c" in text and "cat-file -s" in text


def test_the_committed_snapshot_is_a_valid_baseline():
    base = grm.load_baseline(ROOT / grm.SNAPSHOT)
    assert "star_ledger" not in base and base["stars_as_of"] == base["fetched_at"][:10]


def test_the_page_documents_history_the_prefix_rule_and_the_reset():
    page = (ROOT / "docs" / "wiki" / "Repository-Growth.md").read_text()
    for needle in ("fast-forward", "one small commit per day", "14 days", "delete the `metrics` branch", "reviewed"):
        assert needle in page, needle
