# SPDX-License-Identifier: Apache-2.0
"""The repository growth chart generator (issue #268).

All offline: CI has no token and no plotting library, so every test here uses a
fixture snapshot and a PNG built at run time. What is proved:
- the snapshot never holds a login-like field, and the fetch layer never asks
  GitHub for one;
- render_page() from a fixture gives the expected counts table;
- --check fails on a stale PNG hash, a missing PNG, a hand edit of the data, and
  a hand edit of the page, and passes on a consistent set;
- a failed --refresh leaves every file untouched;
- the cumulative series is monotonic and anchored at day 0, and a repository
  with no forks still renders;
- the committed files pass --check, and matplotlib is imported lazily with a
  clear message when it is missing.
"""

import copy
import datetime
import itertools
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_repo_metrics as grm

PNG_DIR = Path("docs/wiki/images")
WIKI_DIR = Path("docs/wiki")
LOGIN_LIKE = ("login", "user", "author", "owner", "email", "referrer", "path", "avatar", "node")


def png_bytes(color=0) -> bytes:
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    raw = b"\x00" + bytes([color, color, color])
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def fixture(forks=None):
    snap = {
        "schema": 1,
        "repo": "Example/Repo",
        "created_on": "2026-10-10",
        "fetched_at": "2026-10-22T12:00:00Z",
        "stars": {"2026-10-10": 2, "2026-10-12": 5, "2026-10-14": 100, "2026-10-21": 8},
        "forks": {"2026-10-13": 1, "2026-10-20": 2} if forks is None else forks,
        "merged_prs": {"2026-10-11": 3, "2026-10-12": 4, "2026-10-19": 6},
        "closed_issues": {"2026-10-13": 1, "2026-10-22": 2},
    }
    return snap


def setup_tree(tmp_path, snap=None, page=True):
    snap = copy.deepcopy(snap or fixture())
    png = tmp_path / "docs" / "wiki" / "images" / "repo-growth.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(png_bytes())
    snap["source_sha256"] = grm.source_digest(snap)
    snap["png_sha256"] = grm.file_digest(png)
    sp = tmp_path / grm.SNAPSHOT
    sp.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n")
    if page:
        (tmp_path / grm.PAGE).write_text(grm.render_page(snap))
    return snap


def run_check(tmp_path, capsys):
    code = grm.main(["--check", "--root", str(tmp_path)])
    return code, capsys.readouterr().err


# -- series -------------------------------------------------------------------


def test_cumulative_series_is_monotonic_and_day_zero_anchored():
    snap = fixture()
    start, end = grm.span(snap)
    series = grm.cumulative(snap["stars"], start, end)
    assert len(series) == (end - start).days + 1  # one point per day, day 0 first
    assert series[0] == 2  # the stars given on the creation date count at day 0
    assert all(b >= a for a, b in itertools.pairwise(series))
    assert series[-1] == sum(snap["stars"].values()) == 115


def test_weekly_bins_start_on_monday_and_cover_every_week():
    snap = fixture()
    start, end = grm.span(snap)
    weeks = grm.weekly(snap["merged_prs"], start, end)
    assert [w.isoformat() for w, _ in weeks] == ["2026-10-05", "2026-10-12", "2026-10-19"]
    assert [n for _, n in weeks] == [3, 4, 6]


def test_day_counts_groups_timestamps_by_utc_day():
    assert grm.day_counts(["2026-10-10T23:59:59Z", "2026-10-10T00:00:01Z", "2026-10-11T00:00:00Z"]) == {"2026-10-10": 2, "2026-10-11": 1}


# -- page ---------------------------------------------------------------------


def test_render_page_from_a_fixture_has_the_expected_counts_table():
    page = grm.render_page(fixture())
    assert "| Week of | New stars | New forks | PRs merged | Issues closed | Stars so far | Forks so far |" in page
    assert "| 2026-10-05 | 2 | 0 | 3 | 0 | 2 | 0 |" in page
    assert "| 2026-10-12 | 105 | 1 | 4 | 1 | 107 | 1 |" in page
    assert "| 2026-10-19 (partial) | 8 | 2 | 6 | 2 | 115 | 3 |" in page
    assert "Totals: 115 stars, 3 forks, 13 merged pull requests, 3 closed issues." in page
    assert "**Generated at:** 2026-10-22T12:00:00Z (UTC)" in page
    assert "Stars measure attention, not use." in page
    assert "![Hand-drawn style chart" in page


def test_render_page_is_deterministic_and_traffic_is_optional():
    snap = fixture()
    assert grm.render_page(snap) == grm.render_page(copy.deepcopy(snap))
    assert "## Traffic" not in grm.render_page(snap)
    snap["traffic"] = {"views": {"2026-10-20": {"count": 9, "uniques": 4}, "2026-10-21": {"count": 1, "uniques": 1}}}
    page = grm.render_page(snap)
    assert "## Traffic" in page
    assert "| views | 2 | 2026-10-20 | 2026-10-21 | 10 |" in page


def test_a_repository_with_zero_forks_renders():
    snap = fixture(forks={})
    assert grm.validate_snapshot({**snap, "source_sha256": "0" * 64, "png_sha256": "0" * 64}) == []
    page = grm.render_page(snap)
    assert "0 forks" in page
    assert grm.cumulative(snap["forks"], *grm.span(snap)) == [0] * 13


def test_the_chart_draws_with_zero_forks_when_matplotlib_is_present(tmp_path):
    pytest.importorskip("matplotlib")
    out = tmp_path / "chart.png"
    grm.draw_png(fixture(forks={}), out)
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG")
    assert struct.unpack(">I", data[16:20])[0] <= 1000  # about 900 px, sized for the README


def test_matplotlib_is_imported_lazily_with_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    with pytest.raises(RuntimeError, match="python3-matplotlib") as err:
        grm.draw_png(fixture(), tmp_path / "x.png")
    assert "pip install matplotlib" in str(err.value)
    assert "import matplotlib" not in "\n".join(line for line in Path(grm.__file__).read_text().splitlines() if not line.startswith(" "))


# -- snapshot never holds a person -------------------------------------------------


def all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from all_keys(v)


def test_the_committed_snapshot_has_no_login_like_field():
    snap = json.loads((ROOT / grm.SNAPSHOT).read_text())
    keys = {k for k in all_keys(snap) if not grm.DATE_RE.match(k)}
    assert not [k for k in keys if any(word in k.lower() for word in LOGIN_LIKE)], keys
    assert keys <= grm.SNAPSHOT_KEYS | {"views", "clones", "count", "uniques"}


@pytest.mark.parametrize("field", ["login", "stargazers", "users", "referrers", "paths"])
def test_validation_rejects_an_unknown_field(field):
    snap = fixture()
    snap[field] = ["someone"]
    problems = grm.validate_snapshot({**snap, "source_sha256": "0" * 64, "png_sha256": "0" * 64})
    assert any("unknown field" in p for p in problems)


def test_validation_rejects_a_name_hidden_in_a_series_or_traffic():
    base = {"source_sha256": "0" * 64, "png_sha256": "0" * 64}
    snap = fixture()
    snap["stars"] = {"someone": 1}
    assert grm.validate_snapshot({**snap, **base})
    snap = fixture()
    snap["traffic"] = {"referrers": {}}
    assert grm.validate_snapshot({**snap, **base})
    snap = fixture()
    snap["traffic"] = {"views": {"2026-10-20": {"count": 1, "uniques": 1, "path": "/x"}}}
    assert grm.validate_snapshot({**snap, **base})
    snap = fixture()
    snap["stars"] = {"2026-09-01": 1}  # before the repository existed
    assert grm.validate_snapshot({**snap, **base})


# -- fetch layer --------------------------------------------------------------------


class FakeGh:
    def __init__(self):
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        text = " ".join(args)
        if "/stargazers" in text:
            # REST, not GraphQL: the default Actions token is refused on the GraphQL
            # stargazers connection (issue #296). Only the time stamp may be selected.
            assert args[:2] == ["api", "--paginate"] and "application/vnd.github.star+json" in text
            jq = args[args.index("--jq") + 1]
            assert jq == ".[].starred_at" and "login" not in text and "user" not in text
            return "2026-10-10T01:00:00Z\n2026-10-10T02:00:00Z\n2026-10-11T01:00:00Z\n"
        if "traffic/views" in text:
            return json.dumps({"views": [{"timestamp": "2026-10-21T00:00:00Z", "count": 5, "uniques": 2}]})
        if "traffic/clones" in text:
            raise RuntimeError("HTTP 403: admin rights needed")
        if "/forks" in text:
            return "2026-10-12T00:00:00Z\n"
        if args[0] == "api":
            return "2026-10-10T00:00:00Z\n"
        if args[:2] == ["pr", "list"]:
            return json.dumps([{"mergedAt": "2026-10-11T05:00:00Z"}, {"mergedAt": None}])
        if args[:2] == ["issue", "list"]:
            return json.dumps([{"closedAt": "2026-10-12T05:00:00Z"}])
        raise AssertionError(text)


def test_stars_are_fetched_over_rest_never_graphql():
    fake = FakeGh()
    with mock.patch.object(grm, "run_gh", fake):
        assert grm.fetch_stars("Example/Repo") == ["2026-10-10T01:00:00Z", "2026-10-10T02:00:00Z", "2026-10-11T01:00:00Z"]
    assert not any("graphql" in " ".join(c) for c in fake.calls)
    assert not hasattr(grm, "STARS_QUERY")


def test_fetch_builds_per_day_counts_pages_stars_and_asks_for_no_login():
    fake = FakeGh()
    now = datetime.datetime(2026, 10, 22, 12, 0, 0, tzinfo=datetime.UTC)
    with mock.patch.object(grm, "run_gh", fake):
        snap = grm.fetch_snapshot("Example/Repo", now=now)
    assert snap["stars"] == {"2026-10-10": 2, "2026-10-11": 1}
    assert snap["forks"] == {"2026-10-12": 1}
    assert snap["merged_prs"] == {"2026-10-11": 1}
    assert snap["closed_issues"] == {"2026-10-12": 1}
    assert snap["created_on"] == "2026-10-10" and snap["fetched_at"] == "2026-10-22T12:00:00Z"
    assert "traffic" not in snap  # not asked for
    assert all(isinstance(c, list) and all(isinstance(a, str) for a in c) for c in fake.calls)
    assert not any("traffic" in " ".join(c) for c in fake.calls)
    assert grm.validate_snapshot({**snap, "source_sha256": "0" * 64, "png_sha256": "0" * 64}) == []


def test_traffic_is_fetched_only_when_asked_merged_with_earlier_days_and_tolerates_refusal():
    previous = {"traffic": {"views": {"2026-10-01": {"count": 3, "uniques": 1}}}}
    with mock.patch.object(grm, "run_gh", FakeGh()):
        snap = grm.fetch_snapshot("Example/Repo", traffic=True, previous=previous)
    # clones are refused by the fake (admin needed), so the earlier traffic is kept as it was
    assert snap["traffic"] == previous["traffic"]

    class Allowed(FakeGh):
        def __call__(self, args):
            if "traffic/clones" in " ".join(args):
                return json.dumps({"clones": [{"timestamp": "2026-10-21T00:00:00Z", "count": 1, "uniques": 1}]})
            return super().__call__(args)

    with mock.patch.object(grm, "run_gh", Allowed()):
        snap = grm.fetch_snapshot("Example/Repo", traffic=True, previous=previous)
    assert set(snap["traffic"]["views"]) == {"2026-10-01", "2026-10-21"}
    assert snap["traffic"]["clones"] == {"2026-10-21": {"count": 1, "uniques": 1}}


def test_gh_is_called_with_an_argument_list_and_no_shell(monkeypatch):
    seen = {}

    def fake_run(args, **kw):
        seen["args"], seen["kw"] = args, kw
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr(grm.subprocess, "run", fake_run)
    assert grm.run_gh(["api", "repos/a/b; rm -rf x"]) == "ok"
    assert seen["args"] == ["gh", "api", "repos/a/b; rm -rf x"]
    assert not seen["kw"].get("shell")


def test_only_a_50x_answer_is_retried(monkeypatch):
    monkeypatch.setattr(grm.time, "sleep", lambda s: None)
    answers = iter([subprocess.CompletedProcess([], 1, "", "HTTP 502: bad gateway"), subprocess.CompletedProcess([], 0, "fine", "")])
    monkeypatch.setattr(grm.subprocess, "run", lambda *a, **k: next(answers))
    assert grm.run_gh(["x"]) == "fine"
    calls = []

    def forbidden(*a, **k):
        calls.append(1)
        return subprocess.CompletedProcess([], 1, "", "HTTP 403: rate limit")

    monkeypatch.setattr(grm.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError):
        grm.run_gh(["x"])
    assert len(calls) == 1


# -- --check ------------------------------------------------------------------------


def test_a_consistent_set_passes_check(tmp_path, capsys):
    setup_tree(tmp_path)
    assert run_check(tmp_path, capsys)[0] == 0


def test_check_fails_on_a_stale_png_hash(tmp_path, capsys):
    setup_tree(tmp_path)
    (tmp_path / grm.PNG).write_bytes(png_bytes(color=9))  # a different picture than the one recorded
    code, err = run_check(tmp_path, capsys)
    assert code == 1 and "png_sha256" in err


def test_check_fails_on_a_missing_png(tmp_path, capsys):
    setup_tree(tmp_path)
    (tmp_path / grm.PNG).unlink()
    code, err = run_check(tmp_path, capsys)
    assert code == 1 and "missing" in err


def test_check_fails_on_a_hand_edit_of_the_data(tmp_path, capsys):
    setup_tree(tmp_path)
    sp = tmp_path / grm.SNAPSHOT
    snap = json.loads(sp.read_text())
    snap["stars"]["2026-10-10"] += 1000
    sp.write_text(json.dumps(snap))
    code, err = run_check(tmp_path, capsys)
    assert code == 1 and "source_sha256" in err


def test_check_fails_on_a_hand_edit_of_the_page_and_on_a_missing_page(tmp_path, capsys):
    setup_tree(tmp_path)
    page = tmp_path / grm.PAGE
    page.write_text(page.read_text().replace("Totals: 115", "Totals: 999"))
    code, err = run_check(tmp_path, capsys)
    assert code == 1 and "does not match" in err
    page.unlink()
    assert run_check(tmp_path, capsys)[0] == 1


def test_check_fails_on_a_png_with_metadata_chunks(tmp_path, capsys):
    snap = setup_tree(tmp_path)
    png = tmp_path / grm.PNG
    data = png_bytes()
    body = b"Comment\x00hello"
    text = struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", zlib.crc32(b"tEXt" + body) & 0xFFFFFFFF)
    png.write_bytes(data[:33] + text + data[33:])
    snap["png_sha256"] = grm.file_digest(png)
    (tmp_path / grm.SNAPSHOT).write_text(json.dumps(snap))
    code, err = run_check(tmp_path, capsys)
    assert code == 1 and "tEXt" in err


def test_check_needs_no_plotting_library(tmp_path, capsys, monkeypatch):
    setup_tree(tmp_path)
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    assert run_check(tmp_path, capsys)[0] == 0


def test_the_committed_files_pass_check():
    result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "gen_repo_metrics.py"), "--check"], check=False, capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr


# -- --refresh ----------------------------------------------------------------------


def snapshot_files(tmp_path):
    return {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in sorted(tmp_path.rglob("*")) if p.is_file()}


def test_a_failed_fetch_leaves_the_files_untouched(tmp_path, monkeypatch, capsys):
    setup_tree(tmp_path)
    before = snapshot_files(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("gh api failed: HTTP 401")

    monkeypatch.setattr(grm, "fetch_snapshot", boom)
    assert grm.main(["--refresh", "--root", str(tmp_path)]) == 1
    assert "refresh failed" in capsys.readouterr().err
    assert snapshot_files(tmp_path) == before


def test_a_failed_draw_leaves_the_files_untouched(tmp_path, monkeypatch, capsys):
    setup_tree(tmp_path)
    before = snapshot_files(tmp_path)
    fresh = fixture()
    fresh["fetched_at"] = "2026-10-23T00:00:00Z"
    monkeypatch.setattr(grm, "fetch_snapshot", lambda *a, **k: fresh)

    def no_plot(snap, out):
        raise RuntimeError("matplotlib is not installed")

    monkeypatch.setattr(grm, "draw_png", no_plot)
    assert grm.main(["--refresh", "--root", str(tmp_path)]) == 1
    assert snapshot_files(tmp_path) == before


def test_a_successful_refresh_writes_a_set_that_passes_check(tmp_path, monkeypatch, capsys):
    fresh = fixture()
    monkeypatch.setattr(grm, "fetch_snapshot", lambda *a, **k: fresh)
    monkeypatch.setattr(grm, "draw_png", lambda snap, out: out.write_bytes(png_bytes(color=3)))
    assert grm.main(["--refresh", "--root", str(tmp_path)]) == 0
    assert run_check(tmp_path, capsys)[0] == 0
    snap = json.loads((tmp_path / grm.SNAPSHOT).read_text())
    assert snap["png_sha256"] == grm.file_digest(tmp_path / grm.PNG)


def test_another_repository_can_use_its_own_paths(tmp_path, monkeypatch, capsys):
    snap = fixture()
    snap["repo"] = "Example/Other"
    monkeypatch.setattr(grm, "fetch_snapshot", lambda repo, *a, **k: {**snap, "repo": repo})
    monkeypatch.setattr(grm, "draw_png", lambda s, out: out.write_bytes(png_bytes()))
    common = ["--root", str(tmp_path), "--snapshot", "m/s.json", "--out", "m/i/c.png", "--page", "m/P.md"]
    assert grm.main(["--refresh", "--repo", "Example/Other", *common]) == 0
    assert "(i/c.png)" in (tmp_path / "m" / "P.md").read_text()
    assert grm.main(["--check", *common]) == 0
    assert grm.main(["--refresh", "--repo", "Example/Other", "--no-page", "--root", str(tmp_path), "--snapshot", "n.json", "--out", "n.png"]) == 0
    assert not (tmp_path / "docs").exists()


def test_traffic_flag_needs_refresh():
    with pytest.raises(SystemExit):
        grm.main(["--traffic"])


def test_a_failing_second_or_third_write_leaves_all_three_files_unchanged(tmp_path, monkeypatch):
    setup_tree(tmp_path)
    before = snapshot_files(tmp_path)
    fresh = fixture()
    fresh["fetched_at"] = "2026-10-23T00:00:00Z"
    monkeypatch.setattr(grm, "draw_png", lambda snap, out: out.write_bytes(png_bytes(color=7)))
    real_replace = grm.os.replace
    for failing in (2, 3):
        calls = []

        def flaky(src, dst, failing=failing, calls=calls):
            calls.append(dst)
            if len(calls) == failing:
                raise OSError("disk full")
            return real_replace(src, dst)

        monkeypatch.setattr(grm.os, "replace", flaky)
        with pytest.raises(OSError, match="disk full"):
            grm.write_all(fresh, tmp_path / grm.SNAPSHOT, tmp_path / grm.PNG, tmp_path / grm.PAGE, "images/repo-growth.png")
        assert len(calls) == failing
        assert snapshot_files(tmp_path) == before  # same bytes, and no staging leftovers


OLD_STAGING_NAMES = (".repo-growth.png.new", ".metrics-snapshot.json.new", ".Repository-Growth.md.new")


def test_files_named_like_the_old_staging_names_survive_a_refresh_and_a_failed_one(tmp_path, monkeypatch):
    setup_tree(tmp_path)
    fresh = fixture()
    fresh["fetched_at"] = "2026-10-23T00:00:00Z"
    monkeypatch.setattr(grm, "draw_png", lambda snap, out: out.write_bytes(png_bytes(color=7)))
    homes = {".repo-growth.png.new": PNG_DIR, ".metrics-snapshot.json.new": WIKI_DIR, ".Repository-Growth.md.new": WIKI_DIR}
    bystanders = {}
    for name, rel in homes.items():
        path = tmp_path / rel / name
        path.write_bytes(b"not mine: " + name.encode())
        bystanders[path] = path.read_bytes()
    args = (fresh, tmp_path / grm.SNAPSHOT, tmp_path / grm.PNG, tmp_path / grm.PAGE, "images/repo-growth.png")
    real_replace = grm.os.replace
    monkeypatch.setattr(grm.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        grm.write_all(*args)
    assert {p: p.read_bytes() for p in bystanders} == bystanders
    monkeypatch.setattr(grm.os, "replace", real_replace)
    grm.write_all(*args)
    assert {p: p.read_bytes() for p in bystanders} == bystanders
    assert json.loads((tmp_path / grm.SNAPSHOT).read_text())["fetched_at"] == "2026-10-23T00:00:00Z"


def test_two_interleaved_writers_do_not_clobber_each_other(tmp_path, monkeypatch):
    setup_tree(tmp_path)
    first, second = fixture(), fixture()
    first["fetched_at"], second["fetched_at"] = "2026-10-23T00:00:00Z", "2026-10-24T00:00:00Z"
    monkeypatch.setattr(grm, "draw_png", lambda snap, out: out.write_bytes(png_bytes(color=7 if snap is first else 9)))
    paths = (tmp_path / grm.SNAPSHOT, tmp_path / grm.PNG, tmp_path / grm.PAGE, "images/repo-growth.png")
    real_replace = grm.os.replace
    state = {"inner": False}

    def interleave(src, dst):
        # The first writer has staged all three files and is about to install them; a second
        # writer now runs start to finish. With shared staging names it would overwrite or
        # consume the first writer's files.
        if not state["inner"]:
            state["inner"] = True
            grm.write_all(second, *paths)
        return real_replace(src, dst)

    monkeypatch.setattr(grm.os, "replace", interleave)
    grm.write_all(first, *paths)
    snap = json.loads(paths[0].read_text())
    assert snap["fetched_at"] == "2026-10-23T00:00:00Z"  # the writer that installs last wins, whole
    assert snap["png_sha256"] == grm.file_digest(paths[1])
    assert paths[2].read_text() == grm.render_page(snap, "images/repo-growth.png")
    leftovers = sorted(p.name for p in tmp_path.rglob("*") if p.is_file() and p.name.endswith(".new"))
    assert not leftovers


def test_staged_files_keep_the_mode_of_the_file_they_replace(tmp_path, monkeypatch):
    setup_tree(tmp_path)
    (tmp_path / grm.PAGE).chmod(0o640)
    monkeypatch.setattr(grm, "draw_png", lambda snap, out: out.write_bytes(png_bytes(color=7)))
    grm.write_all(fixture(), tmp_path / grm.SNAPSHOT, tmp_path / grm.PNG, tmp_path / grm.PAGE, "images/repo-growth.png")
    assert (tmp_path / grm.PAGE).stat().st_mode & 0o777 == 0o640


def test_home_embeds_the_chart_with_alt_text_from_the_metrics_branch():
    home = (ROOT / "docs" / "wiki" / "Home.md").read_text()
    assert "![" + grm.ALT_TEXT + "](" + grm.DEFAULT_IMAGE_URL + ")" in home
    assert "the as-of date is printed in the picture" in home


# -- the wiki and README are wired up -----------------------------------------------


def test_the_chart_is_linked_and_embedded_with_alt_text():
    readme = (ROOT / "README.md").read_text()
    assert "![" + grm.ALT_TEXT + "](" + grm.DEFAULT_IMAGE_URL + ")" in readme
    assert "scripts/gen_repo_metrics.py" in readme
    for name in ("Home.md", "_Sidebar.md", "Project-Status.md"):
        assert "(Repository-Growth.md)" in (ROOT / "docs" / "wiki" / name).read_text(), name
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "python3 -I scripts/gen_repo_metrics.py --check" in ci
