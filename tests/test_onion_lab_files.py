# SPDX-License-Identifier: Apache-2.0
"""Guards on the onion-service lab files and the optional cloud flag, issue #391.

labs/onion-lab holds the config files the lab lesson walks through (a torrc, an nginx server block, an i2pd tunnel and router
file, a static page) and check_origin.py, the audit the lesson tells a learner to run. The cloud flag lives in
modules/docker-host. Everything here reads text or talks to a loopback server this test starts itself: no Tor or I2P process
is started, and no real network is touched.

Each rule is a function over text with a negative case, so a rule that stops biting fails here. The rules are the ones the
lesson names: nothing listens on a public interface, the web server does not name itself, no status page, no clearnet
resource, no key or address in the repository, and the cloud flag is off unless asked for and adds nothing public.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

from onion_lab_fixtures import Clean, Leaky, Redirecting, serving

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "onion-lab"
MODULE = ROOT / "modules" / "docker-host"
STACK = ROOT / "stacks" / "30-workloads"

ONION = re.compile(r"\b[a-z2-7]{16,56}\.onion\b")
B32 = re.compile(r"\b[a-z2-7]{32,56}\.b32\.i2p\b")
I2P_NAME = re.compile(r"\b[a-z0-9-]+\.i2p\b")
LONG_B64 = re.compile(r"[A-Za-z0-9+/=_-]{60,}")
PORT = 8080


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def code_lines(text: str) -> list[str]:
    """Non-comment, non-empty lines of an ini, torrc or nginx style file."""
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def load_checker():
    spec = importlib.util.spec_from_file_location("check_origin", LAB / "check_origin.py")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # no __pycache__ inside the lab directory
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


# --- rules over the config files -----------------------------------------------------------------------------------


def torrc_problems(text: str) -> list[str]:
    lines = code_lines(text)
    problems = []
    dirs = [line for line in lines if line.startswith("HiddenServiceDir ")]
    ports = [line for line in lines if line.startswith("HiddenServicePort ")]
    if len(dirs) != 1:
        problems.append(f"expected one HiddenServiceDir, found {len(dirs)}")
    for d in dirs:
        if not d.split(None, 1)[1].startswith("/var/lib/tor/"):
            problems.append(f"the service directory is outside /var/lib/tor: {d}")
    if len(ports) != 1:
        problems.append(f"expected one HiddenServicePort, found {len(ports)}")
    for p in ports:
        target = p.split()[2] if len(p.split()) > 2 else ""
        if not target.startswith(("127.0.0.1:", "unix:")):
            problems.append(f"the target is not loopback or a unix socket: {p}")
    if "SocksPort 0" not in lines:
        problems.append("a service host needs no SOCKS listener: SocksPort 0 is missing")
    for banned in ("ORPort", "DirPort", "ExitRelay", "BridgeRelay", "ControlPort", "HiddenServiceNonAnonymousMode", "HiddenServiceSingleHopMode"):
        if any(line.split()[0] == banned for line in lines):
            problems.append(f"{banned} is set")
    if any(line.startswith("HiddenServiceVersion ") and line.split()[1] != "3" for line in lines):
        problems.append("only version 3 onion services exist")
    return problems


def nginx_problems(text: str) -> list[str]:
    lines = code_lines(text)
    body = " ".join(lines)
    problems = []
    listens = [line for line in lines if line.startswith("listen ")]
    if not listens:
        problems.append("no listen directive")
    for line in listens:
        arg = line.rstrip(";").split()[1]
        if not arg.startswith("127.0.0.1:"):
            problems.append(f"listens beyond loopback: {line}")
    if "server_tokens off;" not in lines:
        problems.append("server_tokens off; is missing, so the Server header names the version")
    for banned in ("stub_status", "autoindex on", "server-status", "add_header Server", "proxy_pass", "fastcgi_pass"):
        if banned in body:
            problems.append(f"{banned} is not part of a static lab origin")
    if re.search(r"\ballow\s+127\.0\.0\.1", body):
        problems.append("a localhost-only allow rule is open to Tor, which connects from loopback")
    return problems


def i2pd_tunnel_problems(text: str) -> list[str]:
    sections: dict[str, dict[str, str]] = {}
    current = None
    for line in code_lines(text):
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections[current] = {}
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            sections[current][key.strip()] = value.strip()
    problems = []
    if len(sections) != 1:
        problems.append(f"expected one tunnel, found {len(sections)}")
    for name, s in sections.items():
        if s.get("type") != "http":
            problems.append(f"{name}: type is not http")
        if s.get("host") != "127.0.0.1" or s.get("port") != str(PORT):
            problems.append(f"{name}: the tunnel does not point at the loopback origin")
        keys = s.get("keys", "")
        if not keys.endswith(".dat") or "/" in keys:
            problems.append(f"{name}: keys must be a file name under the router's data directory")
        if s.get("port") in ("7070", "4444", "4447", "7656", "7654"):
            problems.append(f"{name}: points at one of the router's own local services")
    return problems


def i2pd_router_problems(text: str) -> list[str]:
    lines = code_lines(text)
    problems = []
    flat = "\n".join(lines)
    if "notransit = true" not in lines:
        problems.append("notransit = true is missing")
    for section in ("http", "httpproxy", "socksproxy", "sam", "bob", "i2cp", "i2pcontrol"):
        m = re.search(rf"\[{section}\]\n((?:(?!\[).*\n?)*)", flat + "\n")
        if not m or "enabled = false" not in m.group(1):
            if section == "http":
                if not m or "address = 127.0.0.1" not in m.group(1):
                    problems.append("the web console must be off or bound to 127.0.0.1")
            else:
                problems.append(f"[{section}] is not switched off")
    return problems


def html_files_problems(text: str) -> list[str]:
    problems = []
    if re.search(r"(?i)(src|href|action|poster|data)\s*=\s*[\"']?(https?:)?//", text):
        problems.append("loads or links something from another host")
    if re.search(r"(?i)url\(\s*[\"']?(https?:)?//|@import", text):
        problems.append("css pulls something from another host")
    if re.search(r"(?i)<meta[^>]+generator", text):
        problems.append("a generator tag names the software")
    if re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        problems.append("an IP address is written into the page")
    if re.search(r"(?i)<script|<iframe|<link|<img|<form", text):
        problems.append("the lab page is plain text, with no resource tag")
    return problems


def test_the_lab_files_exist():
    for name in ("torrc.example", "nginx-onion-lab.conf", "i2pd-tunnels.conf", "i2pd.conf.example", "index.html", "404.html", "check_origin.py"):
        assert (LAB / name).is_file(), name


def test_the_torrc_has_one_loopback_service_and_no_relay_or_listener():
    assert torrc_problems(read(LAB / "torrc.example")) == []


def test_the_torrc_rule_bites():
    good = read(LAB / "torrc.example")
    for bad in (
        good.replace("127.0.0.1:8080", "0.0.0.0:8080"),
        good.replace("SocksPort 0", "SocksPort 9050"),
        good + "\nORPort 9001\n",
        good + "\nControlPort 9051\n",
        good.replace("/var/lib/tor/", "/srv/keys/"),
        good + "\nHiddenServiceDir /var/lib/tor/two/\nHiddenServicePort 80 127.0.0.1:8081\n",
        good.replace("HiddenServiceDir", "#HiddenServiceDir"),
    ):
        assert torrc_problems(bad), bad


def test_the_nginx_server_block_listens_on_loopback_only_and_hides_its_version():
    assert nginx_problems(read(LAB / "nginx-onion-lab.conf")) == []


def test_the_nginx_rule_bites():
    good = read(LAB / "nginx-onion-lab.conf")
    for bad in (
        good.replace("listen 127.0.0.1:8080;", "listen 8080;"),
        good.replace("listen 127.0.0.1:8080;", "listen 0.0.0.0:8080;"),
        good.replace("listen 127.0.0.1:8080;", "listen 127.0.0.1:8080;\n    listen [::]:8080;"),
        good.replace("server_tokens off;", ""),
        good.replace("server_tokens off;", "server_tokens on;"),
        good + "\nserver { listen 127.0.0.1:8080; location /status { stub_status; allow 127.0.0.1; deny all; } }\n",
        good.replace("location / {", "autoindex on;\n    location / {"),
    ):
        assert nginx_problems(bad), bad


def test_the_i2pd_tunnel_is_one_http_server_tunnel_to_the_loopback_origin():
    assert i2pd_tunnel_problems(read(LAB / "i2pd-tunnels.conf")) == []


def test_the_i2pd_tunnel_rule_bites():
    good = read(LAB / "i2pd-tunnels.conf")
    for bad in (
        good.replace("127.0.0.1", "192.0.2.10"),
        good.replace("port = 8080", "port = 7070"),
        good.replace("type = http", "type = server"),
        good.replace("onion-lab.dat", "/etc/i2pd/onion-lab.dat"),
        good + "\n[second]\ntype = http\nhost = 127.0.0.1\nport = 8080\nkeys = second.dat\n",
    ):
        assert i2pd_tunnel_problems(bad), bad


def test_the_i2pd_router_file_switches_off_every_local_service_and_transit():
    assert i2pd_router_problems(read(LAB / "i2pd.conf.example")) == []


def test_the_i2pd_router_rule_bites():
    good = read(LAB / "i2pd.conf.example")
    assert i2pd_router_problems(good.replace("notransit = true", "")), "transit"
    assert i2pd_router_problems(good.replace("[sam]\nenabled = false", "[sam]\nenabled = true")), "sam"
    assert i2pd_router_problems(good.replace("address = 127.0.0.1", "address = 192.0.2.5")), "console"


def test_the_lab_page_is_plain_text_with_no_resource():
    for name in ("index.html", "404.html"):
        assert html_files_problems(read(LAB / name)) == [], name


def test_the_html_rule_bites():
    for bad in (
        '<img src="https://cdn.example.test/a.png">',
        '<a href="//cdn.example.test/x">x</a>',
        '<style>body{background:url(http://cdn.example.test/b.png)}</style>',
        '<meta name="generator" content="x">',
        "<p>origin at 192.0.2.10</p>",
        '<script src="app.js"></script>',
    ):
        assert html_files_problems(bad), bad


def test_no_file_in_the_lab_names_an_address_or_holds_a_key():
    files = [p for p in LAB.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert len(files) >= 7, "the guard collected too few files"
    for p in files:
        body = read(p)
        assert not ONION.search(body), p.name
        assert not B32.search(body), p.name
        assert not I2P_NAME.search(body), p.name
        assert not LONG_B64.search(body), p.name
        assert "PRIVATE KEY" not in body, p.name
        assert "—" not in body, p.name
        assert p.suffix not in {".dat", ".key", ".pem"}, p.name
        assert p.name not in {"hostname", "hs_ed25519_secret_key", "hs_ed25519_public_key"}, p.name


def test_the_address_shapes_the_guard_bans_are_really_matched():
    assert ONION.search("go to " + "a" * 56 + ".onion")
    assert B32.search("x " + "b" * 52 + ".b32.i2p")
    assert I2P_NAME.search("irc.example.i2p")
    assert LONG_B64.search("A" * 70)
    assert not ONION.search("<your-address>.onion")


# --- the audit script ------------------------------------------------------------------------------------------------


def test_the_listening_check_flags_a_wildcard_origin_and_passes_loopback():
    c = load_checker()
    good = "LISTEN 0 511 127.0.0.1:8080 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
    assert c.origin_exposure(good, PORT) == []
    for bad in (
        "LISTEN 0 511 0.0.0.0:8080 0.0.0.0:*\n",
        "LISTEN 0 511 *:8080 *:*\n",
        "LISTEN 0 511 [::]:8080 [::]:*\n",
        "LISTEN 0 511 192.0.2.10:8080 0.0.0.0:*\n",
        "LISTEN 0 511 127.0.0.1:8080 0.0.0.0:*\nLISTEN 0 511 [::]:8080 [::]:*\n",
    ):
        assert c.origin_exposure(bad, PORT), bad
    assert c.origin_exposure("LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n", PORT) == ["nothing listens on port 8080, so there is no origin to publish"]


def test_the_wildcard_listing_names_every_open_listener_for_review():
    c = load_checker()
    text = "LISTEN 0 511 127.0.0.1:8080 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 4096 [::]:4567 [::]:*\nLISTEN 0 5 [::1]:631 [::]:*\n"
    assert c.wildcard_listeners(text) == ["0.0.0.0:22", "[::]:4567"]


def test_the_header_check_flags_a_version_a_stack_hint_and_a_leaked_address():
    c = load_checker()
    assert c.header_problems([("Server", "nginx"), ("Content-Type", "text/html"), ("Content-Length", "10")]) == []
    assert c.header_problems([("Server", "nginx/1.30.6")]), "version"
    assert c.header_problems([("Server", "Apache/2.4.58 (Ubuntu)")]), "apache"
    assert c.header_problems([("X-Powered-By", "PHP/8.3")]), "x-powered-by"
    assert c.header_problems([("Via", "1.1 proxy")]), "via"
    assert c.header_problems([("X-Forwarded-For", "203.0.113.9")]), "x-forwarded-for"
    assert c.header_problems([("Location", "http://203.0.113.5:8080/css/")]), "absolute redirect with an address"
    assert c.header_problems([("Location", "http://example.test:8080/css/")]), "absolute redirect"
    assert c.header_problems([("X-Backend", "203.0.113.7")]), "any header value holding an address"
    assert c.header_problems([("Location", "/css/")]) == [], "a relative redirect is fine"


def test_the_body_check_flags_clearnet_resources_and_names_links_for_review():
    c = load_checker()
    assert c.body_problems("<p>plain</p>") == []
    for bad in (
        '<script src="https://cdn.example.test/a.js"></script>',
        '<link rel="stylesheet" href="//cdn.example.test/a.css">',
        '<img src="http://cdn.example.test/a.png">',
        '<iframe src="https://example.test/"></iframe>',
        '<form action="https://example.test/post"></form>',
        '<style>@import url("https://cdn.example.test/a.css");</style>',
        '<div style="background:url(https://cdn.example.test/a.png)"></div>',
        '<meta name="generator" content="Hugo 0.1">',
        "<p>the origin is 203.0.113.9</p>",
        "<!-- built at host 203.0.113.9 -->",
    ):
        assert c.body_problems(bad), bad
    # An ordinary link is not a load, but it is a click that sends a referrer, so it is listed as a review line.
    assert c.body_problems('<a href="https://example.test/">out</a>') == []
    assert c.outbound_links('<a href="https://example.test/">out</a><a href="/in">in</a>') == ["https://example.test/"]


def test_a_bare_server_name_is_listed_for_review_and_a_version_is_a_failure():
    c = load_checker()
    assert c.server_review([("Server", "nginx"), ("Content-Type", "text/html")]) == ["header Server names the software: nginx"]
    assert c.server_review([("server", " Caddy ")]) == ["header Server names the software: Caddy"]
    assert c.server_review([("Content-Type", "text/html"), ("Server", "")]) == []
    assert c.server_review([("Content-Type", "text/html")]) == []
    # A version or an operating system is already a failure in header_problems, so it is not listed twice.
    assert c.server_review([("Server", "nginx/1.30.6")]) == []
    assert c.server_review([("Server", "Apache (Ubuntu)")]) == []
    assert c.header_problems([("Server", "nginx/1.30.6")])


def test_the_status_page_check_flags_a_2xx_or_3xx_and_nothing_else():
    c = load_checker()
    assert c.exposed_paths({"/server-status": 404, "/.git/HEAD": 404, "/": 200}) == []
    assert c.exposed_paths({"/server-status": 200, "/.env": 200, "/nginx_status": 403}) == ["/.env", "/server-status"]
    assert c.exposed_paths({"/.env": 301, "/status": 302, "/stub_status": 204, "/phpinfo.php": 500, "/server-info": 401}) == ["/.env", "/status", "/stub_status"]
    assert c.exposed_paths({"/.env": 399, "/status": 400, "/server-info": 199}) == ["/.env"]
    assert "/server-status" in c.PROBE_PATHS and "/stub_status" in c.PROBE_PATHS and "/.git/HEAD" in c.PROBE_PATHS


def test_the_audit_lists_the_server_name_for_review_without_failing(tmp_path, capsys):
    c = load_checker()
    ss = tmp_path / "ss.txt"
    with serving(Clean) as port:
        ss.write_text(LOOPBACK_ONLY.format(port=port))
        assert c.main(["--port", str(port), "--ss-file", str(ss)]) == 0
    out = capsys.readouterr().out
    assert out.count("[REVIEW] header Server names the software: nginx") == 1, "once, not once per request"
    assert "0 problems" in out


def test_the_audit_inspects_the_headers_and_status_of_the_probe_responses(tmp_path, capsys):
    c = load_checker()
    ss = tmp_path / "ss.txt"
    with serving(Redirecting) as port:
        ss.write_text(LOOPBACK_ONLY.format(port=port))
        assert c.main(["--port", str(port), "--ss-file", str(ss)]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] the path /.env answers 301" in out
    assert "[FAIL] header Location is an absolute address" in out and "/.env/" in out
    assert "[FAIL] the path /status answers 200" in out
    assert "2 problems" not in out and "3 problems" in out


LOOPBACK_ONLY = "LISTEN 0 511 127.0.0.1:{port} 0.0.0.0:*\n"


def test_the_audit_passes_a_clean_loopback_origin_and_fails_a_leaky_one(tmp_path, capsys):
    c = load_checker()
    ss = tmp_path / "ss.txt"
    with serving(Clean) as clean_port:
        ss.write_text(LOOPBACK_ONLY.format(port=clean_port))
        assert c.main(["--port", str(clean_port), "--ss-file", str(ss)]) == 0
    assert "0 problems" in capsys.readouterr().out
    with serving(Leaky) as leaky_port:
        ss.write_text(LOOPBACK_ONLY.format(port=leaky_port))
        assert c.main(["--port", str(leaky_port), "--ss-file", str(ss)]) == 1
        out = capsys.readouterr().out
        for needle in ("Server", "X-Powered-By", "cdn.example.test", "203.0.113.9", "/server-status"):
            assert needle in out, needle
        ss.write_text(f"LISTEN 0 511 0.0.0.0:{leaky_port} 0.0.0.0:*\n")
        assert c.main(["--port", str(leaky_port), "--ss-file", str(ss)]) == 1
    assert "listens on 0.0.0.0" in capsys.readouterr().out


def test_the_audit_refuses_a_target_that_is_not_loopback(tmp_path, capsys):
    c = load_checker()
    ss = tmp_path / "ss.txt"
    ss.write_text(LOOPBACK_ONLY.format(port=8080))
    assert c.main(["--host", "203.0.113.5", "--port", "8080", "--ss-file", str(ss)]) == 2
    assert "loopback" in capsys.readouterr().out
    assert c.main(["--host", "example.test", "--port", "8080", "--ss-file", str(ss)]) == 2


def test_the_audit_uses_only_the_standard_library_and_sends_nothing_but_get_requests():
    body = read(LAB / "check_origin.py")
    imports = set(re.findall(r"^(?:from|import) (\w+)", body, re.MULTILINE))
    assert imports <= {"argparse", "html", "http", "ipaddress", "re", "subprocess", "sys"}, imports
    for banned in ("import socket", "urllib", "import requests", "os.system", "shell=True", "eval(", "exec(", '"POST"', '"PUT"', '"DELETE"'):
        assert banned not in body, banned
    # Every request the script makes is a GET (the import allow-list above is what keeps a library out).
    assert re.findall(r'conn\.request\("(\w+)"', body) == ["GET"]


# --- the cloud flag --------------------------------------------------------------------------------------------------


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", text)


def onion_block(template: str) -> str:
    m = re.search(r"%\{~ if onion_service_enabled \}\n(.*?)%\{~ endif \}", template, re.DOTALL)
    return m.group(0) if m else ""


def onion_outside_the_block(template: str) -> list[str]:
    """Every onion-specific word that sits outside an `if onion_service_enabled` block."""
    rest = re.sub(r"%\{~ if onion_service_enabled \}.*?%\{~ endif \}", "", template, flags=re.DOTALL)
    return [w for w in ("HiddenService", "/etc/tor", "cah-onion", "onion-origin", "torrc", "ReachableAddresses") if w in rest]


def flag_listening_problems(block: str) -> list[str]:
    problems = []
    for m in re.finditer(r"(?m)^\s*HiddenServicePort\s+\d+\s+(\S+)", block):
        if not m.group(1).startswith("127.0.0.1:"):
            problems.append(f"onion target {m.group(1)}")
    for m in re.finditer(r'(?m)^\s+- "([^"]*:[0-9]+:[0-9]+)"', block):
        if not m.group(1).startswith("127.0.0.1:"):
            problems.append(f"published port {m.group(1)}")
    for banned in ("0.0.0.0", "[::]", "network_mode", "privileged", "docker.sock", "ORPort", "DirPort", "ExitRelay", "BridgeRelay", "ControlPort"):
        if banned in block:
            problems.append(f"{banned}")
    if re.search(r"(?m)^\s+- \"?[0-9]+:[0-9]+\"?\s*$", block):
        problems.append("a published port with no address")
    return problems


def flag_key_problems(block: str) -> list[str]:
    problems = []
    if re.search(r"hs_ed25519|BEGIN [A-Z ]*KEY|\.onion\b|cat[^\n]*hostname", block):
        problems.append("a key file name, key text, an address or a read of the address")
    if re.search(r"(?m)^[^#\n]*echo[^\n]*\$\(\s*cat", block):
        problems.append("a command substitution that prints a file")
    return problems


def test_the_flag_defaults_to_off_in_the_module_and_the_stack():
    for directory in (MODULE, STACK):
        text = strip_comments(read(directory / "variables.tf"))
        m = re.search(r'variable "onion_service_enabled" \{(.*?)\n\}', text, re.DOTALL)
        assert m, directory
        assert re.search(r"default\s*=\s*false", m.group(1)), directory
        assert re.search(r"nullable\s*=\s*false", m.group(1)), directory
        assert "bool" in m.group(1)


def test_every_onion_word_in_the_cloud_init_sits_inside_the_flag_block():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    assert len(onion_block(template)) > 1000, "the scan lost its target"
    assert onion_outside_the_block(template) == []
    assert onion_outside_the_block(template + "\n  - path: /etc/tor/torrc\n"), "the rule must bite"


def test_the_flag_block_listens_on_loopback_only_and_runs_no_relay():
    block = onion_block(read(MODULE / "cloud-init.yaml.tftpl"))
    assert flag_listening_problems(block) == []
    for bad in (
        block.replace('"127.0.0.1:8080:8080"', '"8080:8080"'),
        block.replace('"127.0.0.1:8080:8080"', '"0.0.0.0:8080:8080"'),
        block.replace("HiddenServicePort 80 127.0.0.1:8080", "HiddenServicePort 80 192.0.2.10:8080"),
        block + "\n      ORPort 9001\n",
        block + "\n      ControlPort 9051\n",
        block + "\n          network_mode: host\n",
        block + "\n            - /var/run/docker.sock:/var/run/docker.sock\n",
    ):
        assert flag_listening_problems(bad), bad


def test_the_flag_block_carries_no_key_and_no_address_and_never_prints_one():
    block = onion_block(read(MODULE / "cloud-init.yaml.tftpl"))
    assert flag_key_problems(block) == []
    for bad in (
        block + "\n      cat /var/lib/tor/cah-site/hostname\n",
        block + "\n      echo \"$(cat /var/lib/tor/cah-site/hostname)\"\n",
        block + "\n      /var/lib/tor/cah-site/hs_ed25519_secret_key\n",
        block + "\n      " + "a" * 56 + ".onion\n",
    ):
        assert flag_key_problems(bad), bad


def test_the_flag_adds_no_resource_and_no_firewall_rule():
    main = strip_comments(read(STACK / "main.tf"))
    resources = re.findall(r'(?m)^(resource|data|module)\s+"([^"]+)"', main)
    assert ("resource", "digitalocean_droplet") not in resources, "the droplet lives in the module"
    # The stack still has the same blocks as before the flag: tag, ssh key lookup, firewall, workload, project, two Twingate.
    assert sorted(name for _, name in resources) == sorted(
        ["digitalocean_tag", "digitalocean_ssh_key", "workload_firewall", "workload", "digitalocean_project_resources", "twingate_resource", "twingate_resource"]
    )
    assert "onion" not in "".join(re.findall(r"inbound_from_other_tags\s*=\s*\[.*?\]", main, re.DOTALL))
    module_main = strip_comments(read(MODULE / "main.tf"))
    assert len(re.findall(r'(?m)^resource\s+"', module_main)) == 1


def test_the_cost_manifest_and_approvals_are_untouched_by_the_flag():
    # The flag must not need an approval-level edit: the stack's manifest still prices nothing and says unapproved.
    manifest = json.loads(read(STACK / "cost.json"))
    assert manifest["resources"] == [] and manifest["workload_approved"] is False


def test_the_origin_image_default_is_pinned_by_tag_and_digest_in_the_module_and_the_lab_lesson_names_the_same_one():
    variables = read(MODULE / "variables.tf")
    m = re.search(r'variable "onion_origin_image" \{.*?default\s*=\s*"([^"]+)"', variables, re.DOTALL)
    assert m
    assert re.fullmatch(r"nginx:\d+\.\d+\.\d+-alpine@sha256:[0-9a-f]{64}", m.group(1))
    lab = read(ROOT / "labs" / "wordpress-at-scale" / "compose.yaml")
    tag = m.group(1).split("@")[0]
    assert f"library/{tag}" in lab, "the tag is the one the WordPress-at-scale lab already uses"
