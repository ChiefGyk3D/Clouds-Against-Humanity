# SPDX-License-Identifier: Apache-2.0
"""The darknet landscape lesson: registered, honest about what was read, and safe to read.

docs/wiki/The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md tells the documented history of
darknet markets, uses public cases as an OPSEC case study and compares layering Tor, I2P and a VPN. A banner that
claims more than was read, a dead link, a missing registration, an onion or I2P address, how-to wording for the
trades it describes, a number with no date or a claims row with no URL would each teach or reveal the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
URL = re.compile(r"\]\(https://[^)\s]+\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# An onion v2 (16) or v3 (56) host name, or an I2P base32 host name; the Tor lesson's guard, plus a long-name catch-all.
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
LONG_HOST = re.compile(r"\b[a-z0-9]{40,}\b", re.IGNORECASE)
READ_DATE = "2026-11-01"
STATUS_WORDS = ("Read", "Secondary", "General knowledge", "**est.**")
# How-to wording for buying, selling or evading: phrases that would turn a history into a guide.
HOWTO = re.compile(
    r"\bhow\s+(?:do\s+(?:i|you)\s+|to\s+|can\s+(?:i|you)\s+)(?:buy|sell|order|vend|launder|cash\s+out|ship|evade|avoid\s+(?:detection|police|investigators))\b"
    r"|\bstep[- ]by[- ]step\b.{0,40}\b(?:market|vendor|buyer|order)\b"
    r"|\b(?:best|top|safest|working|trusted)\s+(?:darknet|dark\s*web)\s+(?:market|markets|vendor|vendors|site|sites)\b"
    r"|\bbecome\s+a\s+vendor\b|\bvendor\s+(?:guide|setup)\b|\bbuyer\s+guide\b",
    re.IGNORECASE,
)


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def web_rows_missing_url_or_date(body: str) -> list[str]:
    """Every row not about this wiki, the issue or general knowledge needs a URL and a read date."""
    bad = []
    for r in register_rows(body):
        if "General knowledge" in r[-1] or "issue 381" in r[1] or "issue 423" in r[1] or "(this wiki)" in r[1]:
            continue
        if not URL.search(r[1]) or READ_DATE not in r[-1]:
            bad.append(r[0])
    return bad


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# The darknet landscape")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and READ_DATE in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_neighbors_are_named():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in ("Tor-I2P-and-the-Darknet-Without-the-Myths", "Threat-Model",
                   "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
                   "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys"):
        assert needed in links, needed


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    sidebar_line = next(line for line in nav.splitlines() if f"page: {NAME}," in line)
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
    assert rows >= 4, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_onion_or_i2p_address_no_ip_address_and_no_em_dash():
    body = text()
    assert ".onion" in body, "the guard collected nothing: the page names the .onion suffix when it explains Onion-Location"
    assert not ONION.findall(body)
    assert not ADDR.findall(body)
    assert "—" not in body
    # a long random-looking host or token would trip the repository secret scan; links are the only long strings
    prose = URL.sub("", body)
    assert not LONG_HOST.findall(re.sub(r"\([^)]*\)", "", prose))


def test_the_address_guard_bites():
    fake_onion = "go to " + "a" * 56 + "." + "onion"
    fake_i2p = "go to " + "b" * 52 + "." + "b32.i2p"
    assert ONION.findall(fake_onion) and ONION.findall(fake_i2p)
    assert ADDR.findall("host 192.0.2.7")
    assert LONG_HOST.findall("token " + "x9" * 25)


def test_the_page_has_no_how_to_wording_for_the_trades_it_describes():
    body = text()
    assert len(body.splitlines()) > 100, "the guard collected too little text"
    hits = [m.group(0) for m in HOWTO.finditer(body)]
    assert not hits, hits
    assert "no marketplace walkthroughs" in body.lower()
    assert "does not teach anyone to buy or sell" in body


def test_the_how_to_guard_bites():
    # built at run time so this file never contains the phrases it forbids
    opener, verb, noun, extra = "how", "buy", "market", "detection"
    bad = [
        f"{opener} to {verb} from a {noun}",
        f"{opener} do you {'sell'} there",
        f"{opener} to avoid {extra}",
        f"the best darknet {noun} today",
        f"become a {'vendor'}",
        f"step-by-step guide to a first {noun} order",
    ]
    for sentence in bad:
        assert HOWTO.search(sentence), sentence
    assert not HOWTO.search("The market sold goods and the court described how the site was run.")


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_web_row_has_a_url_and_the_read_date():
    body = text()
    rows = register_rows(body)
    web = [r for r in rows if URL.search(r[1])]
    assert len(web) >= 18, "the guard collected too few sourced rows"
    assert not web_rows_missing_url_or_date(body)
    sources = " ".join(r[1] for r in web)
    for host in ("justice.gov", "fbi.gov", "europol.europa.eu", "wired.com", "usenix.org", "theverge.com",
                 "law.justia.com", "support.torproject.org", "tails.net", "whonix.org", "geti2p.net",
                 "community.torproject.org", "en.wikipedia.org"):
        assert host in sources, host


def test_the_register_guards_bite():
    no_status = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(no_status) == ["X"]
    no_url = ("## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n"
              "| Y | a page with no link | Read 2026-11-01 |\n")
    assert web_rows_missing_url_or_date(no_url) == ["Y"]
    no_date = ("## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n"
               "| Z | [p](https://example.org/p) | Read earlier |\n")
    assert web_rows_missing_url_or_date(no_date) == ["Z"]


BIBLE_HEADING = "## The Darknet Market Bible and what kind of document it is"
# Names of markets and directories that the Bible section has no reason to print.
BIBLE_FORBIDDEN_NAMES = ("Silk Road", "AlphaBay", "Hansa", "Incognito", "DarkMarket", "Hydra", "Evolution",
                         "Wall Street", "dark.fail", "Hidden Wiki")
BIBLE_OVERREACH = re.compile(
    r"\b(?:read|reviewed|studied)\b[^.\n]{0,40}\b(?:whole|full|entire|every|all\s+(?:of\s+)?(?:its|the))\b",
    re.IGNORECASE,
)


def bible_section(body: str) -> str:
    """The Bible section up to its first subsection (the principles subsection is judged elsewhere)."""
    return body.split(BIBLE_HEADING)[1].split("\n## ")[0].split("\n### ")[0]


def bible_section_problems(section: str) -> list[str]:
    """What is wrong with the Bible section: it must say plainly what was read and reproduce nothing operational."""
    problems = []
    for needle in ("Introduction page only", "2024-12-29", "certificate", "I read no other page",
                   "does not summarize its procedures", "archival", "unsourced beyond"):
        if needle not in section:
            problems.append(f"missing: {needle}")
    if "Dread" not in section or "no address" not in section:
        problems.append("Dread must be named as a kind of forum, with no address")
    if BIBLE_OVERREACH.search(section):
        problems.append("claims to have read more than the Introduction")
    if re.search(r"https?://|\]\(", section) or ".onion" in section or ADDR.search(section):
        problems.append("link or address in the section")
    problems.extend(f"name: {n}" for n in BIBLE_FORBIDDEN_NAMES if n in section)
    return problems


def test_the_darknet_market_bible_is_described_from_its_introduction_only():
    body = text()
    section = bible_section(body)
    assert len(section.splitlines()) >= 5, "the guard collected too little text"
    assert not bible_section_problems(section), bible_section_problems(section)
    assert "did not read the document itself" not in body
    rows = {r[0]: r for r in register_rows(body)}
    kind = next(r for k, r in rows.items() if "Darknet Market Bible" in k and "issue 381" in r[1])
    assert "**est.**" in kind[2]
    intro = next(r for k, r in rows.items() if "Introduction" in k and "issue 423" in r[1])
    assert "2024-12-29" in intro[1] and "Internet Archive" in intro[1] and "plain text" in intro[1]
    assert not URL.search(intro[1]), "the Introduction is cited in plain text, not linked"
    assert "Read 2026-11-01" in intro[2] and "Introduction page only" in intro[2]
    circulated = next(r for k, r in rows.items() if "circulated" in k and "issue 423" in r[1])
    assert "Unsourced" in circulated[2] and "maintainer" in circulated[1]


def test_the_bible_guard_bites():
    good = bible_section(text())
    assert not bible_section_problems(good)
    assert bible_section_problems(good.replace("Introduction page only", "whole document"))
    assert bible_section_problems(good + "\nI read the entire guide.")
    assert bible_section_problems(good + "\nI read all of its pages.")
    assert bible_section_problems(good + "\nSee [it](https://example.org/x).")
    assert bible_section_problems(good + "\nIt lists AlphaBay.")
    assert bible_section_problems(good + "\nHost " + "192.0.2.7")
    assert bible_section_problems(good.replace("2024-12-29", "some day"))
    assert bible_section_problems(good.replace("Dread", "a forum"))


def test_the_four_principles_and_the_trap_are_present_and_threat_model_comes_first():
    body = text()
    for principle in ("**Threat modeling**", "**Compartmentalization**", "**Metadata**", "**Reuse of identities**"):
        assert principle in body, principle
    trap = body.split("## The OPSEC trap")[1].split("\n## ")[0]
    assert "**Threat model first.**" in trap
    assert trap.index("**Threat model first.**") < trap.index("Then check your habits")


def test_the_layering_section_ends_with_it_depends_on_the_threat_model_and_covers_each_combination():
    layering = text().split("## Layering Tor, I2P and a VPN")[1].split("\n## ")[0]
    for combo in ("**Tor alone**", "**VPN, then Tor**", "**Tor, then VPN**", "**VPN without Tor**",
                  "**Tor and I2P, each for its own purpose**"):
        assert combo in layering, combo
    assert "it depends on the threat model" in layering.lower()


def test_the_law_paragraph_tells_learners_to_check_their_jurisdiction():
    law = text().split("## The law in general terms")[1].split("\n## ")[0]
    assert "Check your own jurisdiction" in law
    assert "nothing here is legal advice" in law.lower()


def test_dated_history_covers_the_named_cases():
    history = text().split("## The documented history, in dates")[1].split("\n### ")[0]
    for needle in ("2013-10-01", "2015-02-04", "2017-07-05", "2017-07-20", "2017-06-20", "2021-01-12", "2024-03"):
        assert needle in history, needle
    for case in ("Silk Road", "AlphaBay", "Hansa", "DarkMarket", "Incognito"):
        assert case in history, case


def test_no_service_address_is_printed_for_legitimate_services_either():
    body = text()
    section = body.split("### How to find the official address of a legitimate service")[1].split("\n### ")[0]
    assert "from the HTTPS site you already reached" in section or "HTTPS site you already reached" in section
    assert "prints no onion address" in section
    assert not re.search(r"https?://[^\s)]*\.onion", body)
