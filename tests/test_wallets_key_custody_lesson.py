# SPDX-License-Identifier: Apache-2.0
"""The wallets and key custody lesson: registered, honest about what was run, diagrams intact, safe to read.

docs/wiki/Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md is page 4 of the
five-page cryptocurrency set (issue 399). A banner that claims more than was run, a dead link, a missing registration, a
diagram with no picture or alt text, a recovery phrase or key or address on the page, an affiliate link without its
disclosure beside it, a Raspberry Pi claim stated as fact, a drill script that does not do what the page says, a worked
number that the arithmetic does not give, price talk, or a register row with no URL and no date would each teach or
reveal the wrong thing.
"""

import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig"
PAGE = WIKI / f"{NAME}.md"
PAGE_ONE = "Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks"
PAGE_TWO = "How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
# A wallet address in any of the common shapes: legacy Bitcoin, Bech32 Bitcoin, Ethereum and Monero.
ADDRESS = re.compile(
    r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"
    r"|\bbc1[ac-hj-np-z02-9]{11,71}\b"
    r"|\b0x[0-9a-fA-F]{40}\b"
    r"|\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b"
)
# Extended keys and wallet-import-format keys, and the two best-known public test phrases.
KEYSHAPE = re.compile(
    r"\b[xyztu](?:prv|pub)[1-9A-HJ-NP-Za-km-z]{20,}\b"
    r"|\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"
    r"|\babandon abandon\b|\bzoo zoo\b|\blegal winner thank\b"
)
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
# The only 64-digit hex value the page may carry: the SHA-256 of the public BIP39 English word list.
PUBLIC_HEX = {"2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"}
AFFILIATE = "https://affil.trezor.io/aff_c?offer_id=133&aff_id=32739"
THREATS = "## The threat model"
RECOMMEND = "## The hardware wallet I recommend: Trezor"
EXERCISE = "## Free exercise: create, back up, restore and verify with no funds"


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
    """Rows that cite a page must carry a URL and the read date; framing and general-knowledge rows are exempt by name."""
    exempt = (
        "The maintainer's framing",
        "The maintainer's statement",
        "The maintainer's position",
        "The author's own",
        "General knowledge",
    )
    bad = []
    for row in register_rows(body):
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def undisclosed_links(body: str, link: str = AFFILIATE) -> list[int]:
    """Positions of the affiliate link with no 'affiliate link' wording and commission statement just before it."""
    bad = []
    for m in re.finditer(re.escape(link), body):
        before = body[max(0, m.start() - 700) : m.start()].lower()
        if "affiliate link" not in before or "commission" not in before or "no cost to the reader" not in before:
            bad.append(m.start())
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


def drill_source(body: str) -> str:
    part = section(body, EXERCISE)
    return re.search(r"```python\n(.*?)\n```", part, re.DOTALL).group(1)


def load_drill(tmp_path: Path):
    script = tmp_path / "wallet_drill.py"
    script.write_text(drill_source(text()), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("wallet_drill", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return script, module


def made_up_words(tmp_path: Path) -> tuple[Path, list[str]]:
    """A 2,048-word list of invented tokens: the algorithm does not depend on the real words."""
    words = [f"w{i:04d}" for i in range(2048)]
    path = tmp_path / "words.txt"
    path.write_text("\n".join(words) + "\n", encoding="utf-8")
    return path, words


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_run():
    body = text()
    assert body.startswith("# Wallets and key custody")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run on a blockchain network, a node or a hardware wallet" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    assert "I did not open it" in body or "(I did not open it)" in body, "the affiliate link was not opened"


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 7, "the guard collected too few links"
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
        PAGE_ONE,
        PAGE_TWO,
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Hashing-Encryption-and-Keys",
        "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
    ):
        assert needed in links, needed
    assert "#key-management-and-custody-the-hard-part" in body
    assert "#what-pinodexmr-documents" in body, "the PiNodeXMR example on the overview page is linked"
    # Page three is named in plain text until it is in the wiki, then it must be linked.
    monero = sorted(p.stem for p in WIKI.glob("How-Monero*.md"))
    if monero:
        assert any(stem in links for stem in monero), "the Monero page exists, so it must be linked"
    else:
        assert "issue 398" in body and "not in the wiki yet" in body
    for issue in ("396", "397", "398", "399", "400", "372"):
        assert issue in body, f"issue {issue} is named"


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line, "the banner says unverified draft"
    assert "Page 4 of 5" in line


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


def test_every_table_has_a_named_first_header_cell():
    heads = table_headers(text())
    assert len(heads) >= 10, "the guard collected too few tables"
    assert all(h[0] for h in heads), [h for h in heads if not h[0]]


def test_the_table_guard_bites():
    assert table_headers("| | b |\n|---|---|\n| 1 | 2 |\n") == [["", "b"]]
    assert table_headers("| a | b |\n|---|---|\n| 1 | 2 |\n") == [["a", "b"]]
    assert tables("## H\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\ntext\n", "## H") == [[["1", "2"], ["3", "4"]]]


def test_no_addresses_keys_phrases_stray_hex_ip_addresses_em_dashes_or_money_amounts():
    body = text()
    assert not ADDRESS.findall(body), ADDRESS.findall(body)
    assert not KEYSHAPE.findall(body), KEYSHAPE.findall(body)
    assert not IPV4.findall(body), IPV4.findall(body)
    assert "—" not in body
    assert "$" not in body and "usd" not in body.lower() and "dollar" not in body.lower(), "no money amounts at all"
    found = set(HEX64.findall(body))
    assert found, "the guard collected no hash at all"
    assert found <= PUBLIC_HEX, sorted(found - PUBLIC_HEX)
    assert "wallet" in body.lower(), "the guard collected nothing"


def test_the_secret_guards_bite():
    assert ADDRESS.search("send to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa today")
    assert ADDRESS.search("send to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq today")
    assert ADDRESS.search("send to 0x" + "ab" * 20 + " today")
    assert ADDRESS.search("send to 4" + "A" + "b" * 93 + " today")
    assert not ADDRESS.search("the placeholder shares A, B and C are labels, not addresses")
    assert KEYSHAPE.search("key xprv" + "9" * 30)
    assert KEYSHAPE.search("use " + "K" + "x" * 51)
    assert KEYSHAPE.search("the phrase abandon abandon abandon")
    assert not KEYSHAPE.search("the extended public key is derived from the parent")
    assert HEX64.search("key " + "ab" * 32) and "ab" * 32 not in PUBLIC_HEX
    assert IPV4.search("host 192.0.2.7") and not IPV4.search("as of release 0.9.7.1")


# ---- the Trezor recommendation and the affiliate link -----------------------------------------------------------------


def test_the_affiliate_link_is_exact_and_always_disclosed_just_before_it():
    body = text()
    assert body.count(AFFILIATE) >= 1, "the maintainer's link, exactly as given"
    assert not undisclosed_links(body), "every occurrence has the disclosure within the preceding text"
    top = body[:3500].lower()
    assert "affiliate disclosure" in top and "may receive a commission" in top and "no cost to the reader" in top, (
        "a prominent disclosure near the top, before any recommendation"
    )
    assert body.index("Affiliate disclosure") < body.index("## What you will be able to do")
    assert "the maintainer's statement" in body and "I did not compare checkout totals" in body
    assert "affil.trezor.io" in body, "the host is checked against the one Trezor names"


def test_the_affiliate_guard_bites():
    good = (
        "> **Affiliate disclosure.** This is an affiliate link and this project may receive a commission at no cost to "
        "the reader. [x](" + AFFILIATE + ")"
    )
    assert undisclosed_links(good) == []
    assert undisclosed_links("buy here [x](" + AFFILIATE + ")") != []
    assert undisclosed_links("an affiliate link, with a commission. [x](" + AFFILIATE + ")") != [], "needs the cost words"
    far = "an affiliate link, a commission, no cost to the reader." + " filler" * 200 + " [x](" + AFFILIATE + ")"
    assert undisclosed_links(far) != [], "a disclosure far away does not count"


def test_the_recommendation_states_what_was_and_was_not_verified_about_open_source_and_the_pi():
    body = text()
    part = section(body, RECOMMEND)
    assert "open source" in part.lower() and "GPLv3" in part and "LGPLv3" in part
    assert "reproducible-build" in part or "reproducible build" in part.lower()
    assert "Raspberry Pi Zero" in part
    assert "PiTrezor" in part and "community project" in part and "not Trezor's project" in part
    assert "Supported by what I read" in part and "Not supported by what I read" in part
    assert "anybody that has your SD card can access your seed words and private key" in part, "the author's own caveat"
    assert "not vetted by security professionals" in part, "the Wasabi Wallet post's caution"
    assert "we leave further investigation to others" in part, "WalletScrutiny's limit"
    assert "diy" in part.lower()
    assert "archive copy" in part, "the Wasabi host did not load, and the page says so"
    assert "The maintainer's account (not a source)" in part and "built one himself" in part
    assert "that it has none is my reading (est.)" in part, "the secure-element point is marked as the author's reading"
    assert "The advice to buy the real device stands" in part
    assert "development purposes only" in part, "the emulator is for development only"
    assert "DIY" in part, "Trezor's own wording about DIY builds is quoted"
    assert "buy only from the manufacturer or its authorized channels" in body.lower()
    for check in ("holographic seal", "blank", "firmware", "authentication check"):
        assert check in part.lower() + section(body, RECOMMEND).lower(), check
    assert "trezor.io/resellers" in body
    assert "I read no other vendor's documentation" in part


PI_OVERCLAIMS = (
    "protection of the real hardware",
    "same protection",
    "as secure as",
    "equivalent wallet",
    "equals the real device",
    "identical to the real",
    "just as secure",
)
PI_NEGATORS = ("not supported", "do not read", "does not", "lacks", "stands", "no source")


def pi_overclaims(body: str) -> list[str]:
    """Phrases that put the Pi build level with the real device, with no refusal in the 250 characters around them."""
    bad = []
    for phrase in PI_OVERCLAIMS:
        for m in re.finditer(re.escape(phrase), body, re.IGNORECASE):
            context = body[max(0, m.start() - 250) : m.end() + 250].lower()
            if not any(n in context for n in PI_NEGATORS):
                bad.append(phrase)
    return bad


def test_the_page_does_not_claim_the_pi_build_equals_the_real_device():
    body = text()
    assert "protection of the real hardware" in body, "the guard collected nothing: the refusal sentence is gone"
    assert pi_overclaims(body) == []
    # The attributed claims stay attributed to a source or marked as a reading.
    assert body.count("PiTrezor") >= 8


def test_the_pi_overclaim_guard_bites():
    assert pi_overclaims("A PiTrezor gives the same protection as the real device.") == ["same protection"]
    assert pi_overclaims("The Pi build is just as secure, and cheaper.") == ["just as secure"]
    assert pi_overclaims("It is an equivalent wallet, and cheaper.") == ["equivalent wallet"]
    assert pi_overclaims("Not supported: that it gives the protection of the real hardware.") == []
    far = "It is as secure as the real device." + " filler" * 200 + " not supported"
    assert pi_overclaims(far) == ["as secure as"], "a refusal far away does not count"


def test_no_other_vendor_is_named_or_attacked_and_the_pi_is_not_stated_as_fact():
    body = text()
    for vendor in ("Coldcard", "BitBox", "KeepKey", "Keystone", "Ledger Nano", "Ledger Stax", "Ledger Flex", "SafePal"):
        assert vendor not in body, vendor
    for claim in ("any Raspberry Pi can be a Trezor", "runs on a Raspberry Pi Zero", "can run Trezor firmware"):
        for m in re.finditer(re.escape(claim), body):
            context = body[max(0, m.start() - 200) : m.end() + 200].lower()
            assert any(w in context for w in ("rewrite", "not supported", "unverified", "could not")), claim


# ---- BIP39, SLIP39 and the toy arithmetic ------------------------------------------------------------------------------


def test_the_bip39_table_is_the_arithmetic_the_standard_gives():
    body = text()
    part = body.split("| Entropy (bits) |")[1].split("\n\n")[0]
    rows = [[c.strip() for c in line.strip("|").split("|")] for line in part.splitlines()[2:]]
    assert len(rows) == 5, "the guard collected too few rows"
    for ent, cs, total, words in rows:
        ent, cs, total, words = int(ent), int(cs), int(total), int(words)
        assert cs == ent // 32 and ent % 32 == 0
        assert total == ent + cs and total % 11 == 0 and words == total // 11
    assert [int(r[3]) for r in rows] == [12, 15, 18, 21, 24]
    assert 2**11 == 2048
    # One random wrong word in a 12-word phrase passes the 4-bit checksum about once in sixteen.
    assert 2 ** (11 * 12) // 2 ** (128) == 16
    assert "2,048 words" in body and "2,048 rounds" in body


def test_the_slip39_sizes_on_the_page_add_up():
    body = text()
    # id 15, ext 1, e 4, GI 4, Gt 4, g 4, I 4, t 4 = 40 bits of header; ps = padding plus the secret; checksum 30.
    header, checksum = 15 + 1 + 4 * 6, 30
    for secret_bits, padded, words in ((128, 130, 20), (256, 260, 33)):
        assert padded % 10 == 0 and padded >= secret_bits and padded - secret_bits < 10
        assert (header + padded + checksum) == words * 10
    assert "20-word" in body and "33-word" in body
    assert "1,024" in body and "16 groups" in body


def test_the_toy_shamir_numbers_are_what_the_arithmetic_gives():
    body = text()
    rows = {r[0]: (int(r[1]), int(r[2])) for r in tables(body, "## Shamir secret sharing (SLIP39)")[0]}
    assert set(rows) == {"A", "B", "C"}, "the guard collected the three shares"
    p = 97

    def f(x: int) -> int:
        return (42 + 7 * x) % p

    assert {k: v[1] for k, v in rows.items()} == {"A": f(1), "B": f(2), "C": f(3)}

    def recover(a: tuple[int, int], b: tuple[int, int]) -> int:
        (x1, y1), (x2, y2) = a, b
        return (y1 * x2 * pow(x2 - x1, -1, p) + y2 * x1 * pow(x1 - x2, -1, p)) % p

    pts = list(rows.values())
    for i in range(3):
        for j in range(i + 1, 3):
            assert recover(pts[i], pts[j]) == 42, "any two shares give the secret"
    # One share is consistent with every secret: for each s there is exactly one slope a with s + 2a = 56.
    x, y = rows["B"]
    consistent = {s for s in range(p) if any((s + a * x) % p == y for a in range(p))}
    assert consistent == set(range(p)) and len(consistent) == 97
    assert "all 97 secrets" in body and "42" in body


def test_the_shamir_guard_bites():
    p = 97
    pts = [(1, (42 + 7) % p), (2, (42 + 14) % p)]
    (x1, y1), (x2, y2) = pts
    assert (y1 * x2 * pow(x2 - x1, -1, p) + y2 * x1 * pow(x1 - x2, -1, p)) % p == 42
    wrong = [(1, 50), (2, (42 + 14) % p)]
    (x1, y1), (x2, y2) = wrong
    assert (y1 * x2 * pow(x2 - x1, -1, p) + y2 * x1 * pow(x1 - x2, -1, p)) % p != 42, "a wrong share gives a wrong secret"


def test_the_multisig_counts_on_the_page_are_what_combinatorics_gives():
    body = text()
    n, m = 3, 2
    assert math.comb(n, m) == 3 and sum(math.comb(n, k) for k in range(m, n + 1)) == 4
    assert n - m == 1 and m - 1 == 1, "one key lost and one key stolen are both survivable at 2-of-3"
    part = section(body, "## Multisignature wallets")
    assert "2-of-3" in part and "any one key can be lost" in part and "any one key can be stolen" in part


# ---- the drill script on the page -------------------------------------------------------------------------------------


def test_the_drill_script_has_no_network_or_file_writes_and_is_the_page_text(tmp_path):
    source = drill_source(text())
    for banned in ("socket", "urllib", "requests", "http", "subprocess", "os.system", "open(path, \"w", ".write("):
        assert banned not in source, banned
    assert "open(path, encoding=" in source, "the only file access is reading the word list"
    assert 'if __name__ == "__main__":' in source


def test_the_drill_round_trips_checks_and_matches_an_independent_computation(tmp_path):
    _script, drill = load_drill(tmp_path)
    _path, words = made_up_words(tmp_path)
    entropy = bytes(range(16))
    phrase = drill.to_phrase(entropy, words)
    assert len(phrase.split()) == 12 and all(w in set(words) for w in phrase.split())
    assert drill.from_phrase(phrase, words) == entropy
    # Independent computation with integers: 128 bits of entropy then the first 4 bits of SHA-256, 11 bits per word.
    big = int.from_bytes(entropy, "big") << 4 | (hashlib.sha256(entropy).digest()[0] >> 4)
    expected = [words[(big >> (11 * (11 - i))) & 0x7FF] for i in range(12)]
    assert phrase.split() == expected
    # A changed word is either refused or restores some other wallet; it can never restore the original.
    parts = phrase.split()
    parts[4] = words[(words.index(parts[4]) + 1) % 2048]
    assert drill.from_phrase(" ".join(parts), words) != entropy
    assert drill.from_phrase(phrase + " " + words[0], words) is None, "a 13-word phrase is refused"
    assert drill.from_phrase(" ".join(["notaword"] * 12), words) is None, "unknown words are refused"
    # The seed follows the standard's shape: 64 bytes, deterministic, and the passphrase changes it without an error.
    seed = drill.seed(phrase)
    assert len(seed) == 64 and seed == drill.seed(phrase)
    assert drill.seed(phrase, "x") != seed and drill.seed(phrase, "x") != drill.seed(phrase, "y")
    assert seed == hashlib.pbkdf2_hmac("sha512", phrase.encode(), b"mnemonic", 2048)
    assert drill.label(seed) == hashlib.sha256(seed).hexdigest()[:8]


def test_the_drill_catches_about_fifteen_in_sixteen_wrong_words(tmp_path):
    script, _drill = load_drill(tmp_path)
    path, _words = made_up_words(tmp_path)
    out = subprocess.run(
        [sys.executable, "-I", str(script), str(path), "break"], capture_output=True, text=True, check=True, timeout=120
    ).stdout
    m = re.search(r"in (\d+) made-up phrases: the checksum caught (\d+), missed (\d+)", out)
    assert m, out
    trials, caught, missed = map(int, m.groups())
    assert trials == 300 and caught + missed == trials
    assert 0.90 <= caught / trials <= 0.97, "about 15/16 are caught"


def test_the_drill_make_and_check_agree_through_the_command_line(tmp_path):
    script, _drill = load_drill(tmp_path)
    path, _words = made_up_words(tmp_path)
    run = [sys.executable, "-I", str(script), str(path)]
    made = subprocess.run([*run, "make"], capture_output=True, text=True, check=True, timeout=120).stdout
    phrase = re.search(r"throwaway phrase: (.+)", made).group(1)
    first = re.search(r"fingerprint, no passphrase: ([0-9a-f]{8})", made).group(1)
    checked = subprocess.run(
        [*run, "check"], input=phrase + "\nhorse\n", capture_output=True, text=True, check=True, timeout=120
    ).stdout
    assert "checksum: ok" in checked
    assert re.search(r"fingerprint, no passphrase: " + first, checked), "the restore matches the backup"
    with_pass = re.search(r"fingerprint, with passphrase: ([0-9a-f]{8})", checked).group(1)
    assert with_pass != first, "a passphrase gives a different wallet and no error"
    bad_words = phrase.split()
    bad_words[0] = "w9999"
    bad = subprocess.run(
        [*run, "check"], input=" ".join(bad_words) + "\n", capture_output=True, text=True, check=True, timeout=120
    ).stdout
    assert "checksum: FAILED" in bad


def test_the_drill_guard_bites(tmp_path):
    _script, drill = load_drill(tmp_path)
    _path, words = made_up_words(tmp_path)
    phrase = drill.to_phrase(bytes(16), words)
    swapped = phrase.split()
    swapped[0] = words[1]
    swapped_text = " ".join(swapped)
    # Entropy of all zeros has a fixed checksum; changing a word's top bits must break it or change the entropy.
    assert drill.from_phrase(swapped_text, words) != bytes(16), "a changed word never restores the original"
    short = tmp_path / "short.txt"
    short.write_text("one two three\n", encoding="utf-8")
    try:
        drill.load(str(short))
    except SystemExit:
        pass
    else:
        raise AssertionError("a short word list must be refused")


def test_the_page_names_the_word_list_hash_and_the_scratch_conformance_run():
    body = text()
    assert next(iter(PUBLIC_HEX)) in body and "bip-0039/english.txt" in body
    assert "all 24 English" in body and "282 of 300" in body


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


def test_the_diagrams_cover_the_topics_the_issue_asks_for():
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(text()))
    for topic in ("ledger", "hardware wallet", "shamir", "multisig"):
        assert topic in alts, topic


# ---- the register -----------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 30, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "bip-0039.mediawiki",
        "bip-0032.mediawiki",
        "bip-0044.mediawiki",
        "bip-0011.mediawiki",
        "bip-0174.mediawiki",
        "slip-0039.md",
        "slip-0044.md",
        "developer.bitcoin.org/devguide/wallets.html",
        "developer.bitcoin.org/devguide/transactions.html",
        "managing-wallets.md",
        "ethereum.org/developers/docs/accounts",
        "eips.ethereum.org/EIPS/eip-20",
        "moneropedia/mnemonicseed.html",
        "moneropedia/spendkey.html",
        "moneropedia/viewkey.html",
        "csrc.nist.gov/glossary/term/split_knowledge",
        "csrc.nist.gov/glossary/term/separation_of_duty",
        "csrc.nist.gov/glossary/term/hardware_security_module_hsm",
        "trezor-firmware/main/LICENSE.md",
        "docs/common/reproducible-build.md",
        "docs/core/emulator/index.md",
        "docs/legacy/index.md",
        "docs/core/misc/optiga.md",
        "trezor.io/learn/security-privacy/how-trezor-keeps-you-safe/security-safety-in-trezor",
        "trezor-safe-device-authentication-check",
        "trezor.io/learn/a/secure-element-in-trezor-safe-3",
        "trezor.io/guides/trezor-devices/trezor-safe-3/authenticate-trezor-safe-3",
        "trezor-s-trusted-display-verify-every-address-on-your-device",
        "understanding-trezor-wallet-backups-12-20-or-24-words",
        "personal-security-standards/scams-and-phishing",
        "trezor.io/resellers",
        "trezor.io/security",
        "trezor.io/affiliate",
        "pitrezor.com/2018/02/pitrezor-homemade-trezor-bitcoin-wallet.html",
        "blog.wasabiwallet.io/diy-hardware-wallets-part-ii/",
        "old.walletscrutiny.com/hardware/pitrezor",
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
    port = next(r for k, r in rows.items() if k.startswith("A community project (PiTrezor)"))
    assert "pitrezor.com" in port[1] and "Read 2026-11-01" in port[2] and "the fork's code not read" in port[2]
    wasabi = next(r for k, r in rows.items() if k.startswith("PiTrezor is a port that is not vetted"))
    assert "blog.wasabiwallet.io" in wasabi[1] and "archive copy" in wasabi[2]
    scrutiny = next(r for k, r in rows.items() if k.startswith("PiTrezor's verdict"))
    assert "walletscrutiny.com/hardware/pitrezor" in scrutiny[1] and "Read 2026-11-01" in scrutiny[2]
    his = next(r for k, r in rows.items() if k.startswith("The maintainer built a PiTrezor"))
    assert "**est.**" in his[2] and "not independently checked" in his[2], "his account is marked as his"
    reading = next(r for k, r in rows.items() if k.startswith("A Pi Zero has no secure element"))
    assert "**est.**" in reading[2] and "no source I read states it" in reading[2]
    assert not any(k.startswith("A Raspberry Pi Zero can reproduce") for k in rows), "the old unsourced row is replaced"
    link = next(r for k, r in rows.items() if k.startswith('"No cost to the reader"'))
    assert "**est.**" in link[2]


# ---- scope and tone ---------------------------------------------------------------------------------------------------


def test_the_exercise_is_a_checklist_on_a_wallet_with_no_funds_and_says_what_was_not_run():
    part = section(text(), EXERCISE)
    boxes = re.findall(r"^- \[ \] ", part, re.MULTILINE)
    assert len(boxes) >= 10, "the guard collected too few checklist items"
    for needed in ("nothing", "create", "restor", "compare", "wipe", "wrong word", "wrong passphrase", "photo"):
        assert needed in part.lower(), needed
    assert "Not run" in part
    assert "testnet" in part.lower() or "test network" in part.lower()


def test_the_history_is_the_authors_account_and_the_recommendation_is_the_maintainers():
    body = text()
    part = section(body, "## Before hardware wallets: the Core wallet on a netbook")
    assert "netbook" in part and "around 2016" in part and "not sourced" in part
    assert "Why that setup worked" in part and "Where it fell short" in part
    assert "encrypted at rest" in part


def test_the_threat_table_has_every_threat_the_issue_names():
    part = section(text(), THREATS).lower()
    for threat in (
        "malware",
        "clipboard",
        "phishing",
        "supply chain",
        "theft of the device",
        "coercion",
        "loss",
        "bit rot",
        "cloud",
        "human leak",
    ):
        assert threat in part, threat
    rows = tables(text(), THREATS)[0]
    assert len(rows) == 11 and all(len(r) == 4 for r in rows)


def test_each_coin_is_covered_and_monero_is_not_bip39():
    body = text()
    for heading in ("### Bitcoin", "### Ethereum", "### Monero"):
        assert heading in body, heading
    monero = body.split("### Monero")[1].split("\n## ")[0]
    assert "25 words" in monero and "not BIP39" in monero and "spend key" in monero and "view key" in monero
    assert "deprecated" in monero


def test_the_page_does_not_repeat_the_stance_and_has_no_price_talk_shilling_or_evasion_content():
    body = text().lower()
    for banned in (
        "to the moon", "shitcoin", "memecoin", "hodl", "lambo", "buy the dip", "bullish", "bearish",
        "market cap", "all-time high", "pump", "airdrop", "evade detection", "avoid law enforcement",
        "launder money", "hide your funds", "bypass kyc", "how to avoid being traced", "untraceable",
        "cryptobro", "mcafee", "to avoid tracing", "stay anonymous", "cover your tracks", "comfortable with cryptocurrency",
    ):
        assert banned not in body, banned
    assert body.count("price") <= 1 and body.count("trading") <= 1
    assert "no price talk, no coin shilling and no trading advice" in body
    assert "no how-to for anything illegal" in body


def test_old_pages_are_dated_where_they_are_used():
    body = text()
    assert "2009-2020" in body, "the developer guide's own copyright range is stated"
    assert "2013-09-10" in body and "2017-12-18" in body, "the BIP39 and SLIP39 dates are stated"
    assert "June 2017" in body, "the Monero view-key statement is dated by its own text"
    assert "deprecated" in body, "the Monero page's own deprecation notice is stated"
    assert "show no edit date" in body, "Trezor's pages carry no edit date and the page says so"
