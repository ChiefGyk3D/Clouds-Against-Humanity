# SPDX-License-Identifier: Apache-2.0
"""The business continuity and disaster recovery lesson: registered, honest about what was run, and checkable.

docs/wiki/Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md teaches BCP versus DR and plans recovery for this
project's own pieces. A broken link, a missing registration, a recovery step cited from a file that does not exist, a
sample output that no longer matches the script, a claim with no status, or a link that pushes another lesson over its
link cap would each teach the wrong thing.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Business-Continuity-and-Disaster-Recovery-BCP-and-DR"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
REPO_URL = "https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/"
STATUS_WORDS = ("Read", "Observed", "Not read", "General knowledge", "**est.**", "Common practice")
BLAST = "Plan-for-Failure-Blast-Radius-and-Assuming-Breach"
PIECES = ("1. The repository", "2. The secret store", "3. Spacelift state", "4. Twingate", "5. The connectors", "6. The wiki", "7. The home logging server")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(tag: str) -> list[str]:
    return [b for t, b in FENCE.findall(text()) if t == tag]


def csv_blocks() -> list[str]:
    return [b for b in blocks("text") if b.startswith("system,tier,")]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("## Where to next")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def cited_repo_paths(body: str) -> set[str]:
    paths = set(re.findall(re.escape(REPO_URL) + r"([A-Za-z0-9_./-]+?)(?:#[^)]*)?\)", body))
    paths |= set(re.findall(r"`((?:tests|scripts|docs|\.github)/[A-Za-z0-9_./-]+)`", body))
    return paths


def missing_paths(paths: set[str]) -> list[str]:
    return sorted(p for p in paths if not (ROOT / p).exists())


def run_checker(tmp: Path, table: str, today: str = "2026-10-31") -> subprocess.CompletedProcess:
    script, data = tmp / "bia_check.py", tmp / "table.csv"
    script.write_text(blocks("python")[0], encoding="utf-8")
    data.write_text(table, encoding="utf-8")
    return subprocess.run([sys.executable, "-I", str(script), str(data), "--today", today], capture_output=True, text=True, timeout=60, check=False)


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Business continuity and disaster recovery")
    assert "Status: unverified draft" in body
    assert "no recovery procedure on this page was run" in body
    assert "2026-10-31" in body
    assert "ever been timed" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav and 'status: "draft"' in nav.split(f"page: {NAME},")[1].split("\n")[0]
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [line for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in line]
    assert len(rows) >= 7, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors: set[str] = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_related_lessons_link_the_new_one():
    skip = {"Glossary.md", "_Sidebar.md", "Reading-Order.md", "Contents.md", PAGE.name}
    inbound = [p.name for p in WIKI.glob("*.md") if p.name not in skip and f"{NAME}.md" in p.read_text(encoding="utf-8")]
    assert len(inbound) >= 4, inbound


def test_the_blast_radius_lesson_is_named_in_plain_text_so_its_link_cap_holds():
    # tests/test_blast_radius_lesson.py caps the pages that link that lesson at 9, and it is already at 9.
    assert f"{BLAST}.md" not in text()
    assert "blast radius and assuming breach" in text()


def test_the_cap_guard_bites():
    assert f"{BLAST}.md" in "see [x](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md)"


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert not ADDR.findall(body), set(ADDR.findall(body))
    assert "—" not in body
    assert "Python" in body, "the guard collected nothing"


def test_the_address_guard_bites():
    assert ADDR.findall("ping 192.0.2.7")


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n\n## Where to next\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_sources_are_dated_and_the_unread_one_is_not_cited():
    body = text()
    reg = body.split("## Claims register")[1]
    for needle in ("NIST SP 800-34", "Ready.gov", "AWS Well-Architected", "CISA #StopRansomware", "GitLab", "Atlassian", "CrowdStrike"):
        row = next((line for line in reg.splitlines() if needle in line), "")
        assert "Read 2026-10-31" in row, needle
    assert "returned \"404 - Page not found\"" in body
    assert "Not read: the page returned" in reg


def test_the_four_postmortems_carry_their_dates():
    section = text().split("## Lessons from public postmortems")[1].split("## A worked plan for this project")[0]
    for date in ("10 February 2017", "29 April 2022", "19 to 20 October 2025", "August 2024"):
        assert date in section, date


def test_the_project_plan_covers_all_seven_pieces_with_steps_and_coverage():
    plan = text().split("## A worked plan for this project")[1].split("## Free exercises")[0]
    for piece in PIECES:
        assert f"### {piece}" in plan, piece
    assert plan.count("**Recovery steps**") == 7 and plan.count("**Covered by**") == 7
    assert plan.count("**Proposed RTO / RPO**") == 7
    assert "**None.**" in plan or "**None**" in plan, "the plan must say None where nothing exists"
    assert "proposals" in plan and "never timed" in plan


def test_every_repository_file_the_page_cites_exists():
    paths = cited_repo_paths(text())
    assert len(paths) >= 8, "the guard collected too few paths"
    assert not missing_paths(paths)


def test_the_path_guard_bites():
    assert missing_paths({"docs/stages/99-not-a-stage.md"}) == ["docs/stages/99-not-a-stage.md"]


def test_the_checker_output_on_the_page_matches_a_real_run(tmp_path):
    body = text()
    tables = csv_blocks()
    assert len(tables) == 2, "expected the project table and the broken table"
    done = run_checker(tmp_path, tables[0])
    assert done.returncode == 0, done.stdout + done.stderr
    for line in done.stdout.strip().splitlines():
        assert line in body, line
    assert "7 systems, 0 fail, 2 warn" in done.stdout


def test_the_broken_table_fails_in_the_ways_the_page_says(tmp_path):
    done = run_checker(tmp_path, csv_blocks()[1])
    assert done.returncode == 1
    assert done.stdout.count("FAIL") == 4
    for needle in ("cannot meet an RPO of 4 h", "shop: RTO 2 h is shorter than database's 8 h", "cache: RTO 1 h is shorter", "'queue', which is not in the table"):
        assert needle in done.stdout, needle
    assert "WARN  shop: the last restore test (2024-01-05) is more than a year old" in done.stdout


def test_the_checker_passes_a_sound_table(tmp_path):
    sound = "system,tier,rto_hours,rpo_hours,copy_every_hours,last_restore_test,depends_on\ndb,0,8,4,4,2026-09-01,\napp,1,12,4,4,2026-09-01,db\n"
    done = run_checker(tmp_path, sound)
    assert done.returncode == 0 and "0 fail, 0 warn" in done.stdout, done.stdout


def test_the_tabletop_has_its_ground_rules_and_five_injects():
    section = text().split("### Exercise 4: a free tabletop on a scenario from this project")[1].split("## Checkpoint")[0]
    assert "Only what is written down counts" in section
    assert "at most three findings" in section
    injects = re.findall(r"^\d\. \*\*", section, re.MULTILINE)
    assert len(injects) == 5, injects
    assert "could not read DIGITALOCEAN_TOKEN from Doppler" in section
    assert "nothing is run, restored or changed" in section


def test_the_bcp_and_dr_definitions_are_attributed_to_nist():
    section = text().split("## BCP and DR: two plans, not one")[1].split("## Business impact analysis")[0]
    assert "NIST SP 800-34 Rev. 1" in section
    assert "sustaining an organization's mission/business processes" in section
    assert "information system-focused plan" in section
