# SPDX-License-Identifier: Apache-2.0
"""The how-Bitcoin-works lesson: registered, honest about what was run, diagrams intact, and safe to read.

docs/wiki/How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md is page 2 of the five-page
cryptocurrency set (issue 397). A banner that claims more than was run, a dead link, a missing registration, a diagram with
no picture or alt text, a wallet address or a stray long hex value, a snapshot whose hash no longer matches its own header
fields, a worked answer that the heuristic does not give, price talk, advice for evading tracing, or a register row with no
URL and no date would each teach or reveal the wrong thing.
"""

import datetime
import hashlib
import json
import re
import struct
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable"
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
# A dotted quad is an address unless it follows the word "release" (a four-part version).
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
TIP = "974138"
# The only 64-digit hex values the page may carry: public block, Merkle and transaction identifiers read from a public
# explorer and named in the snapshot. Anything else is a stray value.
PUBLIC_HEX = {
    "00000000152340ca42227603908689183edc47355204e7aca59383b0aaac1fd8",  # block 57043 hash
    "0000000013e7e85518dac94d012d73253d3fdac5c30c4143b177f3086f129580",  # block 57042 hash (its previous block)
    "5c1d2211f598cd6498f42b269fe3ce4a6fdb40eaa638f86a0579c4e63a721b5a",  # block 57043 Merkle root
    "bd9075d78e65a98fb054cb33cf0ecf14e3e7f8b3150231df8680919a79ac8fe5",  # block 57043 reward transaction
    "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",  # the famous transaction
}
SNAP = "## A real snapshot: one famous public transaction"
EXERCISE = "## Free exercise: cluster a synthetic graph"


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
    exempt = ("The maintainer's framing", "The author's own", "General knowledge", "Constructed by the author")
    bad = []
    for row in register_rows(body):
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def snapshot(body: str) -> dict[str, str]:
    """The snapshot table as {row label: value}, with backticks removed."""
    out = {}
    for line in section(body, SNAP).splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            out[cells[0]] = cells[1]
    return out


def number(cell: str) -> int:
    return int(re.match(r"[\d,]+", cell).group(0).replace(",", ""))


def dsha(raw: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(raw).digest()).digest()


def header_hash(version: int, prev: str, merkle: str, when: int, bits: int, nonce: int) -> str:
    """Double SHA-256 of the 80-byte header, shown the way explorers show it (byte order reversed)."""
    raw = (
        struct.pack("<I", version)
        + bytes.fromhex(prev)[::-1]
        + bytes.fromhex(merkle)[::-1]
        + struct.pack("<III", when, bits, nonce)
    )
    assert len(raw) == 80
    return dsha(raw)[::-1].hex()


def merkle_of_two(a: str, b: str) -> str:
    return dsha(bytes.fromhex(a)[::-1] + bytes.fromhex(b)[::-1])[::-1].hex()


# ---- the synthetic graph in the exercise -------------------------------------------------------------------------


def exercise_rows(body: str) -> list[tuple[str, list[tuple[str, Decimal]], list[tuple[str, Decimal]], Decimal]]:
    rows = []
    for line in section(body, EXERCISE).splitlines():
        m = re.match(r"\| (T\d) \| ([^|]+) \| ([^|]+) \| ([\d.]+) \|", line)
        if m:
            pair = re.compile(r"([A-Z]\d) ([\d.]+)")
            ins = [(a, Decimal(v)) for a, v in pair.findall(m[2])]
            outs = [(a, Decimal(v)) for a, v in pair.findall(m[3])]
            rows.append((m[1], ins, outs, Decimal(m[4])))
    return rows


def seen_before(body: str) -> set[str]:
    m = re.search(r"\*\*Seen before T1:\*\* ([A-Z0-9, ]+)\.", section(body, EXERCISE))
    return {a.strip() for a in m[1].split(",")}


def common_input_clusters(rows) -> set[frozenset[str]]:
    """Union-find over the inputs of each transaction: addresses spent together are one cluster."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _tx, ins, _outs, _fee in rows:
        first = find(ins[0][0])
        for addr, _v in ins[1:]:
            parent[find(addr)] = first
    groups: dict[str, set[str]] = {}
    for a in list(parent):
        groups.setdefault(find(a), set()).add(a)
    return {frozenset(g) for g in groups.values()}


def change_labels(rows, seen: set[str]) -> dict[str, str]:
    """One-time change rule in the shape the research paper describes: exactly one output is new, none repeats an input."""
    seen = set(seen)
    out = {}
    for tx, ins, outs, _fee in rows:
        in_addrs = {a for a, _ in ins}
        seen |= in_addrs
        new = [a for a, _ in outs if a not in seen]
        if len(new) == 1 and not (in_addrs & {a for a, _ in outs}):
            out[tx] = new[0]
        seen |= {a for a, _ in outs}
    return out


def merged(clusters: set[frozenset[str]], change: dict[str, str], rows) -> set[frozenset[str]]:
    """Add each labeled change address to the cluster of its transaction's inputs."""
    result = [set(c) for c in clusters]
    for tx, ins, _outs, _fee in rows:
        if tx in change:
            for c in result:
                if ins[0][0] in c:
                    c.add(change[tx])
    return {frozenset(c) for c in result}


def answer_sets(body: str, label: str) -> set[frozenset[str]]:
    line = next(r for r in section(body, EXERCISE).splitlines() if r.startswith(f"| {label} |"))
    return {frozenset(s.strip() for s in grp.split(",")) for grp in re.findall(r"\{([^}]*)\}", line)}


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_run():
    body = text()
    assert body.startswith("# How Bitcoin works")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run on a blockchain network or a node" in body
    assert "**Not run:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 6, "the guard collected too few links"
    missing = sorted({t for t, _ in found if not (WIKI / f"{t}.md").exists()})
    assert not missing, missing
    bad = []
    for target, anchor in found:
        if anchor and anchor not in headings((WIKI / f"{target}.md").read_text(encoding="utf-8")):
            bad.append(f"{target}#{anchor}")
    assert not bad, bad


def test_the_page_links_the_existing_lessons_and_names_the_siblings_correctly():
    body = text()
    links = {t for t, _ in LINK.findall(body)}
    for needed in (
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Hashing-Encryption-and-Keys",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
    ):
        assert needed in links, needed
    assert "#digital-signatures" in body
    assert "#what-pinodexmr-documents" in body, "the PiNodeXMR example on the overview page is linked"
    # Page one is linked once it is in the wiki, and named in plain text until then.
    if (WIKI / f"{PAGE_ONE}.md").exists():
        assert PAGE_ONE in links, "page one exists, so it must be linked"
    else:
        assert PAGE_ONE not in body, "page one is not in the wiki yet; name it in plain text"
        assert "Blockchain fundamentals" in body and "issue 396" in body
    for issue in ("396", "398", "399", "400", "372"):
        assert issue in body, f"issue {issue} is named"
    # Pages three, four and five are in the wiki, so they are linked, and the stale statement is gone.
    for prefix in ("How-Monero-Works-", "Wallets-and-Key-Custody-", "Running-Monero-Properly-"):
        found = {t for t in links if t.startswith(prefix)}
        assert found, f"the page {prefix} exists and must be linked"
        assert all((WIKI / f"{t}.md").is_file() for t in found), found
    assert "Pages not in the wiki yet" not in body


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
    assert rows >= 12, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_stray_hex_ip_addresses_em_dashes_or_money_amounts():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not IPV4.findall(body), IPV4.findall(body)
    assert "—" not in body
    assert "$" not in body and "usd" not in body.lower() and "dollar" not in body.lower(), "no money amounts at all"
    found = set(HEX64.findall(body))
    assert found, "the guard collected no hash at all"
    assert found <= PUBLIC_HEX, sorted(found - PUBLIC_HEX)
    assert "bitcoin" in body.lower(), "the guard collected nothing"


def test_the_address_and_hex_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the placeholder addresses A1, A2 and C1 are labels, not addresses")
    assert HEX64.search("key " + "ab" * 32) and "ab" * 32 not in PUBLIC_HEX
    assert IPV4.search("host 192.0.2.7") and not IPV4.search("as of release 0.9.7.1")


def test_the_snapshot_records_the_date_the_height_and_the_tip_and_prints_no_address():
    part = section(text(), SNAP)
    assert DATE in part and TIP in part and "57043" in part
    assert "blockstream.info" in part, "the explorer is named"
    assert "I print no address" in part


def test_the_snapshot_hash_merkle_root_and_reward_match_their_own_fields():
    rows = snapshot(text())
    want = rows["Block hash"]
    got = header_hash(
        int(rows["Version"]),
        rows["Previous block hash"],
        rows["Merkle root"],
        int(rows["Time (Unix seconds)"]),
        int(rows["Difficulty bits (hex)"], 16),
        int(rows["Nonce"]),
    )
    assert got == want, (got, want)
    assert rows["Transactions in block"] == "2"
    assert merkle_of_two(rows["Reward transaction id"], rows["Transaction id"]) == rows["Merkle root"]
    when = int(rows["Time (Unix seconds)"])
    utc = datetime.datetime.fromtimestamp(when, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    assert rows["Time (UTC)"].startswith(utc), (rows["Time (UTC)"], utc)
    subsidy, fee = number(rows["Block subsidy at that height (satoshis)"]), number(rows["Fee (satoshis)"])
    assert subsidy == 5_000_000_000 == 50 * 100_000_000
    assert number(rows["Reward transaction output (satoshis)"]) == subsidy + fee, "reward = subsidy + the one fee"
    assert number(rows["Input value, all inputs (satoshis)"]) == number(rows["Output value (satoshis)"]) + fee
    assert number(rows["Inputs"]) == 131 and rows["Outputs"].startswith("1")
    assert rows["Distinct addresses among the inputs"].startswith("1"), "all inputs were paid to one address"
    height = number(rows["Block height"])
    assert number(rows["Confirmations when read"]) == int(TIP) - height + 1


def test_the_snapshot_guard_bites():
    good = (
        "00000000152340ca42227603908689183edc47355204e7aca59383b0aaac1fd8",
        "0000000013e7e85518dac94d012d73253d3fdac5c30c4143b177f3086f129580",
        "5c1d2211f598cd6498f42b269fe3ce4a6fdb40eaa638f86a0579c4e63a721b5a",
    )
    assert header_hash(1, good[1], good[2], 1274552191, 0x1C159C24, 188133155) == good[0]
    assert header_hash(1, good[1], good[2], 1274552191, 0x1C159C24, 188133156) != good[0], "one nonce digit changes it"
    assert merkle_of_two(
        "bd9075d78e65a98fb054cb33cf0ecf14e3e7f8b3150231df8680919a79ac8fe5",
        "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
    ) == good[2]
    assert merkle_of_two(
        "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
        "bd9075d78e65a98fb054cb33cf0ecf14e3e7f8b3150231df8680919a79ac8fe5",
    ) != good[2], "order matters"


def test_the_halving_and_difficulty_arithmetic_on_the_page_is_right():
    body = text()
    assert "210,000" in body and "2,016" in body
    tip = int(TIP)
    halvings = tip // 210_000
    assert halvings == 4
    assert Decimal(50) / (2**halvings) == Decimal("3.125")
    assert "3.125" in body, "the subsidy at the recorded tip, from the rule, is stated"
    assert 2016 * 600 == 1_209_600


def test_the_synthetic_exercise_has_the_shape_the_answer_key_depends_on():
    body = text()
    rows = exercise_rows(body)
    assert len(rows) == 4, "the guard collected too few transactions"
    for tx, ins, outs, fee in rows:
        assert sum(v for _, v in ins) == sum(v for _, v in outs) + fee, f"{tx} does not balance"
    names = {a for _, ins, outs, _ in rows for a, _ in ins + outs}
    assert all(re.fullmatch(r"[A-Z]\d", n) for n in names), "placeholder labels only"
    assert not ADDRESS.findall(section(body, EXERCISE))
    assert "synthetic" in section(body, EXERCISE).lower() and "no chain data" in section(body, EXERCISE).lower()


def test_the_answer_key_is_what_the_two_rules_actually_give():
    body = text()
    rows = exercise_rows(body)
    seen = seen_before(body)
    clusters = common_input_clusters(rows)
    multi = {c for c in clusters if len(c) > 1}
    assert answer_sets(body, "Common-input rule") == multi
    change = change_labels(rows, seen)
    assert change == {"T1": "C1", "T2": "C2"}, change
    assert answer_sets(body, "After the change rule") == {c for c in merged(clusters, change, rows) if len(c) > 1}
    section_text = section(body, EXERCISE)
    for must in ("not proved", "equal", "tag", "ambiguous"):
        assert must in section_text.lower(), must


def test_the_exercise_guard_bites():
    rows = [
        ("T1", [("A1", Decimal(1)), ("A2", Decimal(1))], [("B1", Decimal(2))], Decimal(0)),
        ("T2", [("C1", Decimal(1))], [("D1", Decimal(1))], Decimal(0)),
    ]
    assert common_input_clusters(rows) == {frozenset({"A1", "A2"}), frozenset({"C1"})}, "unrelated inputs stay apart"
    chained = rows + [("T3", [("A2", Decimal(1)), ("E1", Decimal(1))], [("F1", Decimal(2))], Decimal(0))]
    assert frozenset({"A1", "A2", "E1"}) in common_input_clusters(chained), "the effect is transitive"
    wrong = {frozenset({"A1", "A2"})}
    assert wrong != {c for c in common_input_clusters(chained) if len(c) > 1}, "a wrong key would be caught"
    two_new = [("T1", [("A1", Decimal(1))], [("B1", Decimal("0.5")), ("B2", Decimal("0.5"))], Decimal(0))]
    assert change_labels(two_new, set()) == {}, "two new outputs: ambiguous, so nothing is labeled"
    self_change = [("T1", [("A1", Decimal(1))], [("A1", Decimal("0.5")), ("B2", Decimal("0.5"))], Decimal(0))]
    assert change_labels(self_change, set()) == {}, "an output that repeats an input is skipped"


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


def test_the_diagrams_cover_the_topics_the_issue_asks_for():
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(text()))
    for topic in ("utxo", "keys", "cluster", "traced", "peeling"):
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
        "developer.bitcoin.org/devguide/transactions.html",
        "developer.bitcoin.org/devguide/block_chain.html",
        "developer.bitcoin.org/devguide/mining.html",
        "developer.bitcoin.org/devguide/p2p_network.html",
        "developer.bitcoin.org/devguide/wallets.html",
        "en.bitcoin.it/wiki/Controlled_supply",
        "chainparams.cpp",
        "imc13.pdf",
        "arxiv.org/abs/1107.4524",
        "arxiv.org/abs/1804.04080",
        "justice.gov/opa/pr/department-justice-seizes-23-million",
        "bitcointalk.org/index.php?topic=137.0",
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


def test_every_documented_case_has_a_date_a_source_and_the_limit_it_shows():
    part = section(text(), "## Documented cases: what tracing showed")
    rows = [
        [c.strip() for c in line.strip("|").split("|")]
        for line in part.splitlines()
        if line.startswith("|") and not line.startswith("|---")
    ][1:]
    assert len(rows) >= 4, "the guard collected too few cases"
    for row in rows:
        assert re.search(r"20\d\d", row[1]), f"no date: {row[0]}"
        assert URL.search(row[2]) or "register" in row[2].lower(), f"no source: {row[0]}"
        assert len(row[3]) > 40, f"no statement of what it shows: {row[0]}"
    for needed in ("2021-06-07", "April 11 2012", "March 15 2013", "number 21-528"):
        assert needed in part or needed.replace(" ", " ") in text(), needed


def test_the_traced_cases_use_no_personal_addresses_and_say_what_was_not_read():
    body = text()
    not_verified = section(body, "## Not verified, plainly")
    for unread in ("affidavit", "Nick", "tracking ransomware end-to-end"):
        assert unread.lower() in not_verified.lower(), unread
    assert "63.7" in body and "approximately 75" in body, "the case figures are in bitcoin, as the release gives them"


def test_the_page_does_not_repeat_the_stance_and_has_no_price_talk_shilling_or_evasion_content():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "pump", "airdrop", "evade detection", "avoid law enforcement",
        "launder money", "hide your funds", "bypass kyc", "how to avoid being traced", "untraceable",
        "cryptobro", "mcafee", "to avoid tracing", "stay anonymous", "cover your tracks",
    ):
        assert banned not in body, banned
    assert body.count("price") <= 1 and body.count("trading") <= 1, "named once as out of scope, nothing more"
    assert "no how-to for anything illegal" in body
    assert "no advice for avoiding tracing" in body or "no advice for evading tracing" in body


def test_the_page_says_what_an_analyst_cannot_conclude():
    body = text()
    part = section(body, "## What an analyst can and cannot conclude")
    for needed in ("can say", "cannot say"):
        assert needed in part.lower(), needed
    assert "## Pseudonymous is not anonymous" in body
    assert "## What a ransom payment leaves behind" in body
    exercise = section(body, EXERCISE)
    assert "Not run" in exercise


def test_old_pages_are_dated_where_they_are_used():
    body = text()
    assert "2009-2020" in body, "the developer guide's own copyright range is stated"
    assert "2008" in body, "the whitepaper's year is stated"
    assert "last edited on 15 April 2026" in body, "the wiki page's own edit date is stated"
    assert "Wayback" in body or "web.archive.org" in body, "the way the press release was read is stated"
