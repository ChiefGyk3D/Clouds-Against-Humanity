# SPDX-License-Identifier: Apache-2.0
"""The star ledger (issue #296).

The default Actions token cannot read stargazer time stamps (GraphQL and REST are
both refused), so CI records one dated cumulative star count per UTC day instead.
What is proved here:
- the snapshot schema accepts the optional `stars_as_of` and `star_ledger` fields,
  an old snapshot without them still validates and keeps its digest, and hostile
  ledgers fail: out-of-order or duplicate days, future days, days at or before the
  baseline, non-integers, bools, negatives, drops beyond the tolerance, oversize;
- in CI mode the refresh makes NO stargazers request, reads only the repo's
  stargazers_count, keeps the baseline star times, appends one point a day and
  replaces a same-day point; GITHUB_ACTIONS=true selects CI mode on its own;
- the local path still fetches full time stamps;
- the chart draws baseline plus ledger and says so in the picture.
"""

import copy
import datetime
import json
import sys
from pathlib import Path
from unittest import mock

import pytest
from test_growth_bundle import REPO, make_bundle, problems
from test_repo_metrics import fixture

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_repo_metrics as grm

ZERO = {"source_sha256": "0" * 64, "png_sha256": "0" * 64}


@pytest.fixture(autouse=True)
def _not_in_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


def with_ledger(ledger=None, as_of="2026-10-20", fetched="2026-10-25T05:30:00Z"):
    snap = fixture()
    snap["fetched_at"] = fetched
    snap["stars"] = {"2026-10-10": 20, "2026-10-12": 50, "2026-10-19": 30}  # 100 by the 19th
    snap["stars_as_of"] = as_of
    snap["star_ledger"] = {"2026-10-21": 104, "2026-10-22": 110, "2026-10-23": 140} if ledger is None else ledger
    return snap


def bad(snap):
    return grm.validate_snapshot({**snap, **ZERO})


def test_a_good_ledger_validates_and_counts_the_latest_point():
    snap = with_ledger()
    assert bad(snap) == []
    assert grm.current_stars(snap) == 140
    assert grm.totals(snap)["stars"] == 140


def test_an_old_snapshot_is_still_valid_and_keeps_its_digest():
    snap = fixture()
    assert bad(snap) == []
    assert grm.current_stars(snap) == sum(snap["stars"].values())
    legacy = json.dumps({k: snap.get(k) for k in ("schema", "repo", "created_on", "fetched_at", "stars", "forks", "merged_prs", "closed_issues", "traffic")}, sort_keys=True, separators=(",", ":"))
    import hashlib

    assert grm.source_digest(snap) == hashlib.sha256(legacy.encode()).hexdigest()


def test_the_ledger_is_covered_by_the_source_hash():
    a, b = with_ledger(), with_ledger()
    b["star_ledger"]["2026-10-23"] = 141
    assert grm.source_digest(a) != grm.source_digest(b)


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda s: s.update(star_ledger={"2026-10-22": 110, "2026-10-21": 104}), "order"),
        (lambda s: s.update(star_ledger={"2026-10-21": 104, "2026-10-26": 110}), "outside"),  # after fetched_at
        (lambda s: s.update(star_ledger={"2026-10-20": 104}), "outside"),  # on the baseline day
        (lambda s: s.update(star_ledger={"2026-10-15": 104}), "outside"),  # inside the baseline
        (lambda s: s.update(star_ledger={"2026-10-21": 104.5}), "bad value"),
        (lambda s: s.update(star_ledger={"2026-10-21": "104"}), "bad value"),
        (lambda s: s.update(star_ledger={"2026-10-21": True}), "bad value"),
        (lambda s: s.update(star_ledger={"2026-10-21": -1}), "bad value"),
        (lambda s: s.update(star_ledger={"2026-10-21": 10**9}), "bad value"),
        (lambda s: s.update(star_ledger={"2026-10-21": 100, "2026-10-22": 60}), "drop"),
        (lambda s: s.update(star_ledger={"2026-10-21": 40}), "drop"),  # first point far below the baseline total
        (lambda s: s.update(star_ledger={"21-10-2026": 104}), "date"),
        (lambda s: s.update(star_ledger={"2026-02-30": 104}), "date"),
        (lambda s: s.update(star_ledger=[["2026-10-21", 104]]), "object"),
        (lambda s: s.update(star_ledger=None), "object"),
        (lambda s: s.pop("stars_as_of"), "stars_as_of"),  # a ledger needs its baseline date
        (lambda s: s.update(stars_as_of="2026-10-26"), "stars_as_of"),  # after fetched_at
        (lambda s: s.update(stars_as_of="2026-10-01"), "stars_as_of"),  # before created_on
        (lambda s: s.update(stars_as_of="soon"), "stars_as_of"),
        (lambda s: s["stars"].update({"2026-10-21": 3}), "outside"),  # baseline stars after the baseline date
        (lambda s: s.update(star_ledger={f"2026-{m:02d}-{d:02d}": 1 for m in range(11, 13) for d in range(1, 29)}), None),
    ],
)
def test_hostile_ledgers_fail(mutate, needle):
    snap = with_ledger()
    mutate(snap)
    out = bad(snap)
    assert out, "the hostile snapshot was accepted"
    if needle:
        assert any(needle in p for p in out), out


def test_a_small_drop_from_unstarring_is_tolerated():
    assert bad(with_ledger({"2026-10-21": 104, "2026-10-22": 102, "2026-10-23": 140})) == []


def test_an_oversized_ledger_fails():
    start = datetime.date(2026, 10, 21)
    big = {(start + datetime.timedelta(days=i)).isoformat(): 100 for i in range(grm.MAX_LEDGER_POINTS + 1)}
    snap = with_ledger(big, fetched=f"{(start + datetime.timedelta(days=grm.MAX_LEDGER_POINTS + 2)).isoformat()}T00:00:00Z")
    assert any("too many" in p for p in bad(snap))


def test_the_bundle_verifier_rejects_a_future_ledger_point(tmp_path):
    b = make_bundle(tmp_path / "b", snap=with_ledger({"2026-10-21": 104, "2026-10-26": 110}, fetched="2026-10-26T05:30:00Z"))
    assert problems(b)  # fetched_at (and the last point) are after NOW


def test_a_ledger_bundle_passes_the_verifier(tmp_path):
    snap = with_ledger({"2026-10-21": 104, "2026-10-25": 140})
    b = make_bundle(tmp_path / "b", snap=snap)
    assert problems(b) == []


# -- the fetch layer in CI mode ---------------------------------------------------------


class CiGh:
    def __init__(self, count=150):
        self.calls, self.count = [], count

    def __call__(self, args):
        self.calls.append(args)
        text = " ".join(args)
        assert "stargazers" != text and "/stargazers" not in text and "graphql" not in text, text
        if args[:2] == ["api", f"repos/{REPO}"] and ".stargazers_count" in args:
            return f"{self.count}\n"
        if "/forks" in text:
            return "2026-10-12T00:00:00Z\n"
        if args[0] == "api":
            return "2026-10-10T00:00:00Z\n"
        if args[:2] == ["pr", "list"]:
            return json.dumps([{"mergedAt": "2026-10-11T05:00:00Z"}])
        if args[:2] == ["issue", "list"]:
            return json.dumps([{"closedAt": "2026-10-12T05:00:00Z"}])
        raise AssertionError(text)


def baseline():
    snap = with_ledger({})
    del snap["star_ledger"]
    snap["repo"] = REPO
    return snap


DAY = datetime.datetime(2026, 10, 24, 6, 0, 0, tzinfo=datetime.UTC)


def test_ci_mode_makes_no_stargazers_request_and_reads_only_the_count():
    gh = CiGh()
    with mock.patch.object(grm, "run_gh", gh):
        snap = grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=baseline())
    assert not any("/stargazers" in " ".join(c) or "graphql" in " ".join(c) for c in gh.calls)
    assert any(".stargazers_count" in c for c in gh.calls)
    assert snap["stars"] == baseline()["stars"] and snap["stars_as_of"] == "2026-10-20"
    assert snap["star_ledger"] == {"2026-10-24": 150}
    assert grm.validate_snapshot({**snap, **ZERO}) == []


def test_ci_mode_appends_one_point_per_day_and_keeps_old_points():
    prev = with_ledger({"2026-10-21": 104, "2026-10-23": 140})
    with mock.patch.object(grm, "run_gh", CiGh(150)):
        snap = grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=baseline(), ledger_from=prev)
    assert snap["star_ledger"] == {"2026-10-21": 104, "2026-10-23": 140, "2026-10-24": 150}


def test_a_same_day_rerun_replaces_that_days_point():
    prev = with_ledger({"2026-10-21": 104, "2026-10-24": 140})
    with mock.patch.object(grm, "run_gh", CiGh(151)):
        snap = grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=baseline(), ledger_from=prev)
    assert snap["star_ledger"] == {"2026-10-21": 104, "2026-10-24": 151}


def test_points_at_or_before_the_baseline_date_in_a_carried_ledger_fail_closed():
    newer = baseline()
    newer["stars_as_of"] = "2026-10-22"
    newer["stars"]["2026-10-22"] = 5
    prev = with_ledger({"2026-10-21": 104, "2026-10-22": 108, "2026-10-23": 140})
    with mock.patch.object(grm, "run_gh", CiGh(150)), pytest.raises(RuntimeError, match="keep every earlier point"):
        grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=newer, ledger_from=prev)


def test_ci_mode_without_a_baseline_fails_closed():
    with mock.patch.object(grm, "run_gh", CiGh()), pytest.raises(RuntimeError, match="baseline"):
        grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=None)


def test_a_baseline_for_another_repository_is_refused():
    other = baseline()
    other["repo"] = "Other/Thing"
    with mock.patch.object(grm, "run_gh", CiGh()), pytest.raises(RuntimeError, match="baseline"):
        grm.fetch_snapshot(REPO, now=DAY, star_times=False, baseline=other)


def test_the_local_path_still_asks_for_star_times():
    class Local(CiGh):
        def __call__(self, args):
            text = " ".join(args)
            if "/stargazers" in text:
                self.calls.append(args)
                return "2026-10-10T01:00:00Z\n"
            return super().__call__(args)

    gh = Local()
    with mock.patch.object(grm, "run_gh", gh):
        snap = grm.fetch_snapshot(REPO, now=DAY)
    assert any("/stargazers" in " ".join(c) for c in gh.calls)
    assert snap["stars"] == {"2026-10-10": 1} and "star_ledger" not in snap and "stars_as_of" not in snap


def _fake_write_all(snap, sp, pp, pg, ref):
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(snap))


def write_baseline(tmp_path, snap):
    snap = copy.deepcopy(snap)
    snap["source_sha256"] = grm.source_digest(snap)
    snap["png_sha256"] = "1" * 64
    path = tmp_path / "base.json"
    path.write_text(json.dumps(snap))
    return path


def test_main_selects_ci_mode_from_the_environment_and_never_asks_for_star_times(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    base = write_baseline(tmp_path, baseline())
    gh = CiGh(150)
    monkeypatch.setattr(grm, "run_gh", gh)
    monkeypatch.setattr(grm, "draw_png", lambda s, out: out.write_bytes(b"\x89PNG\r\n\x1a\n"))
    monkeypatch.setattr(grm, "write_all", _fake_write_all)
    code = grm.main(["--refresh", "--repo", REPO, "--no-page", "--root", str(tmp_path), "--snapshot", "out/s.json", "--out", "out/c.png", "--baseline", str(base)])
    assert code == 0
    assert not any("/stargazers" in " ".join(c) or "graphql" in " ".join(c) for c in gh.calls)
    out = json.loads((tmp_path / "out" / "s.json").read_text())
    assert out["star_ledger"] and out["stars_as_of"] == "2026-10-20"


def test_the_explicit_flag_also_selects_ci_mode(tmp_path, monkeypatch):
    base = write_baseline(tmp_path, baseline())
    gh = CiGh(150)
    monkeypatch.setattr(grm, "run_gh", gh)
    monkeypatch.setattr(grm, "write_all", _fake_write_all)
    code = grm.main(["--refresh", "--no-star-times", "--repo", REPO, "--no-page", "--root", str(tmp_path), "--snapshot", "out/s.json", "--out", "out/c.png", "--baseline", str(base)])
    assert code == 0 and not any("/stargazers" in " ".join(c) for c in gh.calls)


def test_a_tampered_baseline_file_fails_the_refresh(tmp_path, monkeypatch, capsys):
    base = write_baseline(tmp_path, baseline())
    data = json.loads(base.read_text())
    data["stars"]["2026-10-12"] = 99999
    base.write_text(json.dumps(data))
    monkeypatch.setattr(grm, "run_gh", CiGh())
    code = grm.main(["--refresh", "--no-star-times", "--repo", REPO, "--no-page", "--root", str(tmp_path), "--snapshot", "out/s.json", "--out", "out/c.png", "--baseline", str(base)])
    assert code == 1 and "baseline" in capsys.readouterr().err


def test_the_ledger_from_file_is_read_with_the_strict_loader(tmp_path, monkeypatch, capsys):
    base = write_baseline(tmp_path, baseline())
    junk = tmp_path / "prev.json"
    junk.write_text('{"star_ledger": {"2026-10-21": 1}, "star_ledger": {}}')  # duplicate keys
    monkeypatch.setattr(grm, "run_gh", CiGh())
    code = grm.main(["--refresh", "--no-star-times", "--repo", REPO, "--no-page", "--root", str(tmp_path), "--snapshot", "out/s.json", "--out", "out/c.png", "--baseline", str(base), "--ledger-from", str(junk)])
    assert code == 1


# -- drawing and the page ---------------------------------------------------------------


def test_the_chart_draws_baseline_plus_ledger_and_says_so(tmp_path):
    pytest.importorskip("matplotlib")
    out = tmp_path / "chart.png"
    snap = with_ledger()
    grm.draw_png(snap, out)
    assert out.read_bytes().startswith(b"\x89PNG")
    note = grm.star_note(snap)
    assert "2026-10-20" in note and "daily counts" in note and "not per-star times" in note
    assert grm.star_note(fixture()) == ""


def test_the_page_says_how_the_star_line_is_built():
    page = grm.render_page(fixture())
    assert "daily counts" in page and "per-star times" in page
    assert "--refresh" in page and "backfill" in page.lower()


# -- a refresh that crosses UTC midnight ---------------------------------------------------


class Clock:
    def __init__(self, *stamps):
        self.stamps = list(stamps)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.stamps.pop(0)


def utc(day, hms):
    h, m, sec = map(int, hms.split(":"))
    return datetime.datetime(2026, 10, day, h, m, sec, tzinfo=datetime.UTC)


class CountingGh(CiGh):
    def __init__(self, *counts):
        super().__init__()
        self.counts = list(counts)
        self.count_calls = 0

    def __call__(self, args):
        if args[:2] == ["api", f"repos/{REPO}"] and ".stargazers_count" in args:
            self.calls.append(args)
            self.count_calls += 1
            return f"{self.counts.pop(0)}\n"
        return super().__call__(args)


def test_a_count_taken_across_midnight_is_requested_again_and_dated_by_the_second_request(monkeypatch):
    # first request straddles midnight (23:59:59 -> 00:00:01); the retry is clean (day 25)
    clock = Clock(utc(24, "23:58:00"), utc(24, "23:59:59"), utc(25, "00:00:01"), utc(25, "00:00:02"), utc(25, "00:00:03"))
    gh = CountingGh(149, 150)
    monkeypatch.setattr(grm, "_utcnow", clock)
    with mock.patch.object(grm, "run_gh", gh):
        snap = grm.fetch_snapshot(REPO, star_times=False, baseline=baseline())
    assert gh.count_calls == 2
    assert snap["star_ledger"] == {"2026-10-25": 150}  # the count from the clean request, on its own day
    assert snap["fetched_at"] == "2026-10-25T00:00:03Z"


def test_a_count_that_keeps_crossing_midnight_fails_closed(monkeypatch):
    clock = Clock(utc(24, "23:58:00"), utc(24, "23:59:59"), utc(25, "00:00:01"), utc(25, "23:59:59"), utc(26, "00:00:01"))
    gh = CountingGh(149, 150)
    monkeypatch.setattr(grm, "_utcnow", clock)
    with mock.patch.object(grm, "run_gh", gh), pytest.raises(RuntimeError, match="midnight"):
        grm.fetch_snapshot(REPO, star_times=False, baseline=baseline())


def test_a_clean_request_is_made_once(monkeypatch):
    clock = Clock(utc(25, "09:59:00"), utc(25, "10:00:00"), utc(25, "10:00:01"))
    gh = CountingGh(150)
    monkeypatch.setattr(grm, "_utcnow", clock)
    with mock.patch.object(grm, "run_gh", gh):
        snap = grm.fetch_snapshot(REPO, star_times=False, baseline=baseline())
    assert gh.count_calls == 1 and snap["fetched_at"] == "2026-10-25T10:00:01Z"
