# SPDX-License-Identifier: Apache-2.0
"""The "how I2P works" lesson: registered, honest about what was run, diagrams intact, and safe to read.

docs/wiki/How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md is page 3 of the Tor, I2P and VPN series.
A banner that claims more than was run, a dead link, a missing registration, a diagram with no picture or no alt text,
an onion or I2P address, or a register row with no URL and no date would each teach or reveal the wrong thing.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
# An onion or I2P address: a long base-32 label, or any name under .onion, .b32.i2p or .i2p.
ADDRESS = re.compile(r"\b[a-z2-7]{16,60}\.(?:onion|b32\.i2p)\b|\.b32\.i2p\b|\b[a-z0-9][a-z0-9-]*\.i2p\b|\.onion\b")
# A dotted quad is an address unless it follows the word "release" (a four-part version such as release 0.9.7.1).
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "General knowledge", "**est.**")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def sourced_rows_without_url_and_date(body: str) -> list[str]:
    """Rows that cite a page must carry a URL and the read date; process and framing rows are exempt by name."""
    exempt = ("The maintainer's framing", "The author's own check", "General knowledge")
    bad = []
    for row in register_rows(body):
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# How I2P works")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and DATE in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_page_links_the_overview_and_sibling_lessons():
    links = set(LINK.findall(text()))
    for needed in (
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
    ):
        assert needed in links, needed


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(l for l in nav.splitlines() if f"page: {NAME}," in l)
    assert 'status: "draft"' in line, "the banner says unverified draft"


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


def test_no_addresses_onion_or_i2p_names_or_em_dashes():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not IPV4.findall(body), IPV4.findall(body)
    assert "—" not in body
    assert "tunnel" in body.lower(), "the guard collected nothing"


def test_the_address_guard_bites():
    assert ADDRESS.search("go to " + "a" * 52 + ".b32.i2p")
    assert ADDRESS.search("go to " + "a" * 56 + ".onion")
    assert ADDRESS.search("visit example.i2p today")
    assert IPV4.search("host 192.0.2.7") and not IPV4.search("as of release 0.9.7.1")
    assert not ADDRESS.search("the `.i2p` suffix and the i2p.net site")


def test_every_diagram_has_alt_text_a_source_and_a_picture_that_exists():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 6, "expected six diagrams"
    assert len(re.findall(r"```mermaid", body)) == len(found), "a Mermaid block has no picture above it"
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    for m in found:
        alt = m["alt"].strip()
        assert 20 <= len(alt) <= 150, alt
        assert alt.lower() not in {"diagram", "image", "picture"}, alt
        png = (PAGE.parent / m["path"]).resolve()
        assert png.is_file(), m["path"]
        assert png.relative_to(ROOT).as_posix() in manifest, m["path"]
        assert m["src"].lstrip().startswith(("flowchart", "sequenceDiagram")), m["path"]


def test_the_diagram_guard_bites():
    bare = "![alt text here](images/x.png)\n\nno details block, so no source\n"
    assert not WRAPPED.search(bare)
    good = "![alt text here](images/x.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n  a --> b\n```\n\n</details>"
    assert WRAPPED.search(good)
    assert not WRAPPED.search(good.replace("<details>\n", ""))


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in ("i2p.net/en/docs/overview/intro", "i2p.net/en/docs/overview/tunnel-routing",
                 "i2p.net/en/docs/overview/garlic-routing", "i2p.net/en/docs/overview/network-database",
                 "i2p.net/en/docs/overview/peer-selection", "i2p.net/en/docs/overview/threat-model",
                 "i2p.net/en/docs/overview/comparison", "i2p.net/en/papers", "arxiv.org/abs/1809.09086",
                 "monero-project/monero/master/docs/ANONYMITY_NETWORKS.md", "docs.getmonero.org",
                 "community.torproject.org/onion-services/overview"):
        assert host in reg, host
    assert reg.count(DATE) >= 15


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


def test_old_pages_are_dated_where_they_are_used():
    body = text()
    assert "updated in 2010" in body or "last updated in **2010-11**" in body
    assert "accurate for 0.8.1" in body or "accurate for release 0.8.1" in body
    assert "ElGamal/AES" in body and "ECIES-X25519-AEAD-Ratchet" in body


def test_the_page_makes_no_how_to_or_evasion_content():
    body = text().lower()
    assert "no how-to for anything illegal" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "escrow", "bypass a block", "evade detection"):
        assert banned not in body


def test_the_law_pointer_and_series_message_are_present():
    body = text()
    assert "Check the law where you live" in body and "Nothing here is legal advice" in body
    assert "no silver bullet" in body
    assert "Privacy is who can see in" in body and "who can tell it is you" in body
