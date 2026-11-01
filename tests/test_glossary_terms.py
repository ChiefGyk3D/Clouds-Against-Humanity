# SPDX-License-Identifier: Apache-2.0
"""Every term in the wiki Glossary is defined once (issue #409).

The same term with two definitions can contradict itself, so the first column of the Glossary table must hold
each term at most once, compared case-insensitively after HTML anchors and Markdown are stripped. The check
collects loosely (every table row after the header) and asserts strictly (no repeat, and enough rows were seen).
"""

import re
from pathlib import Path

from wikitext import page_text

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
HTML_TAG = re.compile(r"<[^>]*>")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean_term(cell: str) -> str:
    """A first-column cell reduced to its comparable term: no anchors, links or emphasis, lower case."""
    text = HTML_TAG.sub("", cell)
    text = MD_LINK.sub(r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return " ".join(text.split()).lower()


def first_column_terms(markdown: str) -> list[str]:
    """The cleaned first-column term of every body row of the first table in the text."""
    terms = []
    in_table = False
    for line in markdown.splitlines():
        if line.startswith("|"):
            cells = line.split("|")
            first = cells[1].strip() if len(cells) > 2 else ""
            if set(first) <= set("-: ") and first:
                in_table = True
                continue
            if in_table:
                terms.append(clean_term(first))
        elif in_table and terms:
            break
    return terms


def repeated(terms: list[str]) -> list[str]:
    return sorted({t for t in terms if terms.count(t) > 1})


def test_no_glossary_term_is_defined_twice():
    terms = first_column_terms(page_text(WIKI / "Glossary.md"))
    assert len(terms) > 500, f"the guard collected too few rows: {len(terms)}"
    assert all(terms), "a row has an empty first cell"
    assert repeated(terms) == []


def test_the_guard_bites_on_case_anchors_and_markdown():
    table = (
        "| Term | Meaning |\n|---|---|\n"
        "| **Patch** | one |\n"
        "| **patch** | two |\n"
        "| <a id=\"x\"></a>**[PATCH](A.md)** | three |\n"
        "| **`PHP-FPM`** | four |\n"
        "| **php-fpm** | five |\n"
        "| **Other** | six |\n"
    )
    assert first_column_terms(table) == ["patch", "patch", "patch", "php-fpm", "php-fpm", "other"]
    assert repeated(first_column_terms(table)) == ["patch", "php-fpm"]
    assert repeated(first_column_terms("| T | M |\n|---|---|\n| **A** | x |\n| **B** | y |\n")) == []
