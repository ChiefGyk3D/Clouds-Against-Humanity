# SPDX-License-Identifier: Apache-2.0
"""The privacy-versus-security lesson: its citations exist, it is registered and honest about what was read.

docs/wiki/Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md has no script. It quotes the Monero
project, the European Commission, NIST and two lockpicking-hobby pages, and it gives lockpicking rules. A missing
registration, a source with no date, a real address, a wallet address, a lockpicking how-to or an overclaim about
what Monero can defeat would each teach the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# A Monero standard address is 95 base58 characters starting with 4 or 8.
XMR_ADDR = re.compile(r"\b[48][1-9A-HJ-NP-Za-km-z]{94}\b")
PATH_TOKEN = re.compile(r"`((?:modules|stacks|scripts|\.github|\.spacelift|tests)/[A-Za-z0-9_./-]+|\.gitignore)`")
STATUS_WORDS = ("Read", "Not read", "Not claimed", "**est.**", "Nothing run")
HOWTO_WORDS = ("tension wrench", "raking", "single pin picking", "how to pick", "bump key how", "shim a")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def section(body: str, start: str, end: str) -> str:
    return body.split(start)[1].split(end)[0]


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def rows_missing_date(rows: list[list[str]]) -> list[str]:
    """A row that points at a URL must carry the read date, or say it was not read."""
    return [r[0] for r in rows if "http" in r[1] and "2026-10-31" not in r[-1] and "Not read" not in r[-1]]


def howto_hits(body: str) -> list[str]:
    low = body.lower()
    return [w for w in HOWTO_WORDS if w in low]


def test_the_banner_says_what_was_and_was_not_read():
    body = text()
    assert body.startswith("# Privacy versus security")
    assert "Status: unverified draft" in body
    assert "**Not read:**" in body and "**Not run:**" in body and "2026-10-31" in body
    assert "Nothing here is legal advice" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 10, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_cited_repository_paths_exist():
    for p in PATH_TOKEN.findall(text()):
        assert (ROOT / p).exists(), p


def test_the_path_guard_bites():
    assert PATH_TOKEN.findall("see `scripts/does_not_exist.py`") == ["scripts/does_not_exist.py"]
    assert not (ROOT / "scripts/does_not_exist.py").exists()


def test_the_blast_radius_lesson_is_not_linked_so_its_link_cap_holds():
    # tests/test_blast_radius_lesson.py caps how many pages may link that lesson, and the cap is full.
    assert "Plan-for-Failure-Blast-Radius" not in text()


def test_the_sibling_lessons_are_named_by_issue_and_not_linked():
    body = text()
    assert "issues 358 and 360" in body and "not merged yet" in body
    assert not re.search(r"\]\((?:Tor|I2P|Cryptography)[A-Za-z0-9_-]*\.md", body)


def test_the_lesson_is_registered_in_contents_and_reading_order_but_not_the_sidebar():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    assert "sidebar" not in entry
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    assert NAME not in (WIKI / "_Sidebar.md").read_text(encoding="utf-8")


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 6, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_wallet_addresses_or_em_dashes():
    body = text()
    assert not ADDR.findall(body)
    assert not XMR_ADDR.findall(body)
    assert "—" not in body


def test_the_address_guards_bite():
    assert ADDR.findall("ping 192.0.2.7")
    assert XMR_ADDR.findall("4" + "A" * 94)


def test_the_picture_overlaps_and_tensions_are_present():
    body = text()
    assert "Privacy is the blinds and drapes" in body and "Security is the locks" in body
    over = section(body, "## Where they overlap", "## Where they pull apart")
    for item in ("Encryption", "Access control", "Data minimization"):
        assert item in over, item
    apart = section(body, "## Where they pull apart", "## Monero")
    for item in ("A lock with no blind", "A blind with no lock", "Anonymity against accountability"):
        assert item in apart, item


def test_monero_is_sourced_from_the_project_and_makes_no_overclaim():
    body = text()
    monero = section(body, "## Monero: a worked example", "## Privacy law basics")
    assert monero.count("https://www.getmonero.org/") >= 6
    assert "makes no claim about what Monero can or cannot defeat" in monero
    for prop in ("Key custody", "The view key", "Node trust", "Wallet and device security", "Software integrity"):
        assert prop in monero, prop
    for banned in ("untraceable by", "cannot be broken", "impossible to trace", "guarantees anonymity"):
        assert banned not in body.lower(), banned


def test_privacy_law_is_high_level_dated_and_not_advice():
    law = section(text(), "## Privacy law basics", "## The physical side")
    for needle in ("Not legal advice", "Check your own jurisdiction", "Purpose limitation", "Data minimization", "Storage limitation", "integrity and confidentiality"):
        assert needle in law, needle
    assert "2026-10-31" in law and "commission.europa.eu" in law


def test_every_physical_control_names_its_nist_control_and_a_privacy_cost():
    phys = section(text(), "## The physical side of security", "### Secure disposal")
    rows = table_rows("| Control idea" + section(phys, "| Control idea", "Two observations"))
    names = [r[0] for r in rows]
    for want in ("Locks and key control", "Doors and access control", "Tailgating", "Alarms", "Cameras", "Visitors", "Secure disposal", "Clean desk"):
        assert any(want in n for n in names), want
    assert len(rows) >= 9, "the guard collected too few rows"
    assert all(len(r) == 4 and r[2] and r[3] for r in rows)
    for control in ("PE-3(8)", "PE-6(1)", "PE-6(3)", "PE-8", "MP-6"):
        assert control in phys, control


def test_disposal_names_the_current_edition_and_the_withdrawn_one():
    disposal = section(text(), "### Secure disposal", "## Why lockpicking")
    assert "Rev. 2" in disposal and "withdrawn on September 26, 2025" in disposal
    for m in ("clear", "purge", "destroy"):
        assert m in disposal


def test_lockpicking_puts_the_rules_first_and_gives_no_how_to():
    pick = section(text(), "## Why lockpicking is a common hobby in the field", "## Free exercise")
    first_rules = pick.index("The rules come before anything else")
    assert first_rules < pick.index("What the hobby teaches defenders")
    for needle in ("Only locks you own", "Check your local law", "no step-by-step technique", "no bypass guide"):
        assert needle in pick, needle
    assert "toool.us" in pick and "2026-10-31" in pick
    assert not howto_hits(text())


def test_the_how_to_guard_bites():
    assert howto_hits("Use a tension wrench and raking motions")
    assert not howto_hits("Never pick a lock you do not own")


def test_the_exercise_has_a_table_to_fill_and_a_checklist():
    ex = section(text(), "## Free exercise", "## Checkpoint")
    header = next(line for line in ex.splitlines() if line.startswith("| Item"))
    assert header.count("|") >= 8 and "Blind, lock or both" in header
    blank = [line for line in ex.splitlines() if re.fullmatch(r"(\| *)+\|", line)]
    assert len(blank) >= 5, "the table needs empty rows to fill in"
    assert ex.count("- [ ]") >= 8
    for cell in ("Predict first", "**Check.**", "**Undo.**"):
        assert cell in ex, cell


def test_the_page_has_no_script():
    assert not re.search(r"^```(?:bash|sh|python|powershell)", text(), re.MULTILINE)


def test_every_claims_register_row_has_a_status_and_a_date():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(rows), rows_missing_status(rows)
    assert not rows_missing_date(rows), rows_missing_date(rows)
    assert any("getmonero.org" in r[1] for r in rows) and any("toool.us" in r[1] for r in rows)
    assert any("Not read" in r[-1] for r in rows), "the register must admit what was not read"


def test_the_register_guards_bite():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]
    assert rows_missing_date([["X", "https://example.org/a", "Read sometime"]]) == ["X"]
    assert not rows_missing_date([["X", "https://example.org/a", "Not read"]])
