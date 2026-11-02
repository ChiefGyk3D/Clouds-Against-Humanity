# SPDX-License-Identifier: Apache-2.0
"""The defender's-view lesson on Tor, I2P and VPN detection: registered, honest about what was read and run, diagrammed, safe.

docs/wiki/Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View.md is page 7 of the series. It says where a
network can watch, which signals are public, what each gets wrong, what blocking costs and why a detection is a lead. A banner
that claims more than was run, a dead link, a missing registration, an address outside the documentation ranges, a claim with
no status or date, a diagram with no alt text, an evasion how-to, a statement about this repository's own posture, or a lab
script that no longer prints what the page says would each teach or reveal the wrong thing.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View"
PAGE = WIKI / f"{NAME}.md"
TOR = "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services"
I2P = "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database"
VPN = "How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Documentation ranges (RFC 5737) only: nothing on this page is a real host.
ALLOWED_ADDR = re.compile(r"^(?:192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3})$")
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
STATUS_WORDS = ("Read", "General knowledge", "**est.**", "Observed")
URL = re.compile(r"\]\(https://[^)\s]+\)")
DIAGRAM = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>images/[^)\n]+\.png)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>"
    r"\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
IMAGE_ANY = re.compile(r"!\[[^\]\n]*\]\([^)\n]+\)")
MAX_ALT = 150
EXPECTED_DIAGRAMS = 5
DATE_READ = "2026-11-01"
LONG_RANDOM = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
LAB_BLOCK = re.compile(r"```python\n(?P<code>\"\"\"detect_lab\.py.*?)\n```", re.DOTALL)
LAB_OUTPUT = re.compile(r"[Ii]t printed:\n\n```\n(?P<out>.*?)\n```", re.DOTALL)
TRIPLE = re.compile(r'^(?P<name>[A-Z_]+) = """\n(?P<body>.*?)"""', re.DOTALL | re.MULTILINE)


def text() -> str:
    return page_text(PAGE)  # without the generated navigation blocks (issue #417)


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def stray_addresses(body: str) -> list[str]:
    return [a for a in ADDR.findall(body) if not ALLOWED_ADDR.match(a)]


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


def lab_script(body: str) -> str:
    found = LAB_BLOCK.search(body)
    assert found, "the lab script block is missing from the page"
    return found["code"] + "\n"


def run_lab(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60, check=False)


def table(out: str) -> dict[str, tuple[int, int, int]]:
    """Rule letter -> (hits, true, false) from the printed score table."""
    rows = {}
    for line in out.splitlines():
        m = re.match(r"^([A-F])\s{2,}.*?\s(\d+)\s+(\d+)\s+(\d+)$", line)
        if m:
            rows[m[1]] = (int(m[2]), int(m[3]), int(m[4]))
    return rows


def expected_from_data(code: str) -> dict:
    """Recompute the answers from the script's own data with different code (sets and a plain loop), as a cross-check."""
    blocks = {m["name"]: m["body"] for m in TRIPLE.finditer(code)}
    log_day = date(2026, 10, 31)
    relays = [r.split() for r in blocks["RELAYS"].strip().splitlines()]
    exits = set(blocks["EXITS"].split())
    conns = []
    for line in blocks["LOG"].strip().splitlines():
        if "not a filterlog line" in line:
            continue
        f = line.split("filterlog: ")[1].split(",")
        conns.append((f[16], f[18], f[19], int(f[21])))
    relay_ip = {r[0].split(":")[0] for r in relays}
    pairs = {tuple(r[0].split(":")) for r in relays}
    pairs = {(a, int(p)) for a, p in pairs}
    fresh = {(r[0].split(":")[0], int(r[0].split(":")[1])) for r in relays if (log_day - date.fromisoformat(r[2])).days <= 7}
    return {
        "n": len(conns),
        "A": [c for c in conns if c[2] in relay_ip and c[1].startswith("192.0.2.")],
        "B": [c for c in conns if (c[2], c[3]) in pairs],
        "C": [c for c in conns if (c[2], c[3]) in fresh],
        "D": [c for c in conns if c[1] in exits],
        "E": [c for c in conns if c[1] in relay_ip],
    }


def test_the_banner_says_it_was_written_from_reading_and_only_a_synthetic_script_was_run():
    body = text()
    assert body.startswith("# Detecting and managing Tor, I2P and VPN traffic on a network")
    assert "Page 7 of a seven-page series" in body
    assert "Status: unverified draft, written from reading" in body
    assert "**Not run:**" in body and DATE_READ in body
    for tool in ("Suricata", "Zeek", "Wazuh", "pfSense"):
        assert tool in body.split("**Not run:**")[1].split("\n")[0], tool
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_series_and_tool_pages_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 16, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        TOR, I2P, VPN,
        "Tor-I2P-and-the-Darknet-Without-the-Myths",
        "Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet",
        "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
        "IDS-and-IPS-Snort-and-Suricata", "Wazuh-SIEM-and-Data-Pipelines", "Logs-SIEM-and-Detection-Basics",
        "Packet-Filters-Compared-iptables-nftables-ufw-pf", "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
        "The-CIA-Triad-Confidentiality-Integrity-Availability",
        "GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations",
        "Privacy-Law-Around-the-World-GDPR-PIPEDA-POPIA-and-PIPL-Compared-With-the-United-States",
        "Why-ZTNA-Not-a-VPN",
    ):
        assert needed in links, needed


def test_the_opsec_page_is_linked_now_that_it_exists():
    body = text()
    for named in ("operational security for Tor and I2P", "series page 6"):
        assert named in body, named
    found = {t for t in LINK.findall(body) if t.startswith("OPSEC-for-Tor-and-I2P-")}
    assert found, "series page 6 exists and must be linked"
    assert all((WIKI / f"{t}.md").exists() for t in found), found
    # The stale statement that the OPSEC page is being written is gone.
    assert "being written at the same time" not in body


EXERCISES = "Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts"


def exercise_links(body: str) -> set[str]:
    return {t for t in LINK.findall(body) if t == EXERCISES}


def test_the_whonix_and_qubes_exercises_are_linked_now_that_they_exist():
    body = text()
    for named in ("Whonix and Qubes exercises", "issue 372"):
        assert named in body, named
    assert exercise_links(body) == {EXERCISES}, "the exercises page (issue 372) exists and must be linked"
    assert (WIKI / f"{EXERCISES}.md").is_file()
    # The stale statement that the exercises are not written yet is gone.
    assert "are not written yet, so they are named in plain text" not in body


def test_the_exercise_link_guard_bites():
    assert not exercise_links("the hands-on Whonix and Qubes exercises (issue 372) are not written yet")
    assert exercise_links(f"the [hands-on Whonix and Qubes exercises]({EXERCISES}.md)")


def test_the_lesson_is_registered_in_contents_reading_order_nav_and_the_defend_track():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = next(row for row in nav.splitlines() if f"{{page: {NAME}," in row)
    assert 'status: "draft"' in line
    assert 'subgroup: "Detection and monitoring"' in line
    assert nav.index(f"{{page: {NAME},") < nav.index("  privacy:"), "the page must sit in the Defend and detect track"
    assert nav.index("  defend:") < nav.index(f"{{page: {NAME},")
    related = re.search(r"related: \[([^\]]*)\]", line)
    assert related, "the page needs a related list"
    names = [n.strip() for n in related[1].split(",")]
    assert 3 <= len(names) <= 6 and NAME not in names
    for n in (TOR, I2P, VPN):
        assert n in names, n
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special


def test_glossary_rows_point_at_real_headings_and_no_term_is_defined_twice():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    rows = 0
    terms = []
    mine = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| **"):
            terms.append(line.split("**")[1].lower())
            if f"{NAME}.md" in line:
                mine.append(line.split("**")[1].lower())
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 4, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    # tests/test_glossary_terms.py bars every repeated term; the terms this page adds must each be defined exactly once.
    assert len(mine) == rows, "every row that links this page starts with a bold term"
    dupes = sorted({t for t in mine if terms.count(t) > 1})
    assert not dupes, dupes


def test_only_documentation_addresses_no_onion_names_long_random_values_or_em_dashes():
    body = text()
    assert len(ADDR.findall(body)) >= 25, "the guard collected too few addresses"
    assert not stray_addresses(body), set(stray_addresses(body))
    assert not ONION.findall(body)
    assert "—" not in body
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)  # link and picture targets are paths, not values
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs


def test_the_address_guard_bites():
    assert stray_addresses("host 8.8.8.8") == ["8.8.8.8"]
    assert stray_addresses("host 10.0.0.1 and 127.0.0.1") == ["10.0.0.1", "127.0.0.1"]
    assert not stray_addresses("Alice 192.0.2.10 and 203.0.113.50 and 198.51.100.7")
    assert ONION.findall("go to " + "a" * 56 + ".onion")
    assert LONG_RANDOM.findall("x" + "a1" * 20)


def test_placeholders_are_example_test_and_documentation_ranges():
    body = text()
    assert "example.test" in body
    for real in ("example.com", "example.org", "example.net"):
        assert real not in body, real
    for block in ("192.0.2.", "198.51.100.", "203.0.113."):
        assert block in body, block


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
    good = ("![Diagram, six places a network can watch and what each sees of Tor traffic](images/a.png)\n\n<details>\n"
            "<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path, wiki) == ["picture missing: images/a.png"]
    (wiki / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path, wiki)
    assert diagram_problems(good.replace("Diagram, six places a network can watch and what each sees of Tor traffic", "x"), tmp_path, wiki)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path, wiki)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("endpoint", "dns", "firewall", "proxy", "network sensor", "siem", "relay list", "exit list", "bridge",
                 "pluggable transport", "reseed", "ntcp2", "wireguard", "openvpn", "ipsec", "consumer vpn", "lead",
                 "who to ask", "example.test"):
        assert term in sources, term


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 30, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 24
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("check.torproject.org", "metrics.torproject.org", "support.torproject.org", "community.torproject.org",
                 "spec.torproject.org", "i2p.net", "wireguard.com", "build.openvpn.net", "rfc-editor.org",
                 "docs.suricata.io", "docs.zeek.org", "documentation.wazuh.com", "docs.netgate.com",
                 "engineering.salesforce.com", "FoxIO-LLC/ja4", "attack.mitre.org", "unb.ca"):
        assert host in sources, host


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_pages_the_issue_names_are_cited_for_the_signals():
    sources = " ".join(r[1] for r in register_rows(text()))
    for item in ("torbulkexitlist", "collector.html", "onionoo.html", "censorship-7", "getting-bridges",
                 "pt-spec/architecture-overview", "tor-spec/preliminaries", "tor-spec/negotiating-channels",
                 "overview/threat-model", "overview/intro", "wireguard.com/protocol/", "openvpn-2.6/openvpn.8.html",
                 "rfc7296", "rfc8484", "rules/datasets.html", "rules/ja-keywords.html", "frameworks/intel.html",
                 "logs/ssl.html", "cdb-list.html", "system-inventory", "raw-filter-format.html", "aliases-types.html",
                 "T1090/003", "tls-fingerprinting-with-ja3", "using-tb-safely"):
        assert item in sources, item


def test_the_dated_research_and_its_limits_are_stated():
    body = text()
    assert "ISCXTor2016" in body and "2017" in body
    assert "I did not read the paper" in body
    assert "no accuracy claim" in body or "make no accuracy claim" in body
    assert "User-Agent" in body
    assert "2023" in body  # Chromium extension-order randomization, as the JA4 project reports it
    # The ATT&CK sub-technique id is not written in prose: the threat-framework test only allows ids its reference file lists.
    assert "multi-hop proxy sub-technique" in body and "12 May 2026" in body and "T1090.003" not in body


def test_the_policy_section_weighs_the_trade_offs_for_the_groups_the_issue_names():
    body = text()
    section = body.split("## Blocking, allow-listing or watching: a policy choice")[1].split("\n## ")[0]
    for word in ("employees", "schools", "libraries", "journalists"):
        assert word in section, word
    for option in ("Block", "Allow-list", "Watch", "Do nothing"):
        assert option in section, option
    assert "[The CIA triad]" in body or "The-CIA-Triad" in body
    assert "privacy" in section.lower() and "legal" in section.lower()
    assert "Check the law where you live" in body
    assert "nothing here is legal advice" in body.lower()
    assert "No country's law was checked" in body


def test_a_detection_is_a_lead_and_the_incident_angle_is_present():
    body = text()
    assert "a lead, not proof" in body.lower() or "lead, not proof" in body.lower()
    section = body.split("## A detection is a lead, not proof: the incident-response angle")[1].split("\n## ")[0]
    for word in ("who to ask", "record", "runbook", "contact tree", "do not accuse"):
        assert word in section.lower(), word
    assert "Business-Continuity-and-Disaster-Recovery-BCP-and-DR" in section
    assert "Wazuh-SIEM-and-Data-Pipelines" in body


def test_the_page_says_what_defenders_cannot_see_in_general_terms():
    body = text()
    section = body.split("## What defenders cannot see")[1].split("\n## ")[0]
    for word in ("content", "who", "bridge", "encrypted DNS", "endpoint"):
        assert word in section, word


def test_the_page_makes_no_evasion_how_to_or_illegal_content():
    body = text().lower()
    assert "no way to avoid detection" in body or "gives no way to avoid detection" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "evade detection", "bypass the filter", "bypass the firewall",
                   "get around the block", "unblock", "hide from your network", "avoid the sensor", "make tor look like"):
        assert banned not in body, banned
    assert "no onion or i2p service" in body or "no address of any onion or i2p service" in body


def test_the_page_states_no_posture_of_this_repository_and_no_maintainer_opinion():
    body = text().lower()
    for banned in ("twingate", "droplet", "doppler", "this project logs", "this repository logs", "our firewall",
                   "the maintainer", "in my opinion", "i recommend", "we recommend", "best vpn"):
        assert banned not in body, banned


def test_the_threat_model_comes_before_the_machinery():
    body = text()
    order = ["## What you will be able to do", "## The series, and what this page is part of",
             "## What the wiki already says (and the gap)", "## Why a defender might care, and who else is on these networks",
             "## The threat model, stated first", "## Where detection can happen", "## Tor: what is public and what is not",
             "## I2P: what is public and what is not", "## VPNs: ports, protocols and providers",
             "## DNS, SNI and TLS fingerprints, and their limits", "## Endpoint signals",
             "## Monitoring and alerting with the tools the wiki teaches", "## Known false positives and false negatives",
             "## Blocking, allow-listing or watching: a policy choice",
             "## A detection is a lead, not proof: the incident-response angle", "## What defenders cannot see",
             "## What this means for the series' message", "## Exercise: match a synthetic log to a synthetic relay list",
             "## Not verified, plainly", "## Claims register"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)
    for needed in ("### The relay list and the exit list", "### Bridges and pluggable transports", "### The traffic itself",
                   "### Suricata", "### Zeek", "### pfSense and other firewalls", "### Wazuh", "### DNS logs"):
        assert needed in body, needed
    assert "no silver bullet" in body and "Privacy is who can see in" in body


def test_what_the_wiki_already_teaches_is_stated_from_the_pages_and_the_gap_is_named():
    body = text()
    section = body.split("## What the wiki already says (and the gap)")[1].split("\n## ")[0]
    for page in ("IDS-and-IPS-Snort-and-Suricata", "Wazuh-SIEM-and-Data-Pipelines", "Packet-Filters-Compared",
                 "Logs-SIEM-and-Detection-Basics"):
        assert page in section, page
    assert "Zeek" in section and "no page in the wiki teaches it" in section.lower()
    ids = (WIKI / "IDS-and-IPS-Snort-and-Suricata.md").read_text(encoding="utf-8")
    wazuh = (WIKI / "Wazuh-SIEM-and-Data-Pipelines.md").read_text(encoding="utf-8")
    assert "ja3" in ids and "pfSense" in ids  # what the page says the IDS lesson teaches really is there
    assert "CDB" not in wazuh and "Syscollector" not in wazuh  # and the gap it names is real
    zeek_pages = [p.name for p in WIKI.glob("*.md") if "zeek" in p.read_text(encoding="utf-8").lower()
                  and p.name not in {"Glossary.md", NAME + ".md"} and "Detecting-and-Managing" not in p.name]
    assert not zeek_pages, f"the page says no wiki page mentions Zeek, but these do: {zeek_pages}"


def test_the_examples_for_each_tool_are_marked_as_unrun_shapes():
    body = text()
    for tool_heading in ("### Suricata", "### Zeek", "### pfSense and other firewalls", "### Wazuh"):
        section = body.split(tool_heading)[1].split("\n### ")[0].split("\n## ")[0]
        assert "UNVERIFIED" in section or "not run" in section.lower() or "never loaded" in section.lower(), tool_heading
    assert body.count("UNVERIFIED") >= 3


def test_the_exercise_is_predict_first_and_names_what_it_touches():
    body = text()
    section = body.split("## Exercise: match a synthetic log to a synthetic relay list")[1].split("\n## ")[0]
    assert "Predict" in section or "predict" in section
    assert "reads no file" in section and "opens no socket" in section
    assert "ground truth" in section.lower()
    assert "false positive" in section.lower() and "missed" in section.lower()


def test_the_lab_script_on_the_page_runs_and_prints_what_the_page_says():
    body = text()
    done = run_lab(lab_script(body))
    assert done.returncode == 0, done.stderr
    expected = LAB_OUTPUT.search(body)
    assert expected, "the expected output block is missing from the page"
    assert done.stdout.strip() == expected["out"].strip()


def test_the_printed_answers_match_a_hand_computation_and_an_independent_recomputation():
    code = lab_script(text())
    done = run_lab(code)
    assert done.returncode == 0, done.stderr
    got = table(done.stdout)
    # Worked by hand from the page's data (see the exercise): hits, true, false.
    assert got == {"A": (7, 3, 4), "B": (4, 3, 1), "C": (3, 3, 0), "D": (4, 3, 1), "E": (0, 0, 0), "F": (3, 2, 1)}
    assert "Parsed 22 filterlog lines (1 skipped)" in done.stdout
    assert "Tor connections in the log: 9" in done.stdout
    assert "Caught by C or D: 6" in done.stdout
    assert "Missed by every list rule: 3" in done.stdout
    assert "VPN connections in the log: 3; caught by F: 2" in done.stdout
    assert "Hosts to ask about (rule C): 192.0.2.21" in done.stdout
    # Cross-check with different code over the same data.
    exp = expected_from_data(code)
    assert exp["n"] == 22
    for rule in "ABCDE":
        assert len(exp[rule]) == got[rule][0], rule
    # The prose quotes the same numbers.
    body = text()
    for sentence in ("Rule A matched 7 connections and only 3 were Tor", "Rule C matched 3, all Tor",
                     "Rule E matched 0", "9 Tor connections", "6 were caught", "3 were missed"):
        assert sentence in body, sentence


def test_the_lab_guard_bites_when_the_port_check_or_the_age_check_is_removed():
    body = text()
    good = lab_script(body)
    base = run_lab(good).stdout
    no_port = good.replace("lambda c: (c[2], c[3]) in fresh_addrs", "lambda c: c[2] in relay_ips")
    assert no_port != good
    out = run_lab(no_port)
    assert out.returncode == 0, out.stderr
    assert table(out.stdout)["C"] == (7, 3, 4)
    assert out.stdout != base
    no_age = good.replace("lambda c: (c[2], c[3]) in fresh_addrs", "lambda c: (c[2], c[3]) in relay_addrs")
    out2 = run_lab(no_age)
    assert table(out2.stdout)["C"] == (4, 3, 1)
    assert out2.stdout != base


def test_the_script_is_standard_library_only_reads_no_file_and_opens_no_socket():
    code = lab_script(text())
    for banned in ("import socket", "urllib", "requests", "subprocess", "os.system", "open(", "ssl", "import os", "pathlib",
                   "eval(", "exec("):
        assert banned not in code, banned
    imports = set(re.findall(r"^(?:from|import) (\w+)", code, re.MULTILINE))
    assert imports <= {"datetime"}, imports
