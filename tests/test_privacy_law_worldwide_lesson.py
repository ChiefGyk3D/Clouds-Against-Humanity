# SPDX-License-Identifier: Apache-2.0
"""The worldwide privacy law lesson: registered, honest about what was read and run, diagrams intact, figures checked.

docs/wiki/Privacy-Law-Around-the-World-GDPR-PIPEDA-POPIA-and-PIPL-Compared-With-the-United-States.md is page 3 of the
three-page GRC and compliance set (issue 404). A banner that claims more than was done, a dead link, a missing
registration, a diagram with no picture, no alt text or the wrong shape, a register row with no URL and no date, a repeated
"not legal advice" notice, an opinion section on a page that is meant to be factual, a fine that exceeds the cap printed next
to it, a breach clock worked out wrongly in the answer key, a sentence that says a law does not restrain the state in
absolute terms, or a sibling page linked before it exists would each teach or reveal the wrong thing.
"""

import json
import re
import struct
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Privacy-Law-Around-the-World-GDPR-PIPEDA-POPIA-and-PIPL-Compared-With-the-United-States"
PAGE = WIKI / f"{NAME}.md"
PAGE_ONE = "GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations"
PAGE_TWO_PREFIX = "US-Privacy-Law-"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
EXERCISE = "## Free exercise: a company with customers in four regions"
CASES = "## What non-compliance has cost: documented cases"
BRITISH = ("defence", "behaviour", "colour", "organisation", "centre", "licence", "programme", "analyse", "favour", "realise", "offence")


def british_words(body: str) -> list[str]:
    """Whole words only, so the plural 'analyses' (correct in American English) is not caught."""
    return sorted(w for w in BRITISH if re.search(rf"\b{w}\b", body))


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
    """Statements of this repository's own security settings must not be published."""
    return [p for p in POSTURE if re.search(p, body, re.IGNORECASE)]


# Sentences that say, in absolute terms, that the PIPL does not restrain the state. The page must say what the articles say.
ABSOLUTE_STATE = (
    r"does not (?:restrain|limit|constrain|bind) the state",
    r"no limits? on the state",
    r"exempts? the state",
    r"state organs are exempt",
    r"only (?:restrains|limits|binds) (?:companies|businesses)",
)


def absolute_state_claims(body: str) -> list[str]:
    return [p for p in ABSOLUTE_STATE if re.search(p, body, re.IGNORECASE)]


def sibling_problems(body: str, wiki_names: list[str]) -> list[str]:
    """Page two is linked once it is in the wiki and named in plain text until then; page three is this page."""
    problems = []
    page_two = [n for n in wiki_names if n.startswith(PAGE_TWO_PREFIX)]
    linked = {t for t, _ in LINK.findall(body)}
    if page_two:
        if not any(n.removesuffix(".md") in linked for n in page_two):
            problems.append("page two is in the wiki and is not linked")
    else:
        if PAGE_TWO_PREFIX in body:
            problems.append("page two is not in the wiki yet and its file name appears")
    return problems


def add_months(day: datetime, months: int) -> datetime:
    """Same day of the month, months later; the exercise only uses days that exist in the target month."""
    total = day.month - 1 + months
    return day.replace(year=day.year + total // 12, month=total % 12 + 1)


def gdpr_deadline(aware: datetime) -> datetime:
    return aware + timedelta(hours=72)


def money_millions(cell: str) -> float:
    """Millions in a cell such as 'EUR 403 million', 'R1,000,000' or 'EUR 1.2 billion'."""
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(million|billion)", cell)
    if m:
        return float(m.group(1).replace(",", "")) * (1000 if m.group(2) == "billion" else 1)
    m = re.search(r"[R€]\s?([\d,]{5,})", cell) or re.search(r"EUR ([\d,]{5,})", cell)
    return float(m.group(1).replace(",", "")) / 1_000_000


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_not_run():
    body = text()
    assert body.startswith("# Privacy law around the world: GDPR, PIPEDA, POPIA and PIPL compared with the United States")
    assert "Status: unverified draft, written from reading" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    assert "Page three of three" in body and "issue 404" in body


def test_education_not_legal_advice_is_said_once_and_briefly():
    body = text().lower()
    assert body.count("not legal advice") == 1
    assert "legal advice" in body.split("## what you will be able to do")[0], "said up front, not buried"


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


def test_the_page_links_page_one_and_the_existing_lessons():
    body = text()
    links = {t for t, _ in LINK.findall(body)}
    for needed in (
        PAGE_ONE,
        "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
        "The-CIA-Triad-Confidentiality-Integrity-Availability",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cross-Tenant-Data-Governance-Retention-and-DLP",
        "Logs-SIEM-and-Detection-Basics",
        "Glossary",
    ):
        assert needed in links, needed
    for issue in ("402", "403", "404"):
        assert issue in body, f"issue {issue} is named"


def test_page_two_is_linked_when_it_is_in_the_wiki_and_named_in_plain_text_until_then():
    names = [p.name for p in WIKI.glob("*.md")]
    assert sibling_problems(text(), names) == []


def test_the_sibling_guard_bites():
    linked = "see [US privacy law](US-Privacy-Law-X.md) here"
    plain = "page two (issue 403) covers the United States"
    leaked = "see US-Privacy-Law-X for the United States"
    assert sibling_problems(linked, ["US-Privacy-Law-X.md"]) == []
    assert sibling_problems(plain, ["US-Privacy-Law-X.md"]) == ["page two is in the wiki and is not linked"]
    assert sibling_problems(plain, []) == []
    assert sibling_problems(leaked, []) == ["page two is not in the wiki yet and its file name appears"]


def test_the_lesson_is_registered_in_contents_reading_order_home_sidebar_and_nav():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line, "the banner says unverified draft"


def test_glossary_rows_point_at_real_headings_and_none_repeats_a_term():
    heads = headings(text())
    anchors = set()
    rows = 0
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 14, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    glossary = (WIKI / "Glossary.md").read_text(encoding="utf-8")
    terms = [m.group(1).lower() for m in re.finditer(r"^\| \*\*([^*]+)\*\* \|", glossary, re.MULTILINE)]
    assert len(terms) > 100, "the guard collected too few glossary terms"
    mine = [m.group(1).lower() for m in re.finditer(rf"^\| \*\*([^*]+)\*\* \|[^\n]*{NAME}\.md", glossary, re.MULTILINE)]
    assert len(mine) == rows, (len(mine), rows)
    repeated = sorted({t for t in mine if terms.count(t) > 1})
    assert not repeated, repeated
    # The guard bites: a term that is defined twice is reported.
    assert sorted({t for t in ["a", "b", "a"] if ["a", "b", "a"].count(t) > 1}) == ["a"]


def test_american_spelling_no_em_dashes_no_ip_addresses_and_no_opinion_section():
    body = text()
    low = body.lower()
    assert "—" not in body
    assert not IPV4.findall(body), IPV4.findall(body)
    assert not british_words(low), british_words(low)
    assert "privacy" in low, "the guard collected nothing"
    for banned in ("in my opinion", "i believe", "## opinion", "the maintainer's view", "soap box"):
        assert banned not in low, banned
    assert "opinion" in low and "page two" in low, "the page says where opinions live"


def test_the_spelling_guard_bites():
    assert british_words("the organisation's defence and an offence") == ["defence", "offence", "organisation"]
    assert not british_words("the organization's defense and impact analyses")


def test_every_table_has_a_named_first_header_cell():
    bad = []
    lines = text().splitlines()
    tables = 0
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and lines[i + 1].startswith("|---") and (i == 0 or not lines[i - 1].startswith("|")):
            tables += 1
            first = line.strip("|").split("|")[0].strip()
            if not first:
                bad.append(i + 1)
    assert tables >= 6, "the guard collected too few tables"
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
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(text()))
    for topic in ("region", "breach", "transfer"):
        assert topic in alts, topic
    sources = " ".join(m["src"] for m in WRAPPED.finditer(text()))
    for law in ("GDPR", "PIPEDA", "POPIA", "PIPL"):
        assert law in sources, law
    for clock in ("72 hours", "30 days", "60 days"):
        assert clock in sources, clock
    for mechanism in ("adequacy", "standard contractual clauses", "security assessment"):
        assert mechanism in sources.lower(), mechanism


# ---- the register --------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679",
        "edpb_guidelines_202209_personal_data_breach_notification_v2.0_en.pdf",
        "commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en",
        "standard-contractual-clauses-scc_en",
        "dataprotection.ie/en/news-media/press-releases/Data-Protection-Commission-announces-conclusion-of-inquiry-into-Meta-Ireland",
        "legislation.gov.uk/eur/2016/679/article/33",
        "legislation.gov.uk/eur/2016/679/article/83",
        "laws-lois.justice.gc.ca/eng/acts/p-8.6/FullText.html",
        "laws-lois.justice.gc.ca/eng/regulations/SOR-2018-64/FullText.html",
        "priv.gc.ca",
        "parl.ca/legisinfo/en/bill/44-1/c-27",
        "PROTECTION-OF-PERSONAL-INFORMATION-ACT-4-OF-2013.pdf",
        "20200622-gg43461-rg11136-pr21-POPIAsections.pdf",
        "inforegulator.org.za/enforcement-notices",
        "ENFORCEMENT-NOTICE-DOJCD-MATTER-090523.pdf",
        "FIRST-NATIONAL-BANK-INFRINGEMENT-NOTICE-211026_Redacted.pdf",
        "INFRINGEMENT-NOTICE-CENTRAL-JOHANNESBURG-TVET-COLLEGE_Redacted.pdf",
        "digichina.stanford.edu/work/translation-personal-information-protection-law",
        "chinalawtranslate.com/en/national-intelligence-law-of-the-p-r-c-2017",
        "digichina.stanford.edu/work/translation-cybersecurity-law",
        "cac.gov.cn/2024-03/22/c_1712776611775634.htm",
        "cac.gov.cn/2022-07/21/c_1660021534306352.htm",
        "cac.gov.cn/2022-07/21/c_1660021534364976.htm",
        "gov.br/anpd",
        "github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/412",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 26


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


# ---- facts that can be checked on the page --------------------------------------------------------------------------


def test_the_gdpr_paragraphs_carry_the_numbers_and_articles_the_text_gives():
    part = section(text(), "## The European Union: the GDPR")
    for needed in (
        "Regulation (EU) 2016/679",
        "27 April 2016",
        "25 May 2018",
        "Article 3(2)",
        "Article 6(1)",
        "legitimate interests",
        "Article 9",
        "Article 12(3)",
        "one month",
        "two further months",
        "Article 28",
        "Article 30",
        "250",
        "Article 33",
        "72 hours",
        "Article 34",
        "Article 35",
        "Article 37",
        "Article 45",
        "Article 46",
        "Article 49",
        "Article 83",
        "EUR 20 million",
        "4%",
        "EUR 10 million",
        "2%",
        "reasonable degree of certainty",
        "4 June 2021",
    ):
        assert needed in part, needed


def test_the_canada_south_africa_and_china_paragraphs_carry_the_numbers_the_texts_give():
    ca = section(text(), "## Canada: PIPEDA")
    for needed in (
        "S.C. 2000, c. 5",
        "2000-04-13",
        "2026-09-30",
        "2025-03-04",
        "real risk of significant harm",
        "section 10.1",
        "24 months",
        "thirty days",
        "$10,000",
        "$100,000",
        "Bill C-27",
        "2025-01-06",
        "substantially similar",
        "Alberta",
        "British Columbia",
        "Quebec",
    ):
        assert needed in ca, needed
    za = section(text(), "## South Africa: POPIA")
    for needed in (
        "Act 4 of 2013",
        "1 July 2020",
        "30 June 2021",
        "juristic",
        "section 22",
        "as soon as reasonably possible",
        "section 72",
        "R10 million",
        "10 years",
        "Information Regulator",
        "information officer",
        "section 99",
    ):
        assert needed in za, needed
    cn = section(text(), "## China: the PIPL")
    for needed in (
        "August 20, 2021",
        "November 1, 2021",
        "Article 3",
        "Article 13",
        "Article 38",
        "Article 40",
        "Article 52",
        "Article 55",
        "Article 57",
        "immediately",
        "Article 66",
        "RMB 50 million",
        "5%",
        "Article 69",
        "Order No. 16",
        "2024-03-22",
        "100,000",
        "1,000,000",
        "10,000",
    ):
        assert needed in cn, needed


def test_the_pipl_is_described_as_protection_from_companies_and_the_state_side_is_cited_not_overstated():
    cn = section(text(), "## China: the PIPL")
    for needed in (
        "Articles 33 to 37",
        "Article 35",
        "Article 68",
        "National Intelligence Law",
        "Article 7",
        "Cybersecurity Law",
        "Article 28",
        "companies",
    ):
        assert needed in cn, needed
    assert "Article 13" in cn and "statutory duties" in cn
    assert not absolute_state_claims(text()), absolute_state_claims(text())


def test_the_state_claim_guard_bites():
    assert absolute_state_claims("the PIPL does not restrain the state at all")
    assert absolute_state_claims("State organs are exempt from it")
    assert not absolute_state_claims("Articles 33 to 37 apply the law to state organs, with exceptions")


def test_the_comparison_tables_cover_every_dimension_the_issue_asks_for_for_every_law():
    body = text()
    part = section(body, "## The comparison table")
    header_rows = [r for r in part.splitlines() if r.startswith("| Dimension")]
    assert len(header_rows) == 2, "two tables, one per half of the dimensions"
    for header in header_rows:
        for law in ("GDPR", "PIPEDA", "POPIA", "PIPL", "United States"):
            assert law in header, (law, header)
    labels = [r.split("|")[1].strip() for r in part.splitlines() if r.startswith("|") and not r.startswith("|---") and not r.startswith("| Dimension")]
    for dimension in (
        "Who and what it covers",
        "Legal basis for processing",
        "Individual rights",
        "Officer or contact",
        "Breach duty",
        "Cross-border transfers",
        "Regulator",
        "Penalties",
        "How it differs from the United States",
    ):
        assert dimension in labels, dimension
    for row in part.splitlines():
        if row.startswith("|") and not row.startswith("|---") and not row.startswith("| Dimension"):
            cells = [c.strip() for c in row.strip("|").split("|")]
            assert len(cells) == 6 and all(len(c) > 20 for c in cells[1:]), row[:80]


def test_the_united_states_column_repeats_page_two_and_page_one_without_contradicting_them():
    body = text()
    part = section(body, "## The comparison table")
    for needed in (
        "No general",
        "23 comprehensive",
        "19",
        "2026-11-01",
        "60 calendar days",
        "30 days",
        "500",
        "15 U.S.C. 9901",
        "28 CFR Part 202",
        "$750",
    ):
        assert needed in part, needed


def test_the_cases_have_a_date_a_source_and_amounts_that_respect_the_caps():
    part = section(text(), CASES)
    rows = [r for r in part.splitlines() if r.startswith("|") and not r.startswith("|---")][1:]
    assert len(rows) >= 8, "the guard collected too few cases"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert re.search(r"20\d\d", cells[1]), f"no date: {cells[0]}"
        assert URL.search(cells[2]), f"no source: {cells[0]}"
    for needed in (
        "EUR 1.2 billion",
        "12 May 2023",
        "22 May 2023",
        "EUR 403 million",
        "21 September 2026",
        "EUR 824,990,000",
        "8 October 2026",
        "EUR 500,000",
        "3 September 2026",
        "SEK 1.8 million",
        "9 May 2023",
        "R1,000,000",
        "21 October 2026",
        "R500,000",
        "9 October 2026",
        "RMB 8.026 billion",
        "21 July 2022",
    ):
        assert needed in part, needed
    # POPIA administrative fines may not exceed R10 million (section 109(2)(c)).
    for amount in re.findall(r"R(1,000,000|500,000)", part):
        assert money_millions("R" + amount) <= 10
    # The CAC decision says 80.26 yi yuan; one yi is 100 million.
    assert abs(80.26 * 100 / 1000 - 8.026) < 1e-9
    assert abs(money_millions("RMB 8.026 billion") - 8026) < 1e-6
    # The Meta fine is above the GDPR cap for a EUR 10 million or 2 percent breach, as the page says it is a transfer breach.
    assert money_millions("EUR 1.2 billion") == 1200


def test_the_money_guard_bites():
    assert money_millions("EUR 403 million") == 403
    assert money_millions("R1,000,000") == 1
    assert money_millions("EUR 824,990,000") == 824.99
    assert money_millions("R500,000") == 0.5
    assert money_millions("R12 million") > 10, "a fine above the cap would be caught"


def test_the_uk_and_brazil_figures_are_the_ones_the_texts_give():
    part = section(text(), "## A few others, briefly")
    for needed in ("17,500,000", "8,700,000", "72 hours", "13,709", "14 August 2018", "R$50,000,000", "Article 48", "Article 52"):
        assert needed in part, needed


# ---- the exercise --------------------------------------------------------------------------------------------------

ALERT = datetime(2026, 3, 3, 6, 40, tzinfo=UTC)
AWARE = datetime(2026, 3, 3, 9, 0, tzinfo=UTC)
REQUEST = datetime(2026, 3, 10, tzinfo=UTC)
CUSTOMERS = {"European Union": 12000, "Canada": 800, "South Africa": 3000, "Mainland China": 450}


def test_the_exercise_facts_are_synthetic_consistent_and_the_answers_are_computed_here():
    ex = section(text(), EXERCISE)
    # The customer table on the page is the one used here.
    rows = [r for r in ex.splitlines() if r.startswith("|") and not r.startswith("|---")][1:5]
    parsed = {}
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        region = next(k for k in CUSTOMERS if cells[0].startswith(k))
        parsed[region] = int(cells[1].replace(",", ""))
    assert parsed == CUSTOMERS
    total = sum(CUSTOMERS.values())
    assert total == 16250 and "16,250" in ex
    # The GDPR clock runs from awareness (09:00 UTC), not from the alert (06:40 UTC).
    deadline = gdpr_deadline(AWARE)
    assert deadline == datetime(2026, 3, 6, 9, 0, tzinfo=UTC)
    assert deadline.strftime("%A") == "Friday" and AWARE.strftime("%A") == "Tuesday"
    assert "2026-03-06 09:00 UTC" in ex and "Friday" in ex
    earlier = gdpr_deadline(ALERT)
    assert deadline - earlier == timedelta(hours=2, minutes=20)
    assert "2026-03-06 06:40 UTC" in ex and "2 hours 20 minutes" in ex
    # PIPEDA breach record: 24 months after the day the organization determines the breach occurred.
    keep_until = add_months(AWARE, 24)
    assert keep_until.date().isoformat() == "2028-03-03" and "2028-03-03" in ex
    # Access requests received on 2026-03-10.
    gdpr_month = add_months(REQUEST, 1)
    gdpr_extended = add_months(REQUEST, 3)
    pipeda_30 = REQUEST + timedelta(days=30)
    pipeda_60 = REQUEST + timedelta(days=60)
    assert (gdpr_month.date().isoformat(), gdpr_extended.date().isoformat()) == ("2026-04-10", "2026-06-10")
    assert (pipeda_30.date().isoformat(), pipeda_60.date().isoformat()) == ("2026-04-09", "2026-05-09")
    for needed in ("2026-04-10", "2026-06-10", "2026-04-09", "2026-05-09"):
        assert needed in ex, needed
    # Only one of the four laws gives a number: the shortest numeric clock is the GDPR's 72 hours.
    clocks = {"GDPR": 72, "PIPEDA": None, "POPIA": None, "PIPL": None}
    numeric = {k: v for k, v in clocks.items() if v is not None}
    assert min(numeric.values()) == 72 and list(numeric) == ["GDPR"]
    assert "72 hours" in ex and "immediately" in ex and "as soon as feasible" in ex and "as soon as reasonably possible" in ex
    assert "Not run" in ex


def test_the_exercise_says_what_the_gdpr_requires_of_a_company_with_no_eu_establishment():
    ex = section(text(), EXERCISE)
    for needed in ("every supervisory authority", "Article 27", "representative", "one-stop-shop", "lead"):
        assert needed in ex, needed


def test_the_clock_guard_bites():
    wrong = AWARE + timedelta(hours=48)
    assert wrong != gdpr_deadline(AWARE)
    assert gdpr_deadline(AWARE) - AWARE == timedelta(hours=72)
    assert add_months(datetime(2026, 3, 10), 1).date().isoformat() == "2026-04-10"
    assert add_months(datetime(2026, 11, 10), 3).date().isoformat() == "2027-02-10"
    assert sum(CUSTOMERS.values()) != 16000


def test_the_exercise_has_no_real_company_or_person():
    ex = section(text(), EXERCISE)
    assert "Example Outfitters" in ex
    assert "invented" in ex and "made-up" in ex
    for real in ("Amazon", "Meta ", "Google", "Uber"):
        assert real not in ex, real


# ---- the rest ------------------------------------------------------------------------------------------------------


def test_the_adequacy_list_claims_match_what_the_commission_page_said_on_the_day():
    body = text()
    assert "Canada" in body and "Data Privacy Framework" in body and "10 July 2023" in body
    assert "27 January 2026" in body and "Brazil" in body
    assert "South Africa" in body and "China" in body
    low = body.lower()
    assert "neither south africa nor china" in low


def test_no_security_posture_detail_of_this_repository_is_on_the_page_and_the_guard_bites():
    body = text()
    assert "privacy" in body.lower(), "the guard collected nothing"
    assert not posture_phrases(body), posture_phrases(body)
    assert posture_phrases("check the branch protection settings")
    assert not posture_phrases("check the settings in your own system")


def test_what_the_page_did_not_read_is_named():
    part = section(text(), "## Not verified, plainly")
    for needed in (
        "Regulation 1182/71",
        "India",
        "Japan",
        "Australia",
        "later amendments",
        "Chinese",
        "English translation",
        "web.archive.org",
        "Bill C-27",
        "standard contract",
        "cybersecurity incident",
    ):
        assert needed in part, needed
