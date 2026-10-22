"""The baseline script on the first-hour lesson runs, and detects the drift the page says it detects.

docs/wiki/First-Hour-on-a-New-System-Updates-and-Baseline.md teaches an order (update, baseline,
harden, then applications) and a Bash script that records a baseline. A script that does not run,
or that misses a change, teaches the wrong thing. The test pulls the script out of the page, takes
a baseline, changes a throwaway copy of the inputs it can be pointed at (the output file only; the
script is read-only and never changes the system), and checks the comparison reports no drift on
two identical runs and a difference when a line is edited.
"""

import re
import subprocess
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "docs" / "wiki" / "First-Hour-on-a-New-System-Updates-and-Baseline.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
SECTIONS = ["os", "packages", "listening-ports", "users", "groups-with-admin-rights", "enabled-services", "firewall", "config-hashes"]


def script() -> str:
    found = [b for tag, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if tag == "bash" and "baseline.sh - write" in b]
    assert len(found) == 1, f"expected one baseline.sh block, found {len(found)}"
    return found[0]


def run(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(path), *args], capture_output=True, text=True, timeout=120, check=False)


@pytest.fixture()
def baseline(tmp_path):
    p = tmp_path / "baseline.sh"
    p.write_text(script())
    return p


def test_the_order_is_in_the_page_and_in_that_order():
    text = PAGE.read_text(encoding="utf-8")
    steps = ["1. Update, then turn on automatic updates", "2. Take a baseline", "3. Harden", "4. Applications and workloads"]
    positions = [text.index(s) for s in steps]
    assert positions == sorted(positions)


def test_snapshot_has_every_section(baseline, tmp_path):
    out = tmp_path / "a.txt"
    done = run(baseline, "snapshot", str(out))
    assert done.returncode == 0, done.stderr
    body = out.read_text()
    for name in SECTIONS:
        assert f"## {name}" in body


def test_compare_is_quiet_without_drift_and_loud_with_it(baseline, tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    assert run(baseline, "snapshot", str(a)).returncode == 0
    b.write_text(a.read_text())
    quiet = run(baseline, "compare", str(a), str(b))
    assert quiet.returncode == 0 and "no drift" in quiet.stdout
    b.write_text(a.read_text().replace("## users\n", "## users\nintruder uid=0 shell=/bin/sh\n"))
    loud = run(baseline, "compare", str(a), str(b))
    assert loud.returncode != 0 or "intruder" in loud.stdout
    assert "+intruder" in loud.stdout


def test_bad_usage_exits_nonzero(baseline):
    assert run(baseline).returncode == 2
    assert run(baseline, "snapshot").returncode == 2
