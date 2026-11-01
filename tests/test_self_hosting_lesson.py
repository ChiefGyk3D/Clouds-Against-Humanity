# SPDX-License-Identifier: Apache-2.0
"""The self-hosting lesson with SearXNG as the worked example (issue #424): registered, sourced, honest, safe to follow.

docs/wiki/Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md teaches the trade of running a service
yourself, who sees a query on each path, and a local lab. A banner that claims more than was run, a dead link, a
missing registration, a real address, a lab command that binds to every address, a named public instance, a figure
for memory that no source gave, or a claim with no status would each teach or reveal the wrong thing.
"""

import re
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALLOWED_ADDR = re.compile(r"^(?:127\.0\.0\.1|192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3})$")
STATUS_WORDS = ("Read", "General knowledge", "**est.**", "Observed", "Not run")
URL = re.compile(r"https://([a-z0-9.-]+)(/[^)\s`]*)?")
ALLOWED_HOSTS = {"docs.searxng.org", "docs.docker.com", "github.com", "raw.githubusercontent.com", "hub.docker.com", "auth.docker.io", "registry-1.docker.io"}
DIAGRAM = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>images/[^)\n]+\.png)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>"
    r"\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
IMAGE_ANY = re.compile(r"!\[[^\]\n]*\]\([^)\n]+\)")
PATH = re.compile(r"`((?:workloads|stacks|modules|scripts|tests|docs/stages|docs/superpowers)/[A-Za-z0-9_./-]+)`")
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
MAX_ALT = 150
EXPECTED_DIAGRAMS = 2
DATE_READ = "2026-11-01"
PRICE = re.compile(r"[$]\s?\d|\b\d+\s?(?:dollars|USD|EUR)\b|\b(?:cheap|cheaper|cheapest|free of charge)\b|per month", re.IGNORECASE)


def text() -> str:
    return page_text(PAGE)  # without the generated navigation blocks (issue #417)


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("\n## ")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def stray_addresses(body: str) -> list[str]:
    return [a for a in ADDR.findall(body) if not ALLOWED_ADDR.match(a)]


def foreign_hosts(body: str) -> list[str]:
    return sorted({h for h, _ in URL.findall(body) if h not in ALLOWED_HOSTS})


def wildcard_binds(code: str) -> list[str]:
    return [ln for ln in code.splitlines() if re.search(r"0\.0\.0\.0|\[::\]|SEARXNG_BIND=\s*$|-p\s+\d+:\d+|--publish\s+\d+:\d+", ln)]


def diagram_problems(body: str, wiki: Path = WIKI) -> list[str]:
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


def test_the_banner_says_it_was_written_from_reading_and_nothing_was_deployed():
    body = text()
    assert body.startswith("# Self-hosting: when and why, with SearXNG as the worked example")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and DATE_READ in body
    assert "## Not verified, plainly" in body
    assert "Docker Engine" in body.split("**Not run:**")[1].split("\n")[0]


def test_every_linked_wiki_page_exists_and_the_required_lessons_are_linked():
    links = set(LINK.findall(text()))
    assert len(links) >= 10, "the guard collected too few links"
    assert not sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    required = {
        "Containers-and-Docker-Basics",
        "How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves",
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet",
        "Backups-Recovery-and-Patching",
        "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet",
        "Attack-Surface-List-Shrink-Measure",
        "Grafana-Basics-From-a-Blank-Page",
        "Detection-and-Monitoring-Wazuh-and-the-Landscape",
    }
    assert required <= links, sorted(required - links)


def test_the_lesson_is_registered_everywhere_with_three_to_six_related_pages():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = next(ln for ln in nav.splitlines() if f"page: {NAME}," in ln)
    assert 'status: "draft"' in line and "subgroup: \"Stage guides and design\"" in line
    related = re.search(r"related: \[([^\]]*)\]", line)
    assert related, "the nav entry has no related list"
    names = [n.strip() for n in related[1].split(",") if n.strip()]
    assert 3 <= len(names) <= 6, names
    for n in names:
        assert f"page: {n}," in nav, n
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [ln for ln in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in ln]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings_and_no_term_is_duplicated():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    gloss = (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines()
    anchors = set()
    for line in gloss:
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)
    terms = [re.match(r"\| \*\*(.+?)\*\*", ln)[1].lower() for ln in gloss if ln.startswith("| **")]
    mine = [re.match(r"\| \*\*(.+?)\*\*", ln)[1].lower() for ln in gloss if ln.startswith("| **") and f"{NAME}.md" in ln]
    assert len(terms) > 100 and len(mine) >= 5, "the guard collected too little"
    # Older rows may repeat a term; this page's own terms must each appear exactly once.
    assert [t for t in mine if terms.count(t) != 1] == []


def test_no_address_outside_the_documentation_ranges_and_no_em_dash_and_no_price_talk():
    body = text()
    assert "127.0.0.1" in body, "the guard collected nothing"
    assert not stray_addresses(body)
    assert "—" not in body
    assert not PRICE.findall(body), PRICE.findall(body)


def test_the_address_and_price_guards_bite():
    assert stray_addresses("ping 10.0.0.7") == ["10.0.0.7"]
    assert not stray_addresses("ping 192.0.2.7 and 127.0.0.1")
    assert PRICE.findall("costs $12 per month")


def test_only_the_sources_read_are_linked_and_no_public_instance_is_named():
    body = text()
    assert len(URL.findall(body)) >= 8, "the guard collected too few sources"
    assert not foreign_hosts(body), foreign_hosts(body)
    for needle in ("searx.space", "searx.be", "searx.tiekoetter", "priv.au"):
        assert needle not in body, needle


def test_the_source_guard_bites():
    assert foreign_hosts("see https://searx.example.net/ and https://docs.searxng.org/x") == ["searx.example.net"]


def test_every_cited_repository_path_exists():
    cited = sorted(set(PATH.findall(text())))
    assert len(cited) >= 6, "the guard collected too little"
    missing = [c for c in cited if not (ROOT / c.rstrip("/")).exists()]
    assert not missing, missing


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_every_diagram_is_wrapped_has_alt_text_a_source_and_a_picture():
    body = text()
    assert len(DIAGRAM.findall(body)) == EXPECTED_DIAGRAMS
    assert not diagram_problems(body)


def test_the_diagram_guard_bites():
    bare = "![too short](images/x.png)\n"
    assert diagram_problems(bare)
    long_alt = "![" + "a" * 151 + "](images/x.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n```\n\n</details>"
    assert any("alt text" in p for p in diagram_problems(long_alt))


def test_the_lab_binds_to_loopback_and_never_to_every_address():
    code = "\n".join(b for t, b in FENCE.findall(text()) if t == "bash")
    assert "SEARXNG_BIND=127.0.0.1" in code and "ss -ltn" in code, "the guard collected nothing"
    assert not wildcard_binds(code), wildcard_binds(code)


def test_the_lab_guard_bites():
    assert wildcard_binds("docker run -p 8080:8080 x")
    assert wildcard_binds("SEARXNG_BIND=0.0.0.0")
    assert wildcard_binds("SEARXNG_BIND=\n")
    assert not wildcard_binds("export SEARXNG_BIND=127.0.0.1")


def test_memory_is_stated_as_unknown_and_no_invented_figure_is_given():
    body = text()
    assert "unknown" in body.lower()
    section = body.split("## Does it fit")[1].split("\n## ")[0]
    assert "unknown" in section.lower()
    assert "not measured" in section.lower() or "nothing was measured" in section.lower()
    assert not re.search(r"\b\d+\s?(?:MB|MiB|GB|GiB)\b", section.replace("1.2 to 1.6 GB", "").replace("2 GB", "")), section


def test_the_image_digests_match_the_compose_file():
    compose = (ROOT / "workloads" / "searxng" / "docker-compose.yml").read_text(encoding="utf-8")
    digests = set(re.findall(r"sha256:[0-9a-f]{64}", compose))
    assert len(digests) == 2
    body = text()
    for d in digests:
        assert d in body, d


def test_the_page_makes_no_statement_about_this_repositorys_own_posture():
    body = text().lower()
    for needle in ("this repository has no public", "this project has no public", "our firewall", "this repository is secure"):
        assert needle not in body, needle


def test_the_checklist_covers_every_item_the_issue_asks_for():
    section = text().split("## The self-hosting checklist for any service")[1].split("\n## ")[0]
    rows = [ln for ln in section.splitlines() if ln.startswith("| ") and not ln.startswith("|---")][1:]
    assert len(rows) >= 9, "the guard collected too few rows"
    for word in ("Threat model", "Where it listens", "Who may reach it", "Secrets", "Updates", "Backups", "Monitoring", "Logging", "When not"):
        assert any(r.split("|")[1].strip().startswith(word) for r in rows), word
    assert all(r.rstrip().endswith("|") and r.count("|") >= 4 for r in rows)
