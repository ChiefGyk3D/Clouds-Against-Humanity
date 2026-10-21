"""Mechanical accessibility checks for the wiki pages in docs/wiki/.

Issue #130 asks for an accessibility pass over the whole wiki. The parts a
machine can hold are held here so the pass does not decay:

- every image has alt text that describes it (not a filename, not a stock word)
  and is short enough to be read aloud (long detail belongs in the text beside
  the image or in the Mermaid source block);
- no link says only "here" or similar, and no link has empty text or an empty target;
- heading levels never skip (an H2 is followed by an H2 or H3, never an H4);
- every table has a header row with a name in every cell.

The judgement parts (colour used as the only signal, jargon expanded on first
use or linked to the Glossary, emoji used as the only meaning) stay a manual
review at each wiki pull request; a regular expression cannot decide them.
Each rule is a function, and the tests also feed it bad text to prove it bites.
"""

import re
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
MAX_ALT = 150
FENCE = re.compile(r"^[ ]*(```|~~~).*?^[ ]*\1[^\n]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
IMAGE = re.compile(r"!\[([^\]\n]*)\]\(([^)\n]*)\)")
# A link is [text](target) not preceded by "!"; text may not contain "]".
LINK = re.compile(r"(?<!!)\[([^\]\n]*)\]\(([^)\n]*)\)")
HEADING = re.compile(r"^(#{1,6})[ \t]+(\S.*?)[ \t]*#*[ \t]*$")
FILENAME_ALT = re.compile(r"^[\w./-]+\.(png|jpe?g|gif|svg|webp)$", re.IGNORECASE)
SLUG_ALT = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)+$")
STOCK_ALT = {"image", "img", "picture", "photo", "screenshot", "diagram", "figure", "graphic", "icon", "alt", "alt text"}
VAGUE_LINK = {
    "here", "click here", "click", "link", "this link", "this page", "this", "read more", "more",
    "this document", "this doc", "see here", "go here", "over here", "there",
}


def strip_code(text: str) -> str:
    """Page text with fenced blocks removed and each inline code span masked as the word "code".

    Masking (not deleting) keeps a link or a table cell that holds only code
    from looking empty, and keeps examples such as `![](x.png)` from being counted."""
    return INLINE_CODE.sub("code", FENCE.sub("", text))


def alt_problems(page: str, text: str) -> list[str]:
    problems = []
    for m in IMAGE.finditer(strip_code(text)):
        alt = m.group(1).strip()
        if not alt:
            problems.append(f"{page}: image {m.group(2)!r} has no alt text")
        elif FILENAME_ALT.match(alt) or SLUG_ALT.match(alt):
            problems.append(f"{page}: alt text {alt!r} is a filename")
        elif alt.lower().rstrip(".") in STOCK_ALT:
            problems.append(f"{page}: alt text {alt!r} says nothing about the picture")
        elif len(alt) > MAX_ALT:
            problems.append(f"{page}: alt text is {len(alt)} characters, over {MAX_ALT}: {alt[:50]!r}...")
    return problems


def link_problems(page: str, text: str) -> list[str]:
    problems = []
    for m in LINK.finditer(strip_code(text)):
        label, target = m.group(1).strip(), m.group(2).strip()
        if not label:
            problems.append(f"{page}: link to {target!r} has empty text")
        elif label.lower().strip(" .:,;") in VAGUE_LINK:
            problems.append(f"{page}: link text {label!r} is not descriptive")
        if not target:
            problems.append(f"{page}: link {label!r} has an empty target")
    return problems


def heading_problems(page: str, text: str) -> list[str]:
    problems = []
    previous = 0
    for line in strip_code(text).splitlines():
        m = HEADING.match(line)
        if not m:
            continue
        level = len(m.group(1))
        if previous == 0 and level > 1:
            problems.append(f"{page}: first heading is H{level}, expected H1: {m.group(2)!r}")
        elif previous and level > previous + 1:
            problems.append(f"{page}: H{previous} is followed by H{level}: {m.group(2)!r}")
        previous = level
    return problems


def table_problems(page: str, text: str) -> list[str]:
    problems = []
    lines = strip_code(text).splitlines()
    separator = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
    for i, line in enumerate(lines):
        if not separator.match(line) or "|" not in line:
            continue
        header = lines[i - 1] if i else ""
        cells = [c.strip() for c in header.strip().strip("|").split("|")]
        if "|" not in header or not all(cells):
            problems.append(f"{page}: table header {header.strip()[:60]!r} has no header row or an unnamed column")
    return problems


def all_problems(page: str, text: str) -> list[str]:
    return alt_problems(page, text) + link_problems(page, text) + heading_problems(page, text) + table_problems(page, text)


def pages() -> list[Path]:
    return sorted(WIKI.glob("*.md"))


# -- the real tree ---------------------------------------------------------


def test_pages_were_collected():
    assert len(pages()) >= 40


@pytest.mark.parametrize(
    "check", [alt_problems, link_problems, heading_problems, table_problems], ids=lambda f: f.__name__
)
def test_every_page_passes(check):
    problems = []
    for page in pages():
        problems += check(page.name, page.read_text())
    assert not problems, "\n".join(problems)


def test_the_checks_see_something_to_check():
    text = "".join(p.read_text() for p in pages())
    assert len(IMAGE.findall(strip_code(text))) >= 10
    assert len(LINK.findall(strip_code(text))) >= 100
    assert sum(1 for line in strip_code(text).splitlines() if HEADING.match(line)) >= 100


# -- the checks bite -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "![](images/a.png)",
        "![   ](images/a.png)",
        "![diagram](images/a.png)",
        "![Screenshot.](images/a.png)",
        "![a-diagram-name.png](images/a.png)",
        "![architecture-overview](images/a.png)",
        "![" + "x" * (MAX_ALT + 1) + "](images/a.png)",
    ],
)
def test_bad_alt_text_is_caught(text):
    assert alt_problems("x.md", text)


def test_good_alt_text_passes_and_code_examples_are_ignored():
    assert not alt_problems("x.md", "![The firing alert in the lab's Prometheus](images/a.png)")
    assert not alt_problems("x.md", "```\n![](images/a.png)\n```\nand `![](b.png)`")


@pytest.mark.parametrize(
    "text",
    ["[here](a.md)", "See [Click here](a.md).", "[ ](a.md)", "[](a.md)", "[link](a.md)", "[Here.](a.md)", "[text]()"],
)
def test_bad_links_are_caught(text):
    assert link_problems("x.md", text)


def test_good_links_pass_and_images_are_not_links():
    assert not link_problems("x.md", "Read the [Glossary](Glossary.md) and ![A real description of it](images/a.png).")
    assert not link_problems("x.md", "```\n[here](a.md)\n```")


def test_skipped_heading_levels_are_caught():
    assert heading_problems("x.md", "# A\n\n#### D\n")
    assert heading_problems("x.md", "## starts at two\n")
    assert not heading_problems("x.md", "# A\n## B\n### C\n## D\n# E\n")
    assert not heading_problems("x.md", "# A\n```\n#### not a heading\n```\n## B\n")


def test_tables_without_a_named_header_are_caught():
    assert table_problems("x.md", "|   |   |\n|---|---|\n| a | b |\n")
    assert table_problems("x.md", "| Name |   |\n|---|---|\n| a | b |\n")
    assert table_problems("x.md", "just text\n|---|---|\n| a | b |\n")
    assert not table_problems("x.md", "| Name | Why |\n|---|---|\n| a |  |\n")
