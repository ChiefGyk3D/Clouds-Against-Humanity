"""The code on the deception lesson pages runs, and says what the pages say it does.

docs/wiki/Deception-and-Honeypots-*.md teach with scripts the learner pastes into
files. A lesson whose script is broken, or whose printed output has drifted from
what the script prints, teaches the wrong thing. These tests pull each script out
of the page text, run it in a temporary folder, and compare against the page.

Everything runs on localhost with invented data. The checks collect loosely (any
fenced block) and assert strictly (exactly one block per marker, and the output
matches), and each has a negative case showing the guard bites.
"""

import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
SIEM = WIKI / "Deception-and-Honeypots-Alerts-in-the-SIEM.md"
CANARY = WIKI / "Deception-and-Honeypots-Plant-a-Canary.md"
HONEY = WIKI / "Deception-and-Honeypots-Honeyfiles-on-Your-Host.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def blocks(path: Path, lang: str) -> list[str]:
    return [body for tag, body in FENCE.findall(path.read_text(encoding="utf-8")) if tag == lang]


def one_block(path: Path, lang: str, marker: str) -> str:
    found = [b for b in blocks(path, lang) if marker in b]
    assert len(found) == 1, f"{path.name}: expected one {lang} block with {marker!r}, found {len(found)}"
    return found[0]


def run_py(folder: Path, script: str, *args: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", script, *args],
        cwd=folder, capture_output=True, text=True, timeout=30, env=env, check=False,
    )


# --- lesson 5: the generator, the detector and the draft rules -------------------


@pytest.fixture()
def siem_lab(tmp_path):
    (tmp_path / "make_events.py").write_text(one_block(SIEM, "python", "Builds SYNTHETIC honeypot events"))
    (tmp_path / "detect.py").write_text(one_block(SIEM, "python", "A toy detector"))
    made = run_py(tmp_path, "make_events.py")
    assert made.returncode == 0, made.stderr
    (tmp_path / "events.jsonl").write_text(made.stdout)
    return tmp_path


def alerts(proc) -> list[dict]:
    return [json.loads(line) for line in proc.stdout.splitlines()]


def test_the_generator_makes_eighteen_lines_with_documentation_addresses_only(siem_lab):
    lines = (siem_lab / "events.jsonl").read_text().splitlines()
    assert len(lines) == 18
    docs = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except ValueError:
            pass  # the deliberately invalid line
    assert len(parsed) == 17
    for event in parsed:
        assert any(ipaddress.ip_address(event["src_ip"]) in net for net in docs), event["src_ip"]


def test_the_detector_alerts_on_source_a_only_and_drops_the_bad_lines(siem_lab):
    proc = run_py(siem_lab, "detect.py", "events.jsonl")
    assert proc.returncode == 0, proc.stderr
    got = alerts(proc)
    assert [(a["rule"], a["src_ip"]) for a in got] == [
        ("brute_force", "203.0.113.7"),
        ("success_after_brute_force", "203.0.113.7"),
        ("brute_force", "192.0.2.66"),
    ]
    assert 'dropped: {"not_json": 1, "too_long": 1, "bad_shape": 0}' in proc.stderr


def test_the_output_shown_on_the_page_is_what_the_detector_prints(siem_lab):
    shown = one_block(SIEM, "text", '"rule": "brute_force"')
    shown_alerts = [json.loads(x) for x in shown.splitlines() if x.startswith("{")]
    assert shown_alerts == alerts(run_py(siem_lab, "detect.py", "events.jsonl"))
    assert 'dropped: {"not_json": 1, "too_long": 1, "bad_shape": 0}' in shown


def test_hostile_lines_stay_data_and_a_text_search_is_fooled(siem_lab):
    text = (siem_lab / "events.jsonl").read_text()
    assert text.count("cowrie.login.success") == 4  # the page says a text search counts 4 ...
    got = alerts(run_py(siem_lab, "detect.py", "events.jsonl"))
    successes = [a for a in got if a["rule"] == "success_after_brute_force"]
    assert [a["src_ip"] for a in successes] == ["203.0.113.7"]  # ... the parsed field finds one chain alert
    # source D tripped the brute-force rule, so a substring check would have fired a second, false chain alert
    assert [a["rule"] for a in got if a["src_ip"] == "192.0.2.66"] == ["brute_force"]
    assert not (siem_lab / "pwned").exists()


def test_negative_cases_the_rule_stays_quiet_below_the_threshold(siem_lab):
    lines = (siem_lab / "events.jsonl").read_text().splitlines(keepends=True)

    def alerts_without(*banned: str) -> list[dict]:
        (siem_lab / "cut.jsonl").write_text("".join(x for x in lines if not any(b in x for b in banned)))
        return alerts(run_py(siem_lab, "detect.py", "cut.jsonl"))

    d = "192.0.2.66"                                            # the page's commands also remove source D
    assert alerts_without("203.0.113.7", d) == []               # no source A at all
    assert alerts_without('"guess4"', '"guess5"', d) == []      # four failures: one short
    assert len(alerts_without('"guess5"', d)) == 2              # five failures: both rules fire
    assert len(alerts_without()) == 3                           # control: nothing removed


def test_the_detector_survives_odd_shapes(siem_lab):
    odd = [
        "[]", "5", "null", "{}", '{"eventid": 5}', '{"eventid": "cowrie.login.failed"}',
        '{"eventid": "cowrie.login.failed", "src_ip": "x", "timestamp": "not a time"}',
        '{"eventid": "cowrie.login.failed", "src_ip": 5, "timestamp": "2026-01-01T00:00:00Z"}',
    ]
    (siem_lab / "odd.jsonl").write_text("\n".join(odd) + "\n")
    proc = run_py(siem_lab, "detect.py", "odd.jsonl")
    assert proc.returncode == 0, proc.stderr
    assert alerts(proc) == []
    assert '"not_json": 0' in proc.stderr and '"bad_shape": 8' in proc.stderr


def test_the_draft_rules_are_well_formed_and_reference_only_their_own_ids():
    xml = one_block(SIEM, "xml", "<group")
    root = ET.fromstring(xml)
    rules = {r.get("id"): r for r in root.iter("rule")}
    assert len(rules) == len(list(root.iter("rule"))) >= 4, "duplicate or missing rule ids"
    for rule in rules.values():
        for tag in ("if_sid", "if_matched_sid"):
            for ref in rule.findall(tag):
                assert ref.text.strip() in rules, f"{tag} names an unknown rule: {ref.text}"
    assert rules["100902"].get("frequency") == "5" and rules["100902"].get("timeframe") == "60"
    # the lesson says the draft is unverified; the banner must keep saying it
    assert "never loaded" in SIEM.read_text(encoding="utf-8").lower()


# --- lesson 3: the local tripwire -------------------------------------------------


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def raw_request(port: int, request: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(request)
        s.shutdown(socket.SHUT_WR)
        data = b""
        while chunk := s.recv(4096):
            data += chunk
    return data


@pytest.fixture()
def tripwire(tmp_path):
    (tmp_path / "build_bait.py").write_text(one_block(CANARY, "python", "Builds the decoy document"))
    (tmp_path / "tripwire.py").write_text(one_block(CANARY, "python", "A local tripwire"))
    port = free_port()
    env = {**os.environ, "TRIPWIRE_PORT": str(port)}
    built = run_py(tmp_path, "build_bait.py", env=env)
    assert built.returncode == 0, built.stderr
    server = subprocess.Popen(
        [sys.executable, "-I", "tripwire.py"], cwd=tmp_path,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError("the tripwire did not start")
        yield tmp_path, port
    finally:
        server.terminate()
        server.wait(timeout=5)


def bait_fields(folder: Path) -> dict:
    out = {}
    for line in (folder / "bait" / "vpn-notes-OLD.txt").read_text().splitlines():
        key, _, value = line.partition(": ")
        out[key] = value
    return out


def test_only_the_token_and_the_decoy_user_raise_an_alert(tripwire):
    folder, port = tripwire
    bait = bait_fields(folder)
    token_path = bait["details"].split(f":{port}", 1)[1]
    log = folder / "alerts.jsonl"

    raw_request(port, b"GET /index.html HTTP/1.0\r\n\r\n")                       # noise
    body = b"user=admin&password=x"
    raw_request(port, b"POST /login HTTP/1.0\r\nContent-Length: %d\r\n\r\n%s" % (len(body), body))
    assert not log.exists(), "noise must not alert"

    hostile = b'evil"\x1b[2J{{x}}'
    raw_request(port, b"GET %s HTTP/1.0\r\nUser-Agent: %s\r\n\r\n" % (token_path.encode(), hostile))
    pwd = bait["password"]
    body = f"user={bait['user']}&password={pwd}".encode()
    raw_request(port, b"POST /login HTTP/1.0\r\nContent-Length: %d\r\n\r\n%s" % (len(body), body))

    for _ in range(100):
        if log.exists() and len(log.read_text().splitlines()) >= 2:
            break
        time.sleep(0.05)
    records = [json.loads(x) for x in log.read_text().splitlines()]
    assert [r["eventid"] for r in records] == ["decoy.token.hit", "decoy.credential.used"]
    assert records[0]["user_agent"] == hostile.decode()      # intact, as data
    assert records[1]["username"] == bait["user"]
    assert pwd not in log.read_text(), "the password must never be logged"


def test_the_bait_is_built_at_run_time_and_differs_each_time(tmp_path):
    script = one_block(CANARY, "python", "Builds the decoy document")
    seen = set()
    for n in range(2):
        folder = tmp_path / str(n)
        folder.mkdir()
        (folder / "build_bait.py").write_text(script)
        assert run_py(folder, "build_bait.py").returncode == 0
        seen.add(bait_fields(folder)["password"])
    assert len(seen) == 2


# --- lesson 4: the watcher's guard against forged lines ----------------------------

FAKE_TOOL = """#!/usr/bin/env bash
# stands in for inotifywait: prints events, one with a newline in the file name
printf '2026-01-01T00:00:00+0000|OPEN|bait.txt\\n'
printf '2026-01-01T00:00:01+0000|CREATE|line1\\nALERT forged|\\n'
printf '2026-01-01T00:00:02+0000|OPEN,ISDIR|\\n'
printf '2026-01-01T00:00:03+0000|DELETE|a|b\\n'
"""


def run_watch(tmp_path: Path, script: str) -> str:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    tool = bindir / "inotifywait"
    tool.write_text(FAKE_TOOL)
    tool.chmod(0o755)
    watch = tmp_path / "watch.sh"
    watch.write_text(script)
    watch.chmod(0o755)
    env = {"PATH": f"{bindir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    proc = subprocess.run(
        ["bash", str(watch), "bait", str(tmp_path / "alerts.log")],
        cwd=tmp_path, capture_output=True, text=True, timeout=30, env=env, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return (tmp_path / "alerts.log").read_text()


def test_the_watcher_drops_forged_lines_and_quotes_names(tmp_path):
    script = one_block(HONEY, "bash", "inotifywait -m")
    log = run_watch(tmp_path, script)
    assert "forged" not in log                                   # the second line of the name never became an alert
    assert "ISDIR" not in log                                    # listing the folder is not a touch
    assert log.count("ALERT time=") == 3                         # OPEN, CREATE (name truncated), DELETE
    assert "file=a\\|b" in log                                   # %q quotes the bar


def test_without_the_guard_the_same_input_forges_an_alert(tmp_path):
    script = one_block(HONEY, "bash", "inotifywait -m")
    unguarded = "\n".join(
        line for line in script.splitlines() if "stamp" not in line and "dropped a line" not in line
    ).replace("file=%q", "file=%s")
    assert "stamp" not in unguarded and "%q" not in unguarded
    log = run_watch(tmp_path, unguarded)
    assert "ALERT forged" in log
