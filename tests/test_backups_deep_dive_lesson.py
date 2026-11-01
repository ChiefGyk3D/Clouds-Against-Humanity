# SPDX-License-Identifier: Apache-2.0
"""The backups deep dive lesson: its drill runs, its citations exist, it is registered and honest about what was run.

docs/wiki/Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md extends the Backups page with 3-2-1-1-0,
immutable copies, key custody and restore testing, and lists what this project would have to back up with the file
for each (or None). A cited file that does not exist, a drill whose output differs from the page, a missing
registration or a real address would each teach the wrong thing.
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
NAME = "Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PATH_TOKEN = re.compile(r"`((?:modules|stacks|scripts|docs|\.github|\.spacelift|tests)/[A-Za-z0-9_./-]+|board\.yaml|\.gitignore)`")
STATUS_WORDS = ("Read", "Observed", "Not run", "**est.**", "General knowledge")
RAID_LESSON = "RAID-Levels-Parity-Rebuilds-and-Why-RAID-Is-Continuity-Not-a-Backup"
BCP_LESSON = "Business-Continuity-and-Disaster-Recovery-BCP-and-DR"
RAID_SECTION = "## RAID is business continuity, not a backup"
TOPICS = (
    RAID_SECTION,
    "## From 3-2-1 to 3-2-1-1-0",
    "## Backup types: full, incremental, differential",
    "## Immutable and offline copies",
    "## Encryption and key custody",
    "## Backing up the backup system itself",
    "## Restore testing",
    "## Retention and legal holds",
    "## The ransomware angle",
    "## Cloud traps",
    "## Where this shows up in this project",
    "## Free path: a restore drill on your own computer",
    "## Claims register",
)


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
    """A project row must cite files that exist, or start with None in its file column and say None in its status."""
    bad = []
    for r in rows:
        files, status = r[2], r[3]
        paths = cited_paths(files)
        if any(not (ROOT / p).exists() for p in paths):
            bad.append(r[0])
        elif files.startswith("None"):
            if "None" not in status:
                bad.append(r[0])
        elif not paths:
            bad.append(r[0])
    return bad


def project_rows(body: str) -> list[list[str]]:
    return table_rows(section(body, "## Where this shows up in this project", "Four honest notes"))


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def test_the_banner_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Backups deep dive")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-10-31" in body


def test_every_topic_the_issue_asked_for_has_a_section():
    body = text()
    missing = [t for t in TOPICS if f"\n{t}\n" not in body]
    assert not missing, missing


def test_the_coiner_of_3_2_1_1_0_is_named_with_a_page_and_dates():
    body = text()
    assert "At Veeam, we extended the rule to 3-2-1-1-0" in body
    assert "February 5, 2024" in body and "July 3, 2026" in body
    assert "https://www.veeam.com/blog/321-backup-rule.html" in body
    for needle in ("SP 800-34", "StopRansomware"):
        assert needle in body, needle


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_blast_radius_lesson_is_named_in_plain_text_and_the_continuity_lesson_is_linked():
    # tests/test_blast_radius_lesson.py caps how many pages may link the blast radius lesson, so it is not linked
    # from here. The continuity lesson is merged and is linked (issue 421).
    body = text()
    assert "Plan-for-Failure-Blast-Radius" not in body
    assert "business continuity and disaster recovery" in body
    assert f"]({BCP_LESSON}.md" in body
    assert f"]({RAID_LESSON}.md" in body


def raid_section(body: str) -> str:
    return section(body, RAID_SECTION, "\n## From 3-2-1 to 3-2-1-1-0")


def test_the_page_leads_with_raid_as_continuity_and_not_a_backup():
    body = text()
    opening = body.split("> Unfamiliar word or acronym?")[0]
    assert "RAID" in opening and "not a backup" in opening, "the opening paragraph carries the framing"
    assert body.index(RAID_SECTION) < body.index("## From 3-2-1 to 3-2-1-1-0"), "the RAID section comes first"
    assert body.index(RAID_SECTION) < body.index("## Backup types"), "the RAID section comes before the backup types"
    sec = raid_section(body)
    for needed in (
        "business continuity",
        "availability",
        "not a backup",
        "at most one copy",
        "deletion",
        "corruption",
        "ransomware",
        "site",
        "SP 800-34",
        "cannot be a replacement for a solid backup strategy",
        "Without a backup of the system separate from the system itself",
        "Linux Raid Wiki",
        "backup, backup, BACK UP",
        "RAID is not a panacea",
        "Patterson",
        "backup versions of all information every night",
    ):
        assert needed in sec, needed
    for link in (BCP_LESSON, RAID_LESSON, "The-CIA-Triad-Confidentiality-Integrity-Availability"):
        assert f"]({link}.md" in sec, link


def test_the_raid_section_has_a_table_that_says_what_each_event_does_to_raid_and_to_a_backup():
    sec = raid_section(text())
    rows = table_rows(sec)
    assert len(rows) >= 7, "the guard collected too few rows"
    events = " ".join(r[0] for r in rows).lower()
    for needed in ("drive", "deleted", "ransomware", "corrupt", "controller", "fire"):
        assert needed in events, needed
    # a drive failure is the one row where RAID helps; every other row says RAID does not
    first = rows[0]
    assert "Yes" in first[1] and "drive" in first[0].lower()
    assert sum("**No**" in r[1] for r in rows) >= 5
    assert sum("**No**" in r[2] for r in rows) <= 2, "a backup is not a cure for everything either"


def test_the_raid_section_guard_bites():
    assert raid_section(f"x\n{RAID_SECTION}\nbody\n\n## From 3-2-1 to 3-2-1-1-0\ny") == "\nbody\n"
    bad = ["a drive fails", "Yes", "Yes"], ["ransomware", "Yes", "Yes"]
    assert sum("**No**" in r[1] for r in bad) == 0


def test_the_banner_and_summary_say_the_raid_section_was_added_on_2026_11_01_from_reading():
    body = text()
    banner = body.split("## What you will be able to do")[0]
    assert "2026-11-01" in banner and "issue 421" in banner
    low = body.split("## What you will be able to do")[1].split("## What the wiki already says")[0].lower()
    assert "raid" in low and "not a backup" in low


def test_the_register_carries_the_raid_sources_read_on_2026_11_01():
    rows = register_rows(text())
    joined = " ".join(r[1] for r in rows)
    for host in (
        "nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-34r1.pdf",
        "raid.wiki.kernel.org/index.php/How_to_protect_your_data",
        "www2.eecs.berkeley.edu/Pubs/TechRpts/1987/CSD-87-391.pdf",
    ):
        assert host in joined, host
    assert sum("2026-11-01" in r[-1] for r in rows) >= 3
    assert not rows_missing_status(rows)


def test_the_common_mistakes_table_names_the_raid_is_a_backup_mistake():
    block = section(text(), "## Common mistakes", "## Claims register")
    assert any("RAID" in r[0] and "backup" in r[0].lower() for r in table_rows(block))


def test_the_lesson_is_registered_in_contents_and_reading_order_not_the_sidebar():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    assert "sidebar" not in entry, "new lessons are reached from Contents and Reading Order, not the sidebar"
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [line for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in line]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


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
    assert len(rows) >= 10, "the guard collected too few rows"
    assert not rows_missing_citation(rows)
    assert sum(r[2].startswith("None") for r in rows) >= 4, "the table should say None where nothing exists"
    wanted = ("repository", "wiki", "Issues", "OpenTofu state", "secret store", "Twingate", "backup system itself", "timed restore")
    joined = " ".join(r[0] for r in rows)
    assert all(w in joined for w in wanted), [w for w in wanted if w not in joined]


def test_the_citation_guard_bites():
    rows = [
        ["a", "x", "`scripts/does_not_exist.py`", "Built"],
        ["b", "x", "`scripts/secret_rule.py`", "Built"],
        ["c", "x", "None here", "Built"],
        ["d", "x", "None; the design is in `docs/does/not/exist.md`", "None"],
        ["e", "x", "no path at all", "Built"],
    ]
    assert rows_missing_citation(rows) == ["a", "c", "d", "e"]


def test_every_repository_path_the_page_names_exists():
    paths = set(cited_paths(text()))
    assert len(paths) >= 10, "the guard collected too few paths"
    assert not [p for p in sorted(paths) if not (ROOT / p).exists()]


def test_the_immutability_table_names_what_it_does_not_protect_against():
    block = section(text(), "### What immutability protects against, and what it does not", "Notice that **versioning is not immutability.**")
    rows = table_rows(block)
    assert len(rows) >= 6
    assert sum("**No**" in r[1] for r in rows) >= 3
    assert any("account" in r[0] for r in rows)


def test_the_key_custody_table_has_a_circular_and_a_single_holder_case():
    block = section(text(), "## Encryption and key custody", "## Backing up the backup system itself")
    assert "single point of failure" in block and "A circle" in block
    assert "irrecoverably lost" in block


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(rows)
    assert any("nvlpubs.nist.gov" in r[1] for r in rows) and any("cisa.gov/stopransomware" in r[1] for r in rows)
    assert sum("2026-10-31" in r[-1] for r in rows) >= 10


def test_the_register_guard_bites():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]


def script() -> str:
    found = [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == "bash" and "# backup_drill.sh - " in b]
    assert len(found) == 1, f"expected one backup_drill.sh block, found {len(found)}"
    return found[0]


@pytest.mark.skipif(any(shutil.which(t) is None for t in ("sha256sum", "tar", "openssl", "dd")), reason="GNU coreutils, tar and openssl are needed")
def test_the_drill_runs_and_its_output_matches_the_page(tmp_path):
    path = tmp_path / "backup_drill.sh"
    path.write_text(script())
    done = subprocess.run(["bash", str(path)], capture_output=True, text=True, timeout=120, check=False, env={**os.environ, "TMPDIR": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    shown = next(b for t, b in FENCE.findall(text()) if t == "text" and b.startswith("== Backup types"))
    norm = re.compile(r"took \d+ ms")
    got = [line.rstrip() for line in norm.sub("took N ms", done.stdout).strip().splitlines()]
    want = [line.rstrip() for line in norm.sub("took N ms", shown).strip().splitlines()]
    assert got == want
    assert not any(tmp_path.glob("tmp*")), "the script must delete its own lab folder"


def test_the_drill_never_touches_anything_outside_its_own_folder():
    body = script()
    assert "mktemp -d" in body
    for line in body.splitlines():
        if line.startswith(("rm ", "chmod ", "tar ", "cp ")):
            assert not re.search(r"\s/(?!$)", line), line
    assert not re.search(r"\bsudo\b|\bcurl\b|\bwget\b|\bchattr\b", body)
    assert "of=copy-a/backup.tgz" in body, "the only deliberate damage is to the drill's own copy"
