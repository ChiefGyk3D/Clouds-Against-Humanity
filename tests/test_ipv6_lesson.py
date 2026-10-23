# SPDX-License-Identifier: Apache-2.0
"""The IPv6 lesson's code runs, says what the page says, and keeps the page's promises.

docs/wiki/IPv6-Adoption-and-Handling-It-Safely.md has the learner paste scripts into files with
`cat > name <<'LAB_EOF'`. The two pure-Python ones (subnets.py and allowlist.py) are pulled out of the
page, run in a temporary folder and compared with the output the page prints; the others are checked
for syntax only, because they need a Linux network namespace. The page also promises: documentation
addresses only, no em dashes, the maintainer's words quoted, a retrieval date for every statistic.
"""

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "IPv6-Adoption-and-Handling-It-Safely.md"
HEREDOC = re.compile(
    r"cat > (?P<name>[\w.-]+) <<'LAB_EOF'\n(?P<body>.*?)^LAB_EOF$",
    re.MULTILINE | re.DOTALL,
)
FILES = {"subnets.py", "ra.py", "lab-up.sh", "serve.py", "probe.py", "allowlist.py"}


def page() -> str:
    return PAGE.read_text()


def files() -> dict[str, str]:
    return {m["name"]: m["body"] for m in HEREDOC.finditer(page())}


def run(tmp_path, name, *args):
    (tmp_path / name).write_text(files()[name])
    return subprocess.run(
        [sys.executable, "-I", name, *args],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_all_lab_files_are_on_the_page():
    assert FILES <= set(files())


def test_python_files_compile_and_the_shell_file_parses(tmp_path):
    for name, body in files().items():
        (tmp_path / name).write_text(body)
        if name.endswith(".py"):
            compile(body, name, "exec")
        else:
            done = subprocess.run(["bash", "-n", name], cwd=tmp_path, capture_output=True, text=True, check=False)
            assert done.returncode == 0, done.stderr


def test_subnets_prints_what_the_page_shows(tmp_path):
    done = run(tmp_path, "subnets.py")
    assert done.returncode == 0, done.stderr
    out = done.stdout
    for line in (
        "a /48 holds 65536 separate /64 networks",
        "a /56 holds 256 separate /64 networks",
        "   2001:db8:abcd:1::/64   first host 2001:db8:abcd:1::1",
        "  fd12:3456:789a::1    unique local (ULA, private, not routed on the internet)",
        "  ::ffff:192.0.2.5     IPv4-mapped (an IPv4 client seen through an IPv6 socket)",
        "on 2001:db8:abcd:1::/64 that is 2001:db8:abcd:1:200:5eff:fe00:5301",
    ):
        assert line in out, line
        assert line in page(), f"the page no longer shows: {line}"
    ula = re.search(r"different every run\): (\S+)", out).group(1)
    net = ipaddress.ip_network(ula)
    assert net.prefixlen == 64 and net.subnet_of(ipaddress.ip_network("fd00::/8"))


def test_allowlist_matches_the_page_and_unwraps_mapped_addresses(tmp_path):
    done = run(tmp_path, "allowlist.py", "192.0.2.0/24,198.51.100.7", "192.0.2.9", "2001:db8::9", "::ffff:192.0.2.9", "::ffff:203.0.113.5")
    assert done.returncode == 0, done.stderr
    rows = {line.split()[0]: line.split()[1:] for line in done.stdout.splitlines()[1:5]}
    assert rows["192.0.2.9"] == ["allow", "allow"]
    assert rows["2001:db8::9"] == ["deny", "deny"]
    assert rows["::ffff:192.0.2.9"] == ["deny", "allow"]  # the naive check denies its own client
    assert rows["::ffff:203.0.113.5"] == ["deny", "deny"]
    assert "WARNING: IPv4 only." in done.stdout
    both = run(tmp_path, "allowlist.py", "192.0.2.0/24,2001:db8:1:1::/64", "2001:db8:1:1::5", "2001:db8:1:2::5")
    assert "WARNING" not in both.stdout
    assert "WARNING: a /0 entry" in run(tmp_path, "allowlist.py", "0.0.0.0/0", "192.0.2.1").stdout


def test_ra_refuses_anything_but_a_slash_64(tmp_path):
    done = run(tmp_path, "ra.py", "e0", "2001:db8:1::/48")
    assert done.returncode != 0
    assert "/64" in done.stderr


def test_the_maintainers_words_are_quoted_exactly_and_nothing_waits_for_him():
    text = page()
    for quote in (
        "While IPv6 has been a thing for years, many companies are hesitant to adopt it, and even I haven't, for a myriad of reasons.",
        "IPv6 probably doesn't work, as I have it disabled on pfSense.",
        "While v6 fixes IP exhaustion, the format is hard to remember, and it was designed around the idea that every single device can have its own IP address directly, and it becomes harder to secure traffic.",
    ):
        assert quote in text
    assert "## Why the author has not adopted IPv6" in text
    low = text.lower()
    for waiting in ("to be supplied", "waiting for him", "placeholder", "tbd", "todo"):
        assert waiting not in low, waiting


def test_no_em_dash_and_no_forbidden_word():
    text = page()
    assert "—" not in text
    assert not re.search(r"\bpaid\b", text, re.IGNORECASE)


def test_every_ipv6_address_in_the_page_is_a_documentation_ula_or_scope_address():
    token = re.compile(r"(?<![\w:.])([0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?:/\d{1,3})?)(?![\w:])")
    allowed = [
        ipaddress.ip_network(n)
        for n in ("2001:db8::/32", "fc00::/7", "fe80::/10", "ff00::/8", "::/128", "::1/128", "::ffff:0:0/96", "::/0", "2000::/3")
    ]
    bad = []
    for fence_free in re.split(r"(?m)^```.*?^```", page(), flags=re.DOTALL | re.MULTILINE):
        for m in token.finditer(fence_free):
            raw = m.group(1)
            if raw.count(":") < 2 or raw.strip(":") == "":
                continue
            try:
                net = ipaddress.ip_network(raw, strict=False)
            except ValueError:
                continue  # a time such as 22:09:47, or a MAC address
            if not any(net.version == a.version and net.subnet_of(a) for a in allowed):
                bad.append(raw)
    assert not bad, f"not documentation, ULA, link-local or scope addresses: {bad}"


def test_every_statistic_carries_a_retrieval_date_and_the_register_says_numbers_drift():
    text = page()
    register = text[text.index("## Claims register") :]
    assert "2026-10-22" in register
    assert "drift" in register
    for needle in ("45.589127", "43.64", "0.005", "M-21-07", "Cloudflare Radar"):
        assert needle in register, needle
    assert "HTTP 403" in register  # the Cloudflare figure is not quoted because it was not read


def test_required_sections_exist():
    text = page()
    for heading in (
        "## What you will be able to do",
        "## Why adoption is slow",
        "## Why the author has not adopted IPv6",
        "## What this project does, and why",
        "## Turning it on deliberately: everything that must change together",
        "## If IPv6 is disabled on your router (as the maintainer's pfSense has it)",
        "## A threat model of a dual-stack host",
        "## Build, break, detect, evade, defend (the dual-stack loop)",
        "### Flip the board",
        "## Claims register",
    ):
        assert heading in text, heading
    assert "**Cost box. Read this before you create anything.**" in text
