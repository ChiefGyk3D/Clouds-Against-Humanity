# SPDX-License-Identifier: Apache-2.0
"""Audit the lab's web server (the origin) for the mistakes that expose a service behind an onion or I2P address.

It answers the questions the lesson lists, for an origin on THIS machine only:

  1. Does the origin listen on anything but loopback?
  2. Do the response headers (the front page, a missing page and every probe path) carry a version, an operating system,
     a proxy hint or an address? A Server header that names only the software is listed for review, not failed.
  3. Does the page load or embed anything from another host, or write an address into its text?
  4. Do the usual status and debug paths answer with a 2xx or 3xx status?

It sends plain GET requests to a loopback address and reads `ss -ltn`. It refuses any other target, never touches Tor or I2P,
and changes nothing. A clean run proves only that these four checks found nothing; it does not prove the service is safe.

Usage: python3 check_origin.py [--host 127.0.0.1] [--port 8080] [--ss-file FILE]
Exit status: 0 no problems, 1 problems found, 2 refused or could not run.
"""

import argparse
import html.parser
import http.client
import ipaddress
import re
import subprocess
import sys

PROBE_PATHS = (
    "/server-status",
    "/server-info",
    "/nginx_status",
    "/stub_status",
    "/status",
    "/phpinfo.php",
    "/.git/HEAD",
    "/.env",
)
STACK_HEADERS = ("x-powered-by", "x-aspnet-version", "x-generator", "via", "x-forwarded-for", "x-real-ip", "x-backend", "x-served-by")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
VERSIONED = re.compile(r"[A-Za-z][\w.-]*/\d")
WILDCARDS = ("0.0.0.0", "*", "[::]", "::")
# Attributes that make a browser fetch or embed something on its own.
LOAD_ATTRS = {
    "script": "src",
    "img": "src",
    "iframe": "src",
    "embed": "src",
    "source": "src",
    "audio": "src",
    "video": "src",
    "track": "src",
    "object": "data",
    "form": "action",
}
REMOTE = re.compile(r"^\s*(?:https?:)?//", re.IGNORECASE)


def listeners(ss_text):
    """(local address, port) of each listener in `ss -ltn` output."""
    found = []
    for line in ss_text.splitlines():
        cols = line.split()
        if len(cols) < 5 or cols[0] != "LISTEN":
            continue
        local = cols[3]
        addr, _, port = local.rpartition(":")
        if port.isdigit():
            found.append((addr, int(port)))
    return found


def is_loopback(addr):
    return addr.startswith("127.") or addr in ("[::1]", "::1")


def origin_exposure(ss_text, port):
    """Problems with where the origin port listens."""
    on_port = [addr for addr, p in listeners(ss_text) if p == port]
    if not on_port:
        return [f"nothing listens on port {port}, so there is no origin to publish"]
    problems = []
    for addr in on_port:
        if not is_loopback(addr):
            where = "every interface" if addr in WILDCARDS else "a non-loopback address"
            problems.append(f"the origin listens on {addr}:{port} ({where}); bind it to 127.0.0.1")
    return problems


def wildcard_listeners(ss_text):
    """Every listener on a wildcard address, for the learner to review (the origin check is separate)."""
    return sorted({f"{addr}:{port}" for addr, port in listeners(ss_text) if addr in WILDCARDS})


def header_problems(headers):
    problems = []
    for name, value in headers:
        value = value.strip()
        lower = name.lower()
        if lower == "server" and (VERSIONED.search(value) or "(" in value):
            problems.append(f"header Server names a version or an operating system: {value}")
        if lower in STACK_HEADERS:
            problems.append(f"header {name} describes the stack or a hop: {value}")
        elif lower == "location" and REMOTE.match(value):
            problems.append(f"header Location is an absolute address (a redirect can name a host or port): {value}")
        elif lower != "server" and IPV4.search(value):
            problems.append(f"header {name} holds an IP address: {value}")
    return problems


def server_review(headers):
    """Review lines for a Server header that names the software without a version.

    A bare name such as `nginx` is what a stock server sends even with its version hidden, so it is listed for the
    reader to judge and is not a failure. A version or an operating system is already a failure in header_problems,
    so it is left out here."""
    lines = []
    for name, value in headers:
        value = value.strip()
        if name.lower() == "server" and value and not (VERSIONED.search(value) or "(" in value):
            lines.append(f"header Server names the software: {value}")
    return lines


class Scan(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.loads = []
        self.links = []
        self.generator = False
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in LOAD_ATTRS and REMOTE.match(a.get(LOAD_ATTRS[tag]) or ""):
            self.loads.append(f"<{tag} {LOAD_ATTRS[tag]}={a[LOAD_ATTRS[tag]]}>")
        if tag == "link" and REMOTE.match(a.get("href") or ""):
            self.loads.append(f"<link href={a['href']}>")
        if tag == "a" and REMOTE.match(a.get("href") or ""):
            self.links.append(a["href"])
        if tag == "meta" and (a.get("name") or "").lower() == "generator":
            self.generator = True
        style = a.get("style") or ""
        if re.search(r"url\(\s*[\"']?(?:https?:)?//", style, re.IGNORECASE):
            self.loads.append(f"<{tag} style=...url(...)>")

    def handle_data(self, data):
        self.text.append(data)

    def handle_comment(self, data):
        self.text.append(data)


def scan(body):
    s = Scan()
    s.feed(body)
    s.close()
    return s


def body_problems(body):
    s = scan(body)
    problems = [f"loads something from another host: {x}" for x in s.loads]
    if re.search(r"@import|url\(\s*[\"']?(?:https?:)?//", " ".join(s.text), re.IGNORECASE):
        problems.append("a style block pulls something from another host")
    if s.generator:
        problems.append("a generator meta tag names the software that made the page")
    for ip in sorted(set(IPV4.findall(" ".join(s.text)))):
        problems.append(f"an IP address is written into the page text: {ip}")
    return problems


def outbound_links(body):
    return scan(body).links


def exposed_paths(results):
    """Paths whose status is 2xx or 3xx: the page answers, or redirects somewhere (a redirect still tells a visitor the path exists)."""
    return sorted(path for path, status in results.items() if 200 <= status < 400 and path != "/")


def fetch(host, port, path):
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request("GET", path, headers={"Host": "lab.example.test", "User-Agent": "check_origin"})
        resp = conn.getresponse()
        return resp.status, resp.getheaders(), resp.read(200_000).decode("utf-8", "replace")
    finally:
        conn.close()


def read_ss(ss_file):
    if ss_file:
        with open(ss_file, encoding="utf-8") as handle:
            return handle.read()
    return subprocess.run(["ss", "-ltnH"], capture_output=True, text=True, check=True, timeout=10).stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ss-file", help="read `ss -ltnH` output from this file instead of running it (for tests)")
    args = parser.parse_args(argv)
    try:
        if not ipaddress.ip_address(args.host).is_loopback:
            raise ValueError
    except ValueError:
        print(f"check_origin: refusing {args.host}: this audit talks to a loopback address only")
        return 2
    problems = []
    print(f"check_origin: {args.host}:{args.port}")
    try:
        ss_text = read_ss(args.ss_file)
    except (OSError, subprocess.SubprocessError) as err:
        print(f"check_origin: could not read the listening ports: {err}")
        return 2
    problems += origin_exposure(ss_text, args.port)
    for line in wildcard_listeners(ss_text):
        print(f"[REVIEW] something listens on every interface: {line} (is it supposed to?)")
    try:
        status, headers, body = fetch(args.host, args.port, "/")
        problems += header_problems(headers)
        problems += body_problems(body)
        for link in outbound_links(body):
            print(f"[REVIEW] the page links out to {link} (a click sends a referrer and ends the session's cover)")
        _, miss_headers, _ = fetch(args.host, args.port, "/no-such-page")
        probes = {path: fetch(args.host, args.port, path) for path in PROBE_PATHS}
    except OSError as err:
        print(f"check_origin: could not reach the origin: {err}")
        return 2
    responses = [headers, miss_headers] + [probe[1] for probe in probes.values()]
    problems += [p for p in dict.fromkeys(q for h in responses[1:] for q in header_problems(h)) if p not in problems]
    reviews = list(dict.fromkeys(line for h in responses for line in server_review(h)))
    results = {path: probe[0] for path, probe in probes.items()}
    problems += [f"the path {p} answers {results[p]}" for p in exposed_paths(results)]
    if status != 200:
        problems.append(f"the front page answered {status}, not 200")
    for line in reviews:
        print(f"[REVIEW] {line} (no version, so not a failure; hide it if your server can)")
    for p in problems:
        print(f"[FAIL] {p}")
    print(f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
