# SPDX-License-Identifier: Apache-2.0
"""The weekly work panel of the growth chart (issue #301).

The first week of a Monday-start chart is nearly empty by construction, and on a
0-100 axis a count of 1 is invisible, so the chart looked as if nothing happened.
What is proved, from fixed snapshots and with no plotting library (CI has none):
- issues opened are a series of the snapshot (schema 2), fetched with the same
  token as the other counts; schema 1 snapshots still validate, keep their hash
  and render the same page;
- every bar prints its count, a zero included, for a near-empty week (1 closed,
  0 pull requests), an empty week and a normal week;
- a rolling last-7-days group is part of the panel, so the recent past is never
  blank, and its counts are the sums over exactly seven UTC days.
"""

import copy
import datetime
import json
import sys
from pathlib import Path
from unittest import mock

import pytest
from test_repo_metrics import FakeGh, fixture

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_repo_metrics as grm

NO_HASHES = {"source_sha256": "0" * 64, "png_sha256": "0" * 64}


def v2(**over):
    """A schema 2 snapshot, taken on a Monday 07:00 UTC so the new week holds one close and no PR."""
    snap = {
        "schema": 2,
        "repo": "Example/Repo",
        "created_on": "2026-10-10",
        "fetched_at": "2026-10-26T07:00:00Z",
        "stars": {"2026-10-10": 2},
        "forks": {"2026-10-13": 1},
        "merged_prs": {"2026-10-11": 3, "2026-10-12": 4, "2026-10-21": 6},
        "opened_issues": {"2026-10-12": 2, "2026-10-22": 5, "2026-10-26": 2},
        "closed_issues": {"2026-10-13": 1, "2026-10-21": 3, "2026-10-26": 1},
    }
    snap.update(over)
    return snap


def texts(model):
    return {g["label"].split("\n")[0]: g["text"] for g in model["groups"]}


# -- the snapshot -----------------------------------------------------------------------


def test_schema_2_with_opened_issues_validates_and_schema_1_still_does():
    assert grm.validate_snapshot({**v2(), **NO_HASHES}) == []
    assert grm.validate_snapshot({**fixture(), **NO_HASHES}) == []  # schema 1, no opened_issues
    assert grm.SCHEMA == 2 and 1 in grm.SCHEMAS


@pytest.mark.parametrize(
    "mutate, expect",
    [
        (lambda s: s.pop("opened_issues"), "needs opened_issues"),
        (lambda s: s.update(schema=1), "needs schema 2"),
        (lambda s: s.update(schema=3), "schema is not"),
        (lambda s: s.update(schema=True), "schema is not"),
        (lambda s: s["opened_issues"].update({"2026-10-12": 0}), "bad value"),
        (lambda s: s["opened_issues"].update({"2026-10-12": "2"}), "bad value"),
        (lambda s: s["opened_issues"].update({"2026-12-31": 1}), "outside created_on..fetched_at"),
        (lambda s: s.update(opened_issues=[1]), "not an object"),
    ],
)
def test_bad_opened_issues_or_schema_fail_validation(mutate, expect):
    snap = v2()
    mutate(snap)
    found = grm.validate_snapshot({**snap, **NO_HASHES})
    assert found and any(expect in p for p in found), found


def test_the_hash_of_a_schema_1_snapshot_does_not_change_and_opened_issues_is_hashed():
    old = fixture()
    legacy = grm.source_digest(old)
    assert "opened_issues" not in old and grm.source_digest(copy.deepcopy(old)) == legacy
    new = v2()
    edited = copy.deepcopy(new)
    edited["opened_issues"]["2026-10-22"] = 6
    assert grm.source_digest(new) != grm.source_digest(edited)


def test_fetch_asks_for_issue_creation_times_only_and_stores_per_day_counts():
    class Gh(FakeGh):
        def __call__(self, args):
            if args[:2] == ["issue", "list"] and "all" in args:
                assert args[args.index("--json") + 1] == "createdAt"  # no title, author or body
                return json.dumps([{"createdAt": "2026-10-12T01:00:00Z"}, {"createdAt": "2026-10-12T09:00:00Z"}, {"createdAt": "2026-10-13T00:00:00Z"}])
            return super().__call__(args)

    fake = Gh()
    now = datetime.datetime(2026, 10, 22, 12, 0, 0, tzinfo=datetime.UTC)
    with mock.patch.object(grm, "run_gh", fake):
        snap = grm.fetch_snapshot("Example/Repo", now=now)
    assert snap["schema"] == 2
    assert snap["opened_issues"] == {"2026-10-12": 2, "2026-10-13": 1}
    assert snap["closed_issues"] == {"2026-10-12": 1}
    assert grm.validate_snapshot({**snap, **NO_HASHES}) == []


def test_the_page_gains_an_opened_column_for_schema_2_and_is_unchanged_for_schema_1():
    page = grm.render_page(v2())
    assert "| Week of | New stars | New forks | PRs merged | Issues opened | Issues closed | Stars so far | Forks so far |" in page
    assert "| 2026-10-26 (partial) | 0 | 0 | 0 | 2 | 1 | 2 | 1 |" in page
    assert "9 opened issues, 5 closed issues." in page  # 2 + 5 + 2 opened
    old = grm.render_page(fixture())
    assert "Issues opened" not in old and "| Week of | New stars | New forks | PRs merged | Issues closed |" in old


# -- the panel: every bar says its number --------------------------------------------------


def test_near_empty_current_week_prints_one_close_and_zero_pull_requests():
    model = grm.panel_model(v2())
    assert model["keys"] == ["merged_prs", "opened_issues", "closed_issues"]
    assert model["legend"] == ["PRs merged", "Issues opened", "Issues closed"]
    week = texts(model)["Oct 26"]
    assert week == ["0", "2", "1"]  # PRs, opened, closed: the 1 and the explicit 0 are both printed
    assert "(so far)" in [g for g in model["groups"] if g["kind"] == "week"][-1]["label"]


def test_an_empty_week_prints_zeros_not_blanks():
    model = grm.panel_model(v2(opened_issues={"2026-10-12": 2}, closed_issues={"2026-10-13": 1}, merged_prs={"2026-10-11": 3}))
    assert texts(model)["Oct 26"] == ["0", "0", "0"]
    assert texts(model)["Oct 19"] == ["0", "0", "0"]
    assert all(t != "" for g in model["groups"] for t in g["text"])


def test_a_normal_week_prints_its_sums_and_every_group_has_one_label_per_series():
    model = grm.panel_model(v2())
    assert texts(model)["Oct 19"] == ["6", "5", "3"]
    assert texts(model)["Oct 12"] == ["4", "2", "1"]
    assert texts(model)["Oct 05"] == ["3", "0", "0"]
    assert all(len(g["text"]) == len(model["keys"]) == len(g["counts"]) for g in model["groups"])
    assert all(g["text"] == [str(n) for n in g["counts"]] for g in model["groups"])


def test_a_schema_1_snapshot_has_no_opened_series_but_still_labels_every_bar():
    model = grm.panel_model(fixture())
    assert model["keys"] == ["merged_prs", "closed_issues"]
    assert all(len(g["text"]) == 2 for g in model["groups"])
    assert "opened" not in model["summary"]


# -- the rolling last seven days ---------------------------------------------------------------


def test_rolling_window_is_exactly_seven_utc_days_ending_on_the_snapshot_day():
    first, last, counts = grm.rolling_window(v2())
    assert (first.isoformat(), last.isoformat()) == ("2026-10-20", "2026-10-26")
    assert counts == {"merged_prs": 6, "opened_issues": 7, "closed_issues": 4}
    edge = v2(merged_prs={"2026-10-19": 50, "2026-10-20": 1, "2026-10-26": 1})
    assert grm.rolling_window(edge)[2]["merged_prs"] == 2  # Oct 19 is outside, Oct 20 and 26 are inside


def test_the_recent_past_is_never_blank_on_a_monday():
    snap = v2()
    monday = texts(grm.panel_model(snap))["Oct 26"]
    assert monday == ["0", "2", "1"]  # the Monday-start week is nearly empty
    rolling = grm.panel_model(snap)["groups"][-1]
    assert rolling["kind"] == "rolling" and rolling["counts"] == [6, 7, 4]
    assert rolling["label"].startswith("Last 7 days") and "Oct 20 to Oct 26" in rolling["label"]
    assert grm.panel_model(snap)["summary"] == "Last 7 days (2026-10-20 to 2026-10-26): 6 PRs merged, 7 issues opened, 4 issues closed"


def test_a_fully_empty_week_still_gets_a_rolling_group_of_zeros():
    model = grm.panel_model(v2(merged_prs={"2026-10-11": 1}, opened_issues={"2026-10-12": 1}, closed_issues={"2026-10-13": 1}))
    assert model["groups"][-1]["text"] == ["0", "0", "0"]


# -- drawing (only where a plotting library exists) -----------------------------------------------


@pytest.mark.parametrize("snap", [v2(), v2(opened_issues={"2026-10-12": 2}, closed_issues={"2026-10-13": 1}, merged_prs={"2026-10-11": 3}), fixture()])
def test_the_chart_draws_for_near_empty_empty_normal_and_schema_1_snapshots(tmp_path, snap):
    pytest.importorskip("matplotlib")
    out = tmp_path / "chart.png"
    grm.draw_png(snap, out)
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert 5_000 < out.stat().st_size < grm.MAX_PNG_BYTES


# -- round 2: the bar labels are drawn, the lists fail loudly, extremes stay readable ----------------------


class StubAxes:
    """Records every call; stands in for a matplotlib Axes so no plotting library is needed."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record

    def named(self, name):
        return [c for c in self.calls if c[0] == name]


def draw_stub(snap):
    ax = StubAxes()
    panel = grm.panel_model(snap)
    grm.draw_work_panel(ax, panel, {"merged_prs": "g", "opened_issues": "y", "closed_issues": "p"}, patch=lambda **kw: kw)
    return ax, panel


def test_every_bar_gets_exactly_one_printed_count_including_zeros_at_its_own_position():
    ax, panel = draw_stub(v2())
    printed = ax.named("text")
    bars = ax.named("bar")
    assert len(bars) == len(panel["keys"])
    assert len(printed) == len(panel["groups"]) * len(panel["keys"])
    for j, bar in enumerate(bars):  # one bar() call per series, one height per group
        for i, (x, h) in enumerate(zip(bar[1][0], bar[1][1], strict=True)):
            mine = [t for t in printed if t[1][0] == x]
            assert len(mine) == 1  # one label at this bar's x
            _, y, text = mine[0][1]
            assert text == str(h) == panel["groups"][i]["text"][j]
            assert y >= h  # at or above the top of its own bar
    assert [t[1][2] for t in printed].count("0") >= 3  # the explicit zeros are printed


def test_zero_height_bars_are_labeled_with_a_0_above_the_axis():
    ax, _ = draw_stub(v2(opened_issues={"2026-10-12": 2}, closed_issues={"2026-10-13": 1}, merged_prs={"2026-10-11": 3}))
    zeros = [t for t in ax.named("text") if t[1][2] == "0"]
    assert zeros and all(t[1][1] > 0 for t in zeros)


def test_headroom_leaves_the_top_of_the_panel_for_the_legend_at_any_scale():
    for tallest in (0, 1, 97, 123456):
        assert grm.panel_ylim_top(tallest) >= max(tallest, 1) * 1.3
    ax, _ = draw_stub(v2(opened_issues={"2026-10-12": 123456}))
    assert ax.named("set_ylim")[0][1] == (0, grm.panel_ylim_top(123456))


def test_legend_swatches_have_fixed_colors_not_taken_from_the_bars():
    ax, panel = draw_stub(v2(opened_issues={"2026-10-12": 123456}))
    legend = ax.named("legend")[0]
    assert [h["facecolor"] for h in legend[2]["handles"]] == ["g", "y", "p"]
    assert [h["label"] for h in legend[2]["handles"]] == panel["legend"]
    assert all("label" not in c[2] for c in ax.named("bar"))  # nothing else can feed the legend


def test_the_picture_palette_is_fixed_holds_every_series_color_and_fits_256():
    palette = grm.chart_palette()
    assert palette == grm.chart_palette() and 0 < len(palette) <= 256
    for text in grm.CHART_COLORS:
        assert tuple(int(text[i : i + 2], 16) for i in (1, 3, 5)) in palette  # exactly, so a swatch never shifts


def test_opened_issues_per_day_cap_matches_the_bundle_cap():
    assert grm.validate_snapshot({**v2(opened_issues={"2026-10-12": grm.MAX_DAY_COUNT}), **NO_HASHES}) == []
    found = grm.validate_snapshot({**v2(opened_issues={"2026-10-12": grm.MAX_DAY_COUNT + 1}), **NO_HASHES})
    assert any("bad value" in p for p in found)


class ListGh(FakeGh):
    """FakeGh, except the list call whose argument list holds `needle` answers with `size` rows."""

    def __init__(self, needle=None, size=0, key="closedAt"):
        super().__init__()
        self.needle, self.size, self.key = needle, size, key

    def __call__(self, args):
        self.calls.append(args)
        if self.needle and args[0] in ("pr", "issue") and args[1] == "list" and self.needle in args:
            return json.dumps([{self.key: "2026-10-12T00:00:00Z"}] * self.size)
        if args[:2] == ["issue", "list"] and "all" in args:
            return json.dumps([{"createdAt": "2026-10-12T00:00:00Z"}])
        return super().__call__(args)


NOW = datetime.datetime(2026, 10, 22, 12, tzinfo=datetime.UTC)


def test_every_list_call_is_pinned_to_the_list_limit():
    gh = ListGh()
    with mock.patch.object(grm, "run_gh", gh):
        grm.fetch_snapshot("Example/Repo", now=NOW)
    lists = {tuple(c) for c in gh.calls if c[:2] in (["pr", "list"], ["issue", "list"])}  # ListGh records some calls twice
    limits = [c[c.index("--limit") + 1] for c in sorted(lists)]
    assert grm.LIST_LIMIT == 5000 and limits == ["5000", "5000", "5000"]


@pytest.mark.parametrize(("needle", "key"), [("merged", "mergedAt"), ("closed", "closedAt"), ("all", "createdAt")])
def test_a_list_that_reaches_the_limit_fails_loudly_and_writes_nothing(tmp_path, monkeypatch, needle, key):
    with mock.patch.object(grm, "run_gh", ListGh(needle, grm.LIST_LIMIT, key)), pytest.raises(RuntimeError, match="5000"):
        grm.fetch_snapshot("Example/Repo", now=NOW)
    with mock.patch.object(grm, "run_gh", ListGh(needle, grm.LIST_LIMIT - 1, key)):
        grm.fetch_snapshot("Example/Repo", now=NOW)  # one short of the limit is fine
    drawn = []
    monkeypatch.setattr(grm, "draw_png", lambda *a: drawn.append(a))
    with mock.patch.object(grm, "run_gh", ListGh(needle, grm.LIST_LIMIT, key)):
        code = grm.main(["--refresh", "--root", str(tmp_path), "--repo", "Example/Repo"])
    assert code == 1 and drawn == [] and not any(tmp_path.rglob("*"))


def test_alt_text_and_wording_name_the_new_series_only_for_schema_2():
    new, old = grm.render_page(v2()), grm.render_page(fixture())
    assert "issues opened, issues closed and the last 7 days" in new
    assert "Forks, merged pull requests, issues opened and closed issues are read fresh every day." in new
    assert f"![{grm.ALT_TEXT}]" in old and "last 7 days" not in old
