# SPDX-License-Identifier: Apache-2.0
"""The OPSEC lesson for Tor and I2P: registered, honest about what was read, diagrammed, and safe to read.

docs/wiki/OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits.md is page 6 of the seven-page
series on VPNs, Tor and I2P. It sets the Tor Project's own browsing advice beside the four layers of an identity
(device, network, account, behavior), tells documented cases of mistakes by date and source with no person named,
gives one honest checklist for a beginner and a separate one for a journalist or a person at risk, and points at
organizations that help. A banner that claims more than was done, a dead link, a missing registration, an address
outside the documentation ranges, a claim with no status or date, a diagram with no alt text, no source or no picture,
a layer that lost its leaks, a case that names a person, a checklist that merged into the other, a link to a page
that is not written yet, a link to a page that has a link cap, an extension of the darknet page that repeats it, or
a line that states a security detail about this repository would each teach or reveal the wrong thing.
"""

import json
import re
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits"
PAGE = WIKI / f"{NAME}.md"
DARKNET = WIKI / "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md"
BROWSING = "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix"
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
EXPECTED_DIAGRAMS = 4
DATE_READ = "2026-11-01"
LONG_RANDOM = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
LAYERS = ("Device", "Network", "Account", "Behavior")
RULES = ("Use Tor Browser and software set up for Tor", "Do not sign in as yourself", "Do not torrent over Tor",
         "Do not add extensions or plugins", "Use HTTPS", "Do not open downloaded documents while online",
         "Keep the window at its default size", "Keep the software updated", "Do not reuse an identity across contexts",
         "Do not pick your exit country")
BEGINNER = "## A checklist for a beginner who wants to browse privately"
AT_RISK = "## A checklist for a journalist or a person at risk"
HELPERS = ("accessnow.org", "ssd.eff.org", "freedom.press", "digitalfirstaid.org", "cpj.org", "securityinabox.org")
PEOPLE = ("Ulbricht", "Eldo", "McAfee", "Cazes", "Dread Pirate", "Roberts")


def text() -> str:
    return page_text(PAGE)


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


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    return body[start:].split("\n## ", 1)[0]


def table_in(body: str, heading: str) -> list[list[str]]:
    block = next(iter(tables(section(body, heading))), None)
    assert block is not None, f"no table under {heading}"
    return [[c.strip() for c in r.strip("|").split("|")] for r in block[1:]]


def layer_problems(body: str) -> list[str]:
    """The layers table has the four layers in order and every row says what leaks and what Tor or I2P changes."""
    rows = table_in(body, "## The four layers of an identity")
    problems = []
    if [r[0].split(":")[-1].strip() for r in rows] != list(LAYERS):
        problems.append(f"layers are {[r[0] for r in rows]}")
    for r in rows:
        if len(r) != 4 or any(len(c) < 30 for c in r[1:]):
            problems.append(f"thin row: {r[0]}")
    return problems


def rule_problems(body: str) -> list[str]:
    rows = table_in(body, "## The Tor Project's own advice, one rule at a time")
    problems = []
    if [r[0] for r in rows] != list(RULES):
        problems.append(f"rules are {[r[0] for r in rows]}")
    for r in rows:
        if len(r) != 4 or not URL.search(r[3]) or DATE_READ not in r[3]:
            problems.append(f"rule without a dated source: {r[0]}")
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


def names_a_person(body: str) -> list[str]:
    return [p for p in PEOPLE if re.search(rf"\b{re.escape(p)}\b", body)]


def checklist_items(body: str, heading: str) -> list[str]:
    return [ln for ln in section(body, heading).splitlines() if re.match(r"^\d+\. ", ln)]


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# OPSEC for Tor and I2P that holds up")
    assert "Page 6 of a seven-page series" in body
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and DATE_READ in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_finished_siblings_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 10, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        OVERVIEW, BROWSING,
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves",
        "Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Threat-Model",
    ):
        assert needed in links, needed


def test_the_detecting_page_is_linked_now_that_it_exists():
    body = text()
    assert "detecting and managing Tor, I2P and VPN traffic on a network" in body
    found = {t for t in LINK.findall(body) if t.startswith("Detecting-and-Managing-Tor-I2P-and-VPN-")}
    assert found, "the series page 7 exists and must be linked"
    assert all((WIKI / f"{t}.md").exists() for t in found), found
    # The stale statement that the last page is not written yet is gone.
    assert "The last page is not written yet" not in body


def test_the_whonix_and_qubes_exercises_are_still_named_in_plain_text_not_linked():
    # Issue 372 is not written, so there is no page to link; this stays plain text until there is.
    body = text()
    assert "hands-on Whonix and Qubes exercises" in body
    linked = {t for t in LINK.findall(body) if re.search(r"Exercise", t)}
    assert not linked, linked


def test_a_page_with_a_link_cap_is_not_linked():
    # tests/test_blast_radius_lesson.py caps how many pages may link that lesson, and the cap is full.
    assert "Plan-for-Failure-Blast-Radius" not in text()


def test_the_lesson_is_registered_in_contents_reading_order_and_nav_after_the_browsing_page():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    lines = nav.splitlines()
    idx = next(i for i, row in enumerate(lines) if f"page: {NAME}," in row)
    assert f"page: {BROWSING}," in lines[idx - 1], "the page follows the browsing setups page in the track"
    assert 'status: "draft"' in lines[idx] and 'subgroup: "Tor, I2P, VPN and browsing"' in lines[idx]
    related = re.search(r"related: \[([^\]]*)\]", lines[idx]).group(1).split(", ")
    assert 3 <= len(related) <= 6, related
    assert all((WIKI / f"{r}.md").exists() for r in related), related


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    terms = []
    glossary = (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines()
    for line in glossary:
        if f"{NAME}.md" in line:
            terms.append(line.split("|")[1].strip().strip("*").lower())
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert len(terms) >= 4, "expected glossary rows for the new terms"
    assert len(set(terms)) == len(terms), "a glossary term is defined twice"
    every = [ln.split("|")[1].strip().strip("*").lower() for ln in glossary if ln.startswith("| **")]
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
    alt = "Diagram, the four layers of an identity and where each one leaks when you use Tor or I2P"
    good = (f"![{alt}](images/a.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\n"
            "flowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path, wiki) == ["picture missing: images/a.png"]
    (wiki / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path, wiki)
    assert diagram_problems(good.replace(alt, "x"), tmp_path, wiki)
    assert diagram_problems(good.replace(alt, "x" * (MAX_ALT + 1)), tmp_path, wiki)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path, wiki)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("device", "network", "account", "behavior", "fingerprint", "metadata", "ip address", "login",
                 "writing style", "timing", "new identity", "separate", "restart", "threat model", "helpline"):
        assert term in sources, term


def test_every_table_has_a_named_first_header_cell_and_the_guard_bites():
    assert len(tables(text())) >= 6, "the guard collected too few tables"
    assert not unnamed_first_cells(text()), unnamed_first_cells(text())
    assert unnamed_first_cells("| | B |\n|---|---|\n| x | y |\n") == ["| | B |"]
    assert not unnamed_first_cells("| A | B |\n|---|---|\n| x | y |\n")


def test_the_layers_table_has_four_layers_each_with_leaks_and_what_tor_or_i2p_changes():
    body = text()
    assert not layer_problems(body), layer_problems(body)
    assert layer_problems(body.replace("| Layer 3: Account |", "| Layer 3: Login |", 1))
    sec = section(body, "## The four layers of an identity")
    for word in ("Tor and I2P act here", "You act here", "ISP"):
        assert word in sec, word


def test_the_tor_projects_rules_are_all_present_each_with_a_dated_source():
    body = text()
    assert not rule_problems(body), rule_problems(body)
    assert rule_problems(body.replace("| Do not torrent over Tor |", "| Torrent as you like |", 1))
    sec = section(body, "## The Tor Project's own advice, one rule at a time")
    for word in ("support.torproject.org", "tb-manual.torproject.org", "letterboxing", "strongly discouraged",
                 "must be kept updated", "practically impossible"):
        assert word in sec, word
    # The series plan's wording and the Tor Project's wording are told apart.
    assert "the series plan's wording" in sec.lower() or "wording of the series plan" in sec.lower()


def test_the_login_exception_is_stated_with_its_example():
    sec = section(text(), "## Logins: the exception and what it costs")
    assert "censored" in sec and "unless" in sec.lower()
    assert "they know who you are" in sec


def test_the_cases_have_a_date_a_layer_and_a_source_and_name_no_person():
    body = text()
    rows = table_in(body, "## Documented mistakes, by date and source")
    assert len(rows) >= 3, "the guard collected too few cases"
    for r in rows:
        assert len(r) == 5, r
        assert re.search(r"\b20\d\d\b", r[0]), r[0]
        assert any(layer in r[2] for layer in LAYERS), r[2]
        assert URL.search(r[4]) and DATE_READ in r[4], r[0]
    assert not names_a_person(body), names_a_person(body)
    assert names_a_person("a man named Eldo") == ["Eldo"]
    assert not names_a_person("the Second Circuit opinion")
    sec = section(body, "## Documented mistakes, by date and source")
    for word in ("allegation", "secondary", "Not read"):
        assert word in sec, word


def test_the_darknet_page_is_extended_not_duplicated():
    darknet = page_text(DARKNET)
    assert f"({NAME}.md" in darknet, "the darknet page points at this page from its OPSEC section"
    trap = section(darknet, "## The OPSEC trap: perfect technique without a threat model")
    assert f"({NAME}.md" in trap
    mine = text()
    assert "## The OPSEC trap: perfect technique without a threat model" not in mine
    assert "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md#the-opsec-trap" in mine
    # None of the darknet page's four-principle table rows is copied here.
    assert "### Four general principles, seen in public cases" not in mine


def test_the_two_checklists_are_separate_and_each_item_is_a_numbered_action():
    body = text()
    assert body.index(BEGINNER) < body.index(AT_RISK)
    beginner, risk = checklist_items(body, BEGINNER), checklist_items(body, AT_RISK)
    assert len(beginner) >= 8 and len(risk) >= 8, (len(beginner), len(risk))
    low = section(body, BEGINNER).lower()
    for word in ("qubes", "whonix", "tails"):
        assert word not in low, f"the beginner list stays simple: {word}"
    risk_low = section(body, AT_RISK).lower()
    for word in ("threat model", "trainer", "helpline", "one purpose"):
        assert word in risk_low, word
    assert "does not replace" in risk_low
    assert checklist_items("## X\n\n1. a\n2. b\n", "## X") == ["1. a", "2. b"]


def test_the_helpers_are_named_with_what_each_one_says_about_itself_and_the_date_read():
    sec = section(text(), "## Organizations that help people at risk")
    for host in HELPERS:
        assert host in sec, host
    assert sec.count(DATE_READ) >= 6
    for word in ("free-of-charge", "24/7", "two hours", "Digital First Aid Kit", "Safety Kit"):
        assert word in sec or word.lower() in sec.lower(), word


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 20, "the page reads twenty outside sources"
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("support.torproject.org", "tb-manual.torproject.org", "tails.net", "geti2p.net", "ssd.eff.org",
                 "accessnow.org", "freedom.press", "digitalfirstaid.org", "cpj.org", "securityinabox.org",
                 "nbcnews.com", "arxiv.org", "law.justia.com"):
        assert host in sources, host


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_sources_are_cited_with_their_own_words_and_dates():
    body = text()
    for item in ("Generally it is impossible to have perfect anonymity", "Torrent file-sharing applications have been observed",
                 "DO NOT IGNORE THIS WARNING", "Last Reviewed: January 28, 2025", "Tails is safe but not magic",
                 "2012-12-04", "2013-12-18", "2017-05-31", "round-trip translation", "free route mixnet",
                 "separate Firefox profile", "mat2", "It is impossible to reliably find and remove all metadata",
                 "Seven Steps To Digital Security", "Simpler is Safer"):
        assert item in body, item


def test_the_sections_run_in_order():
    body = text()
    order = ["## The idea in one paragraph", "## Threat model first, then tools",
             "## The four layers of an identity", "## The Tor Project's own advice, one rule at a time",
             "## One identity per compartment", "## Logins: the exception and what it costs",
             "## Files, photos and metadata", "## Writing style and timing", "## I2P: the same habits, a different pipe",
             "## Documented mistakes, by date and source", "## OPSEC theater: effort with no threat model",
             BEGINNER, AT_RISK, "## Organizations that help people at risk", "## Exercises", "## Checkpoint",
             "## Common mistakes", "## Not verified, plainly", "## Claims register"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)


def test_the_page_carries_no_maintainer_opinion_or_badge_commentary():
    low = text().lower()
    for banned in ("larp", "skid", "poser", "badge", "the maintainer's view", "starter pack"):
        assert banned not in low, banned


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
    for banned in ("buy drugs", "vendor shop", "how to buy", "evade", "bypass the filter", "get around geo",
                   "unblock netflix", "launder", "how to hide from", "step-by-step install", "sudo apt",
                   "avoid law enforcement", "avoid detection"):
        assert banned not in body, banned
    assert "no address of any onion or i2p service" in body


def test_the_law_note_tells_learners_to_check_their_jurisdiction():
    body = text()
    assert "Check the law where you live" in body
    assert "nothing here is legal advice" in body.lower()
    assert "No country's law was checked" in body


def test_no_product_is_ranked_best_or_sold():
    lower = text().lower()
    for banned in ("best vpn", "the best browser", "we recommend", "i recommend", "top pick", "buy now", "affiliate link"):
        assert banned not in lower, banned
