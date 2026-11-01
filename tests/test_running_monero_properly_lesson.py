# SPDX-License-Identifier: Apache-2.0
"""The running-Monero-properly lesson: registered, honest about what was run, diagrams intact, layout consistent, safe to read.

docs/wiki/Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md is page 5 of the
five-page cryptocurrency set (issue 400). A banner that claims more than was run (nothing here was installed or run),
a dead link, a missing registration, a diagram with no picture or alt text, a wallet qube that can reach the network in
the layout table, a walk-through step that crosses a boundary the layout does not allow, a hardware-wallet-in-Qubes
claim marked as documented when no document says it, a mention of the maintainer's work on PiNodeXMR, a key or address or
onion name on the page, price talk, or a register row with no URL and no date would each teach or reveal the wrong thing.
"""

import itertools
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR"
PAGE = WIKI / f"{NAME}.md"
PAGE_ONE = "Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks"
PAGE_TWO = "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable"
PAGE_THREE = "How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware"
PAGE_FOUR = "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
# A wallet address in any of the common shapes: legacy Bitcoin, Bech32 Bitcoin, Ethereum and Monero.
ADDRESS = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    r"|\bbc1[ac-hj-np-z02-9]{11,71}\b"
    r"|\b0x[0-9a-fA-F]{40}\b"
    r"|\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"
)
# Extended keys, wallet-import keys, the best-known public test phrases, and onion or I2P service names.
KEYSHAPE = re.compile(
    r"\b[xyztu](?:prv|pub)[1-9A-HJ-NP-Za-km-z]{20,}\b"
    r"|\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"
    r"|\babandon abandon\b|\bzoo zoo\b|\blegal winner thank\b"
)
SERVICE_NAME = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
LOOPBACK = {"127.0.0.1"}
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
HW = "## A hardware wallet with Monero"
DESIGN = "## The Qubes and Whonix design"
PATH = "## The transaction path"
PINODE = "## PiNodeXMR: why an always-on node"
EXERCISE = "## Free exercise: a paper walk-through of the transaction path"
LAYOUT = "### The layout"
CHANNEL = "### The channel between the wallet qube and the blockchain qube"
DOCUMENTED = "### What the documents say and what is my reading"
OWN_OR_REMOTE = "### Your own node or a remote node you trust"
SECURING = "### Securing the node"
BOUNDARIES = (
    "Internet to the network qube",
    "Gateway to the blockchain qube",
    "Blockchain qube to wallet qube",
    "USB qube to wallet qube",
    "Device screen",
    "Hypervisor and dom0",
    "The paper backup",
)


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def section(body: str, heading: str) -> str:
    """The text under a heading, up to the next heading of the same or a higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    rest = body.split(heading, 1)[1]
    return re.split(rf"\n#{{1,{level}}} ", rest)[0]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def sourced_rows_without_url_and_date(body: str) -> list[str]:
    """Rows that cite a page must carry a URL and the read date; framing and general-knowledge rows are exempt by name."""
    exempt = ("The maintainer's", "The author's own", "General knowledge", "This page's")
    bad = []
    for row in register_rows(body):
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def table_headers(body: str) -> list[list[str]]:
    """The header row of every table: a line starting with a pipe, followed by a separator row."""
    lines = body.splitlines()
    out = []
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and re.match(r"^\|[-| :]+\|$", lines[i + 1]):
            out.append([c.strip() for c in line.strip("|").split("|")])
    return out


def tables(body: str, heading: str) -> list[list[list[str]]]:
    """Tables in a section as lists of data rows (cells stripped)."""
    result, current = [], []
    for line in section(body, heading).splitlines() + [""]:
        if re.match(r"^\|[-| :]+\|$", line):
            continue
        if line.startswith("|"):
            current.append([c.strip() for c in line.strip("|").split("|")])
        elif current:
            result.append(current[1:])
            current = []
    return result


# ---- the layout and the walk-through as data ---------------------------------------------------------------------------


def parse_layout(rows: list[list[str]]) -> dict[str, dict[str, object]]:
    """Layout rows: qube, role, network (the qube it uses for network, or none or internet), holds, data channels."""
    layout = {}
    for row in rows:
        qube = row[0].strip("`")
        channels = {c.strip().strip("`") for c in re.split(r"[;,]", re.sub(r"\([^)]*\)", "", row[4])) if c.strip()}
        layout[qube] = {"netvm": row[2].strip("`").lower(), "holds": row[3], "channels": channels - {"none"}}
    return layout


def network_reachable(layout: dict[str, dict[str, object]]) -> set[str]:
    """Every qube that has a network path to the internet by following the network column upward."""
    reach = set()
    for qube in layout:
        seen, here = set(), qube
        while here in layout and here not in seen:
            seen.add(here)
            up = layout[here]["netvm"]
            if up == "internet":
                reach.add(qube)
                break
            if up == "none":
                break
            here = up
    return reach


def layout_problems(layout: dict[str, dict[str, object]]) -> list[str]:
    """The properties the design promises: the wallet and USB qubes have no network, and the wallet talks to exactly two qubes."""
    problems = []
    reach = network_reachable(layout)
    for offline in ("xmr-wallet", "sys-usb"):
        if offline not in layout:
            problems.append(f"{offline} is missing from the layout")
        elif offline in reach or layout[offline]["netvm"] != "none":
            problems.append(f"{offline} has a network path")
    if "xmr-wallet" in layout and layout["xmr-wallet"]["channels"] != {"sys-usb", "xmr-node"}:
        problems.append(f"xmr-wallet channels are {sorted(layout['xmr-wallet']['channels'])}")
    if "xmr-node" in layout and "xmr-node" not in reach:
        problems.append("xmr-node has no network path, so it cannot sync")
    if "xmr-node" in layout and layout["xmr-node"]["netvm"] != "sys-whonix":
        problems.append("xmr-node must reach the network only through sys-whonix")
    for name, info in layout.items():
        for peer in info["channels"]:
            if peer in layout and name not in layout[peer]["channels"]:
                problems.append(f"{name} lists {peer} but {peer} does not list {name}")
    return problems


def allowed_hops(layout: dict[str, dict[str, object]]) -> set[frozenset[str]]:
    """Hops a packet or a message may take: network links up the netvm chain, listed data channels, and the cable."""
    hops = set()
    for name, info in layout.items():
        up = info["netvm"]
        if up not in ("none",):
            hops.add(frozenset((name, up)))
        for peer in info["channels"]:
            hops.add(frozenset((name, peer)))
    hops.add(frozenset(("sys-usb", "device")))
    return hops


def walk_problems(steps: list[list[str]], layout: dict[str, dict[str, object]]) -> list[str]:
    """Every hop of every step must be an allowed hop; the wallet qube must never touch a network qube or the internet."""
    allowed = allowed_hops(layout)
    # The wallet qube may meet a networked qube only through its one declared channel, to the blockchain qube.
    forbidden = (network_reachable(layout) | {"internet"}) - set(layout["xmr-wallet"]["channels"])
    problems = []
    for step in steps:
        path = [p.strip().strip("`") for p in step[1].split(">")]
        for a, b in itertools.pairwise(path):
            if frozenset((a, b)) not in allowed:
                problems.append(f"step {step[0]}: {a} to {b} is not an allowed hop")
            if "xmr-wallet" in (a, b) and ({a, b} - {"xmr-wallet"}) & forbidden:
                problems.append(f"step {step[0]}: the wallet qube touches the network")
    return problems


def first_words(rows: list[list[str]]) -> set[str]:
    """The first word of every row's status cell (third column), without bold markers."""
    return {r[2].split()[0].strip("*") for r in rows}


def load_layout() -> dict[str, dict[str, object]]:
    return parse_layout(tables(text(), LAYOUT)[0])


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_documents_and_names_what_was_not_run():
    body = text()
    assert body.startswith("# Running Monero properly")
    assert "Status: unverified draft, written from reading" in body
    assert "I installed and ran no Qubes OS, no Whonix, no Monero software, no hardware wallet and no PiNodeXMR" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    low = body.lower()
    assert "the maintainer will run" in low and "correct" in low, "the page says he will run and correct it"
    assert "on his own machine" in low


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 14, "the guard collected too few links"
    missing = sorted({t for t, _ in found if not (WIKI / f"{t}.md").exists()})
    assert not missing, missing
    bad = []
    for target, anchor in found:
        if anchor and anchor not in headings((WIKI / f"{target}.md").read_text(encoding="utf-8")):
            bad.append(f"{target}#{anchor}")
    assert not bad, bad


def test_the_page_links_the_four_siblings_and_the_lessons_it_depends_on():
    body = text()
    links = {t for t, _ in LINK.findall(body)}
    for needed in (
        PAGE_ONE,
        PAGE_TWO,
        PAGE_THREE,
        PAGE_FOUR,
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "Patch-Management-and-Automatic-Security-Updates",
        "Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing",
        "DMZ-Hardening-Checklist",
        "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet",
        "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
    ):
        assert needed in links, needed
    assert "#what-pinodexmr-documents" in body, "the PiNodeXMR example on the overview page is linked"
    for issue in ("396", "397", "398", "399", "400", "372"):
        assert issue in body, f"issue {issue} is named"


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line, "the banner says unverified draft"
    assert "Page 5 of 5" in line


def test_glossary_rows_point_at_real_headings_and_no_term_is_defined_twice():
    heads = headings(text())
    anchors = set()
    rows = 0
    terms = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| **"):
            terms.append(line.split("**")[1].strip().lower())
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 8, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    # tests/test_glossary_terms.py bars every repeated term; this page must not add a second row for any term it defines.
    mine = [
        line.split("**")[1].strip().lower()
        for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| **") and f"{NAME}.md" in line
    ]
    assert len(mine) == rows
    duplicates = sorted({t for t in mine if terms.count(t) > 1})
    assert not duplicates, duplicates


def test_every_table_has_a_named_first_header_cell():
    heads = table_headers(text())
    assert len(heads) >= 10, "the guard collected too few tables"
    assert all(h[0] for h in heads), [h for h in heads if not h[0]]


def test_the_table_guard_bites():
    assert table_headers("| | b |\n|---|---|\n| 1 | 2 |\n") == [["", "b"]]
    assert table_headers("| a | b |\n|---|---|\n| 1 | 2 |\n") == [["a", "b"]]
    assert tables("## H\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\ntext\n", "## H") == [[["1", "2"], ["3", "4"]]]


def test_no_addresses_keys_phrases_onion_names_stray_hex_other_ip_addresses_em_dashes_or_money():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not KEYSHAPE.findall(body), KEYSHAPE.findall(body)
    assert not SERVICE_NAME.findall(body), SERVICE_NAME.findall(body)
    assert not HEX64.findall(body), "no 64-digit value at all, not even a published checksum"
    assert not (set(IPV4.findall(body)) - LOOPBACK), set(IPV4.findall(body)) - LOOPBACK
    assert "—" not in body
    assert "$" not in body and "usd" not in body.lower() and "dollar" not in body.lower(), "no money amounts at all"
    assert "password: " not in body.lower(), "a default password is described, never printed"
    assert "wallet" in body.lower(), "the guard collected nothing"


def test_the_secret_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the placeholder qubes are labels, not addresses")
    assert KEYSHAPE.search("the phrase abandon abandon abandon")
    assert SERVICE_NAME.search("connect to " + "a" * 16 + ".onion now")
    assert SERVICE_NAME.search("connect to " + "b" * 52 + ".b32.i2p now")
    assert not SERVICE_NAME.search("the word onion and the word i2p alone are fine")
    assert HEX64.search("sum " + "ab" * 32)
    assert IPV4.search("host 192.0.2.7") and set(IPV4.findall("use 127.0.0.1:18081")) <= LOOPBACK
    assert not IPV4.search("as of release 0.9.7.1") and not IPV4.search("version v0.18.3.3")


# ---- the layout, the walk-through and the threat table --------------------------------------------------------------


def test_the_layout_gives_the_wallet_and_usb_qubes_no_network_and_the_wallet_two_channels():
    layout = load_layout()
    assert {"sys-usb", "xmr-wallet", "xmr-node", "sys-whonix", "sys-net"} <= set(layout)
    assert not layout_problems(layout), layout_problems(layout)
    reach = network_reachable(layout)
    assert reach == {"xmr-node", "sys-whonix", "sys-net"}, reach


def test_the_layout_guard_bites():
    layout = load_layout()
    # Give the wallet qube a network and the guard must say so.
    online = {k: dict(v) for k, v in layout.items()}
    online["xmr-wallet"]["netvm"] = "sys-whonix"
    assert any("has a network path" in p for p in layout_problems(online))
    # Give the USB qube a network.
    usb = {k: dict(v) for k, v in layout.items()}
    usb["sys-usb"]["netvm"] = "sys-net"
    assert any("sys-usb has a network path" in p for p in layout_problems(usb))
    # A third channel on the wallet qube.
    wide = {k: dict(v) for k, v in layout.items()}
    wide["xmr-wallet"]["channels"] = set(wide["xmr-wallet"]["channels"]) | {"sys-whonix"}
    assert any("xmr-wallet channels" in p for p in layout_problems(wide))
    # A node that routes around the gateway.
    direct = {k: dict(v) for k, v in layout.items()}
    direct["xmr-node"]["netvm"] = "sys-net"
    assert any("only through sys-whonix" in p for p in layout_problems(direct))
    # A one-sided channel.
    lopsided = {k: dict(v) for k, v in layout.items()}
    lopsided["xmr-node"]["channels"] = set()
    assert any("does not list" in p for p in layout_problems(lopsided))
    # The parser reads names and the netvm column.
    sample = parse_layout([["`a`", "r", "`none`", "h", "`b` (x); `c`"], ["`b`", "r", "`internet`", "h", "`a`"]])
    assert sample["a"]["channels"] == {"b", "c"} and sample["b"]["netvm"] == "internet"
    assert network_reachable(sample) == {"b"}


def test_the_walk_through_only_uses_hops_the_layout_allows():
    body = text()
    layout = load_layout()
    steps = tables(body, EXERCISE)[0]
    assert len(steps) >= 10, "the guard collected too few steps"
    assert not walk_problems(steps, layout), walk_problems(steps, layout)
    joined = " ".join(s[1] for s in steps)
    for party in ("internet", "sys-net", "sys-whonix", "xmr-node", "xmr-wallet", "sys-usb", "device"):
        assert party in joined, party


def test_the_walk_through_guard_bites():
    layout = load_layout()
    assert walk_problems([["1", "xmr-wallet > xmr-node"]], layout) == []
    bad = walk_problems([["1", "xmr-wallet > sys-whonix"]], layout)
    assert any("not an allowed hop" in p for p in bad)
    assert any("touches the network" in p for p in walk_problems([["2", "xmr-wallet > internet"]], layout))
    assert walk_problems([["3", "device > sys-usb > xmr-wallet"]], layout) == []
    skipped = walk_problems([["4", "device > xmr-wallet"]], layout)
    assert any("not an allowed hop" in p for p in skipped), "the USB qube cannot be skipped"
    assert walk_problems([["5", "xmr-node > sys-whonix > sys-net > internet"]], layout) == []


def test_the_threat_table_covers_every_boundary_and_each_row_says_what_an_attacker_needs():
    rows = tables(text(), EXERCISE)[1]
    names = [r[0] for r in rows]
    for boundary in BOUNDARIES:
        assert boundary in names, boundary
    assert len(rows) == len(BOUNDARIES)
    for row in rows:
        assert len(row) == 5 and all(cell for cell in row), row
    needs = " ".join(r[2].lower() for r in rows)
    for needed in ("compromise", "usb", "confirm", "dom0", "paper"):
        assert needed in needs, needed


# ---- hardware wallet with Monero: what the documents say ----------------------------------------------------------------


def test_the_hardware_section_names_the_models_the_command_and_the_key_differences():
    part = section(text(), HW)
    for model in ("Safe 5", "Safe 3", "Model T", "Safe 7", "Model One"):
        assert model in part, model
    assert "--hw-device Trezor --generate-from-device" in part
    assert "hw_key_images_sync" in part and "restore height" in part.lower()
    assert "SLIP-0010" in part, "the Trezor derives Monero keys its own way"
    assert "Polyseed" in part and "Legacy" in part, "the current Monero seed documents, not the deprecated page"
    assert "deprecated" in part
    assert "watch-only credentials" in part, "what the device exports to the wallet"
    assert "Ledger" in part and "I read no end-user Ledger document" in part
    assert "Cake" in part, "the Safe 7 route is the vendor's, stated as the vendor's"


def test_the_page_states_what_the_source_code_says_about_file_signing_with_a_device():
    body = text()
    assert "sign_transfer" in body and "submit_transfer" in body
    assert "command not supported by HW wallet" in body
    assert "3fd0f88" in body, "the repository head the source was read at is recorded"
    part = section(body, CHANNEL)
    assert "RPC channel" in part and "File channel" in part
    assert "unsigned_monero_tx" in part and "signed_monero_tx" in part
    assert "NOT necessarily the recommended" in body, "the Monero project's own warning about general-purpose signing machines"


def test_the_qubes_parts_use_the_documents_exact_lines_and_say_which_are_old():
    body = text()
    assert "qubes.ConnectTCP +18081 monero-wallet-ws @default allow target=monerod-ws" in body
    assert "qvm-connect-tcp ::18081" in body
    assert "qvm-usb attach" in body
    assert "127.0.0.1:18081" in body
    assert "v0.18.3.3" in body and "2024-08-22" in body, "the Monero guide is dated and its version is old"
    assert "UNFINISHED" in body and "testers-only" in body, "the Whonix offline wallet page's own warnings"
    assert "COMMUNITY SUPPORT ONLY" in body
    assert "more trusted to less trusted" in body
    assert "block device" in body.lower(), "Qubes prefers a block device to USB passthrough"
    assert "USB qube" in section(body, "### The USB qube and why it matters")


def test_the_documented_versus_reading_table_never_calls_a_combination_documented():
    rows = tables(text(), DOCUMENTED)[0]
    assert len(rows) >= 8, "the guard collected too few rows"
    statuses = first_words(rows)
    assert statuses <= {"Documented", "Combined", "Maintainer's", "Not"}, statuses
    assert {"Documented", "Combined", "Maintainer's", "Not"} <= statuses
    for row in rows:
        first = row[0].lower()
        if "hardware wallet" in first and "qubes" in first:
            assert not row[2].startswith("Documented"), row
    assert any("hardware wallet" in r[0].lower() and "qubes" in r[0].lower() for r in rows)


def test_the_documented_table_guard_bites():
    rows = [["a", "b", "**Documented** here"], ["c", "d", "Combined by me"], ["hardware wallet in Qubes", "e", "Documented"]]
    assert first_words(rows) == {"Documented", "Combined"}
    assert first_words([["x", "y", "Documented, for a thing"]]) == {"Documented,"}, "a comma after the word is caught"
    combo = [r for r in rows if "hardware wallet" in r[0].lower() and "qubes" in r[0].lower()]
    assert combo and combo[0][2].startswith("Documented"), "the combination guard would see this row as wrongly documented"


# ---- PiNodeXMR ---------------------------------------------------------------------------------------------------------


def test_the_pinodexmr_section_reuses_the_overview_sources_re_dated_and_names_its_commits():
    body = text()
    part = section(body, PINODE)
    assert "c0c80f1" in body and "fb2a6d5" in body, "the repository and wiki commits are recorded"
    assert "2026-10-18" in body and "2025-05-20" in body
    for needed in ("full or pruned", "Tor", "I2P", "private node", "web interface", "Ubuntu Server"):
        assert needed.lower() in part.lower(), needed
    assert "#what-pinodexmr-documents" in part, "the overview page's section is linked"
    assert "my disk images require you to trust me" in body.lower()
    assert "--rpc-ssl disabled" in body and "--confirm-external-bind" in body
    assert "fail2ban" in body.lower()


def test_the_own_node_versus_remote_node_table_names_privacy_and_trust():
    rows = tables(text(), OWN_OR_REMOTE)[0]
    assert len(rows) >= 6, "the guard collected too few rows"
    flat = section(text(), OWN_OR_REMOTE).lower()
    for needed in ("your own node", "remote node", "ip address", "trusted", "tor", "fee", "decoy", "sync"):
        assert needed in flat, needed


def test_node_security_covers_patching_exposed_rpc_access_control_and_backup_with_links():
    part = section(text(), SECURING)
    for sub in ("#### Patching", "#### No exposed RPC", "#### Access control", "#### Backup"):
        assert sub in part, sub
    assert "Patch-Management-and-Automatic-Security-Updates.md" in part
    assert "Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md" in part
    assert "DMZ-Hardening-Checklist.md" in part and "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md" in part
    low = part.lower()
    for needed in ("never forward", "default", "plain http", "no seed", "restore", "static"):
        assert needed in low, needed


def test_the_maintainers_work_on_pinodexmr_is_not_mentioned_in_any_wording():
    low = text().lower()
    for banned in (
        "contribut",
        "pull request",
        "opened issues",
        "his fork",
        "commits attributed",
        "maintainer has run a monero node",
        "worked on pinodexmr",
        "helped build",
        "his patches",
        "authored",
    ):
        assert banned not in low, banned
    assert "pinodexmr" in low


# ---- diagrams ---------------------------------------------------------------------------------------------------------


def test_every_diagram_has_alt_text_a_source_and_a_picture_that_exists():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 4, "expected four diagrams"
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


def test_the_diagrams_cover_the_topics_the_issue_asks_for_and_use_the_layout_names():
    found = list(WRAPPED.finditer(text()))
    alts = " ".join(m["alt"].lower() for m in found)
    for topic in ("qubes", "unsigned", "pinodexmr", "hardware wallet"):
        assert topic in alts, topic
    sources = "\n".join(m["src"] for m in found)
    for name in ("sys-usb", "xmr-wallet", "xmr-node", "sys-whonix"):
        assert name in sources, name


# ---- the register -----------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 40, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date_and_the_expected_sources_are_there():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "cli_wallet_daemon_isolation_qubes_whonix.html",
        "offline-transaction-signing.md",
        "interacting/remote-nodes.md",
        "monero-wallet-cli-reference.md",
        "monerod-tori2p.md",
        "mnemonics/index.md",
        "mnemonics/legacy.md",
        "mnemonics/polyseed.md",
        "src/device_trezor/README.md",
        "src/simplewallet/simplewallet.cpp",
        "src/wallet/wallet2.cpp",
        "docs/ANONYMITY_NETWORKS.md",
        "user-guides/tor_wallet.html",
        "user-guides/ledger-wallet-cli.html",
        "trezor.io/coins/wallet/monero",
        "what-is-monero-and-how-does-it-work-with-trezor",
        "set-up-monero-cli-with-your-trezor",
        "set-up-monero-gui-with-your-trezor",
        "core/src/apps/monero/README.md",
        "LedgerHQ/app-monero",
        "usb-qubes.html",
        "how-to-use-usb-devices.html",
        "device-handling-security.html",
        "how-to-copy-and-move-files.html",
        "data-leaks.html",
        "security-in-qubes/firewall.html",
        "developer/services/qrexec.html",
        "qvm/sys-usb.sls",
        "whonix.org/wiki/Monero_Offline_Wallet",
        "whonix.org/wiki/Monero_Wallet_Isolation",
        "whonix.org/wiki/Monero",
        "whonix.org/wiki/Qubes",
        "whonix.org/wiki/I2P",
        "shermand100/PiNodeXMR/c0c80f105e4b806ccb7414d1aadf42a128378894/README.md",
        "wiki/shermand100/PiNodeXMR/Manual.md",
        "tor-Setup-&-Usage.md",
        "i2p-Setup-and-Use.md",
        "Use-of-IP-Ban-Lists.md",
        "nodeControl.html",
        "moneroPrivate.sh",
        "moneroTorPrivate.sh",
        "www.getmonero.org/downloads",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 40


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


def test_the_unverified_items_are_marked_in_the_register():
    rows = {r[0]: r for r in register_rows(text())}
    combo = next(r for k, r in rows.items() if k.startswith("A hardware wallet in the wallet qube"))
    assert "**est.**" in combo[2] and "unverified" in combo[2].lower()
    design = next(r for k, r in rows.items() if k.startswith("The maintainer's design"))
    assert "issue 400" in design[1].lower() or "issue 400" in design[0].lower()


# ---- scope and tone ---------------------------------------------------------------------------------------------------


def test_the_exercise_is_paper_only_and_links_the_hands_on_companion():
    part = section(text(), EXERCISE)
    assert "paper" in part.lower() and "nothing to install" in part.lower()
    assert "issue 372" in text() and "Qubes" in part
    assert "Not run" in text()
    assert len(tables(text(), EXERCISE)) == 2, "a walk-through table and a threat table"


def test_the_page_does_not_repeat_the_stance_and_has_no_price_talk_shilling_or_evasion_content():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "pump", "airdrop", "evade detection", "avoid law enforcement",
        "launder money", "hide your funds", "bypass kyc", "how to avoid being traced", "untraceable",
        "cryptobro", "mcafee", "to avoid tracing", "stay anonymous", "cover your tracks", "comfortable with cryptocurrency",
        "affiliate",
    ):
        assert banned not in body, banned
    assert body.count("price") <= 1 and body.count("trading") <= 1, "only the rule sentence itself uses these words"
    assert "no price talk, no coin shilling and no trading advice" in body
    assert "no how-to for anything illegal" in body


def test_old_and_unfinished_sources_are_dated_where_they_are_used():
    body = text()
    assert "2024-08-22" in body and "2026-10-14" in body, "the dates of the Monero guide and of the remote-nodes page"
    assert "2026-05-13" in body, "the anonymity networks document's last change"
    assert "v0.12.2.0" in body, "the Ledger CLI guide is from an old release"
    assert "no edit date" in body, "Trezor's pages carry no edit date and the page says so"
    assert "Whonix" in body and "oldid" in body, "the Whonix pages are dated by the revision read"
    assert "experimental" in body.lower(), "Whonix's and Monero's own word for I2P and for the combination"
