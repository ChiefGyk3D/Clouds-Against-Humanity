"""The attack surface lesson: its script runs and prints what the page shows, and its citations hold.

docs/wiki/Attack-Surface-List-Shrink-Measure.md cites repository files as evidence and teaches with a
loopback script. A script that does not run, or a cited file that does not exist, teaches the wrong thing.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "wiki" / "Attack-Surface-List-Shrink-Measure.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
PATH = re.compile(r"`((?:stacks|modules|scripts|tests|\.spacelift)/[A-Za-z0-9_./-]+)`")


def blocks(tag: str) -> list[str]:
    return [b for t, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if t == tag]


def test_the_loopback_script_prints_what_the_page_shows(tmp_path):
    scripts = blocks("python")
    assert len(scripts) == 1
    path = tmp_path / "door.py"
    path.write_text(scripts[0], encoding="utf-8")
    done = subprocess.run([sys.executable, "-I", str(path)], capture_output=True, text=True, timeout=60, cwd=tmp_path, check=False)
    assert done.returncode == 0, done.stderr
    shown = [b for b in blocks("text") if b.startswith("ports tried:")]
    assert len(shown) == 1
    assert done.stdout.strip() == shown[0].strip()


def test_the_script_only_ever_names_the_loopback_address():
    code = blocks("python")[0]
    addresses = re.findall(r"\"(\d+\.\d+\.\d+\.\d+)\"", code)
    assert addresses, "the guard collected nothing"
    assert set(addresses) == {"127.0.0.1"}


def test_the_guard_bites_on_a_foreign_address():
    sample = 'probe.connect_ex(("192.0.2.1", port))'
    assert set(re.findall(r"\"(\d+\.\d+\.\d+\.\d+)\"", sample)) != {"127.0.0.1"}


def test_every_repository_path_the_page_cites_exists():
    cited = sorted(set(PATH.findall(PAGE.read_text(encoding="utf-8"))))
    assert len(cited) >= 8, "the guard collected too little"
    missing = [c for c in cited if not (ROOT / c.rstrip("/")).exists()]
    assert not missing, missing


def test_the_page_states_the_authorization_rule_and_the_port_move_rule():
    text = PAGE.read_text(encoding="utf-8")
    assert "written permission" in text
    assert "## The port-move rule" in text
    assert "not protection" in text
