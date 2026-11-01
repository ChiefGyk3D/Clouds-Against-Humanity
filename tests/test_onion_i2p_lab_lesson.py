# SPDX-License-Identifier: Apache-2.0
"""The lab lesson on publishing a web server as a Tor onion service and an I2P site: registered, honest, safe, diagrammed.

docs/wiki/Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive.md follows the seven-page
Tor, I2P and VPN series. It shows an onion service and an I2P site as one more layer in front of an ordinary web server, with a
local lab and an optional cloud flag. A banner that claims more than was run, a safety rule that is not up front, an address in
the text, a key in the repository, a mistake without a check, a dead link, a missing registration, a diagram with no alt text
or a transcript that no longer matches the script would each teach or reveal the wrong thing.
"""

import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from onion_lab_fixtures import Clean, Leaky, serving
from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
LAB = ROOT / "labs" / "onion-lab"
NAME = "Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive"
PAGE = WIKI / f"{NAME}.md"
TOR = "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services"
I2P = "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database"
OPSEC = "OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits"
DARKNET = "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN"
BROWSING = "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix"
DETECT = "Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View"
OVERVIEW = "Tor-I2P-and-the-Darknet-Without-the-Myths"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Documentation ranges (RFC 5737), loopback and the all-zero wildcard the page explains: nothing here is a real host.
# Two Tor release numbers (0.4.8.10 on Ubuntu 24.04, 0.4.9.14 on the author's machine) also have four dotted parts.
ALLOWED_ADDR = re.compile(
    r"^(?:192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3}|127\.0\.0\.1|0\.0\.0\.0|0\.4\.8\.10|0\.4\.9\.14)$"
)
ONION = re.compile(r"\b[a-z2-7]{16,56}\.(?:onion|b32\.i2p)\b")
I2P_NAME = re.compile(r"\b(?!b32\b)[a-z0-9-]+\.i2p\b")
STATUS_WORDS = ("Read", "General knowledge", "**est.**", "Observed")
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
CLEAN_OUT = re.compile(r"clean fixture prints:\n\n```\n(?P<out>.*?)\n```", re.DOTALL)
LEAKY_OUT = re.compile(r"leaky fixture prints:\n\n```\n(?P<out>.*?)\n```", re.DOTALL)
MISTAKES = (
    "The web server listens on every interface",
    "The server names itself or its address",
    "The page pulls in clearnet resources",
    "The host also carries a personal identity",
    "A status page or a localhost-only rule is reachable",
)


# Phrases that would state what this repository's own firewall allows or denies.
FIREWALL_POSTURE = ("firewall module", "default outbound", "the stack's rule", "rule list", "allows by default", "same inbound and outbound")


def posture_hits(body: str) -> list[str]:
    return [p for p in FIREWALL_POSTURE if p in body.lower()]


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


def address_shapes(body: str) -> list[str]:
    """Anything shaped like an onion address, a base32 I2P address or a named .i2p site."""
    return ONION.findall(body) + I2P_NAME.findall(body)


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


def audit_output(handler, ss_template: str) -> str:
    """Run labs/onion-lab/check_origin.py against a loopback fixture and return what it prints, with the port shown as 8080."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_origin_for_page", LAB / "check_origin.py")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    with serving(handler) as port, tempfile.TemporaryDirectory() as d:
        ss = Path(d) / "ss.txt"
        ss.write_text(ss_template.format(port=port))
        buf = io.StringIO()
        with redirect_stdout(buf):
            module.main(["--port", str(port), "--ss-file", str(ss)])
    return buf.getvalue().replace(str(port), "8080").strip()


SS_LOOPBACK = "LISTEN 0 511 127.0.0.1:{port} 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
SS_WILDCARD = "LISTEN 0 511 0.0.0.0:{port} 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_run_offline_and_what_was_not():
    body = text()
    assert body.startswith("# Lab: publish a web server as a Tor onion service and an I2P site")
    assert "Status: unverified draft, written from reading" in body
    banner = body.split("**Not run:**")[1].split("\n")[0]
    assert DATE_READ in body
    for thing in ("an onion service", "i2pd", "Tor Browser", "I2P router", "real network"):
        assert thing in banner, thing
    run = body.split("**Run, offline only:**")[1].split("\n")[0]
    for thing in ("tor --verify-config", "nginx -t", "tofu test", "docker compose config", "check_origin.py"):
        assert thing in run, thing
    assert "runs the lab on his own" in body and "reports what differs" in body
    assert "## Not verified, plainly" in body


def test_the_safety_rules_come_first_and_are_prominent():
    body = text()
    first_section = body.index("## What you will be able to do")
    head = body[:first_section]
    for needle in (
        "Do not keep these services publicly reachable for long",
        "default-drop firewall",
        "no direct clearnet exposure of the origin",
        "logging and alerting",
        "patching",
        "key custody",
        "time-boxed",
        "build it, test it, tear it down",
        "service key",
        "Never publish or commit",
        "never paste any onion or I2P address",
        "a good firewall, a VLAN",
        "host isolation",
    ):
        assert needle in head, needle
    assert head.count("\n> ") >= 6, "the safety block is a prominent quote, not a footnote"
    assert "Check the law where you live" in head
    assert "Nothing here is legal advice" in body


def test_every_linked_wiki_page_exists_and_the_pages_the_issue_names_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 14, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (
        TOR, I2P, OPSEC, DARKNET, BROWSING, DETECT, OVERVIEW,
        "Patch-Management-and-Automatic-Security-Updates", "Packet-Filters-Compared-iptables-nftables-ufw-pf",
        "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet", "WordPress-at-Scale-CDN-WAF-and-CI",
        "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options", "Subnets-NAT-and-Firewalls-By-Hand",
    ):
        assert needed in links, needed


def test_the_page_says_which_web_server_it_chose_and_why():
    body = text()
    section = body.split("## Which web server, and why")[1].split("\n## ")[0]
    for needle in ("modules/docker-host", "stacks/30-workloads", "labs/wordpress-at-scale", "nginx", "1.30.6", "static", "why"):
        assert needle in section, needle
    assert "deploys no public web server" in section
    assert "Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon" in section


def test_the_lesson_is_registered_in_the_privacy_track_with_a_related_list():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = next(row for row in nav.splitlines() if f"{{page: {NAME}," in row)
    assert 'status: "draft"' in line
    assert 'subgroup: "Tor, I2P, VPN and browsing"' in line
    assert nav.index("  privacy:") < nav.index(f"{{page: {NAME},") < nav.index("  grc:"), "the page sits in the privacy track"
    related = re.search(r"related: \[([^\]]*)\]", line)
    assert related, "the page needs a related list"
    names = [n.strip() for n in related[1].split(",")]
    assert 3 <= len(names) <= 6 and NAME not in names and len(set(names)) == len(names)
    for n in (TOR, I2P, OPSEC):
        assert n in names, n
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special


def test_glossary_rows_point_at_real_headings_and_no_term_is_defined_twice():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-"))
             for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    terms = []
    mine = []
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| **"):
            terms.append(line.split("**")[1].lower())
            if f"{NAME}.md" in line:
                mine.append(line.split("**")[1].lower())
                anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert len(mine) >= 4, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    dupes = sorted({t for t in mine if terms.count(t) > 1})
    assert not dupes, dupes


def test_no_onion_or_i2p_address_no_long_random_value_no_real_address_and_no_em_dash():
    body = text()
    assert len(ADDR.findall(body)) >= 8, "the guard collected too few addresses"
    assert not stray_addresses(body), set(stray_addresses(body))
    assert not address_shapes(body), address_shapes(body)
    assert "—" not in body
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)  # link and picture targets are paths, not values
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs
    assert "<your-address>.onion" in body or "<the-address-you-read>.onion" in body, "placeholders, never an address"


def test_the_address_guard_bites():
    assert stray_addresses("host 8.8.8.8") == ["8.8.8.8"]
    assert stray_addresses("host 10.0.0.1 and 127.0.0.1") == ["10.0.0.1"]
    assert not stray_addresses("Alice 192.0.2.10 and 203.0.113.50 and 198.51.100.7 and 0.0.0.0")
    assert address_shapes("go to " + "a" * 56 + ".onion")
    assert address_shapes("x " + "b" * 52 + ".b32.i2p")
    assert address_shapes("see irc.example.i2p")
    assert not address_shapes("<your-address>.onion and <52 characters>.b32.i2p")
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
    (tmp_path / "images").mkdir()
    good = ("![Diagram, one web server with a clearnet door, an onion door and an I2P door in front of it](images/a.png)\n\n<details>\n"
            "<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path) == ["picture missing: images/a.png"]
    (tmp_path / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path)
    assert diagram_problems(good.replace("Diagram, one web server with a clearnet door, an onion door and an I2P door in front of it", "x"), tmp_path)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("origin", "127.0.0.1", "onion", "i2p", "clearnet", "tor browser", "i2p router", "second machine", "firewall",
                 "no inbound", "service key", "tear down", "check", "banner", "status page"):
        assert term in sources, term


def test_every_claims_register_row_has_a_status_a_source_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 24, "the guard collected too few rows"
    assert not rows_missing_status(text())
    sourced = [r for r in rows if URL.search(r[1])]
    assert len(sourced) >= 14
    for r in sourced:
        assert DATE_READ in r[2], r[0]
    sources = " ".join(r[1] for r in rows)
    for host in ("community.torproject.org", "gitlab.torproject.org", "riseup.net", "i2pd.readthedocs.io", "nginx.org",
                 "packages.ubuntu.com", "docker.io"):
        assert host in sources, host
    observed = [r for r in rows if "Observed" in r[-1]]
    assert len(observed) >= 4, "the offline runs are registered as observed"


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_config_files_the_page_walks_through_are_the_files_in_the_repository():
    body = text()
    for name in ("torrc.example", "nginx-onion-lab.conf", "i2pd-tunnels.conf", "i2pd.conf.example", "check_origin.py", "index.html", "404.html"):
        assert f"labs/onion-lab/{name}" in body, name
        assert (LAB / name).is_file(), name
    # The lines the page quotes are the lines in the files.
    torrc = (LAB / "torrc.example").read_text(encoding="utf-8")
    for line in ("HiddenServiceDir /var/lib/tor/onion-lab/", "HiddenServicePort 80 127.0.0.1:8080", "SocksPort 0"):
        assert line in body and line in torrc, line
    assert "listen 127.0.0.1:8080;" in body and "listen 127.0.0.1:8080;" in (LAB / "nginx-onion-lab.conf").read_text(encoding="utf-8")
    tunnels = (LAB / "i2pd-tunnels.conf").read_text(encoding="utf-8")
    for line in ("type = http", "host = 127.0.0.1", "port = 8080", "keys = onion-lab.dat"):
        assert line in body and line in tunnels, line


def test_the_lab_walks_build_test_and_tear_down_with_a_time_box():
    body = text()
    for heading in ("### Step 1: the origin", "### Step 2: the Tor onion service", "### Step 3: the I2P site",
                    "### Step 4: connect from a second machine", "### What the logs look like", "### Step 5: audit the origin",
                    "### Step 6: tear it down"):
        assert heading in body, heading
    order = [body.index(h) for h in ("### Step 1:", "### Step 2:", "### Step 3:", "### Step 4:", "### What the logs look like",
                                    "### Step 5:", "### Step 6:")]
    assert order == sorted(order)
    teardown = body.split("### Step 6: tear it down")[1].split("\n## ")[0]
    for needle in ("systemctl disable --now", "apt purge", "ss -ltn", "no way to recover", "delete"):
        assert needle in teardown, needle
    assert "two hours" in body and "alarm" in body


def test_the_page_connects_from_a_second_machine_with_tor_browser_and_an_i2p_router():
    body = text()
    section = body.split("### Step 4: connect from a second machine")[1].split("\n### ")[0]
    for needle in ("Tor Browser", "I2P router", "4444", "http://<your-address>.onion/", ".b32.i2p", "second", "web console"):
        assert needle in section, needle


def test_the_logs_section_shows_shapes_marked_as_constructed_and_says_what_the_origin_log_cannot_tell_you():
    body = text()
    section = body.split("### What the logs look like")[1].split("\n### ")[0]
    for needle in ("constructed", "not captured", "journalctl -u tor@default", "/var/log/i2pd/i2pd.log", "127.0.0.1", "X-I2P",
                   "no visitor address"):
        assert needle in section, needle


def test_each_mistake_has_a_row_with_a_check_and_the_check_exists():
    body = text()
    section = body.split("## The mistakes that expose a service, and how to check each one")[1].split("\n## ")[0]
    header = next(line for line in section.splitlines() if line.startswith("|"))
    assert header.split("|")[1].strip() == "Mistake", "the first header cell is named"
    for mistake in MISTAKES:
        row = next((line for line in section.splitlines() if line.startswith("|") and mistake in line), None)
        assert row, mistake
        assert len([c for c in row.strip("|").split("|") if c.strip()]) >= 4, mistake
    for check in ("origin_exposure", "header_problems", "body_problems", "exposed_paths", "ss -ltn"):
        assert check in section, check
    checker = (LAB / "check_origin.py").read_text(encoding="utf-8")
    for fn in ("origin_exposure", "header_problems", "body_problems", "exposed_paths"):
        assert f"def {fn}(" in checker, fn
    assert "Tor connects from 127.0.0.1" in section or "Tor connects from the loopback address" in section


def test_the_audit_transcripts_on_the_page_are_what_the_script_prints():
    body = text()
    clean = CLEAN_OUT.search(body)
    leaky = LEAKY_OUT.search(body)
    assert clean and leaky, "both transcripts are on the page"
    assert clean["out"].strip() == audit_output(Clean, SS_LOOPBACK)
    assert leaky["out"].strip() == audit_output(Leaky, SS_WILDCARD)
    assert "0 problems" in clean["out"] and "6 problems" in leaky["out"]


def test_keys_are_treated_as_secrets_on_the_page():
    body = text()
    section = body.split("## Keys are secrets")[1].split("\n## ")[0]
    for needle in ("defines the address", "hs_ed25519_secret_key", "0700", "no revocation", "never", "encrypted", "client authorization",
                   "accesslist", "onion-lab.dat", "user_data"):
        assert needle in section, needle


def test_the_cloud_section_describes_a_default_off_flag_and_applies_nothing():
    body = text()
    section = body.split("## Form 2: the optional cloud flag in OpenTofu")[1].split("\n## ")[0]
    for needle in ("onion_service_enabled", "workload_enabled", "onion_origin_image", "default off", "nothing is applied",
                   "tofu test", "mocked", "cost gate", "no approval", "ReachableAddresses", "127.0.0.1:8080",
                   "No port is opened", "I2P is not wired"):
        assert needle in section, needle
    # The numbers the page quotes are the numbers in the tests.
    tests = (ROOT / "modules" / "docker-host" / "tests" / "docker-host.tftest.hcl").read_text(encoding="utf-8")
    assert "the_onion_flag_renders_a_loopback_origin_and_a_tor_that_only_forwards_to_it" in tests
    assert "the_onion_flag_with_the_master_switch_changes_no_firewall_rule" in (ROOT / "stacks" / "30-workloads" / "tests" / "workloads.tftest.hcl").read_text(encoding="utf-8")


def test_the_on_premises_section_names_the_protections_and_stops_where_the_page_stops():
    body = text()
    section = body.split("## On premises: what proper infrastructure means, and where this page stops")[1].split("\n## ")[0]
    for needle in ("firewall", "VLAN", "isolat", "logging", "patch", "key", "Subnets-NAT-and-Firewalls-By-Hand",
                   "Packet-Filters-Compared-iptables-nftables-ufw-pf", "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet",
                   "Patch-Management-and-Automatic-Security-Updates", "this page stops"):
        assert needle in section, needle


def test_the_threat_model_comes_before_the_machinery():
    body = text()
    order = ["## What you will be able to do", "## The series, and what this page is part of", "## Which web server, and why",
             "## The idea: one more layer in front of an ordinary web server", "## The threat model, stated first",
             "## Form 1: a local lab on a VM or a Raspberry Pi", "## The mistakes that expose a service, and how to check each one",
             "## Keys are secrets", "## Form 2: the optional cloud flag in OpenTofu",
             "## On premises: what proper infrastructure means, and where this page stops", "## Exercises",
             "## Not verified, plainly", "## Claims register"]
    positions = [body.index(h) for h in order]
    assert positions == sorted(positions)


def test_the_page_is_defensive_makes_no_evasion_how_to_and_states_no_repository_posture():
    body = text().lower()
    assert "defensive and educational" in body
    for banned in ("buy drugs", "vendor shop", "how to buy", "evade detection", "bypass the filter", "get around the block",
                   "hide from your network", "avoid the sensor", "make tor look like", "darknet market of your own",
                   "bulletproof", "sell "):
        assert banned not in body, banned
    # No claim about how well this repository's own hosts, firewall, secrets or access are protected.
    for banned in ("twingate", "doppler", "spacelift", "our firewall", "this project's firewall", "this repository is secure",
                   "this project is secure", "is hardened", "are hardened", "zero trust", *FIREWALL_POSTURE):
        assert banned not in body, banned
    assert posture_hits("the firewall module's default outbound list is the common web ports") == ["firewall module", "default outbound"]
    assert posture_hits("the tests compare the stack's rule list with the flag on and off") == ["the stack's rule", "rule list"]
    assert posture_hits("the outbound ports the firewall module allows by default") == ["firewall module", "allows by default"]
    assert not posture_hits("set it to whatever your own outbound rules allow")


def test_the_exercises_are_predict_first_and_name_what_they_touch():
    body = text()
    section = body.split("## Exercises")[1].split("\n## ")[0]
    assert section.count("### Exercise") >= 4
    assert "Predict" in section or "predict" in section
    assert "touches no network" in section or "nothing leaves your machine" in section
    assert "check_origin.py" in section
