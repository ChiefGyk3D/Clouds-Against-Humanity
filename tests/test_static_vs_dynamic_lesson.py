# SPDX-License-Identifier: Apache-2.0
"""The static against dynamic lesson: its stand-in script runs and shows what the page says, and its rules hold.

docs/wiki/Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md teaches recon with a loopback script and gives
a career section. A script that does not run, a tool pointed at a foreign address, or a career section that names
an employer or an invented link would teach the wrong thing.
"""

import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "wiki" / "Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
URL = re.compile(r"https?://[^\s)>\"'`]+")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def blocks(tag: str) -> list[str]:
    return [b for t, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if t == tag]


def free_port_pair() -> int:
    for base in range(20000, 40000, 7):
        socks = []
        try:
            for p in (base, base + 1):
                s = socket.socket()
                s.bind(("127.0.0.1", p))
                socks.append(s)
            return base
        except OSError:
            continue
        finally:
            for s in socks:
                s.close()
    raise RuntimeError("no free port pair")


def fetch(url: str):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), ""


def test_the_stand_in_sites_show_the_signs_the_page_teaches(tmp_path):
    scripts = blocks("python")
    assert len(scripts) == 1
    script = tmp_path / "siteduo.py"
    script.write_text(scripts[0], encoding="utf-8")
    base = free_port_pair()
    proc = subprocess.Popen([sys.executable, "-I", str(script), "--base-port", str(base)], stdout=subprocess.PIPE, text=True, cwd=tmp_path)
    try:
        assert "static site" in proc.stdout.readline()
        assert "dynamic site" in proc.stdout.readline()
        time.sleep(0.2)
        s_url, d_url = f"http://127.0.0.1:{base}", f"http://127.0.0.1:{base + 1}"
        s_code, s_head, s_body = fetch(s_url + "/")
        d_code, d_head, d_body = fetch(d_url + "/")
        assert s_code == d_code == 200
        assert 'name="generator" content="Hugo' in s_body
        assert 'name="generator" content="WordPress' in d_body
        assert 'rel="https://api.w.org/"' in d_head["Link"] and "Link" not in s_head
        assert "X-Powered-By" in d_head and "X-Powered-By" not in s_head
        assert s_head["Server"] == d_head["Server"], "the Server header must not tell them apart"
        assert fetch(s_url + "/wp-login.php")[0] == 404
        assert fetch(d_url + "/wp-login.php")[0] == 200
        assert fetch(s_url + "/wp-json/")[0] == 404
        assert fetch(d_url + "/wp-json/")[0] == 200
        assert "/wp-admin/" in fetch(d_url + "/robots.txt")[2]
        assert "/wp-admin/" not in fetch(s_url + "/robots.txt")[2]
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_the_script_only_ever_names_the_loopback_address():
    code = blocks("python")[0]
    addresses = set(ADDR.findall(code))
    assert addresses, "the guard collected nothing"
    assert addresses == {"127.0.0.1"}


def test_the_guard_bites_on_a_foreign_address():
    assert set(ADDR.findall('connect(("192.0.2.1", 80))')) != {"127.0.0.1"}


def test_every_command_in_the_page_targets_loopback_or_a_documentation_domain():
    text = PAGE.read_text(encoding="utf-8")
    commands = [line for b in blocks("bash") for line in b.splitlines() if re.search(r"\b(curl|whatweb)\b", line)]
    assert commands, "the guard collected nothing"
    for line in commands:
        assert "127.0.0.1" in line, line
    # inline recon commands name only a documentation domain
    inline = re.findall(r"`((?:openssl s_client -connect|dig) [^`]+)`", text)
    assert inline, "the guard collected nothing"
    for cmd in inline:
        assert "example.com" in cmd, cmd


def test_the_page_states_the_permission_rule_and_marks_the_stand_ins():
    text = PAGE.read_text(encoding="utf-8")
    assert "written permission" in text
    assert "Recon tools are used **only against sites you own" in text
    assert "not real Hugo" in text
    assert "Unverified draft" in text or "unverified draft" in text


def test_the_page_names_no_employer_and_links_only_known_community_addresses():
    text = PAGE.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for addr in ("https://discord.chiefgyk3d.com", "https://matrix-invite.chiefgyk3d.com"):
        assert addr in readme, addr
        assert addr in text or addr.removeprefix("https://") in text
    assert "https://infosecmap.com/" in text
    assert "Senior Cybersecurity Engineer" in text and "CISSP" in text
    assert not invented_invite(text)


def invented_invite(text: str) -> bool:
    return any(x in text for x in ("discord.gg", "discord.com/invite", "matrix.to"))


def test_the_guard_bites_on_an_invented_invite():
    assert invented_invite("join https://discord.gg/abc")
    assert not invented_invite("join https://discord.chiefgyk3d.com")
