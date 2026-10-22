"""The toy lab on the security tools lesson runs, and does what the page says it does.

docs/wiki/Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md teaches with three Python
scripts the learner saves from the page: a toy three-part system, a toy scan detector and a toy
intercepting proxy. These tests pull each script out of the page, run it on loopback only, and
compare it with the page's claims. Nothing leaves the machine; the only addresses used are
127.x.x.x. Nmap is used only if it is installed, against that same loopback lab.
"""

import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
IPV4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def one_block(marker: str) -> str:
    found = [b for tag, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if tag == "python" and marker in b]
    assert len(found) == 1, f"expected one python block with {marker!r}, found {len(found)}"
    return found[0]


def free_base() -> int:
    for base in range(20100, 20900, 7):
        socks = []
        try:
            for off in range(3):
                s = socket.socket()
                s.bind(("127.0.0.1", base + off))
                socks.append(s)
            return base
        except OSError:
            continue
        finally:
            for s in socks:
                s.close()
    pytest.skip("no free loopback ports")


def wait_for(host: str, port: int) -> None:
    for _ in range(100):
        try:
            socket.create_connection((host, port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.1)
    raise AssertionError(f"{host}:{port} never came up")


@pytest.fixture()
def scripts(tmp_path):
    (tmp_path / "lab.py").write_text(one_block("a toy three-part system"))
    (tmp_path / "scan_detect.py").write_text(one_block("toy detector"))
    (tmp_path / "proxy.py").write_text(one_block("toy intercepting proxy"))
    return tmp_path


def start_lab(folder: Path, base: int, *extra: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-I", "lab.py", "--base-port", str(base), *extra],
        cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for _ in range(3):
        assert "listening on" in proc.stdout.readline()
    return proc


def get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def can_connect(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=0.5).close()
        return True
    except OSError:
        return False


@pytest.fixture()
def lab(scripts):
    base = free_base()
    proc = start_lab(scripts, base)
    wait_for("127.0.0.1", base + 2)
    # Regression note (issue #226): wait_for() itself connects to the db port, and lab.py logs that
    # CONN line from its own server thread, a moment AFTER the connect returns. A test that emptied
    # lab.log right away could have the fixture's late line land after the truncation and count it as
    # a scan connection (one extra dport=<base+2>; about 1 run in 15 alone, about half under load).
    # So the fixture does not hand over until that line exists, and tests then clear the log safely.
    deadline = time.time() + 10
    log = scripts / "lab.log"
    while time.time() < deadline:
        if log.exists() and f"CONN db src=127.0.0.1 dport={base + 2}" in log.read_text():
            break
        time.sleep(0.05)
    else:
        raise AssertionError("the fixture's own probe was never logged")
    yield scripts, base
    proc.terminate()
    proc.wait(timeout=10)


def test_default_build_is_flat_leaky_and_loopback_only(lab):
    _folder, base = lab
    assert all(can_connect("127.0.0.1", base + i) for i in range(3))   # one address: no segmentation
    status, headers, _body = get(f"http://127.0.0.1:{base}/")
    assert status == 200 and headers["Server"].startswith("LabHTTP/1.0 build-")
    assert get(f"http://127.0.0.1:{base}/admin/")[0] == 200            # the debug page the page tells you to find
    assert get(f"http://127.0.0.1:{base}/nope")[0] == 404
    with socket.create_connection(("127.0.0.1", base + 2), timeout=2) as s:
        assert s.recv(100).startswith(b"LABDB 5.5.0")
    listen = subprocess.run(["ss", "-ltn"], capture_output=True, text=True, check=False).stdout if shutil.which("ss") else ""
    for line in listen.splitlines():
        if f":{base}" in line or f":{base + 1}" in line or f":{base + 2}" in line:
            assert "127.0.0.1:" in line and "0.0.0.0:" not in line.split()[3], line


def test_the_log_has_the_fields_the_page_and_the_detector_read(lab):
    folder, base = lab
    get(f"http://127.0.0.1:{base}/.env")
    time.sleep(0.3)
    lines = (folder / "lab.log").read_text().splitlines()
    req = [x for x in lines if " REQ " in x]
    assert re.fullmatch(
        rf'\d{{4}}-\d\d-\d\dT\d\d:\d\d:\d\dZ REQ web src=127\.0\.0\.1 dport={base} GET /\.env 404 ua="[^"]*"', req[-1]
    ), req[-1]
    assert any(re.fullmatch(rf"\S+Z CONN web src=127\.0\.0\.1 dport={base}", x) for x in lines)


def test_fixed_build_segments_and_says_less(scripts):
    base = free_base()
    proc = start_lab(scripts, base, "--fixed")
    try:
        wait_for("127.0.0.1", base)
        if not can_connect("127.0.0.1", base):
            pytest.skip("loopback not available")
        try:
            wait_for("127.0.0.2", base + 1)
            wait_for("127.0.0.3", base + 2)
        except AssertionError:
            pytest.skip("this system does not answer on 127.0.0.2 / 127.0.0.3")
        # the outside view (the front end's address) sees only the web port
        assert can_connect("127.0.0.1", base)
        assert not can_connect("127.0.0.1", base + 1) and not can_connect("127.0.0.1", base + 2)
        status, headers, _ = get(f"http://127.0.0.1:{base}/")
        assert status == 200 and headers["Server"] == "web"
        assert get(f"http://127.0.0.1:{base}/admin/")[0] == 404
        assert get(f"http://127.0.0.2:{base + 1}/")[0] == 200            # the app tier still works
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def run_detect(folder: Path, text: str, window: int, need: int):
    (folder / "t.log").write_text(text)
    return subprocess.run(
        [sys.executable, "-I", "scan_detect.py", "t.log", str(window), str(need)],
        cwd=folder, capture_output=True, text=True, timeout=20, check=False,
    )


def conn(sec: int, port: int, src: str = "198.51.100.5") -> str:
    return f"2026-01-01T00:00:{sec:02d}Z CONN web src={src} dport={port}\n"


def test_detector_fires_on_a_fast_scan_and_not_on_a_slow_one(scripts):
    fast = conn(0, 1) + conn(1, 2) + conn(2, 3)
    slow = conn(0, 1) + conn(20, 2) + conn(40, 3)
    assert "ALERT port_scan src=198.51.100.5 ports=3 window=10s" in run_detect(scripts, fast, 10, 3).stdout
    assert run_detect(scripts, slow, 10, 3).stdout == ""
    assert "ALERT port_scan" in run_detect(scripts, slow, 60, 3).stdout          # the "defend" step


def test_detector_needs_distinct_ports_and_groups_by_source(scripts):
    same_port = conn(0, 1) + conn(1, 1) + conn(2, 1) + conn(3, 1)
    assert run_detect(scripts, same_port, 10, 3).stdout == ""
    split = conn(0, 1) + conn(1, 2, "198.51.100.6") + conn(2, 3, "198.51.100.7")
    assert run_detect(scripts, split, 10, 3).stdout == ""                         # three sources, one port each


def test_detector_treats_hostile_lines_as_data(scripts):
    hostile = (
        "garbage\n\n$(touch pwned) CONN x src=$(touch pwned) dport=1\n"
        "2026-01-01T00:00:00Z CONN web src=198.51.100.5 dport=notanumber\n"
        "2026-13-45T99:00:00Z CONN web src=198.51.100.5 dport=1\n"
        + conn(0, 1) + conn(1, 2) + conn(2, 3)
    )
    proc = run_detect(scripts, hostile, 10, 3)
    assert proc.returncode == 0, proc.stderr
    assert "ALERT port_scan" in proc.stdout and "skipped 2 unparseable lines" in proc.stderr
    assert not (scripts / "pwned").exists()


def test_proxy_forwards_loopback_and_refuses_everything_else(lab):
    folder, base = lab
    pbase = free_base()
    proc = subprocess.Popen([sys.executable, "-I", "proxy.py", str(pbase)], cwd=folder,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_for("127.0.0.1", pbase)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": f"http://127.0.0.1:{pbase}"}))
        with opener.open(f"http://127.0.0.1:{base}/admin/", timeout=5) as r:
            assert r.status == 200 and b"debug page" in r.read()
        for target in ("http://203.0.113.9/", "http://example.com/"):
            with pytest.raises(urllib.error.HTTPError) as err:
                opener.open(target, timeout=5)
            assert err.value.code == 403, target
        with socket.create_connection(("127.0.0.1", pbase), timeout=5) as raw:   # a non-http scheme, sent by hand
            raw.sendall(b"GET https://127.0.0.1/ HTTP/1.0\r\n\r\n")
            assert b" 403 " in raw.recv(200).split(b"\r\n")[0]
        for bad in (b"http://127.0.0.1:notaport/", b"http://127.0.0.1:99999/"):   # bad ports are refused, not a crash
            with socket.create_connection(("127.0.0.1", pbase), timeout=5) as raw:
                raw.sendall(b"GET " + bad + b" HTTP/1.0\r\n\r\n")
                assert b" 403 " in raw.recv(200).split(b"\r\n")[0], bad
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    out = proc.stdout.read()
    assert ">>> GET http://127.0.0.1:" in out and "<<< 200 OK" in out and "<<< Server: LabHTTP/1.0" in out
    assert "203.0.113.9" not in out                                               # refused before anything was printed or sent


@pytest.mark.skipif(shutil.which("nmap") is None, reason="nmap is not installed")
def test_a_connect_scan_leaves_one_connection_line_per_open_port(lab):
    folder, base = lab
    (folder / "lab.log").write_text("")                                           # safe now: the fixture's probe is already logged
    subprocess.run(["nmap", "-sT", "-p", f"{base}-{base + 2}", "127.0.0.1"], capture_output=True, timeout=60, check=True)
    ports: list[str] = []
    for _ in range(100):          # the server logs from its own threads: wait for the lines, not a fixed time
        ports = [x.split()[-1] for x in (folder / "lab.log").read_text().splitlines() if " CONN " in x]
        if len(ports) >= 3:
            break
        time.sleep(0.05)
    time.sleep(0.2)               # a short grace so a spurious extra line would still be caught
    ports = [x.split()[-1] for x in (folder / "lab.log").read_text().splitlines() if " CONN " in x]
    assert sorted(ports) == [f"dport={base + i}" for i in range(3)]      # order-independent


# --- the page itself --------------------------------------------------------------


def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_only_loopback_and_documentation_addresses_appear():
    allowed = ("127.", "192.0.2.", "198.51.100.", "203.0.113.", "0.0.0.0")
    version_like = {"3.13.5", "8.21.0", "7.98", "5.5.0"}
    bad = [ip for ip in IPV4.findall(page_text()) if not ip.startswith(allowed) and ip not in version_like]
    assert not bad, bad


def test_the_companion_link_is_present_and_kept_out_of_the_next_line():
    text = page_text()
    assert "Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md" in text
    assert "may not resolve until" in text
    for line in text.splitlines():
        if "Next:" in line:
            assert "Red-and-Blue-Yin-and-Yang" not in line


def test_every_exercise_has_predict_do_check_undo_and_unrun_things_are_marked():
    text = page_text()
    exercises = re.split(r"^### Exercise ", text, flags=re.MULTILINE)[1:]
    assert len(exercises) >= 8
    for ex in exercises:
        head = ex.splitlines()[0]
        for word in ("**Predict", "**Do", "**Undo"):
            assert word in ex, f"Exercise {head}: missing {word}"
        if "not run" not in head:
            assert "**Check" in ex, f"Exercise {head}: missing **Check"
    assert "est." in text and "PowerShell" in text
