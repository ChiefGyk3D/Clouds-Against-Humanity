"""requirements-dev.txt must mirror the pytest and pyyaml pins CI installs."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"
DEV = ROOT / "requirements-dev.txt"
TOOLS = ("pytest", "pyyaml")


def pins(text: str) -> dict[str, str]:
    """Map each of TOOLS to the version pinned with == in the text."""
    found = {}
    for name in TOOLS:
        match = re.search(rf"(?im)(?<![\w-]){name}==([0-9][\w.]*)", text)
        if match:
            found[name] = match.group(1)
    return found


def ci_install_command() -> str:
    lines = [
        line
        for line in CI.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("install-command:")
    ]
    assert len(lines) == 1, "expected exactly one install-command in ci.yml"
    return lines[0]


def test_ci_pins_every_tool_and_dev_requirements_match():
    ci = pins(ci_install_command())
    dev = pins(DEV.read_text(encoding="utf-8"))
    assert set(ci) == set(TOOLS), f"CI must pin {TOOLS} with ==, found {ci}"
    assert dev == ci, f"requirements-dev.txt {dev} differs from ci.yml {ci}"


def test_guard_bites_on_drift_and_on_an_unpinned_tool():
    ci = pins("install-command: pip install pytest==9.2.0 pyyaml==6.0.2")
    assert pins("pytest==9.2.1\npyyaml==6.0.2\n") != ci
    assert pins("install-command: pip install pytest pyyaml==6.0.2") != ci
    assert pins("pytest==9.2.0\npyyaml==6.0.2\npytest-xdist==3.8.0\n") == ci
