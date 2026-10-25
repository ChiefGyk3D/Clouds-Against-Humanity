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
SNAPSHOT_KEYS = set(DATA_KEYS) | {"source_sha256", "png_sha256"}

NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STAMP_LINE_RE = re.compile(r"^\*\*Generated at:\*\* (\S+) \(UTC\)", re.MULTILINE)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

ALT_TEXT = "Hand-drawn style chart: cumulative stars and forks since the repository was created, and weekly merged pull requests and closed issues"

STARS_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    stargazers(first: 100, after: $after, orderBy: {field: STARRED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      edges { starredAt }
    }
  }
}
"""


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


def totals(snapshot: dict) -> dict[str, int]:
    return {key: sum(snapshot[key].values()) for key in SERIES}


def source_digest(snapshot: dict) -> str:
    """SHA-256 over the data fields only, in a canonical form (not the two hashes themselves)."""
    data = {key: snapshot.get(key) for key in DATA_KEYS}
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
        "## Reproduce it",
        "",
        "Run these from a login that can read the repository. They show the same data without the script:",
        "",
        "```bash",
        f"gh api repos/{repo} --jq .created_at",
        f"gh api repos/{repo}/forks --paginate --jq '.[].created_at'",
        f"gh pr list --repo {repo} --state merged --limit 5000 --json mergedAt",
        f"gh issue list --repo {repo} --state closed --limit 5000 --json closedAt",
        "# stars: a GraphQL query for stargazers(first: 100, orderBy: {field: STARRED_AT, direction: ASC}) { edges { starredAt } }, paged",
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
    stars, forks = cumulative(snapshot["stars"], start, end), cumulative(snapshot["forks"], start, end)
    prs, issues = weekly(snapshot["merged_prs"], start, end), weekly(snapshot["closed_issues"], start, end)
    blue, orange, green, pink = "#0072B2", "#D55E00", "#009E73", "#CC79A7"

    with plt.xkcd():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 7.2), dpi=100, gridspec_kw={"height_ratios": [3, 2]}, facecolor="white")
        top.set_facecolor("white")
        bottom.set_facecolor("white")
        top.plot(days, stars, color=blue, linewidth=2.5, label="Stars")
        top.plot(days, forks, color=orange, linewidth=2.5, label="Forks")
        top.annotate(f"{t['stars']} stars", (days[-1], stars[-1]), xytext=(-70, -8), textcoords="offset points", color=blue, ha="right", va="top")
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
        fig.text(0.5, 0.012, f"As of {snapshot['fetched_at'][:10]} (UTC). Data: GitHub. Stars measure attention, not use.", ha="center", va="bottom", fontsize=9, color="#444444")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
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
    owner, name = repo.split("/")
    stamps, after = [], None
    while True:
        args = ["api", "graphql", "-f", f"query={STARS_QUERY}", "-f", f"owner={owner}", "-f", f"name={name}"]
        if after:
            args += ["-f", f"after={after}"]
        page = json.loads(run_gh(args))["data"]["repository"]["stargazers"]
        stamps += [edge["starredAt"] for edge in page["edges"]]
        if not page["pageInfo"]["hasNextPage"]:
            return stamps
        after = page["pageInfo"]["endCursor"]


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


def fetch_snapshot(repo: str, traffic: bool = False, previous: dict | None = None, now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.now(datetime.UTC)
    created = run_gh(["api", f"repos/{repo}", "--jq", ".created_at"]).strip()
    forks = run_gh(["api", f"repos/{repo}/forks?per_page=100", "--paginate", "--jq", ".[].created_at"]).split()
    prs = json.loads(run_gh(["pr", "list", "--repo", repo, "--state", "merged", "--limit", "5000", "--json", "mergedAt"]))
    issues = json.loads(run_gh(["issue", "list", "--repo", repo, "--state", "closed", "--limit", "5000", "--json", "closedAt"]))
    snap = {
        "schema": SCHEMA,
        "repo": repo,
        "created_on": created[:10],
        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stars": day_counts(fetch_stars(repo)),
        "forks": day_counts(forks),
        "merged_prs": day_counts([p["mergedAt"] for p in prs if p.get("mergedAt")]),
        "closed_issues": day_counts([i["closedAt"] for i in issues if i.get("closedAt")]),
    }
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


def verify_bundle(
    bundle: Path,
    expect_repo: str | None = None,
    max_age_hours: float | None = None,
    now: datetime.datetime | None = None,
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
    return check_files(bundle / BUNDLE_SNAPSHOT, bundle / BUNDLE_PNG, None, "")


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
    parser.add_argument("--image-url", default=None, help="image reference written into the page (default: the metrics branch URL for this repository's own page, else a relative path)")
    mode.add_argument("--verify-bundle", metavar="DIR", help="offline: validate a render-job bundle (snapshot + picture) before publishing it")
    parser.add_argument("--expect-repo", default=None, help="with --verify-bundle: the owner/name the snapshot must be for")
    parser.add_argument("--max-age-hours", type=float, default=None, help="with --verify-bundle: fail when fetched_at is older than this (0 or less: no limit)")
    parser.add_argument("--print-as-of", action="store_true", help="with --verify-bundle: print fetched_at when the bundle is valid")
    args = parser.parse_args(argv)
    if args.traffic and not args.refresh:
        parser.error("--traffic needs --refresh")
    if (args.expect_repo or args.print_as_of or args.max_age_hours is not None) and not args.verify_bundle:
        parser.error("--expect-repo, --max-age-hours and --print-as-of need --verify-bundle")
    if args.verify_bundle:
        bundle = Path(args.verify_bundle)
        limit = args.max_age_hours if args.max_age_hours and args.max_age_hours > 0 else None
        problems = verify_bundle(bundle, args.expect_repo, limit)
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
