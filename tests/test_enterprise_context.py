"""Checks for the four enterprise-context pages in docs/wiki/.

These pages mix verified vendor claims with general industry knowledge, so the
tests keep the mix honest: each page carries the orientation banner, links its
neighbors, has a contrast table and a predict-then-check exercise, and every
row of its claims register is either dated and sourced, general knowledge, or
marked UNVERIFIED. The landscape page's Doppler section is held to the same rule.
"""

import ipaddress
import itertools
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"

PAGES = [
    "Enterprise-Networks-Campus-Branch-Datacenter-Cloud",
    "Enterprise-Infrastructure-Differences",
    "Enterprise-Identity-and-Secrets-at-Scale",
    "Careers-Roles-and-What-to-Learn-Next",
]
# Reading order of the whole Enterprise context section, including the page
# written separately (change management), which has its own conventions.
ORDER = [*PAGES[:2], "Enterprise-Change-Management-for-Beginners", *PAGES[2:]]
BANNER = "Orientation, not a design guide: verified claims dated"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
VERIFIED = re.compile(r"^Verified \d{4}-\d{2}-\d{2}$")
OK_STATUS = (VERIFIED, re.compile(r"^General knowledge$"), re.compile(r"^UNVERIFIED$"))


def text(name: str) -> str:
    return (WIKI / f"{name}.md").read_text()


def slug(heading: str) -> str:
    heading = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return heading.replace(" ", "-")


def anchors(name: str) -> set[str]:
    found = set()
    for line in text(name).splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            found.add(slug(m.group(1)))
    return found


def register_rows(body: str) -> list[list[str]]:
    """Rows of the table under '## Claims register'."""
    section = body.split("## Claims register", 1)[1]
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] != "Claim":
                rows.append(cells)
    return rows


@pytest.mark.parametrize("name", PAGES)
def test_banner_prerequisites_and_next(name):
    body = text(name)
    assert BANNER in "\n".join(body.splitlines()[:4]), f"{name}: banner missing"
    assert re.search(r"^\*\*Prerequisites:\*\* .*\]\(", body, re.MULTILINE)
    assert re.search(r"^Next: .*\]\(", body, re.MULTILINE)


@pytest.mark.parametrize("name", PAGES)
def test_contrast_table_and_exercise(name):
    body = text(name)
    assert re.search(r"^\|.*In this project.*In (an enterprise|a company).*\|", body, re.MULTILINE), (
        f"{name}: no 'In this project / In an enterprise' contrast table"
    )
    for needle in ("Predict, then check", "Reference answers", "Try it yourself"):
        assert needle in body, f"{name}: missing {needle}"


@pytest.mark.parametrize("name", PAGES)
def test_every_claims_register_row_is_dated_general_or_unverified(name):
    rows = register_rows(text(name))
    assert len(rows) >= 5, f"{name}: claims register is too thin"
    for row in rows:
        assert len(row) == 3, f"{name}: bad register row {row}"
        claim, status, source = row
        assert any(p.match(status) for p in OK_STATUS), f"{name}: status {status!r} for {claim!r}"
        if VERIFIED.match(status):
            assert re.search(r"https://\S+", source), f"{name}: verified claim without a URL: {claim!r}"


@pytest.mark.parametrize("name", PAGES)
def test_every_wiki_link_and_anchor_resolves(name):
    problems = []
    for target, anchor in LINK.findall(text(name)):
        if not (WIKI / f"{target}.md").exists():
            problems.append(f"{target} (missing page)")
        elif anchor and anchor not in anchors(target):
            problems.append(f"{target}#{anchor} (missing anchor)")
    assert not problems, f"{name}: {problems}"


def test_next_lines_follow_the_chain():
    for earlier, later in itertools.pairwise(ORDER):
        line = re.search(r"^Next: .*$", text(earlier), re.MULTILINE).group(0)
        assert f"({later}.md)" in line, f"{earlier}: Next should name {later}"


def test_pages_are_in_sidebar_and_reading_order_under_enterprise_context():
    for page, heading in (("_Sidebar", "Enterprise context"), ("Reading-Order", "## Enterprise context")):
        body = text(page)
        assert heading in body, f"{page}: no Enterprise context section"
        links = [t for t, _ in LINK.findall(body)]
        positions = [links.index(n) for n in ORDER]
        assert positions == sorted(positions), f"{page}: pages out of order"
    assert "Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md" in text("Home")


def test_landscape_page_says_doppler_is_used_in_enterprises_with_a_date():
    body = text("Small-Example-Enterprise-Landscape")
    section = body.split("### Doppler is used in enterprises too", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"retrieved \d{4}-\d{2}-\d{2}", section)
    assert "docs.doppler.com" in section
    assert "not an endorsement" in section
    for page in PAGES:
        assert f"({page}.md)" in body, f"landscape page does not point to {page}"


@pytest.mark.parametrize("name", PAGES)
def test_only_documentation_or_private_example_addresses_and_no_secret_shapes(name):
    body = text(name)
    ok_nets = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "10.0.0.0/8")]
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", body):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        assert any(addr in net for net in ok_nets), f"{name}: address outside example ranges"
    assert not re.search(r"dop_(v1|pt|st)_|AKIA[0-9A-Z]{12,}|-----BEGIN", body), f"{name}: secret-shaped literal"
