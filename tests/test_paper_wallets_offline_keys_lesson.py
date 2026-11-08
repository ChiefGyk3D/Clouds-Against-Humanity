# SPDX-License-Identifier: Apache-2.0
"""The paper wallets and offline key generation lesson: registered, honest about what was run, safe to read.

docs/wiki/Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero.md is an addition to the
cryptocurrency set (issue 431). A banner that claims more than was run, a command that is not labeled as run or not
run, a real-looking seed phrase, key, address or long hex value, a procedure that generates before the network is
cut, a generator ranked or endorsed, a dated claim with no date, a diagram with no picture or alt text, a table with
an unnamed first header cell, or a register row with no URL and no date would each teach or reveal the wrong thing.
The page is read through tests/wikitext.py page_text(), which strips the generated blocks (the navigation blocks exist only in the published page, issue #521).
"""

import itertools
import json
import re
from pathlib import Path

from test_wiki_page_nav import published
from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero"
PAGE = WIKI / f"{NAME}.md"
WALLETS = "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig"
RUNNING = "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
ADDRESS = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    r"|\bbc1[ac-hj-np-z02-9]{11,71}\b"
    r"|\b0x[0-9a-fA-F]{40}\b"
    r"|\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"
)
KEYSHAPE = re.compile(
    r"\b[xyztu](?:prv|pub)[1-9A-HJ-NP-Za-km-z]{20,}\b"
    r"|\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"
    r"|\babandon abandon\b|\bzoo zoo\b|\blegal winner thank\b|\bmilk sad wage\b"
)
SERVICE_NAME = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
LONG_HEX = re.compile(r"\b[0-9a-fA-F]{32,}\b")
LONG_BASE64 = re.compile(r"\b[A-Za-z0-9+/]{44,}={0,2}")
PHRASE_LINE = re.compile(r"^(?:[a-z]{3,8} ){11,}[a-z]{3,8}$")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
FENCE = re.compile(r"^```(\w*)\n(.*?)^```", re.DOTALL | re.MULTILINE)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
REASONS = "### The documented reasons"
DISAGREE = "## Where the sources disagree"
TOOLS = "### Tools named as examples"
PROCEDURE = "### The procedure"
QUBES = "### How this differs from the Qubes offline-wallet design"
EXERCISE = "## Free exercise: an offline-generation checklist for a stated threat model"
ORDER = ("download", "verify", "transfer", "cut", "boot", "generate", "record", "derive", "wipe", "fund", "restore", "spend")
MACHINES = {"connected", "media", "offline", "second"}


def text() -> str:
    return page_text(PAGE)


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def section(body: str, heading: str) -> str:
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
    exempt = ("The maintainer's", "The author's own", "General knowledge", "This page's")
    return [
        row[0]
        for row in register_rows(body)
        if not row[1].startswith(exempt) and (not URL.search(row[1]) or DATE not in row[2])
    ]


def table_headers(body: str) -> list[list[str]]:
    lines = body.splitlines()
    return [
        [c.strip() for c in line.strip("|").split("|")]
        for i, line in enumerate(lines[:-1])
        if line.startswith("|") and re.match(r"^\|[-| :]+\|$", lines[i + 1])
    ]


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


def code_blocks(body: str) -> list[tuple[str, str, str]]:
    """Every fenced block that is not Mermaid: (the nearest non-empty line above it, language, content)."""
    out = []
    for m in FENCE.finditer(body):
        if m.group(1) == "mermaid":
            continue
        above = [ln for ln in body[: m.start()].splitlines() if ln.strip()]
        out.append((above[-1] if above else "", m.group(1), m.group(2)))
    return out


def unlabeled_blocks(body: str) -> list[str]:
    """Blocks whose lead-in line does not say NOT RUN or RUN on the date."""
    return [b[2][:40] for b in code_blocks(body) if not (b[0].startswith("NOT RUN") or b[0].startswith(f"RUN on {DATE}"))]


def phrase_lines(body: str) -> list[str]:
    return [ln for _, _, content in code_blocks(body) for ln in content.splitlines() if PHRASE_LINE.match(ln.strip())]


def procedure_problems(rows: list[list[str]]) -> list[str]:
    """Row cells: number, kind, machine, network, what happens. The order and the network rules the page promises."""
    problems, seen = [], {}
    for row in rows:
        _, kind, machine, network = row[0], row[1], row[2], row[3]
        seen.setdefault(kind, row[0])
        if kind not in ORDER:
            problems.append(f"unknown kind {kind}")
        if machine not in MACHINES:
            problems.append(f"unknown machine {machine}")
        if machine in ("offline", "second") and network != "off":
            problems.append(f"step {row[0]}: {machine} machine with the network {network}")
        if machine == "media" and network != "n/a":
            problems.append(f"step {row[0]}: media have no network column")
    kinds = [r[1] for r in rows]
    for a, b in itertools.pairwise(ORDER):
        if a in kinds and b in kinds and kinds.index(a) > kinds.index(b):
            problems.append(f"{a} comes after {b}")
    for needed in ("verify", "cut", "generate", "record", "derive", "restore", "wipe"):
        if needed not in kinds:
            problems.append(f"no {needed} step")
    if "cut" in kinds and "generate" in kinds:
        cut = kinds.index("cut")
        for i, row in enumerate(rows):
            if i > cut and row[2] == "connected" and row[1] not in ("fund", "spend"):
                problems.append(f"step {row[0]}: a connected machine after the cut")
    return problems


# ---- the page ---------------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_documents_and_names_what_was_run_and_not_run():
    body = text()
    assert body.startswith("# Paper wallets and offline key generation")
    assert "Status: unverified draft, written from reading" in body
    assert "**Run:**" in body and "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "throwaway" in body.lower()
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    assert "no real recovery phrase, key or wallet address" in body.lower()
    assert "no price talk, no coin shilling and no trading advice" in body.lower()


def test_the_page_file_carries_no_navigation_block_and_the_published_page_does():
    raw = PAGE.read_text(encoding="utf-8")
    assert "BEGIN GENERATED PAGE NAV" not in raw  # issue #521: the publish step writes them
    shown = published(PAGE.stem)
    assert shown.count("BEGIN GENERATED PAGE NAV top") == 1 and shown.count("BEGIN GENERATED PAGE NAV bottom") == 1
    assert "BEGIN GENERATED" not in text()


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 10, "the guard collected too few links"
    missing = sorted({t for t, _ in found if not (WIKI / f"{t}.md").exists()})
    assert not missing, missing
    bad = [
        f"{target}#{anchor}"
        for target, anchor in found
        if anchor and anchor not in headings((WIKI / f"{target}.md").read_text(encoding="utf-8"))
    ]
    assert not bad, bad


def test_the_page_links_the_pages_it_extends_and_the_setups_it_uses():
    links = {t for t, _ in LINK.findall(text())}
    for needed in (
        WALLETS,
        RUNNING,
        "How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware",
        "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing",
        "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix",
        "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
        "Threat-Model",
    ):
        assert needed in links, needed
    body = text()
    assert f"{WALLETS}.md#shamir-secret-sharing-slip39" in body, "the Shamir section of the wallets page is linked"
    assert "issue 431" in body.lower()
    for issue in ("399", "400"):
        assert issue in body, f"issue {issue} is named"


def test_the_lesson_is_registered_in_the_manifest_in_the_cryptocurrency_track_in_order():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    lines = nav.splitlines()
    mine = next(i for i, row in enumerate(lines) if f"page: {NAME}," in row)
    wallets = next(i for i, row in enumerate(lines) if f"page: {WALLETS}," in row)
    running = next(i for i, row in enumerate(lines) if f"page: {RUNNING}," in row)
    assert wallets < mine < running, "after the wallets page and before the running-Monero page"
    line = lines[mine]
    assert 'status: "draft"' in line and 'subgroup: "Cryptocurrency"' in line and 'audience: "learner"' in line
    related = re.search(r"related: \[([^\]]*)\]", line)
    assert related, "a related list"
    pages = [p.strip() for p in related.group(1).split(",")]
    assert 3 <= len(pages) <= 6 and len(set(pages)) == len(pages), pages
    assert [p for p in pages if not (WIKI / f"{p}.md").exists()] == []
    assert WALLETS in pages and RUNNING in pages
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special


def test_glossary_rows_point_at_real_headings_and_no_term_is_defined_twice():
    heads = headings(text())
    glossary = (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines()
    terms = [line.split("**")[1].strip().lower() for line in glossary if line.startswith("| **")]
    mine = [line for line in glossary if line.startswith("| **") and f"{NAME}.md" in line]
    assert len(mine) >= 5, "expected glossary rows for the new terms"
    anchors = {a for line in mine for a in re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line)}
    assert anchors and anchors <= heads, sorted(anchors - heads)
    names = [line.split("**")[1].strip().lower() for line in mine]
    assert not sorted({t for t in names if terms.count(t) > 1})
    for needed in ("paper wallet", "paper wallet generator", "entropy"):
        assert any(n.startswith(needed) for n in names), needed


def test_every_table_has_a_named_first_header_cell_and_the_guard_bites():
    heads = table_headers(text())
    assert len(heads) >= 10, "the guard collected too few tables"
    assert all(h[0] for h in heads), [h for h in heads if not h[0]]
    assert table_headers("| | b |\n|---|---|\n| 1 | 2 |\n") == [["", "b"]]
    assert table_headers("| a | b |\n|---|---|\n| 1 | 2 |\n") == [["a", "b"]]


def test_no_addresses_keys_phrases_hashes_onion_names_or_money():
    body = text()
    for pattern in (ADDRESS, KEYSHAPE, SERVICE_NAME, LONG_HEX, LONG_BASE64):
        assert not pattern.findall(body), pattern.findall(body)
    assert not phrase_lines(body), phrase_lines(body)
    assert "—" not in body
    assert "$" not in body and "usd" not in body.lower() and "dollar" not in body.lower(), "no money amounts at all"
    assert "password: " not in body.lower()
    assert "wallet" in body.lower(), "the guard collected nothing"


def test_the_secret_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the placeholders are labels, not addresses")
    assert KEYSHAPE.search("the phrase abandon abandon abandon") and KEYSHAPE.search("milk sad wage cup")
    assert SERVICE_NAME.search("connect to " + "a" * 16 + ".onion now")
    assert LONG_HEX.search("fingerprint " + "ab" * 20) and not LONG_HEX.search("version 7.16 and CVE-2023-39910")
    assert LONG_BASE64.search("sig " + "A" * 50)
    phrase = "```text\n" + " ".join(["word"] * 12) + "\n```"
    assert phrase_lines(phrase) == [" ".join(["word"] * 12)]
    assert not phrase_lines("```text\n<word 1> <word 2> ... <word 12>\n```")


# ---- every command is labeled run or not run -------------------------------------------------------------------------


def test_every_command_block_says_whether_it_was_run_and_the_run_block_touched_no_network():
    body = text()
    blocks = code_blocks(body)
    assert len(blocks) >= 5, "the guard collected too few command blocks"
    assert not unlabeled_blocks(body), unlabeled_blocks(body)
    ran = [b for b in blocks if b[0].startswith(f"RUN on {DATE}")]
    assert len(ran) == 1, "one run block: the throwaway signature check"
    out = ran[0][2]
    assert "Good signature" in out and "BAD signature" in out and "example.invalid" in out
    assert "exit=0" in out and "exit=1" in out
    for forbidden in ("curl", "wget", "recv-keys", "monero-wallet-cli", "electrum", "ssh"):
        assert forbidden not in out.lower(), forbidden
    assert "gpg (GnuPG) 2.4.7" in body, "the tool version of the run"
    assert any(b[0].startswith("NOT RUN") for b in blocks)


def test_the_label_guard_bites():
    good = "NOT RUN, from the docs:\n\n```text\nx\n```\n"
    assert not unlabeled_blocks(good)
    assert unlabeled_blocks("Here is a command:\n\n```text\nx\n```\n") == ["x\n"]
    assert not unlabeled_blocks(f"RUN on {DATE}, throwaway:\n\n```text\nx\n```\n")
    assert unlabeled_blocks("RUN on 2026-10-01:\n\n```text\nx\n```\n")
    assert not unlabeled_blocks("```mermaid\nflowchart LR\n```\n")


# ---- the history, the reasons and where the sources disagree ----------------------------------------------------------


def test_the_reasons_table_covers_the_documented_problems_with_a_source_each():
    rows = tables(text(), REASONS)[0]
    assert len(rows) >= 10, "the guard collected too few reasons"
    flat = " ".join(" ".join(r).lower() for r in rows)
    for needed in (
        "printer",
        "address reuse",
        "change",
        "browser",
        "random",
        "malware",
        "photo",
        "water",
        "single point",
        "format",
        "sweep",
    ):
        assert needed in flat, needed
    for row in rows:
        assert len(row) == 3 and all(row), row
        assert "Bitcoin Wiki" in row[2] or "Electrum" in row[2] or "Milk Sad" in row[2] or "bitcoin.org" in row[2] or "est." in row[2], row


def test_the_page_says_where_the_sources_disagree_and_names_them():
    part = section(text(), DISAGREE)
    rows = tables(text(), DISAGREE)[0]
    assert len(rows) >= 4
    for needed in ("Bitcoin Wiki", "BIP38", "Unanimously Discourage", "Mastering Bitcoin", "Moneropedia", "Electrum", "2011", "2016"):
        assert needed in part, needed
    low = part.lower()
    assert "seed" in low and "single key" in low


def test_the_documented_cases_are_dated_cited_and_name_no_people():
    body = text()
    assert "CVE-2023-39910" in body and "Mersenne" in body and "32 bits" in body
    assert "air-gapped" in body.lower()
    assert "2013-08-11" in body and "Android" in body
    assert "2023-07-12" in body
    assert "Randstorm" not in body or "not read" in body.lower()
    assert "Libbitcoin" in body and "dispute" in body.lower(), "the maintainers' disagreement is reported"


# ---- the generators ---------------------------------------------------------------------------------------------------


def test_the_tools_table_is_dated_names_examples_only_and_ranks_nothing():
    rows = tables(text(), TOOLS)[0]
    assert len(rows) >= 4, "the guard collected too few tools"
    names = " ".join(r[0].lower() for r in rows)
    for tool in ("bitaddress", "bip39", "electrum", "monero"):
        assert tool in names, tool
    for row in rows:
        assert len(row) == 4 and all(row), row
        assert DATE in row[2], f"maintenance is dated: {row[0]}"
    flat = " ".join(" ".join(r) for r in rows)
    assert "2016-12-24" in flat, "bitaddress.org's last release is dated"
    assert "0.5.6" in flat and "2023-08-01" in flat
    body = text().lower()
    for banned in ("best generator", "we recommend", "i recommend", "the safest", "top pick", "number one", "ranked first", "winner"):
        assert banned not in body, banned
    assert "no ranking" in body and "examples" in body


def test_the_judging_checklist_names_the_five_checks_and_how_to_do_each():
    part = section(text(), "### How to judge a generator").lower()
    for needed in ("open source", "reproducible", "signature", "hash", "no network", "randomness"):
        assert needed in part, needed


# ---- the procedure ----------------------------------------------------------------------------------------------------


def test_the_procedure_cuts_the_network_before_it_generates_and_keeps_secrets_off_connected_machines():
    rows = tables(text(), PROCEDURE)[0]
    assert len(rows) >= 12, "the guard collected too few steps"
    assert not procedure_problems(rows), procedure_problems(rows)
    kinds = [r[1] for r in rows]
    assert kinds.index("verify") < kinds.index("transfer") < kinds.index("cut") < kinds.index("generate")
    assert kinds.index("record") < kinds.index("derive") < kinds.index("wipe") < kinds.index("fund")
    assert kinds.index("fund") < kinds.index("restore") <= kinds.index("spend")


def test_the_procedure_guard_bites():
    def row(n, kind, machine, network):
        return [str(n), kind, machine, network, "x"]

    good = [
        row(1, "download", "connected", "on"),
        row(2, "verify", "connected", "on"),
        row(3, "transfer", "media", "n/a"),
        row(4, "cut", "offline", "off"),
        row(5, "boot", "offline", "off"),
        row(6, "generate", "offline", "off"),
        row(7, "record", "offline", "off"),
        row(8, "derive", "second", "off"),
        row(9, "wipe", "offline", "off"),
        row(10, "fund", "connected", "on"),
        row(11, "restore", "second", "off"),
        row(12, "spend", "connected", "on"),
    ]
    assert procedure_problems(good) == []
    online = [list(r) for r in good]
    online[5][3] = "on"
    assert any("offline machine with the network on" in p for p in procedure_problems(online))
    late = [good[0], good[1], good[2], good[5], good[3], *good[4:5], *good[6:]]
    assert any("comes after" in p for p in procedure_problems(late)), "a generate before the cut is caught as an order problem"
    unverified = [r for r in good if r[1] != "verify"]
    assert any("no verify step" in p for p in procedure_problems(unverified))
    leak = [list(r) for r in good]
    leak.insert(7, row(99, "record", "connected", "on"))
    assert any("connected machine after the cut" in p for p in procedure_problems(leak))


def test_tails_facts_are_dated_and_the_stick_is_not_a_transfer_medium():
    body = text()
    assert "Tails" in body and "7.16" in body and "2026-10-29" in body
    assert "Offline Mode" in body
    assert "Do not use your Tails USB stick to transfer files" in body
    assert "write-once" in body.lower() or "write-protect" in body.lower()
    assert "most memory" in body
    assert "OpenPGP" in body


def test_bitcoin_and_monero_paths_are_both_covered_and_the_seeds_are_told_apart():
    body = text()
    part = section(body, "### Bitcoin: Electrum")
    for needed in ("Electrum", "not BIP39", "master public key", "Wallet", "Information", "sweep", "watch-only"):
        assert needed.lower() in part.lower(), needed
    monero = section(body, "### Monero: monero-wallet-cli")
    for needed in ("--generate-new-wallet", "--stagenet", "seed", "restore height", "25", "seed offset", "hashes.txt"):
        assert needed.lower() in monero.lower(), needed
    assert "Polyseed" in body


def test_printer_risks_and_the_hand_written_alternative_are_both_discussed():
    part = section(text(), "### Printing, or writing by hand").lower()
    for needed in ("hard drive", "wi-fi", "spooler", "network", "handwrit", "logged", "no storage"):
        assert needed in part, needed


def test_the_qubes_comparison_table_names_both_designs():
    rows = tables(text(), QUBES)[0]
    assert len(rows) >= 5
    flat = " ".join(" ".join(r) for r in rows)
    for needed in ("Qubes", "Tails", "RAM", "disk", "dom0", "wallet qube"):
        assert needed in flat, needed
    assert f"{RUNNING}.md" in section(text(), QUBES)


def test_protecting_the_paper_covers_photos_fire_water_shamir_and_steel():
    part = section(text(), "## Protecting the paper").lower()
    for needed in ("photo", "fire", "water", "shamir", "steel", "laminat", "split"):
        assert needed in part, needed
    assert f"{WALLETS}.md#shamir-secret-sharing-slip39" in section(text(), "## Protecting the paper")


# ---- the exercise ------------------------------------------------------------------------------------------------------


def test_the_exercise_has_a_stated_threat_model_and_a_step_by_step_attacker_table():
    part = section(text(), EXERCISE)
    assert "Threat model:" in part and "throwaway" in part.lower()
    rows = tables(text(), EXERCISE)[0]
    assert len(rows) >= 11, "the guard collected too few steps"
    for row in rows:
        assert len(row) == 4 and all(row), row
    names = " ".join(r[0].lower() for r in rows)
    for needed in ("download", "verify", "disconnect", "generate", "record", "store", "restore", "power off", "printer"):
        assert needed in names or needed in " ".join(" ".join(r).lower() for r in rows), needed
    assert len(tables(text(), EXERCISE)) == 2, "a worked table and an empty template"


# ---- diagrams ---------------------------------------------------------------------------------------------------------


def test_every_diagram_has_alt_text_a_source_and_a_picture_that_exists():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 3, "expected three diagrams"
    assert len(re.findall(r"```mermaid", body)) == len(found), "a Mermaid block has no picture above it"
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    for m in found:
        alt = m["alt"].strip()
        assert 20 <= len(alt) <= 150, alt
        png = (PAGE.parent / m["path"]).resolve()
        assert png.is_file(), m["path"]
        assert png.relative_to(ROOT).as_posix() in manifest, m["path"]
        assert m["src"].lstrip().startswith(("flowchart", "sequenceDiagram")), m["path"]
    alts = " ".join(m["alt"].lower() for m in found)
    for topic in ("paper wallet", "offline", "attacker"):
        assert topic in alts, topic


def test_the_diagram_guard_bites():
    bare = "![alt text here](images/x.png)\n\nno details block, so no source\n"
    assert not WRAPPED.search(bare)
    good = "![alt text here](images/x.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n  a --> b\n```\n\n</details>"
    assert WRAPPED.search(good)
    assert not WRAPPED.search(good.replace("<details>\n", ""))


# ---- the register -----------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status_a_url_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 30, "the guard collected too few rows"
    assert not rows_missing_status(text())
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "en.bitcoin.it/w/index.php?title=Paper_wallet",
        "bitcoin.org/en/secure-your-wallet",
        "bip-0038.mediawiki",
        "bitcoinbook/bitcoinbook",
        "moneropedia/paperwallet.html",
        "pointbiz/bitaddress.org",
        "iancoleman/bip39",
        "electrum.readthedocs.io/en/latest/coldstorage.html",
        "electrum.readthedocs.io/en/latest/malware.html",
        "electrum.readthedocs.io/en/latest/gpg-check.html",
        "electrum.readthedocs.io/en/latest/faq.html",
        "tails.net/doc/first_steps/welcome_screen",
        "tails.net/doc/about/features",
        "tails.net/doc/about/warnings",
        "tails.net/install/expert",
        "tails.net/install/v2/Tails/amd64/stable/latest.json",
        "tails.net/doc/sensitive_documents/printing_and_scanning",
        "verify-monero-binaries.md",
        "offline-transaction-signing.md",
        "monero-wallet-cli-reference.md",
        "milksad.info",
        "bitcoin.org/en/alert/2013-08-11-android",
        "Browser-based_wallet",
        "libbitcoin/libbitcoin-explorer",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 30


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


def test_the_unverified_items_are_marked_in_the_register():
    rows = {r[0]: r for r in register_rows(text())}
    run = next(r for k, r in rows.items() if "throwaway" in k.lower() and "signature" in k.lower())
    assert "Run on" in run[2]
    notrun = [r for k, r in rows.items() if k.lower().startswith("the offline procedure")]
    assert notrun and "**est.**" in notrun[0][2], "the assembled procedure is marked as not run"


# ---- scope and tone ---------------------------------------------------------------------------------------------------


def test_the_page_has_no_price_talk_shilling_evasion_content_or_maintainer_contribution_claims():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "pump", "airdrop", "evade detection", "avoid law enforcement",
        "launder money", "hide your funds", "bypass kyc", "how to avoid being traced", "untraceable",
        "cryptobro", "mcafee", "to avoid tracing", "stay anonymous", "cover your tracks", "comfortable with cryptocurrency",
        "affiliate", "contribut", "pull request", "his fork", "helped build", "authored",
    ):
        assert banned not in body, banned
    assert body.count("price") <= 1 and body.count("trading") <= 1, "only the rule sentence itself uses these words"
    assert "no how-to for anything illegal" in body


def test_the_page_never_states_a_security_posture_detail_about_this_repository():
    body = text().lower()
    for banned in ("this repository", "our firewall", "our droplet", "this project's ssh", "our spacelift", "our doppler"):
        assert banned not in body, banned


def test_dates_are_on_the_claims_that_go_stale():
    body = text()
    for needed in ("2026-08-06", "2024-08-05", "2024-04-28", "2023-11-02", "2026-10-08", "2012-11-20", "2023-08-01"):
        assert needed in body, needed
    assert "no edit date" in body or "no date" in body
