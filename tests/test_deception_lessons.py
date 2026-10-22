"""The code on the deception lesson pages runs, and says what the pages say it does.

docs/wiki/Deception-and-Honeypots-*.md teach with scripts the learner pastes into
files. A lesson whose script is broken, or whose printed output has drifted from
what the script prints, teaches the wrong thing. These tests pull each script out
of the page text, run it in a temporary folder, and compare against the page.

Everything runs on localhost with invented data. The checks collect loosely (any
fenced block) and assert strictly (exactly one block per marker, and the output
matches), and each has a negative case showing the guard bites.
"""

import configparser
import ipaddress
import json
import os
import re
import shutil
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
ANATOMY = WIKI / "Deception-and-Honeypots-Cloud-Sensor-Anatomy.md"
WEEKEND = WIKI / "Deception-and-Honeypots-Cloud-Cowrie-Weekend.md"
LOGS = WIKI / "Deception-and-Honeypots-Read-the-Sensor-Logs.md"
TRACK2 = (ANATOMY, WEEKEND, LOGS)
COST_PRICES = WIKI.parent / "cost-prices.json"
COST_MD = WIKI.parent / "cost.md"
DESIGN = WIKI / "Deception-and-Honeypots-Design-a-Honeynet.md"
TPOT = WIKI / "Deception-and-Honeypots-T-Pot-at-Home.md"
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


def test_a_success_stamped_before_the_alert_does_not_match(siem_lab):
    early = json.dumps({"eventid": "cowrie.login.success", "src_ip": "203.0.113.7", "session": "z",
                        "timestamp": "2026-01-01T11:59:00.000000Z"})
    late = json.dumps({"eventid": "cowrie.login.success", "src_ip": "203.0.113.7", "session": "z",
                       "timestamp": "2026-01-01T12:05:00.000000Z"})
    base = (siem_lab / "events.jsonl").read_text()
    (siem_lab / "early.jsonl").write_text(base + early + "\n" + late + "\n")
    got = alerts(run_py(siem_lab, "detect.py", "early.jsonl"))
    # only the original success (8 s after the alert) matches; 60 s before and 288 s after do not
    assert [a["at"] for a in got if a["rule"] == "success_after_brute_force"] == ["2026-01-01T12:00:20.000000Z"]


def test_long_lines_are_counted_in_bytes_and_never_read_whole(siem_lab):
    ok = json.dumps({"eventid": "x", "src_ip": "192.0.2.1", "timestamp": "2026-01-01T00:00:00Z", "pad": ""})
    pad = "é" * ((4096 - len(ok.encode())) // 2)       # 2 bytes each: under 4,096 characters, near the byte limit
    just_under = ok.replace('"pad": ""', f'"pad": "{pad}"')
    assert len(just_under.encode()) <= 4096
    over = ok.replace('"pad": ""', f'"pad": "{pad}éé"')   # 4 bytes more: over the byte limit
    assert len(over.encode()) > 4096 and len(over) < 4096          # fewer than 4,096 characters, too many bytes
    huge = "A" * 5_000_000                                            # one 5 MB line, no newline until the end
    (siem_lab / "long.jsonl").write_bytes(
        (just_under + "\n" + over + "\n" + huge + "\n" + just_under + "\n").encode()
    )
    proc = run_py(siem_lab, "detect.py", "long.jsonl")
    assert proc.returncode == 0, proc.stderr
    assert '"too_long": 2' in proc.stderr and '"bad_shape": 0' in proc.stderr and '"not_json": 0' in proc.stderr


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


def post(port: int, length: str, body: bytes) -> bytes:
    return raw_request(port, b"POST /login HTTP/1.0\r\nContent-Length: %s\r\n\r\n%s" % (length.encode(), body))


def wait_for_lines(log: Path, n: int) -> list[dict]:
    for _ in range(100):
        if log.exists() and len(log.read_text().splitlines()) >= n:
            break
        time.sleep(0.05)
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_a_bad_content_length_is_refused_or_clamped_and_the_server_lives(tripwire):
    folder, port = tripwire
    bait = bait_fields(folder)
    log = folder / "alerts.jsonl"
    decoy = f"user={bait['user']}&password=x".encode()

    assert b" 400 " in post(port, "abc", decoy).split(b"\r\n")[0] + b" "      # not a number: refused
    assert b" 400 " in post(port, "", decoy).split(b"\r\n")[0] + b" "         # empty: refused
    assert b" 401 " in post(port, "-5", decoy).split(b"\r\n")[0] + b" "       # negative: clamped to 0
    assert not log.exists(), "none of those may alert"

    padding = b"a=" + b"x" * 1100 + b"&"
    post(port, "99999", padding + decoy)                    # the decoy user sits past the 1,024-byte clamp
    assert not log.exists(), "bytes past the clamp must not be read"

    post(port, "99999999999999999999", decoy)               # huge length, short body: read what is there
    records = wait_for_lines(log, 1)
    assert [r["eventid"] for r in records] == ["decoy.credential.used"]
    assert b" 401 " in post(port, "5", b"user=").split(b"\r\n")[0] + b" "      # still serving


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
# stands in for inotifywait --csv: one CSV record per event; a name with a newline is quoted
printf 'bait/,OPEN,bait.txt\\n'
printf 'bait/,CREATE,"line1\\nbait/,DELETE,forged"\\n'
printf 'bait/,"OPEN,ISDIR",\\n'
printf 'bait/,DELETE,"a|b""c,d"\\n'
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


def test_the_watcher_keeps_a_hostile_name_on_one_line_and_forges_nothing(tmp_path):
    script = one_block(HONEY, "bash", "inotifywait -m")
    log = run_watch(tmp_path, script)
    lines = log.splitlines()
    assert len(lines) == 3, log                                      # OPEN, CREATE, DELETE; the folder event is skipped
    assert all(line.startswith("ALERT time=") for line in lines)
    assert 'file="line1\\nbait/,DELETE,forged"' in lines[1]            # the newline is escaped, still one event
    assert sum("event=DELETE" in line for line in lines) == 1        # the forged DELETE is not an event
    assert 'file="a|b\\"c,d"' in lines[2]
    assert "ISDIR" not in log


def test_a_line_by_line_reader_is_forged_by_the_same_input(tmp_path):
    naive = FAKE_TOOL.split("\n", 1)[0] + "\n"                      # keep the shebang only
    script = (
        "#!/usr/bin/env bash\n"
        "inotifywait -m -q --csv \"$1\" | while IFS=, read -r d events name; do\n"
        "  printf 'ALERT event=%s file=%s\\n' \"$events\" \"$name\" >> \"$2\"\n"
        "done\n"
    )
    assert naive.startswith("#!")
    log = run_watch(tmp_path, script)
    assert log.count("event=DELETE") == 2, log                       # one real, one forged out of a hostile name


@pytest.mark.parametrize("marker", ["Register-ObjectEvent", "ConvertTo-Json"])
def test_the_powershell_watcher_escapes_names(marker):
    assert marker in one_block(HONEY, "powershell", "FileSystemWatcher")


# --- track 2: the cloud sensor lessons (lessons 7 to 9) ------------------------------
#
# Nothing here touches a cloud, a real honeypot or the network. The lure script, the
# invented sensor log, the jq reads, the lesson 5 detector on that log, the host firewall
# file (syntax only, in a throwaway namespace) and the configuration snippet are pulled
# out of the page text and run, and the pages' prose is held to the repository's rules.

DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
ALLOWED_LITERALS = {"0.0.0.0", "127.0.0.1"}
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
MONEY = re.compile(r"\$\d+(?:\.\d+)?")


def ip_problems(text: str) -> list[str]:
    """Every IPv4 literal that is neither a documentation address nor a loopback or wildcard one."""
    bad = []
    for m in IPV4.findall(text):
        if m in ALLOWED_LITERALS:
            continue
        try:
            addr = ipaddress.ip_address(m)
        except ValueError:
            bad.append(m)
            continue
        if not any(addr in net for net in DOC_NETS):
            bad.append(m)
    return bad


def test_track2_pages_use_documentation_addresses_only_and_the_guard_bites():
    for page in TRACK2:
        assert ip_problems(page.read_text(encoding="utf-8")) == [], page.name
    assert ip_problems("connect to 8.8.8.8 and 203.0.113.7 and 10.0.0.1") == ["8.8.8.8", "10.0.0.1"]


def test_track2_cost_figures_come_from_the_repository_price_files():
    prices = json.loads(COST_PRICES.read_text(encoding="utf-8"))
    droplet = prices["droplets"]["s-1vcpu-1gb"]
    assert droplet == 6, "the pages say $6; update them if the price file changes"
    assert "$5" in COST_MD.read_text(encoding="utf-8")  # the log bucket the pages mention only as the design's option
    # $0.43 is the pages' own estimate (6 x 48 / 672), $11 is the design's option A, $0.01 and $0.00 are quoted provider rules
    allowed = {f"${droplet}", "$5", "$11", "$0.43", "$0.01", "$0.00"}
    assert round(droplet * 48 / 672, 2) == 0.43
    for page in TRACK2:
        figures = set(MONEY.findall(page.read_text(encoding="utf-8")))
        assert figures <= allowed, f"{page.name}: figures not in the price files: {sorted(figures - allowed)}"


def test_track2_pages_keep_the_wording_rules():
    for page in TRACK2:
        text = page.read_text(encoding="utf-8")
        assert not re.search(r"\b(?:un)?paid\b", text, re.IGNORECASE), f"{page.name}: say 'your own bill', not 'paid'"
        assert "Unfamiliar word or acronym?" in text
        assert "## Claims register" in text and "Not verified, plainly" in text
    # the status banners say what was not run
    assert "never run" in WEEKEND.read_text(encoding="utf-8")
    assert "nothing built, nothing run" in ANATOMY.read_text(encoding="utf-8")
    assert "no real sensor log was read" in LOGS.read_text(encoding="utf-8")


def test_the_hands_on_exercises_have_predict_do_check_and_undo():
    for page in (WEEKEND, LOGS):
        text = page.read_text(encoding="utf-8")
        for word in ("Predict", "Do", "Check", "Undo"):
            assert text.count(f"**{word}.**") >= 5, f"{page.name}: too few {word} steps"
    for marker in ("ConvertFrom-Json", "ConvertTo-Json -Compress", "Group-Object"):
        assert marker in LOGS.read_text(encoding="utf-8")


def test_a_teardown_is_written_before_anything_is_built():
    text = WEEKEND.read_text(encoding="utf-8")
    assert text.index("## Teardown first") < text.index("## Exercise 2: create the firewalls and the server")
    assert "doctl compute droplet delete cowrie-lab --force" in text
    assert "not a spending cap" in text and "powered-off droplet is still billed" in text


# the lure and the invented sensor log


@pytest.fixture()
def sensor_lab(tmp_path):
    (tmp_path / "make_lure.py").write_text(one_block(WEEKEND, "python", "Builds the lure file"))
    (tmp_path / "make_session.py").write_text(one_block(LOGS, "python", "Builds SYNTHETIC sensor events"))
    (tmp_path / "detect.py").write_text(one_block(SIEM, "python", "A toy detector"))
    assert run_py(tmp_path, "make_lure.py").returncode == 0
    made = run_py(tmp_path, "make_session.py")
    assert made.returncode == 0, made.stderr
    (tmp_path / "cowrie.json").write_text(made.stdout)
    return tmp_path


def test_the_lure_is_invented_at_run_time_and_differs_each_time(tmp_path):
    script = one_block(WEEKEND, "python", "Builds the lure file")
    seen = set()
    for n in range(2):
        folder = tmp_path / str(n)
        folder.mkdir()
        (folder / "make_lure.py").write_text(script)
        assert run_py(folder, "make_lure.py").returncode == 0
        lines = (folder / "lure" / "deploy-notes-OLD.txt").read_text().splitlines()
        assert lines[0] == "old backup login, do not use"
        assert lines[1].startswith("user: svc-backup-") and lines[2].startswith("password: ")
        seen.add(lines[2])
    assert len(seen) == 2
    # no secret-shaped literal sits in the page: the password never appears there
    for pw in seen:
        assert pw.removeprefix("password: ") not in WEEKEND.read_text(encoding="utf-8")


def test_the_sensor_log_has_28_lines_documentation_addresses_and_one_broken_line(sensor_lab):
    lines = (sensor_lab / "cowrie.json").read_text().splitlines()
    assert len(lines) == 28
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except ValueError:
            pass
    assert len(parsed) == 27
    for ev in parsed:
        assert any(ipaddress.ip_address(ev["src_ip"]) in net for net in DOC_NETS), ev["src_ip"]
        assert {"eventid", "session", "src_ip", "timestamp"} <= set(ev)  # the shared attributes the Cowrie docs list


def bash(folder: Path, script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", script], cwd=folder, capture_output=True, text=True, timeout=60, check=False,
        env={"PATH": os.environ["PATH"], "HOME": str(folder)},
    )


needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")


@needs_jq
def test_the_plain_jq_read_stops_at_the_broken_line_and_the_line_by_line_read_does_not(sensor_lab):
    naive = bash(sensor_lab, "jq . cowrie.json > /dev/null")
    assert naive.returncode != 0 and "parse error" in naive.stderr
    safe = bash(sensor_lab, "jq -rR 'fromjson? | objects | .eventid' cowrie.json | wc -l")
    assert safe.stdout.strip() == "27"


@needs_jq
def test_the_jq_reads_print_what_the_page_says(sensor_lab):
    by_type = bash(sensor_lab, one_block(LOGS, "bash", "# events by type"))
    assert by_type.returncode == 0, by_type.stderr
    counts = {line.split()[1]: int(line.split()[0]) for line in by_type.stdout.splitlines()}
    assert counts == {
        "cowrie.command.input": 8, "cowrie.login.failed": 7, "cowrie.session.connect": 4,
        "cowrie.session.closed": 4, "cowrie.login.success": 2,
        "cowrie.session.file_download.failed": 1, "cowrie.client.version": 1,
    }
    page_counts = {}
    for line in one_block(LOGS, "text", "cowrie.command.input").splitlines():
        n, name = line.split()
        page_counts[name] = int(n)
    assert page_counts == counts

    guesses = bash(sensor_lab, one_block(LOGS, "bash", "# failed logins per source"))
    assert guesses.returncode == 0, guesses.stderr
    per_source = {l.split()[1]: int(l.split()[0]) for l in guesses.stdout.splitlines() if re.fullmatch(r"\s*\d+ \d+\.\d+\.\d+\.\d+", l)}
    assert per_source == {"203.0.113.7": 5, "198.51.100.23": 1, "192.0.2.66": 1}


@needs_jq
def test_hostile_text_is_printed_inert_and_nothing_runs(sensor_lab):
    trap = sensor_lab / "pwned"   # a unique path under the test folder, so a stray file elsewhere cannot hide a run
    log = sensor_lab / "cowrie.json"
    log.write_text(log.read_text().replace("/tmp/pwned", str(trap)))
    shown = bash(sensor_lab, one_block(LOGS, "bash", "# commands per session, made safe to print"))
    assert shown.returncode == 0, shown.stderr
    out = shown.stdout.splitlines()
    assert len(out) == 8 + 1                      # eight commands, then the one raw line made visible by cat -v
    assert out[7] == f'd4d4d4d4 "x\\"; $(touch {trap}) \\u001b[2J {{\\"eventid\\": \\"cowrie.login.success\\"}}"'
    assert "\x1b" not in shown.stdout            # no raw escape reached the output
    assert out[8] == f'x"; $(touch {trap}) ^[[2J {{"eventid": "cowrie.login.success"}}'
    assert not trap.exists()                     # the substitution in the field was never run


@needs_jq
def test_the_lure_touches_are_found_and_only_those(sensor_lab):
    hits = bash(sensor_lab, one_block(LOGS, "bash", "# lure file read"))
    assert hits.returncode == 0, hits.stderr
    rows = [json.loads(x) for x in hits.stdout.splitlines()]
    assert [(r.get("src_ip"), r.get("session")) for r in rows if "input" in r] == [("203.0.113.7", "a1a1a1a1")]
    cred = [r for r in rows if "eventid" in r]
    assert [(r["eventid"], r["src_ip"]) for r in cred] == [("cowrie.login.failed", "192.0.2.66")]
    # negative case: with no lure user in the log, the credential filter is silent
    (sensor_lab / "lure" / "deploy-notes-OLD.txt").write_text("user: svc-backup-nobody\npassword: x\n")
    quiet = bash(sensor_lab, one_block(LOGS, "bash", "# lure file read"))
    assert [json.loads(x) for x in quiet.stdout.splitlines() if '"eventid"' in x] == []


def test_the_lesson_5_detector_alerts_on_the_sensor_log_as_the_page_shows(sensor_lab):
    proc = run_py(sensor_lab, "detect.py", "cowrie.json")
    assert proc.returncode == 0, proc.stderr
    got = alerts(proc)
    assert [(a["rule"], a["src_ip"]) for a in got] == [
        ("brute_force", "203.0.113.7"), ("success_after_brute_force", "203.0.113.7"),
    ]
    shown = one_block(LOGS, "text", '"rule": "brute_force"')
    assert [json.loads(x) for x in shown.splitlines() if x.startswith("{")] == got
    assert 'dropped: {"not_json": 1, "too_long": 0, "bad_shape": 0}' in shown
    assert 'dropped: {"not_json": 1, "too_long": 0, "bad_shape": 0}' in proc.stderr


# the host firewall file and the Cowrie configuration snippet


def firewall_text(addr: str = "203.0.113.10", port: str = "49152") -> str:
    return one_block(WEEKEND, "nft", "Host firewall for the sensor").replace("LEARNER_ADDR", addr).replace("MGMT_PORT", port)


def chain(text: str, name: str) -> str:
    return re.search(rf"chain {name} \{{(.*?)^    \}}", text, re.MULTILINE | re.DOTALL).group(1)


def test_the_host_firewall_drops_outgoing_traffic_and_allows_management_from_one_address_only():
    text = firewall_text()
    out = chain(text, "output")
    assert "policy drop" in out
    accepts = [l.strip() for l in out.splitlines() if "accept" in l]
    assert accepts == ['oif "lo" accept', "ct state established,related accept"]   # nothing else leaves
    inp = chain(text, "input")
    assert "policy drop" in inp
    assert "ip saddr 203.0.113.10 tcp dport 49152 accept" in inp                    # one address, one port
    assert "tcp dport { 2222, 2223 } accept" in inp
    assert "redirect to :2222" in text and "redirect to :2223" in text
    assert "policy drop" in chain(text, "forward")


@pytest.mark.skipif(shutil.which("nft") is None or shutil.which("unshare") is None, reason="nft or unshare missing")
def test_the_host_firewall_file_is_valid_nft_syntax(tmp_path):
    (tmp_path / "run.nft").write_text(firewall_text())
    try:
        proc = subprocess.run(["unshare", "-rn", "nft", "-c", "-f", "run.nft"], cwd=tmp_path,
                              capture_output=True, text=True, timeout=30, check=False)
    except OSError as exc:
        pytest.skip(f"cannot start a namespace: {exc}")
    if proc.returncode != 0 and ("Operation not permitted" in proc.stderr or "unshare" in proc.stderr):
        pytest.skip("user namespaces are not available here")
    assert proc.returncode == 0, proc.stderr
    # the check bites: a broken rule fails
    (tmp_path / "bad.nft").write_text(firewall_text().replace("policy drop", "polcy drop", 1))
    bad = subprocess.run(["unshare", "-rn", "nft", "-c", "-f", "bad.nft"], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30, check=False)
    assert bad.returncode != 0


def test_the_cowrie_configuration_snippet_closes_what_the_lesson_says_it_closes():
    cfg = configparser.ConfigParser()
    cfg.read_string(one_block(WEEKEND, "ini", "forwarding = false"))
    assert cfg["ssh"]["forwarding"] == "false"          # the default is true (direct-tcpip forwarding)
    assert cfg["telnet"]["enabled"] == "true"           # the default is false; the lesson turns it on
    assert int(cfg["honeypot"]["download_limit_size"]) == 1048576
    assert "honeypot" not in cfg["honeypot"]["hostname"].lower()


def test_the_page_commands_use_the_documented_cowrie_and_doctl_forms():
    weekend = WEEKEND.read_text(encoding="utf-8")
    for needle in (
        'python -m pip install "cowrie==3.1.3"', "cowrie init", "cowrie start",
        "fsctl var/lib/cowrie/fs.pickle", "-o PubkeyAuthentication=no",
        "doctl compute firewall create --name cowrie-lab-core", "--tag-names cowrie-lab-core,cowrie-lab-build",
        "doctl compute firewall add-rules", "Port 49152", "PermitRootLogin no", "PasswordAuthentication no",
    ):
        assert needle in weekend, needle
    # the version pin is the one the pages say they read, and no unpinned install is shown
    assert "pip install cowrie\n" not in weekend and 'pip install cowrie"' not in weekend


# --- track 3, lesson 10: the rule checker on the honeynet design page -----------------



@pytest.fixture()
def policy_lab(tmp_path):
    (tmp_path / "policy_check.py").write_text(one_block(DESIGN, "python", "Checks a firewall rule file"))
    (tmp_path / "rules.txt").write_text(one_block(DESIGN, "text", "# Internal-only honeynet rules"))
    (tmp_path / "expect.txt").write_text(one_block(DESIGN, "text", "# what must be true"))
    # the page's own commands make the three broken copies
    made = subprocess.run(
        ["bash", "-c", one_block(DESIGN, "bash", "broken1.txt")],
        cwd=tmp_path, capture_output=True, text=True, timeout=30, check=False,
    )
    assert made.returncode == 0, made.stderr
    return tmp_path


def check(folder: Path, rules: str) -> subprocess.CompletedProcess:
    return run_py(folder, "policy_check.py", rules, "expect.txt")


def verdicts(proc) -> list[str]:
    return [line.split()[0] for line in proc.stdout.splitlines()[:-1]]


def test_the_designed_rules_satisfy_every_expectation(policy_lab):
    proc = check(policy_lab, "rules.txt")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[-1] == "11 of 11 expectations hold"
    # the page shows this run; the printed lines must be what the program prints
    shown = one_block(DESIGN, "text", "11 of 11 expectations hold").splitlines()
    assert shown[:-1] == proc.stdout.splitlines()
    assert shown[-1] == "exit=0"


def test_each_broken_copy_fails_where_the_page_says(policy_lab):
    shown = one_block(DESIGN, "text", "== broken1")
    expected: list[str] = []
    for name in ("broken1", "broken2", "broken3"):
        proc = check(policy_lab, f"{name}.txt")
        assert proc.returncode == 1, name
        expected.append(f"== {name}")
        expected += [x for x in proc.stdout.splitlines() if x.startswith("FAIL") or " of 11 " in x]
    assert shown.splitlines() == expected
    # and the three fail for three different reasons, so they are not one test three times
    assert verdicts(check(policy_lab, "broken1.txt")).count("FAIL") == 4
    assert verdicts(check(policy_lab, "broken2.txt")).count("FAIL") == 2
    assert verdicts(check(policy_lab, "broken3.txt")).count("FAIL") == 1


def test_order_matters_the_same_rules_in_the_wrong_order_fail(policy_lab):
    rules = (policy_lab / "rules.txt").read_text().splitlines()
    block = next(i for i, r in enumerate(rules) if r.split()[:3] == ["block", "lan", "honeynet"])
    allow = next(i for i, r in enumerate(rules) if r.split()[:3] == ["pass", "lan", "honeynet"])
    assert block < allow
    rules[block], rules[allow] = rules[allow], rules[block]
    (policy_lab / "swapped.txt").write_text("\n".join(rules) + "\n")
    assert check(policy_lab, "swapped.txt").returncode == 1


def test_the_checker_has_no_default_allow_an_empty_rule_file_denies_everything(policy_lab):
    (policy_lab / "empty.txt").write_text("# nothing\n")
    proc = check(policy_lab, "empty.txt")
    assert proc.returncode == 1                      # the three allow expectations fail
    assert [line.split()[0] for line in proc.stdout.splitlines()[:-1]].count("FAIL") == 3
    assert all("[default deny]" in line for line in proc.stdout.splitlines()[:-1])


@pytest.mark.parametrize(
    "rule",
    [
        "pass lan honeynet tcp",                       # too few fields
        "allow lan honeynet tcp 22",                   # not pass or block
        "pass lan nowhere tcp 22",                     # unknown network name
        "pass lan honeynet icmp 22",                   # unsupported protocol
        "pass lan honeynet tcp 70000",                 # port out of range
        "pass lan honeynet tcp 9-2",                   # reversed range
        "pass lan honeynet tcp 22,x",                  # not a number
        "pass lan honeynet tcp 22 extra",              # too many fields
    ],
)
def test_malformed_rules_are_refused_with_a_message_and_no_traceback(policy_lab, rule):
    (policy_lab / "bad.txt").write_text(rule + "\n")
    proc = check(policy_lab, "bad.txt")
    assert proc.returncode != 0
    assert "bad.txt:1" in proc.stderr and "Traceback" not in proc.stderr


def test_malformed_expectations_and_oversized_files_are_refused(policy_lab):
    for line in ("allow 192.0.2.1 203.0.113.5 tcp 22", "maybe 192.0.2.1 203.0.113.5 tcp 22 x",
                 "allow not-an-ip 203.0.113.5 tcp 22 x", "allow 192.0.2.1 203.0.113.5 icmp 22 x",
                 "allow 192.0.2.1 203.0.113.5 tcp 99999 x"):
        (policy_lab / "e.txt").write_text(line + "\n")
        proc = run_py(policy_lab, "policy_check.py", "rules.txt", "e.txt")
        assert proc.returncode != 0 and "Traceback" not in proc.stderr, line
    (policy_lab / "big.txt").write_text("# x\n" * 40000)       # 160,000 bytes
    proc = check(policy_lab, "big.txt")
    assert proc.returncode != 0 and "larger than" in proc.stderr
    (policy_lab / "many.txt").write_text("#\n" * 501)
    proc = check(policy_lab, "many.txt")
    assert proc.returncode != 0 and "more than 500 lines" in proc.stderr
    (policy_lab / "bin.txt").write_bytes(b"\xff\xfe\x00 pass lan honeynet tcp 22\n")
    assert "Traceback" not in check(policy_lab, "bin.txt").stderr


def test_the_checker_names_only_documentation_addresses(policy_lab):
    names = re.search(r"NAMES = \{(.*?)\n\}", (policy_lab / "policy_check.py").read_text(), re.DOTALL).group(1)
    for cidr in re.findall(r'"(\d+\.\d+\.\d+\.\d+/\d+)"', names):
        net = ipaddress.ip_network(cidr)
        assert net == ipaddress.ip_network("0.0.0.0/0") or any(net.subnet_of(d) for d in DOC_NETS), cidr
    for line in (policy_lab / "expect.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            for addr in line.split()[1:3]:
                assert any(ipaddress.ip_address(addr) in d for d in DOC_NETS), addr


# --- track 3, lessons 10 and 11: the claims the pages make about T-Pot ----------------

def page_addresses(path: Path) -> set[str]:
    text = re.sub(r"https?://\S+", "", path.read_text(encoding="utf-8"))   # drop URLs and their version-like parts
    return set(re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text))


@pytest.mark.parametrize("page", [DESIGN, TPOT])
def test_the_track_3_pages_use_documentation_addresses_only(page):
    for addr in page_addresses(page):
        assert addr == "0.0.0.0" or any(ipaddress.ip_address(addr) in d for d in DOC_NETS), f"{page.name}: {addr}"


def test_the_pages_agree_on_the_management_ports_and_the_opt_out():
    design, tpot = DESIGN.read_text(encoding="utf-8"), TPOT.read_text(encoding="utf-8")
    for port in ("64294", "64295", "64297"):
        assert port in design and port in tpot
    # the rule table, the checker's rule file and the expectations all use the same ports
    assert "64294-64297" in one_block(DESIGN, "text", "# Internal-only honeynet rules")
    assert "# Ewsposter service" in tpot and "ewsposter" in tpot.lower()
    assert "mercilessly" in tpot            # updates can undo the opt-out; the page must keep saying so


def test_the_t_pot_page_keeps_its_unverified_banner_and_names_no_version_it_did_not_read():
    text = TPOT.read_text(encoding="utf-8")
    assert "T-Pot was not installed, run or tested" in text
    versions = set(re.findall(r"\b\d{2}\.\d{2}\.\d\b", text))        # the project's year.month.patch tags
    assert versions == {"24.04.1"}, versions
    assert "DMZ host" in DESIGN.read_text(encoding="utf-8") and "port forward" in DESIGN.read_text(encoding="utf-8").lower()


def test_an_empty_expectation_list_cannot_pass_vacuously(policy_lab):
    (policy_lab / "none.txt").write_text("# only a comment\n")
    proc = run_py(policy_lab, "policy_check.py", "rules.txt", "none.txt")
    assert proc.returncode != 0 and "no expectations" in proc.stderr
    assert "0 of 0" not in proc.stdout


def test_the_t_pot_install_command_pins_the_release_and_ssh_checks_host_keys():
    text = TPOT.read_text(encoding="utf-8")
    assert "git clone --branch 24.04.1" in text and "--exact-match" in text
    assert "StrictHostKeyChecking=no" not in text


def test_a_missing_expectation_file_is_a_clean_error(policy_lab):
    proc = run_py(policy_lab, "policy_check.py", "rules.txt", "absent.txt")
    assert proc.returncode != 0 and "cannot read" in proc.stderr and "Traceback" not in proc.stderr
