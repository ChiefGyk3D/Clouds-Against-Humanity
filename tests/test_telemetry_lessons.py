"""Checks for the five telemetry lesson pages in docs/wiki/.

The pages are drafts written from a design, so these tests keep three things
honest: each page says it is a draft and links its neighbours, nothing on them
looks like a real address, and every figure in the mini SOC cost tables is
recomputed here from docs/cost-prices.json rather than trusted.
"""

import ipaddress
import itertools
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"

# Dependency order: each page assumes the ones before it.
LESSONS = [
    "Cloud-Telemetry-What-and-Why",
    "Multiple-Sites-and-Identity",
    "Telemetry-Crosses-the-Trust-Boundary",
    "Reading-a-Dashboard-as-an-Operator",
    "Build-Your-Own-Mini-SOC",
]
BANNER = "Unverified draft: written from the design, none of stage 2 has been built or applied"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")


def text(name: str) -> str:
    return (WIKI / f"{name}.md").read_text()


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped."""
    heading = heading.strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading)
    return heading.replace(" ", "-")


def anchors(name: str) -> set[str]:
    found = set()
    for line in text(name).splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            found.add(slug(m.group(1)))
    return found


@pytest.mark.parametrize("name", LESSONS)
def test_page_has_status_banner_prerequisites_and_next(name):
    body = text(name)
    head = "\n".join(body.splitlines()[:4])
    assert BANNER in head, f"{name}: status banner missing from the top"
    assert re.search(r"^\*\*Prerequisites:\*\* .*\]\(", body, re.MULTILINE), f"{name}: no Prerequisites line"
    assert re.search(r"^Next: .*\]\(", body, re.MULTILINE), f"{name}: no Next line"


@pytest.mark.parametrize("name", LESSONS)
def test_page_has_a_predict_exercise_with_reference_answers(name):
    body = text(name)
    assert "Predict, then check" in body, f"{name}: no predict-then-check section"
    assert "Reference answers" in body, f"{name}: no reference answers"
    assert "Try it yourself" in body, f"{name}: no try-it-yourself list"


@pytest.mark.parametrize("name", LESSONS)
def test_every_wiki_link_and_anchor_resolves(name):
    problems = []
    for target, anchor in LINK.findall(text(name)):
        if not (WIKI / f"{target}.md").exists():
            problems.append(f"{target} (missing page)")
        elif anchor and anchor not in anchors(target):
            problems.append(f"{target}#{anchor} (missing anchor)")
    assert not problems, f"{name}: {problems}"


def test_next_lines_follow_the_dependency_order():
    for earlier, later in itertools.pairwise(LESSONS):
        next_line = re.search(r"^Next: .*$", text(earlier), re.MULTILINE).group(0)
        assert f"({later}.md)" in next_line, f"{earlier}: Next should name {later}"


def test_lessons_are_in_sidebar_and_reading_order_in_order():
    for page in ("_Sidebar", "Reading-Order"):
        links = [t for t, _ in LINK.findall(text(page))]
        positions = [links.index(n) for n in LESSONS]  # raises if missing
        assert positions == sorted(positions), f"{page}: lessons out of order"


@pytest.mark.parametrize("name", LESSONS)
def test_only_documentation_or_private_example_addresses(name):
    ok_nets = [
        ipaddress.ip_network(n)
        for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "10.0.0.0/8")
    ]
    bad = []
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text(name)):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if not any(addr in net for net in ok_nets):
            bad.append("address outside the documentation and example ranges")
    assert not bad, f"{name}: {len(bad)} finding(s)"


# --- the cost tables -------------------------------------------------------

PRICES = json.loads((ROOT / "docs" / "cost-prices.json").read_text())["droplets"]
CEILING = json.loads((ROOT / "docs" / "stages" / "approved.json").read_text())["ceiling"]
SITE_CONNECTORS = sum(
    PRICES[m["size"]]
    for m in json.loads((ROOT / "stacks" / "10-access" / "cost.json").read_text())["resources"]
)
# docs/cost.md, "Stage 3 estimate": option A is a s-1vcpu-2gb droplet, a flat
# $5 bucket and the stage 1 connectors, $29 running.
STAGE3_A = SITE_CONNECTORS + PRICES["s-1vcpu-2gb"] + 5
MONEY = re.compile(r"\$(\d+(?:\.\d+)?)")


def cost_tables():
    body = text("Build-Your-Own-Mini-SOC")
    tables = []
    for marker in re.finditer(r"<!-- cost-table ceiling=(\d+) -->\n\n((?:\|.*\n)+)", body):
        ceiling = float(marker.group(1))
        rows = [
            [c.strip() for c in line.strip().strip("|").split("|")]
            for line in marker.group(2).splitlines()[2:]
        ]
        tables.append((ceiling, rows))
    return tables


def droplet_cost(cell: str) -> int:
    if cell == "none":
        return 0
    return sum(PRICES[slug_] for slug_ in re.findall(r"`([^`]+)`", cell))


def test_site_connector_and_stage3_constants_match_the_repo():
    assert SITE_CONNECTORS == 12
    assert STAGE3_A == 29
    cost_doc = (ROOT / "docs" / "cost.md").read_text()
    assert "$29" in cost_doc and "$5 flat" in cost_doc


def test_there_are_two_cost_tables_and_the_first_uses_the_real_ceiling():
    tables = cost_tables()
    assert len(tables) == 2
    assert tables[0][0] == CEILING


def test_every_cost_figure_is_recomputed_from_the_price_file():
    for ceiling, rows in cost_tables():
        assert len(rows) == 7
        for option, droplets, one, two, with3, fits in rows:
            d = droplet_cost(droplets)
            expected = [
                (one, SITE_CONNECTORS, d),
                (two, 2 * SITE_CONNECTORS, d),
                (with3, STAGE3_A, d),
            ]
            for cell, base, add in expected:
                a, b, total = (float(x) for x in MONEY.findall(cell))
                assert (a, b, total) == (base, add, base + add), f"{option}: {cell}"
            fits_cells = [w.strip() for w in fits.split("/")]
            totals = [base + add for _, base, add in expected]
            want = ["Yes" if t <= ceiling else "No" for t in totals]
            assert fits_cells == want, f"{option} at ${ceiling:.0f}: {fits_cells} != {want}"


def test_ceiling_36_reference_answer_matches_the_arithmetic():
    """The page's worked answer for a $36 ceiling, recomputed."""
    rows = cost_tables()[0][1]
    totals = []
    for _, droplets, *_ in rows:
        d = droplet_cost(droplets)
        totals.append((SITE_CONNECTORS + d, 2 * SITE_CONNECTORS + d, STAGE3_A + d))
    one = [t[0] for t in totals if t[0] <= 36]
    two = [t[1] for t in totals if t[1] <= 36]
    three = [t[2] for t in totals if t[2] <= 36]
    assert (len(one), len(two), len(three)) == (6, 3, 2)
