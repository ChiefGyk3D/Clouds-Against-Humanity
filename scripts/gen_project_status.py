# SPDX-License-Identifier: Apache-2.0
"""Generate docs/wiki/Project-Status.md from a saved snapshot of GitHub.

The page answers "where exactly are we" from GitHub itself, never from memory.
Three parts, kept apart on purpose:

  render(snapshot)   a pure function: already-fetched JSON in, Markdown out. No
                     network, no clock. Every test uses it with fixtures.
  fetch_snapshot()   a thin layer over the `gh` CLI. Argument lists only, never
                     a shell. Needs the maintainer's login; CI never runs it.
  main()             --refresh fetches and rewrites the snapshot and the page;
                     --check (the default gate) re-renders the committed
                     snapshot and fails when the committed page differs, so a
                     hand edit, a stale page or a missing time stamp all fail.

Why a snapshot: CI has no maintainer token and the Projects data is private to
the maintainer's login. The snapshot (docs/wiki/.status-snapshot.json) is what a
refresh saw; the page is a pure function of it. The page therefore shows when
the snapshot was taken, and a reader can re-run the stated commands to compare.

Usage (from anywhere inside a clone):
  python -I scripts/gen_project_status.py --check      offline; exit 1 when stale
  python -I scripts/gen_project_status.py              re-render from the snapshot
  python -I scripts/gen_project_status.py --refresh    fetch live data (needs gh
                                                       logged in as the maintainer),
                                                       then rewrite both files

Exit codes: 0 ok, 1 stale or invalid page or snapshot (--check), or a fetch
failure (--refresh), 2 usage.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

SNAPSHOT = Path("docs") / "wiki" / ".status-snapshot.json"
PAGE = Path("docs") / "wiki" / "Project-Status.md"

DEFAULT_REPO = "ChiefGyk3D/Clouds-Against-Humanity"
DEFAULT_OWNER = "ChiefGyk3D"
DEFAULT_PROJECT = 4
SCHEMA = 1

BOARD_FIELDS = ("Status", "Kind", "Area", "Epic", "Size", "Agent", "Sprint")
MAINTAINER_LABEL = "needs-maintainer"
DONE_STATUS = "Done"

STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STAMP_LINE_RE = re.compile(r"^\*\*Generated at:\*\* (\S+) \(UTC\)", re.MULTILINE)

CLOSING_WORDS = ("close", "closes", "closed", "fix", "fixes", "fixed", "resolve", "resolves", "resolved")
REF_WORDS = ("ref", "refs", "reference", "references")
KEYWORD_RE = re.compile(
    r"\b(" + "|".join(CLOSING_WORDS + REF_WORDS) + r")\b:?[ \t]+((?:#\d+|[\w.-]+/[\w.-]+#\d+)(?:[ \t]*(?:,|and|&)[ \t]*(?:#\d+|[\w.-]+/[\w.-]+#\d+))*)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"([\w.-]+/[\w.-]+)?#(\d+)")


# --- parsing ------------------------------------------------------------------


def pr_links(body: str, repo: str) -> dict[int, str]:
    """Issue numbers a PR body mentions with a keyword: {number: "closes" | "refs"}.

    A closing keyword wins over Refs for the same number. A reference into some
    other repository is ignored.
    """
    found: dict[int, str] = {}
    for match in KEYWORD_RE.finditer(body or ""):
        kind = "refs" if match.group(1).lower() in REF_WORDS else "closes"
        for repo_part, number in NUMBER_RE.findall(match.group(2)):
            if repo_part and repo_part.lower() != repo.lower():
                continue
            n = int(number)
            if found.get(n) != "closes":
                found[n] = kind
    return found


def reduce_body(body: str, repo: str) -> str:
    """Keep only the linking phrases of a PR body, so the snapshot stays small."""
    return "\n".join(
        f"{m.group(1)} {m.group(2)}" for m in KEYWORD_RE.finditer(body or "")
    )


def ci_state(rollup: list[dict] | None) -> str:
    """Reduce statusCheckRollup to passing, failing, pending or none."""
    if not rollup:
        return "none"
    state = "passing"
    for item in rollup:
        conclusion = (item.get("conclusion") or "").upper()
        status = (item.get("status") or "").upper()
        context = (item.get("state") or "").upper()
        if conclusion in {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"} or context in {"FAILURE", "ERROR"}:
            return "failing"
        if (status and status != "COMPLETED") or context in {"PENDING", "EXPECTED"}:
            state = "pending"
    return state


# --- classification -----------------------------------------------------------

IN_FLIGHT = "in flight"
MERGED = "has merged PR"
MAINTAINER = "needs the maintainer"
NOT_STARTED = "not started"
CATEGORIES = (IN_FLIGHT, MERGED, MAINTAINER, NOT_STARTED)


def classify(snapshot: dict) -> dict:
    """The 2026-10-22 audit's classification, as data.

    Order matters and is the audit's: an open PR that mentions the issue (any
    keyword, Refs included) makes it IN-FLIGHT; otherwise a merged PR that
    mentions it makes it HAS MERGED PR (a review-for-close candidate, not
    proof of done); otherwise the needs-maintainer label; otherwise NOT STARTED.
    A PR that was closed without merging counts for nothing.
    """
    repo = snapshot["repo"]
    open_links: dict[int, list[tuple[int, str]]] = {}
    merged_links: dict[int, list[tuple[int, str]]] = {}
    pr_linked: dict[int, dict[int, str]] = {}
    for pr in snapshot["prs"]:
        links = pr_links(pr.get("body", ""), repo)
        pr_linked[pr["number"]] = links
        if pr["state"] == "OPEN":
            target = open_links
        elif pr["state"] == "MERGED":
            target = merged_links
        else:
            continue
        for n, kind in links.items():
            target.setdefault(n, []).append((pr["number"], kind))

    categories: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    for issue in snapshot["issues"]:
        if issue["state"] != "OPEN":
            continue
        n = issue["number"]
        if n in open_links:
            cat, prs = IN_FLIGHT, open_links[n]
        elif n in merged_links:
            cat, prs = MERGED, merged_links[n]
        elif MAINTAINER_LABEL in issue.get("labels", []):
            cat, prs = MAINTAINER, []
        else:
            cat, prs = NOT_STARTED, []
        categories[cat].append({"issue": issue, "prs": sorted(prs)})
    for items in categories.values():
        items.sort(key=lambda e: e["issue"]["number"])
    return {"categories": categories, "pr_linked": pr_linked}


def board_gaps(snapshot: dict) -> dict:
    repo = snapshot["repo"]
    items = [i for i in snapshot["board"]["items"] if i.get("repo", repo).lower() == repo.lower()]
    on_board = {(i["type"], i["number"]): i for i in items}
    missing_issues = [i for i in snapshot["issues"] if ("Issue", i["number"]) not in on_board]
    missing_prs = [p for p in snapshot["prs"] if ("PullRequest", p["number"]) not in on_board]
    not_done = []
    for issue in snapshot["issues"]:
        entry = on_board.get(("Issue", issue["number"]))
        if issue["state"] == "CLOSED" and entry is not None:
            status = entry.get("fields", {}).get("Status")
            if status != DONE_STATUS:
                not_done.append((issue, status))
    on_board_issues = sum(1 for key in on_board if key[0] == "Issue")
    return {
        "on_board": on_board,
        "missing_issues": missing_issues,
        "missing_prs": missing_prs,
        "closed_not_done": not_done,
        "board_issue_count": on_board_issues,
    }


# --- rendering ----------------------------------------------------------------


MAX_CELL = 200
PIPE_LOOKALIKE = "\u2223"  # DIVIDES, looks like a pipe
BACKSLASH_LOOKALIKE = "\u29f5"  # REVERSE SOLIDUS OPERATOR, looks like a backslash
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def cell(value: object) -> str:
    """Render untrusted text (a title, a board value) as an inert code span.

    A title is typed by anyone who can open an issue or a pull request, so it
    must never become Markdown: no link, image, autolink, HTML or table break.
    Inside a code span none of those is interpreted. Control characters and
    backticks are removed (a backtick would end the span), whitespace is
    collapsed, the text is cut to MAX_CELL characters, and every pipe and
    backslash becomes a look-alike character (see the comment below).
    """
    text = "".join(" " if unicodedata.category(c) in ("Cc", "Zl", "Zp") else c for c in str(value))
    text = " ".join(text.replace("`", "").split())
    if len(text) > MAX_CELL:
        text = text[: MAX_CELL - 3] + "..."
    if not text:
        return ""
    # A pipe or a backslash is replaced by a look-alike, never escaped. GFM
    # splits a table row on `\|` before it parses inline Markdown, so any escaping
    # scheme that keeps a backslash or a pipe can be made to disagree with the
    # code span. With neither character present in the cell, nothing can.
    text = text.replace("|", PIPE_LOOKALIKE).replace("\\", BACKSLASH_LOOKALIKE)
    return "`" + text + "`"


def ref(snapshot: dict, kind: str, number: int) -> str:
    segment = "pull" if kind == "pr" else "issues"
    return f"[#{number}](https://github.com/{snapshot['repo']}/{segment}/{number})"


def pr_refs(snapshot: dict, prs: list[tuple[int, str]]) -> str:
    return ", ".join(
        f"{ref(snapshot, 'pr', n)} ({'refs only' if kind == 'refs' else 'closes'})"
        for n, kind in prs
    )


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out + [""]


def board_cell(gaps: dict, number: int, field: str) -> str:
    entry = gaps["on_board"].get(("Issue", number))
    if entry is None:
        return "not on board"
    return cell(entry.get("fields", {}).get(field) or "")


def section_for(snapshot: dict, gaps: dict, title: str, blurb: str, entries: list[dict], with_prs: bool) -> list[str]:
    out = [f"### {title} ({len(entries)})", "", blurb, ""]
    if not entries:
        return out + ["None.", ""]
    headers = ["Issue", "Title", "Board status", "Size", "Sprint"] + (["Linked PRs"] if with_prs else [])
    rows = []
    for e in entries:
        n = e["issue"]["number"]
        row = [
            ref(snapshot, "issue", n),
            cell(e["issue"]["title"]),
            board_cell(gaps, n, "Status"),
            board_cell(gaps, n, "Size"),
            board_cell(gaps, n, "Sprint"),
        ]
        if with_prs:
            row.append(pr_refs(snapshot, e["prs"]))
        rows.append(row)
    return out + table(headers, rows)


HEADER = """\
<!-- GENERATED from docs/wiki/.status-snapshot.json by scripts/gen_project_status.py. Do not
edit this page by hand: the snapshot is refreshed from the maintainer's GitHub login with
`python -I scripts/gen_project_status.py --refresh`. CI fails when this page does not match
the snapshot. -->

# Project status: where we are

> Prerequisites: [How this project is planned](How-This-Project-Is-Planned.md), because it explains the board, sprints and sizes this page counts.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

This page is regenerated from GitHub's own issues, pull requests and project board, not from memory. It is a reference page, not a lesson. A refresh saves a snapshot of what GitHub said at one moment, and everything below is counted and listed by code from that snapshot.
"""

HEURISTICS = """\
## How each open issue is classified

The rules are the ones the 2026-10-22 audit used, applied in this order. Only an issue that is open is classified.

1. **In flight:** an open pull request mentions the issue with `Closes`, `Fixes`, `Resolves` or `Refs` followed by `#N`.
2. **Has merged PR:** no open pull request, but a merged one mentions it the same way. This is a candidate to review for closing. **A `Refs` link is not proof the work is done**: it only says the pull request touched the issue, so each row says whether the link was a closing word or `refs only`.
3. **Needs the maintainer:** neither of the above, and the issue has the `needs-maintainer` label.
4. **Not started:** none of the above.

A pull request closed without merging counts for nothing. A reference into another repository is ignored. Linking is by keyword in the pull request body; a number in a title or a branch name is not a link.\n\nTitles and other text from GitHub are shown as plain code text. Special characters in titles are shown as look-alikes: a pipe appears as \u2223 and a backslash as \u29f5, so no title can break a table.
"""


def render(snapshot: dict) -> str:
    repo = snapshot["repo"]
    stamp = snapshot["fetched_at"]
    cls = classify(snapshot)
    cats = cls["categories"]
    gaps = board_gaps(snapshot)
    issues, prs = snapshot["issues"], snapshot["prs"]
    open_issues = [i for i in issues if i["state"] == "OPEN"]
    open_prs = [p for p in prs if p["state"] == "OPEN"]
    merged_prs = [p for p in prs if p["state"] == "MERGED"]
    board_total = snapshot["board"]["total"]
    hidden = len(gaps["missing_issues"])

    out = [HEADER.rstrip("\n"), ""]
    out += [f"**Generated at:** {stamp} (UTC), from `{repo}` and the maintainer's project board. This is a snapshot: GitHub may have moved since.", ""]
    if board_total < len(issues) or hidden:
        out += [
            f"> **Board data may lag.** The board holds {board_total} items and the repository has {len(issues)} issues, so {hidden} issues are not visible on the board. GitHub Projects had an incident on 2026-10-22 that delayed newly added items; the board lists below can undercount until they appear.",
            "",
        ]
    out += ["## The counts", ""]
    out += table(
        ["What", "Count"],
        [
            ["Issues, all states", str(len(issues))],
            ["Open issues", str(len(open_issues))],
            ["Open issues in flight", str(len(cats[IN_FLIGHT]))],
            ["Open issues with a merged PR, to review for close", str(len(cats[MERGED]))],
            ["Open issues that need the maintainer", str(len(cats[MAINTAINER]))],
            ["Open issues not started", str(len(cats[NOT_STARTED]))],
            ["Open pull requests", str(len(open_prs))],
            ["Merged pull requests", str(len(merged_prs))],
            ["Items on the board (all repositories)", str(board_total)],
            ["Issues not visible on the board", str(hidden)],
            ["Pull requests not visible on the board", str(len(gaps["missing_prs"]))],
            ["Closed issues not Done on the board", str(len(gaps["closed_not_done"]))],
        ],
    )
    out += [HEURISTICS.rstrip("\n"), ""]
    out += ["## Open issues by state", ""]
    out += section_for(snapshot, gaps, "In flight", "An open pull request mentions each of these.", cats[IN_FLIGHT], True)
    out += section_for(snapshot, gaps, "Has merged PR: review for close", "A merged pull request mentions each of these and the issue is still open. Check the work against the issue before closing; a `refs only` link is not proof of done.", cats[MERGED], True)
    out += section_for(snapshot, gaps, "Needs the maintainer", "Labeled `needs-maintainer`, with no pull request mentioning it.", cats[MAINTAINER], False)
    out += section_for(snapshot, gaps, "Not started", "Open, no pull request mentions it, no maintainer label.", cats[NOT_STARTED], False)

    out += [f"## Open pull requests ({len(open_prs)})", ""]
    if open_prs:
        rows = []
        for p in sorted(open_prs, key=lambda p: p["number"]):
            links = cls["pr_linked"][p["number"]]
            linked = ", ".join(f"{ref(snapshot, 'issue', n)} ({'refs only' if k == 'refs' else 'closes'})" for n, k in sorted(links.items())) or "none"
            rows.append([
                ref(snapshot, "pr", p["number"]),
                cell(p["title"]),
                "draft" if p.get("isDraft") else "ready",
                cell(p.get("ci", "none")),
                cell((p.get("reviewDecision") or "none").lower().replace("_", " ")),
                linked,
            ])
        out += table(["Pull request", "Title", "Draft", "CI", "Review", "Linked issues"], rows)
    else:
        out += ["None.", ""]

    out += ["## Board gaps", "", "These come from the project board's items, read through GitHub's GraphQL API. See the lag note at the top when the numbers look low.", ""]
    out += [f"### Issues missing from the board ({hidden})", ""]
    if gaps["missing_issues"]:
        out += table(["Issue", "State", "Title"], [[ref(snapshot, "issue", i["number"]), i["state"].lower(), cell(i["title"])] for i in gaps["missing_issues"]])
    else:
        out += ["None.", ""]
    out += [f"### Pull requests missing from the board ({len(gaps['missing_prs'])})", ""]
    if gaps["missing_prs"]:
        out += table(["Pull request", "State", "Title"], [[ref(snapshot, "pr", p["number"]), p["state"].lower(), cell(p["title"])] for p in gaps["missing_prs"]])
    else:
        out += ["None.", ""]
    out += [f"### Closed issues not Done on the board ({len(gaps['closed_not_done'])})", ""]
    if gaps["closed_not_done"]:
        out += table(["Issue", "Board status", "Title"], [[ref(snapshot, "issue", i["number"]), cell(s or "no status"), cell(i["title"])] for i, s in gaps["closed_not_done"]])
    else:
        out += ["None.", ""]

    unlinked = [p for p in prs if p["state"] in ("OPEN", "MERGED") and not cls["pr_linked"][p["number"]]]
    out += [f"## Pull requests with no linked issue ({len(unlinked)})", "", "Open or merged pull requests whose body has no `Closes`, `Fixes`, `Resolves` or `Refs` followed by an issue number.", ""]
    if unlinked:
        out += table(["Pull request", "State", "Title"], [[ref(snapshot, "pr", p["number"]), p["state"].lower(), cell(p["title"])] for p in sorted(unlinked, key=lambda p: p["number"])])
    else:
        out += ["None.", ""]

    owner, number = snapshot["project"]["owner"], snapshot["project"]["number"]
    out += [
        "## Reproduce every number",
        "",
        f"Run these from the maintainer's GitHub login (the board is private to it). `{repo}` is the repository and `{owner}` / `{number}` the owner and number of the project.",
        "",
        "```bash",
        f"gh issue list --repo {repo} --state all --limit 5000 --json number,title,state,labels,createdAt,closedAt,stateReason",
        f"gh pr list --repo {repo} --state all --limit 5000 --json number,title,state,isDraft,mergedAt,createdAt,body,headRefName",
        f"gh pr list --repo {repo} --state open --limit 500 --json number,statusCheckRollup,reviewDecision",
        f"gh project item-list {number} --owner {owner} --limit 5000 --format json",
        "python -I scripts/gen_project_status.py --refresh   # does all of the above and rewrites this page",
        "```",
        "",
        "The classification above is applied to that data by `scripts/gen_project_status.py`. CI re-renders the committed snapshot, `docs/wiki/.status-snapshot.json`, and fails when this page does not match it or has no generated-at time; it does not call GitHub. The page is only as current as the last refresh, which the maintainer runs from a login: by hand, from a scheduled local job, or from a hook in the Scrum Around and Find Out (SAFO) audit.",
        "",
        "Next: [Roadmap](Roadmap.md), which says what is built and what is only planned; this page says what the work is doing right now. For how attention and work have moved week by week, see [Repository growth](Repository-Growth.md).",
    ]
    return "\n".join(out).rstrip("\n") + "\n"


# --- snapshot validation ------------------------------------------------------


def validate_snapshot(snap: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(snap, dict):
        return ["snapshot is not a JSON object"]
    if snap.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    for key in ("repo", "fetched_at"):
        if not isinstance(snap.get(key), str):
            problems.append(f"{key!r} missing")
    repo = snap.get("repo")
    if isinstance(repo, str) and not (repo.count("/") == 1 and all(NAME_RE.match(x) for x in repo.split("/"))):
        problems.append("repo is not owner/name")
    if isinstance(snap.get("fetched_at"), str) and not STAMP_RE.match(snap["fetched_at"]):
        problems.append("fetched_at is not YYYY-MM-DDTHH:MM:SSZ")
    project = snap.get("project")
    if not (isinstance(project, dict) and isinstance(project.get("owner"), str) and NAME_RE.match(project["owner"]) and isinstance(project.get("number"), int)):
        problems.append("project owner/number missing")
    for key in ("issues", "prs"):
        if not isinstance(snap.get(key), list):
            problems.append(f"{key!r} is not a list")
            continue
        for item in snap[key]:
            if not (isinstance(item, dict) and isinstance(item.get("number"), int) and isinstance(item.get("title"), str) and item.get("state") in {"OPEN", "CLOSED", "MERGED"}):
                problems.append(f"bad entry in {key!r}")
                break
    board = snap.get("board")
    if not (isinstance(board, dict) and isinstance(board.get("total"), int) and isinstance(board.get("items"), list)):
        problems.append("board total/items missing")
    return problems


# --- fetch layer (maintainer login only) -------------------------------------

GRAPHQL = """
query($owner: String!, $number: Int!, $after: String) {
  user(login: $owner) {
    projectV2(number: $number) {
      items(first: 100, after: $after) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          content {
            __typename
            ... on Issue { number repository { nameWithOwner } }
            ... on PullRequest { number repository { nameWithOwner } }
          }
          fieldValues(first: 30) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldIterationValue { title field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2FieldCommon { name } } }
            }
          }
        }
      }
    }
  }
}
"""


def run_gh(args: list[str]) -> str:
    """Run gh with an argument list. Never a shell."""
    result = None
    for attempt in range(3):
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, check=False, timeout=300
        )
        # Retry only a gateway error; every other failure is final.
        if result.returncode == 0 or "HTTP 50" not in result.stderr:
            break
        time.sleep(2 * (attempt + 1))
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def parse_board_nodes(nodes: list[dict]) -> list[dict]:
    items = []
    for node in nodes:
        content = node.get("content") or {}
        if content.get("__typename") not in ("Issue", "PullRequest"):
            continue
        fields: dict[str, str] = {}
        for fv in (node.get("fieldValues") or {}).get("nodes", []):
            name = (fv.get("field") or {}).get("name")
            if name not in BOARD_FIELDS:
                continue
            value = fv.get("name", fv.get("title", fv.get("text", fv.get("number"))))
            if value is not None:
                fields[name] = str(value)
        items.append(
            {
                "type": content["__typename"],
                "number": content["number"],
                "repo": content["repository"]["nameWithOwner"],
                "fields": fields,
            }
        )
    return items


def fetch_board(owner: str, number: int) -> dict:
    items: list[dict] = []
    total = 0
    after = ""
    while True:
        args = ["api", "graphql", "-f", f"query={GRAPHQL}", "-f", f"owner={owner}", "-F", f"number={number}"]
        if after:
            args += ["-f", f"after={after}"]
        data = json.loads(run_gh(args))["data"]["user"]["projectV2"]["items"]
        total = data["totalCount"]
        items += parse_board_nodes(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        after = data["pageInfo"]["endCursor"]
    items.sort(key=lambda i: (i["type"], i["number"]))
    return {"total": total, "items": items}


def fetch_snapshot(repo: str, owner: str, project: int) -> dict:
    issues_raw = json.loads(run_gh(["issue", "list", "--repo", repo, "--state", "all", "--limit", "5000", "--json", "number,title,state,labels,createdAt,closedAt,stateReason"]))
    prs_raw = json.loads(run_gh(["pr", "list", "--repo", repo, "--state", "all", "--limit", "5000", "--json", "number,title,state,isDraft,mergedAt,createdAt,body,headRefName"]))
    # CI and review state are fetched for open PRs only: asking for them on
    # every PR in the history times out on GitHub's side.
    open_raw = json.loads(run_gh(["pr", "list", "--repo", repo, "--state", "open", "--limit", "500", "--json", "number,statusCheckRollup,reviewDecision"]))
    open_by_number = {p["number"]: p for p in open_raw}
    issues = [
        {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "labels": sorted(label["name"] for label in i.get("labels", [])),
            "createdAt": i.get("createdAt"),
            "closedAt": i.get("closedAt"),
            "stateReason": i.get("stateReason"),
        }
        for i in sorted(issues_raw, key=lambda i: i["number"])
    ]
    prs = [
        {
            "number": p["number"],
            "title": p["title"],
            "state": p["state"],
            "isDraft": bool(p.get("isDraft")),
            "createdAt": p.get("createdAt"),
            "mergedAt": p.get("mergedAt"),
            "headRefName": p.get("headRefName"),
            "body": reduce_body(p.get("body") or "", repo),
            "ci": ci_state(open_by_number.get(p["number"], {}).get("statusCheckRollup")),
            "reviewDecision": open_by_number.get(p["number"], {}).get("reviewDecision") or "",
        }
        for p in sorted(prs_raw, key=lambda p: p["number"])
    ]
    return {
        "schema": SCHEMA,
        "repo": repo,
        "project": {"owner": owner, "number": project},
        "fetched_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "issues": issues,
        "prs": prs,
        "board": fetch_board(owner, project),
    }


# --- check and CLI ------------------------------------------------------------


def check_page(root: Path) -> list[str]:
    """Problems with the committed page against the committed snapshot. Offline."""
    snap_path, page_path = root / SNAPSHOT, root / PAGE
    try:
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read {SNAPSHOT}: {exc}"]
    problems = validate_snapshot(snap)
    if problems:
        return [f"{SNAPSHOT}: {p}" for p in problems]
    if not page_path.is_file():
        return [f"{PAGE} is missing"]
    have = page_path.read_text(encoding="utf-8")
    stamp = STAMP_LINE_RE.search(have)
    if stamp is None or not STAMP_RE.match(stamp.group(1)):
        return [f"{PAGE} has no valid 'Generated at' time stamp"]
    if stamp.group(1) != snap["fetched_at"]:
        return [f"{PAGE} says it was generated at {stamp.group(1)} but the snapshot was taken at {snap['fetched_at']}"]
    if have != render(snap):
        return [f"{PAGE} does not match {SNAPSHOT} (edited by hand, or the renderer changed)"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="offline: fail when the page is stale")
    mode.add_argument("--refresh", action="store_true", help="fetch live data with gh (maintainer login) and rewrite the snapshot and page")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repository root")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/name (--refresh)")
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="project owner login (--refresh)")
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT, help="project number (--refresh)")
    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.check:
        problems = check_page(root)
        if problems:
            for p in problems:
                print(f"gen_project_status: {p}", file=sys.stderr)
            print("gen_project_status: refresh with: python -I scripts/gen_project_status.py --refresh (maintainer login), or re-render with: python -I scripts/gen_project_status.py", file=sys.stderr)
            return 1
        print(f"gen_project_status: {PAGE} matches {SNAPSHOT}")
        return 0

    if args.refresh:
        try:
            snap = fetch_snapshot(args.repo, args.owner, args.project)
        except (RuntimeError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            print(f"gen_project_status: refresh failed: {exc}", file=sys.stderr)
            return 1
        (root / SNAPSHOT).write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    else:
        try:
            snap = json.loads((root / SNAPSHOT).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"gen_project_status: cannot read {SNAPSHOT}: {exc}", file=sys.stderr)
            return 1
        problems = validate_snapshot(snap)
        if problems:
            print(f"gen_project_status: {SNAPSHOT}: {'; '.join(problems)}", file=sys.stderr)
            return 1
    (root / PAGE).write_text(render(snap), encoding="utf-8")
    print(f"gen_project_status: wrote {PAGE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
