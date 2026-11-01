# SPDX-License-Identifier: Apache-2.0
"""The how-Tor-works lesson: registered, honest about what was read, diagrammed, and safe to read.

docs/wiki/How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md teaches the machinery
under Tor with six diagrams. A banner that claims more than was run, a dead link, a missing registration, an onion
address, a claim with no status or date, a diagram with no alt text, no source or no picture, or an unattributed
statement of a number would each teach or reveal the wrong thing.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services"
PAGE = WIKI / f"{NAME}.md"
OVERVIEW = "Tor-I2P-and-the-Darknet-Without-the-Myths"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
STATUS_WORDS = ("Read", "General knowledge", "**est.**")
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
# A long run of base32 or hex characters next to a key-like word is what the repository secret scan flags.
LONG_RANDOM = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


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


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_run():
    body = text()
    assert body.startswith("# How Tor works in depth")
    assert "Status: unverified draft, written from reading" in body
    assert "Nothing on this page was run" in body
    assert "**Not run:**" in body and DATE_READ in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_overview_and_sibling_lessons_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 6, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    assert OVERVIEW in links
    assert "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero" in links
    assert "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys" in links


def test_the_other_series_pages_are_linked_now_that_they_exist():
    body = text()
    links = set(LINK.findall(body))
    for prefix in ("How-a-VPN-Works-", "How-I2P-Works-", "Privacy-Security-and-Anonymity-", "The-Browsing-Setups-Compared-",
                   "OPSEC-for-Tor-and-I2P-", "Detecting-and-Managing-Tor-I2P-and-VPN-", "The-Darknet-Landscape-"):
        found = {t for t in links if t.startswith(prefix)}
        assert found, f"the page {prefix} exists and must be linked"
        assert all((WIKI / f"{t}.md").exists() for t in found), found
    # The stale statements that these pages are written separately and not linked are gone.
    assert "named here in plain text" not in body and "tracked separately" not in body and "Until they exist" not in body


def test_the_lesson_is_registered_in_contents_reading_order_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(l for l in nav.splitlines() if f"page: {NAME}," in l)
    assert 'status: "draft"' in line


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 8, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_no_addresses_onion_names_long_random_values_or_em_dashes():
    body = text()
    assert not ADDR.findall(body), set(ADDR.findall(body))
    assert not ONION.findall(body)
    assert "—" not in body
    # URLs and the register's identifiers are short; a long random-looking run would trip the secret scan.
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)  # link and picture targets are paths, not values
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs


def test_the_address_guard_bites():
    assert ADDR.findall("host 192.0.2.7")
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
    good = "![Diagram, a circuit of three relays and what each knows](images/a.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>"
    assert diagram_problems(good, tmp_path, wiki) == ["picture missing: images/a.png"]
    (wiki / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path, wiki)
    assert diagram_problems(good.replace("Diagram, a circuit of three relays and what each knows", "x"), tmp_path, wiki)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path, wiki)


def test_the_diagrams_cover_the_required_topics():
    body = text()
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(body)).lower()
    for term in ("guard", "middle", "exit", "consensus", "directory authorities", "bridge", "pluggable transport",
                 "introduction points", "rendezvous point", "hsdir"):
        assert term in sources, term
    assert "sequenceDiagram" in body, "the one-request timeline is a sequence diagram"


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 26
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("freehaven.net", "support.torproject.org", "spec.torproject.org", "community.torproject.org",
                 "metrics.torproject.org", "blog.torproject.org", "arxiv.org"):
        assert host in sources, host


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_spec_pages_the_issue_names_are_cited():
    sources = " ".join(r[1] for r in register_rows(text()))
    for page in ("dir-spec", "path-spec", "guard-spec", "vanguards-spec", "rend-spec", "pt-spec", "tor-spec"):
        assert f"spec.torproject.org/{page}/" in sources, page


def test_the_relay_count_is_dated_and_matches_the_register():
    body = text()
    assert "2026-10-29" in body and "9,220" in body and "2,476" in body
    rows = [r for r in register_rows(body) if "9,220" in r[0]]
    assert rows and "metrics.torproject.org" in rows[0][1]


def test_research_claims_are_attributed_to_the_authors_and_dated():
    body = text()
    assert "2015-03-13" in body and "2018-08-22" in body and "2014-07-30" in body
    row = next(r for r in register_rows(body) if "DeepCorr" in r[0])
    assert "abstract" in row[2].lower()
    sentence = next(s for s in re.split(r"(?<=\.)\s+", body) if "96% accuracy" in s)
    assert "in its experiments" in sentence or "authors" in sentence


def test_the_unverified_hop_count_and_guard_count_are_marked():
    body = text()
    assert "**unverified**" in body
    assert body.count("**unverified**") >= 2


def test_the_page_makes_no_marketplace_how_to_or_evasion_content():
    body = text().lower()
    assert "no onion addresses on this page" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "escrow", "evade detection", "bypass the filter"):
        assert banned not in body
    assert "does not tell you how to hide wrongdoing" in body


def test_the_law_note_tells_learners_to_check_their_jurisdiction():
    body = text()
    assert "Check the law where you live" in body
    assert "nothing here is legal advice" in body.lower()


def test_the_threat_model_comes_before_the_machinery():
    body = text()
    order = ["## The short version and the threat model", "## Directory authorities and the consensus",
             "## One circuit, hop by hop", "## Why three hops", "## Why guards persist",
             "## Bridges and pluggable transports", "## Onion services", "## One request, start to finish",
             "## What is known to break Tor, with dates", "## What Tor Browser adds"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)
    assert "## What this means for the series' message" in body
