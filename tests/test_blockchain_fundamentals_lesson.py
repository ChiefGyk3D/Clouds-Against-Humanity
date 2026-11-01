# SPDX-License-Identifier: Apache-2.0
"""The blockchain fundamentals lesson: registered, honest about what was run, diagrams intact, and safe to read.

docs/wiki/Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md is page 1 of the five-page
cryptocurrency set (issue 396). A banner that claims more than was run, a dead link, a missing registration, a diagram with
no picture or alt text, a wallet address or a stray long hex value, a snapshot table whose hash no longer matches its own
header fields, price talk, or a register row with no URL and no date would each teach or reveal the wrong thing.
"""

import datetime
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
# A wallet address in any of the common shapes: legacy Bitcoin, Bech32 Bitcoin, Ethereum and Monero.
ADDRESS = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    r"|\bbc1[ac-hj-np-z02-9]{11,71}\b"
    r"|\b0x[0-9a-fA-F]{40}\b"
    r"|\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"
)
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
# A dotted quad is an address unless it follows the word "release" (a four-part version).
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
TIP = "974136"
# The only 64-digit hex values the page may carry: public block hashes, Merkle roots and transaction ids that were read
# from a public explorer and are named in the snapshot and the exercise. Anything else is a stray value.
PUBLIC_HEX = {
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",  # block 0 hash
    "00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048",  # block 1 hash
    "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",  # block 0 Merkle root and transaction id
    "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",  # block 1 Merkle root and transaction id
    "00000000d1145790a8694403d4063f323d499e655c83426834d4ce2f8dd4a2ee",  # block 170 hash
    "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",  # the block 170 transfer
    "0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9",  # the earlier output it spends
}


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


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


def snapshot(body: str) -> dict[str, list[str]]:
    """The snapshot table as {row label: [block 0 cell, block 1 cell]}, with backticks removed."""
    part = body.split("## A real snapshot: the first two Bitcoin blocks")[1].split("\n## ")[0]
    out = {}
    for line in part.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            out[cells[0]] = cells[1:]
    return out


def header_hash(version: int, prev: str, merkle: str, when: int, bits: int, nonce: int) -> str:
    """Double SHA-256 of the 80-byte header, shown the way explorers show it (byte order reversed)."""
    raw = (
        struct.pack("<I", version)
        + bytes.fromhex(prev)[::-1]
        + bytes.fromhex(merkle)[::-1]
        + struct.pack("<III", when, bits, nonce)
    )
    assert len(raw) == 80
    return hashlib.sha256(hashlib.sha256(raw).digest()).digest()[::-1].hex()


def test_the_banner_says_it_was_written_from_reading_and_names_the_one_calculation():
    body = text()
    assert body.startswith("# Blockchain fundamentals")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run on a blockchain network or a node" in body
    assert "**Not run:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "Defensive and educational" in body or "defensive and educational" in body


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 8, "the guard collected too few links"
    missing = sorted({t for t, _ in found if not (WIKI / f"{t}.md").exists()})
    assert not missing, missing
    bad = []
    for target, anchor in found:
        if anchor and anchor not in headings((WIKI / f"{target}.md").read_text(encoding="utf-8")):
            bad.append(f"{target}#{anchor}")
    assert not bad, bad


def test_the_page_links_the_existing_lessons_and_the_set_siblings_now_that_they_exist():
    body = text()
    links = {t for t, _ in LINK.findall(body)}
    for needed in (
        "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable",
        "How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware",
        "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig",
        "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Hashing-Encryption-and-Keys",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
    ):
        assert needed in links, needed
    assert "#what-pinodexmr-documents" in body, "the PiNodeXMR example on the overview page is linked"
    for issue in ("397", "398", "399", "400", "372"):
        assert issue in body, f"issue {issue} is named"
    assert all((WIKI / f"{t}.md").is_file() for t in links), "a linked page is missing"
    # The stale statement that the set pages are not written yet is gone.
    assert "Pages that are not written yet" not in body


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line, "the banner says unverified draft"


def test_glossary_rows_point_at_real_headings():
    heads = headings(text())
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 10, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_stray_hex_ip_addresses_or_em_dashes():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not IPV4.findall(body), IPV4.findall(body)
    assert "—" not in body
    found = set(HEX64.findall(body))
    assert found, "the guard collected no hash at all"
    assert found <= PUBLIC_HEX, sorted(found - PUBLIC_HEX)
    assert "blockchain" in body.lower(), "the guard collected nothing"


def test_the_address_and_hex_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the block hash 000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")
    assert HEX64.search("key " + "ab" * 32) and "ab" * 32 not in PUBLIC_HEX
    assert IPV4.search("host 192.0.2.7") and not IPV4.search("as of release 0.9.7.1")


def test_the_snapshot_records_the_date_and_the_height_and_prints_no_address():
    body = text()
    assert TIP in body, "the chain height at the time of the read is recorded"
    part = body.split("## A real snapshot: the first two Bitcoin blocks")[1].split("\n## ")[0]
    assert DATE in part and TIP in part
    assert "blockstream.info" in part, "the explorer is named"
    assert "I print no address" in part


def test_the_snapshot_hashes_match_their_own_header_fields():
    rows = snapshot(text())
    prev0 = rows["Previous block hash"][0]
    zero = "0" * 64 if prev0.startswith("none") else prev0
    for col, prev in ((0, zero), (1, rows["Previous block hash"][1])):
        want = rows["Block hash"][col]
        got = header_hash(
            int(rows["Version"][col]),
            prev,
            rows["Merkle root"][col],
            int(rows["Time (Unix seconds)"][col]),
            int(rows["Difficulty bits (hex)"][col], 16),
            int(rows["Nonce"][col]),
        )
        assert got == want, (col, got, want)
    assert rows["Previous block hash"][1] == rows["Block hash"][0], "block 1 must point at block 0"
    for col in (0, 1):
        assert rows["Transactions"][col] == "1"
        assert rows["Transaction id"][col] == rows["Merkle root"][col], "one transaction: the root is its id"
        when = int(rows["Time (Unix seconds)"][col])
        utc = datetime.datetime.fromtimestamp(when, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
        assert rows["Time (UTC)"][col].startswith(utc), (rows["Time (UTC)"][col], utc)
    assert rows["Height"] == ["0", "1"]


def test_the_snapshot_guard_bites():
    good = (
        "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
    )
    assert header_hash(1, "0" * 64, good[1], 1231006505, 0x1D00FFFF, 2083236893) == good[0]
    assert header_hash(1, "0" * 64, good[1], 1231006505, 0x1D00FFFF, 2083236894) != good[0], "one nonce digit changes it"


def test_every_diagram_has_alt_text_a_source_and_a_picture_that_exists():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 5, "expected five diagrams"
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


def test_the_diagrams_cover_the_four_topics_the_issue_asks_for():
    body = text()
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(body))
    for topic in ("chain of blocks", "life of a transaction", "gossip", "fork"):
        assert topic in alts, topic


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "bitcoin.org/bitcoin.pdf",
        "developer.bitcoin.org/devguide/block_chain.html",
        "developer.bitcoin.org/devguide/p2p_network.html",
        "developer.bitcoin.org/devguide/mining.html",
        "bitcoin.org/en/full-node",
        "NIST.IR.8202",
        "bip-0050",
        "ethereum.org/developers/docs/consensus-mechanisms",
        "ethereum.org/developers/docs/nodes-and-clients",
        "arxiv.org/abs/1311.0243",
        "blockstream.info/api",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 15


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


def test_the_stance_the_background_and_the_anecdote_are_stated_once_and_plainly():
    body = text()
    assert "uses and is comfortable with cryptocurrency" in body
    assert "not everyone is" in body
    stance = body.split("## The stance, the background and where these lessons come from")[1].split("\n## ")[0]
    assert body.count("cryptobro") == stance.count("cryptobro") == 2, "said in the stance section only, not repeated"
    assert "heading up security and IT for cryptocurrency companies" in body
    assert "around 2009 to 2010" in body
    assert "CES 2016" in body and "Every Key" in body
    assert "John McAfee" in body and "his account" in body
    assert body.count("McAfee") == 1, "no other claim about that person"


def test_the_page_has_no_price_talk_shilling_or_evasion_content():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "pump", "airdrop", "evade detection", "avoid law enforcement",
        "launder money", "hide your funds", "bypass kyc",
    ):
        assert banned not in body, banned
    assert body.count("price") <= 1 and body.count("trading") <= 1, "named once as out of scope, nothing more"
    assert "no how-to for anything illegal" in body


def test_the_page_says_what_a_blockchain_is_not_and_marks_the_exercise_as_not_run():
    body = text()
    assert "## What a blockchain is not" in body
    assert "## Free exercise: follow one famous transaction" in body
    for needed in ("not a database you can edit", "not automatically anonymous", "not automatically secure"):
        assert needed in body.lower(), needed
    exercise = body.split("## Free exercise: follow one famous transaction")[1].split("\n## ")[0]
    assert "Not run" in exercise


def test_old_pages_are_dated_where_they_are_used():
    body = text()
    assert "2009-2020" in body or "2009 to 2020" in body, "the developer guide's own copyright range is stated"
    assert "NIST.IR.8202" in body and "October 2018" in body
    assert "light sync" in body.lower(), "the Ethereum page's own caveat on light sync is reported"
