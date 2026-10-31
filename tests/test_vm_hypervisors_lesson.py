# SPDX-License-Identifier: Apache-2.0
"""The virtual machines and hypervisors lesson: it is registered, honest about what was run, and safe to follow.

docs/wiki/Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md teaches a first VM, network modes and a
dated account of the VMware licensing changes. A broken link, a missing registration, a bridged-network command in a
lab page, a real address, or a vendor claim with no status would each teach the wrong thing.
"""

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "Page read", "General knowledge", "**est.**")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(tag: str) -> list[str]:
    return [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == tag]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(r[-1].startswith(w) or w in r[-1] for w in STATUS_WORDS)]


def unsafe_network_lines(commands: str) -> list[str]:
    return [l for l in commands.splitlines() if re.search(r"-(nic|netdev|net)\s+(bridge|tap)|\bbridge=|--network\s+bridged|nic\d?\s+bridged", l)]


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Virtual machines for beginners")
    assert "Status: unverified draft" in body
    assert "no hypervisor was installed and no guest was booted" in body
    assert "**Not run:**" in body and "2026-10-31" in body
    assert "Not verified, plainly" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav and 'status: "draft"' in nav.split(f"page: {NAME},")[1].split("\n")[0]
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-") for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    heads = {re.sub(r"[^a-z0-9-]", "", h.replace(" ", "-")) for h in heads}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_existing_pages_that_assume_a_vm_or_linux_host_link_the_lesson():
    users = [p.name for p in WIKI.glob("*.md") if p.name != PAGE.name and f"{NAME}.md" in p.read_text(encoding="utf-8")]
    skip = {"Glossary.md", "_Sidebar.md", "Reading-Order.md", "Contents.md"}
    inbound = [u for u in users if u not in skip]
    assert len(inbound) >= 4, inbound


def test_no_addresses_except_loopback_and_no_em_dashes():
    body = text()
    found = set(ADDR.findall(body))
    assert found <= {"127.0.0.1"}, found
    assert "127.0.0.1" in found, "the guard collected nothing"
    assert "—" not in body


def test_the_address_guard_bites():
    assert set(ADDR.findall("ping 192.0.2.7")) != {"127.0.0.1"}


def test_the_lab_commands_never_bridge_the_guest_onto_a_real_network():
    cmds = "\n".join(blocks("bash"))
    assert "qemu-system-x86_64" in cmds and "-nic user" in cmds, "the guard collected nothing"
    assert not unsafe_network_lines(cmds)


def test_the_network_guard_bites():
    assert unsafe_network_lines("qemu-system-x86_64 -nic bridge,br=br0")
    assert unsafe_network_lines("qemu-system-x86_64 -netdev tap,id=n0")
    assert not unsafe_network_lines("qemu-system-x86_64 -nic user,model=virtio-net-pci")


def test_the_safety_rule_names_the_three_core_steps():
    rule = text().split("## The safety rule for malware and recon labs")[1].split("## Free path")[0]
    assert "Isolate the network first" in rule
    assert "Snapshot a clean state first" in rule
    assert "Never bridge a hostile VM onto your home LAN" in rule


def test_the_checksum_step_comes_before_the_first_boot():
    body = text()
    assert body.index("sha256sum -c") < body.index("qemu-system-x86_64 -accel kvm")
    assert "do not boot an image that fails its check" in body
    digest = re.search(r"`([0-9a-f]{64})`", body)
    assert digest, "the example checksum is missing"


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 25, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_vmware_account_is_dated_and_cites_vendor_and_news_sources():
    body = text()
    section = body.split("## VMware after Broadcom: a dated account")[1].split("## The bigger options")[0]
    for date in ("2023-11-22", "2023-12-11", "May 2024", "2024-11-11", "2025-03-10", "2025-04-10"):
        assert date in section, date
    for needle in ("BBC News", "Ars Technica", "release notes", "**est.**"):
        assert needle in section, needle
    assert "not verified" in section.lower()
    assert "Read" in section


def test_the_page_names_the_apple_options_from_apples_own_pages():
    body = text()
    assert "Virtualization framework" in body and "macOS 11.0" in body
    assert "`container`" in body and "macOS 26" in body


@pytest.mark.skipif(shutil.which("qemu-img") is None, reason="qemu-img is not installed")
def test_exercise_3_runs_and_the_snapshot_round_trips(tmp_path):
    block = next(b for b in blocks("bash") if "qemu-img create" in b)
    script = block.replace("cd ~/vmlab", f"cd {tmp_path}")
    result = subprocess.run(["bash", "-eu", "-c", script], capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert "virtual size: 4 GiB" in result.stdout
    assert "clean-start" in result.stdout
    # the last listing, after the delete, shows no snapshot line after the final info block
    assert result.stdout.count("clean-start") == 1
