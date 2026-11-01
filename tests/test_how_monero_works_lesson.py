# SPDX-License-Identifier: Apache-2.0
"""The how-Monero-works lesson: registered, honest about what was run, diagrams intact, and safe to read.

docs/wiki/How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md is page 3 of the
five-page cryptocurrency set (issue 398, with the atomic swap scope added in its comment). A banner that claims more than
was run, a dead link, a missing registration, a diagram with no picture or alt text, a wallet address or a stray long hex
value, a side-by-side table whose numbers do not add up, a swap answer the protocol does not give, a documented case with
no date or source, price talk, advice for evading investigators, a repeated stance, or a register row with no URL and no
date would each teach or reveal the wrong thing.
"""

import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware"
PAGE = WIKI / f"{NAME}.md"
PAGE_ONE = "Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
# A wallet address in any of the common shapes: legacy Bitcoin, Bech32 Bitcoin, Ethereum and Monero.
ADDRESS = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    r"|\bbc1[ac-hj-np-z02-9]{11,71}\b"
    r"|\b0x[0-9a-fA-F]{40}\b"
    r"|\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"
)
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
ETH64 = re.compile(r"\b0x[0-9a-f]{64}\b")
# Onion and I2P hostnames are service addresses; none belongs on this page.
HIDDEN_SERVICE = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
# A dotted quad is an address unless it follows the word "release" (a four-part version).
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
DATE = "2026-11-01"
BTC_TIP, XMR_TIP, ETH_TIP = "974141", "3796941", "26320893"
# The only 64-digit hex values the page may carry: public block and transaction identifiers read on the day from a public
# explorer or node. Anything else is a stray value.
PUBLIC_HEX = {
    "0000000000000000000086d9b51ffbf1bae526f17fb57f0244f30b7eb2b34025",  # Bitcoin block 974131
    "36f35cd8817ac39cdb02dac118851d8eaf48184bab2de4721dcb6dcfbaa61dc7",  # the Bitcoin transaction read
    "c818aea630ce1ab717b304818c16d65cc83c3aaedaa2f2a59a90d6668ca3fa5c",  # the earlier transaction it spends from
    "806a1006c62dd385c0442bff5ab0787f96c7f7257b832b6e80b51c84908acefb",  # Monero block 3796930
    "5e01e7607f5e2384c1025abc4303160a88cfb9ee7b469f8a1a43a7892ac0b83b",  # the Monero transaction read
}
PUBLIC_ETH_HEX = {
    "0xef515d4dce219036a117930db96c0c57ac9f5124729fd4f27c78ae618c9e37a4",  # Ethereum block 26320880
    "0x31236a10706d8e977c6ea2d15fbd3473e53df1a2a4ae2e2c13675988db132ecf",  # the Ethereum transaction read
}
SIDE = "## A dated read: a Bitcoin and a Monero transaction side by side"
ETH = "## Ethereum: accounts, contracts, gas and what a trace looks like"
SWAP = "## Atomic swaps: exchanging coins across two chains with no middleman"
SWAP_EX = "## Free exercise: a swap timeline with a failed counterparty"
COMPARE_EX = "## Free exercise: compare a Bitcoin and a Monero transaction"


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def section(body: str, heading: str) -> str:
    return body.split(heading)[1].split("\n## ")[0]


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


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip().strip("`") for c in r.strip("|").split("|")] for r in rows]


def case_rows(body: str) -> list[list[str]]:
    """Every row of every table whose first header cell is Date: the documented cases, each needing a date and a source."""
    out = []
    block: list[str] = []
    for line in body.split("## Claims register")[0].splitlines() + [""]:
        if line.startswith("|"):
            block.append(line)
            continue
        if block:
            rows = table_rows("\n".join(block))
            if rows and rows[0][0] == "Date":
                out.extend(rows[1:])
            block = []
    return out


def cases_without_date_or_source(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not YEAR.search(r[0]) or not URL.search(r[-1])]


def side_by_side(body: str) -> dict[str, list[str]]:
    out = {}
    for row in table_rows(section(body, SIDE))[1:]:
        if len(row) == 3:
            out[row[0]] = row[1:]
    return out


def number(cell: str) -> int:
    return int(re.search(r"\d[\d,]*", cell).group(0).replace(",", ""))


def utc(unix: int) -> str:
    return datetime.datetime.fromtimestamp(unix, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")


# The two worked swap protocols, written out as code so the page's answers are computed, not trusted.
def htlc_outcome(bob_locks: bool, alice_claims_hour: int | None, bob_back_hour: int | None) -> str:
    """Alice holds the secret and her lock times out at hour 48; Bob's lock times out at hour 24."""
    if not bob_locks:
        return "ALICE_REFUND_48"
    if alice_claims_hour is None:
        return "BOTH_REFUND_BOB_24_ALICE_48"
    assert alice_claims_hour < 24, "Alice must claim on Bob's chain before Bob's refund hour"
    if bob_back_hour is not None and bob_back_hour < 48:
        return "COMPLETED"
    return "ALICE_KEEPS_BOTH"


def adaptor_outcome(
    alice_locks: bool, adaptor_sent: bool, alice_redeems_before_t1: bool, bob_refunds_within_t2: bool
) -> str:
    """The Bitcoin and Monero swap of Hoenisch and Soriano del Pino: Bob locks bitcoin first, Alice locks monero second."""
    if alice_redeems_before_t1:
        assert alice_locks and adaptor_sent, "Alice can only redeem with Bob's adaptor signature"
        return "COMPLETED"
    if bob_refunds_within_t2:
        return "BOTH_REFUND" if alice_locks else "BOB_REFUND"
    assert alice_locks, "this page does not set a case in which Alice punishes without having locked"
    return "ALICE_PUNISH"


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_executed():
    body = text()
    assert body.startswith("# How Monero works")
    assert "Status: unverified draft, written from reading" in body
    assert "**Not run:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    banner = body.split("## What you will be able to do")[0]
    for must in ("no wallet", "no swap", "no mixer"):
        assert must in banner.lower(), f"the banner should say {must}"


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 9, "the guard collected too few links"
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
        PAGE_ONE,
        "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig",
        "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR",
        "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Hashing-Encryption-and-Keys",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
    ):
        assert needed in links, needed
    assert "#what-pinodexmr-documents" in body, "the PiNodeXMR section of the overview lesson is linked"
    for issue in ("397", "399", "400", "372", "398"):
        assert issue in body, f"issue {issue} is named"
    assert all((WIKI / f"{t}.md").is_file() for t in links), "a linked page is missing"
    # The stale statement that page five is not on the main branch is gone.
    assert "is not on the main branch yet" not in body


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
    assert rows >= 14, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_stray_hex_hidden_service_names_ip_addresses_or_em_dashes():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not HIDDEN_SERVICE.findall(body), HIDDEN_SERVICE.findall(body)
    assert not IPV4.findall(body), IPV4.findall(body)
    assert "—" not in body
    found = set(HEX64.findall(body))
    assert found, "the guard collected no hash at all"
    assert found <= PUBLIC_HEX, sorted(found - PUBLIC_HEX)
    eth = set(ETH64.findall(body))
    assert eth == PUBLIC_ETH_HEX, sorted(eth ^ PUBLIC_ETH_HEX)


def test_the_address_and_hex_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the block hash 0000000000000000000086d9b51ffbf1bae526f17fb57f0244f30b7eb2b34025")
    assert HEX64.search("key " + "ab" * 32) and "ab" * 32 not in PUBLIC_HEX
    assert ETH64.search("tx 0x" + "ab" * 32) and "0x" + "ab" * 32 not in PUBLIC_ETH_HEX
    assert HIDDEN_SERVICE.search("host " + "a" * 56 + ".onion") and HIDDEN_SERVICE.search("host " + "b" * 52 + ".b32.i2p")
    assert not HIDDEN_SERVICE.search("the .onion suffix and Tor onion services")
    assert IPV4.search("host 192.0.2.7") and not IPV4.search("as of release 0.9.7.1")


def test_the_side_by_side_records_the_date_the_heights_and_prints_no_address():
    body = text()
    part = section(body, SIDE)
    assert DATE in part
    for tip in (BTC_TIP, XMR_TIP):
        assert tip in part, tip
    assert "blockstream.info" in part, "the Bitcoin explorer is named"
    assert "public remote node" in part, "the Monero node is described"
    assert "I print no address" in part
    assert "**Not run:**" in part or "Not run" in part


def test_the_side_by_side_numbers_add_up_and_the_times_match_their_unix_values():
    rows = side_by_side(text())
    for label in (
        "Chain height (tip) when read",
        "Block read",
        "Block hash",
        "Block time (UTC)",
        "Transaction id",
        "Inputs",
        "What the input names",
        "Outputs",
        "Amounts of the outputs",
        "Fee",
        "Who the outputs go to",
        "Size (bytes)",
    ):
        assert label in rows, label
    assert rows["Chain height (tip) when read"] == [BTC_TIP, XMR_TIP]
    assert rows["Block read"] == ["974131", "3796930"]
    for col in (0, 1):
        cell = rows["Block time (UTC)"][col]
        unix = int(re.search(r"\((\d{10})\)", cell).group(1))
        assert cell.startswith(utc(unix)), (cell, utc(unix))
    btc_in = number(rows["What the input names"][0].split("value")[1])
    outs = [number(x) for x in re.findall(r"\d[\d,]*", rows["Amounts of the outputs"][0].replace("satoshis", ""))]
    assert len(outs) == 2 and rows["Outputs"][0].startswith("2"), outs
    assert btc_in == sum(outs) + number(rows["Fee"][0]), (btc_in, outs, rows["Fee"][0])
    assert rows["Inputs"][1].startswith("1") and "ring of 16" in rows["Inputs"][1]
    assert rows["Outputs"][1].startswith("2")
    assert "0" in rows["Amounts of the outputs"][1] and "hidden" in rows["Amounts of the outputs"][1]
    assert "clear" in rows["Fee"][1] and "atomic units" in rows["Fee"][1]
    assert number(rows["Size (bytes)"][1]) > number(rows["Size (bytes)"][0]), "a Monero transaction carries more proof bytes"
    assert "no address" in rows["Who the outputs go to"][1].lower() or "one-time" in rows["Who the outputs go to"][1]


def test_the_side_by_side_guard_bites():
    good = utc(1793540783)
    assert good == "2026-11-01 13:46:23"
    assert not "2026-11-01 13:46:24 (1793540783)".startswith(good), "one second off must fail the time check"
    assert number("value 45,126,020 satoshis") == 45126020
    assert 45126020 != 12034 + 45111973 + 2014, "a fee that is one unit off must fail the sum"


def test_the_ethereum_read_records_the_date_the_height_and_the_missing_trace():
    body = text()
    part = section(body, ETH)
    assert DATE in part and ETH_TIP in part
    assert "26320880" in part and "1793547659" in part
    assert "2026-11-01 15:40:59" in part and utc(1793547659) == "2026-11-01 15:40:59"
    assert "debug_traceTransaction" in part
    assert "does not exist/is not available" in part, "the public node's own refusal is quoted"
    assert "I print no address" in part


def test_every_documented_case_has_a_date_and_a_source():
    rows = case_rows(text())
    assert len(rows) >= 14, f"the guard collected too few cases: {len(rows)}"
    assert not cases_without_date_or_source(rows), cases_without_date_or_source(rows)
    firsts = " ".join(r[0] for r in rows)
    for year in ("2016", "2020", "2022", "2023", "2025"):
        assert year in firsts, year


def test_the_case_guard_bites():
    assert cases_without_date_or_source([["June 2016", "x", "[s](https://example.com/a)"]]) == []
    assert cases_without_date_or_source([["last year", "x", "[s](https://example.com/a)"]]) == ["last year"]
    assert cases_without_date_or_source([["June 2016", "x", "a news story"]]) == ["June 2016"]
    sample = "| Date | What | Source |\n|---|---|---|\n| 2016 | x | [s](https://e.com/a) |\n\n| Other | y |\n|---|---|\n| z | q |\n"
    assert len(case_rows(sample + "## Claims register\n")) == 1


def test_the_swap_answers_are_the_ones_the_protocols_give():
    body = text()
    part = section(body, SWAP_EX)
    answers = part.split("Answers")[1]
    rows = {r[0]: r for r in table_rows(answers)[1:]}
    assert set(rows) == {"H1", "H2", "H3", "H4", "H5", "X1", "X2", "X3", "X4", "X5", "X6"}, sorted(rows)
    expected = {
        "H1": htlc_outcome(True, 10, 11),
        "H2": htlc_outcome(False, None, None),
        "H3": htlc_outcome(True, None, None),
        "H4": htlc_outcome(True, 23, 30),
        "H5": htlc_outcome(True, 23, 50),
        "X1": adaptor_outcome(True, True, True, False),
        "X2": adaptor_outcome(False, False, False, True),
        "X3": adaptor_outcome(True, False, False, True),
        "X4": adaptor_outcome(True, False, False, False),
        "X5": adaptor_outcome(True, True, True, False),
        "X6": adaptor_outcome(True, True, False, True),
    }
    for key, want in expected.items():
        assert rows[key][-1] == want, (key, rows[key][-1], want)
    assert "Not run" in part, "the exercise is marked as not run by a reader"


def test_the_swap_state_machines_bite():
    assert htlc_outcome(True, 23, 50) == "ALICE_KEEPS_BOTH", "a counterparty who is away past the long timeout loses"
    assert htlc_outcome(True, 23, 47) == "COMPLETED"
    try:
        htlc_outcome(True, 30, 31)
    except AssertionError:
        pass
    else:
        raise AssertionError("claiming after the shorter timeout is not allowed")
    assert adaptor_outcome(True, False, False, False) == "ALICE_PUNISH"
    assert adaptor_outcome(True, False, False, True) == "BOTH_REFUND"
    try:
        adaptor_outcome(False, False, False, False)
    except AssertionError:
        pass
    else:
        raise AssertionError("the unsupported case must be refused, not guessed")


def test_every_diagram_has_alt_text_a_source_and_a_picture_that_exists():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 8, "expected eight diagrams"
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


def test_the_diagrams_cover_the_topics_the_issue_asks_for():
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(text()))
    for topic in ("ring", "stealth", "hidden amounts", "dandelion", "trace", "timelock", "two chains", "privacy"):
        assert topic in alts, topic


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 40, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "Zero-to-Monero-2-0-0.pdf",
        "moneropedia/ringsignatures",
        "moneropedia/stealthaddress",
        "moneropedia/ringCT",
        "moneropedia/viewkey",
        "ANONYMITY_NETWORKS.md",
        "getmonero.org/resources/roadmap",
        "releases/tag/v0.18.0.0",
        "releases/tag/v0.16.0.0",
        "arxiv.org/abs/1805.11060",
        "arxiv.org/abs/1704.04299",
        "eprint.iacr.org/2017/338",
        "MRL-0010.pdf",
        "eprint.iacr.org/2020/1126",
        "arxiv.org/abs/2101.12332",
        "bip-0199",
        "bitcointalk.org/index.php?topic=193281",
        "xmr-btc-swap",
        "docs.unstoppableswap.net",
        "blockstream.info/api",
        "ethereum-rpc.publicnode.com",
        "ethereum.org/developers/docs/accounts",
        "ethereum.org/developers/docs/gas",
        "ethereum.org/developers/docs/smart-contracts",
        "ethereum.org/developers/docs/oracles",
        "ethereum.org/developers/docs/bridges",
        "ethereum.org/defi",
        "geth.ethereum.org/docs/developers/evm-tracing/built-in-tracers",
        "erc-20",
        "blog.ethereum.org/2016/06/17",
        "blog.ethereum.org/2016/07/20",
        "ic3.gov/PSA/2022/PSA220829",
        "ic3.gov/PSA/2025/PSA250226",
        "DeFi-Risk-Full-Review.pdf",
        "jy0768",
        "jy0916",
        "jy1933",
        "sb0057",
        "FinCEN",
        "912981",
        "cisa.gov/stopransomware/ransomware-guide",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 35


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


def test_the_stance_the_background_and_the_anecdote_are_left_to_page_one():
    body = text()
    for repeated in ("cryptobro", "McAfee", "CES 2016", "Every Key", "comfortable with cryptocurrency", "heading up security"):
        assert repeated not in body, f"{repeated!r} belongs on page one only"
    assert f"{PAGE_ONE}.md#the-stance-the-background-and-where-these-lessons-come-from" in body, "the stance is linked, not repeated"


def test_the_pinodexmr_project_is_named_but_no_contributions_are_claimed():
    body = text()
    assert "PiNodeXMR" in body
    for m in re.finditer(r"PiNodeXMR", body):
        near = body[max(0, m.start() - 300) : m.end() + 300].lower()
        assert "contribut" not in near, near
        assert "the maintainer's" not in near, near


def test_the_page_has_no_price_talk_shilling_or_evasion_content():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "airdrop", "evade detection", "avoid law enforcement", "avoid detection",
        "launder money", "launder your", "hide your funds", "bypass kyc", "trading volume", "volume of", "best coin",
        "recommend using", "we recommend monero", "how to mix", "how to cash out", "untraceable money",
    ):
        assert banned not in body, banned
    scrub = re.sub(r"price (?:oracle|feed|pairs|information)|prices? (?:of a|in a) ", "", body)
    assert scrub.count("price") <= 1, "price appears only as a named oracle input, and once at most elsewhere"
    assert scrub.count("trading") <= 1 and scrub.count("pump") == 0
    assert "no how-to" in body and "educational" in body


def test_the_page_says_what_it_does_and_does_not_claim_about_swaps_and_regulators():
    body = text()
    part = section(body, SWAP)
    for needed in (
        "no exchange",
        "hash time-locked",
        "adaptor signature",
        "discrete logarithm",
        "refund",
        "punish",
        "do not endorse",
        "no ranking",
    ):
        assert needed in part.lower().replace("hash time-locked contract", "hash time-locked"), needed
    assert "atomic" in part and "found no" in part.lower(), "the absence of a regulator statement is reported, not invented"
    assert "(inference)" in part or "my inference" in part.lower()


def test_both_free_exercises_are_marked_as_not_run():
    body = text()
    for heading in (COMPARE_EX, SWAP_EX):
        assert heading in body, heading
        assert "Not run" in section(body, heading), heading


def test_the_snapshot_and_register_date_old_sources():
    body = text()
    for needed in ("April 4, 2020", "December 4, 2018", "May 2, 2013", "May 7, 2013"):
        assert needed in body, needed
    assert "v2.0.0" in body, "the edition of Zero to Monero is named"
    assert "ring size" in body.lower() and "16" in body
    assert "2018" in body and "2017" in body, "the research papers are dated"
