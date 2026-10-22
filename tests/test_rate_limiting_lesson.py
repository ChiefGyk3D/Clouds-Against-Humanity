"""The simulations on the rate limiting lesson run, and print what the page says they print.

docs/wiki/Rate-Limiting-at-Every-Layer.md teaches with Python scripts the learner saves from the page.
Exercises 1 and 2 are simulations on a pretend clock, so their output is exact and is compared with the
output block printed on the page. Exercise 8 starts a tiny API on 127.0.0.1 (a random free port) and uses
the real clock, so only the shape of its output is checked. Nothing leaves the machine.
"""

import re
import subprocess
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Rate-Limiting-at-Every-Layer.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def blocks(tag: str) -> list[str]:
    return [b for t, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if t == tag]


def script(marker: str) -> str:
    found = [b for b in blocks("python") if b.startswith(marker)]
    assert len(found) == 1, f"expected one python block starting {marker!r}, found {len(found)}"
    return found[0]


def run(code: str, tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    path.write_text(code, encoding="utf-8")
    done = subprocess.run([sys.executable, "-I", str(path)], check=False, capture_output=True, text=True, timeout=60, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip("\n")


def printed(first_line: str) -> str:
    found = [b.strip("\n") for b in blocks("text") if b.strip("\n").startswith(first_line)]
    assert len(found) == 1, f"expected one text block starting {first_line!r}, found {len(found)}"
    return found[0]


def test_algorithms_print_what_the_page_shows(tmp_path):
    out = run(script("# algos.py"), tmp_path, "algos.py")
    assert out == printed("Scenario 1: 12 requests at t=0")
    # The point of the lesson: only the fixed window lets ten through across a boundary.
    scenario2 = out.split("Scenario 2")[1].split("Scenario 3")[0]
    assert re.search(r"fixed window\s+allowed 10 of 10", scenario2)
    assert re.search(r"sliding window log\s+allowed  5 of 10", scenario2)
    assert re.search(r"token bucket \(cap 5\)\s+allowed  5 of 10", scenario2)


def test_a_client_at_the_average_rate_is_never_refused(tmp_path):
    out = run(script("# algos.py"), tmp_path, "algos.py")
    scenario3 = out.split("Scenario 3")[1]
    assert len(re.findall(r"allowed 30 of 30", scenario3)) == 4


def test_the_key_choice_decides_who_is_hurt(tmp_path):
    out = run(script("# keys.py"), tmp_path, "keys.py")
    assert out == printed("per address (each /128 alone)")
    rows = {line.split("legit")[0].strip(): line for line in out.splitlines()}
    assert "attacker blocked   0 of 600" in rows["per address (each /128 alone)"]
    assert "legit blocked   0 of 480" in rows["per account"]


def test_per_key_quota_demo_shape(tmp_path):
    out = run(script("# apikeys.py"), tmp_path, "apikeys.py").splitlines()
    assert out[0].endswith("[200, 200, 200, 200, 200, 429, 429, 429]")
    assert "[200, 200, 200]" in out[1]
    assert "[200, 200, 429, 429]" in out[2]
    assert out[3].startswith("key A again          : 429, Retry-After: ")
    assert out[4].endswith(": 200")
    assert "429, Retry-After: 86400" in out[5]


def test_the_demo_prints_no_key_and_the_page_has_no_key_shaped_literal(tmp_path):
    code = script("# apikeys.py")
    assert "token_hex" in code  # keys are made at run time
    out = run(code, tmp_path, "apikeys.py")
    assert not re.search(r"\b[0-9a-f]{16}\b", out)
    text = PAGE.read_text(encoding="utf-8")
    assert not re.search(r"Bearer [A-Za-z0-9_\-]{16,}", text)


def test_the_lab_only_publishes_on_loopback():
    text = PAGE.read_text(encoding="utf-8")
    ports = re.findall(r"-p (\S+):\d+:\d+", text)
    assert ports and all(p == "127.0.0.1" for p in ports)
    assert "docker.sock" not in text and "--privileged" not in text
