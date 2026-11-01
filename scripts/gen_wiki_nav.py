# SPDX-License-Identifier: Apache-2.0
"""Write the wiki Contents page, the sidebar and the Home page map from one manifest (issue #249).

The manifest, docs/wiki/_nav.yaml, lists every wiki page once, in a theme group, with a
short title, an audience, an optional status marker and a one-line description. Three
outputs are generated from it, so adding a page is one line in one file:

  docs/wiki/Contents.md   every page, grouped, one line each, with its status marker
  docs/wiki/_Sidebar.md   the sidebar: top links, then one collapsible group each (<details>
                          and <summary>, which GitHub's collapsed-sections page documents),
                          with only the core path open by default. Every group lists EVERY
                          page, one line each, then a "Full list" link to its section of
                          Contents.md, so a reader reaches any page from the sidebar (issue #378).
  docs/wiki/Home.md       the hand-written intro stays; only the block between the BEGIN and
                          END markers (HOME_BEGIN, HOME_END) is rewritten: a "Start here" line
                          per kind of reader, then every page grouped like Contents with its
                          one-line description. Nothing outside the markers is touched, and a
                          Home.md without exactly one marker pair is an error.

Order in the sidebar (the sidebar line budget is a test, not a goal):
  - the numbered core path is listed in full, in reading order;
  - any other group lists the entries marked `sidebar: true` first (pinned to the top, in display
    order), then the rest in display order; with none marked it is simply display order;
  - every group ends with "Full list (N)", linking to its heading in Contents.md. The
    section headings of Contents.md are the group titles, so group titles must make
    distinct anchors (validate checks this).
  - an entry may carry `subgroup: "Title"` (not on the core path or the start group). Entries
    with no subgroup are listed first, one per line; then each subgroup is a nested
    `<details><summary>Title (n)</summary>` in order of first appearance, whose rows pack up to
    SIDEBAR_PACK_LINKS (5) links, and at most SIDEBAR_PACK_CHARS (170) characters of visible
    text, per line, joined by a middle dot. A group with no subgroup field is one page per line.
  A page with no subgroup costs one line, a subgroup costs three lines plus its rows, and the
  budget test fails before the limit is reached: that is the signal to fold more pages into
  subgroups, not to raise the budget. The first summary line of every block shares its line
  with <details>, which saves a line per block.

The optional top-level `readers` list gives each audience its Start-here page for the Home map
(every audience exactly once, an existing page). The optional `goals` list (issue #416) adds a
Start-here line per topic track and per goal ({who, page}; no audience, an existing page).

A group with `numbered: true` and `track: true` is a topic track (issue #416): numbered and curated
in Contents and Home like the core path, but closed by default and folded into subgroups in the
sidebar (the core path, with `numbered` alone, is listed in full and takes no subgroup). A page is
in exactly one group, so a track holds its pages instead of a theme group.

Page navigation (issue #417): every other page also carries two generated blocks, a short one after
its first heading and leading quote banners (breadcrumb, previous, next) and the full one at the end
(previous, next, the rest of its group, related pages), each between a BEGIN GENERATED PAGE NAV and
an END GENERATED PAGE NAV line (NAV_BEGIN, NAV_END; "top" and "bottom"). Home and Contents get none,
nor does a page whose first line is a GENERATED comment (another generator writes it whole). A page
with no markers gets them inserted once; after that only the text between them is rewritten, and
--check fails when any block is stale. The optional `related` list of a page entry, the fallback
rule and the reading orders are explained in the header of docs/wiki/_nav.yaml. Tests that count a
page's links or read its first lines use strip_page_nav (via tests/wikitext.py) to see the author's text.

Parts, kept apart on purpose (the same shape as gen_project_status.py):

  load_manifest(text)       parse and reject duplicate keys; PyYAML is imported here only
  validate(manifest, pages) pure: the problems with a manifest against a set of page names
  render_contents(m), render_sidebar(m), render_home_map(m)
                            pure: manifest in, Markdown out. No file reads, no clock.
  apply_home_map(text, block)
                            pure: swap the block between the markers of a Home.md text.
  render_page_nav(m, page), apply_page_nav(text, blocks), strip_page_nav(text)
                            pure: the two blocks of a page, put into (or taken out of) a page text.
  main()                    --check is offline and exits 1 when a generated file is stale
                            or the manifest does not match the pages in docs/wiki.

Usage (from anywhere inside a clone):
  python -I scripts/gen_wiki_nav.py --check   exit 1 when stale or inconsistent
  python -I scripts/gen_wiki_nav.py           rewrite Contents.md, _Sidebar.md and the Home map

Exit codes: 0 ok, 1 stale or inconsistent (--check) or an unreadable manifest, 2 usage or
a missing PyYAML.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = Path("docs/wiki")
MANIFEST = WIKI / "_nav.yaml"
CONTENTS = WIKI / "Contents.md"
SIDEBAR = WIKI / "_Sidebar.md"
HOME = WIKI / "Home.md"
# The generated block of Home.md sits between these two lines; everything else on Home is hand-written.
HOME_BEGIN = "<!-- BEGIN GENERATED PAGE MAP: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->"
HOME_END = "<!-- END GENERATED PAGE MAP -->"
SPECIAL = {"_Sidebar", "_Footer"}  # wiki chrome, not pages a reader navigates to
# Page navigation blocks (issue #417): two generated blocks per page, one at the top (breadcrumb, previous and
# next) and one at the bottom (previous and next, the rest of the track, related pages).
NAV_BEGIN = "<!-- BEGIN GENERATED PAGE NAV {where}: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->"
NAV_END = "<!-- END GENERATED PAGE NAV {where} -->"
NAV_PLACES = ("top", "bottom")
# Home has its own page map and Contents is the index itself, so neither gets a block. A page whose first line is a
# GENERATED comment is written whole by another generator (the status, growth and settings pages); a block added
# here would make that generator's --check fail, so those are left alone too.
NAV_EXEMPT = {"Home", "Contents"}
GENERATED_PAGE_START = "<!-- GENERATED"
RELATED_MIN = 3
RELATED_MAX = 6
RELATED_FALLBACK = 4  # how many neighbors stand in for a missing `related:` list

AUDIENCES = ("everyone", "newcomer", "learner", "builder", "engineer", "operator", "security reader")
STATUSES = ("draft", "est. steps", "unbuilt")
ORDERS = ("curated", "sorted")
MAX_DESC = 220
MAX_TITLE = 80
MAX_WHO = 80
# A subgroup row in the sidebar holds at most this many links and this many characters of visible text.
SIDEBAR_PACK_LINKS = 5
SIDEBAR_PACK_CHARS = 170
# The group the sidebar shows as a row of links across the top instead of a collapsible block.
TOP_GROUP = "start"
TOP_BAR_LABELS = {"Give-Feedback-and-Open-an-Issue": "Give feedback"}

PAGE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
GROUP_ID = re.compile(r"^[a-z][a-z0-9-]*$")
URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(blob|tree)/[A-Za-z0-9_./-]+$")
FORBIDDEN_TEXT = ("|", "\n", "\r", "—", "–", "](", "<", ">", "`")


# -- reading the manifest ---------------------------------------------------------------


def load_manifest(text: str) -> dict:
    """Parse the manifest. A repeated key in any mapping is an error, not a silent overwrite."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - CI installs PyYAML
        raise RuntimeError("PyYAML is required to read docs/wiki/_nav.yaml") from exc

    class Strict(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"duplicate key {key!r} (line {key_node.start_mark.line + 1})")
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    try:
        loaded = yaml.load(text, Loader=Strict)  # a SafeLoader subclass: no Python tags
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}") from exc
    if not isinstance(loaded, dict):
        raise TypeError("the manifest must be a mapping with groups, pages and links")
    return loaded


def groups_of(manifest: dict) -> list[dict]:
    return manifest.get("groups") or []


def entries(manifest: dict, group_id: str) -> list[dict]:
    """The page entries of a group in display order (sorted groups are sorted here, too)."""
    group = next(g for g in groups_of(manifest) if g["id"] == group_id)
    found = list((manifest.get("pages") or {}).get(group_id) or [])
    if group.get("order") == "sorted":
        found.sort(key=lambda e: e["title"].casefold())
    return found


def link_entries(manifest: dict, group_id: str) -> list[dict]:
    found = list((manifest.get("links") or {}).get(group_id) or [])
    found.sort(key=lambda e: e["title"].casefold())
    return found


def all_page_names(manifest: dict) -> list[str]:
    names = []
    for pages in (manifest.get("pages") or {}).values():
        names.extend(e.get("page") for e in pages or [] if isinstance(e, dict))
    return names


# -- checking the manifest --------------------------------------------------------------


def _text_problems(where: str, label: str, value: object, limit: int) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{where}: {label} must be non-empty text"]
    out = []
    if len(value) > limit:
        out.append(f"{where}: {label} is {len(value)} characters, over {limit}")
    for bad in FORBIDDEN_TEXT:
        if bad in value:
            out.append(f"{where}: {label} contains {bad!r}, which breaks the generated Markdown or the style rules")
    if value != value.strip() or "  " in value:
        out.append(f"{where}: {label} has stray spaces")
    return out


def _reader_problems(readers: object, listed: set[str]) -> list[str]:
    """The optional `readers` list: one Start-here page per audience, every audience exactly once."""
    if readers is None:
        return []
    if not isinstance(readers, list):
        return ["readers: must be a list of {audience, who, page} entries"]
    problems: list[str] = []
    covered: list[str] = []
    for r in readers:
        if not isinstance(r, dict):
            problems.append(f"readers: entry {r!r} is not a mapping")
            continue
        where = f"readers.{r.get('audience')}"
        extra = set(r) - {"audience", "who", "page"}
        if extra:
            problems.append(f"{where}: unknown field(s) {sorted(extra)}")
        if r.get("audience") not in AUDIENCES:
            problems.append(f"{where}: audience {r.get('audience')!r} is not one of {AUDIENCES}")
        else:
            covered.append(r["audience"])
        problems += _text_problems(where, "who", r.get("who"), MAX_WHO)
        if r.get("page") not in listed:
            problems.append(f"{where}: page {r.get('page')!r} is not a page in the manifest")
    for a in sorted({a for a in covered if covered.count(a) > 1}):
        problems.append(f"readers: audience {a!r} is listed twice")
    for a in AUDIENCES:
        if a not in covered:
            problems.append(f"readers: no start page for audience {a!r}")
    return problems


def _goal_problems(goals: object, listed: set[str]) -> list[str]:
    """The optional `goals` list (issue #416): a Start-here page per topic track or goal, no audience implied."""
    if goals is None:
        return []
    if not isinstance(goals, list):
        return ["goals: must be a list of {who, page} entries"]
    problems: list[str] = []
    seen_who: list[str] = []
    for r in goals:
        if not isinstance(r, dict):
            problems.append(f"goals: entry {r!r} is not a mapping")
            continue
        where = f"goals.{r.get('who')}"
        extra = set(r) - {"who", "page"}
        if extra:
            problems.append(f"{where}: unknown field(s) {sorted(extra)}")
        problems += _text_problems(where, "who", r.get("who"), MAX_WHO)
        if isinstance(r.get("who"), str):
            seen_who.append(r["who"])
        if r.get("page") not in listed:
            problems.append(f"{where}: page {r.get('page')!r} is not a page in the manifest")
    for w in sorted({w for w in seen_who if seen_who.count(w) > 1}):
        problems.append(f"goals: {w!r} is listed twice")
    return problems


def _related_problems(where: str, page: object, related: object, listed: set[str]) -> list[str]:
    """The optional `related` list of a page (issue #417): RELATED_MIN to RELATED_MAX page names that exist, no
    link to the page itself, none twice."""
    if not isinstance(related, list) or not all(isinstance(r, str) for r in related):
        return [f"{where}: related must be a list of page names"]
    problems = []
    if not RELATED_MIN <= len(related) <= RELATED_MAX:
        problems.append(f"{where}: related has {len(related)} entries, it needs {RELATED_MIN} to {RELATED_MAX}")
    for r in related:
        if r == page:
            problems.append(f"{where}: related lists the page itself")
        elif r not in listed:
            problems.append(f"{where}: related page {r!r} is not a page in the manifest")
    for r in sorted({r for r in related if related.count(r) > 1}):
        problems.append(f"{where}: related lists {r!r} twice")
    return problems


def validate(manifest: dict, pages: set[str]) -> list[str]:
    """Problems with a manifest, given the page names that exist in docs/wiki (minus the special ones).

    Every page exactly once (no orphan, no duplicate), no entry for a missing page, known
    groups, audiences and statuses, and curated text that cannot break the Markdown."""
    problems: list[str] = []
    groups = groups_of(manifest)
    if not groups:
        return ["the manifest has no groups"]
    ids = []
    for g in groups:
        gid = g.get("id") if isinstance(g, dict) else None
        if not isinstance(gid, str) or not GROUP_ID.match(gid):
            problems.append(f"group {g!r}: id must be lower-case letters, digits and hyphens")
            continue
        if gid in ids:
            problems.append(f"group {gid}: declared twice")
        ids.append(gid)
        problems += _text_problems(f"group {gid}", "title", g.get("title"), MAX_TITLE)
        if g.get("order") not in ORDERS:
            problems.append(f"group {gid}: order must be one of {ORDERS}")
        if g.get("track") and (not g.get("numbered") or g.get("order") != "curated" or g.get("open")):
            problems.append(f"group {gid}: a topic track must be numbered, curated and closed by default")
    if TOP_GROUP not in ids:
        problems.append(f"the {TOP_GROUP!r} group is missing (the sidebar's top row comes from it)")
    opened = [g.get("id") for g in groups if g.get("open")]
    if opened != ["core"] and "core" in ids:
        problems.append("exactly the core group should be open by default in the sidebar")
    titles = [g.get("title") for g in groups]
    for t in sorted({t for t in titles if titles.count(t) > 1}, key=str):
        problems.append(f"two groups are both titled {t!r}")

    for section in ("pages", "links"):
        for gid in manifest.get(section) or {}:
            if gid not in ids:
                problems.append(f"{section}: group {gid!r} is not declared in groups")

    seen: dict[str, str] = {}
    for gid, group_entries in (manifest.get("pages") or {}).items():
        for e in group_entries or []:
            if not isinstance(e, dict):
                problems.append(f"pages.{gid}: entry {e!r} is not a mapping")
                continue
            name = e.get("page")
            where = f"pages.{gid}.{name}"
            extra = set(e) - {"page", "title", "audience", "status", "desc", "sidebar", "subgroup", "related"}
            if extra:
                problems.append(f"{where}: unknown field(s) {sorted(extra)}")
            if not isinstance(name, str) or not PAGE_NAME.match(name):
                problems.append(f"pages.{gid}: bad page name {name!r}")
                continue
            if name in SPECIAL:
                problems.append(f"{where}: {name} is wiki chrome and is not listed")
            if name in seen:
                problems.append(f"{where}: listed twice (also in {seen[name]})")
            seen[name] = gid
            problems += _text_problems(where, "title", e.get("title"), MAX_TITLE)
            problems += _text_problems(where, "desc", e.get("desc"), MAX_DESC)
            if e.get("audience") not in AUDIENCES:
                problems.append(f"{where}: audience {e.get('audience')!r} is not one of {AUDIENCES}")
            if "status" in e and e["status"] not in STATUSES:
                problems.append(f"{where}: status {e['status']!r} is not one of {STATUSES}")
            if "sidebar" in e and not isinstance(e["sidebar"], bool):
                problems.append(f"{where}: sidebar must be true or false")
            if "subgroup" in e:
                problems += _text_problems(where, "subgroup", e["subgroup"], MAX_TITLE)
                if gid == TOP_GROUP:
                    problems.append(f"{where}: the {TOP_GROUP!r} group is the sidebar's top row and takes no subgroup")
                if any(g.get("id") == gid and g.get("numbered") and not g.get("track") for g in groups if isinstance(g, dict)):
                    problems.append(f"{where}: a numbered group is a reading path and takes no subgroup")

    for gid, group_links in (manifest.get("links") or {}).items():
        for e in group_links or []:
            where = f"links.{gid}.{(e or {}).get('title')}"
            if not isinstance(e, dict) or not isinstance(e.get("url"), str) or not URL.match(e["url"]):
                problems.append(f"{where}: url must be a github.com blob or tree link")
                continue
            problems += _text_problems(where, "title", e.get("title"), MAX_TITLE)
            problems += _text_problems(where, "desc", e.get("desc"), MAX_DESC)
            if e.get("audience") not in AUDIENCES:
                problems.append(f"{where}: audience {e.get('audience')!r} is not one of {AUDIENCES}")
            if "sidebar" in e and not isinstance(e["sidebar"], bool):
                problems.append(f"{where}: sidebar must be true or false")

    anchors: dict[str, str] = {}
    for g in groups:
        if isinstance(g, dict) and isinstance(g.get("title"), str) and isinstance(g.get("id"), str):
            anchor = slug(g["title"])
            if anchor in anchors:
                problems.append(f"groups {anchors[anchor]} and {g['id']} have the same Contents anchor #{anchor}")
            anchors.setdefault(anchor, g["id"])

    for group_entries in (manifest.get("pages") or {}).values():
        for e in group_entries or []:
            if isinstance(e, dict) and "related" in e:
                problems += _related_problems(f"pages.{e.get('page')}", e.get("page"), e["related"], set(seen))

    problems += _reader_problems(manifest.get("readers"), set(seen))
    problems += _goal_problems(manifest.get("goals"), set(seen))

    for name in sorted(pages - set(seen)):
        problems.append(f"orphan: {name}.md is a wiki page but has no manifest entry")
    for name in sorted(set(seen) - pages):
        problems.append(f"dead entry: {name} is in the manifest but docs/wiki/{name}.md does not exist")

    for g in groups:
        gid = g.get("id")
        if g.get("order") == "sorted":
            listed = [e.get("title") for e in (manifest.get("pages") or {}).get(gid) or [] if isinstance(e, dict)]
            if listed != sorted(listed, key=lambda t: str(t).casefold()):
                problems.append(f"group {gid}: entries are not in title order (it is a sorted group)")
        if g.get("numbered") and not (manifest.get("pages") or {}).get(gid):
            problems.append(f"group {gid}: numbered but empty")
    return problems


# -- rendering --------------------------------------------------------------------------


def slug(heading: str) -> str:
    """The anchor GitHub builds from a heading (the same rule tests/test_markdown_anchors.py uses)."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def _suffix(entry: dict) -> str:
    return f" ({entry['status']})" if entry.get("status") else ""


def _sidebar_item(entry: dict) -> str:
    if "url" in entry:
        return f"[{entry['title']}]({entry['url']})"
    return f"[{entry['title']}]({entry['page']}.md){_suffix(entry)}"


def sidebar_entries(manifest: dict, group: dict) -> list[dict]:
    """The entries a group shows in the sidebar: see the module docstring for the rule."""
    gid = group["id"]
    pages, extra = entries(manifest, gid), link_entries(manifest, gid)
    everything = pages + extra
    if group.get("numbered") and not group.get("track"):
        return everything
    # Marked entries are pinned to the top; the rest follow. Both keep display order, nothing is dropped.
    return [e for e in everything if e.get("sidebar")] + [e for e in everything if not e.get("sidebar")]


def _pack(members: list[dict]) -> list[str]:
    """Pack links into rows joined by " · ": at most SIDEBAR_PACK_LINKS links and SIDEBAR_PACK_CHARS
    characters of visible text (titles, status suffixes and separators) per row; order is kept."""
    rows: list[list[str]] = []
    widths: list[int] = []
    for e in members:
        item = _sidebar_item(e)
        visible = len(e["title"]) + (0 if "url" in e else len(_suffix(e)))
        if rows and len(rows[-1]) < SIDEBAR_PACK_LINKS and widths[-1] + 3 + visible <= SIDEBAR_PACK_CHARS:
            rows[-1].append(item)
            widths[-1] += 3 + visible
        else:
            rows.append([item])
            widths.append(visible)
    return [" · ".join(row) for row in rows]


def render_sidebar(manifest: dict) -> str:
    # Line-saving layout (the budget is a test): the <summary> shares its line with <details>, no
    # blank line between groups, none before </details>. A blank line is kept after each summary
    # because Markdown inside an HTML block needs it, and between the top row and the first group.
    # A page with a `subgroup` goes into a nested <details> whose rows pack several links each.
    lines = [
        "<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this",
        "file by hand: add the page to the manifest and re-run the script. CI fails when this",
        "file does not match the manifest. -->",
        "",
    ]
    top = entries(manifest, TOP_GROUP)
    lines.append(" | ".join(f"**[{TOP_BAR_LABELS.get(e['page'], e['title'])}]({e['page']}.md)**" for e in top))
    lines.append("")
    for group in groups_of(manifest):
        if group["id"] == TOP_GROUP:
            continue
        count = len(entries(manifest, group["id"])) + len(link_entries(manifest, group["id"]))
        opener = "<details open>" if group.get("open") else "<details>"
        lines += [f"{opener}<summary><b>{group['title']}</b> ({count})</summary>", ""]
        shown = sidebar_entries(manifest, group)
        flat = [e for e in shown if not e.get("subgroup")]
        for number, e in enumerate(flat, start=1):
            numbered = group.get("numbered") and not group.get("track") and "url" not in e
            lines.append(f"{f'{number}.' if numbered else '-'} {_sidebar_item(e)}")
        subgroups: dict[str, list[dict]] = {}
        for e in shown:
            if e.get("subgroup"):
                subgroups.setdefault(e["subgroup"], []).append(e)
        for title, members in subgroups.items():
            lines += [f"<details><summary>{title} ({len(members)})</summary>", ""]
            lines += [f"- {row}" for row in _pack(members)]
            lines.append("</details>")
        if subgroups:
            lines.append("")  # an HTML block runs to the next blank line, so the Full list link needs one before it
        lines.append(f"- [Full list ({count})](Contents.md#{slug(group['title'])})")
        lines.append("</details>")
    return "\n".join(lines) + "\n"


def render_home_map(manifest: dict) -> str:
    """The generated block of Home.md, markers included: a Start-here line per kind of reader, then
    every page grouped like Contents with its one-line description (and status marker)."""
    groups = groups_of(manifest)
    total = sum(len(entries(manifest, g["id"])) for g in groups)
    titles = {e["page"]: e["title"] for g in groups for e in entries(manifest, g["id"])}
    out = [
        HOME_BEGIN,
        "",
        "## Every page, by theme",
        "",
        (
            f"All {total} pages of this wiki, grouped the way [Contents](Contents.md) groups them, with one line on what "
            "each is for. Pages marked draft, est. steps or unbuilt say so in their own banner; "
            "[Contents](Contents.md) explains the markers."
        ),
    ]
    readers = manifest.get("readers") or []
    if readers:
        out += ["", "### Start here, by kind of reader", ""]
        out += [f"- **{r['who']}**: [{titles[r['page']]}]({r['page']}.md)" for r in readers]
    goals = manifest.get("goals") or []
    if goals:
        out += ["", "### Start here, by topic track and by goal", ""]
        out += [f"- **{r['who']}**: [{titles[r['page']]}]({r['page']}.md)" for r in goals]
    for g in groups:
        pages, extra = entries(manifest, g["id"]), link_entries(manifest, g["id"])
        out += ["", f"### {g['title']}", ""]
        for number, e in enumerate(pages, start=1):
            bullet = f"{number}." if g.get("numbered") else "-"
            out.append(f"{bullet} [{e['title']}]({e['page']}.md){_suffix(e)}: {e['desc']}")
        out += [f"- [{e['title']}]({e['url']}): {e['desc']}" for e in extra]
    out += ["", HOME_END]
    return "\n".join(out)


def apply_home_map(text: str, block: str) -> str:
    """Replace the block between the markers of a Home.md text; refuse a text without exactly one ordered pair."""
    if text.count(HOME_BEGIN) != 1 or text.count(HOME_END) != 1:
        raise ValueError("Home.md needs exactly one BEGIN and one END page-map marker line")
    start, end = text.index(HOME_BEGIN), text.index(HOME_END)
    if end < start:
        raise ValueError("the END page-map marker comes before the BEGIN marker in Home.md")
    return text[:start] + block + text[end + len(HOME_END):]


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render_contents(manifest: dict) -> str:
    groups = groups_of(manifest)
    total = sum(len(entries(manifest, g["id"])) for g in groups)
    out = [
        "<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this",
        "page by hand: add the page to the manifest and re-run the script. CI fails when this",
        "page does not match the manifest. -->",
        "",
        "# Contents",
        "",
        "> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.",
        "",
        (
            f"Every page of this wiki appears here once ({total} pages), grouped by theme, with a line on what it is for "
            "and who it is for. If you do not know where to begin, take the numbered core path; "
            "[Reading order](Reading-Order.md) has the same pages with time estimates and checkpoints, "
            "and [Start here if you are new](Start-Here-If-You-Are-New.md) is the gentlest first page."
        ),
        "",
        "Some pages carry a status marker, copied from the page's own banner:",
        "",
        "- **draft**: the page calls itself an unverified draft.",
        "- **est. steps**: the page was written from reading, and its steps were not run.",
        "- **unbuilt**: the page describes something that is not built or not applied yet.",
        "",
        "A page with no marker has no such banner. It may still say what was and was not run, so read its status note.",
        "",
        "## Groups",
        "",
    ]
    for g in groups:
        n = len(entries(manifest, g["id"])) + len(link_entries(manifest, g["id"]))
        out.append(f"- [{g['title']}](#{slug(g['title'])}) ({n})")
    for g in groups:
        pages = entries(manifest, g["id"])
        extra = link_entries(manifest, g["id"])
        numbered = bool(g.get("numbered"))
        out += ["", f"## {g['title']}", ""]
        head = (["Step"] if numbered else []) + ["Page", "What it is for and who it is for", "Audience", "Status"]
        out.append(_row(head))
        out.append(_row(["---"] * len(head)))
        for number, e in enumerate(pages, start=1):
            cells = ([str(number)] if numbered else []) + [
                f"[{e['title']}]({e['page']}.md)", e["desc"], e["audience"], e.get("status", ""),
            ]
            out.append(_row(cells))
        for e in extra:
            cells = ([""] if numbered else []) + [f"[{e['title']}]({e['url']})", e["desc"], e["audience"], ""]
            out.append(_row(cells))
    return "\n".join(out) + "\n"


# -- the per-page navigation blocks (issue #417) ----------------------------------------


def has_reading_order(group: dict) -> bool:
    """A numbered group (the core path, a track) or a sorted one has a reading order; the start group and
    the curated, unnumbered tools group do not, so their pages get a breadcrumb and no previous or next."""
    return bool(group.get("numbered")) or group.get("order") == "sorted"


def page_home(manifest: dict) -> dict[str, tuple[dict, list[dict], int]]:
    """Each page name -> (its group, the group's entries in display order, its index in them)."""
    found = {}
    for g in groups_of(manifest):
        ordered = entries(manifest, g["id"])
        for i, e in enumerate(ordered):
            found[e["page"]] = (g, ordered, i)
    return found


def related_for(manifest: dict, page: str) -> list[str]:
    """The pages a page shows as Related: its own `related:` list, else the fallback rule.

    Fallback (deterministic, documented in the manifest header): up to RELATED_FALLBACK other pages of the
    same group, leaving out the previous and next page (they are shown beside it), taking first the pages of
    the same subgroup and then the rest, each nearest first by distance in the group's order, earlier before later."""
    home = page_home(manifest)
    group, ordered, index = home[page]
    own = ordered[index]
    if "related" in own:
        return list(own["related"])
    skip = {page}
    if has_reading_order(group):
        skip |= {ordered[j]["page"] for j in (index - 1, index + 1) if 0 <= j < len(ordered)}
    candidates = [(j, e) for j, e in enumerate(ordered) if e["page"] not in skip]
    candidates.sort(key=lambda je: (je[1].get("subgroup") != own.get("subgroup"), abs(je[0] - index), je[0]))
    return [e["page"] for _, e in candidates[:RELATED_FALLBACK]]


def _link(entry: dict) -> str:
    return f"[{entry['title']}]({entry['page']}.md)"


def _neighbors(group: dict, ordered: list[dict], index: int) -> str:
    if not has_reading_order(group):
        return ""
    parts = []
    if index > 0:
        parts.append(f"Previous: {_link(ordered[index - 1])}")
    if index + 1 < len(ordered):
        parts.append(f"Next: {_link(ordered[index + 1])}")
    return " / ".join(parts)


def _wrap(where: str, body: list[str]) -> str:
    return "\n".join([NAV_BEGIN.format(where=where), *body, NAV_END.format(where=where)])


def render_page_nav(manifest: dict, page: str) -> dict[str, str]:
    """The two generated blocks of one page, markers included: {"top": ..., "bottom": ...}."""
    group, ordered, index = page_home(manifest)[page]
    me = ordered[index]
    crumb = f"[Home](Home.md) > [{group['title']}](Contents.md#{slug(group['title'])}) > {me['title']}"
    neighbors = _neighbors(group, ordered, index)

    top = [crumb] + (["", neighbors] if neighbors else [])

    kind = "track" if group.get("track") or group.get("id") == "core" else "group"
    bottom = [f"Where you are: {crumb}"]
    if neighbors:
        bottom += ["", neighbors]
    plain = [e for e in ordered if not e.get("subgroup")]
    subgroups: dict[str, list[dict]] = {}
    for e in ordered:
        if e.get("subgroup"):
            subgroups.setdefault(e["subgroup"], []).append(e)

    def shown(e: dict) -> str:
        return f"**{e['title']}**" if e["page"] == page else _link(e)

    bottom += ["", f"In this {kind}: [{group['title']}](Contents.md#{slug(group['title'])}), {len(ordered)} pages", ""]
    if plain:
        label = "Also here: " if subgroups else ""
        bottom.append(f"- {label}{' / '.join(shown(e) for e in plain)}")
    for title, members in subgroups.items():
        bottom.append(f"- {title}: {' / '.join(shown(e) for e in members)}")
    titles = {e["page"]: e["title"] for g in groups_of(manifest) for e in entries(manifest, g["id"])}
    related = related_for(manifest, page)
    if related:
        bottom += ["", "Related pages:", ""]
        bottom += [f"- [{titles[r]}]({r}.md)" for r in related]
    return {"top": _wrap("top", top), "bottom": _wrap("bottom", bottom)}


def has_page_nav(name: str, text: str) -> bool:
    """Does this page carry the generated blocks? Not Home, Contents or a page another generator writes whole."""
    return name not in NAV_EXEMPT and name not in SPECIAL and not text.startswith(GENERATED_PAGE_START)


def _top_insertion_point(lines: list[str]) -> int:
    """The line index where the top block goes: after the first heading and after any leading blockquote
    paragraphs (the status banner, the glossary line, the prerequisites line), so a banner stays where it is."""
    i = 1
    while i < len(lines):
        if not lines[i].strip():
            i += 1
        elif lines[i].startswith(">"):
            while i < len(lines) and lines[i].startswith(">"):
                i += 1
        else:
            break
    return i


def apply_page_nav(text: str, blocks: dict[str, str]) -> str:
    """Swap the two blocks of a page text for new ones; a text with no markers gets them inserted once
    (top after the heading and the leading banner quotes, bottom at the end). Anything else is an error."""
    begins = {w: NAV_BEGIN.format(where=w) for w in NAV_PLACES}
    ends = {w: NAV_END.format(where=w) for w in NAV_PLACES}
    counts = [text.count(begins[w]) for w in NAV_PLACES] + [text.count(ends[w]) for w in NAV_PLACES]
    if counts == [0, 0, 0, 0]:
        lines = text.split("\n")
        if not lines or not lines[0].startswith("# "):
            raise ValueError("the page does not begin with a first-level heading, so the top block has no place")
        at = _top_insertion_point(lines)
        before, after = "\n".join(lines[:at]).rstrip("\n"), "\n".join(lines[at:]).strip("\n")
        top_half = f"{before}\n\n{blocks['top']}\n" + (f"\n{after}" if after else "")
        return top_half.rstrip("\n") + f"\n\n{blocks['bottom']}\n"
    if counts != [1, 1, 1, 1]:
        raise ValueError("a page needs exactly one BEGIN and one END marker line for each of its top and bottom page-nav blocks")
    out = text
    for w in NAV_PLACES:
        start, end = out.index(begins[w]), out.index(ends[w])
        if end < start:
            raise ValueError(f"the END page-nav {w} marker comes before its BEGIN marker")
        out = out[:start] + blocks[w] + out[end + len(ends[w]):]
    if out.index(begins["top"]) > out.index(begins["bottom"]):
        raise ValueError("the top page-nav block comes after the bottom one")
    return out


def strip_page_nav(text: str) -> str:
    """The page text without the generated blocks and the blank line each leaves behind (for tests that count links
    or look at the top of a page: the block is navigation, not content)."""
    for w in NAV_PLACES:
        begin, end = NAV_BEGIN.format(where=w), NAV_END.format(where=w)
        while begin in text and end in text:
            start, stop = text.index(begin), text.index(end) + len(end)
            text = text[:start].rstrip("\n") + ("\n\n" if text[stop:].strip("\n") and text[:start].strip("\n") else "\n") + text[stop:].lstrip("\n")
    return text


# -- files ------------------------------------------------------------------------------


def wiki_pages(root: Path) -> set[str]:
    return {p.stem for p in (root / WIKI).glob("*.md")} - SPECIAL


def read_manifest(root: Path) -> dict:
    return load_manifest((root / MANIFEST).read_text(encoding="utf-8"))


def check(root: Path) -> list[str]:
    """Every reason the manifest or the two generated files are not in order (empty when all is well)."""
    try:
        manifest = read_manifest(root)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return [f"cannot read {MANIFEST}: {exc}"]
    problems = validate(manifest, wiki_pages(root))
    if problems:
        return problems
    for path, render in ((CONTENTS, render_contents), (SIDEBAR, render_sidebar)):
        try:
            current = (root / path).read_text(encoding="utf-8")
        except OSError:
            problems.append(f"{path} is missing")
            continue
        if current != render(manifest):
            problems.append(f"{path} does not match {MANIFEST}")
    try:
        home = (root / HOME).read_text(encoding="utf-8")
        if home != apply_home_map(home, render_home_map(manifest)):
            problems.append(f"the page map in {HOME} does not match {MANIFEST}")
    except OSError:
        problems.append(f"{HOME} is missing")
    except ValueError as exc:
        problems.append(f"{HOME}: {exc}")
    for name, path, current, wanted in page_nav_plan(root, manifest, problems):
        if current != wanted:
            problems.append(f"the page navigation blocks in {path} do not match {MANIFEST}")
    return problems


def page_nav_plan(root: Path, manifest: dict, problems: list[str]) -> list[tuple[str, Path, str, str]]:
    """For every page that carries the generated blocks: (name, path, text now, text as it should be).
    A page that cannot take them is reported in `problems` and left out."""
    plan = []
    for name in sorted(wiki_pages(root)):
        path = WIKI / f"{name}.md"
        try:
            current = (root / path).read_text(encoding="utf-8")
        except OSError:
            problems.append(f"{path} is missing")
            continue
        if not has_page_nav(name, current):
            continue
        try:
            wanted = apply_page_nav(current, render_page_nav(manifest, name))
        except ValueError as exc:
            problems.append(f"{path}: {exc}")
            continue
        plan.append((name, path, current, wanted))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="offline: fail when a generated file is stale")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.check:
        problems = check(root)
        if problems:
            for p in problems:
                print(f"gen_wiki_nav: {p}", file=sys.stderr)
            print("gen_wiki_nav: fix the manifest, then re-render with: python -I scripts/gen_wiki_nav.py", file=sys.stderr)
            return 1
        print(f"gen_wiki_nav: {CONTENTS}, {SIDEBAR}, the {HOME} page map and every page's navigation blocks match {MANIFEST}")
        return 0

    try:
        manifest = read_manifest(root)
    except RuntimeError as exc:
        print(f"gen_wiki_nav: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        print(f"gen_wiki_nav: cannot read {MANIFEST}: {exc}", file=sys.stderr)
        return 1
    problems = validate(manifest, wiki_pages(root) | {"Contents"})
    if problems:
        for p in problems:
            print(f"gen_wiki_nav: {p}", file=sys.stderr)
        return 1
    try:  # build Home first: a Home without its markers must stop the run before anything is written
        home = apply_home_map((root / HOME).read_text(encoding="utf-8"), render_home_map(manifest))
    except (OSError, ValueError) as exc:
        print(f"gen_wiki_nav: {HOME}: {exc}", file=sys.stderr)
        return 1
    nav_problems: list[str] = []
    plan = page_nav_plan(root, manifest, nav_problems)
    if nav_problems:  # a page that cannot take its blocks stops the run before anything is written
        for p in nav_problems:
            print(f"gen_wiki_nav: {p}", file=sys.stderr)
        return 1
    (root / CONTENTS).write_text(render_contents(manifest), encoding="utf-8")
    (root / SIDEBAR).write_text(render_sidebar(manifest), encoding="utf-8")
    (root / HOME).write_text(home, encoding="utf-8")
    changed = 0
    for _, path, current, wanted in plan:
        if current != wanted:
            (root / path).write_text(wanted, encoding="utf-8")
            changed += 1
    print(f"gen_wiki_nav: wrote {CONTENTS}, {SIDEBAR}, the page map in {HOME} and the navigation blocks of {len(plan)} pages ({changed} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
