# SPDX-License-Identifier: Apache-2.0
"""The patch management lesson keeps the promises it makes (issue #325).

docs/wiki/Patch-Management-and-Automatic-Security-Updates.md is partly run and partly written
from reading. These tests hold what a machine can hold: the honest status banner, a dated
claims-register row for every vendor page it cites, no real address or credential shape, the
triage script on the page runs and raises exactly the four alerts the page says it raises, and
the registrations. Each guard has a case proving it bites.
"""

import ipaddress
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
PAGE = WIKI / "Patch-Management-and-Automatic-Security-Updates.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
SECRET_SHAPE = re.compile(r"(?i)(password|passwd|token|secret)\s*[:=]\s*(?!\$|<|\{|\.\.\.|')[^\s`]{4,}")
VENDOR = re.compile(r"https://(?:documentation\.ubuntu\.com|manpages\.debian\.org|wiki\.debian\.org|dnf\.readthedocs\.io)/[^\s)|]+")
PATCH_GREMLIN = "https://github.com/ChiefGyk3D/Patch-Gremlin"


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def real_addresses(body: str) -> list[str]:
    bad = []
    for m in IPV4.findall(body):
        try:
            ip = ipaddress.ip_address(m)
        except ValueError:
            continue
        if ip.is_loopback or ip.is_unspecified:
            continue
        if not any(ip in net for net in DOC_NETS):
            bad.append(m)
    return bad


def register_rows(body: str) -> list[str]:
    section = body.split("## Claims register", 1)[1]
    return [line for line in section.splitlines() if line.startswith("|")]


def script() -> str:
    found = [b for tag, b in FENCE.findall(text()) if tag == "bash" and "uu-triage.sh - read" in b]
    assert len(found) == 1, f"expected one uu-triage.sh block, found {len(found)}"
    return found[0]


LOGS = {
    "ok": ["2026-10-29 06:19:10,100 INFO Starting unattended upgrades script"],
    "applied": [
        "2026-10-29 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-29 06:19:12,000 INFO Packages that will be upgraded: libc6 python3-jinja2",
        "2026-10-29 06:19:30,000 INFO All upgrades installed",
    ],
    "reboot": [
        "2026-10-29 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-29 06:19:31,000 WARNING Found /var/run/reboot-required, rebooting",
    ],
    "failed": [
        "2026-10-28 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-28 06:19:30,000 ERROR an old failure from a previous run",
        "2026-10-29 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-29 06:19:30,000 ERROR Installing the upgrades failed!",
    ],
    "oldfailure": [
        "2026-10-28 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-28 06:19:30,000 ERROR an old failure from a previous run",
        "2026-10-29 06:19:10,100 INFO Starting unattended upgrades script",
    ],
    "dryrun": [
        "2026-10-29 06:19:10,100 INFO Starting unattended upgrades script",
        "2026-10-29 06:19:12,000 INFO Packages that will be upgraded: zlib1g",
        "2026-10-29 06:19:13,000 INFO Option --dry-run given, *not* performing real actions",
    ],
    "empty": ["2026-10-29 06:19:10,100 DEBUG nothing useful"],
}


@pytest.fixture()
def triage(tmp_path):
    sh = tmp_path / "uu-triage.sh"
    sh.write_text(script())
    for name, lines in LOGS.items():
        (tmp_path / f"{name}.log").write_text("\n".join(lines) + "\n")

    def run(name, now="2026-10-29 12:00:00", flag=None, *extra):
        env = {
            "PATH": os.environ["PATH"],
            "TZ": "UTC",
            "REBOOT_FLAG": str(flag or tmp_path / "no-such-flag"),
            "TRIAGE_NOW": subprocess.run(["date", "-u", "-d", now, "+%s"], capture_output=True, text=True, check=True).stdout.strip(),
        }
        done = subprocess.run(["bash", str(sh), str(tmp_path / f"{name}.log"), *extra], capture_output=True, text=True, env=env, timeout=60, check=False)
        return done.returncode, done.stdout

    run.dir = tmp_path
    run.script = sh
    return run


def test_page_exists_and_opens_with_an_honest_status_banner():
    banner = next(line for line in text().splitlines() if line.startswith("> **"))
    assert "partly run" in banner.lower()
    assert "written from reading" in banner.lower()


def test_every_vendor_url_in_the_page_has_a_dated_register_row():
    body = text()
    rows = [r for r in register_rows(body) if VENDOR.search(r) or PATCH_GREMLIN in r]
    cited = set(VENDOR.findall(body))
    registered = set(VENDOR.findall("\n".join(rows)))
    assert len(registered) >= 4, "the register must cover Ubuntu, the man page, Debian and DNF"
    assert cited <= registered, cited - registered
    for r in rows:
        assert re.search(r"2026-10-30", r), r
        assert "Read" in r or "README read" in r, r


def test_patch_gremlin_is_linked_by_its_real_url_and_described_as_readme_only():
    body = text()
    assert PATCH_GREMLIN in body
    assert "I did not read its code" in body
    assert any(PATCH_GREMLIN in r and "code not read" in r for r in register_rows(body))


def test_no_real_address_and_no_credential_shape():
    body = text()
    assert real_addresses(body) == []
    assert SECRET_SHAPE.findall(body) == []


def test_guards_bite():
    assert real_addresses("host 8.8.8.8 and 192.0.2.5") == ["8.8.8.8"]
    assert SECRET_SHAPE.findall("token: abcd1234") != []
    assert SECRET_SHAPE.findall("token: $TOKEN") == []
    assert VENDOR.findall("see https://wiki.debian.org/UnattendedUpgrades.") != []
    assert VENDOR.findall("see https://example.org/page") == []


def test_the_four_alerts_are_raised_and_only_those(triage):
    code, out = triage("ok")
    assert (code, out.strip()) == (0, "OK nothing to report")
    code, out = triage("applied")
    assert code == 0 and "NOTICE applied: libc6 python3-jinja2" in out
    code, out = triage("reboot")
    assert code == 1 and "WARNING reboot" in out
    code, out = triage("failed")
    assert code == 2 and "CRITICAL failed: 1 ERROR" in out
    code, out = triage("empty")
    assert code == 2 and "stale: no run recorded" in out


def test_the_stale_alert_fires_only_past_the_limit(triage):
    assert triage("ok", "2026-10-30 06:00:00")[0] == 0  # 24 hours, inside the 36-hour default
    code, out = triage("ok", "2026-11-02 12:00:00")
    assert code == 2 and "newest run began 101 hours ago" in out
    assert triage("ok", "2026-10-30 06:00:00", None, "12")[0] == 2  # a tighter limit bites


def test_only_the_newest_run_counts(triage):
    code, out = triage("oldfailure")
    assert code == 0, out


def test_a_reboot_flag_file_raises_the_warning(triage):
    flag = triage.dir / "flag"
    flag.write_text("")
    code, out = triage("ok", flag=flag)
    assert code == 1 and "WARNING reboot" in out


def test_a_dry_run_is_not_reported_as_applied(triage):
    code, out = triage("dryrun")
    assert code == 0 and "dry run, nothing installed" in out and "applied:" not in out


def test_usage_and_unreadable_log_have_their_own_exit_codes(triage):
    bare = subprocess.run(["bash", str(triage.script)], capture_output=True, text=True, check=False)
    assert bare.returncode == 64
    missing = subprocess.run(["bash", str(triage.script), str(triage.dir / "nope.log")], capture_output=True, text=True, check=False)
    assert missing.returncode == 2


def test_the_script_is_read_only(triage):
    body = script()
    for word in ("rm ", "curl", "wget", "apt-get", "systemctl", "> /"):
        assert word not in body, word


def test_registered_everywhere():
    name = "Patch-Management-and-Automatic-Security-Updates.md"
    for page in ("_Sidebar.md", "Contents.md", "Reading-Order.md", "Droplet-Hardening.md"):
        assert name in (WIKI / page).read_text(), page
    assert "Patch-Management-and-Automatic-Security-Updates" in (WIKI / "_nav.yaml").read_text()
    glossary = (WIKI / "Glossary.md").read_text()
    for term in ("Allowed origins", "Needrestart", "Patch Gremlin", "Reboot-required flag", "Stale-host alert"):
        assert f"| **{term}** |" in glossary, term
