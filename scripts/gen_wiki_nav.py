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
  The sidebar spends one line per page, so it grows with the wiki; the budget test fails
  before the limit is reached, which is the signal to fold subgroups, not to raise the budget.

The optional top-level `readers` list gives each audience its Start-here page for the Home map
(every audience exactly once, an existing page).

Parts, kept apart on purpose (the same shape as gen_project_status.py):

  load_manifest(text)       parse and reject duplicate keys; PyYAML is imported here only
  validate(manifest, pages) pure: the problems with a manifest against a set of page names
  render_contents(m), render_sidebar(m), render_home_map(m)
                            pure: manifest in, Markdown out. No file reads, no clock.
  apply_home_map(text, block)
                            pure: swap the block between the markers of a Home.md text.
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

AUDIENCES = ("everyone", "newcomer", "learner", "builder", "engineer", "operator", "security reader")
STATUSES = ("draft", "est. steps", "unbuilt")
ORDERS = ("curated", "sorted")
MAX_DESC = 220
MAX_TITLE = 80
MAX_WHO = 80
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
            extra = set(e) - {"page", "title", "audience", "status", "desc", "sidebar"}
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

    problems += _reader_problems(manifest.get("readers"), set(seen))

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
    if group.get("numbered"):
        return everything
    # Marked entries are pinned to the top; the rest follow. Both keep display order, nothing is dropped.
    return [e for e in everything if e.get("sidebar")] + [e for e in everything if not e.get("sidebar")]


def render_sidebar(manifest: dict) -> str:
    # Line-saving layout (the budget is a test): no blank line between groups, none before
    # </details>. A blank line is kept after each <summary> because Markdown inside an HTML
    # block needs it, and between the top row and the first group.
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
        lines.append("<details open>" if group.get("open") else "<details>")
        lines += [f"<summary><b>{group['title']}</b> ({count})</summary>", ""]
        for number, e in enumerate(sidebar_entries(manifest, group), start=1):
            numbered = group.get("numbered") and "url" not in e
            lines.append(f"{f'{number}.' if numbered else '-'} {_sidebar_item(e)}")
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
    return problems


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
        print(f"gen_wiki_nav: {CONTENTS}, {SIDEBAR} and the {HOME} page map match {MANIFEST}")
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
    (root / CONTENTS).write_text(render_contents(manifest), encoding="utf-8")
    (root / SIDEBAR).write_text(render_sidebar(manifest), encoding="utf-8")
    (root / HOME).write_text(home, encoding="utf-8")
    print(f"gen_wiki_nav: wrote {CONTENTS}, {SIDEBAR} and the page map in {HOME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
