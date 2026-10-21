"""American English is the project's spelling standard (see docs/wiki/How-This-Project-Is-Planned.md).

The checker looks at README.md and docs/wiki/*.md and flags a conservative list of
unambiguous British spellings in prose. Fenced code, inline code, URLs and link
targets are ignored, and docs/american-english-allowlist.txt lists deliberate
exceptions as `path:word | reason`. The checker is a function so a test can prove
it bites on an injected word and stays quiet inside a code fence.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "docs" / "american-english-allowlist.txt"

# Only words that are British and nothing else; "dialogue", "cancelled" (a GitHub result
# value) and "towards" are left out on purpose. ISE_STEMS take the endings prose uses, so
# "realistic" or "analysis" cannot match.
ISE_STEMS = [
    "organis",
    "recognis",
    "authoris",
    "minimis",
    "optimis",
    "standardis",
    "summaris",
    "centralis",
    "serialis",
    "normalis",
    "finalis",
    "customis",
    "utilis",
    "prioritis",
    "categoris",
    "virtualis",
    "synchronis",
    "initialis",
    "sanitis",
    "generalis",
    "visualis",
    "characteris",
]
ISE_ENDINGS = r"(?:e|es|ed|ing|er|ers|ation|ations|able)"
BRITISH = re.compile(
    r"\b(?:"
    r"behaviour\w*|colour\w*|favour\w*|honour\w*|neighbour\w*|labour|flavour\w*|harbour\w*|humour"
    r"|defence\w*|offence\w*|pretence|licences?"
    r"|centre\w*|metre\w*|litre\w*|fibre\w*|theatre\w*|calibre"
    r"|catalogue\w*|labelled|labelling|modelled|modelling|travelled|travelling"
    r"|signalling|fuelled|levelled|counselling"
    r"|grey\w*|programme\w*|cheque\w*|tyre\w*|kerb|aluminium|artefact\w*|enrolment|fulfilment"
    r"|instalment\w*|judgement\w*|ageing|whilst|amongst|learnt|spelt|practise\w*"
    r"|analys(?:e|ed|ing|er|ers)|paralys(?:e|es|ed|ing)"  # not "analyses", the plural of analysis
    r"|(?:" + "|".join(ISE_STEMS) + r")" + ISE_ENDINGS +
    r")\b",
    re.IGNORECASE,
)

FENCE_LINE = re.compile(r"^\s*(```|~~~)")
MASK = re.compile(r"`[^`\n]*`|https?://\S+|\]\([^)\n]*\)|<[^>\n]+>")


def british_words(text: str) -> list[tuple[int, str]]:
    """(line number, word) for each British spelling in prose, skipping code, URLs and link targets."""
    found = []
    in_fence = False
    for number, line in enumerate(text.split("\n"), start=1):
        if FENCE_LINE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in BRITISH.finditer(MASK.sub(" ", line)):
            found.append((number, m.group(0)))
    return found


def load_allowlist(text: str) -> set[tuple[str, str]]:
    """Parse `path:word | reason` lines; a line without a reason is an error."""
    allowed = set()
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entry, sep, reason = line.partition("|")
        path, colon, word = entry.strip().rpartition(":")
        if not sep or not reason.strip() or not colon or not path or not word.strip():
            raise ValueError(f"allowlist line needs 'path:word | reason': {raw!r}")
        allowed.add((path.strip(), word.strip().lower()))
    return allowed


def pages() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "docs" / "wiki").glob("*.md"))]


def test_checker_collects_the_pages():
    names = {p.name for p in pages()}
    assert "README.md" in names and "How-This-Project-Is-Planned.md" in names
    assert len(pages()) > 30


def test_no_british_spelling_in_readme_or_wiki():
    allowed = load_allowlist(ALLOWLIST.read_text(encoding="utf-8"))
    problems = []
    for page in pages():
        rel = page.relative_to(ROOT).as_posix()
        for number, word in british_words(page.read_text(encoding="utf-8")):
            if (rel, word.lower()) not in allowed:
                problems.append(f"{rel}:{number}: {word}")
    assert not problems, "British spelling (use American English):\n" + "\n".join(problems)


def test_checker_catches_an_injected_word():
    assert british_words("The defence is deep.\nA second line.") == [(1, "defence")]
    assert british_words("Behaviour, colours and organised work; whilst analysing.")[0] == (1, "Behaviour")


def test_checker_ignores_code_urls_and_link_targets():
    text = "```\ndefence behaviour\n```\nInline `colour` and https://example.invalid/defence and [x](grey-page.md).\n"
    assert british_words(text) == []
    assert british_words("~~~\ncentre\n~~~\nthe centre") == [(4, "centre")]


def test_checker_leaves_american_and_ambiguous_words_alone():
    assert british_words("defense, color, analyses, license, licensed, center, organize, analysis, cancelled, dialogue, towards") == []


def test_allowlist_needs_a_reason_and_matches_path_and_word():
    assert load_allowlist("# c\n\ndocs/wiki/X.md:defence | quoted vendor text\n") == {("docs/wiki/X.md", "defence")}
    with pytest.raises(ValueError):
        load_allowlist("docs/wiki/X.md:defence\n")
    with pytest.raises(ValueError):
        load_allowlist("docs/wiki/X.md:defence |   \n")
