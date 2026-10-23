"""The blast radius lesson: its exercise script runs, and its claims register, sections and links hold.

docs/wiki/Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md teaches a mindset and a small Python
exercise that computes what one compromised node reaches. A script that does not run, or numbers on
the page that the script does not produce, teach the wrong thing. The test pulls the script out of
the page, runs it, and checks the output shown on the page against the real output.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+\.md)(?:#[^)]*)?\)")
SECTIONS = [
    "## What you will be able to do",
    "## The maintainer's framing, in his words",
    "## In plain words",
    "## Three ideas, defined once",
    "## Why defenders have to be right every time",
    "## Contain, detect, recover, and prevent",
    "## Where this shows up in this project",
    "## What does not count as protection",
    "## Honest limits",
    "## Free path: a lab with nothing to lose",
    "## Checkpoint",
    "## Common mistakes",
    "## Claims register",
]


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def script() -> str:
    found = [b for tag, b in FENCE.findall(text()) if tag == "python" and "radius.py - what does" in b]
    assert len(found) == 1, f"expected one radius.py block, found {len(found)}"
    return found[0]


def run(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(path), *args], capture_output=True, text=True, timeout=60, check=False)


@pytest.fixture()
def radius(tmp_path):
    p = tmp_path / "radius.py"
    p.write_text(script())
    return p


def test_default_run_matches_the_output_shown_on_the_page(radius):
    done = run(radius)
    assert done.returncode == 0, done.stderr
    shown = [b for tag, b in FENCE.findall(text()) if tag == "text" and b.startswith("Before:")]
    assert len(shown) == 1
    assert done.stdout.strip() == shown[0].strip()


def test_cutting_the_edge_shrinks_the_radius_and_states_a_cost(radius):
    out = run(radius).stdout
    assert "web compromised: reach went from 1 to 0." in out
    assert "What it costs:" in out


def test_a_second_cut_changes_the_laptop_not_the_web_server(radius):
    out = run(radius, "laptop", "vault").stdout
    assert "laptop compromised: reach went from 3 to 2." in out


def test_a_missing_edge_exits_two(radius):
    done = run(radius, "x", "y")
    assert done.returncode == 2 and "usage" in done.stderr


def test_required_sections_are_present_in_order():
    body = text()
    positions = [body.index(s) for s in SECTIONS]
    assert positions == sorted(positions)


def test_the_maintainers_framing_is_quoted_and_attributed():
    body = text()
    assert "we will fail to protect from those attacks" in body
    assert "they only have to be right once" in body
    assert "ChiefGyk3D" in body and "Grammar fixes only" in body


def test_the_three_questions_box_is_present():
    body = text()
    for q in ("what can it reach", "How will I know", "How do I recover"):
        assert q in body


def test_claims_register_marks_unrun_and_estimates():
    reg = text().split("## Claims register")[1]
    assert "2026-10-22" in reg
    assert "est." in reg and "Not run" in reg
    assert "**Observed**" in reg


def test_no_em_dashes_in_the_lesson():
    assert "—" not in text()


def test_no_machine_addresses_in_the_lesson():
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text())


def test_every_linked_wiki_page_exists():
    missing = sorted({t for t in LINK.findall(text()) if not (WIKI / t).exists()})
    assert not missing, missing


def test_glossary_has_exactly_one_blast_radius_row_and_it_links_the_lesson():
    rows = [l for l in (WIKI / "Glossary.md").read_text().splitlines() if l.startswith("| **Blast radius**")]
    assert len(rows) == 1
    assert PAGE.name in rows[0]
    # both earlier references are kept
    assert "WordPress-at-Scale-CDN-WAF-and-CI.md#tenant-isolation" in rows[0]
    assert "Build-and-Destroy-Stack-Per-Service.md#why-one-stack-per-service" in rows[0]


def test_glossary_defines_assume_breach_and_defense_in_depth():
    g = (WIKI / "Glossary.md").read_text()
    assert "| **Assume breach** |" in g and "| **Defense in depth** |" in g


def test_at_least_four_existing_pages_link_the_lesson_at_first_use():
    users = [p.name for p in WIKI.glob("*.md") if p != PAGE and p.name not in {"Glossary.md", "_Sidebar.md", "Reading-Order.md"} and PAGE.name in p.read_text()]
    assert 4 <= len(users) <= 8, users


def test_the_lesson_is_in_the_sidebar_and_reading_order():
    assert PAGE.name in (WIKI / "_Sidebar.md").read_text()
    assert PAGE.name in (WIKI / "Reading-Order.md").read_text()
