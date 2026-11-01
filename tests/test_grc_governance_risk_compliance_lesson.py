# SPDX-License-Identifier: Apache-2.0
"""The GRC lesson: registered, honest about what was read and run, diagrams intact, facts that can be checked checked.

docs/wiki/GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations.md is page 1 of the three-page
GRC and compliance set (issue 402). A banner that claims more than was done, a dead link, a missing registration, a diagram
with no picture, no alt text or the wrong shape, a register row with no URL and no date, a repeated "not legal advice"
notice, an opinion section on a page that is meant to be factual, a settlement whose parts do not add up, or an exercise
that cites a repository file that does not exist would each teach or reveal the wrong thing.
"""

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
STATUS_WORDS = ("Read", "Run on", "General knowledge", "**est.**", "Constructed")
URL = re.compile(r"\]\(https?://[^)\s]+\)")
DATE = "2026-11-01"
IPV4 = re.compile(r"(?<!release )\b(?:\d{1,3}\.){3}\d{1,3}\b")
EXERCISE = "## Free exercise: one control, the evidence an auditor would ask for"
BRITISH = ("defence", "behaviour", "colour", "organisation", "centre", "licence", "programme", "analyse", "favour", "realise")


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


def money(cell: str) -> int:
    """Whole millions of dollars in a cell such as '$300 million'."""
    return int(re.search(r"\$(\d+) million", cell).group(1))


POSTURE = (
    r"required_approving_review_count",
    r"required approving review",
    r"enforce_admins",
    r"administrators? (?:not|are not) (?:enforced|subject)",
    r"branch protection",
    r"branch rule",
    r"stale reviews",
    r"no human approval",
    r"gap against the text of \(b\)",
    r"github api",
    r"gh api",
)


def posture_phrases(body: str) -> list[str]:
    """Statements of this repository's own branch-protection settings must not be published."""
    return [p for p in POSTURE if re.search(p, body, re.IGNORECASE)]


def too_tall(width: int, height: int) -> bool:
    return height > 1.6 * width


def settlement_parts(part: str) -> tuple[int, list[int]]:
    total = int(re.search(r"at least \$(\d+) million", part).group(1))
    parts = [int(m) for m in re.findall(r"\$(\d+) million (?:to a fund|to 48 states|to the CFPB)", part)]
    return total, parts


# ---- the page ----------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_not_run():
    body = text()
    assert body.startswith("# Governance, risk and compliance in plain terms")
    assert "Status: unverified draft, written from reading" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "## Not verified, plainly" in body
    assert "defensive and educational" in body.lower()
    assert "Page one of three" in body and "issue 402" in body


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


def test_the_page_links_the_existing_lessons_and_names_the_siblings_in_plain_text():
    body = text()
    links = {t for t, _ in LINK.findall(body)}
    for needed in (
        "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
        "The-CIA-Triad-Confidentiality-Integrity-Availability",
        "Patch-Management-and-Automatic-Security-Updates",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cross-Tenant-Data-Governance-Retention-and-DLP",
        "CI-Tests-and-Cost-Gate",
        "Enterprise-Change-Management-for-Beginners",
    ):
        assert needed in links, needed
    for issue in ("402", "403", "404"):
        assert issue in body, f"issue {issue} is named"
    # Pages two and three are not in the wiki yet; they are named in plain text until they are.
    assert not [p for p in WIKI.glob("*.md") if "Privacy-Law" in p.name and p.name in body]


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


def test_american_spelling_no_em_dashes_no_ip_addresses_and_no_opinion_section():
    body = text()
    low = body.lower()
    assert "—" not in body
    assert not IPV4.findall(body), IPV4.findall(body)
    assert not british_words(low), british_words(low)
    assert "governance" in low, "the guard collected nothing"
    for banned in ("in my opinion", "i believe", "## opinion", "the maintainer's view", "soap box"):
        assert banned not in low, banned
    assert "opinion" in low and "page two" in low, "the page says where opinions live"


def test_the_spelling_and_opinion_guards_bite():
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
    alts = " ".join(m["alt"].lower() for m in WRAPPED.finditer(text()))
    for topic in ("loop", "law", "attestation", "evidence"):
        assert topic in alts, topic


# ---- the register --------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_every_sourced_row_has_a_url_and_the_read_date():
    assert not sourced_rows_without_url_and_date(text())
    reg = text().split("## Claims register")[1]
    for host in (
        "nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
        "doi.org/10.6028/NIST.SP.800-53r5",
        "csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
        "csrc.nist.gov/pubs/sp/800/171/r3/final",
        "nistspecialpublication800-30r1.pdf",
        "iso.org/standard/27001",
        "cisecurity.org/controls/cis-controls-list",
        "PLAW-107publ204",
        "pcisecuritystandards.org/about_us",
        "blog.pcisecuritystandards.org/just-published-pci-dss-v4-0-1",
        "hhs.gov/hipaa/for-professionals/security",
        "ecfr.gov/current/title-45/part-164",
        "ecfr.gov/current/title-16/part-314",
        "USCODE-2023-title44-chap35-subchapII-sec3551",
        "USCODE-2023-title44-chap36-sec3608",
        "aicpa-cima.com",
        "ftc.gov/news-events/news/press-releases/2019/07",
        "hhs.gov/hipaa/for-professionals/compliance-enforcement/agreements/anthem",
        "commerce.senate.gov",
    ):
        assert host in reg, host
    assert reg.count(DATE) >= 18


def test_the_register_guards_bite():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]
    undated = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | [p](https://example.com/p) | Read 2026-10-31 |\n"
    assert sourced_rows_without_url_and_date(undated) == ["X"]
    nourl = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | a page | Read 2026-11-01 |\n"
    assert sourced_rows_without_url_and_date(nourl) == ["X"]


# ---- facts that can be checked on the page --------------------------------------------------------------------------


def test_the_six_csf_functions_and_the_four_core_controls_are_named():
    body = text()
    for fn in ("GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"):
        assert fn in body, fn
    assert "February 26, 2024" in body and "Release 5.2.0" in body and "2025-08-27" in body
    assert "CIS Controls v8.1" in body and "18" in body


def test_the_equifax_settlement_parts_add_up_and_the_dates_and_cases_are_present():
    part = section(text(), "## What non-compliance costs: documented cases")
    total, parts = settlement_parts(part)
    assert total == 575 and len(parts) == 3 and sum(parts) == total, (total, parts)
    for needed in ("July 22, 2019", "October 15, 2018", "$16 million"):
        assert needed in part, needed
    rows = [r for r in part.splitlines() if r.startswith("|") and not r.startswith("|---")][1:]
    assert len(rows) >= 3, "the guard collected too few cases"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert re.search(r"20\d\d", cells[1]), f"no date: {cells[0]}"
        assert URL.search(cells[2]), f"no source: {cells[0]}"


def test_the_settlement_guard_bites():
    good = "pay at least $575 million: $300 million to a fund, $175 million to 48 states, $100 million to the CFPB"
    total, parts = settlement_parts(good)
    assert total == sum(parts) == 575
    off = good.replace("$100 million", "$90 million")
    total, parts = settlement_parts(off)
    assert total != sum(parts)


def test_the_law_paragraphs_carry_the_numbers_the_primary_texts_give():
    body = text()
    for needed in (
        "Public Law 107-204",
        "July 30, 2002",
        "section 404",
        "$5,000,000",
        "20 years",
        "60 calendar days",
        "6 years",
        "500 consumers",
        "30 days",
        "Qualified Individual",
        "44 U.S.C. 3551",
        "December 23, 2022",
        "31 December 2024",
        "31 March 2025",
        "does not enforce",
    ):
        assert needed in body, needed
    assert "ITGC" in body or "IT general controls" in body


def test_the_compliance_is_not_security_section_has_both_directions_and_labels_the_constructed_one():
    part = section(text(), "## Compliance is not security, and security is not compliance")
    assert "Target" in part and "certified" in part.lower()
    assert "March 26, 2014" in part and "September 2013" in part and "110 million" in part
    assert "Constructed" in part, "the secure-but-not-compliant example is marked as made up"
    assert "I found no" in part, "the page says it found no sourced case for that direction"


def test_the_exercise_covers_every_part_of_cm3_and_says_what_was_not_run():
    ex = section(text(), EXERCISE)
    rows = [r for r in ex.splitlines() if re.match(r"\| (a|b|c|d|e|f|g) \|", r)]
    assert [r.split("|")[1].strip() for r in rows] == list("abcdefg"), "one row per CM-3 part, a to g"
    for r in rows:
        assert len(r.split("|")) >= 5 and len(r.split("|")[3].strip()) > 30, r
    assert "Not run" in ex and "CM-3" in ex and "Configuration Change Control" in ex
    assert "your own system" in ex, "the review requirement is left to the reader to check"
    assert not posture_phrases(text()), posture_phrases(text())


def test_the_repository_paths_the_page_cites_exist():
    body = text()
    cited = set(re.findall(r"`((?:scripts|\.github/workflows|tests|docs)/[A-Za-z0-9_./-]+)`", body))
    assert len(cited) >= 5, "the guard collected too few paths"
    missing = sorted(p for p in cited if not (ROOT / p).exists())
    assert not missing, missing
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in ("tofu:", "python:", "security:", "ci-green:"):
        assert job in ci, job
    assert "name: CI green" in ci and "CI green" in body


def test_no_security_posture_detail_of_this_repository_is_on_the_page_and_the_guard_bites():
    body = text()
    assert "CI green" in body, "the guard collected nothing"
    assert not posture_phrases(body), posture_phrases(body)
    for leaked in (
        "the required approving review count is 0",
        "administrators not enforced",
        "enforce_admins false",
        "a read-only GitHub API request for the branch protection",
        "dismissal of stale reviews turned on",
        "no human approval is required",
        "This is a gap against the text of (b)",
    ):
        assert posture_phrases(leaked), leaked
    assert not posture_phrases("check whether a review is required in your own system")


def test_the_path_guard_bites():
    assert not (ROOT / "scripts" / "no_such_file.py").exists()
    assert (ROOT / "scripts" / "identifier_check.py").exists()


# ---- what a certification or report does and does not tell you (issue 420, change 1) ---------------------------------

CERT = "## What a certification or report does and does not tell you"
NEXT_AFTER_CERT = "## The frameworks at overview level"
LAW_SECTION = "## Law, regulation, framework, standard and attestation"
PASS_FAIL_CLAIM = re.compile(r"\bwould (?:have )?(?:failed|fail|passed|pass)\b|\bfailed (?:a |its |the )?SOC 2\b", re.IGNORECASE)
NAMES_IN_SOURCES = ("Connor", "Paganini", "Pawlicki", "Linton", "Mayes", "Kindem", "Amato", "Emily Hill", "Sullivan")
EY_SOURCES = (
    "theregister.com/2025/10/29/ey_exposes_4tb_sql_database",
    "securityaffairs.com/184062/data-breach/ernst-young-exposes-4tb-sql-server-backup-publicly-on-microsoft-azure",
    "techradar.com/pro/security/ey-reportedly-leaked-a-massive-4tb-database-online-exposing-company-secrets-online-for-all-to-see",
    "nationalcioreview.com/articles-insights/extra-bytes/ernst-young-found-exposing-massive-sql-backup-on-azure",
)
NEW_REGISTER_HOSTS = (
    "assets.ctfassets.net/rb9cdnjh59cm/2paxzm46AxmwDDSZGkdtFS",
    "journalofaccountancy.com/issues/2026/feb/promises-of-fast-and-easy-threaten-soc-credibility",
    "journalofaccountancy.com/issues/2026/may/aicpa-guides-peer-reviewers-to-address-soc-2-risks",
    "journalofaccountancy.com/podcast/2026/apr/the-risks-of-quick",
    "aicpa-cima.com/cpe-learning/webcast/soc-2-report-walkthrough",
    "iso.org/certification.html",
    "dqsglobal.com/en/certify/iso-27001-certification",
    "PCI_DSS-QRG-v3_2_1.pdf",
) + EY_SOURCES
NEW_GLOSSARY_TERMS = (
    "Carve-out method",
    "Complementary user entity controls (CUEC)",
    "SOC 2 Type 1 and Type 2",
    "Surveillance audit",
)


def cert_section(body: str) -> str:
    return body.split(CERT)[1].split("\n## ")[0]


def pass_fail_claims(body: str) -> list[str]:
    """A sentence that says a named kind of firm would pass or fail a SOC 2 is a verdict the sources do not give."""
    return [m.group(0) for m in PASS_FAIL_CLAIM.finditer(body)]


def names_found(body: str) -> list[str]:
    return [n for n in NAMES_IN_SOURCES if n in body]


def test_the_certification_section_sits_after_the_attestation_material_and_before_the_frameworks():
    body = text()
    assert body.count(CERT) == 1
    assert body.index(LAW_SECTION) < body.index(CERT) < body.index(NEXT_AFTER_CERT)


def test_the_certification_section_covers_snapshot_scope_opinion_cycles_the_gap_and_what_to_ask_for():
    part = cert_section(text())
    low = part.lower()
    assert len(part) > 3000, "the guard collected too little of the section"
    for needed in (
        "Type 1",
        "Type 2",
        "as of a point in time",
        "specified period of time",
        "carve-out",
        "complementary user entity controls",
        "exception",
        "not a certification",
        "surveillance",
        "recertification",
        "three years",
        "IAF CertSearch",
        "in between PCI DSS assessments",
        "Constructed",
    ):
        assert needed.lower() in low, needed
    assert "what to ask for" in low and "scope" in low and "incident" in low and "monitoring" in low
    assert "not a guarantee" in low or "does not say the organization is secure" in low


def test_the_ey_case_is_dated_sourced_and_says_what_is_not_known():
    part = cert_section(text())
    for src in EY_SOURCES:
        assert src in part, src
    for needed in ("October 29, 2025", "October 30, 2025", "October 31, 2025", "Neo Security", "4 TB", "first 1,000 bytes"):
        assert needed in part, needed
    low = part.lower()
    assert "not known" in low and "how long" in low and "accessed" in low
    assert "write-up" in low and "could not read" in low, "the primary write-up was not readable and the page says so"
    assert "does not say" in low, "the page says what the sources do not settle"


def test_no_verdict_that_any_firm_would_pass_or_fail_a_soc_2_and_no_person_is_named_and_the_guards_bite():
    body = text()
    assert "SOC 2" in body, "the guard collected nothing"
    assert not pass_fail_claims(body), pass_fail_claims(body)
    assert not names_found(body), names_found(body)
    assert pass_fail_claims("a firm like that would have failed a SOC 2 report")
    assert pass_fail_claims("it would pass")
    assert not pass_fail_claims("This page does not judge whether any firm passes or fails a SOC 2 report.")
    assert names_found("said Linton of a firm") == ["Linton"]
    assert not names_found("a Dutch firm said its researcher")


def test_the_new_sources_are_in_the_register_with_a_url_a_date_and_a_status():
    reg = text().split("## Claims register")[1]
    for host in NEW_REGISTER_HOSTS:
        assert host in reg, host
    assert not rows_missing_status(text())
    assert not sourced_rows_without_url_and_date(text())


def test_the_not_verified_list_names_what_the_new_section_did_not_read():
    nv = section(text(), "## Not verified, plainly")
    for needed in ("Neo Security", "accreditation body", "ISO/IEC 27006", "Type 1", "no firm"):
        assert needed in nv, needed


def test_the_new_glossary_terms_exist_once_and_point_at_the_section():
    gloss = (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines()
    for term in NEW_GLOSSARY_TERMS:
        rows = [line for line in gloss if line.startswith(f"| **{term}**")]
        assert len(rows) == 1, (term, len(rows))
        assert f"{NAME}.md#what-a-certification-or-report-does-and-does-not-tell-you" in rows[0], term
