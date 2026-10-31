"""The 52cah-unattended-upgrades file must replace the stock origins list (#338).

A second apt config file ADDS to Unattended-Upgrade::Allowed-Origins; only the
`#clear` directive empties the stock list first. Measured in an Ubuntu 24.04
container: without it the effective list also holds the base release pocket.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = [
    ROOT / "modules" / "twingate-bootstrap" / "cloud-init.yaml.tftpl",
    ROOT / "modules" / "edge-host" / "cloud-init.yaml.tftpl",
]
CLEAR = "#clear Unattended-Upgrade::Allowed-Origins;"
OPEN = "Unattended-Upgrade::Allowed-Origins {"


def block(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    i = lines.index(OPEN)
    return lines[max(0, i - 1) : i + 1]


def test_something_was_collected():
    assert len(TEMPLATES) == 2 and all(t.exists() for t in TEMPLATES)


@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda p: p.parent.name)
def test_clear_directly_precedes_the_origins_list(tpl):
    assert block(tpl.read_text(encoding="utf-8")) == [CLEAR, OPEN]


def test_the_guard_bites_without_the_clear_line():
    text = TEMPLATES[0].read_text(encoding="utf-8").replace(CLEAR, "# gone")
    assert block(text) != [CLEAR, OPEN]
