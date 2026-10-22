"""The code on the CDN real-client-IP lesson runs, and says what the page says it does.

docs/wiki/Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md teaches with scripts the
learner pastes into files. The two pure-Python ones (xff.py and asn.py) need no
Nginx, so they are pulled out of the page, run in a temporary folder, and compared
with the output the page prints. The Nginx part of the lab is not run here.
"""

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md"
HEREDOC = re.compile(
    r"cat > (?P<name>[\w.-]+) <<'LAB_EOF'\n(?P<body>.*?)^LAB_EOF$",
    re.MULTILINE | re.DOTALL,
)
IPV4 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?:/\d{1,2})?(?![\w.])")
# Documentation (RFC 5737), loopback, private, benchmark and shared ranges the page may print.
OK_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "127.0.0.0/8",
        "10.0.0.0/8",
        "198.18.0.0/15",
        "100.64.0.0/10",
        "0.0.0.0/0",
        "192.168.0.0/16",
        "172.16.0.0/12",
    )
]


def page() -> str:
    return PAGE.read_text()


def script(name: str) -> str:
    found = {m["name"]: m["body"] for m in HEREDOC.finditer(page())}
    assert name in found, f"{name} is not on the page"
    return found[name]


def run(tmp_path, name, *args):
    (tmp_path / name).write_text(script(name))
    return subprocess.run(
        [sys.executable, "-I", name, *args],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_all_lab_files_are_on_the_page():
    found = {m["name"] for m in HEREDOC.finditer(page())}
    assert {
        "app.py",
        "make-conf.sh",
        "ctl.sh",
        "pp.py",
        "xff.py",
        "asn.py",
        "cf-ranges.sh",
    } <= found


def test_xff_cases_match_the_page(tmp_path):
    text = page()
    cases = [
        (
            ("198.51.100.50", "203.0.113.99, 192.0.2.7", "198.51.100.0/24"),
            "client=192.0.2.7 (first untrusted from the right)",
        ),
        (
            (
                "198.51.100.50",
                "203.0.113.99, 192.0.2.7, 198.51.100.60",
                "198.51.100.0/24",
            ),
            "client=192.0.2.7 (first untrusted from the right)",
        ),
        (
            ("203.0.113.200", "10.0.0.1", "198.51.100.0/24"),
            "client=203.0.113.200 (peer not trusted: header ignored)",
        ),
        (
            ("198.51.100.50", "203.0.113.99", "198.51.100.0/24"),
            "client=203.0.113.99 (first untrusted from the right)",
        ),
    ]
    for args, expected in cases:
        result = run(tmp_path, "xff.py", *args)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected
        assert expected in text, "the page's printed output drifted from the script"


def test_a_forged_header_from_an_untrusted_peer_is_ignored(tmp_path):
    result = run(tmp_path, "xff.py", "203.0.113.200", "198.51.100.1", "192.0.2.0/24")
    assert "peer not trusted" in result.stdout
    assert result.stdout.startswith("client=203.0.113.200")


def test_asn_lookup_matches_the_page(tmp_path):
    result = run(
        tmp_path,
        "asn.py",
        "198.51.100.77",
        "203.0.113.9",
        "203.0.113.200",
        "192.0.2.50",
        "2001:db8:100::5",
        "198.18.1.1",
    )
    assert result.returncode == 0, result.stderr
    text = page()
    for line in result.stdout.splitlines():
        assert line.rstrip() in text, f"page output drifted: {line!r}"
    assert (tmp_path / "asn-table.csv").exists()


def test_longest_prefix_wins_in_the_toy_table(tmp_path):
    result = run(tmp_path, "asn.py", "203.0.113.9", "203.0.113.200")
    first, second = result.stdout.splitlines()
    assert "AS64501" in first and "AS64502" in second


def test_page_prints_only_documentation_style_addresses():
    bad = []
    for number, line in enumerate(page().splitlines(), 1):
        for match in IPV4.finditer(line):
            try:
                addr = ipaddress.ip_address(match.group(1))
            except ValueError:
                continue
            if not any(addr in net for net in OK_NETS):
                # Cloudflare's own first ranges appear only in the pasted Exercise 7 output.
                if "set_real_ip_from" in line:
                    continue
                bad.append((number, match.group(1)))
    assert not bad, f"addresses outside the documentation ranges: {bad}"


def test_page_links_both_siem_repositories_and_pfsense_docs():
    text = page()
    assert "https://github.com/ChiefGyk3D/pfsense-siem-stack" in text
    assert "https://github.com/ChiefGyk3D/siem-docker-stack" in text
    assert "https://docs.netgate.com/pfsense/en/latest/" in text


def test_page_has_the_required_sections():
    text = page()
    for heading in (
        "## The trust problem",
        "## Why an IP address is a weak identifier",
        "## OSI and TCP/IP for cloud people",
        "## Build, break, detect, evade, defend",
        "### Flip the board",
        "## Threat model",
        "## Claims register",
    ):
        assert heading in text, heading


def test_no_em_dashes_on_the_page():
    assert "—" not in page()
