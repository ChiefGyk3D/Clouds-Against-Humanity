# SPDX-License-Identifier: Apache-2.0
"""The CIA triad lesson: its script runs, its citations exist, it is registered and honest about what was run.

docs/wiki/The-CIA-Triad-Confidentiality-Integrity-Availability.md maps this project's controls to the three
properties and cites the repository file for each. A cited file that does not exist, a script whose output differs
from the page, a missing registration or a real address would each teach the wrong thing.
"""

import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "The-CIA-Triad-Confidentiality-Integrity-Availability"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PATH_TOKEN = re.compile(r"`((?:modules|stacks|scripts|\.github|\.spacelift|tests)/[A-Za-z0-9_./-]+|\.gitignore)`")
STATUS_WORDS = ("Read", "Observed", "Not run", "**est.**", "General knowledge")
PROPERTIES = ("Confidentiality", "Integrity", "Availability")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def section(body: str, start: str, end: str) -> str:
    return body.split(start)[1].split(end)[0]


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def cited_paths(cell: str) -> list[str]:
    return PATH_TOKEN.findall(cell)


def rows_missing_citation(rows: list[list[str]]) -> list[str]:
    """A project row must cite a file that exists, or say None in its file column and status."""
    bad = []
    for r in rows:
        files = r[2]
        paths = cited_paths(files)
        if files.startswith("None"):
            if "None" not in r[3]:
                bad.append(r[1])
        elif not paths or any(not (ROOT / p).exists() for p in paths):
            bad.append(r[1])
    return bad


def project_rows(body: str) -> list[list[str]]:
    return table_rows(section(body, "## Where this shows up in this project", "Three honest observations"))


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def test_the_banner_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# The CIA triad")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-10-31" in body


def test_all_three_properties_have_a_heading_and_a_nist_definition():
    body = text()
    for p in PROPERTIES:
        assert f"### {p}\n" in body
    for needle in ("Preserving authorized restrictions", "improper information modification or destruction", "timely and reliable access"):
        assert needle in body, needle


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_blast_radius_lesson_is_named_in_plain_text_not_linked():
    # tests/test_blast_radius_lesson.py caps how many pages may link it, and that cap is already full.
    assert "Plan-for-Failure-Blast-Radius" not in text()
    assert "blast radius" in text()


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav and 'status: "draft"' in nav.split(f"page: {NAME},")[1].split("\n")[0]
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [line for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in line]
    assert len(rows) >= 6, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_the_backups_page_links_the_lesson():
    assert f"{NAME}.md" in (WIKI / "Backups-Recovery-and-Patching.md").read_text(encoding="utf-8")


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert not ADDR.findall(body)
    assert "—" not in body


def test_the_address_guard_bites():
    assert ADDR.findall("ping 192.0.2.7")


def test_every_project_row_cites_an_existing_file_or_says_none():
    rows = project_rows(text())
    assert len(rows) >= 15, "the guard collected too few rows"
    assert {r[0] for r in rows} == set(PROPERTIES)
    assert not rows_missing_citation(rows)
    assert any(r[2].startswith("None") for r in rows), "the table should say None where nothing exists"


def test_the_citation_guard_bites():
    rows = [["Integrity", "x", "`scripts/does_not_exist.py`", "Built"], ["Integrity", "y", "`scripts/secret_rule.py`", "Built"], ["Availability", "z", "None here", "Built"]]
    assert rows_missing_citation(rows) == ["x", "z"]


def test_the_trade_offs_and_extensions_are_present():
    body = text()
    trade = section(body, "## The trade-offs", "## Extra properties")
    for pair in ("Confidentiality against availability", "Integrity against availability"):
        assert pair in trade, pair
    ext = body.split("## Extra properties some frameworks add")[1].split("## Where this shows up")[0]
    assert "Authenticity" in ext and "Non-repudiation" in ext and "extensions" in ext


def test_the_five_failure_shapes_are_mapped():
    block = section(text(), "## How real failures map to the triad", "## The trade-offs")
    for event in ("Ransomware", "A leaked token", "A bad deploy", "A cloud region outage", "An insider"):
        assert event in block, event


def test_the_lesson_leads_into_the_next_two_lessons_by_name_only():
    body = text()
    tail = body.split("## Leading into business continuity and disaster recovery")[1].split("## Checkpoint")[0]
    assert "issues 356 and 357" in body
    assert "business continuity" in tail and "disaster recovery" in tail
    assert "named, not linked" in tail


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(rows)
    assert any("csrc.nist.gov" in r[1] for r in rows) and any("2026-10-31" in r[-1] for r in rows)


def test_the_register_guard_bites():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]


def script() -> str:
    found = [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == "bash" and "# cia_lab.sh - " in b]
    assert len(found) == 1, f"expected one cia_lab.sh block, found {len(found)}"
    return found[0]


@pytest.mark.skipif(shutil.which("sha256sum") is None or shutil.which("tar") is None, reason="GNU coreutils and tar are needed")
def test_the_lab_script_runs_and_its_output_matches_the_page(tmp_path):
    path = tmp_path / "cia_lab.sh"
    path.write_text(script())
    done = subprocess.run(["bash", str(path)], capture_output=True, text=True, timeout=60, check=False, env={**os.environ, "TMPDIR": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    shown = next(b for t, b in FENCE.findall(text()) if t == "text" and b.startswith("== Integrity"))
    norm = re.compile(r"restore took \d+ ms")
    got = norm.sub("restore took N ms", done.stdout).strip().splitlines()
    want = norm.sub("restore took N ms", shown).strip().splitlines()
    if os.geteuid() == 0:
        got = [line for line in got if "denied" not in line and "still readable" not in line]
        want = [line for line in want if "denied" not in line]
    assert got == want
    assert not any(tmp_path.glob("tmp*")), "the script must delete its own lab folder"


def test_the_script_never_touches_anything_outside_its_own_folder():
    body = script()
    assert "mktemp -d" in body
    for line in body.splitlines():
        if line.startswith(("rm ", "chmod ", "tar ")):
            assert not re.search(r"\s/(?!$)", line), line
    assert not re.search(r"\bsudo\b|\bcurl\b|\bwget\b", body)
