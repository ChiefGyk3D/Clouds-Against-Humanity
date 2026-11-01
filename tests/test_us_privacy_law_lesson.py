# SPDX-License-Identifier: Apache-2.0
"""The US privacy law lesson: registered, honest about what was read and run, diagrams intact, facts checked.

docs/wiki/US-Privacy-Law-No-General-Right-the-Patchwork-Data-Brokers-Social-Security-Numbers-and-License-Plate-Readers.md
is page 2 of the three-page GRC and compliance set (issue 403). A banner that claims more than was done, a dead link, a
missing registration, a diagram with no picture or the wrong shape, a register row with no URL and no date, an opinion
that leaks into the factual part, an opinion section that presents itself as fact, a comparison with China that blurs
protection from companies and protection from the state, a table of state laws that does not add up, a named person in
the license plate reader section, or a statement about this repository's own settings would each teach or reveal the
wrong thing.
"""

import json
import re
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "US-Privacy-Law-No-General-Right-the-Patchwork-Data-Brokers-Social-Security-Numbers-and-License-Plate-Readers"
PAGE = WIKI / f"{NAME}.md"
GRC1 = "GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
READ_ON = date(2026, 11, 1)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
BRITISH = ("defence", "behaviour", "colour", "organisation", "centre", "licence", "programme", "analyse", "favour", "realise")
OPINION = "## The maintainer's view (on his soap box)"
EXERCISE = "## Free exercise: which laws apply, and a broker's published process"
LAWS = "## The federal laws and the FTC in one table"
STATES = "### Comprehensive state laws"
ALPR = "## License plate readers and Flock"
# Names of people who appear in the sources about license plate readers. The page names none of them.
PEOPLE = ("Langley", "Adam King", "Giannoulias", "Schmidt", "Arrington", "Talbot", "Frommer", "Freeman", "Daggett")


def british_words(body: str) -> list[str]:
    """Whole words only, so the plural 'analyses' (correct in American English) is not caught."""
    return sorted(w for w in BRITISH if re.search(rf"\b{w}\b", body))


def named_people(body: str) -> list[str]:
    return sorted(p for p in PEOPLE if p in body)


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
    stop = re.search(rf"\n#{{1,{level}}} ", rest)
    return rest[: stop.start()] if stop else rest


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def sourced_rows_without_url_and_date(body: str) -> list[str]:
    exempt = ("The maintainer's framing", "The author's own", "General knowledge", "Constructed by the author")
    bad = []
    for row in register_rows(body):
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


def too_tall(width: int, height: int) -> bool:
    return height > 1.6 * width


POSTURE = (
    r"required_approving_review_count",
    r"required approving review",
    r"enforce_admins",
    r"branch protection",
    r"branch rule",
    r"stale reviews",
    r"no human approval",
    r"github api",
    r"gh api",
)


def posture_phrases(body: str) -> list[str]:
    """Statements of this repository's own branch-protection settings must not be published."""
    return [p for p in POSTURE if re.search(p, body, re.IGNORECASE)]


def in_force(rows: list[list[str]], on: date) -> list[str]:
    """States whose ISO effective date (third column) is on or before the given day."""
    return [r[0] for r in rows if date.fromisoformat(r[2]) <= on]


def glossary_terms() -> list[str]:
    terms = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \*\*(.+?)\*\*", line)
        if m:
            terms.append(re.sub(r"\s*\(basics\)\s*", "", m.group(1)).strip().lower())
    return terms


def duplicates(terms: list[str]) -> list[str]:
    return sorted({t for t in terms if terms.count(t) > 1})


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_not_run():
    body = text()
    assert body.startswith("# US privacy law")
    assert "Status: unverified draft, written from reading" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    assert "Page two of three" in body and "issue 403" in body


def test_education_not_legal_advice_is_said_once_and_briefly():
    body = text().lower()
    assert body.count("not legal advice") == 1
    assert "legal advice" in body.split("## what you will be able to do")[0], "said up front, not buried"


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 5, "the guard collected too few links"
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
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cross-Tenant-Data-Governance-Retention-and-DLP",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Hashing-Encryption-and-Keys",
        "The-CIA-Triad-Confidentiality-Integrity-Availability",
    ):
        assert needed in links, needed
    for issue in ("402", "403", "404"):
        assert issue in body, f"issue {issue} is named"
    # Page one is linked once it is in the wiki and named in plain text until then.
    if (WIKI / f"{GRC1}.md").exists():
        assert GRC1 in links, "page one is merged, so it is linked"
    else:
        assert GRC1 not in links and "GRC in plain terms" in body


def test_the_lesson_is_registered_in_contents_reading_order_home_sidebar_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line, "the banner says unverified draft"


def test_glossary_rows_point_at_real_headings_and_no_term_is_defined_twice():
    heads = headings(text())
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 10, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    mine = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \*\*(.+?)\*\*", line)
        if m and f"{NAME}.md" in line:
            mine.append(m.group(1).strip().lower())
    assert len(mine) >= 10
    every = glossary_terms()
    assert not [t for t in mine if every.count(t) > 1], "a new term is defined twice"


def test_the_duplicate_guard_bites():
    assert duplicates(["ftc", "alpr", "ftc"]) == ["ftc"]
    assert not duplicates(["ftc", "alpr", "fcra"])


def test_american_spelling_no_em_dashes_no_ip_addresses_and_no_employer_or_contribution_talk():
    body = text()
    low = body.lower()
    assert "—" not in body
    assert not IPV4.findall(body), IPV4.findall(body)
    assert not british_words(low), british_words(low)
    assert "privacy" in low, "the guard collected nothing"
    for banned in ("my employer", "his employer", "the maintainer's employer", "maintainer's contributions", "his contributions"):
        assert banned not in low, banned


def test_the_spelling_guard_bites():
    assert british_words("the organisation's defence") == ["defence", "organisation"]
    assert not british_words("the organization's defense and impact analyses")


def test_every_table_has_a_named_first_header_cell():
    bad = []
    lines = text().splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and lines[i + 1].startswith("|---") and (i == 0 or not lines[i - 1].startswith("|")):
            first = line.strip("|").split("|")[0].strip()
            if not first:
                bad.append(i + 1)
    assert not bad, bad


# ---- diagrams ------------------------------------------------------------------------------------------------------


def test_every_diagram_has_alt_text_a_source_a_picture_and_a_wide_shape():
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
        assert m["src"].lstrip().startswith("flowchart"), m["path"]
        width, height = png_size(png)
        assert not too_tall(width, height), (m["path"], width, height)


def test_the_diagram_guards_bite():
    bare = "![alt text here](images/x.png)\n\nno details block, so no source\n"
    assert not WRAPPED.search(bare)
    good = "![alt text here](images/x.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n  a --> b\n```\n\n</details>"
    assert WRAPPED.search(good)
    assert not WRAPPED.search(good.replace("<details>\n", ""))
    assert too_tall(100, 161) and not too_tall(100, 160)


def test_the_diagrams_cover_the_three_topics_the_issue_asks_for():
    alts = [m["alt"].lower() for m in WRAPPED.finditer(text())]
    assert len(alts) == 3
    assert "patchwork" in alts[0] and "state" in alts[0]
    assert "broker" in alts[1] and "buyer" in alts[1]
    assert "social security" in alts[2]


# ---- the register --------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 40, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "supremecourt.gov/opinions/17pdf/16-402",
        "tile.loc.gov/storage-services/service/ll/usrep/usrep389/usrep389347",
        "usrep442/usrep442735",
        "usrep565/usrep565400",
        "usrep381/usrep381479",
        "usrep429/usrep429589",
        "supremecourt.gov/opinions/21pdf/19-1392",
        "CDOC-110hdoc50",
        "USCODE-2023-title5-partI-chap5-subchapII-sec552a",
        "USCODE-2023-title18-partI-chap119-sec2511",
        "USCODE-2023-title18-partI-chap121-sec2701",
        "USCODE-2023-title18-partI-chap121-sec2710",
        "USCODE-2023-title18-partI-chap123-sec2721",
        "USCODE-2023-title15-chap91-sec6502",
        "USCODE-2023-title20-chap31-subchapIII-part4-sec1232g",
        "USCODE-2023-title15-chap41-subchapIII-sec1681b",
        "USCODE-2023-title15-chap94-subchapI-sec6802",
        "USCODE-2023-title15-chap2-subchapI-sec45",
        "USCODE-2023-title42-chap156-subchapIII-partA-sec17932",
        "USCODE-2023-title42-chap7-subchapXI-partC-sec1320d-5",
        "ecfr.gov/current/title-45/part-160",
        "iapp.org/resources/article/us-state-privacy-legislation-tracker",
        "oag.ca.gov/privacy/ccpa",
        "cppa.ca.gov/regulations/pdf/data_broker_reg_delete_act_statute_eff_20260101",
        "legislature.vermont.gov/statutes/section/09/062/02446",
        "illinoiscourts.gov/Opinions/SupremeCourt/2019/123186",
        "app.leg.wa.gov/RCW",
        "ncsl.org/technology-and-communication/security-breach-notification-laws",
        "ftc.gov/news-events/news/press-releases/2022/08",
        "ftc.gov/news-events/news/press-releases/2024/01",
        "140527databrokerreport",
        "federalregister.gov/documents/2024/12/13",
        "federalregister.gov/documents/2025/05/15",
        "USCODE-2024-title15-chap123-sec9901",
        "ssa.gov/policy/docs/ssb/v69n2/v69n2p55",
        "ssa.gov/employer/randomization",
        "ssa.gov/pubs/EN-05-10064",
        "cms.gov/medicare/new-medicare-card",
        "pubmed.ncbi.nlm.nih.gov/19581585",
        "auditor.ca.gov/pdfs/reports/2019-118",
        "flocksafety.com/legal/lpr-policy",
        "flocksafety.com/trust/myths-facts",
        "flocksafety.com/blog/flock-guardrails-address-lpr-privacy-concerns-and-police-transparency",
        "flocksafety.com/blog/flock-safetys-response-to-illinois-lpr-data-use-and-out-of-state-sharing-concerns",
        "law.lis.virginia.gov/vacode/title2.2/chapter55.6/section2.2-5517",
        "npr.org/2026/02/17",
        "arstechnica.com/tech-policy/2024/10",
        "dallasnews.com/news/texas/2025/06/13",
        "eff.org/deeplinks/2025/10",
        "404media.co/a-texas-cop-searched",
        "digichina.stanford.edu/work/translation-personal-information-protection-law",
        "chinalawtranslate.com/en/national-intelligence-law",
        "digichina.stanford.edu/work/translation-cybersecurity-law",
        "cac.gov.cn/2022-07/21",
        "merics.org/en/report/chinas-social-credit-system-2021",
        "chinacopyrightandmedia.wordpress.com/2014/06/14",
        "ohchr.org/sites/default/files/documents/countries/2022-08-31",
        "consumer.risk.lexisnexis.com",
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


# ---- the Constitution and the cases --------------------------------------------------------------------------------


def test_the_constitution_section_quotes_the_cases_and_dates_them():
    part = section(text(), "## What the Constitution does and does not say about privacy")
    assert "does not appear" in part and "House Document 110-50" in part
    assert "cannot be translated into a general constitutional" in part, "the Katz sentence is quoted"
    rows = table_rows(part)
    cases = {r[0]: r for r in rows if "U.S." in " ".join(r)}
    assert len(rows) >= 6, "the guard collected too few cases"
    for key, cite, year in (
        ("Griswold", "381 U.S. 479", "1965"),
        ("Katz", "389 U.S. 347", "1967"),
        ("Whalen", "429 U.S. 589", "1977"),
        ("Smith", "442 U.S. 735", "1979"),
        ("Jones", "565 U.S. 400", "2012"),
        ("Carpenter", "585 U.S.", "2018"),
    ):
        row = next((r for name, r in cases.items() if key in name), None)
        assert row is not None, key
        joined = " ".join(row)
        assert cite in joined and year in joined, (key, row)
    for needed in ("127 days", "narrow", "June 24, 2022", "California", "inalienable", "Proposition 7"):
        assert needed in part, needed
    assert "Dobbs" in part


# ---- the federal laws ----------------------------------------------------------------------------------------------


def test_the_federal_law_table_has_every_law_with_its_year_and_five_filled_columns():
    part = section(text(), LAWS)
    rows = table_rows(part)
    by_name = {r[0]: r for r in rows}
    assert len(rows) >= 13, "the guard collected too few laws"
    for r in rows:
        assert len(r) == 6 and all(len(c) > 3 for c in r), r
    expect = {
        "FCRA": "1970",
        "Privacy Act": "1974",
        "FERPA": "1974",
        "ECPA": "1968",
        "Stored Communications Act": "1986",
        "VPPA": "1988",
        "DPPA": "1994",
        "HIPAA": "1996",
        "COPPA": "1998",
        "GLBA": "1999",
        "HITECH": "2009",
        "SOX": "2002",
        "FTC Act": "1914",
    }
    for key, year in expect.items():
        row = next((r for name, r in by_name.items() if key in name), None)
        assert row is not None, key
        assert year in row[1], (key, row[1])
    sox = next(r for name, r in by_name.items() if "SOX" in name)
    assert "not a privacy law" in " ".join(sox).lower(), "SOX is said plainly to be financial-controls law"
    assert "banks" in " ".join(next(r for name, r in by_name.items() if "FTC Act" in name)).lower(), "the FTC Act limit is stated"


def test_hipaa_and_hitech_numbers_come_from_the_texts():
    part = section(text(), "## HIPAA and HITECH, a little closer")
    for needed in ("$100", "$50,000", "$1,500,000", "60 calendar days", "February 17, 2009", "45 CFR 160.404", "covered entit"):
        assert needed in part, needed


# ---- the states ----------------------------------------------------------------------------------------------------


def test_the_state_table_matches_the_tracker_and_the_in_force_count_is_computed_from_dates():
    part = section(text(), STATES)
    rows = table_rows(part)
    assert len(rows) == 23, len(rows)
    names = [r[0] for r in rows]
    assert names == sorted(names), "the table is in alphabetical order"
    for state in ("California", "Colorado", "Connecticut", "Texas", "Virginia", "Utah", "Vermont", "Alabama", "Louisiana", "Oklahoma"):
        assert state in names, state
    now = in_force(rows, READ_ON)
    not_yet = sorted(set(names) - set(now))
    assert len(now) == 19 and not_yet == ["Alabama", "Louisiana", "Oklahoma", "Vermont"], (len(now), not_yet)
    for r in rows:
        assert ("yes" if r[0] in now else "not yet") == r[3].lower(), r
    assert "19" in part and "23" in part and "2026-09-08" in part
    cal = next(r for r in rows if r[0] == "California")
    assert cal[2] == "2020-01-01"


def test_the_state_table_guard_bites():
    fake = [["A", "x", "2026-10-31", "yes"], ["B", "y", "2026-11-02", "not yet"], ["C", "z", "2026-11-01", "yes"]]
    assert in_force(fake, READ_ON) == ["A", "C"]


def test_california_biometric_breach_and_health_data_facts():
    part = section(text(), "## The states")
    for needed in (
        "$25 million",
        "100,000",
        "$750",
        "Proposition 24",
        "January 1, 2023",
        "$1,000",
        "$5,000",
        "January 25, 2019",
        "Washington My Health My Data",
        "Consumer Protection Act",
        "All 50 states",
        "January 17, 2022",
    ):
        assert needed in part, needed


# ---- data brokers --------------------------------------------------------------------------------------------------


def test_the_data_broker_section_carries_the_dated_actions_and_the_deletion_rules():
    part = section(text(), "## Data brokers")
    for needed in (
        "May 2014",
        "nine data brokers",
        "August 29, 2022",
        "January 9, 2024",
        "December 13, 2024",
        "May 15, 2025",
        "April 24, 2024",
        "January 8, 2025",
        "April 8, 2025",
        "January 1, 2026",
        "August 1, 2026",
        "45 days",
        "$100",
        "$900",
        "January 1, 2027",
        "1798.99.80",
        "proposed",
        "I did not check",
    ):
        assert needed in part, needed
    # The data flow, in words, matches the diagram that follows.
    assert "a person" in part.lower() and "buyer" in part.lower()


# ---- Social Security numbers ---------------------------------------------------------------------------------------


def test_the_ssn_timeline_is_in_order_and_cites_the_ssa_texts():
    part = section(text(), "## Social Security numbers")
    for needed in (
        "1936",
        "Executive Order 9397",
        "June 25, 2011",
        "never intended to serve as a personal identification document",
        "13478",
        "Section 7 of the Privacy Act",
        "420 million",
        "147 million",
        "March 2026",
        "Medicare Beneficiary Identifier",
    ):
        assert needed in part, needed
    rows = table_rows(section(part, "### How the number drifted"))
    years = [int(re.match(r"\d{4}", r[0]).group(0)) for r in rows]
    assert len(years) >= 10, "the guard collected too few events"
    assert years == sorted(years), years
    for link in ("Cryptography-Fundamentals", "Hashing-Encryption-and-Keys"):
        assert link in part, link


# ---- license plate readers and Flock -------------------------------------------------------------------------------


def test_the_alpr_section_separates_established_from_contested_and_names_nobody():
    part = section(text(), ALPR)
    assert "Established" in part and "Contested" in part
    est = section(part, "### What is established, and what is contested")
    rows = table_rows(est)
    assert len(rows) >= 8, "the guard collected too few statements"
    labels = {r[1] for r in rows}
    assert labels <= {"Established", "Contested", "Not established"}, labels
    assert {"Established", "Contested"} <= labels
    for r in rows:
        assert re.search(r"20\d\d", r[2]) and URL.search(r[3]), f"no date or source: {r[0]}"
    for needed in (
        "21 days",
        "2.2-5517",
        "99.9 percent",
        "320 million",
        "February 2020",
        "7 days",
        "30 days",
        "August 13, 2026",
        "June 30, 2026",
        "June 12, 2025",
        "October 2024",
        "I did not find a decision",
    ):
        assert needed in part, needed
    assert not named_people(text()), named_people(text())


def test_the_people_guard_bites():
    assert named_people("the sheriff Adam King said") == ["Adam King"]
    assert not named_people("the county sheriff's office said")


CERT_VIEW = "In my view, a certification or an attestation report is only a snapshot"
CERT_NOTE = "depends on its scope and criteria, which public reporting does not settle"


def test_the_certification_view_sits_only_in_the_opinion_section_and_no_would_fail_claim_is_made():
    body = text()
    op = section(body, OPINION)
    assert body.count(CERT_VIEW) == 1 and CERT_VIEW in op, "the view is in the opinion section and nowhere else"
    assert CERT_NOTE in op and "no source I read says that firm failed" in op
    low = body.lower()
    for claim in ("would fail", "did fail", "has failed", "failed a soc 2", "failed its soc 2"):
        assert claim not in low, claim
    assert f"{GRC1}.md#what-a-certification-or-report-does-and-does-not-tell-you" in op, "page one's section is linked"
    assert not named_people(op)
    assert "I read no source on the exposure itself" not in body, "page one now carries sources on the exposure"
    assert "the sourced account of the exposure with what is and is not known about it" in op


def test_the_certification_guard_bites():
    outside = "facts. " + CERT_VIEW + " more"
    assert outside.count(CERT_VIEW) == 1 and CERT_VIEW not in "## x\nopinion only"
    assert "would fail" in "the firm would fail a SOC 2".lower()


# ---- the opinion ---------------------------------------------------------------------------------------------------


def test_the_opinion_section_is_clearly_headed_comes_after_the_facts_and_is_not_presented_as_fact():
    body = text()
    assert body.count(OPINION) == 1
    assert body.index(ALPR) < body.index(OPINION) < body.index(EXERCISE)
    facts = body.split(OPINION)[0].lower()
    for banned in ("in my opinion", "i believe", "soap box", "the maintainer's view"):
        assert banned not in facts, banned
    op = section(body, OPINION)
    low = op.lower()
    assert "soap box" in low and "his view" in low
    assert "opinion, not established fact" in low
    assert low.count("**point ") == 4, "four points, as the issue lists them"
    assert low.count("what the sources say") >= 4, "each point sits next to what the sources say"
    for needed in ("no right to privacy", "a dollar", "Social Security numbers should not be used as ID"):
        assert needed.lower() in low, needed


def test_the_china_comparison_is_about_companies_and_not_the_state_and_is_cited_with_articles():
    op = section(text(), OPINION)
    for needed in (
        "Personal Information Protection Law",
        "August 20, 2021",
        "November 1, 2021",
        "Article 33",
        "Article 34",
        "Article 35",
        "Article 66",
        "50 million",
        "National Intelligence Law",
        "Article 7",
        "Cybersecurity Law",
        "Article 28",
        "protection from companies, not from the state",
        "DiDi",
        "July 21, 2022",
        "August 31, 2022",
        "no single",
    ):
        assert needed in op, needed
    low = op.lower()
    assert "does not restrain the state" not in low, "the text of Articles 33 to 37 does bind state organs a little, so the page says what it does say"
    assert "exceptions" in low


def test_the_opinion_words_stay_out_of_the_laws_and_flock_sections():
    body = text()
    for heading in (LAWS, ALPR, "## Social Security numbers", "## Data brokers"):
        sec = section(body, heading).lower()
        for word in ("outrageous", "scandal", "disgrace", "should be banned", "dystopian"):
            assert word not in sec, (heading, word)


# ---- the exercise and the repository -------------------------------------------------------------------------------


def test_the_exercise_has_both_parts_a_worked_answer_and_says_what_was_not_run():
    ex = section(text(), EXERCISE)
    for needed in ("Part A", "Part B", "Not run", "do not submit", "answer key", "Texas", "location data"):
        assert needed.lower() in ex.lower(), needed
    assert "LexisNexis" in ex and "FACT Act" in ex
    assert "Washington" in ex


def test_no_security_posture_detail_of_this_repository_is_on_the_page_and_the_guard_bites():
    body = text()
    assert "privacy" in body.lower(), "the guard collected nothing"
    assert not posture_phrases(body), posture_phrases(body)
    for leaked in ("enforce_admins false", "the branch protection on main", "required approving review count"):
        assert posture_phrases(leaked), leaked
    assert not posture_phrases("check whether a review is required in your own system")


def test_the_repository_paths_the_page_cites_exist():
    body = text()
    cited = set(re.findall(r"`((?:scripts|\.github/workflows|tests|docs)/[A-Za-z0-9_./-]+)`", body))
    missing = sorted(p for p in cited if not (ROOT / p).exists())
    assert not missing, missing
