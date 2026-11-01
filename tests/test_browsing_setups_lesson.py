# SPDX-License-Identifier: Apache-2.0
"""The browsing setups lesson: registered, honest about what was read, diagrammed, and safe to read.

docs/wiki/The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix.md compares five ways to
reach Tor (Tor Browser on a normal operating system, Brave's Tor window, Whonix, Tails, and Qubes running Whonix), says
what each one's trust boundary and threat model are, and carries one clearly marked section of the maintainer's own
opinion about running Tails or Kali as a daily system. A banner that claims more than was done, a dead link, a missing
registration, an address outside the documentation ranges, a claim with no status or date, a diagram with no alt text,
no source or no picture, a matrix that lost a setup or a threat, opinion words that leak out of the marked section, a
section that criticizes a habit with no way out, a link to a page that has a link cap, or a line that states a security
detail about this repository would each teach or reveal the wrong thing.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix"
PAGE = WIKI / f"{NAME}.md"
OVERVIEW = "Tor-I2P-and-the-Darknet-Without-the-Myths"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALLOWED_ADDR = re.compile(r"^(?:192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3})$")
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
STATUS_WORDS = ("Read", "General knowledge", "**est.**", "Observed", "Not read")
URL = re.compile(r"\]\(https://[^)\s]+\)")
DIAGRAM = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>images/[^)\n]+\.png)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>"
    r"\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
IMAGE_ANY = re.compile(r"!\[[^\]\n]*\]\([^)\n]+\)")
MAX_ALT = 150
EXPECTED_DIAGRAMS = 6
DATE_READ = "2026-11-01"
LONG_RANDOM = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
SETUPS = ("Tor Browser on a normal OS", "Brave's Tor window", "Whonix", "Tails", "Qubes with Whonix")
THREATS = ("A site or tracker fingerprinting the browser", "An app that ignores Tor", "A browser bug that exposes the real address",
           "Malware on the computer or the host", "Traces left on the computer", "A watcher on the local network",
           "An observer of both ends", "Your own habits", "Altered hardware or firmware")
MAINTAINER_HEADING = "## The maintainer's view: Tails and Kali as a daily system, and the badge"
OPINION_WORDS = ("larp", "skid", "poser")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def stray_addresses(body: str) -> list[str]:
    return [a for a in ADDR.findall(body) if not ALLOWED_ADDR.match(a)]


def tables(body: str) -> list[list[str]]:
    """Every markdown table as its list of lines, found by a header line followed by a separator line."""
    lines = body.splitlines()
    found = []
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", lines[i + 1]):
            block = [line]
            for later in lines[i + 2:]:
                if not later.startswith("|"):
                    break
                block.append(later)
            found.append(block)
    return found


def unnamed_first_cells(body: str) -> list[str]:
    return [t[0] for t in tables(body) if not t[0].strip("|").split("|")[0].strip()]


def matrix_problems(body: str) -> list[str]:
    """The matrix has the five setups as columns and the nine threats as rows, every cell an answer."""
    start = body.index("## The matrix: five setups against nine threats")
    section = body[start:].split("\n## ")[0]
    block = next(iter(tables(section)), None)
    if block is None:
        return ["no table in the matrix section"]
    header = [c.strip() for c in block[0].strip("|").split("|")]
    problems = []
    if header != ["Threat", *SETUPS]:
        problems.append(f"header is {header}")
    rows = [[c.strip() for c in r.strip("|").split("|")] for r in block[1:]]
    if [r[0] for r in rows] != list(THREATS):
        problems.append(f"threats are {[r[0] for r in rows]}")
    for r in rows:
        if len(r) != 6 or any(len(c) < 20 for c in r[1:]):
            problems.append(f"thin row: {r[0]}")
    return problems


def diagram_problems(body: str, root: Path = ROOT, wiki: Path = WIKI) -> list[str]:
    """Every picture on the page is a wrapped diagram with alt text, a Mermaid source and a picture on disk."""
    problems = []
    wrapped = list(DIAGRAM.finditer(body))
    if len(wrapped) != len(IMAGE_ANY.findall(body)):
        problems.append("a picture on the page is not a wrapped diagram")
    for m in wrapped:
        alt = m["alt"].strip()
        if len(alt) < 20 or len(alt) > MAX_ALT:
            problems.append(f"alt text length {len(alt)}: {alt[:40]!r}")
        if not m["src"].strip():
            problems.append(f"empty source for {m['path']}")
        if not (wiki / m["path"]).is_file():
            problems.append(f"picture missing: {m['path']}")
    return problems


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    return body[start:].split("\n## ", 1)[0] if body[start:].startswith(heading) else ""


def opinion_outside(body: str, heading: str = MAINTAINER_HEADING, words: tuple[str, ...] = OPINION_WORDS) -> list[str]:
    """Opinion words that appear anywhere except inside the marked section."""
    inside = section(body, heading)
    outside = body.replace(inside, "", 1).lower()
    return [w for w in words if w in outside]


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# The browsing setups compared")
    assert "Page 5 of a seven-page series" in body
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and DATE_READ in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_finished_siblings_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 14, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        OVERVIEW,
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves",
        "Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR",
        "How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware",
        "Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS",
        "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options",
        "Threat-Model",
    ):
        assert needed in links, needed


def test_the_unwritten_series_pages_are_named_in_plain_text_not_linked():
    body = text()
    for plain in ("operational security for Tor and I2P", "detecting and managing Tor, I2P and VPN traffic on a network",
                  "hands-on Whonix and Qubes exercises"):
        assert plain in body, plain
    linked_series = {t for t in LINK.findall(body) if re.search(r"OPSEC-for|Detecting|Exercise", t)}
    assert not linked_series, linked_series


def test_a_page_with_a_link_cap_is_not_linked():
    # tests/test_blast_radius_lesson.py caps how many pages may link that lesson, and the cap is full.
    assert "Plan-for-Failure-Blast-Radius" not in text()


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    rows = 0
    terms = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            terms.append(line.split("|")[1].strip().strip("*").lower())
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 6, "expected glossary rows for the new terms"
    assert len(set(terms)) == len(terms), "a glossary term is defined twice"
    # A term this page adds must not already be defined by another row of the glossary.
    every = [ln.split("|")[1].strip().strip("*").lower() for ln in
             (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if ln.startswith("| **")]
    assert all(every.count(t) == 1 for t in terms), [t for t in terms if every.count(t) != 1]
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_only_documentation_addresses_no_onion_names_long_random_values_or_em_dashes():
    body = text()
    assert not stray_addresses(body), set(stray_addresses(body))
    assert not ONION.findall(body)
    assert "—" not in body
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs


def test_the_address_guard_bites():
    assert stray_addresses("host 8.8.8.8") == ["8.8.8.8"]
    assert stray_addresses("host 10.0.0.1 and 192.0.3.1") == ["10.0.0.1", "192.0.3.1"]
    assert not stray_addresses("Alice 192.0.2.10 and 203.0.113.50")
    assert ONION.findall("go to " + "a" * 56 + ".onion")
    assert LONG_RANDOM.findall("x" + "a1" * 20)


def test_every_diagram_has_alt_text_a_source_block_and_a_picture_that_exists():
    body = text()
    wrapped = list(DIAGRAM.finditer(body))
    assert len(wrapped) == EXPECTED_DIAGRAMS, f"expected {EXPECTED_DIAGRAMS} diagrams, found {len(wrapped)}"
    assert not diagram_problems(body)
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    for m in wrapped:
        assert f"docs/wiki/{m['path']}" in manifest, m["path"]
    names = [m["path"] for m in wrapped]
    assert len(set(names)) == len(names)


def test_the_diagram_guard_bites(tmp_path):
    wiki = tmp_path
    (wiki / "images").mkdir()
    good = ("![Diagram, five setups and where each draws its boundary around the browser and Tor](images/a.png)\n\n<details>\n"
            "<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path, wiki) == ["picture missing: images/a.png"]
    (wiki / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path, wiki)
    assert diagram_problems(good.replace("Diagram, five setups and where each draws its boundary around the browser and Tor", "x"),
                            tmp_path, wiki)
    too_long = "x" * (MAX_ALT + 1)
    assert diagram_problems(good.replace("Diagram, five setups and where each draws its boundary around the browser and Tor",
                                         too_long), tmp_path, wiki)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path, wiki)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("tor browser", "brave", "whonix", "tails", "qubes", "gateway", "workstation", "host", "usb", "ram",
                 "sys-whonix", "dom0", "disposable", "trust boundary", "other apps", "hypervisor", "persistent"):
        assert term in sources, term


def test_every_table_has_a_named_first_header_cell_and_the_guard_bites():
    assert len(tables(text())) >= 7, "the guard collected too few tables"
    assert not unnamed_first_cells(text()), unnamed_first_cells(text())
    assert unnamed_first_cells("| | B |\n|---|---|\n| x | y |\n") == ["| | B |"]
    assert not unnamed_first_cells("| A | B |\n|---|---|\n| x | y |\n")


def test_the_matrix_has_five_setups_against_nine_threats_each_cell_an_answer():
    body = text()
    assert not matrix_problems(body), matrix_problems(body)
    assert matrix_problems(body.replace("| Brave's Tor window | Whonix | Tails |", "| Brave's Tor window | Tails |", 1))
    assert matrix_problems(body.replace("| Your own habits |", "| Your habits |", 1))


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 20, "the page reads twenty outside sources"
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("support.torproject.org", "tb-manual.torproject.org", "support.brave.app", "whonix.org", "tails.net",
                 "doc.qubes-os.org", "kali.org", "parrotsec.org"):
        assert host in sources, host


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_sources_the_issue_names_are_cited_with_their_own_dates_and_words():
    body = text()
    for item in ("Brave does NOT implement most of the privacy protections from Tor Browser", "2026-10-31",
                 "NOT a recommended distribution", "2026-May-14", "Daily Use & Dev", "7.4",
                 "Tails is safe but not magic", "Qubes OS 4.3.2", "silver bullet", "Kicksecure",
                 "Warnings", "letterboxing", "reliant upon the security of the host"):
        assert item in body, item


def test_the_sections_run_in_order_and_each_setup_has_a_threat_model_and_its_limits():
    body = text()
    order = ["## The idea in one paragraph", "## Threat models first", "## The five setups, one at a time",
             "## The matrix: five setups against nine threats", "## Why the browser-only model is weaker than Whonix",
             "## Tails: what it is for, and the daily-system question", "## Kali and ParrotOS: a tool kit and a daily system",
             MAINTAINER_HEADING, "## Choosing: six situations", "## Exercises", "## Checkpoint", "## Common mistakes",
             "## Not verified, plainly", "## Claims register"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)
    for needed in ("### Tor Browser on a normal operating system", "### Brave's Tor window", "### Whonix",
                   "### Tails", "### Qubes with Whonix"):
        assert needed in body, needed
    assert body.count("**Threat model.**") == 5
    assert body.count("**What it does not protect against.**") == 5
    assert body.count("**Cost and fit.**") == 5


def test_the_maintainers_section_is_marked_has_the_joke_and_a_way_out_and_does_not_leak():
    body = text()
    sec = section(body, MAINTAINER_HEADING)
    assert sec, "the maintainer's section is missing"
    assert "This section is the maintainer's opinion" in sec
    assert "not a source" in sec
    low = sec.lower()
    for word in OPINION_WORDS:
        assert word in low, word
    assert "ParrotOS for most of this project" in sec
    assert "What to run instead" in sec and "What to learn first" in sec
    assert "habit" in low
    assert "not a generation" in low, "the joke must say it is not aimed at a generation"
    assert not opinion_outside(body), opinion_outside(body)


def test_the_opinion_guard_bites():
    body = text()
    assert opinion_outside(body + "\nYou are a poser.\n") == ["poser"]
    assert opinion_outside("## A\n\nskid here\n\n" + MAINTAINER_HEADING + "\n\nlarp\n") == ["skid"]
    assert not opinion_outside("## A\n\nplain\n\n" + MAINTAINER_HEADING + "\n\nlarp skid poser\n\n## B\n\nplain\n")


def test_the_page_makes_no_coined_term_claim_and_aims_at_the_habit():
    low = section(text(), MAINTAINER_HEADING).lower()
    for banned in ("coined", "invented the term", "originated the term", "stupid", "idiot", "worthless", "kids these days"):
        assert banned not in low, banned


def test_kali_and_parrot_are_cited_from_their_own_documentation():
    sec = section(text(), "## Kali and ParrotOS: a tool kit and a daily system")
    assert "kali.org/docs/introduction/should-i-use-kali-linux" in text()
    for word in ("virtual machine", "Home", "Security", "Daily Use & Dev", "professional penetration testers"):
        assert word in sec, word
    assert "parrotsec.org/download" in text() and "parrotsec.org/docs/introduction/download-parrot" in text()


def test_the_page_states_nothing_about_this_repositorys_own_security_and_names_no_machine():
    lower = text().lower()
    for banned in ("this repository", "our droplet", "this project's lab", "twingate", "doppler", "spacelift", "hostname",
                   "serial number of"):
        assert banned not in lower, banned


def test_american_spelling_only():
    lower = text().lower()
    for british in ("behaviour", "colour", "defence", "anonymise", "organisation", "favour", "centre ", "licence",
                    "recognise", "minimise", "analyse", "pseudonymise", "catalogue", "sceptic", "grey ", "whilst"):
        assert british not in lower, british


def test_the_page_makes_no_evasion_how_to_or_illegal_content():
    body = text().lower()
    assert "no way around a block, a paywall or a rule" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "evade detection", "bypass the filter", "get around geo",
                   "unblock netflix", "launder", "how to hide from", "step-by-step install", "sudo apt"):
        assert banned not in body
    assert "no onion or i2p service" in body or "no address of any onion or i2p service" in body


def test_the_law_note_tells_learners_to_check_their_jurisdiction():
    body = text()
    assert "Check the law where you live" in body
    assert "nothing here is legal advice" in body.lower()
    assert "No country's law was checked" in body


def test_no_product_is_ranked_best_or_sold():
    lower = text().lower()
    for banned in ("best vpn", "the best browser", "we recommend", "i recommend", "top pick", "buy now", "affiliate link"):
        assert banned not in lower, banned
