"""The scripts on the IDS and IPS lesson run, and the page keeps the promises it makes.

docs/wiki/IDS-and-IPS-Snort-and-Suricata.md teaches with a capture builder, two rules, a small
summarizer and a container wrapper. These tests pull each file out of the page, build the
capture in a temporary folder, parse it with the standard library, and check the summarizer
against output files made up at run time. Suricata itself is run only if it is installed
(the lesson runs it in a container; a test run does not pull images or touch a network).
Everything is invented data on documentation addresses.
"""

import hashlib
import ipaddress
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "IDS-and-IPS-Snort-and-Suricata.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def one_block(lang: str, marker: str) -> str:
    found = [b for tag, b in FENCE.findall(text()) if tag == lang and marker in b]
    assert len(found) == 1, f"expected one {lang} block with {marker!r}, found {len(found)}"
    return found[0]


@pytest.fixture()
def lab(tmp_path):
    (tmp_path / "make_pcap.py").write_text(one_block("python", "make_pcap.py - writes lab.pcap"))
    (tmp_path / "summarize.py").write_text(one_block("python", "summarize.py OUT_DIR"))
    (tmp_path / "local.rules").write_text(one_block("text", "local.rules - our own rules"))
    return tmp_path


def run_py(folder: Path, script: str, *args: str):
    return subprocess.run([sys.executable, "-I", script, *args], cwd=folder, capture_output=True, text=True, check=False)


def read_pcap(path: Path):
    data = path.read_bytes()
    magic, vmaj, vmin, _tz, _sig, _snap, link = struct.unpack("<IHHiIII", data[:24])
    assert (magic, vmaj, vmin, link) == (0xA1B2C3D4, 2, 4, 1)
    pos, frames = 24, []
    while pos < len(data):
        _s, _us, caplen, origlen = struct.unpack("<IIII", data[pos:pos + 16])
        assert caplen == origlen
        frames.append(data[pos + 16:pos + 16 + caplen])
        pos += 16 + caplen
    assert pos == len(data)
    return frames


def csum(b: bytes) -> int:
    if len(b) % 2:
        b += b"\x00"
    total = sum(struct.unpack(f"!{len(b) // 2}H", b))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def dissect(frame: bytes):
    assert frame[12:14] == b"\x08\x00"
    ip = frame[14:]
    ihl = (ip[0] & 0x0F) * 4
    assert csum(ip[:ihl]) == 0, "bad IP header checksum"
    src, dst = ipaddress.ip_address(ip[12:16]), ipaddress.ip_address(ip[16:20])
    tcp = ip[ihl:]
    pseudo = ip[12:20] + struct.pack("!BBH", 0, 6, len(tcp))
    assert csum(pseudo + tcp) == 0, "bad TCP checksum"
    sport, dport = struct.unpack("!HH", tcp[:4])
    return src, dst, sport, dport, tcp[(tcp[12] >> 4) * 4:]


# --- the capture ------------------------------------------------------------------------


def test_the_capture_is_what_the_page_says(lab):
    done = run_py(lab, "make_pcap.py")
    assert done.returncode == 0 and "wrote lab.pcap with 140 packets" in done.stdout
    frames = read_pcap(lab / "lab.pcap")
    assert len(frames) == 140
    requests = []
    for f in frames:
        src, dst, _sp, _dp, payload = dissect(f)
        for ip in (src, dst):
            assert any(ip in net for net in DOC_NETS), ip
        if payload.startswith(b"GET "):
            requests.append((str(src), payload.split(b" ")[1].decode()))
    assert sorted(requests) == sorted(
        [("192.0.2.10", "/index.html"), ("192.0.2.10", "/cah-lab/probe?id=1")] + [("192.0.2.50", "/healthcheck")] * 12
    )


def test_the_capture_is_reproducible(lab):
    run_py(lab, "make_pcap.py")
    first = hashlib.sha256((lab / "lab.pcap").read_bytes()).hexdigest()
    (lab / "lab.pcap").unlink()
    run_py(lab, "make_pcap.py")
    assert hashlib.sha256((lab / "lab.pcap").read_bytes()).hexdigest() == first


def test_the_case_variant_holds_only_the_capital_letter_request(lab):
    done = run_py(lab, "make_pcap.py", "case")
    assert done.returncode == 0 and "wrote lab-case.pcap with 10 packets" in done.stdout
    paths = [dissect(f)[4].split(b" ")[1] for f in read_pcap(lab / "lab-case.pcap") if dissect(f)[4].startswith(b"GET ")]
    assert paths == [b"/CAH-LAB/PROBE?id=1"]


# --- the rules --------------------------------------------------------------------------


def test_the_rules_use_the_local_sid_range_and_are_well_formed(lab):
    rules = [r for r in (lab / "local.rules").read_text().splitlines() if r and not r.startswith("#")]
    assert len(rules) == 2
    sids = []
    for rule in rules:
        assert re.match(r"^alert http any any -> any any \(.*\)$", rule)
        sid = int(re.search(r"\bsid:(\d+);", rule).group(1))
        assert 1000000 <= sid <= 1999999
        assert re.search(r"\brev:\d+;", rule) and re.search(r'msg:"[^";\\]+";', rule)
        sids.append(sid)
    assert len(set(sids)) == len(sids)


def test_the_page_uses_only_documentation_and_loopback_addresses():
    # the lesson shows a few illustrative lines from Suricata's documentation; none may hold a real-looking host
    for m in re.finditer(r"\b(\d{1,3}(?:\.\d{1,3}){3})(?:/\d+)?\b", text()):
        ip = ipaddress.ip_address(m.group(1))
        ok = ip.is_loopback or any(ip in net for net in DOC_NETS) or m.group(1) in {"0.0.0.0", "3.12.4.0"}  # 3.12.4.0 is a Snort version
        assert ok, f"{m.group(0)} is not a documentation or loopback address"


# --- the summarizer ----------------------------------------------------------------------


def fake_run(folder: Path, alerts: list[tuple[int, str, str]], rules_failed: int = 0, junk: bool = False) -> Path:
    out = folder / "fake_out"
    out.mkdir(exist_ok=True)
    lines = []
    for sid, msg, src in alerts:
        lines.append(json.dumps({"event_type": "alert", "src_ip": src, "alert": {"signature_id": sid, "signature": msg}}))
    lines.append(json.dumps({"event_type": "stats", "stats": {"detect": {"engines": [
        {"rules_loaded": 2 - rules_failed, "rules_failed": rules_failed}]}}}))
    if junk:
        lines.append("{not json; $(touch pwned)")
    (out / "eve.json").write_text("\n".join(lines) + "\n")
    (out / "stats.log").write_text(
        f"Counter | TM Name | Value\ndecoder.pkts | Total | 140\ndetect.alert | Total | {len(alerts)}\n")
    return out


def test_the_summary_counts_by_rule_and_source(lab):
    out = fake_run(lab, [(1000001, "probe", "192.0.2.10")] + [(1000002, "health", "192.0.2.50")] * 3)
    done = run_py(lab, "summarize.py", str(out))
    assert done.returncode == 0
    assert "rules loaded: 2   rules FAILED to load: 0" in done.stdout
    assert "sid 1000001    1  probe" in done.stdout and "sid 1000002    3  health" in done.stdout
    assert "decoder.pkts" in done.stdout and "(not present)" in done.stdout


def test_the_canary_fails_when_an_expected_rule_is_silent(lab):
    out = fake_run(lab, [(1000002, "health", "192.0.2.50")])
    done = run_py(lab, "summarize.py", str(out), "--expect", "1000001", "1000002")
    assert done.returncode == 1 and "MISSING: rule 1000001 did not alert" in done.stdout and "canary: FAILED" in done.stdout
    ok = run_py(lab, "summarize.py", str(out), "--expect", "1000002")
    assert ok.returncode == 0 and "canary: ok" in ok.stdout


def test_a_failed_rule_load_is_reported_even_when_alerts_look_fine(lab):
    out = fake_run(lab, [(1000002, "health", "192.0.2.50")], rules_failed=1)
    assert "rules FAILED to load: 1" in run_py(lab, "summarize.py", str(out)).stdout


def test_a_hostile_line_stays_data(lab):
    out = fake_run(lab, [(1000001, "probe", "192.0.2.10")], junk=True)
    done = run_py(lab, "summarize.py", str(out))
    assert done.returncode == 0 and "unparseable lines skipped: 1" in done.stdout
    assert not (lab / "pwned").exists()


# --- the wrapper ---------------------------------------------------------------------------


def test_the_wrapper_keeps_the_container_small():
    for lang, marker in (("bash", "run.sh RULES_FILE"), ("powershell", "run.ps1 RULES_FILE")):
        body = one_block(lang, marker)
        assert "--network none" in body and "--cap-drop all" in body
        assert "docker.sock" not in body and "podman.sock" not in body and "--privileged" not in body
        assert "jasonish/suricata:8.0.7" in body and ":latest" not in body
        assert "RUNTIME" in body and "IMAGE" in body
        assert "sudo" not in body
    assert not re.search(r"-v\s+\S*(\$HOME|~|/home|/:)", one_block("bash", "run.sh RULES_FILE").replace("$PWD", ""))


@pytest.mark.skipif(
    not (shutil.which("suricata") and Path("/etc/suricata/suricata.yaml").is_file()),
    reason="no suricata with /etc/suricata/suricata.yaml on this machine",
)
def test_suricata_alerts_on_the_capture_as_the_page_says(lab):
    run_py(lab, "make_pcap.py")
    out = lab / "out"
    out.mkdir()
    done = subprocess.run(
        ["suricata", "-c", "/etc/suricata/suricata.yaml", "-r", "lab.pcap", "-S", "local.rules", "-l", "out", "-k", "none"],
        cwd=lab, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    summary = run_py(lab, "summarize.py", "out", "--expect", "1000001", "1000002")
    assert summary.returncode == 0 and "sid 1000002   12" in summary.stdout


# --- the page keeps its promises -----------------------------------------------------------


def test_the_banner_says_what_was_not_run():
    banner = text().split("> **Status:", 1)[1].split("\n", 1)[0]
    for word in ("PowerShell", "Snort", "not run", "Docker", "Wazuh", "pfSense", "OPNsense"):
        assert word in banner or word.lower() in banner.lower(), word


def test_the_lesson_has_the_loop_and_the_flip_and_the_threat_model():
    page = text()
    for word in ("**Build.**", "**Break.**", "**Detect.**", "**Evade.**", "**Defend.**", "### Flip the board",
                 "## Threat model of the IDS itself", "## Claims register"):
        assert word in page, word


def test_every_exercise_has_predict_do_check_and_undo():
    sections = re.split(r"^### Exercise \d+[^\n]*\n", text(), flags=re.MULTILINE)[1:]
    assert len(sections) == 8
    for number, body in enumerate(sections, 1):
        body = re.split(r"\n## |\n### ", body, maxsplit=1)[0]
        for part in ("**Predict.**", "**Do", "**Check.**", "**Undo.**"):
            assert part in body, f"exercise {number} lacks {part}"


def test_sibling_lessons_are_linked_by_exact_name_but_not_from_the_next_line():
    page = text()
    for name in ("Packet-Filters-Compared-iptables-nftables-ufw-pf", "File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh",
                 "Rate-Limiting-at-Every-Layer"):
        assert f"]({name}.md" in page, name
    nxt = [line for line in page.splitlines() if line.startswith("Next:")]
    assert len(nxt) == 1 and "Packet-Filters" not in nxt[0] and "File-Integrity" not in nxt[0] and "Rate-Limiting" not in nxt[0]
    assert "may not resolve until" in page


def test_the_lesson_is_linked_from_the_navigation_and_the_glossary_has_the_new_terms():
    assert "IDS-and-IPS-Snort-and-Suricata.md" in (WIKI / "_Sidebar.md").read_text()
    assert "IDS-and-IPS-Snort-and-Suricata.md" in (WIKI / "Reading-Order.md").read_text()
    glossary = (WIKI / "Glossary.md").read_text()
    for term in ("EVE JSON", "NFQUEUE", "Network tap", "Signature (IDS)", "Snort", "SPAN port", "Suricata"):
        assert f"| **{term}** |" in glossary, term
