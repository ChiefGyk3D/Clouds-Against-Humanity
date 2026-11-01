# SPDX-License-Identifier: Apache-2.0
"""The Tor, I2P and darknet lesson: registered, honest about what was run, and safe to read.

docs/wiki/Tor-I2P-and-the-Darknet-Without-the-Myths.md teaches two anonymity networks and four tools, and uses a
Monero node as its worked example. A banner that claims more than was run, a dead link, a missing registration,
a real address, a claim with no status, or text about a security review beyond its bare existence would each teach
or reveal the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Tor-I2P-and-the-Darknet-Without-the-Myths"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
STATUS_WORDS = ("Read", "Observed", "General knowledge", "**est.**")
AUDIT_WORDS = re.compile(r"\b(audit|vulnerab|CVE|finding|exploit|severity|weakness)", re.IGNORECASE)


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("## Maintainer notes to add")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# Tor, I2P and the darknet without the myths")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and "2026-10-31" in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    sidebar_line = next(l for l in nav.splitlines() if f"page: {NAME}," in l)
    assert "sidebar: true" not in sidebar_line, "the sidebar is a short opt-in list"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 7, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_onion_names_or_em_dashes():
    body = text()
    found = set(ADDR.findall(body))
    assert found <= {"127.0.0.1"}, found
    assert "127.0.0.1" in found, "the guard collected nothing"
    assert not ONION.findall(body)
    assert "—" not in body


def test_the_address_guard_bites():
    assert set(ADDR.findall("host 192.0.2.7")) != {"127.0.0.1"}
    assert ONION.findall("go to " + "a" * 56 + ".onion")


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n\n## Maintainer notes to add\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_sources_are_cited_with_urls_and_a_date():
    reg = text().split("## Claims register")[1]
    for host in ("support.torproject.org", "community.torproject.org", "geti2p.net", "tails.net", "whonix.org",
                 "qubes-os.org", "getmonero.org", "raw.githubusercontent.com/monero-project",
                 "github.com/shermand100/PiNodeXMR"):
        assert host in reg, host
    assert reg.count("2026-10-31") >= 20


def test_the_maintainer_notes_block_exists_and_is_last():
    body = text()
    assert "## Maintainer notes to add" in body
    tail = body.split("## Maintainer notes to add")[1]
    assert "\n## " not in tail
    assert len(re.findall(r"^\d+\. ", tail, re.MULTILINE)) >= 5


def test_the_security_review_is_mentioned_only_by_existence():
    body = text()
    contrib = body.split("### The maintainer's contributions, from public history only")[1].split("### Where privacy")[0]
    assert "security review" in contrib
    sentence = next(s for s in re.split(r"(?<=\.)\s+", contrib) if "security review" in s)
    assert not AUDIT_WORDS.search(sentence), sentence
    # no audit detail anywhere else about PiNodeXMR
    for line in body.splitlines():
        if "PiNodeXMR" in line and "security review" not in line:
            assert not re.search(r"\b(audit|vulnerab|CVE|severity)", line, re.IGNORECASE), line


def test_the_audit_guard_bites():
    assert AUDIT_WORDS.search("The audit found a weakness")
    assert not AUDIT_WORDS.search("One body of recent work is a security review.")


def test_the_page_makes_no_marketplace_or_how_to_commit_crime_content():
    body = text().lower()
    assert "no marketplace walkthroughs" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "escrow"):
        assert banned not in body


def test_the_law_paragraph_tells_learners_to_check_their_jurisdiction():
    law = text().split("## The law in one paragraph")[1].split("## Exercises")[0]
    assert "Check your own jurisdiction" in law
    assert "nothing here is legal advice" in law.lower()


def test_the_sibling_lessons_are_named_in_plain_text_not_linked():
    body = text()
    assert "privacy versus security" in body and "cryptography" in body
    assert "issues 359 and 360" in body
