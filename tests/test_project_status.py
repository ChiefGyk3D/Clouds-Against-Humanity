# SPDX-License-Identifier: Apache-2.0
"""The generated project status page (issue #259).

What is proved here, all offline (CI has no maintainer token and never calls
GitHub):
- each classification rule of the 2026-10-22 audit, one test per rule, so that
  reverting a rule fails a test: in flight, has merged PR, needs the maintainer,
  not started, the order between them, and what does not count;
- the board gaps (missing issues and PRs, closed but not Done) and the
  'board data may lag' line;
- the committed page is exactly the render of the committed snapshot, says when
  it was generated, and fails --check when edited by hand or stale;
- the fetch layer passes argument lists to gh and never a shell.
"""

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_project_status as gps

REPO = "Example/Repo"
STAMP = "2026-10-22T12:00:00Z"


def issue(n, state="OPEN", labels=(), title=None):
    return {"number": n, "title": title or f"Issue {n}", "state": state, "labels": list(labels)}


def pr(n, body="", state="OPEN", draft=False, ci="none", review=""):
    return {
        "number": n,
        "title": f"PR {n}",
        "state": state,
        "isDraft": draft,
        "body": body,
        "ci": ci,
        "reviewDecision": review,
    }


def item(kind, n, repo=REPO, **fields):
    return {"type": kind, "number": n, "repo": repo, "fields": fields}


def snap(issues=(), prs=(), board=(), total=None):
    return {
        "schema": gps.SCHEMA,
        "repo": REPO,
        "project": {"owner": "Example", "number": 4},
        "fetched_at": STAMP,
        "issues": list(issues),
        "prs": list(prs),
        "board": {"total": len(board) if total is None else total, "items": list(board)},
    }


def cats(snapshot):
    result = gps.classify(snapshot)["categories"]
    return {k: [e["issue"]["number"] for e in v] for k, v in result.items()}


# --- the link parser ------------------------------------------------------------


@pytest.mark.parametrize(
    "word", ["Closes", "closes", "Fixes", "Resolves", "Refs", "refs", "Fixed", "Resolved", "Closed"]
)
def test_every_keyword_links(word):
    assert gps.pr_links(f"{word} #7", REPO) == {7: "refs" if word.lower() == "refs" else "closes"}


def test_a_list_of_numbers_all_link():
    assert gps.pr_links("Closes #1, #2 and #3", REPO) == {1: "closes", 2: "closes", 3: "closes"}


def test_a_closing_word_beats_refs_for_the_same_number():
    assert gps.pr_links("Refs #4\nCloses #4", REPO) == {4: "closes"}
    assert gps.pr_links("Closes #4\nRefs #4", REPO) == {4: "closes"}


def test_a_bare_number_or_other_repo_does_not_link():
    assert gps.pr_links("see #5 and (#6)", REPO) == {}
    assert gps.pr_links("Closes Other/Thing#9", REPO) == {}
    assert gps.pr_links("Closes example/repo#9", REPO) == {9: "closes"}


def test_reduce_body_keeps_only_the_links():
    body = "Long text with a secret-looking line\nCloses #3, #4\nmore text"
    reduced = gps.reduce_body(body, REPO)
    assert "secret" not in reduced and "more text" not in reduced
    assert gps.pr_links(reduced, REPO) == {3: "closes", 4: "closes"}


# --- classification: one test per rule -----------------------------------------


@pytest.mark.parametrize("body", ["Closes #1", "Fixes #1", "Resolves #1", "Refs #1"])
def test_an_open_pr_makes_the_issue_in_flight(body):
    result = cats(snap([issue(1)], [pr(10, body)]))
    assert result[gps.IN_FLIGHT] == [1]
    assert result[gps.NOT_STARTED] == []


def test_a_draft_pr_still_counts_as_in_flight():
    assert cats(snap([issue(1)], [pr(10, "Closes #1", draft=True)]))[gps.IN_FLIGHT] == [1]


def test_a_merged_pr_makes_the_issue_a_review_for_close():
    result = cats(snap([issue(1)], [pr(10, "Closes #1", state="MERGED")]))
    assert result[gps.MERGED] == [1]
    assert result[gps.NOT_STARTED] == []


def test_a_refs_only_merged_pr_still_lands_in_review_but_is_flagged():
    snapshot = snap([issue(1)], [pr(10, "Refs #1", state="MERGED")])
    assert cats(snapshot)[gps.MERGED] == [1]
    page = gps.render(snapshot)
    assert "refs only" in page
    assert "A `Refs` link is not proof the work is done" in page


def test_a_closing_merged_pr_is_not_labeled_refs_only():
    page = gps.render(snap([issue(1)], [pr(10, "Closes #1", state="MERGED")]))
    row = next(line for line in page.splitlines() if line.startswith("| [#1]"))
    assert "(closes)" in row and "refs only" not in row


def test_an_open_pr_beats_a_merged_pr():
    prs = [pr(10, "Closes #1", state="MERGED"), pr(11, "Refs #1")]
    assert cats(snap([issue(1)], prs))[gps.IN_FLIGHT] == [1]


def test_the_needs_maintainer_label():
    result = cats(snap([issue(1, labels=["needs-maintainer"]), issue(2, labels=["bug"])]))
    assert result[gps.MAINTAINER] == [1]
    assert result[gps.NOT_STARTED] == [2]


def test_a_pr_outranks_the_maintainer_label():
    open_pr = cats(snap([issue(1, labels=["needs-maintainer"])], [pr(10, "Refs #1")]))
    assert open_pr[gps.IN_FLIGHT] == [1]
    merged = cats(snap([issue(1, labels=["needs-maintainer"])], [pr(10, "Closes #1", state="MERGED")]))
    assert merged[gps.MERGED] == [1]


def test_not_started_is_the_rest():
    assert cats(snap([issue(1)]))[gps.NOT_STARTED] == [1]


def test_a_pr_closed_without_merging_counts_for_nothing():
    assert cats(snap([issue(1)], [pr(10, "Closes #1", state="CLOSED")]))[gps.NOT_STARTED] == [1]


def test_closed_issues_are_not_classified():
    result = cats(snap([issue(1, state="CLOSED")], [pr(10, "Closes #1")]))
    assert all(v == [] for v in result.values())


def test_a_pr_in_another_repo_does_not_make_an_issue_in_flight():
    assert cats(snap([issue(1)], [pr(10, "Closes Other/Thing#1")]))[gps.NOT_STARTED] == [1]


# --- board gaps and the lag line -----------------------------------------------


def test_issues_and_prs_missing_from_the_board():
    snapshot = snap(
        [issue(1), issue(2)],
        [pr(10), pr(11)],
        [item("Issue", 1, Status="Next"), item("PullRequest", 10)],
    )
    gaps = gps.board_gaps(snapshot)
    assert [i["number"] for i in gaps["missing_issues"]] == [2]
    assert [p["number"] for p in gaps["missing_prs"]] == [11]


def test_a_board_item_from_another_repository_does_not_count():
    snapshot = snap([issue(1)], [], [item("Issue", 1, repo="Other/Thing", Status="Done")])
    assert [i["number"] for i in gps.board_gaps(snapshot)["missing_issues"]] == [1]


def test_closed_issue_not_done_on_the_board():
    snapshot = snap(
        [issue(1, "CLOSED"), issue(2, "CLOSED"), issue(3, "OPEN"), issue(4, "CLOSED")],
        [],
        [
            item("Issue", 1, Status="Next"),
            item("Issue", 2, Status="Done"),
            item("Issue", 3, Status="Next"),
            item("Issue", 4),
        ],
    )
    got = [(i["number"], s) for i, s in gps.board_gaps(snapshot)["closed_not_done"]]
    assert got == [(1, "Next"), (4, None)]


def test_a_closed_issue_missing_from_the_board_is_a_missing_issue_not_a_not_done_one():
    gaps = gps.board_gaps(snap([issue(1, "CLOSED")]))
    assert gaps["closed_not_done"] == []
    assert len(gaps["missing_issues"]) == 1


def test_the_lag_line_when_the_board_holds_fewer_items_than_there_are_issues():
    snapshot = snap([issue(1), issue(2), issue(3)], [], [item("Issue", 1)])
    page = gps.render(snapshot)
    assert "Board data may lag" in page
    assert "2 issues are not visible on the board" in page


def test_the_lag_line_uses_the_board_total_even_when_every_issue_is_listed():
    snapshot = snap([issue(1), issue(2)], [], [item("Issue", 1), item("Issue", 2)], total=1)
    assert "Board data may lag" in gps.render(snapshot)


def test_no_lag_line_when_the_board_is_complete():
    snapshot = snap([issue(1)], [], [item("Issue", 1, Status="Next")])
    page = gps.render(snapshot)
    assert "Board data may lag" not in page
    assert "| Issues not visible on the board | 0 |" in page


def test_prs_with_no_linked_issue():
    prs = [
        pr(10, "Closes #1"),
        pr(11, "no link here"),
        pr(12, "no link", state="MERGED"),
        pr(13, "no link", state="CLOSED"),
        pr(14, "Refs #1", state="MERGED"),
    ]
    page = gps.render(snap([issue(1)], prs))
    assert "## Pull requests with no linked issue (2)" in page
    section = page.split("## Pull requests with no linked issue")[1].split("## Reproduce")[0]
    assert "[#11]" in section and "[#12]" in section
    assert "[#10]" not in section and "[#13]" not in section and "[#14]" not in section


# --- page content --------------------------------------------------------------


def test_the_page_states_when_it_was_generated_and_the_commands():
    page = gps.render(snap([issue(1)]))
    assert f"**Generated at:** {STAMP} (UTC)" in page
    assert "gh issue list --repo Example/Repo --state all" in page
    assert "gen_project_status.py --refresh" in page


def test_open_prs_show_ci_and_review_state():
    page = gps.render(snap([issue(1)], [pr(10, "Closes #1", ci="failing", review="CHANGES_REQUESTED")]))
    row = next(line for line in page.splitlines() if line.startswith("| [#10]"))
    assert "failing" in row and "changes requested" in row


HOSTILE_TITLES = [
    "[click](https://evil.example)",
    "![x](https://evil.example/p.png)",
    "<script>alert(1)</script>",
    "a `b` | c `|` d",
    "see https://evil.example and www.evil.example and bob@evil.example",
    "line one\nline two\r\n| injected | row |",
    "x" * 5000,
    "\\[escaped](https://evil.example)",
    "# heading > quote * star _ under ~ tilde",
    "x\n# Heading\n[a](https://evil.example)",
]
CODE_SPAN = re.compile(r"`[^`]*`")
LEGIT_LINK = re.compile(r"\[#\d+\]\(https://github\.com/Example/Repo/(?:issues|pull)/\d+\)")


def rows_for(page, number):
    rows = [line for line in page.splitlines() if line.startswith(f"| [#{number}]")]
    assert rows
    return rows


def assert_inert(page, number):
    """Outside code spans a row holds only the one link this code builds."""
    for row in rows_for(page, number):
        bare = LEGIT_LINK.sub("#", CODE_SPAN.sub("", row))
        assert "](" not in bare and "![" not in bare and "<" not in bare and "http" not in bare, row
        assert row.count("`") % 2 == 0 and len(row) < 1200, row
    for line in page.splitlines():
        assert not line.startswith(("# Heading", "[a]("))


@pytest.mark.parametrize("title", HOSTILE_TITLES, ids=range(len(HOSTILE_TITLES)))
@pytest.mark.parametrize("where", ["issue", "pr", "unlinked", "closed"])
def test_a_hostile_title_stays_inert_everywhere(title, where):
    if where == "issue":
        snapshot, number = snap([issue(1, title=title)]), 1
    elif where == "pr":
        pull = pr(10, "Closes #1")
        pull["title"] = title
        snapshot, number = snap([issue(1)], [pull]), 10
    elif where == "unlinked":
        pull = pr(10, "nothing")
        pull["title"] = title
        snapshot, number = snap([], [pull]), 10
    else:
        snapshot, number = snap([issue(1, "CLOSED", title=title)], [], [item("Issue", 1, Status="Next")]), 1
    assert_inert(gps.render(snapshot), number)


def test_titles_are_code_spans_with_pipes_escaped_and_backticks_removed():
    page = gps.render(snap([issue(1, title="a | b `x` <i>")]))
    assert "`a \\| b x <i>`" in rows_for(page, 1)[0]


def test_a_long_title_is_cut():
    row = rows_for(gps.render(snap([issue(1, title="y" * 5000)])), 1)[0]
    assert "y" * 201 not in row and "..." in row


def test_a_newline_in_a_title_cannot_start_a_new_line():
    page = gps.render(snap([issue(1, title="x\n# Heading\n| [#9](https://evil.example) |")]))
    assert "`x # Heading \\| [#9](https://evil.example) \\|`" in page


def test_board_values_and_ci_are_inert_too():
    snapshot = snap(
        [issue(1)],
        [pr(10, "Closes #1", ci="[a](https://evil.example)", review="![b](https://evil.example/p.png)")],
        [item("Issue", 1, Status="[s](https://evil.example)", Size="<b>", Sprint="x")],
    )
    page = gps.render(snapshot)
    assert_inert(page, 1)
    assert_inert(page, 10)


def test_the_repo_name_must_be_a_plain_owner_slash_name():
    for bad in ("a/b](https://evil.example", "a b/c", "abc", "a/b/c"):
        broken = snap([issue(1)])
        broken["repo"] = bad
        assert gps.validate_snapshot(broken), bad
    broken = snap([issue(1)])
    broken["project"]["owner"] = "x](https://evil.example"
    assert gps.validate_snapshot(broken)


def test_render_is_deterministic_and_does_not_mutate_its_input():
    snapshot = snap([issue(2), issue(1)], [pr(10, "Closes #1")])
    before = copy.deepcopy(snapshot)
    assert gps.render(snapshot) == gps.render(snapshot)
    assert snapshot == before


@pytest.mark.parametrize(
    "rollup, want",
    [
        (None, "none"),
        ([], "none"),
        ([{"status": "COMPLETED", "conclusion": "SUCCESS"}, {"status": "COMPLETED", "conclusion": "SKIPPED"}], "passing"),
        ([{"status": "COMPLETED", "conclusion": "SUCCESS"}, {"status": "IN_PROGRESS", "conclusion": ""}], "pending"),
        ([{"status": "IN_PROGRESS"}, {"status": "COMPLETED", "conclusion": "FAILURE"}], "failing"),
        ([{"state": "FAILURE"}], "failing"),
        ([{"state": "PENDING"}], "pending"),
        ([{"state": "SUCCESS"}], "passing"),
    ],
)
def test_ci_state(rollup, want):
    assert gps.ci_state(rollup) == want


# --- the committed page and snapshot -------------------------------------------


def test_the_committed_page_matches_the_committed_snapshot():
    assert gps.check_page(ROOT) == []


def test_the_committed_page_says_when_it_was_generated():
    page = (ROOT / gps.PAGE).read_text(encoding="utf-8")
    match = gps.STAMP_LINE_RE.search(page)
    assert match and gps.STAMP_RE.match(match.group(1))


def test_the_committed_snapshot_is_valid():
    snapshot = json.loads((ROOT / gps.SNAPSHOT).read_text(encoding="utf-8"))
    assert gps.validate_snapshot(snapshot) == []


def run_script(*args, root=None):
    cmd = [sys.executable, "-I", str(ROOT / "scripts" / "gen_project_status.py"), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def make_root(tmp_path, snapshot=None):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    snapshot = snapshot or snap([issue(1)], [pr(10, "Refs #1")], [item("Issue", 1, Status="Next")])
    (tmp_path / gps.SNAPSHOT).write_text(json.dumps(snapshot))
    return tmp_path


def test_check_passes_after_a_render(tmp_path):
    root = make_root(tmp_path)
    assert run_script(root=root).returncode == 0
    assert run_script("--check", root=root).returncode == 0


def test_check_fails_on_a_hand_edit_with_a_clear_message(tmp_path):
    root = make_root(tmp_path)
    run_script(root=root)
    page = root / gps.PAGE
    page.write_text(page.read_text() + "\nhand edit\n")
    result = run_script("--check", root=root)
    assert result.returncode == 1
    assert "does not match" in result.stderr and "--refresh" in result.stderr


def test_check_fails_when_the_snapshot_changed_but_the_page_did_not(tmp_path):
    root = make_root(tmp_path)
    run_script(root=root)
    changed = json.loads((root / gps.SNAPSHOT).read_text())
    changed["issues"].append(issue(2))
    (root / gps.SNAPSHOT).write_text(json.dumps(changed))
    assert run_script("--check", root=root).returncode == 1


def test_check_fails_when_the_stamp_is_missing_or_does_not_match(tmp_path):
    root = make_root(tmp_path)
    run_script(root=root)
    page = root / gps.PAGE
    good = page.read_text()
    page.write_text(good.replace("**Generated at:** ", "**Made at:** "))
    missing = run_script("--check", root=root)
    assert missing.returncode == 1 and "time stamp" in missing.stderr
    page.write_text(good.replace(STAMP, "2026-01-01T00:00:00Z"))
    other = run_script("--check", root=root)
    assert other.returncode == 1 and "snapshot was taken" in other.stderr


def test_check_fails_for_a_missing_page_or_snapshot(tmp_path):
    root = make_root(tmp_path)
    assert run_script("--check", root=root).returncode == 1
    (root / gps.SNAPSHOT).unlink()
    assert run_script("--check", root=root).returncode == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(fetched_at="yesterday"),
        lambda s: s.update(schema=99),
        lambda s: s.pop("board"),
        lambda s: s["issues"].append({"number": "x"}),
    ],
)
def test_an_invalid_snapshot_fails_check(tmp_path, mutate):
    bad = snap([issue(1)])
    mutate(bad)
    root = make_root(tmp_path, bad)
    assert run_script("--check", root=root).returncode == 1


# --- the fetch layer -----------------------------------------------------------


def test_gh_is_called_with_an_argument_list_and_no_shell(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(gps.subprocess, "run", fake_run)
    assert gps.run_gh(["issue", "list", "--repo", "a/b; rm -rf x"]) == "[]"
    args, kwargs = calls[0]
    assert isinstance(args, list) and args[0] == "gh"
    assert not kwargs.get("shell")


def test_a_gateway_error_is_retried_and_other_errors_are_not(monkeypatch):
    monkeypatch.setattr(gps.time, "sleep", lambda s: None)
    outcomes = iter(
        [
            subprocess.CompletedProcess([], 1, "", "HTTP 504: gateway"),
            subprocess.CompletedProcess([], 0, "ok", ""),
        ]
    )
    monkeypatch.setattr(gps.subprocess, "run", lambda *a, **k: next(outcomes))
    assert gps.run_gh(["x"]) == "ok"
    count = []

    def hard(*a, **k):
        count.append(1)
        return subprocess.CompletedProcess([], 1, "", "HTTP 401: bad credentials")

    monkeypatch.setattr(gps.subprocess, "run", hard)
    with pytest.raises(RuntimeError):
        gps.run_gh(["x"])
    assert len(count) == 1


def test_board_nodes_are_reduced_to_the_fields_the_page_uses():
    nodes = [
        {
            "content": {"__typename": "Issue", "number": 5, "repository": {"nameWithOwner": REPO}},
            "fieldValues": {
                "nodes": [
                    {"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": "Next", "field": {"name": "Status"}},
                    {"__typename": "ProjectV2ItemFieldIterationValue", "title": "S1", "field": {"name": "Sprint"}},
                    {"__typename": "ProjectV2ItemFieldTextValue", "text": "Claude", "field": {"name": "Agent"}},
                    {"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": "P1", "field": {"name": "Priority"}},
                    {"__typename": "ProjectV2ItemFieldRepositoryValue"},
                ]
            },
        },
        {"content": {"__typename": "DraftIssue"}, "fieldValues": {"nodes": []}},
        {"content": None, "fieldValues": {"nodes": []}},
    ]
    assert gps.parse_board_nodes(nodes) == [
        {"type": "Issue", "number": 5, "repo": REPO, "fields": {"Status": "Next", "Sprint": "S1", "Agent": "Claude"}}
    ]


def test_refresh_writes_the_snapshot_and_the_page(tmp_path, monkeypatch):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    fresh = snap([issue(1)], [pr(10, "Closes #1")], [item("Issue", 1, Status="Next")])
    monkeypatch.setattr(gps, "fetch_snapshot", lambda repo, owner, project: fresh)
    assert gps.main(["--refresh", "--root", str(tmp_path)]) == 0
    assert json.loads((tmp_path / gps.SNAPSHOT).read_text()) == fresh
    assert gps.check_page(tmp_path) == []


def test_a_failed_refresh_leaves_the_files_alone(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    run_script(root=root)
    before = (root / gps.PAGE).read_text(), (root / gps.SNAPSHOT).read_text()

    def boom(repo, owner, project):
        raise RuntimeError("no network")

    monkeypatch.setattr(gps, "fetch_snapshot", boom)
    assert gps.main(["--refresh", "--root", str(root)]) == 1
    assert ((root / gps.PAGE).read_text(), (root / gps.SNAPSHOT).read_text()) == before
    assert "refresh failed" in capsys.readouterr().err
