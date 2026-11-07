# SPDX-License-Identifier: Apache-2.0
"""The disk forensics lesson: it is registered, honest about what was run, and safe to follow.

docs/wiki/Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md teaches imaging, hashing first and The Sleuth Kit commands
on a practice image the reader builds. A broken link, a missing registration, a claim with no status, a real address,
a missing authorization rule or a hash step placed after the examination would each teach the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "Search summary only", "**est.**")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("Not verified, plainly")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def test_the_page_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Disk forensics with Autopsy and The Sleuth Kit")
    assert "Status: unverified draft" in body
    assert "Autopsy itself was not installed or started" in body
    assert "**Not run:**" in body and "2026-11-07" in body
    assert "Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_gap_check_links_are_present():
    links = set(LINK.findall(text()))
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        "Hashing-Encryption-and-Keys",
        "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options",
        "Terminal-and-Your-First-Script",
    ):
        assert needed in links, needed


def test_sibling_forensics_lessons_are_plain_text_not_links():
    body = text()
    for issue in ("#474", "#476", "#477", "#478"):
        assert issue in body, issue
    # The generated nav blocks list every page of the "Digital forensics" subgroup once the siblings exist, so the
    # check is on the hand-written text only: the marked blocks are cut out first.
    hand_written = re.sub(r"<!-- BEGIN GENERATED .*?<!-- END GENERATED [^>]*-->", "", body, flags=re.DOTALL)
    assert not re.search(r"\]\((?:[^)]*)(Memory|Network|Toolkits|Foundations)[^)]*Forensic", hand_written)


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in line and 'subgroup: "Digital forensics"' in line
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 4


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_addresses_no_em_dashes_no_callsign_style_placeholders_missing():
    body = text()
    assert not ADDR.findall(body)
    assert "—" not in body


def test_the_authorization_rule_is_stated_up_front():
    body = text()
    assert body.index("Examine only your own devices or data you are explicitly authorized to examine") < body.index("## What you will be able to do")
    assert "not legal advice" in body


def test_the_hash_step_comes_before_the_examination_commands():
    body = text()
    assert body.index("sha256sum lab.dd > lab.dd.sha256") < body.index("mmls lab.dd\n   fsstat")
    assert re.search(r"`[0-9a-f]{64}`|[0-9a-f]{64}  lab\.dd", body)


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 25, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n\nNot verified, plainly"
    assert rows_missing_status(bad) == ["X"]


def test_versions_and_licenses_are_dated():
    body = text()
    for needle in ("4.23.1", "4.15.0", "2026-05-07", "2026-04-15", "Apache License", "Common Public License", "October 2023"):
        assert needle in body, needle
