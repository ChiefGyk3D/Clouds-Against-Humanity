"""Navigation checks for the wiki pages in docs/wiki/.

A page nobody links to is a page nobody reads. These tests keep the sidebar,
the Reading-Order page and the "Next:" lines honest as pages are added.
"""

import re
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE_LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
EXEMPT = {"_Sidebar", "_Footer", "Home"}


def pages() -> set[str]:
    return {p.stem for p in WIKI.glob("*.md")}


def linked(name: str) -> list[str]:
    return PAGE_LINK.findall((WIKI / f"{name}.md").read_text())


def test_every_page_is_in_the_sidebar_or_reading_order():
    reachable = set(linked("_Sidebar")) | set(linked("Reading-Order"))
    missing = sorted(pages() - EXEMPT - reachable)
    assert not missing, f"not in the sidebar or Reading-Order: {missing}"


def test_every_page_the_sidebar_links_exists():
    missing = sorted(set(linked("_Sidebar")) - pages())
    assert not missing, f"sidebar links to missing pages: {missing}"


def test_every_page_named_in_a_next_line_exists():
    problems = []
    for page in sorted(WIKI.glob("*.md")):
        for line in page.read_text().splitlines():
            if "Next:" not in line:
                continue
            for target in PAGE_LINK.findall(line):
                if target not in pages():
                    problems.append(f"{page.name}: {target}")
    assert not problems, f"Next lines name missing pages: {problems}"


def test_reading_order_lists_no_page_twice_within_one_path():
    text = (WIKI / "Reading-Order.md").read_text()
    sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    checked = 0
    for section in sections:
        title = section.splitlines()[0]
        rows = [
            line
            for line in section.splitlines()
            if re.match(r"\|\s*\d+\s*\|", line)
        ]
        if not rows:
            continue
        checked += 1
        targets = [PAGE_LINK.search(row).group(1) for row in rows if PAGE_LINK.search(row)]
        dupes = sorted({t for t in targets if targets.count(t) > 1})
        assert not dupes, f"{title}: listed twice: {dupes}"
    assert checked >= 5, "expected the core path and at least four tracks"


def test_reading_order_pages_all_exist():
    missing = sorted(set(linked("Reading-Order")) - pages())
    assert not missing, f"Reading-Order links to missing pages: {missing}"
