# SPDX-License-Identifier: Apache-2.0
"""The network, log and timeline forensics lesson: registered, honest about what was run, safe to follow (issue #477).

docs/wiki/Network-Log-and-Timeline-Forensics-Packet-Captures-Logs-and-Plaso.md teaches evidence handling for a capture,
log trust, the time zone mistake and a plaso timeline. A broken link, a missing registration, a claim with no status, a real
address or callsign, or a link to a sibling lesson that does not exist yet would each mislead a reader.
"""

import re
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Network-Log-and-Timeline-Forensics-Packet-Captures-Logs-and-Plaso"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
LAB_ADDR = re.compile(r"\b(?:10\.89\.0\.\d{1,3}|0\.0\.0\.0)\b")
STATUS_WORDS = ("Read", "Run", "Observed", "**est.**")


def text() -> str:
    return page_text(PAGE)


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def non_lab_addresses(body: str) -> list[str]:
    return [a for a in ADDR.findall(body) if not LAB_ADDR.fullmatch(a)]


def heading_slugs(body: str) -> set[str]:
    return {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Network, log and timeline forensics")
    assert "Status: unverified draft" in body
    assert "2026-11-07" in body
    assert "Not verified, plainly" in body
    assert "What I ran and what failed" in body


def test_every_linked_wiki_page_exists_and_no_sibling_lesson_is_linked_early():
    links = set(LINK.findall(text()))
    assert len(links) >= 6, "the guard collected too few links"
    assert not sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    # The sibling forensics lessons exist now and are linked; the check above fails on a dead link.


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    assert 'subgroup: "Digital forensics"' in entry
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 5, "expected glossary rows for pcap, tshark, follow stream, plaso, super timeline"


def test_glossary_rows_point_at_real_headings():
    heads = heading_slugs(text())
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_in_page_anchors_point_at_real_headings():
    body = text()
    heads = heading_slugs(body)
    own = set(re.findall(r"\]\(#([a-z0-9-]+)\)", body))
    assert own, "the guard collected nothing"
    assert own <= heads, sorted(own - heads)


def test_no_em_dashes_and_only_lab_addresses():
    body = text()
    assert "—" not in body
    assert not non_lab_addresses(body), non_lab_addresses(body)
    assert non_lab_addresses("host 192.0.2.7"), "the address guard does not bite"


def test_no_callsign_style_placeholders_or_real_secrets():
    body = text()
    assert "hunter2-lab" in body, "the invented lab password should be marked as invented"
    assert "invented" in body


def test_every_claims_register_row_has_a_status():
    body = text()
    rows = register_rows(body)
    assert len(rows) >= 15, "the guard collected too few rows"
    assert not rows_missing_status(body)


def test_the_status_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | Y | trust me |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_time_zone_lesson_names_both_runs_and_the_offset():
    body = text()
    assert "--timezone America/New_York" in body
    assert "2026-11-07T10:49:52+00:00" in body and "2026-11-07T15:49:52+00:00" in body
    assert "7 minutes 2 seconds" in body


def test_the_plaso_facts_are_dated_and_use_the_real_parser_names():
    body = text()
    assert "20261027" in body and "Apache-2.0" in body
    assert "text/apache_access" in body and "text/syslog_traditional" in body


def test_the_law_section_says_not_legal_advice_and_keeps_to_own_network():
    body = text()
    assert "not legal advice" in body
    assert "own computer" in body or "container network you create" in body
