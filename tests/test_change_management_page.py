"""Checks for docs/wiki/Enterprise-Change-Management-for-Beginners.md.

The page is general-industry orientation, not a description of this project.
These tests keep it honest: the banner is present, it has Prerequisites and a
Next line, every predict-then-check exercise has a reference answer, the change
failure rate in the worked table is recomputed rather than trusted, and the
page never claims the project runs a CAB.
"""

import re
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Enterprise-Change-Management-for-Beginners.md"
BANNER = (
    "Orientation: general industry practice, not used by this project; "
    "frameworks cited with retrieval dates or marked UNVERIFIED"
)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")


def text() -> str:
    return PAGE.read_text()


def test_banner_prerequisites_and_next_line():
    t = text()
    assert BANNER in t.splitlines()[2]
    assert "**Prerequisites:**" in t
    nexts = [line for line in t.splitlines() if line.startswith("Next:")]
    assert len(nexts) == 1
    for target in LINK.findall(nexts[0]):
        assert (WIKI / f"{target[0]}.md").exists(), target


def test_every_exercise_has_a_reference_answer():
    t = text()
    exercises = re.findall(r"^### Exercise \d+", t, flags=re.MULTILINE)
    assert len(exercises) >= 5
    for block in re.split(r"^### Exercise \d+", t, flags=re.MULTILINE)[1:]:
        block = block.split("\n## ")[0]
        assert "**Reference answer.**" in block, block[:80]


def test_change_failure_rate_is_recomputed():
    t = text()
    rows = re.findall(r"^\| (\d) \| (\d+) \| (\d+) \|$", t, flags=re.MULTILINE)
    assert len(rows) == 4
    deployments = sum(int(r[1]) for r in rows)
    failures = sum(int(r[2]) for r in rows)
    rate = round(100 * failures / deployments)
    assert f"= **{rate}%**" in t


def test_page_says_the_project_does_not_use_change_management():
    t = text()
    assert "## Is any of this used in this project?" in t
    section = t.split("## Is any of this used in this project?")[1]
    assert section.lstrip().startswith("**No.**")
    assert "No CAB" in section


def test_unsourced_framework_claims_are_marked():
    t = text()
    for framework in ("SOC 2", "ISO/IEC 27001", "SOX IT general controls"):
        line = next(ln for ln in t.splitlines() if ln.startswith("- **" + framework))
        assert "UNVERIFIED" in line, framework


def test_internal_anchors_exist():
    for target, anchor in LINK.findall(text()):
        if not anchor:
            continue
        other = (WIKI / f"{target}.md").read_text()
        slugs = set()
        for h in re.findall(r"^#+ (.+)$", other, flags=re.MULTILINE):
            s = re.sub(r"[^\w\- ]", "", h.lower()).strip().replace(" ", "-")
            slugs.add(s)
        assert anchor in slugs, f"{target}#{anchor}"
