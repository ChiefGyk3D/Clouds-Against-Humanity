# SPDX-License-Identifier: Apache-2.0
"""The how-a-VPN-works lesson: registered, honest about what was read and run, diagrammed, and safe to read.

docs/wiki/How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md explains the tunnel, what it
hides and what it does not, with seven diagrams and two free exercises. A banner that claims more than was run, a dead
link, a missing registration, an address outside the documentation ranges, a claim with no status or date, a diagram
with no alt text, no source or no picture, a vendor named without having been read, or a lab script that no longer
prints what the page says would each teach or reveal the wrong thing.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves"
PAGE = WIKI / f"{NAME}.md"
OVERVIEW = "Tor-I2P-and-the-Darknet-Without-the-Myths"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Documentation ranges (RFC 5737), the loopback addresses the local test uses, and the two route prefixes that mean "all".
ALLOWED_ADDR = re.compile(r"^(?:192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3}|127\.0\.0\.[0-3]|0\.0\.0\.0|127\.0\.0\.0)$")
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
EXPECTED_DIAGRAMS = 7
DATE_READ = "2026-11-01"
# A long run of base32 or hex characters next to a key-like word is what the repository secret scan flags.
LONG_RANDOM = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
LAB_BLOCK = re.compile(r"```python\n(?P<code>\"\"\"vpn_lab\.py.*?)\n```", re.DOTALL)
LAB_OUTPUT = re.compile(r"it printed:\n\n```\n(?P<out>.*?)\n```", re.DOTALL)
# Brands the page does not mention because it read nothing from them. Only the two audited providers are named.
OTHER_BRANDS = ("nordvpn", "proton vpn", "protonvpn", "surfshark", "private internet access", "cyberghost", "ivpn",
                "tunnelbear", "windscribe", "purevpn", "hotspot shield", "ipvanish", "hidemyass", "tailscale")


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


def test_the_banner_says_it_was_written_from_reading_and_no_vpn_was_run():
    body = text()
    assert body.startswith("# How a VPN works")
    assert "Page 1 of a seven-page series" in body
    assert "Status: unverified draft, written from reading" in body
    assert "No VPN was run" in body
    assert "**Not run:**" in body and DATE_READ in body
    assert "## Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_finished_siblings_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 12, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        OVERVIEW,
        "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services",
        "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database",
        "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN",
        "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero",
        "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys",
        "Why-ZTNA-Not-a-VPN",
        "IPv6-Adoption-and-Handling-It-Safely",
    ):
        assert needed in links, needed


def test_the_unwritten_series_pages_are_named_in_plain_text_not_linked():
    body = text()
    for plain in ("privacy, security and anonymity and why there is no silver bullet", "the browsing setups compared",
                  "operational security for Tor and I2P", "detecting and managing Tor, I2P and VPN traffic on a network"):
        assert plain in body, plain
    # The only wiki pages with series names in their targets are the finished ones.
    linked_series = {t for t in LINK.findall(body) if re.search(r"Browsing|OPSEC-for|Detecting|Silver", t)}
    assert not linked_series, linked_series


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
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 8, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)


def test_only_documentation_and_loopback_addresses_no_onion_names_long_random_values_or_em_dashes():
    body = text()
    assert len(ADDR.findall(body)) >= 10, "the guard collected too few addresses"
    assert not stray_addresses(body), set(stray_addresses(body))
    assert not ONION.findall(body)
    assert "—" not in body
    # URLs and the register's identifiers are short; a long random-looking run would trip the secret scan.
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)  # link and picture targets are paths, not values
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs


def test_the_address_guard_bites():
    assert stray_addresses("host 8.8.8.8") == ["8.8.8.8"]
    assert stray_addresses("host 10.0.0.1 and 192.0.3.1") == ["10.0.0.1", "192.0.3.1"]
    assert not stray_addresses("Alice 192.0.2.10 and 203.0.113.50 and 127.0.0.2 and 0.0.0.0/0")
    assert ONION.findall("go to " + "a" * 56 + ".onion")
    assert LONG_RANDOM.findall("x" + "a1" * 20)


def test_placeholders_are_alice_and_example_test():
    body = text()
    assert "Alice" in body and "example.test" in body and "alice.example.test" in body
    assert "192.0.2.10" in body and "203.0.113.50" in body
    for real in ("example.com", "example.org", "example.net"):
        assert real not in body, real


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
    good = ("![Diagram, a packet through a tunnel and what each hop sees](images/a.png)\n\n<details>\n"
            "<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path, wiki) == ["picture missing: images/a.png"]
    (wiki / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path, wiki)
    assert diagram_problems(good.replace("Diagram, a packet through a tunnel and what each hop sees", "x"), tmp_path, wiki)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path, wiki)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("local network", "internet provider", "vpn provider", "example.test", "encrypt", "outer packet",
                 "wireguard", "openvpn", "ipsec", "consumer vpn", "corporate vpn", "zero trust", "controller",
                 "dns leak", "ipv6 leak", "cookie"):
        assert term in sources, term


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 24
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("wireguard.com", "man7.org", "build.openvpn.net", "rfc-editor.org", "datatracker.ietf.org",
                 "ssd.eff.org", "coveryourtracks.eff.org", "petsymposium.org", "leviathansecurity.com",
                 "nvd.nist.gov", "cure53.de", "mullvad.net", "help.netflix.com", "tcpdump.org", "freedesktop.org"):
        assert host in sources, host


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_rfcs_and_protocol_pages_the_issue_names_are_cited():
    sources = " ".join(r[1] for r in register_rows(text()))
    for item in ("wireguard.com/protocol/", "wireguard.com/known-limitations/", "build.openvpn.net/man/openvpn-2.6/",
                 "rfc4301", "rfc4303", "rfc7296", "rfc5737", "rfc6761", "rfc9849", "Why-ZTNA-Not-a-VPN.md"):
        assert item in sources, item


def test_the_audit_reports_are_dated_scoped_and_not_a_ranking():
    body = text()
    assert "2024-06-27" in body and "2022-09-22" in body
    for scope_word in ("two staging servers", "Did **not** cover a source review", "not production"):
        assert scope_word in body, scope_word
    assert "**not** because of any view about the companies" in body
    assert "I read no other audit" in body
    assert "no inference about any provider not named" in body
    rows = [r for r in register_rows(body) if "cure53.de" in r[1]]
    assert len(rows) == 2
    lower = body.lower()
    for brand in OTHER_BRANDS:
        assert brand not in lower, brand
    for banned in ("best vpn", "top vpn", "fastest vpn", "we recommend", "i recommend", "recommended vpn"):
        assert banned not in lower, banned


def test_dated_cases_are_dated_and_the_vendor_account_is_marked_unconfirmed():
    body = text()
    assert "CVE-2024-3661" in body and "2024-05-06" in body and "2026-07-28" in body
    assert "That is the provider's account" in body
    row = next(r for r in register_rows(body) if "search warrant" in r[0])
    assert "not confirmed elsewhere" in row[2]


def test_the_page_makes_no_evasion_how_to_or_illegal_content():
    body = text().lower()
    assert "no way around a block, a paywall or a rule" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "evade detection", "bypass the filter", "get around geo",
                   "unblock netflix", "watch region-locked"):
        assert banned not in body
    assert "no onion or i2p service" in body or "no address of any onion or i2p service" in body


def test_the_law_note_tells_learners_to_check_their_jurisdiction():
    body = text()
    assert "Check the law where you live" in body
    assert "nothing here is legal advice" in body.lower()
    assert "No country's law was checked" in body


def test_the_threat_model_comes_before_the_machinery():
    body = text()
    order = ["## The idea in one paragraph", "## The threat model, stated first",
             "## The path of a packet, without a VPN and with one", "## Inside the tunnel: encapsulation",
             "## WireGuard, OpenVPN and IPsec in plain terms", "## Three things called",
             "## What a VPN moves: trust from your ISP to the provider", "## What a VPN protects",
             "## What a VPN does not protect", "## No-logs claims, and what an audit does and does not prove",
             "## VPNs and the law, and terms of service, in general terms", "## Jurisdictions",
             "## Marketing myths, checked", "## What this means for the series' message", "## Exercises",
             "## Not verified, plainly", "## Claims register"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)
    for needed in ("### The provider sees what your ISP used to see",
                   "### Accounts, cookies and fingerprints still identify you", "### Payment and account identity",
                   "### DNS and IPv6 leaks", "### The kill switch, and what failing open looks like",
                   "### A dated case: TunnelVision"):
        assert needed in body, needed
    assert "no silver bullet" in body and "Privacy is who can see in" in body


def test_both_free_exercises_are_present_and_say_what_they_touch():
    body = text()
    assert "### Exercise 1: check your own machine for DNS and IPv6 leaks" in body
    assert "### Exercise 2: compare what a destination sees with and without a relay" in body
    assert "Linux only" in body
    assert "sends nothing to a leak-test website" in body
    assert "a model, not a VPN" in body
    for tool in ("ip route get", "ip -6 route get", "resolvectl status", "tcpdump", "getent ahosts"):
        assert tool in body, tool


def test_the_lab_script_on_the_page_runs_and_prints_what_the_page_says():
    body = text()
    done = run_lab(lab_script(body))
    assert done.returncode == 0, done.stderr
    expected = LAB_OUTPUT.search(body)
    assert expected, "the expected output block is missing from the page"
    assert done.stdout.strip() == expected["out"].strip()
    assert "Different source addresses at the destination: 2" in done.stdout
    assert "Different cookies at the destination: 1" in done.stdout


def test_the_lab_guard_bites_when_the_relay_does_not_change_the_address():
    body = text()
    mutated = lab_script(body).replace("source_address=(RELAY, 0)", "source_address=(ALICE, 0)")
    assert mutated != lab_script(body)
    done = run_lab(mutated)
    assert done.returncode == 0, done.stderr
    assert "Different source addresses at the destination: 1" in done.stdout
    assert done.stdout.strip() != LAB_OUTPUT.search(body)["out"].strip()


def test_the_script_uses_only_loopback_and_no_network_calls_beyond_it():
    code = lab_script(text())
    hosts = set(re.findall(r'"(\d{1,3}(?:\.\d{1,3}){3})"', code))
    story_labels = {"192.0.2.10", "203.0.113.50"}  # documentation addresses used only as printed labels
    assert hosts - story_labels == {"127.0.0.1", "127.0.0.2", "127.0.0.3"}
    assert story_labels <= hosts
    for banned in ("urllib", "requests", "socket.create_connection", "subprocess", "os.system", "ssl"):
        assert banned not in code, banned
