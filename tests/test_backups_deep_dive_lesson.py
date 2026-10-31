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
TOPICS = (
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


def test_the_blast_radius_and_continuity_lessons_are_named_in_plain_text_not_linked():
    # tests/test_blast_radius_lesson.py caps how many pages may link the blast radius lesson, and the continuity
    # lesson may not be merged yet, so neither is linked from here.
    body = text()
    assert "Plan-for-Failure-Blast-Radius" not in body
    assert "business continuity and disaster recovery" in body


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
