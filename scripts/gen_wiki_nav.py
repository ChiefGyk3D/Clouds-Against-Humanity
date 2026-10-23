# SPDX-License-Identifier: Apache-2.0
"""Write the wiki Contents page and the sidebar from one manifest (issue #249).

The manifest, docs/wiki/_nav.yaml, lists every wiki page once, in a theme group, with a
short title, an audience, an optional status marker and a one-line description. Two files
are generated from it, so adding a page is one line in one file:

  docs/wiki/Contents.md   every page, grouped, one line each, with its status marker
  docs/wiki/_Sidebar.md   a compact sidebar: top links, then one collapsible group each,
                          with only the core path open by default

Parts, kept apart on purpose (the same shape as gen_project_status.py):

  load_manifest(text)       parse and reject duplicate keys; PyYAML is imported here only
  validate(manifest, pages) pure: the problems with a manifest against a set of page names
  render_contents(m), render_sidebar(m)
                            pure: manifest in, Markdown out. No file reads, no clock.
  main()                    --check is offline and exits 1 when a generated file is stale
                            or the manifest does not match the pages in docs/wiki.

Usage (from anywhere inside a clone):
  python -I scripts/gen_wiki_nav.py --check   exit 1 when stale or inconsistent
  python -I scripts/gen_wiki_nav.py           rewrite Contents.md and _Sidebar.md

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
SPECIAL = {"_Sidebar", "_Footer"}  # wiki chrome, not pages a reader navigates to

AUDIENCES = ("everyone", "newcomer", "learner", "builder", "engineer", "operator", "security reader")
STATUSES = ("draft", "est. steps", "unbuilt")
ORDERS = ("curated", "sorted")
MAX_DESC = 220
MAX_TITLE = 80
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
    loaded = yaml.load(text, Loader=Strict)  # a SafeLoader subclass: no Python tags
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
            extra = set(e) - {"page", "title", "audience", "status", "desc"}
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


def render_sidebar(manifest: dict) -> str:
    lines = [
        "<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this",
        "file by hand: add the page to the manifest and re-run the script. CI fails when this",
        "file does not match the manifest. -->",
        "",
    ]
    top = entries(manifest, TOP_GROUP)
    lines.append(" | ".join(f"**[{TOP_BAR_LABELS.get(e['page'], e['title'])}]({e['page']}.md)**" for e in top))
    for group in groups_of(manifest):
        if group["id"] == TOP_GROUP:
            continue
        pages = entries(manifest, group["id"])
        extra = link_entries(manifest, group["id"])
        count = len(pages) + len(extra)
        lines += ["", "<details open>" if group.get("open") else "<details>"]
        lines += [f"<summary><b>{group['title']}</b> ({count})</summary>", ""]
        for number, e in enumerate(pages, start=1):
            bullet = f"{number}." if group.get("numbered") else "-"
            lines.append(f"{bullet} {_sidebar_item(e)}")
        for e in extra:
            lines.append(f"- {_sidebar_item(e)}")
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


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
        print(f"gen_wiki_nav: {CONTENTS} and {SIDEBAR} match {MANIFEST}")
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
    (root / CONTENTS).write_text(render_contents(manifest), encoding="utf-8")
    (root / SIDEBAR).write_text(render_sidebar(manifest), encoding="utf-8")
    print(f"gen_wiki_nav: wrote {CONTENTS} and {SIDEBAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
