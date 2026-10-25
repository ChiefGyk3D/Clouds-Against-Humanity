# SPDX-License-Identifier: Apache-2.0
"""Draw a repository growth chart from a saved snapshot of GitHub data (issue #268).

The chart is a hand-drawn-style PNG (matplotlib's xkcd mode): cumulative stars
and forks since the repository was created, and weekly merged pull requests and
closed issues underneath. It is drawn by this script and served from this
repository's own `metrics` branch (refreshed daily by .github/workflows/growth-chart.yml),
never hotlinked from a chart service, so a reader's address goes to GitHub only.

Parts, kept apart on purpose (the same shape as gen_project_status.py):

  render_page(snapshot)   pure: snapshot in, Markdown out. No network, no clock,
                          no plotting library.
  draw_png(snapshot)      matplotlib, imported lazily inside this function only.
                          Nothing else in the file needs it, and CI never does.
  fetch_snapshot()        a thin layer over the `gh` CLI. Argument lists only,
                          never a shell. Counts per day, never a user name.
  main()                  --check is offline and needs neither a token nor a
                          plotting library; --refresh fetches, draws, and writes;
                          the default re-draws from the committed snapshot.

What is stored: per-day counts only (new stars, new forks, merged pull requests,
closed issues, and optionally daily traffic totals). The stargazer query asks for
the time of each star and nothing else; fork and pull request queries ask for a
time stamp only. No login, name, address, referrer or path is requested, so none
can be saved. The snapshot is checked for exactly that on every run.

Two ways to refresh. With a person's own login (locally), --refresh reads every star's
time stamp: that is the full history, and the way to backfill the baseline. The default
Actions token is refused on both stargazer endpoints (GraphQL and REST), so CI runs
--refresh --no-star-times (automatic when GITHUB_ACTIONS=true): it keeps the star history
of the committed baseline snapshot (--baseline), reads only the current star count, and
adds it to `star_ledger`, one dated cumulative count per UTC day carried from the last
published snapshot (--ledger-from). The chart joins the ledger to the baseline with
straight segments and says so in the picture. `stars_as_of` is the last day the per-star
times cover; both fields are optional, so older snapshots stay valid.

The snapshot records two hashes: `source_sha256` over the data fields (so a hand
edit of the numbers is caught) and `png_sha256` of the picture drawn from them (so
a missing, stale or hand-edited picture is caught). --check recomputes both
offline, the way docs/diagrams.json records a source hash next to each picture.

The daily workflow runs --refresh into a bundle (snapshot + picture, nothing else),
then --verify-bundle DIR re-checks it offline before anything is published: exact file
set, regular files only, size caps, a real PNG, matching hashes, only per-day counts,
the expected repository, and a time stamp that is neither stale nor from the future.

Usage (from anywhere inside a clone):
  python3 -I scripts/gen_repo_metrics.py --verify-bundle DIR --expect-repo OWNER/NAME
                                                      [--max-age-hours N] [--print-as-of]
  python3 -I scripts/gen_repo_metrics.py --check      offline; exit 1 when stale
  python3 -I scripts/gen_repo_metrics.py              re-draw from the snapshot
                                                      (needs matplotlib)
  python3 -I scripts/gen_repo_metrics.py --refresh    fetch live data with gh as a
                                                      login that can read the repo,
                                                      then rewrite snapshot, picture
                                                      and page (needs matplotlib)
  python3 -I scripts/gen_repo_metrics.py --refresh --no-star-times --baseline FILE --ledger-from FILE
                                                      CI mode (see above): no stargazer request
  python3 -I scripts/gen_repo_metrics.py --refresh --traffic
                                                      also keep daily views and
                                                      clones (needs admin; GitHub
                                                      keeps only 14 days)

Another repository: pass its name and its own file names, for example
  python3 -I scripts/gen_repo_metrics.py --refresh --repo ChiefGyk3D/Skid-Finder \\
      --snapshot docs/.metrics-snapshot.json --out docs/images/repo-growth.png \\
      --page docs/Repository-Growth.md
(or --no-page to write the snapshot and picture only).

matplotlib is not a dependency of the repository. To draw, use the system package
(python3-matplotlib on Debian-based systems) or a private virtual environment:
  python3 -m venv "$HOME/.cache/plot-venv" && "$HOME/.cache/plot-venv/bin/python" -m pip install matplotlib
and run this script with that interpreter.

Exit codes: 0 ok, 1 stale or invalid files (--check), or a fetch or draw failure
(--refresh; the files are left untouched), 2 usage.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = 1
DEFAULT_REPO = "ChiefGyk3D/Clouds-Against-Humanity"
SNAPSHOT = Path("docs") / "wiki" / ".metrics-snapshot.json"
PNG = Path("docs") / "wiki" / "images" / "repo-growth.png"
PAGE = Path("docs") / "wiki" / "Repository-Growth.md"

# The daily workflow (.github/workflows/growth-chart.yml) publishes a fresh picture to
# an orphan branch; the pages show that one. The committed picture stays as the
# hash-checked fallback that --check compares against the committed snapshot.
DEFAULT_IMAGE_URL = f"https://raw.githubusercontent.com/{DEFAULT_REPO}/metrics/repo-growth.png"

# A bundle is what the render job hands to the publish job: exactly these two files.
BUNDLE_SNAPSHOT = "metrics-snapshot.json"
BUNDLE_PNG = "repo-growth.png"
MAX_SNAPSHOT_BYTES = 256 * 1024
MAX_PNG_BYTES = 1024 * 1024
MAX_DAY_COUNT = 1_000_000  # one day of stars, forks, pull requests or issues

SERIES = ("stars", "forks", "merged_prs", "closed_issues")
TRAFFIC_KINDS = ("views", "clones")
DATA_KEYS = ("schema", "repo", "created_on", "fetched_at", *SERIES, "traffic")
# Optional fields, covered by the source hash only when present (so a snapshot made before
# they existed keeps its hash): the day the per-star times in `stars` run to, and a ledger of
# dated cumulative star counts recorded by CI, which cannot read star times (issue #296).
OPTIONAL_KEYS = ("stars_as_of", "star_ledger")
SNAPSHOT_KEYS = set(DATA_KEYS) | set(OPTIONAL_KEYS) | {"source_sha256", "png_sha256"}
MAX_LEDGER_POINTS = 4000
# A carried snapshot whose newest point is older than this (measured to the new snapshot's
# time) is refused. A deliberate reset (a newer baseline, or a lost ledger) is a separate,
# reviewed action: delete the `metrics` branch, and the next run starts a ledger afresh.
MAX_CARRY_AGE_DAYS = 14
MAX_STARS = 100_000_000
LEDGER_DROP_SLACK = 5  # a count may fall by this much plus 5% between points (unstarring, spam removal)

NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STAMP_LINE_RE = re.compile(r"^\*\*Generated at:\*\* (\S+) \(UTC\)", re.MULTILINE)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

ALT_TEXT = "Hand-drawn style chart: cumulative stars and forks since the repository was created, and weekly merged pull requests and closed issues"


# --- dates and series (pure) --------------------------------------------------


def to_date(text: str) -> datetime.date:
    return datetime.date.fromisoformat(text)


def day_counts(stamps: list[str]) -> dict[str, int]:
    """Count ISO time stamps per UTC calendar day: {"2026-10-10": 3, ...}."""
    out: dict[str, int] = {}
    for stamp in stamps:
        day = stamp[:10]
        out[day] = out.get(day, 0) + 1
    return dict(sorted(out.items()))


def days_between(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    return [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]


def cumulative(daily: dict[str, int], start: datetime.date, end: datetime.date) -> list[int]:
    """Running total per day from day 0 (start) to end, inclusive. Never decreases."""
    total, out = 0, []
    for day in days_between(start, end):
        total += daily.get(day.isoformat(), 0)
        out.append(total)
    return out


def week_start(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=day.weekday())  # Monday


def weekly(daily: dict[str, int], start: datetime.date, end: datetime.date) -> list[tuple[datetime.date, int]]:
    """Sum per Monday-to-Sunday week (UTC), from the week of start to the week of end."""
    first, last = week_start(start), week_start(end)
    weeks = [first + datetime.timedelta(days=7 * i) for i in range((last - first).days // 7 + 1)]
    sums = dict.fromkeys(weeks, 0)
    for text, n in daily.items():
        sums[week_start(to_date(text))] += n
    return [(w, sums[w]) for w in weeks]


def span(snapshot: dict) -> tuple[datetime.date, datetime.date]:
    return to_date(snapshot["created_on"]), to_date(snapshot["fetched_at"][:10])


def stars_as_of(snapshot: dict) -> datetime.date:
    """The last day the per-star times in `stars` cover (the snapshot date when not recorded)."""
    return to_date(snapshot.get("stars_as_of") or snapshot["fetched_at"][:10])


def current_stars(snapshot: dict) -> int:
    ledger = snapshot.get("star_ledger")
    return list(ledger.values())[-1] if ledger else sum(snapshot["stars"].values())


def star_note(snapshot: dict) -> str:
    """The sentence printed under the chart when part of the stars line is daily counts."""
    if not snapshot.get("star_ledger"):
        return ""
    return f"Stars after {stars_as_of(snapshot).isoformat()} are daily counts, not per-star times."


def totals(snapshot: dict) -> dict[str, int]:
    out = {key: sum(snapshot[key].values()) for key in SERIES}
    out["stars"] = current_stars(snapshot)
    return out


def source_digest(snapshot: dict) -> str:
    """SHA-256 over the data fields only, in a canonical form (not the two hashes themselves)."""
    data = {key: snapshot.get(key) for key in DATA_KEYS}
    data.update({key: snapshot[key] for key in OPTIONAL_KEYS if key in snapshot})
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- page (pure) ---------------------------------------------------------------


def weekly_rows(snapshot: dict) -> list[list[str]]:
    start, end = span(snapshot)
    columns = {key: weekly(snapshot[key], start, end) for key in SERIES}
    rows, running = [], dict.fromkeys(("stars", "forks"), 0)
    for i, (week, _) in enumerate(columns["stars"]):
        running["stars"] += columns["stars"][i][1]
        running["forks"] += columns["forks"][i][1]
        label = week.isoformat() + (" (partial)" if i == len(columns["stars"]) - 1 and week_start(end) + datetime.timedelta(days=6) > end else "")
        rows.append([label, *(str(columns[k][i][1]) for k in SERIES), str(running["stars"]), str(running["forks"])])
    return rows


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers), *("| " + " | ".join(r) + " |" for r in rows), ""]


def render_page(snapshot: dict, image: str = DEFAULT_IMAGE_URL) -> str:
    """The Markdown page for a snapshot. Pure: the same snapshot always gives the same page."""
    repo, created, fetched = snapshot["repo"], snapshot["created_on"], snapshot["fetched_at"]
    start, end = span(snapshot)
    age = (end - start).days
    t = totals(snapshot)
    out = [
        "<!-- GENERATED from the metrics snapshot by scripts/gen_repo_metrics.py. Do not edit this",
        "page by hand: the snapshot is refreshed with `python3 -I scripts/gen_repo_metrics.py --refresh`",
        "from a login that can read the repository. CI fails when this page, the snapshot and the",
        "picture disagree. -->",
        "",
        "# Repository growth: stars, forks and work per week",
        "",
        "> Prerequisites: [Project status](Project-Status.md), which counts the same issues and pull requests this page charts by week.",
        "",
        "> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.",
        "",
        f"**Generated at:** {fetched} (UTC), from `{repo}`, which was created on {created} (day 0 on the chart). The numbers come from GitHub and drift: this is a snapshot, not a live counter.",
        "",
        f"![{ALT_TEXT}]({image})",
        "",
        f"*The picture is redrawn every day by a workflow and shows its own as-of date. The table and totals below are the last committed snapshot, taken {fetched[:10]}.*",
        "",
        "## How the stars line is built",
        "",
        "GitHub does not let the workflow's built-in token read when each star happened, so the daily run cannot rebuild the star history. Instead the line has two parts. Up to the baseline date it comes from per-star times, read by the maintainer with their own login. After that date it is one point per day, the repository's star count that day, recorded by the workflow and joined by straight (dashed) segments. Those later points are daily counts, not per-star times, and the picture says so under the as-of date. Forks, merged pull requests and closed issues are read fresh every day.",
        "",
        "The metrics branch is mutable, so nothing on it is trusted. Each run checks that its snapshot still has the committed baseline's star history, keeps every earlier daily point exactly (only today's point may be added or replaced), and descends from the exact branch commit it read; the push is a plain fast-forward, never a force, and the branch keeps one small commit per day. A branch that moved, lost a point, or went more than 14 days without an update makes the run fail instead of publishing. A deliberate reset, for example after a new baseline is committed, is a separate reviewed step: delete the `metrics` branch and the next run starts a ledger afresh from the new baseline date.",
        "",
        "To backfill the baseline, run `python3 -I scripts/gen_repo_metrics.py --refresh` locally with your own login: it asks for every star's time stamp, moves the baseline date to today and drops the ledger it replaces. The workflow never asks for star times (`--no-star-times`, chosen automatically when `GITHUB_ACTIONS` is true).",
        "",
        f"*As of {fetched[:10]}, {age} days after the repository was created: {t['stars']} stars, {t['forks']} forks, {t['merged_prs']} pull requests merged and {t['closed_issues']} issues closed.*",
        "",
        "## How to read it honestly",
        "",
        "- **Stars measure attention, not use.** A star is a click. It says someone saw the project and liked the idea, not that they ran it, finished a lesson or would recommend it. Forks are a little closer to use, and still a weak signal.",
        "- **Early numbers are noisy.** A repository that is a few days or weeks old can jump on one share or one post and then flatten. One chart of a short history proves very little; read the shape over months.",
        "- **The numbers come from GitHub and drift.** Accounts get deleted and spam stars get removed, so a count can fall. Times are in UTC, and a week runs Monday to Sunday.",
        "- **Throughput is not quality.** Pull requests merged and issues closed show how much moved, not how good it is.",
        "- **Only counts per day are stored.** The snapshot has no user names, no addresses and no tokens, and CI checks that.",
        "",
        "## The numbers behind the chart",
        "",
        "This table is the text version of the picture, one row per week (UTC, Monday to Sunday). The last two columns are running totals at the end of that week.",
        "",
        *md_table(["Week of", "New stars", "New forks", "PRs merged", "Issues closed", "Stars so far", "Forks so far"], weekly_rows(snapshot)),
        f"Totals: {t['stars']} stars, {t['forks']} forks, {t['merged_prs']} merged pull requests, {t['closed_issues']} closed issues.",
        "",
    ]
    traffic = snapshot.get("traffic")
    if traffic:
        out += ["## Traffic (kept daily, because GitHub keeps only 14 days)", "", "Views and clones as GitHub reports them to a repository admin. Unique counts are per day and cannot be added across days, so only the plain counts are summed here.", ""]
        rows = []
        for kind in TRAFFIC_KINDS:
            days = traffic.get(kind, {})
            if days:
                rows.append([kind, str(len(days)), min(days), max(days), str(sum(d["count"] for d in days.values()))])
        out += md_table(["Kind", "Days kept", "First day", "Last day", "Sum of daily counts"], rows)
    out += [
        "## How the daily picture is published, and the risk that remains",
        "",
        "A workflow draws the picture every day and pushes it to an orphan branch named `metrics`, never to `main`. One job (read-only) fetches counts and draws; a second job validates the result again and pushes it. The second job needs `contents: write`, and GitHub cannot limit the built-in token to one branch, so that token is **repository-wide**. The workflow narrows what it does with it: the job holds no other secret and runs only the checked-in publish script, which refuses to write any ref but `refs/heads/metrics`, passes the token to the git commands that talk to GitHub and nowhere else, and never writes it to disk. That is a limit on this script, not access control.",
        "",
        "The control that holds is a repository ruleset: restrict creation and updates of the `metrics` branch to the GitHub Actions app, block deletion and keep `main` protected as it is (pull request, status checks, no force push). Without that ruleset, anything that can run code in the publish job could write any branch.",
        "",
        "## Reproduce it",
        "",
        "Run these from a login that can read the repository. They show the same data without the script:",
        "",
        "```bash",
        f"gh api repos/{repo} --jq .created_at",
        f"gh api repos/{repo}/forks --paginate --jq '.[].created_at'",
        f"gh pr list --repo {repo} --state merged --limit 5000 --json mergedAt",
        f"gh issue list --repo {repo} --state closed --limit 5000 --json closedAt",
        f"gh api --paginate -X GET repos/{repo}/stargazers -H 'Accept: application/vnd.github.star+json' --jq '.[].starred_at'",
        "python3 -I scripts/gen_repo_metrics.py --refresh   # does all of the above, draws the chart and rewrites this page",
        "python3 -I scripts/gen_repo_metrics.py --check     # offline: the same check CI runs",
        "```",
        "",
        "Drawing needs matplotlib, which the repository does not depend on: use the system package (`python3-matplotlib` on Debian-based systems), or make a private virtual environment with `python3 -m pip install matplotlib` and run the script with that interpreter. The check needs only Python.",
        "",
        "The same script works for any repository you can read: pass `--repo owner/name` with its own `--snapshot`, `--out` and `--page` paths (or `--no-page`). Run `python3 -I scripts/gen_repo_metrics.py --help` for the list.",
        "",
        "Next: [Project status](Project-Status.md), which says what the work is doing right now.",
    ]
    return "\n".join(out).rstrip("\n") + "\n"


# --- validation (pure) ----------------------------------------------------------


def ledger_problems(snap: dict, lo: datetime.date, hi: datetime.date) -> list[str]:
    """Problems with stars_as_of and star_ledger (both optional; a ledger needs its baseline date)."""
    problems: list[str] = []
    raw = snap.get("stars_as_of")
    if "stars_as_of" not in snap and "star_ledger" not in snap:
        return problems
    base = None
    if "stars_as_of" in snap:
        try:
            base = to_date(raw) if isinstance(raw, str) and DATE_RE.match(raw) else None
        except ValueError:
            base = None
        if base is None or not lo <= base <= hi:
            return ["stars_as_of is not a real date between created_on and fetched_at"]
        late = [d for d in snap["stars"] if isinstance(d, str) and DATE_RE.match(d) and to_date(d) > base] if isinstance(snap.get("stars"), dict) else []
        if late:
            problems.append(f"stars has a day outside created_on..stars_as_of: {late[0]}")
    if "star_ledger" not in snap:
        return problems
    if base is None:
        return problems + ["star_ledger needs stars_as_of"]
    ledger = snap["star_ledger"]
    if not isinstance(ledger, dict):
        return problems + ["star_ledger is not an object of days"]
    if len(ledger) > MAX_LEDGER_POINTS:
        return problems + [f"star_ledger has too many points (limit {MAX_LEDGER_POINTS})"]
    days = list(ledger)
    if not all(isinstance(d, str) and DATE_RE.match(d) for d in days):
        return problems + ["star_ledger has a key that is not a YYYY-MM-DD date"]
    try:
        parsed = [to_date(d) for d in days]
    except ValueError:
        return problems + ["star_ledger has a key that is not a real date"]
    if any(not base < d <= hi for d in parsed):
        return problems + ["star_ledger has a day outside stars_as_of..fetched_at (after stars_as_of, up to fetched_at)"]
    if parsed != sorted(set(parsed)):
        return problems + ["star_ledger days are not in strictly increasing order"]
    previous = sum(snap["stars"].values()) if isinstance(snap.get("stars"), dict) else 0
    for day, value in ledger.items():
        if not (isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_STARS):
            return problems + [f"star_ledger has a bad value on {day}"]
        if value < previous - (LEDGER_DROP_SLACK + previous // 20):
            return problems + [f"star_ledger drops from {previous} to {value} on {day}, more than a sane tolerance"]
        previous = value
    return problems


def validate_snapshot(snap: object) -> list[str]:
    """Structure problems with a snapshot, including any field that could hold a person's name."""
    if not isinstance(snap, dict):
        return ["snapshot is not a JSON object"]
    problems: list[str] = []
    extra = sorted(set(snap) - SNAPSHOT_KEYS)
    if extra:
        problems.append(f"unknown field(s) {extra}: only per-day counts are allowed in the snapshot")
    if snap.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    repo = snap.get("repo")
    if not (isinstance(repo, str) and repo.count("/") == 1 and all(NAME_RE.match(x) for x in repo.split("/"))):
        problems.append("repo is not owner/name")
    created, fetched = snap.get("created_on"), snap.get("fetched_at")
    if not (isinstance(created, str) and DATE_RE.match(created)):
        problems.append("created_on is not YYYY-MM-DD")
    if not (isinstance(fetched, str) and STAMP_RE.match(fetched)):
        problems.append("fetched_at is not YYYY-MM-DDTHH:MM:SSZ")
    for key in ("source_sha256", "png_sha256"):
        if not (isinstance(snap.get(key), str) and HASH_RE.match(snap[key])):
            problems.append(f"{key} is not a SHA-256 hex digest")
    if problems:
        return problems
    try:
        lo, hi = to_date(created), to_date(fetched[:10])
    except ValueError:
        return ["created_on or fetched_at is not a real date"]
    if hi < lo:
        problems.append("fetched_at is before created_on")

    def check_days(label: str, days: object, leaf) -> None:
        if not isinstance(days, dict):
            problems.append(f"{label} is not an object of days")
            return
        for day, value in days.items():
            if not (isinstance(day, str) and DATE_RE.match(day)):
                problems.append(f"{label} has a key that is not a YYYY-MM-DD date")
                return
            try:
                inside = lo <= to_date(day) <= hi
            except ValueError:
                inside = False
            if not inside:
                problems.append(f"{label} has a day outside created_on..fetched_at: {day}")
                return
            if not leaf(value):
                problems.append(f"{label} has a bad value on {day}")
                return

    def count(v: object) -> bool:
        return isinstance(v, int) and not isinstance(v, bool) and v > 0

    for key in SERIES:
        check_days(key, snap.get(key), count)
    problems += ledger_problems(snap, lo, hi)
    traffic = snap.get("traffic")
    if traffic is not None:
        if not (isinstance(traffic, dict) and set(traffic) <= set(TRAFFIC_KINDS)):
            problems.append("traffic must hold only views and clones")
        else:

            def traffic_day(v: object) -> bool:
                return isinstance(v, dict) and set(v) == {"count", "uniques"} and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in v.values())

            for kind, days in traffic.items():
                check_days(f"traffic.{kind}", days, traffic_day)
    return problems


# --- drawing (matplotlib, imported lazily) ----------------------------------------


def _load_stripper():
    spec = importlib.util.spec_from_file_location("strip_png_metadata", Path(__file__).resolve().parent / "strip_png_metadata.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draw_png(snapshot: dict, out: Path) -> None:
    """Draw the chart to `out` (a PNG about 900 px wide), optimized and stripped of metadata."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import logging

        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is not installed. Use the system package (python3-matplotlib on Debian-based systems) "
            "or a private virtual environment: python3 -m venv VENV && VENV/bin/python -m pip install matplotlib, "
            "then run this script with VENV/bin/python."
        ) from exc
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # the xkcd font is usually absent; the fallback is fine

    start, end = span(snapshot)
    days = list(range((end - start).days + 1))
    t = totals(snapshot)
    base_end = stars_as_of(snapshot)
    base_days = list(range((base_end - start).days + 1))
    stars = cumulative(snapshot["stars"], start, base_end)
    ledger = snapshot.get("star_ledger") or {}
    ledger_x = [(to_date(d) - start).days for d in ledger]
    ledger_y = list(ledger.values())
    forks = cumulative(snapshot["forks"], start, end)
    prs, issues = weekly(snapshot["merged_prs"], start, end), weekly(snapshot["closed_issues"], start, end)
    blue, orange, green, pink = "#0072B2", "#D55E00", "#009E73", "#CC79A7"
    note = star_note(snapshot)
    star_x, star_y = (ledger_x[-1], ledger_y[-1]) if ledger else (base_days[-1], stars[-1])

    with plt.xkcd():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 7.2), dpi=100, gridspec_kw={"height_ratios": [3, 2]}, facecolor="white")
        top.set_facecolor("white")
        bottom.set_facecolor("white")
        top.plot(base_days, stars, color=blue, linewidth=2.5, label="Stars")
        if ledger:
            # straight segments from the end of the per-star history through the daily counts
            top.plot([base_days[-1], *ledger_x], [stars[-1], *ledger_y], color=blue, linewidth=2.5, linestyle="--")
        top.plot(days, forks, color=orange, linewidth=2.5, label="Forks")
        top.annotate(f"{t['stars']} stars", (star_x, star_y), xytext=(-70, -8), textcoords="offset points", color=blue, ha="right", va="top")
        top.annotate(f"{t['forks']} forks", (days[-1], forks[-1]), xytext=(-8, 26), textcoords="offset points", color=orange, ha="right", va="bottom")
        top.set_title(f"Stars and forks since day 0 ({start.isoformat()})")
        top.set_xlabel("Days since the repository was created")
        top.set_ylabel("Total so far")
        top.set_xlim(0, max(days[-1], 1))
        top.set_ylim(bottom=0)
        top.legend(loc="upper left", frameon=False)
        for side in ("top", "right"):
            top.spines[side].set_visible(False)
            bottom.spines[side].set_visible(False)

        x = list(range(len(prs)))
        width = 0.38
        bottom.bar([i - width / 2 for i in x], [n for _, n in prs], width, color=green, label="PRs merged")
        bottom.bar([i + width / 2 for i in x], [n for _, n in issues], width, color=pink, label="Issues closed")
        step = max(1, len(x) // 8)
        bottom.set_xticks(x[::step])
        bottom.set_xticklabels([w.strftime("%b %d") for w, _ in prs][::step])
        bottom.set_title("Work per week (weeks start on Monday, UTC)")
        bottom.set_xlabel("Week of")
        bottom.set_ylabel("Count")
        bottom.legend(loc="upper left", frameon=False)
        caption = f"As of {snapshot['fetched_at'][:10]} (UTC). Data: GitHub. Stars measure attention, not use."
        if note:
            caption = f"{caption}\n{note}"
        fig.text(0.5, 0.012, caption, ha="center", va="bottom", fontsize=9, color="#444444")
        fig.tight_layout(rect=(0, 0.07 if note else 0.04, 1, 1))
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, format="png", dpi=100, facecolor="white", metadata={"Software": None})
        plt.close(fig)

    try:
        from PIL import Image

        img = Image.open(out).convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        img.save(out, optimize=True)
    except ImportError:
        pass  # Pillow is optional: the picture is still valid, only larger
    optipng = shutil.which("optipng")
    if optipng:
        subprocess.run([optipng, "-quiet", "-o2", str(out)], check=False, capture_output=True)
    stripper = _load_stripper()
    out.write_bytes(stripper.strip(out.read_bytes()))


# --- fetch layer (a login that can read the repository) -----------------------------

_RETRY_RE = re.compile(r"HTTP 50\d")


def run_gh(args: list[str]) -> str:
    """Run gh with an argument list, never a shell. Retried only on a 50x answer."""
    result = None
    for attempt in range(3):
        result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False, timeout=300)
        if result.returncode == 0:
            return result.stdout
        if not _RETRY_RE.search(result.stderr):
            break
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gh {' '.join(args[:2])} failed: {(result.stderr or '').strip()[:300]}")


def fetch_stars(repo: str) -> list[str]:
    """Time stamps of every star, over REST (the default Actions token is refused on the
    GraphQL stargazers connection, issue #296). --jq keeps only starred_at, so no login
    ever leaves the gh process."""
    args = ["api", "--paginate", "-X", "GET", f"repos/{repo}/stargazers", "-H", "Accept: application/vnd.github.star+json", "-F", "per_page=100", "--jq", ".[].starred_at"]
    return run_gh(args).split()


def fetch_traffic(repo: str, previous: dict | None) -> dict | None:
    """Daily views and clones, merged into what was kept before. None when the API refuses."""
    merged = {kind: dict((previous or {}).get(kind, {})) for kind in TRAFFIC_KINDS}
    try:
        for kind in TRAFFIC_KINDS:
            data = json.loads(run_gh(["api", f"repos/{repo}/traffic/{kind}"]))
            for entry in data.get(kind, []):
                merged[kind][entry["timestamp"][:10]] = {"count": int(entry["count"]), "uniques": int(entry["uniques"])}
    except (RuntimeError, ValueError, KeyError):
        return None
    merged = {kind: dict(sorted(days.items())) for kind, days in merged.items() if days}
    return merged or None


def fetch_snapshot(
    repo: str,
    traffic: bool = False,
    previous: dict | None = None,
    now: datetime.datetime | None = None,
    star_times: bool = True,
    baseline: dict | None = None,
    ledger_from: dict | None = None,
) -> dict:
    """Live counts for `repo`.

    star_times=True (a person's own login, locally): every star's time stamp, which is the
    full history and the way to backfill the baseline. star_times=False (CI): the default
    Actions token is refused on both stargazer endpoints, so no time stamp is requested.
    The star history comes from `baseline` (a committed snapshot of this repository), and
    today's cumulative count (stargazers_count) is added to a ledger carried from
    `ledger_from`: one point per UTC day, a same-day rerun replacing that day's point.
    """
    now = now or datetime.datetime.now(datetime.UTC)
    if not star_times and (not isinstance(baseline, dict) or baseline.get("repo") != repo or not isinstance(baseline.get("stars"), dict)):
        raise RuntimeError(f"CI mode needs a baseline snapshot of {repo} with star times (backfill it locally with --refresh)")
    created = run_gh(["api", f"repos/{repo}", "--jq", ".created_at"]).strip()
    forks = run_gh(["api", f"repos/{repo}/forks?per_page=100", "--paginate", "--jq", ".[].created_at"]).split()
    prs = json.loads(run_gh(["pr", "list", "--repo", repo, "--state", "merged", "--limit", "5000", "--json", "mergedAt"]))
    issues = json.loads(run_gh(["issue", "list", "--repo", repo, "--state", "closed", "--limit", "5000", "--json", "closedAt"]))
    snap = {
        "schema": SCHEMA,
        "repo": repo,
        "created_on": created[:10],
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forks": day_counts(forks),
        "merged_prs": day_counts([p["mergedAt"] for p in prs if p.get("mergedAt")]),
        "closed_issues": day_counts([i["closedAt"] for i in issues if i.get("closedAt")]),
    }
    if star_times:
        snap["stars"] = day_counts(fetch_stars(repo))
    else:
        as_of = stars_as_of(baseline).isoformat()
        today = now.strftime("%Y-%m-%d")
        count = int(run_gh(["api", f"repos/{repo}", "--jq", ".stargazers_count"]).strip())
        ledger = {d: c for d, c in ((ledger_from or {}).get("star_ledger") or {}).items() if isinstance(d, str) and d > as_of}
        if today > as_of:
            ledger[today] = count
        snap["stars"] = dict(baseline["stars"])
        snap["stars_as_of"] = as_of
        if ledger:
            snap["star_ledger"] = dict(sorted(ledger.items()))
        extension = ledger_extension_problems((ledger_from or {}).get("star_ledger"), snap.get("star_ledger"), today)
        if extension:
            raise RuntimeError("; ".join(extension))
    kept = (previous or {}).get("traffic")
    snap["traffic"] = (fetch_traffic(repo, kept) if traffic else None) or kept
    if snap["traffic"] is None:
        del snap["traffic"]
    return snap


# --- check and CLI ---------------------------------------------------------------------


def check_files(snapshot_path: Path, png_path: Path, page_path: Path | None, image_ref: str) -> list[str]:
    """Problems with the committed files, offline. Needs neither a token nor matplotlib."""
    try:
        snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read {snapshot_path}: {exc}"]
    problems = validate_snapshot(snap)
    if problems:
        return [f"{snapshot_path}: {p}" for p in problems]
    if snap["source_sha256"] != source_digest(snap):
        return [f"{snapshot_path}: the data does not match source_sha256 (edited by hand? re-draw with the script)"]
    if not png_path.is_file():
        return [f"{png_path} is missing"]
    try:
        stripper = _load_stripper()
        extra = sorted({k.decode("latin-1") for k in stripper.chunk_types(png_path.read_bytes())} - {k.decode() for k in stripper.KEEP})
    except (ValueError, OSError) as exc:  # PngError is a ValueError: a malformed PNG fails the check, not crashes it
        return [f"{png_path} is not a valid PNG: {exc}"]
    if extra:
        return [f"{png_path} carries metadata chunks {extra}: run scripts/strip_png_metadata.py, then re-draw"]
    if file_digest(png_path) != snap["png_sha256"]:
        return [f"{png_path} does not match png_sha256 (stale or edited picture; re-draw with the script)"]
    if page_path is not None:
        if not page_path.is_file():
            return [f"{page_path} is missing"]
        have = page_path.read_text(encoding="utf-8")
        stamp = STAMP_LINE_RE.search(have)
        if stamp is None or not STAMP_RE.match(stamp.group(1)):
            return [f"{page_path} has no valid 'Generated at' time stamp"]
        if stamp.group(1) != snap["fetched_at"]:
            return [f"{page_path} says it was generated at {stamp.group(1)} but the snapshot was taken at {snap['fetched_at']}"]
        if have != render_page(snap, image_ref):
            return [f"{page_path} does not match {snapshot_path} (edited by hand, or the renderer changed)"]
    return []


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def _refuse_constant(name: str) -> object:
    raise ValueError(f"{name} is not valid JSON")


def load_snapshot_file(path: Path, what: str, repo: str | None = None) -> dict:
    """Read a committed or carried snapshot with the strict loader: size cap, no duplicate
    keys, full validation and a matching source hash. Raises RuntimeError naming `what`."""
    try:
        if path.stat().st_size > MAX_SNAPSHOT_BYTES:
            raise RuntimeError(f"{what} is larger than {MAX_SNAPSHOT_BYTES} bytes")
        snap = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=_refuse_constant)
    except RecursionError as exc:
        raise RuntimeError(f"{what} is nested too deeply") from exc
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"{what} cannot be read: {exc}") from exc
    problems = validate_snapshot(snap)
    if problems:
        raise RuntimeError(f"{what} is invalid: {'; '.join(problems)}")
    if snap["source_sha256"] != source_digest(snap):
        raise RuntimeError(f"{what} does not match its source_sha256")
    if repo is not None and snap["repo"] != repo:
        raise RuntimeError(f"{what} is for {snap['repo']}, not {repo}")
    return snap


def load_baseline(path: Path, repo: str | None = None) -> dict:
    """The committed snapshot that holds the star history. It must carry NO ledger (CI
    records the ledger, never main) and must say how far its star times run."""
    snap = load_snapshot_file(path, "the baseline snapshot", repo)
    if "star_ledger" in snap:
        raise RuntimeError("the baseline snapshot must not contain a star_ledger (the ledger is recorded by CI on the metrics branch)")
    if "stars_as_of" not in snap:
        raise RuntimeError("the baseline snapshot has no stars_as_of (backfill it with a local --refresh)")
    return snap


def last_point_day(snap: dict) -> datetime.date:
    ledger = snap.get("star_ledger")
    return to_date(list(ledger)[-1]) if ledger else to_date(snap["fetched_at"][:10])


def load_carried(path: Path, repo: str, baseline: dict, reference: datetime.datetime) -> dict:
    """The previously published snapshot whose ledger is carried forward.

    Its identity fields must equal the baseline's exactly; it must hold a ledger (the one
    exception: nothing could have been recorded yet, because it was taken on the very day
    the baseline's star times end); and its newest point may not be older than
    MAX_CARRY_AGE_DAYS before `reference`."""
    snap = load_snapshot_file(path, "the carried snapshot", repo)
    for key in ("created_on", "stars", "stars_as_of"):
        if snap.get(key) != baseline.get(key):
            raise RuntimeError(f"the carried snapshot's {key} differs from the baseline's (a newer baseline needs the metrics branch deleted, as a reviewed change)")
    if not snap.get("star_ledger") and snap["fetched_at"][:10] != snap["stars_as_of"]:
        raise RuntimeError("the carried snapshot has no star_ledger")
    if reference.date() - last_point_day(snap) > datetime.timedelta(days=MAX_CARRY_AGE_DAYS):
        raise RuntimeError(f"the carried snapshot is more than {MAX_CARRY_AGE_DAYS} days old (a reset is a separate, reviewed change)")
    return snap


def ledger_extension_problems(old: dict | None, new: dict | None, today: str) -> list[str]:
    """`new` must keep every point of `old` exactly, in order; only `today` may be added or replaced."""
    old, new = old or {}, new or {}
    problems = []
    kept = [d for d in old if d != today]
    if [d for d in new if d != today] != kept:
        problems.append("the star ledger does not keep every earlier point, in order (only today's may be added or replaced)")
    elif any(new[d] != old[d] for d in kept):
        problems.append("the star ledger changed an earlier point")
    if any(d > today for d in new):
        problems.append("the star ledger has a point after today")
    return problems


def verify_bundle(
    bundle: Path,
    expect_repo: str | None = None,
    max_age_hours: float | None = None,
    now: datetime.datetime | None = None,
    baseline: Path | None = None,
    previous: Path | None = None,
) -> list[str]:
    """Problems with a render-job bundle, offline. Treats every byte of it as untrusted.

    The bundle is a directory holding exactly the snapshot and the picture, both
    regular files under a size cap. The snapshot goes through the same validation as
    the committed one, plus bounds on counts, the expected repository and a fresh
    time stamp. Needs neither a token nor matplotlib.
    """
    now = now or datetime.datetime.now(datetime.UTC)
    if bundle.is_symlink() or not bundle.is_dir():
        return [f"{bundle} is not a directory"]
    expected = {BUNDLE_SNAPSHOT: MAX_SNAPSHOT_BYTES, BUNDLE_PNG: MAX_PNG_BYTES}
    names = sorted(entry.name for entry in bundle.iterdir())
    extra = [n for n in names if n not in expected]
    if extra:
        return [f"unexpected entries in the bundle: {extra}"]
    problems = []
    for name, cap in expected.items():
        path = bundle / name
        try:
            info = path.lstat()
        except OSError:
            problems.append(f"{name} is missing")
            continue
        if not stat.S_ISREG(info.st_mode):
            problems.append(f"{name} is not a regular file")
        elif info.st_size > cap:
            problems.append(f"{name} is larger than {cap} bytes")
        elif info.st_size == 0:
            problems.append(f"{name} is empty")
    if problems:
        return problems
    try:
        snap = json.loads((bundle / BUNDLE_SNAPSHOT).read_bytes().decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=_refuse_constant)
    except RecursionError:
        return [f"{BUNDLE_SNAPSHOT} is nested too deeply"]
    except (ValueError, OSError) as exc:  # includes UnicodeDecodeError and JSONDecodeError
        return [f"{BUNDLE_SNAPSHOT} is not valid JSON: {exc}"]
    problems = validate_snapshot(snap)
    if problems:
        return [f"{BUNDLE_SNAPSHOT}: {p}" for p in problems]
    if expect_repo is not None and snap["repo"] != expect_repo:
        return [f"{BUNDLE_SNAPSHOT}: repo is {snap['repo']}, expected {expect_repo}"]
    for key in SERIES:
        if any(v > MAX_DAY_COUNT for v in snap[key].values()):
            problems.append(f"{key} has a count that is too large for one day")
    if problems:
        return problems
    stamp = datetime.datetime.strptime(snap["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
    if stamp > now + datetime.timedelta(minutes=10):
        return [f"{BUNDLE_SNAPSHOT}: fetched_at is in the future"]
    if max_age_hours is not None and now - stamp > datetime.timedelta(hours=max_age_hours):
        return [f"{BUNDLE_SNAPSHOT}: fetched_at is more than {max_age_hours:g} hours old"]
    chain = chain_problems(snap, stamp, expect_repo, baseline, previous)
    return chain or check_files(bundle / BUNDLE_SNAPSHOT, bundle / BUNDLE_PNG, None, "")


def chain_problems(snap: dict, stamp: datetime.datetime, repo: str | None, baseline_path: Path | None, previous_path: Path | None) -> list[str]:
    """The new snapshot must descend from the committed baseline and, when there is one, from
    the published snapshot it replaces: same identity fields, earlier ledger points kept."""
    if baseline_path is None:
        return [] if previous_path is None else ["--previous needs --baseline"]
    try:
        base = load_baseline(baseline_path, repo or snap["repo"])
        for key in ("repo", "created_on", "stars", "stars_as_of"):
            if snap.get(key) != base.get(key):
                return [f"{BUNDLE_SNAPSHOT}: {key} differs from the committed baseline"]
        old = None
        if previous_path is not None:
            old = load_carried(previous_path, base["repo"], base, stamp)
        return ledger_extension_problems((old or {}).get("star_ledger"), snap.get("star_ledger"), stamp.strftime("%Y-%m-%d"))
    except RuntimeError as exc:
        return [str(exc)]


def write_all(snap: dict, snapshot_path: Path, png_path: Path, page_path: Path | None, image_ref: str) -> None:
    """Write picture, snapshot and page as one unit: all of them change, or none does.

    The picture is drawn into a private temp directory first, then every output is
    staged next to its target. Only when all staging succeeded are the targets
    replaced; if a replace fails, the ones already replaced are put back.
    """
    with tempfile.TemporaryDirectory() as tmp:
        drawn = Path(tmp) / "chart.png"
        draw_png(snap, drawn)
        snap = {**snap, "source_sha256": source_digest(snap), "png_sha256": file_digest(drawn)}
        outputs = {png_path: drawn.read_bytes(), snapshot_path: (json.dumps(snap, indent=1, sort_keys=True) + "\n").encode("utf-8")}
        if page_path is not None:
            outputs[page_path] = render_page(snap, image_ref).encode("utf-8")
    staged: dict[Path, Path] = {}  # target -> the exact staging file this call created
    originals: dict[Path, bytes | None] = {}
    replaced: list[Path] = []
    try:
        for target, data in outputs.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            originals[target] = target.read_bytes() if target.is_file() else None
            mode = stat.S_IMODE(target.stat().st_mode) if originals[target] is not None else 0o644
            # A unique name in the target's own directory: no other run can share it, and
            # os.replace stays on one filesystem. mkstemp creates it 0600 and exclusively.
            fd, name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".new")
            staged[target] = Path(name)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.chmod(name, mode)
        for target, tmp_path in staged.items():
            os.replace(tmp_path, target)
            replaced.append(target)
    except BaseException:
        for target in reversed(replaced):
            before = originals[target]
            if before is None:
                target.unlink(missing_ok=True)  # this call created it
            else:
                target.write_bytes(before)
        raise
    finally:
        for target, tmp_path in staged.items():
            if target not in replaced:
                tmp_path.unlink(missing_ok=True)  # only files this call created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="offline: fail when the snapshot, picture or page disagree")
    mode.add_argument("--refresh", action="store_true", help="fetch live data with gh, then rewrite snapshot, picture and page")
    parser.add_argument("--traffic", action="store_true", help="with --refresh: also keep daily views and clones (needs admin; GitHub keeps 14 days)")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repository root that the other paths are relative to")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/name (--refresh)")
    parser.add_argument("--snapshot", default=str(SNAPSHOT), help="snapshot path, relative to --root")
    parser.add_argument("--out", default=str(PNG), help="picture path, relative to --root")
    parser.add_argument("--page", default=str(PAGE), help="Markdown page path, relative to --root")
    parser.add_argument("--no-page", action="store_true", help="write and check no Markdown page")
    parser.add_argument("--no-star-times", action="store_true", help="with --refresh: do not request stargazer time stamps (the Actions token cannot read them); keep the baseline's star history and add today's count to the ledger. Chosen automatically when GITHUB_ACTIONS=true")
    parser.add_argument("--baseline", default=None, help=f"the committed snapshot holding the star times, relative to --root (--refresh in CI mode: default {SNAPSHOT}; --verify-bundle: the bundle must descend from it)")
    parser.add_argument("--previous", default=None, metavar="FILE", help="with --verify-bundle and --baseline: the published snapshot being replaced; its ledger must be kept")
    parser.add_argument("--ledger-from", default=None, metavar="FILE", help="with --refresh in CI mode: the previously published snapshot whose star ledger is carried forward")
    parser.add_argument("--image-url", default=None, help="image reference written into the page (default: the metrics branch URL for this repository's own page, else a relative path)")
    mode.add_argument("--verify-bundle", metavar="DIR", help="offline: validate a render-job bundle (snapshot + picture) before publishing it")
    parser.add_argument("--expect-repo", default=None, help="with --verify-bundle: the owner/name the snapshot must be for")
    parser.add_argument("--max-age-hours", type=float, default=None, help="with --verify-bundle: fail when fetched_at is older than this (0 or less: no limit)")
    parser.add_argument("--print-as-of", action="store_true", help="with --verify-bundle: print fetched_at when the bundle is valid")
    args = parser.parse_args(argv)
    if args.traffic and not args.refresh:
        parser.error("--traffic needs --refresh")
    if (args.expect_repo or args.print_as_of or args.max_age_hours is not None or args.previous) and not args.verify_bundle:
        parser.error("--expect-repo, --max-age-hours, --previous and --print-as-of need --verify-bundle")
    if args.verify_bundle:
        bundle = Path(args.verify_bundle)
        limit = args.max_age_hours if args.max_age_hours and args.max_age_hours > 0 else None
        problems = verify_bundle(bundle, args.expect_repo, limit, baseline=(Path(args.root) / args.baseline) if args.baseline else None, previous=Path(args.previous) if args.previous else None)
        for p in problems:
            print(f"gen_repo_metrics: {p}", file=sys.stderr)
        if problems:
            return 1
        if args.print_as_of:
            print(json.loads((bundle / BUNDLE_SNAPSHOT).read_text(encoding="utf-8"))["fetched_at"])
        else:
            print(f"gen_repo_metrics: bundle {bundle} is valid")
        return 0
    root = Path(args.root)
    snapshot_path, png_path = root / args.snapshot, root / args.out
    page_path = None if args.no_page else root / args.page
    own_page = args.repo == DEFAULT_REPO and args.page == str(PAGE) and args.out == str(PNG)
    if not page_path:
        image_ref = ""
    elif args.image_url:
        image_ref = args.image_url
    elif own_page:
        image_ref = DEFAULT_IMAGE_URL
    else:
        image_ref = Path(os.path.relpath(png_path, page_path.parent)).as_posix()

    if args.check:
        problems = check_files(snapshot_path, png_path, page_path, image_ref)
        for p in problems:
            print(f"gen_repo_metrics: {p}", file=sys.stderr)
        if problems:
            print("gen_repo_metrics: refresh with: python3 -I scripts/gen_repo_metrics.py --refresh (needs gh and matplotlib), or re-draw with: python3 -I scripts/gen_repo_metrics.py", file=sys.stderr)
            return 1
        print(f"gen_repo_metrics: {args.out} and {args.snapshot} match")
        return 0

    try:
        if args.refresh:
            try:
                previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                previous = None
            if previous is not None and previous.get("repo") != args.repo:
                previous = None
            if args.no_star_times or os.environ.get("GITHUB_ACTIONS") == "true":
                base = load_baseline(root / (args.baseline or str(SNAPSHOT)), args.repo)
                carried = load_carried(Path(args.ledger_from), args.repo, base, datetime.datetime.now(datetime.UTC)) if args.ledger_from and Path(args.ledger_from).is_file() else None
                snap = fetch_snapshot(args.repo, args.traffic, previous, star_times=False, baseline=base, ledger_from=carried)
            else:
                snap = fetch_snapshot(args.repo, args.traffic, previous)
        else:
            snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(snap, dict):
            raise TypeError("snapshot is not a JSON object")
        problems = validate_snapshot({**snap, "source_sha256": "0" * 64, "png_sha256": "0" * 64})
        if problems:
            print(f"gen_repo_metrics: data failed validation: {'; '.join(problems)}", file=sys.stderr)
            return 1
        write_all(snap, snapshot_path, png_path, page_path, image_ref)
    except (RuntimeError, OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(f"gen_repo_metrics: {'refresh' if args.refresh else 'render'} failed: {exc}", file=sys.stderr)
        return 1
    t = totals(json.loads(snapshot_path.read_text(encoding="utf-8")))
    print(f"gen_repo_metrics: wrote {args.snapshot}, {args.out}" + (f", {args.page}" if page_path else "") + f" ({t['stars']} stars, {t['forks']} forks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
