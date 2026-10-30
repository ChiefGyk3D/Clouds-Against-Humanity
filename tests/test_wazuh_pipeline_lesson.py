# SPDX-License-Identifier: Apache-2.0
"""The Wazuh SIEM and data pipelines lesson (issue #321): its scripts run and say what the page says.

The page teaches with two Python scripts the learner pastes into files. A script that is
broken, or output on the page that has drifted from what the script prints, teaches the
wrong thing. These tests pull each block out of the page, run it in a temporary folder and
compare. The Wazuh XML is only checked to be well-formed and to stay in the documented
custom ID range: the page says it was never loaded into a manager, and so does this file.
Everything is invented data on documentation addresses. The guards collect loosely (any
fenced block) and assert strictly (exactly one block per marker), and each has a negative
case showing it bites.
"""

import ipaddress
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Wazuh-SIEM-and-Data-Pipelines.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def blocks(text: str, lang: str) -> list[str]:
    return [body for tag, body in FENCE.findall(text) if tag == lang]


def one_block(text: str, lang: str, marker: str) -> str:
    found = [b for b in blocks(text, lang) if marker in b]
    assert len(found) == 1, f"expected one {lang} block with {marker!r}, found {len(found)}"
    return found[0]


def run_py(folder: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", script, *args], cwd=folder, capture_output=True, text=True, timeout=30, check=False
    )


@pytest.fixture()
def lab(tmp_path):
    text = PAGE.read_text(encoding="utf-8")
    (tmp_path / "make_log.py").write_text(one_block(text, "python", "Builds an INVENTED connector log"))
    (tmp_path / "pipeline.py").write_text(one_block(text, "python", "A toy of the Wazuh server"))
    for name, args in (("connector.log", ()), ("skewed.log", ("--skew", "3600"))):
        made = run_py(tmp_path, "make_log.py", *args)
        assert made.returncode == 0, made.stderr
        (tmp_path / name).write_text(made.stdout)
    return tmp_path


def alerts(proc) -> list[dict]:
    return [json.loads(line) for line in proc.stdout.splitlines()]


def stats(proc) -> dict:
    line = next(ln for ln in proc.stderr.splitlines() if ln.startswith("stats:"))
    return json.loads(line[len("stats:"):])


def test_the_page_exists_and_says_it_was_written_from_reading():
    text = PAGE.read_text(encoding="utf-8")
    assert "written from reading" in text.split("\n## ", 1)[0]


def test_the_log_has_fourteen_lines_with_documentation_addresses_only(lab):
    lines = (lab / "connector.log").read_text().splitlines()
    assert len(lines) == 14
    for ip in set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "\n".join(lines))):
        assert any(ipaddress.ip_address(ip) in net for net in DOC_NETS), ip


def test_exactly_one_alert_for_the_burst_and_the_stats_match_the_page(lab):
    proc = run_py(lab, "pipeline.py", "connector.log")
    assert proc.returncode == 0, proc.stderr
    got = alerts(proc)
    assert [(a["rule"], a["level"], a["srcip"], a["at"]) for a in got] == [
        (100111, 10, "203.0.113.7", "Oct 30 12:00:12")
    ]
    assert stats(proc) == {"lines": 14, "no_header": 0, "no_decoder": 1, "undecoded": 1, "decoded": 12, "alerts": 1}


def test_negative_four_failures_stay_quiet_and_five_fire(lab):
    text = (lab / "connector.log").read_text().splitlines()
    four = [ln for ln in text if "192.0.2.66" in ln]
    assert len(four) == 4
    (lab / "four.log").write_text("\n".join(four) + "\n")
    assert alerts(run_py(lab, "pipeline.py", "four.log")) == []
    (lab / "five.log").write_text("\n".join(four + [four[-1].replace(":46 ", ":48 ")]) + "\n")
    assert [a["rule"] for a in alerts(run_py(lab, "pipeline.py", "five.log"))] == [100111]


def test_clock_skew_hides_the_burst_and_the_skewed_hosts_stamps_are_an_hour_back(lab):
    skewed = (lab / "skewed.log").read_text()
    assert "Oct 30 11:00:03 connector-b" in skewed
    proc = run_py(lab, "pipeline.py", "skewed.log")
    assert alerts(proc) == []
    assert stats(proc)["decoded"] == 12  # nothing was dropped: the lines parse, the counting fails


def test_min_level_three_shows_the_quiet_rule(lab):
    proc = run_py(lab, "pipeline.py", "connector.log", "--min-level", "3")
    levels = [a["level"] for a in alerts(proc)]
    assert levels.count(3) == 11 and levels.count(10) == 1  # 6 + 1 + 4 decoded failures, one burst alert


def test_the_pipeline_survives_garbage_lines(lab):
    junk = b"not a log line\n" + bytes([255, 254, 0]) + b"\n" + b"A" * 20000 + b"\n"
    (lab / "junk.log").write_bytes(junk)
    proc = run_py(lab, "pipeline.py", "junk.log")
    assert proc.returncode == 0, proc.stderr
    assert stats(proc)["no_header"] == 3 and alerts(proc) == []


def test_the_draft_xml_is_well_formed_and_uses_the_documented_custom_id_range():
    text = PAGE.read_text(encoding="utf-8")
    decoders = ET.fromstring("<root>" + one_block(text, "xml", "<decoder") + "</root>")
    assert [d.get("name") for d in decoders.findall("decoder")] == ["cahdemo", "cahdemo"]
    rules = ET.fromstring("<root>" + one_block(text, "xml", "<rule ") + "</root>")
    ids = [int(r.get("id")) for r in rules.iter("rule")]
    assert ids and all(100000 <= i <= 120000 for i in ids), ids
    assert all(r.get("level") is not None for r in rules.iter("rule"))


def test_the_xml_guard_bites_on_an_id_outside_the_range():
    bad = ET.fromstring('<root><rule id="5710" level="5"/></root>')
    assert not all(100000 <= int(r.get("id")) <= 120000 for r in bad.iter("rule"))


def test_the_claims_register_cites_wazuh_pages_with_a_retrieval_date():
    text = PAGE.read_text(encoding="utf-8")
    register = text.split("## Claims register", 1)[1]
    assert "2026-10-30" in register
    assert len(re.findall(r"https://documentation\.wazuh\.com/current/\S+", register)) >= 8


def test_no_non_documentation_address_in_the_page():
    text = PAGE.read_text(encoding="utf-8")
    for ip in set(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)):
        addr = ipaddress.ip_address(ip)
        assert any(addr in net for net in DOC_NETS) or addr.is_loopback or ip == "0.0.0.0", ip
