# SPDX-License-Identifier: Apache-2.0
"""The hands-on Whonix and Qubes OS lesson: registered, honest about what was run, safe, diagrammed (issue 372).

docs/wiki/Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts.md follows the seven-page
Tor, I2P and VPN series. It has a Whonix exercise in an isolated lab, a Qubes OS exercise with a reading path for readers whose
hardware cannot run Qubes, and a paper exercise that joins the two. A step marked run that was not, a safety rule that is not up
front, an unmarked step, a command the documents never showed, a policy line that does not parse, a dead link, a missing
registration, a diagram with no alt text or a signature transcript that no longer matches what gpg prints would each teach or
reveal the wrong thing.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts"
PAGE = WIKI / f"{NAME}.md"
TOR = "How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services"
OPSEC = "OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits"
BROWSING = "The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix"
DARKNET = "The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN"
MONERO = "Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR"
OVERVIEW = "Tor-I2P-and-the-Darknet-Without-the-Myths"
DETECT = "Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View"
ONION_LAB = "Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive"
PAPER = "Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero"
VM_DESKTOP = "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options"
VM_MODELS = "Virtual-Machines-Containers-and-Cloud-Service-Models"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Documentation ranges (RFC 5737), loopback, the Whonix internal gateway address and its netmask as the Whonix pages print them,
# and the Whonix release number, which also has four dotted parts: nothing here is a real host.
ALLOWED_ADDR = re.compile(
    r"^(?:192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3}|127\.0\.0\.1|0\.0\.0\.0"
    r"|10\.152\.152\.(?:0|10)|255\.255\.192\.0|18\.2\.4\.2)$"
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
STEP_HEAD = re.compile(r"^### ((?:Whonix|Qubes) step (\d+): .+)$", re.MULTILINE)
MARKER = re.compile(r"^\*\*(Run on stand-in files, 2026-11-01|Not run)\.\*\*")
# Every Qubes command-line tool the page may show. Each one appears in a Qubes or Whonix document that was read; a tool that no
# document showed (a guess from memory) is not on the list.
QUBES_TOOLS = {
    "qvm-ls", "qvm-prefs", "qvm-copy", "qvm-move", "qvm-run", "qvm-create", "qvm-remove", "qvm-open-in-dvm", "qvm-features",
    "qvm-firewall", "qubes-policy-editor",
}
TOOL = re.compile(r"\b(qvm-[a-z-]+|qubes-[a-z-]+|qubesctl)\b")
POLICY_LINE = re.compile(r"^qubes\.[A-Za-z]+\s+(?:\*|\+\S+)\s+\S+\s+\S+\s+(?:allow|ask|deny)(?:\s+\S+=\S+)*$")
POLICY_FILE = re.compile(r"^[A-Za-z0-9_-]+$")
FIREWALL_POSTURE = ("firewall module", "default outbound", "the stack's rule", "rule list", "allows by default", "same inbound and outbound")
EVASION = ("avoid detection", "evade detection", "hide from your isp", "bypass the filter", "get around the block", "defeat the firewall")


def text() -> str:
    return page_text(PAGE)  # without the generated navigation and contents blocks


def section(body: str, heading: str, level: str = "##") -> str:
    """The text under a heading, up to the next heading of the same or a higher level."""
    start = body.index(f"{level} {heading}\n")
    rest = body[start + len(level) + len(heading) + 2:]
    stop = re.search(rf"\n#{{1,{len(level)}}} ", rest)
    return (rest[: stop.start()] if stop else rest).strip()


def steps(body: str) -> dict[str, str]:
    """Each 'Whonix step N' and 'Qubes step N' section, keyed by its heading text."""
    found = {}
    for m in STEP_HEAD.finditer(body):
        rest = body[m.end():]
        stop = re.search(r"\n#{2,3} ", rest)
        found[m[1]] = (rest[: stop.start()] if stop else rest).strip()
    return found


def unmarked_steps(sections: dict[str, str]) -> list[str]:
    return [h for h, s in sections.items() if not MARKER.match(s)]


def run_steps(sections: dict[str, str]) -> list[str]:
    return [h for h, s in sections.items() if s.startswith("**Run on stand-in files")]


def fenced(body: str) -> list[str]:
    """The text of every fenced code block, including blocks indented inside a list item."""
    return re.findall(r"^[ \t]*```[a-z]*\n(.*?)\n[ \t]*```", body, re.DOTALL | re.MULTILINE)


def tools_used(body: str) -> set[str]:
    return {t for block in fenced(body) if "mermaid" not in block[:20] for t in TOOL.findall(block)}


def unknown_tools(body: str) -> set[str]:
    return tools_used(body) - QUBES_TOOLS


def policy_lines(body: str) -> list[str]:
    return [ln.strip() for block in fenced(body) for ln in block.splitlines() if ln.strip().startswith("qubes.")]


def bad_policy_lines(body: str) -> list[str]:
    return [ln for ln in policy_lines(body) if not POLICY_LINE.match(ln)]


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


def tables(body: str) -> list[list[list[str]]]:
    """Every Markdown table in the text as a list of rows of cells (the header row first, the rule row dropped)."""
    out, cur = [], []
    for line in body.splitlines() + [""]:
        if line.startswith("|"):
            if not line.startswith("|---"):
                cur.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif cur:
            out.append(cur)
            cur = []
    return out


def table_after(body: str, marker: str) -> list[list[str]]:
    return tables(body[body.index(marker):])[0]


# ---- the banner, the safety rules, the markers -------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_run_offline_and_what_was_not():
    body = text()
    assert body.startswith("# Hands-on Whonix and Qubes OS: the gateway split, compartments, disposables and policy prompts")
    assert "Status: unverified draft, written from reading" in body
    assert DATE_READ in body
    run = body.split("**Run, offline only:**")[1].split("\n")[0]
    for thing in ("gpg", "sha512sum", "stand-in", "detached signature", "no network"):
        assert thing in run, thing
    banner = body.split("**Not run:**")[1].split("\n")[0]
    for thing in ("Whonix", "Qubes", "VirtualBox", "virtual machine", "Tor", "any network"):
        assert thing in banner, thing
    assert "runs the exercises on his own" in body and "reports what differs" in body
    assert "## Not verified, plainly" in body


def test_the_law_and_the_safety_rules_come_first_and_are_prominent():
    body = text()
    first_section = body.index("## What you will be able to do")
    head = body[:first_section]
    for needle in (
        "Check the law where you live",
        "Nothing here is legal advice",
        "isolated lab",
        "NAT",
        "never bridge",
        "clone",
        "No real accounts",
        "no real data",
        "time-boxed",
        "back up",
        "nothing here tests a machine, account or network that is not yours",
    ):
        assert needle in head, needle
    assert head.count("\n> ") >= 8, "the safety block is a prominent quote, not a footnote"
    assert head.index("Check the law where you live") < head.index("NAT"), "the law comes before the lab rules"


def test_every_step_says_whether_it_was_run_and_only_the_two_verification_steps_were():
    body = text()
    sections = steps(body)
    whonix = [h for h in sections if h.startswith("Whonix")]
    qubes = [h for h in sections if h.startswith("Qubes")]
    assert len(whonix) >= 8 and len(qubes) >= 8, (len(whonix), len(qubes))
    assert not unmarked_steps(sections), unmarked_steps(sections)
    assert run_steps(sections) == [
        "Whonix step 1: verify the download",
        "Qubes step 1: verify the installer",
    ], run_steps(sections)
    for prefix in ("Whonix", "Qubes"):
        numbers = [int(m[2]) for m in STEP_HEAD.finditer(body) if m[1].startswith(prefix)]
        assert numbers == list(range(1, len(numbers) + 1)), (prefix, numbers)


def test_the_step_marker_guard_bites():
    good = {"Whonix step 1: x": "**Not run.** Written from reading.", "Qubes step 1: y": "**Run on stand-in files, 2026-11-01.** ok"}
    assert not unmarked_steps(good) and run_steps(good) == ["Qubes step 1: y"]
    assert unmarked_steps({"Whonix step 2: z": "Do the thing."}) == ["Whonix step 2: z"]
    assert unmarked_steps({"Whonix step 2: z": "**Run.** yes"}) == ["Whonix step 2: z"]
    assert STEP_HEAD.findall("### Whonix step 2: z\n") and not STEP_HEAD.findall("### Whonix part 2: z\n")


def test_the_part_three_exercise_is_paper_only():
    part = section(text(), "Part 3: the two together, on paper")
    assert part.startswith("**Paper only.**") and "nothing to install" in part


def test_the_exercises_are_predict_first():
    body = text()
    assert body.count("**Predict.**") >= 10, body.count("**Predict.**")
    assert body.count("**Check.**") >= 10


# ---- links, registration, glossary --------------------------------------------------------------------------------------


def test_every_linked_wiki_page_exists_and_the_pages_the_issue_names_are_linked():
    body = text()
    links = set(LINK.findall(body))
    assert len(links) >= 12, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for needed in (OVERVIEW, TOR, BROWSING, OPSEC, MONERO, VM_DESKTOP, VM_MODELS, ONION_LAB, DETECT, PAPER, DARKNET):
        assert needed in links, needed


def test_no_capped_lesson_is_linked():
    # tests/test_blast_radius_lesson.py, tests/test_bcp_dr_lesson.py and tests/test_cia_triad_lesson.py cap how many pages link them.
    body = text()
    for capped in ("Plan-for-Failure-Blast-Radius", "Business-Continuity-and-Disaster-Recovery-BCP-and-DR",
                   "The-CIA-Triad-Confidentiality-Integrity-Availability"):
        assert capped not in body, capped


def test_the_lesson_is_registered_right_after_the_opsec_page_with_a_related_list():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    lines = nav.splitlines()
    index = next(i for i, row in enumerate(lines) if f"{{page: {NAME}," in row)
    assert f"{{page: {OPSEC}," in lines[index - 1], "the page sits right after the OPSEC page"
    line = lines[index]
    assert 'status: "draft"' in line and 'subgroup: "Tor, I2P, VPN and browsing"' in line
    assert nav.index("  privacy:") < nav.index(f"{{page: {NAME},") < nav.index("  grc:"), "the page sits in the privacy track"
    related = re.search(r"related: \[([^\]]*)\]", line)
    assert related, "the page needs a related list"
    names = [n.strip() for n in related[1].split(",")]
    assert 3 <= len(names) <= 6 and NAME not in names and len(set(names)) == len(names)
    for n in (BROWSING, OPSEC, MONERO):
        assert n in names, n
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
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


# ---- addresses, diagrams, register -------------------------------------------------------------------------------------


def test_no_onion_or_i2p_address_no_long_random_value_no_real_address_and_no_dash_character():
    body = text()
    assert len(ADDR.findall(body)) >= 6, "the guard collected too few addresses"
    assert not stray_addresses(body), set(stray_addresses(body))
    assert not address_shapes(body), address_shapes(body)
    assert "—" not in body and "–" not in body
    visible = re.sub(r"\]\([^)\s]+\)", "]()", body)  # link and picture targets are paths, not values
    runs = [r for r in LONG_RANDOM.findall(visible) if re.search(r"[0-9]", r) and re.search(r"[A-Za-z]", r)]
    assert not runs, runs


def test_the_address_guard_bites():
    assert stray_addresses("host 8.8.8.8") == ["8.8.8.8"]
    assert stray_addresses("host 10.0.0.1 and 10.152.152.10 and 127.0.0.1") == ["10.0.0.1"]
    assert not stray_addresses("Alice 192.0.2.10 and 203.0.113.50 and 198.51.100.7 and Whonix 18.2.4.2")
    assert address_shapes("go to " + "a" * 56 + ".onion")
    assert address_shapes("see irc.example.i2p")
    assert not address_shapes("<your-address>.onion")
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
    good = ("![Diagram, a Whonix Workstation reaches the network only through the Gateway on an internal network](images/a.png)\n\n<details>\n"
            "<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n</details>")
    assert diagram_problems(good, tmp_path) == ["picture missing: images/a.png"]
    (tmp_path / "images" / "a.png").write_bytes(b"x")
    assert not diagram_problems(good, tmp_path)
    assert diagram_problems(good.replace("Diagram, a Whonix Workstation reaches the network only through the Gateway on an internal network", "x"), tmp_path)
    too_long = "![" + "w" * (MAX_ALT + 1) + "](images/a.png)" + good.split("(images/a.png)")[1]
    assert diagram_problems(too_long, tmp_path)
    assert diagram_problems("![alt text long enough to pass](images/a.png)\n\n```mermaid\nflowchart LR\n```", tmp_path)


def test_the_diagrams_cover_the_required_topics():
    sources = " ".join(m["src"] for m in DIAGRAM.finditer(text())).lower()
    for term in ("gateway", "workstation", "internal network", "nat", "second adapter", "dom0", "sys-whonix", "anon-whonix",
                 "disposable", "ask", "deny", "offline", "template", "sys-net", "sys-firewall", "host"):
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
    for host in ("whonix.org", "kicksecure.com", "github.com/QubesOS/qubes-doc", "github.com/QubesOS/qubes-core-admin", "virtualbox.org"):
        assert host in sources, host
    observed = [r for r in rows if "Observed" in r[-1]]
    assert len(observed) >= 4, "the offline runs are registered as observed"
    assert any("37ae9d10a7/" in r[1] for r in rows), "the Qubes documentation is pinned to a commit"


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


# ---- the content the issue asks for ------------------------------------------------------------------------------------


def test_the_whonix_exercise_shows_the_split_and_checks_it_with_the_projects_own_pages():
    part = section(text(), "Part 1: Whonix in an isolated lab")
    for needle in (
        "Whonix-Gateway", "Whonix-Workstation", "internal network", "10.152.152.10", "case", "systemcheck", "Leak Tests",
        "fails closed", "ip -br addr", "ip route", "192.0.2.1", "Shut down the Gateway", "ping", "NOTIMP", "check.torproject.org",
    ):
        assert needle in part, needle
    assert "clone" in part and "snapshot" in part and "data loss" in part, "Whonix advises clones over VirtualBox snapshots"
    assert "Not attached" in part, "the failure demonstration never connects the extra adapter"
    assert "the Gateway is not the place for anonymous work" in part.replace("\n", " ") or "only in the Workstation" in part


def test_the_misconfiguration_table_names_each_leak_with_its_source():
    part = section(text(), "What leaks when the Workstation is misconfigured", "###")
    rows = table_after(part, "|")
    assert rows[0][0].strip(), "the first header cell is named"
    assert len(rows) >= 8, "header plus at least seven misconfigurations"
    joined = " ".join(" ".join(r) for r in rows).lower()
    for needle in ("second nat adapter", "host-only", "host", "gateway", "one workstation", "install", "wireless", "fails closed"):
        assert needle in joined, needle
    for row in rows[1:]:
        assert "Whonix" in row[-1] or "Kicksecure" in row[-1], row


def test_the_qubes_hardware_section_is_honest_and_offers_a_reading_path():
    part = section(text(), "What Qubes needs, honestly", "###")
    for needle in ("necessary, but not sufficient", "6 GB", "16 GB", "32 GB", "128 GB", "VT-d", "IOMMU", "not recommended",
                   "not supported", "USB flash drive", "AMD", "reading walkthrough", "Release 4.3", "Whonix 18"):
        assert needle in part, needle
    whonix_side = section(text(), "Choose your path by your hardware")
    for needle in ("1 GB", "10 GB", "8 GB", "VT-x", "AMD-V"):
        assert needle in whonix_side, needle
    assert "daily" in part.lower() and "back up" in part.lower()


def test_the_qubes_exercise_covers_compartments_a_disposable_a_copy_with_the_prompt_and_a_compromised_qube():
    body = text()
    qubes_part = section(body, "Part 2: Qubes OS compartments")
    for needle in ("lab-untrusted", "lab-vault", "lab-work", "dom0", "sys-whonix", "anon-whonix", "default-dvm", "QubesIncoming",
                   "Ctrl+Shift+C", "Ctrl+Shift+V", "30-lab-exercise", "qubes.Filecopy", "@anyvm", "ask", "deny", "not amnesic",
                   "more trusted to less trusted", "template", "covert"):
        assert needle in qubes_part, needle
    reach = section(body, "What a compromised qube can and cannot reach", "###")
    rows = table_after(reach, "|")
    assert rows[0][0].strip() and len(rows) >= 9, "a named first header cell and at least eight rows"
    joined = " ".join(" ".join(r) for r in rows).lower()
    for needle in ("network", "other qubes", "template", "dom0", "clipboard", "files", "covert", "hypervisor", "usb"):
        assert needle in joined, needle


def test_the_commands_and_policy_lines_on_the_page_are_the_ones_the_documents_showed():
    body = text()
    used = tools_used(body)
    assert len(used) >= 8, used
    assert not unknown_tools(body), unknown_tools(body)
    lines = policy_lines(body)
    assert len(lines) >= 2 and not bad_policy_lines(body), bad_policy_lines(body)
    assert "qubes.Filecopy * lab-untrusted lab-vault deny" in lines
    for name in re.findall(r"qubes-policy-editor (\S+)", body):
        assert POLICY_FILE.match(name), name


def test_the_command_and_policy_guards_bite():
    assert unknown_tools("```\nqvm-teleport work\nqvm-ls\n```") == {"qvm-teleport"}
    assert not unknown_tools("```\nqvm-ls\nqubes-policy-editor 30-x\n```")
    assert tools_used("no code here qvm-ls") == set()
    assert bad_policy_lines("```\nqubes.Filecopy * a b maybe\n```") == ["qubes.Filecopy * a b maybe"]
    assert bad_policy_lines("```\nqubes.Filecopy a b deny\n```")
    assert not bad_policy_lines("```\nqubes.Filecopy * a b deny\nqubes.ConnectTCP +22 a b allow target=c\n```")
    assert not POLICY_FILE.match("30 bad.policy") and POLICY_FILE.match("30-lab-exercise")


def test_the_connecting_exercise_links_the_monero_page_and_does_not_repeat_it():
    body = text()
    part = section(body, "Part 3: the two together, on paper")
    assert MONERO in set(LINK.findall(part))
    rows = table_after(part, "|")
    assert rows[0][0].strip() and len(rows) >= 8, "a named first header cell and at least seven boundaries"
    for banned in ("qubes.ConnectTCP +18081", "monero-wallet-ws", "monerod-ws", "xmr-node", "xmr-wallet", "unsigned_monero_tx"):
        assert banned not in body, banned
    assert "USB qube" in part and "answer" in part.lower()
    assert PAPER in set(LINK.findall(body)), "offline key generation on a live system is the other offline pattern"


def test_the_disposable_step_says_a_disposable_is_not_amnesic_and_not_a_privacy_tool():
    part = steps(text())["Qubes step 4: use a disposable"]
    for needle in ("not amnesic", "forensics", "Whonix", "does not claim"):
        assert needle in part, needle


def test_the_page_is_defensive_makes_no_evasion_how_to_and_states_no_repository_posture():
    body = text().lower()
    for phrase in FIREWALL_POSTURE:
        assert phrase not in body, phrase
    for phrase in EVASION:
        assert phrase not in body, phrase
    assert "educational and defensive" in body
    assert "docs/stages" not in body and "stacks/" not in body, "no repository path is described"


# ---- the one thing that was run: the stand-in verification --------------------------------------------------------------


def run(args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, check=False)


def test_the_stand_in_verification_on_the_page_behaves_as_the_page_says(tmp_path):
    assert shutil.which("gpg") and shutil.which("sha512sum"), "the page's run steps need gpg and sha512sum"
    home = tmp_path / "gnupg"
    empty = tmp_path / "gnupg-empty"
    work = tmp_path / "work"
    bad = tmp_path / "tampered"
    for d in (home, empty, work, bad):
        d.mkdir(mode=0o700)
    image = work / "Whonix-LXQt-standin.ova"
    image.write_text("stand-in file, not an image.\n", encoding="utf-8")
    (bad / image.name).write_text("stand-in file, not an image!\n", encoding="utf-8")
    base = ["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
    try:
        key = run([*base, "--homedir", str(home), "--quick-generate-key", "Stand-in <standin@example.invalid>", "rsa2048", "sign", "never"], work)
        assert key.returncode == 0, key.stderr
        sign = run([*base, "--homedir", str(home), "--armor", "--detach-sign", image.name], work)
        assert sign.returncode == 0, sign.stderr
        shutil.copy(work / f"{image.name}.asc", bad / f"{image.name}.asc")
        good = run(["gpg", "--homedir", str(home), "--verify-options", "show-notations", "--verify", f"{image.name}.asc", image.name], work)
        assert good.returncode == 0 and "Good signature" in good.stderr, good.stderr
        tampered = run(["gpg", "--homedir", str(home), "--verify-options", "show-notations", "--verify", f"{image.name}.asc", image.name], bad)
        assert tampered.returncode == 1 and "BAD signature" in tampered.stderr, tampered.stderr
        nokey = run(["gpg", "--homedir", str(empty), "-v", "--verify", f"{image.name}.asc", image.name], work)
        assert nokey.returncode == 2 and "No public key" in nokey.stderr, nokey.stderr
        data = image.read_bytes()
        stdin = subprocess.run(["gpg", "--homedir", str(home), "-v", "--verify", f"{image.name}.asc", "-"], cwd=work, input=data,
                               capture_output=True, check=False)
        assert stdin.returncode == 0 and b"Good signature" in stdin.stderr, stdin.stderr
        sums = run(["sha512sum", image.name], work)
        (work / "Whonix-LXQt-standin.sha512sums").write_text(sums.stdout, encoding="utf-8")
        (bad / "Whonix-LXQt-standin.sha512sums").write_text(sums.stdout, encoding="utf-8")
        ok = run(["sha512sum", "--strict", "--check", "Whonix-LXQt-standin.sha512sums"], work)
        assert ok.returncode == 0 and ok.stdout.strip() == f"{image.name}: OK", ok.stdout
        failed = run(["sha512sum", "--strict", "--check", "Whonix-LXQt-standin.sha512sums"], bad)
        assert failed.returncode == 1 and f"{image.name}: FAILED" in failed.stdout, failed.stdout
    finally:
        for d in (home, empty):
            subprocess.run(["gpgconf", "--homedir", str(d), "--kill", "gpg-agent"], check=False, capture_output=True)
    body = text()
    for printed in ("Good signature", "BAD signature", "No public key", "OK", "FAILED"):
        assert printed in body, printed
    assert "gpg --verify-options show-notations --verify" in body
    assert "sha512sum --strict --check" in body
