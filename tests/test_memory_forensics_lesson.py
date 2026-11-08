# SPDX-License-Identifier: Apache-2.0
"""The memory forensics lesson: it is registered, honest about what was run, and safe to follow.

docs/wiki/Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md teaches acquiring a lab VM's RAM and
reading it with Volatility 3. A broken link, a missing registration, a claim with no status, a real address, or a
command that bridges the lab guest onto a real network would each teach the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "General knowledge", "**est.**")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def bridged_lines(commands: str) -> list[str]:
    return [l for l in commands.splitlines() if re.search(r"-(nic|netdev|net)\s+(bridge|tap)|\bbridge=", l)]


def test_the_page_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Memory forensics: acquiring RAM")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-11-07" in body
    assert "Volatility 3 2.28.2" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 4, "the guard collected too few links"
    assert not sorted(t for t in links if not (WIKI / f"{t}.md").exists())


def test_the_lesson_is_registered_in_the_digital_forensics_subgroup():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in line and 'subgroup: "Digital forensics"' in line
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 4


def test_glossary_rows_point_at_real_headings():
    heads = set()
    for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE):
        heads.add(re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-")))
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_addresses_except_loopback_and_no_em_dashes():
    body = text()
    found = set(ADDR.findall(body))
    assert found == {"127.0.0.1"}, found
    assert "—" not in body


def test_the_callsign_and_machine_names_are_placeholders():
    body = text()
    assert "N0TST" in body
    assert r"local-hostname: lab\n" in body


def test_the_guest_is_never_bridged_onto_a_real_network():
    cmds = "\n".join(b for t, b in FENCE.findall(text()) if t == "bash")
    assert "-nic user" in cmds and "hostfwd=tcp:127.0.0.1" in cmds, "the guard collected nothing"
    assert not bridged_lines(cmds)


def test_the_bridge_guard_bites():
    assert bridged_lines("qemu-system-x86_64 -nic bridge,br=br0")
    assert not bridged_lines("qemu-system-x86_64 -nic user,model=virtio-net-pci")


def test_the_checksum_is_checked_before_the_first_boot():
    body = text()
    assert body.index("sha512sum -c sums") < body.index("qemu-system-x86_64 -accel kvm")
    assert "do not boot the image" in body


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_license_and_version_are_stated_with_dates():
    body = text()
    assert "Volatility Software License, Version 1.0" in body
    assert "2.28.2" in body and "2026-09-17" in body


def test_the_page_names_the_plugins_it_ran():
    body = text()
    for plugin in ("linux.pslist.PsList", "linux.psscan.PsScan", "linux.sockstat.Sockstat", "linux.malware.malfind.Malfind", "windows.psscan.PsScan", "windows.netscan.NetScan"):
        assert plugin in body, plugin


def test_siblings_and_firmware_lessons_are_linked_and_the_pages_exist():
    # Was: siblings are plain text until they merge. They are on main now, so each is a link to a page that exists.
    body = re.sub(r"<!-- BEGIN GENERATED .*?<!-- END GENERATED [^>]*-->", "", text(), flags=re.DOTALL)
    links = set(LINK.findall(body))
    for prefix in (
        "Digital-Forensics-Foundations",
        "Disk-Forensics",
        "Network-Log-and-Timeline-Forensics",
        "DFIR-Toolkits",
        "Device-Firmware-Security",
        "Open-Firmware",
    ):
        hits = [t for t in links if t.startswith(prefix)]
        assert hits, prefix
        assert all((WIKI / f"{t}.md").exists() for t in hits), prefix
    assert "plain text until they merge" not in body
