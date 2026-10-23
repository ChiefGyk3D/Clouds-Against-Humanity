"""The order of a new machine's first hour is stated the same way everywhere it is described.

Issue #232: update, baseline, harden, then applications. The stage guides and the edge design must
say it, the template's real structure must follow it (the
update before the connector install, the hardening switched on before the connector install), and
the edge design must record the install rule, the version pins and the reboot-slot window.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "modules" / "twingate-bootstrap" / "cloud-init.yaml.tftpl"
EDGE = ROOT / "docs" / "superpowers" / "specs" / "2026-10-19-edge-dmz-design.md"
LESSON = ROOT / "docs" / "wiki" / "First-Hour-on-a-New-System-Updates-and-Baseline.md"
GUIDES = [ROOT / "docs" / "stages" / n for n in ("01-access.md", "aws-access.md", "02-telemetry.md")]
ORDER = "update, baseline, harden, then applications"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_every_guide_and_the_edge_design_state_the_order():
    for p in GUIDES + [EDGE]:
        flat = re.sub(r"\s+", " ", read(p)).lower()
        assert ORDER in flat or "update (and switch on unattended security updates), take a baseline, harden, then applications" in flat, p.name


def test_the_template_follows_the_order():
    t = read(TEMPLATE)
    assert t.index("package_update: true") < t.index("package_upgrade: true") < t.index("\nruncmd:")
    assert "unattended-upgrades" in t.split("write_files:")[0]
    run = t.split("\nruncmd:")[1]
    harden = run.index("sshd -t && systemctl restart ssh")
    connector = run.index("apt-get install -yq twingate-connector")
    assert harden < connector, "hardening must be switched on before the connector is installed"


def test_edge_design_records_the_edge_rules():
    flat = re.sub(r"\s+", " ", read(EDGE))
    assert "No service is installed until its own stack is built and approved" in flat
    assert "Exact version pins from each project's releases" in flat
    assert "between 01:00 and 03:00 Eastern" in flat
    assert "04:00" in flat and "05:00" in flat
    assert "No two droplets share a minute" in flat
    assert "rings of devices" in flat


def test_slot_window_is_before_the_connector_windows():
    # The connector windows the design and the lesson cite come from the real droplet hardening page.
    hardening = read(ROOT / "docs" / "wiki" / "Droplet-Hardening.md")
    assert "04:00" in hardening and "05:00" in hardening
    assert "between 01:00 and 03:00 Eastern" in read(LESSON)
