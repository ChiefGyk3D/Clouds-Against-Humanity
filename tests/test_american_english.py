"""American English is the project's spelling standard (see docs/wiki/How-This-Project-Is-Planned.md).

The checker looks at README.md and docs/wiki/*.md and flags a conservative list of
unambiguous British spellings in prose. Fenced code, inline code, URLs and link
targets are ignored, and docs/american-english-allowlist.txt lists deliberate
exceptions as `path:word | reason`. The checker is a function so a test can prove
it bites on an injected word and stays quiet inside a code fence.
"""

import ast
import io
import json
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "docs" / "american-english-allowlist.txt"

# Only words that are British and nothing else; "dialogue" and "towards" are left out on
# purpose. "cancelled" is here too: prose spells it "canceled", and the few literals that
# must keep it (a GitHub job result value) are allowlisted with a reason. ISE_STEMS take the endings prose uses, so
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
    r"|catalogue\w*|cancelled|cancelling|unlabelled|labelled|labelling|modelled|modelling|travelled|travelling"
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


def british_words(text: str, fenced: bool = True) -> list[tuple[int, str]]:
    """(line number, word) for each British spelling in prose, skipping code, URLs and link targets."""
    found = []
    in_fence = False
    for number, line in enumerate(text.split("\n"), start=1):
        if fenced and FENCE_LINE.match(line):
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


def tracked(*patterns: str) -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", *patterns], capture_output=True, text=True, check=True).stdout
    return [ROOT / name for name in out.split()]


def python_prose(text: str) -> str:
    """Comments and docstrings only, on their original line numbers; identifiers and string data are skipped."""
    lines = [""] * (text.count("\n") + 1)
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            lines[tok.start[0] - 1] += " " + tok.string
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and ast.get_docstring(node, clean=False):
            first = node.body[0]
            for offset, doc_line in enumerate(first.value.value.split("\n")):
                lines[first.lineno - 1 + offset] += " " + doc_line
    return "\n".join(lines)


def comment_prose(text: str) -> str:
    """Whole-line comments of HCL, YAML and shell files, on their original line numbers."""
    return "\n".join(line if line.lstrip().startswith(("#", "//")) else "" for line in text.split("\n"))


def json_descriptions(text: str) -> str:
    """The 'description' strings of a JSON file, one per line, so a hit names the value (line numbers are not kept)."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "description" and isinstance(value, str):
                    found.append(value.replace("\n", " "))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads(text))
    return "\n".join(found)


def prose_of(path: Path) -> list[tuple[int, str]]:
    """British words in the prose of one repository file, by kind of file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return british_words(text)
    if path.suffix == ".py":
        return british_words(python_prose(text), fenced=False)
    if path.suffix == ".json" and path.parts[-3:-1] == ("docs", "threat-model"):
        return british_words(json_descriptions(text), fenced=False)
    if path.suffix in {".tf", ".hcl", ".yml", ".yaml", ".sh"}:
        return british_words(comment_prose(text), fenced=False)
    return []


def pages() -> list[Path]:
    return [
        *tracked("*.md", "*.py", "*.tf", "*.hcl", "*.yml", "*.yaml", "*.sh"),
        *sorted((ROOT / "docs" / "threat-model").glob("*.json")),
    ]


def test_checker_collects_the_pages():
    names = {p.name for p in pages()}
    assert {"README.md", "How-This-Project-Is-Planned.md", "zero_ports_check.py"} <= names
    assert any(p.suffix == ".json" for p in pages()) and len(pages()) > 100


def test_no_british_spelling_in_repository_prose():
    allowed = load_allowlist(ALLOWLIST.read_text(encoding="utf-8"))
    problems = []
    for page in pages():
        rel = page.relative_to(ROOT).as_posix()
        for number, word in prose_of(page):
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
    assert british_words("defense, color, analyses, license, licensed, center, organize, analysis, canceled, dialogue, towards") == []


def test_allowlist_needs_a_reason_and_matches_path_and_word():
    assert load_allowlist("# c\n\ndocs/wiki/X.md:defence | quoted vendor text\n") == {("docs/wiki/X.md", "defence")}
    with pytest.raises(ValueError):
        load_allowlist("docs/wiki/X.md:defence\n")
    with pytest.raises(ValueError):
        load_allowlist("docs/wiki/X.md:defence |   \n")


def test_cancelled_is_caught_in_prose_and_code_comments_but_not_in_code():
    assert british_words("A cancelled job.") == [(1, "cancelled")]
    assert british_words(python_prose("x = fut.cancelled()  # a cancelled future\n")) == [(1, "cancelled")]
    assert british_words(python_prose("x = fut.cancelled()\n"), fenced=False) == []


def test_comment_and_json_extractors_skip_code_and_keys():
    assert british_words(comment_prose('name = "colour"  # fine\n# the behaviour\n'), fenced=False) == [(2, "behaviour")]
    assert british_words(json_descriptions('{"colour": {"description": "grey box"}}'), fenced=False) == [(1, "grey")]
    assert british_words(json_descriptions('{"colour": "x", "description": "gray"}'), fenced=False) == []
