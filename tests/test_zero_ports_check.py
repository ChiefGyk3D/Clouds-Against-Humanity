"""scripts/zero_ports_check.py: the external zero-open-ports check.

Hermetic. Nothing here reaches a real network target: an autouse guard fails any
socket call that is not loopback, the API is either a fake object or a local
HTTP server on an ephemeral loopback port (so urllib's real redirect and proxy
machinery runs), and the port accounting uses an injected connect function with
a fake clock. Real sockets are opened only against loopback and only for a
handful of ports.
"""

from __future__ import annotations

import ast
import concurrent.futures
import contextlib
import errno
import io
import ipaddress
import itertools
import json
import os
import socket
import stat
import subprocess
import sys
import threading
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "zero_ports_check.py"
sys.path.insert(0, str(ROOT / "scripts"))
import zero_ports_check as zpc

# Built at run time so no secret-shaped literal sits in the file (gitleaks scans it).
CRED = "-".join(("tok", "SECRET", "MARKER", "0123456789"))  # noqa: FLY002 - keep it out of the source text
A = "198.51.100.10"  # documentation range (TEST-NET-2): never a real address
B = "198.51.100.11"
RESERVED = "198.51.100.50"
PROJ = "proj-1"
U1 = "198.51.100.11"  # first address units() builds
TESTNET2 = ipaddress.ip_network("198.51.100.0/24")


def OK(addr: ipaddress.IPv4Address) -> bool:
    """The real predicate, plus the documentation range the fixtures use."""
    return zpc.default_address_ok(addr) or addr in TESTNET2


# ------------------------------------------------------------------ guards


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def check(address):
        host = address[0] if isinstance(address, tuple) else address
        if host != "127.0.0.1":
            raise AssertionError("a test tried to reach a non-loopback address")

    def connect(self, address):
        check(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        check(address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if host not in ("127.0.0.1", "localhost", None):
            raise AssertionError("a test tried to resolve a non-loopback name")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    for name in ("DIGITALOCEAN_TOKEN", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
                 "no_proxy", "NO_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)


# ------------------------------------------------------------------ fakes


BASELINE_TAG = "cah-baseline-tor1"
_NO_TAGS = object()


def droplet(did: int, ip: str | object = A, *, v6=(), v4_extra=(), tags: object = None) -> dict:
    v4 = [{"ip_address": "10.116.0.2", "type": "private"}]
    if ip is not None:
        v4.append({"ip_address": ip, "type": "public"})
    v4.extend(v4_extra)
    out = {"id": did, "networks": {"v4": v4, "v6": list(v6)}}
    if tags is not _NO_TAGS:
        out["tags"] = [BASELINE_TAG, "other"] if tags is None else tags
    return out


class FakeAPI:
    """The DigitalOcean listings the script reads, with knobs for the hostile cases."""

    def __init__(self, *, tagged=None, project_droplets=None, projects=None,
                 reserved4=(), reserved6=(), page_size=200, tag=BASELINE_TAG):
        self.tag = tag
        self.tagged = [droplet(1001, A), droplet(1002, B)] if tagged is None else tagged
        ids = [d["id"] for d in self.tagged] if project_droplets is None else project_droplets
        self.projects = [{"id": PROJ, "name": zpc.PROJECT_NAME}] if projects is None else projects
        self.resources = [{"urn": f"do:droplet:{i}"} for i in ids] + [{"urn": "do:volume:abc"}]
        self.reserved4 = list(reserved4)
        self.reserved6 = list(reserved6)
        self.page_size = page_size
        self.total_override = None
        self.cycle = False
        self.endless = False
        self.calls: list[tuple[str, dict]] = []

    def _list(self, key, items, params, total=None):
        page = int(params["page"])
        if self.cycle:
            page = 1
        size = self.page_size
        chunk = items[(page - 1) * size: page * size]
        more = page * size < len(items) or self.cycle
        data = {"meta": {"total": len(items) if total is None else total}, key: chunk,
                "links": {"pages": {"next": f"https://elsewhere.invalid/x?page={page + 1}"} if more else {}}}
        if self.total_override is not None:
            data["meta"]["total"] = self.total_override
        return data

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        if path == "/v2/projects":
            return self._list("projects", self.projects, params)
        if path.startswith("/v2/projects/") and path.endswith("/resources"):
            return self._list("resources", self.resources, params)
        if path == "/v2/droplets":
            assert params["tag_name"] == self.tag
            if self.endless:
                page = int(params["page"])
                return {"droplets": [droplet(50000 + page, A)], "meta": {"total": 10**6},
                        "links": {"pages": {"next": "x"}}}
            return self._list("droplets", self.tagged, params)
        if path == "/v2/reserved_ips":
            return self._list("reserved_ips", self.reserved4, params)
        if path == "/v2/reserved_ipv6":
            return self._list("reserved_ipv6s", self.reserved6, params)
        raise AssertionError(f"unexpected path {path}")


class InlineExecutor:
    """Runs each task at submit time: deterministic for the fake-clock tests."""

    def __init__(self, max_workers=None):
        pass

    def submit(self, fn, *args):
        fut = concurrent.futures.Future()
        try:
            fut.set_result(fn(*args))
        except (RuntimeError, OSError, ValueError) as exc:  # mimic a worker failure
            fut.set_exception(exc)
        return fut

    def shutdown(self, wait=True, cancel_futures=False):
        pass


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, d):
        self.t += d


class Counters:
    """Counts every connect, scan or control. Zero after any discovery failure."""

    def __init__(self, outcome=zpc.TIMEOUT):
        self.scan = 0
        self.control = 0
        self.outcome = outcome
        self.calls = []

    def connect(self, address, port, timeout):
        self.scan += 1
        self.calls.append((address, port))
        return self.outcome(address, port) if callable(self.outcome) else self.outcome

    def control_connect(self, host, port, timeout):
        self.control += 1


def units(n=2) -> zpc.Inventory:
    return zpc.Inventory(tuple(
        zpc.Unit(f"connector-{i}", f"198.51.100.{10 + i}", 1000 + i) for i in range(1, n + 1)))


def run_main(api, expected=2, *, argv=(), counters=None, token=CRED, env=None, **hook_kw):
    counters = counters or Counters()
    kw = {
        "address_ok": OK,
        "connect": counters.connect,
        "control_connect": counters.control_connect,
        "transport_factory": lambda t: api,
        "ports": range(1, 4),
        "budget": zpc.Budget(concurrency=4, rate=1e9, batch=4096),
        "executor_factory": InlineExecutor,
        "sleep": lambda d: None,
    }
    kw.update(hook_kw)
    out = io.StringIO()
    environment = {"DIGITALOCEAN_TOKEN": token} if env is None else env
    code = zpc.main(["--expect-connectors", str(expected), *argv], env=environment,
                    hooks=zpc.Hooks(**kw), stdout=out)
    return code, out.getvalue(), counters


# ------------------------------------------------------------------ discovery


def test_discovery_happy_path_labels_and_calls():
    api = FakeAPI()
    inv = zpc.discover(api, 2, "tor1", OK)
    assert inv.labels == ("connector-1", "connector-2")
    assert [u.address for u in inv.units] == [A, B]
    paths = {p for p, _ in api.calls}
    assert paths == {"/v2/projects", f"/v2/projects/{PROJ}/resources", "/v2/droplets",
                     "/v2/reserved_ips", "/v2/reserved_ipv6"}
    assert A not in repr(inv) and B not in repr(inv)


def test_tagged_droplet_outside_project_is_ignored_not_scanned():
    api = FakeAPI(tagged=[droplet(1001, A), droplet(1002, B), droplet(1003, "198.51.100.99")],
                  project_droplets=[1001, 1002])
    inv = zpc.discover(api, 2, "tor1", OK)
    assert {u.droplet_id for u in inv.units} == {1001, 1002}
    assert "198.51.100.99" not in {u.address for u in inv.units}


def test_reserved_ip_attached_to_target_is_one_more_target():
    api = FakeAPI(reserved4=[{"ip": RESERVED, "droplet": {"id": 1001}},
                             {"ip": "198.51.100.77", "droplet": None},
                             {"ip": "198.51.100.78", "droplet": {"id": 4242}}])
    inv = zpc.discover(api, 2, "tor1", OK)
    assert [u.label for u in inv.units] == ["connector-1", "connector-1-extra-1", "connector-2"]
    assert RESERVED in {u.address for u in inv.units}
    assert "198.51.100.77" not in {u.address for u in inv.units}


def _bad(**kw):
    return FakeAPI(**kw)


def _ip_case(value):
    return lambda: FakeAPI(tagged=[droplet(1001, value), droplet(1002, B)])


def _mapped():
    return _ip_case("::ffff:198.51.100.10")()


DISCOVERY_FAILURES = {
    "pagination-cycle": lambda: _cycle(),
    "repeated-item": lambda: FakeAPI(tagged=[droplet(1001, A), droplet(1001, B)], project_droplets=[1001]),
    "total-contradicts-pages": lambda: _total(),
    "empty-inventory": lambda: FakeAPI(tagged=[], project_droplets=[]),
    "fewer-than-expected": lambda: FakeAPI(tagged=[droplet(1001, A)]),
    "page-cap-hit": lambda: _endless(),
    "non-string-address": _ip_case(None),
    "integer-address": _ip_case(3325256714),
    "float-address": _ip_case(1.5),
    "list-address": _ip_case([A]),
    "ipv4-mapped-ipv6": _mapped,
    "decimal-spelling": _ip_case("3325256714"),
    "octal-spelling": _ip_case("0306.0063.0144.012"),
    "leading-zero": _ip_case("198.051.100.10"),
    "hex-spelling": _ip_case("0xc6.0x33.0x64.0x0a"),
    "trailing-space": _ip_case(A + " "),
    "trailing-newline": _ip_case(A + "\n"),
    "trailing-prefix": _ip_case(A + "/32"),
    "three-octets": _ip_case("198.51.100"),
    "private": _ip_case("10.1.2.3"),
    "loopback": _ip_case("127.0.0.1"),
    "link-local": _ip_case("169.254.1.1"),
    "multicast": _ip_case("224.0.0.1"),
    "reserved-range": _ip_case("240.0.0.1"),
    "cgnat": _ip_case("100.64.0.1"),
    "no-public-address": lambda: FakeAPI(tagged=[droplet(1001, None), droplet(1002, B)]),
    "public-ipv6-on-droplet": lambda: FakeAPI(tagged=[
        droplet(1001, A, v6=[{"ip_address": "2001:db8::1", "type": "public"}]), droplet(1002, B)]),
    "malformed-ipv6-entry": lambda: FakeAPI(tagged=[droplet(1001, A, v6=["x"]), droplet(1002, B)]),
    "project-droplet-without-tag": lambda: FakeAPI(project_droplets=[1001, 1002, 1999]),
    "project-missing": lambda: FakeAPI(projects=[{"id": "p", "name": "other"}]),
    "project-duplicated": lambda: FakeAPI(projects=[{"id": "p1", "name": zpc.PROJECT_NAME},
                                                     {"id": "p2", "name": zpc.PROJECT_NAME}]),
    "project-id-malformed": lambda: FakeAPI(projects=[{"id": "../x", "name": zpc.PROJECT_NAME}]),
    "reserved-ipv6-on-target": lambda: FakeAPI(reserved6=[{"ip": "2001:db8::5", "droplet": {"id": 1001}}]),
    "reserved-ip-private": lambda: FakeAPI(reserved4=[{"ip": "10.0.0.9", "droplet": {"id": 1001}}]),
    "reserved-malformed-assignment": lambda: FakeAPI(reserved4=[{"ip": RESERVED, "droplet": "1001"}]),
    "bool-droplet-id": lambda: FakeAPI(tagged=[droplet(True, A), droplet(1002, B)], project_droplets=[1, 1002]),
    "duplicate-address": lambda: FakeAPI(tagged=[droplet(1001, A), droplet(1002, A)]),
}


def _cycle():
    api = FakeAPI(page_size=1)
    api.cycle = True
    return api


def _total():
    api = FakeAPI()
    api.total_override = 5
    return api


def _endless():
    api = FakeAPI()
    api.endless = True
    return api


@pytest.mark.parametrize("name", sorted(DISCOVERY_FAILURES))
def test_every_discovery_failure_is_exit_2_with_zero_connects(name):
    api = DISCOVERY_FAILURES[name]()
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 2, "tor1", OK)
    counters = Counters()
    code, out, _ = run_main(DISCOVERY_FAILURES[name](), counters=counters)
    assert code == 2, out
    assert counters.scan == 0 and counters.control == 0
    assert "PASS" not in out
    for secret in (A, B, CRED):
        assert secret not in out


def test_endless_listing_stops_at_the_page_cap():
    api = _endless()
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 2, "tor1", OK)
    assert len([c for c in api.calls if c[0] == "/v2/droplets"]) == zpc.MAX_PAGES


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "2", None])
def test_expected_must_be_a_positive_int(bad):
    with pytest.raises(zpc.CheckError):
        zpc.discover(FakeAPI(), bad, "tor1", OK)


@pytest.mark.parametrize("region", ["", "TOR1", "tor1/../x", "tor 1", "a" * 40, "t\n"])
def test_region_is_validated_before_any_request(region):
    api = FakeAPI()
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 2, region, OK)
    assert api.calls == []


def test_default_address_predicate_is_global_only():
    for text in ("198.51.100.10", "203.0.113.1", "10.0.0.1", "127.0.0.1", "169.254.0.1", "224.0.0.1"):
        assert zpc.default_address_ok(ipaddress.IPv4Address(text)) is False


# ----------------------------------------------- discovery over real urllib


class Site:
    """A loopback HTTP server whose answers come from `route(handler) -> (status, headers, body)`."""

    def __init__(self, route):
        self.hits: list[dict] = []
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # http.server API name
                site.hits.append({"path": self.path, "auth": self.headers.get("Authorization")})
                status, headers, body = route(self)
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


@pytest.fixture
def make_site():
    sites = []

    def make(route):
        site = Site(route)
        sites.append(site)
        return site

    yield make
    for site in sites:
        site.close()


def json_route(api):
    def route(handler):
        parts = urllib.parse.urlsplit(handler.path)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query).items()}
        return 200, {"Content-Type": "application/json"}, json.dumps(api.get(parts.path, params)).encode()
    return route


def test_real_urllib_happy_path_sends_bearer_to_the_fixed_origin_only(make_site):
    api = FakeAPI(page_size=1)  # forces pagination; the "next" URLs point at elsewhere.invalid
    site = make_site(json_route(api))
    transport = zpc.ApiTransport(CRED, site.url)
    inv = zpc.discover(transport, 2, "tor1", OK)
    assert [u.address for u in inv.units] == [A, B]
    assert site.hits and all(h["auth"] == f"Bearer {CRED}" for h in site.hits)
    assert all(h["path"].startswith("/v2/") for h in site.hits)


def test_returned_next_url_is_never_followed(make_site):
    other = make_site(lambda h: (200, {}, b"{}"))
    api = FakeAPI(page_size=1)
    original = api._list

    def list_with_foreign_next(key, items, params, total=None):
        data = original(key, items, params, total)
        if data["links"]["pages"]:
            data["links"]["pages"]["next"] = other.url + "/v2/droplets?page=2"
        return data

    api._list = list_with_foreign_next
    site = make_site(json_route(api))
    zpc.discover(zpc.ApiTransport(CRED, site.url), 2, "tor1", OK)
    assert other.hits == []


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_is_refused_and_the_token_never_reaches_the_other_host(make_site, status):
    other = make_site(lambda h: (200, {}, b"{}"))
    first = make_site(lambda h: (status, {"Location": other.url + "/v2/projects"}, b""))
    with pytest.raises(zpc.CheckError) as info:
        zpc.discover(zpc.ApiTransport(CRED, first.url), 2, "tor1", OK)
    assert "redirect" in str(info.value)
    assert other.hits == [], "the redirect target was contacted"
    assert len(first.hits) == 1
    assert CRED not in str(info.value) and CRED not in repr(info.value)


def test_default_urllib_would_follow_the_redirect_so_the_test_above_bites(make_site):
    other = make_site(lambda h: (200, {"Content-Type": "application/json"}, b"{}"))
    first = make_site(lambda h: (302, {"Location": other.url + "/v2/projects"}, b""))
    with contextlib.closing(urllib.request.build_opener().open(first.url + "/v2/projects", timeout=5)):
        pass
    assert len(other.hits) == 1


def test_proxy_environment_is_ignored(make_site, monkeypatch):
    proxy = make_site(lambda h: (200, {}, b"{}"))
    site = make_site(json_route(FakeAPI()))
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, proxy.url)
    zpc.discover(zpc.ApiTransport(CRED, site.url), 2, "tor1", OK)
    assert proxy.hits == []
    assert site.hits


def test_proxy_control_default_urllib_does_use_the_proxy(make_site, monkeypatch):
    proxy = make_site(lambda h: (200, {"Content-Type": "application/json"}, b"{}"))
    site = make_site(lambda h: (200, {}, b"{}"))
    monkeypatch.setenv("http_proxy", proxy.url)
    with contextlib.closing(urllib.request.build_opener().open(site.url + "/v2/projects", timeout=5)):
        pass
    assert proxy.hits, "without ProxyHandler({}) the proxy variable would redirect the token"


@pytest.mark.parametrize("body", [
    b"not json", b"[]", b"3", b'{"a": 1, "a": 2}', b'{"meta": NaN}', b"\xff\xfe", b"[" * 100000,
    b"",
])
def test_bad_bodies_are_one_typed_error(make_site, body):
    site = make_site(lambda h: (200, {}, body))
    with pytest.raises(zpc.CheckError):
        zpc.discover(zpc.ApiTransport(CRED, site.url), 2, "tor1", OK)


def test_oversized_body_is_refused(make_site):
    site = make_site(lambda h: (200, {}, b'{"projects": [], "pad": "' + b"x" * 5000 + b'"}'))
    transport = zpc.ApiTransport(CRED, site.url, max_body=1000)
    with pytest.raises(zpc.CheckError, match="larger"):
        transport.get("/v2/projects", {})


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_error_statuses_are_fixed_messages_without_the_body(make_site, status):
    site = make_site(lambda h: (status, {}, b"leaky-body-" + CRED.encode()))
    with pytest.raises(zpc.CheckError) as info:
        zpc.discover(zpc.ApiTransport(CRED, site.url), 2, "tor1", OK)
    assert "leaky" not in str(info.value) and CRED not in str(info.value)
    assert len(site.hits) == 1, "a read is not retried here: the run is simply cannot-tell"


def test_connection_failure_is_a_typed_error():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # nothing listens here now
    with pytest.raises(zpc.CheckError):
        zpc.ApiTransport(CRED, f"http://127.0.0.1:{port}").get("/v2/projects", {})


@pytest.mark.parametrize("base", ["http://example.invalid", "https://evil.example", "http://127.0.0.1.evil.example",
                                  "ftp://127.0.0.1", "http://localhost:80"])
def test_a_non_default_origin_is_refused_unless_loopback_http(base):
    with pytest.raises(zpc.CheckError):
        zpc.ApiTransport(CRED, base)


@pytest.mark.parametrize("token", ["", "short", "has space in it 123", "line\nbreak12345", "x" * 300, None, 5])
def test_malformed_token_is_refused(token):
    with pytest.raises(zpc.CheckError):
        zpc.ApiTransport(token, "http://127.0.0.1:1")


# ------------------------------------------------------------------- scanning


def full_scan(counters, n_units=2, *, ports=range(1, zpc.MAX_PORT + 1), batch=4096, reread=None):
    inv = units(n_units)
    clock = Clock()
    rereads = []

    def default_reread():
        rereads.append(1)
        return inv

    acc = zpc.scan(inv, counters.connect, zpc.Budget(batch=batch), reread=reread or default_reread,
                   clock=clock, sleep=clock.sleep, executor_factory=InlineExecutor, ports=ports)
    return inv, acc, rereads, clock


def test_full_sweep_accounts_for_every_port_exactly_once_and_passes():
    counters = Counters()
    _inv, acc, rereads, clock = full_scan(counters)
    assert counters.scan == 2 * zpc.MAX_PORT
    assert len(set(counters.calls)) == 2 * zpc.MAX_PORT, "an attempt was repeated"
    assert {p for a, p in counters.calls if a == U1} == set(range(1, 65536))
    assert acc.unique == [zpc.MAX_PORT, zpc.MAX_PORT] and acc.duplicates == 0
    result = zpc.verdict(acc, 2)
    assert result.code == 0 and result.reasons == ()
    assert len(rereads) == -(-2 * zpc.MAX_PORT // 4096), "re-read after each batch, including the last"
    assert clock.t > 80, "the 1,500/s cap was applied on the (fake) clock"


def test_loopback_listener_is_found_open_and_bound_but_not_listening_is_refused():
    open_sock = socket.socket()
    open_sock.bind(("127.0.0.1", 0))
    open_sock.listen(4)
    refused_sock = socket.socket()
    refused_sock.bind(("127.0.0.1", 0))  # bound, never listening: stays bound, no port-reuse race
    try:
        open_port = open_sock.getsockname()[1]
        refused_port = refused_sock.getsockname()[1]
        inv = zpc.Inventory((zpc.Unit("connector-1", "127.0.0.1", 1),))
        acc = zpc.scan(inv, zpc.tcp_connect, zpc.Budget(concurrency=4, rate=1e6, timeout=2.0),
                       reread=lambda: inv, ports=sorted([open_port, refused_port]))
    finally:
        open_sock.close()
        refused_sock.close()
    assert acc.open_ports == [[open_port]]
    assert acc.refused_ports == [[refused_port]]
    result = zpc.verdict(acc, 1, 2)
    assert result.code == 1
    assert any("an answer was received" in r for r in result.reasons)


def test_refusal_alone_fails_the_silence_criterion():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, 100):
        acc.record(0, port, zpc.TIMEOUT)
    acc.record(0, 100, zpc.REFUSED)
    result = zpc.verdict(acc, 1, 100)
    assert result.code == 1
    assert "refusal" in " ".join(result.reasons)


def test_all_timeouts_are_exit_0_only_when_complete():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, 11):
        acc.record(0, port, zpc.TIMEOUT)
    assert zpc.verdict(acc, 1, 10).code == 0
    assert zpc.verdict(acc, 1, 11).code == 2  # one port short of what was promised
    assert zpc.verdict(acc, 2, 10).code == 2  # one connector fewer than expected


def test_missing_final_port_is_exit_2():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, zpc.MAX_PORT):
        acc.record(0, port, zpc.TIMEOUT)
    assert zpc.verdict(acc, 1).code == 2


def test_duplicated_port_is_exit_2():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, 11):
        acc.record(0, port, zpc.TIMEOUT)
    acc.record(0, 5, zpc.TIMEOUT)
    assert acc.duplicates == 1
    assert zpc.verdict(acc, 1, 10).code == 2


def test_out_of_range_port_is_exit_2():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, 11):
        acc.record(0, port, zpc.TIMEOUT)
    acc.record(0, 0, zpc.TIMEOUT)
    acc.record(0, 70000, zpc.TIMEOUT)
    assert zpc.verdict(acc, 1, 10).code == 2


@pytest.mark.parametrize("outcome", [zpc.LOCAL, zpc.UNREACHABLE, zpc.ERROR])
def test_error_classes_are_exit_2_and_never_counted_as_timeouts(outcome):
    counters = Counters(outcome=lambda a, p: outcome if (a, p) == (U1, 2) else zpc.TIMEOUT)
    _inv, acc, _, _ = full_scan(counters, 2, ports=range(1, 5))
    assert acc.counts[0][zpc.TIMEOUT] == 3 and acc.counts[0][outcome] == 1
    assert zpc.verdict(acc, 2, 4).code == 2


def test_answer_plus_error_exits_1_and_lists_both():
    def outcome(a, p):
        return {1: zpc.OPEN, 2: zpc.LOCAL}.get(p, zpc.TIMEOUT)

    _, acc, _, _ = full_scan(Counters(outcome=outcome), 1, ports=range(1, 5))
    result = zpc.verdict(acc, 1, 4)
    assert result.code == 1
    text = " ".join(result.reasons)
    assert "accepted a connection" in text and "local resource error" in text


def test_worker_failure_is_an_error_not_a_timeout():
    def explode(address, port, timeout):
        raise RuntimeError("boom")

    inv = units(1)
    acc = zpc.scan(inv, explode, zpc.Budget(), reread=lambda: inv, executor_factory=InlineExecutor,
                   sleep=lambda d: None, ports=range(1, 4))
    assert acc.counts[0][zpc.ERROR] == 3 and acc.counts[0][zpc.TIMEOUT] == 0
    assert zpc.verdict(acc, 1, 3).code == 2


def test_bogus_outcome_from_connect_is_an_error():
    inv = units(1)
    acc = zpc.scan(inv, lambda a, p, t: "weird", zpc.Budget(), reread=lambda: inv,
                   executor_factory=InlineExecutor, sleep=lambda d: None, ports=range(1, 4))
    assert acc.counts[0][zpc.ERROR] == 3


def test_a_worker_that_cannot_start_is_a_local_error():
    class NoThreads(InlineExecutor):
        def submit(self, fn, *args):
            raise RuntimeError("can't start new thread")

    inv = units(1)
    acc = zpc.scan(inv, lambda a, p, t: zpc.TIMEOUT, zpc.Budget(), reread=lambda: inv,
                   executor_factory=NoThreads, sleep=lambda d: None, ports=range(1, 4))
    assert acc.counts[0][zpc.LOCAL] == 3
    assert zpc.verdict(acc, 1, 3).code == 2


@pytest.mark.parametrize("code, expected", [
    (errno.ECONNREFUSED, zpc.REFUSED), (errno.ECONNRESET, zpc.REFUSED),
    (errno.ETIMEDOUT, zpc.TIMEOUT),
    (errno.ENETUNREACH, zpc.UNREACHABLE), (errno.EHOSTUNREACH, zpc.UNREACHABLE),
    (errno.EMFILE, zpc.LOCAL), (errno.ENFILE, zpc.LOCAL), (errno.EADDRNOTAVAIL, zpc.LOCAL),
    (errno.ENOBUFS, zpc.LOCAL), (errno.ENOMEM, zpc.LOCAL),
    (errno.EACCES, zpc.ERROR), (None, zpc.ERROR), (errno.EPERM, zpc.ERROR),
])
def test_errno_classification(code, expected):
    assert zpc.classify_errno(code) == expected


class FakeSocket:
    created = 0
    closed = 0

    def __init__(self, behaviour):
        self.behaviour = behaviour
        type(self).created += 1

    def settimeout(self, t):
        if self.behaviour == "settimeout-fails":
            raise OSError(errno.EBADF, "x")

    def connect(self, address):
        b = self.behaviour
        if b == "ok":
            return
        if b == "timeout":
            raise TimeoutError()
        if isinstance(b, int):
            raise OSError(b, "x")

    def close(self):
        type(self).closed += 1


@pytest.mark.parametrize("behaviour, expected", [
    ("ok", zpc.OPEN), ("timeout", zpc.TIMEOUT), (errno.ECONNREFUSED, zpc.REFUSED),
    (errno.EMFILE, zpc.LOCAL), (errno.EADDRNOTAVAIL, zpc.LOCAL), (errno.ENOBUFS, zpc.LOCAL),
    (errno.ENETUNREACH, zpc.UNREACHABLE), ("settimeout-fails", zpc.LOCAL),
])
def test_sockets_are_closed_on_every_path(behaviour, expected):
    FakeSocket.created = FakeSocket.closed = 0
    result = zpc.tcp_connect("192.0.2.1", 80, 1.0, socket_factory=lambda *a: FakeSocket(behaviour))
    assert result == expected
    assert FakeSocket.created == 1 and FakeSocket.closed == 1


def test_socket_creation_failure_is_a_local_error_with_nothing_to_close():
    def factory(*args):
        raise OSError(errno.EMFILE, "too many open files")

    assert zpc.tcp_connect("192.0.2.1", 80, 1.0, socket_factory=factory) == zpc.LOCAL


def test_peak_concurrency_never_exceeds_the_budget():
    lock = threading.Lock()
    state = {"now": 0, "peak": 0}

    def connect(address, port, timeout):
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
        threading.Event().wait(0.002)
        with lock:
            state["now"] -= 1
        return zpc.TIMEOUT

    inv = units(1)
    acc = zpc.scan(inv, connect, zpc.Budget(concurrency=8, rate=1e7, batch=300), reread=lambda: inv,
                   ports=range(1, 1201))
    assert acc.unique == [1200]
    assert 2 <= state["peak"] <= 8


def test_attempt_rate_never_exceeds_the_cap_on_a_fake_clock():
    clock = Clock()
    stamps = []

    def connect(address, port, timeout):
        stamps.append(clock())
        return zpc.TIMEOUT

    inv = units(1)
    zpc.scan(inv, connect, zpc.Budget(rate=100.0, concurrency=4, batch=250), reread=lambda: inv,
             clock=clock, sleep=clock.sleep, executor_factory=InlineExecutor, ports=range(1, 1001))
    assert len(stamps) == 1000
    worst = 0
    left = 0
    for right, t in enumerate(stamps):
        while t - stamps[left] >= 1.0 - 1e-9:
            left += 1
        worst = max(worst, right - left + 1)
    assert worst <= 100, f"{worst} attempts started inside one second"
    assert stamps[-1] - stamps[0] >= 9.9


def test_inventory_change_between_batches_discards_the_results():
    inv = units(2)
    changed = zpc.Inventory(inv.units[:1] + (zpc.Unit("connector-2", "198.51.100.99", 1002),))
    calls = []

    def reread():
        calls.append(1)
        return inv if len(calls) < 2 else changed

    counters = Counters()
    clock = Clock()
    with pytest.raises(zpc.InventoryChanged):
        zpc.scan(inv, counters.connect, zpc.Budget(batch=10), reread=reread, clock=clock,
                 sleep=clock.sleep, executor_factory=InlineExecutor, ports=range(1, 100))
    assert counters.scan == 20, "the sweep stopped after the batch that saw the change"


def test_inventory_change_is_exit_2_and_prints_no_results():
    api = FakeAPI()
    state = {"n": 0}
    original = api.get

    def flapping(path, params):
        data = original(path, params)
        if path == "/v2/droplets":
            state["n"] += 1
            if state["n"] > 1:  # the first call is discovery; the next is the first re-read
                data = json.loads(json.dumps(data))
                data["droplets"][0]["networks"]["v4"][1]["ip_address"] = "198.51.100.77"
        return data

    api.get = flapping
    code, out, counters = run_main(api)
    assert code == 2
    assert "results discarded" in out and "PASS" not in out and "attempted" not in out
    assert counters.scan == 6


def test_inventory_change_at_the_final_reread_is_detected():
    inv = units(1)
    calls = []

    def reread():
        calls.append(1)
        return inv if len(calls) < 1 else units(1).__class__(())

    with pytest.raises(zpc.InventoryChanged):
        zpc.scan(inv, lambda a, p, t: zpc.TIMEOUT, zpc.Budget(batch=4096), reread=reread,
                 executor_factory=InlineExecutor, sleep=lambda d: None, ports=range(1, 4))
    assert len(calls) == 1


def test_discovery_failure_during_a_reread_is_exit_2():
    api = FakeAPI()
    state = {"n": 0}
    original = api.get

    def failing(path, params):
        if path == "/v2/projects":
            state["n"] += 1
            if state["n"] > 1:
                raise zpc.CheckError("the API could not be reached or the connection failed")
        return original(path, params)

    api.get = failing
    code, out, _ = run_main(api)
    assert code == 2 and "PASS" not in out


def test_interrupt_is_exit_2_and_discards_results():
    def interrupted(delay):
        raise KeyboardInterrupt

    code, out, _ = run_main(FakeAPI(), budget=zpc.Budget(concurrency=4, rate=1.0, batch=4096),
                            sleep=interrupted)
    assert code == 2 and "interrupted" in out and "PASS" not in out and "attempted" not in out


def test_low_file_limit_is_cannot_tell_before_any_request():
    api = FakeAPI()
    code, out, counters = run_main(api, getrlimit=lambda which: (100, 4096), budget=zpc.Budget(concurrency=512))
    assert code == 2 and "open-file limit" in out
    assert api.calls == [] and counters.scan == 0
    with pytest.raises(zpc.CheckError):
        zpc.check_nofile(512, lambda which: (512, 512))
    zpc.check_nofile(512, lambda which: (4096, 4096))


# ----------------------------------------------------------------- main, e2e


def test_main_pass_prints_only_labels_counts_and_fixed_strings():
    code, out, counters = run_main(FakeAPI())
    assert code == 0
    assert counters.control == 1 and counters.scan == 6
    assert "connector-1: attempted 3, timeouts 3, answers 0, errors 0" in out
    assert "TCP only; observed from this network only" in out
    assert "verdict: PASS" in out
    for secret in (A, B, CRED, "198.51.100", "1001"):
        assert secret not in out


def test_main_answer_is_exit_1_and_names_port_numbers_only():
    counters = Counters(outcome=lambda a, p: zpc.REFUSED if (a, p) == (A, 2) else zpc.TIMEOUT)
    code, out, _ = run_main(FakeAPI(), counters=counters)
    assert code == 1
    assert "connector-1: ports that answered with a refusal: 2" in out
    assert "an answer was received" in out
    assert A not in out


def test_main_real_threads_and_loopback_listener_end_to_end():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    try:
        port = listener.getsockname()[1]
        api = FakeAPI(tagged=[droplet(1001, "127.0.0.1")], project_droplets=[1001])

        def control(host, p, timeout):
            with socket.create_connection(("127.0.0.1", port), timeout):
                pass

        out = io.StringIO()
        code = zpc.main(
            ["--expect-connectors", "1"], env={"DIGITALOCEAN_TOKEN": CRED}, stdout=out,
            hooks=zpc.Hooks(address_ok=lambda a: True, control_connect=control, ports=[port],
                            transport_factory=lambda t: api,
                            budget=zpc.Budget(concurrency=4, rate=1e6)))
    finally:
        listener.close()
    assert code == 1
    assert f"connector-1: open ports: {port}" in out.getvalue()


def test_positive_control_failure_is_cannot_tell_with_zero_scan_connects():
    def refuse(host, port, timeout):
        raise OSError(errno.ECONNREFUSED, "x")

    counters = Counters()
    code, out, _ = run_main(FakeAPI(), counters=counters, control_connect=refuse)
    assert code == 2 and "positive control" in out and counters.scan == 0


def test_missing_token_is_exit_2_before_any_request():
    api = FakeAPI()
    out = io.StringIO()
    code = zpc.main(["--expect-connectors", "2"], env={}, stdout=out,
                    hooks=zpc.Hooks(address_ok=OK, ports=range(1, 4)))
    assert code == 2 and "token" in out.getvalue()
    assert api.calls == []


def test_unreachable_target_network_is_exit_2():
    counters = Counters(outcome=zpc.UNREACHABLE)
    code, out, _ = run_main(FakeAPI(), counters=counters)
    assert code == 2 and "unreachable" in out


# ---------------------------------------------------------------- the token


def _every_path_output():
    outputs = []
    paths = [
        lambda: run_main(FakeAPI()),
        lambda: run_main(FakeAPI(), counters=Counters(outcome=zpc.OPEN)),
        lambda: run_main(FakeAPI(tagged=[])),
        lambda: run_main(FakeAPI(), counters=Counters(outcome=zpc.LOCAL)),
    ]
    for path in paths:
        outputs.append(path()[1])
    return outputs


def test_token_never_appears_in_any_output():
    for out in _every_path_output():
        assert CRED not in out


def test_token_never_appears_in_exception_text_repr_or_traceback(make_site):
    for status in (401, 500):
        site = make_site(lambda h, s=status: (s, {}, b"x"))
        transport = zpc.ApiTransport(CRED, site.url)
        with pytest.raises(zpc.CheckError) as info:
            transport.get("/v2/projects", {})
        blob = "".join(traceback.format_exception(info.value))
        for text in (str(info.value), repr(info.value), repr(info.value.args), blob):
            assert CRED not in text
        assert CRED not in repr(transport) and CRED not in repr(vars(transport))
    with pytest.raises(zpc.CheckError) as info:
        zpc.ApiTransport("bad token", "http://127.0.0.1:1")
    assert "bad token" not in str(info.value)


def test_token_is_not_in_the_report_and_no_child_process_exists(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a child process was started")

    monkeypatch.setattr(subprocess.Popen, "__init__", forbidden)
    for name in ("system", "fork", "execv", "execve", "posix_spawn", "popen"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, forbidden)
    before = dict(os.environ)
    report = tmp_path / "report.txt"
    code, _out, _ = run_main(FakeAPI(), argv=["--out", str(report)])
    assert code == 0
    assert CRED not in report.read_text() and A not in report.read_text()
    assert dict(os.environ) == before, "the script must not export the token or any variable"


def test_script_source_spawns_nothing_and_reads_only_the_token_variable():
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert not imported & {"subprocess", "pty", "multiprocessing", "ctypes", "shlex", "pickle"}
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"system", "popen", "fork", "execv", "execve", "execvp", "posix_spawn",
                        "spawnv", "putenv", "unsetenv", "getenv", "Popen"}
    environ_uses = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "environ"]
    assert len(environ_uses) == 1, "os.environ is read once, as the default for the env parameter"
    gets = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "env"]
    assert len(gets) == 1 and gets[0].args[0].id == "TOKEN_ENV"
    assert zpc.TOKEN_ENV == "DIGITALOCEAN_TOKEN"


# -------------------------------------------------- no way to give an address

FORBIDDEN_WORDS = {"host", "hosts", "hostname", "addr", "address", "addresses", "ip", "ips", "target",
                   "targets", "file", "files", "url", "uri", "cidr", "range", "input", "list", "domain",
                   "net", "network", "subnet", "from", "source", "inventory"}


def forbidden_options(parser):
    bad = []
    for action in parser._actions:
        for opt in action.option_strings:
            words = set(opt.lstrip("-").lower().split("-"))
            if words & FORBIDDEN_WORDS:
                bad.append(opt)
        if not action.option_strings and action.dest != "help":
            bad.append(action.dest)  # a positional
    return bad


def test_no_option_can_name_a_host_address_target_or_file():
    parser = zpc.build_parser()
    assert forbidden_options(parser) == []
    allowed = {"-h", "--help", "--expect-connectors", "--region", "--resource-key", "--out"}
    assert {o for a in parser._actions for o in a.option_strings} == allowed


def test_the_option_guard_bites():
    import argparse

    for name in ("--target", "--host", "--addresses", "--targets-file", "--ip", "--cidr", "--input-file"):
        parser = argparse.ArgumentParser()
        parser.add_argument(name)
        assert forbidden_options(parser) == [name]
    parser = argparse.ArgumentParser()
    parser.add_argument("where")
    assert forbidden_options(parser) == ["where"]


def test_a_positional_address_is_rejected_by_the_parser():
    counters = Counters()
    with pytest.raises(SystemExit) as info:
        zpc.main(["--expect-connectors", "1", "198.51.100.10"], env={"DIGITALOCEAN_TOKEN": CRED},
                 hooks=zpc.Hooks(), stdout=io.StringIO())
    assert info.value.code == 2 and counters.scan == 0


def test_other_environment_variables_cannot_supply_a_target():
    env = {"DIGITALOCEAN_TOKEN": CRED, "TARGET": "198.51.100.99", "TARGETS": "198.51.100.99",
           "HOST": "198.51.100.99", "ZERO_PORTS_TARGET": "198.51.100.99"}
    code, _out, counters = run_main(FakeAPI(), env=env)
    assert code == 0
    assert "198.51.100.99" not in {a for a, _ in counters.calls}


@pytest.mark.parametrize("flag", ["--target", "--host", "--address", "--file", "--ip"])
def test_unknown_address_like_flags_are_rejected(flag):
    with pytest.raises(SystemExit) as info:
        zpc.main(["--expect-connectors", "1", flag, "198.51.100.10"], env={}, stdout=io.StringIO())
    assert info.value.code == 2


def test_expect_connectors_is_required_and_at_least_one():
    with pytest.raises(SystemExit):
        zpc.main([], env={}, stdout=io.StringIO())
    code, _out, counters = run_main(FakeAPI(), expected=0)
    assert code == 2 and counters.scan == 0


def test_cli_without_a_token_exits_2_and_help_exits_0():
    env = {"PATH": os.environ.get("PATH", "")}
    run = subprocess.run([sys.executable, "-I", str(SCRIPT), "--expect-connectors", "1"],
                         capture_output=True, text=True, env=env, timeout=60, check=False)
    assert run.returncode == 2 and "token" in run.stdout
    helped = subprocess.run([sys.executable, "-I", str(SCRIPT), "--help"],
                            capture_output=True, text=True, env=env, timeout=60, check=False)
    assert helped.returncode == 0 and "--expect-connectors" in helped.stdout


# --------------------------------------------------------------------- report


def test_report_is_mode_0600_matches_the_console_and_is_not_overwritten(tmp_path):
    report = tmp_path / "r.txt"
    code, out, _ = run_main(FakeAPI(), argv=["--out", str(report)])
    assert code == 0
    assert stat.S_IMODE(report.stat().st_mode) == 0o600
    assert report.read_text() == out
    api = FakeAPI()
    code2, out2, counters = run_main(api, argv=["--out", str(report)])
    assert code2 == 2 and "not overwriting" in out2
    assert api.calls == [] and counters.scan == 0, "refused before any network use"
    assert report.read_text() == out, "the earlier report is untouched"


def test_report_inside_the_repository_is_refused(tmp_path, monkeypatch):
    # A stand-in repository under tmp_path: a failing guard must never write into the real tree.
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    inside = fake_repo / "zero-ports-report-test.txt"
    api = FakeAPI()
    code, out, _ = run_main(api, argv=["--out", str(inside)])
    assert code == 2 and "inside the repository" in out
    assert not inside.exists() and api.calls == []


def test_report_in_a_missing_directory_is_refused(tmp_path):
    code, _out, _ = run_main(FakeAPI(), argv=["--out", str(tmp_path / "nope" / "r.txt")])
    assert code == 2


def test_symlink_report_path_is_not_followed(tmp_path):
    target = tmp_path / "victim"
    link = tmp_path / "link"
    link.symlink_to(target)
    code, _out, _ = run_main(FakeAPI(), argv=["--out", str(link)])
    assert code == 2 and not target.exists()


def test_symlinked_parent_leading_outside_the_repo_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "linkdir").symlink_to(real)
    code, _out, _ = run_main(FakeAPI(), argv=["--out", str(tmp_path / "linkdir" / "r.txt")])
    assert code == 2 and not (real / "r.txt").exists()


def test_failure_to_write_the_report_is_exit_2(tmp_path, monkeypatch):
    def broken(path, lines):
        raise zpc.CheckError("the report could not be written")

    monkeypatch.setattr(zpc, "write_report", broken)
    code, out, _ = run_main(FakeAPI(), argv=["--out", str(tmp_path / "r.txt")])
    assert code == 2 and "report could not be written" in out and "PASS" not in out


def test_failure_to_write_never_hides_an_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(zpc, "write_report", lambda p, l: (_ for _ in ()).throw(zpc.CheckError("x")))
    code, out, _ = run_main(FakeAPI(), counters=Counters(outcome=zpc.OPEN),
                            argv=["--out", str(tmp_path / "r.txt")])
    assert code == 1 and "report could not be written" in out


def test_report_write_really_fails_on_a_read_only_directory(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        code, out, _ = run_main(FakeAPI(), argv=["--out", str(ro / "r.txt")])
    finally:
        ro.chmod(0o700)
    assert code == 2 and "PASS" not in out


# ----------------------------------------------------------------------- docs


def test_docs_give_the_full_command_with_doppler_and_the_limits():
    guide = (ROOT / "docs" / "stages" / "01-access.md").read_text()
    assert "doppler run -- python3 -I scripts/zero_ports_check.py --expect-connectors 2" in guide
    for phrase in ("second network", "UDP", "do not destroy", "exit 0", "exit 1", "exit 2"):
        assert phrase.lower() in guide.lower(), phrase
    wiki = (ROOT / "docs" / "wiki" / "Droplet-Hardening.md").read_text()
    assert "zero_ports_check" in wiki and "does not prove" in wiki.lower()
    for text in (guide, wiki):
        assert not any(tok in text for tok in ("DIGITALOCEAN_TOKEN=do", "dop_v1"))


# ===================================================================== fix round 1
# Finding 1: a TimeoutError outside the connect call is a setup failure, never a "no answer".


class FaultSocket:
    """A socket whose setup, connect or close raises on demand."""

    def __init__(self, fault):
        self.fault = fault
        self.closed = 0

    def settimeout(self, t):
        if self.fault == "settimeout":
            raise TimeoutError("setup failed")

    def connect(self, address):
        if self.fault == "close-after-open":
            return
        if self.fault == "close-after-refusal":
            raise ConnectionRefusedError(errno.ECONNREFUSED, "x")
        raise TimeoutError()  # a real connect timeout (the close then fails too)

    def close(self):
        self.closed += 1
        if self.fault.startswith("close-after") or self.fault == "close-after-timeout":
            raise TimeoutError("close failed")


def _factory_for(fault):
    if fault == "factory":
        def broken(*args):
            raise TimeoutError("socket setup failed")
        return broken
    return lambda *args: FaultSocket(fault)


SETUP_FAULTS = ["factory", "settimeout", "close-after-timeout"]
ANSWER_THEN_CLOSE_FAULTS = {
    "close-after-open": (zpc.OPEN_CLEANUP, zpc.OPEN),
    "close-after-refusal": (zpc.REFUSED_CLEANUP, zpc.REFUSED),
}


@pytest.mark.parametrize("fault", SETUP_FAULTS)
def test_timeouterror_outside_connect_is_a_local_error_not_a_timeout(fault):
    outcome = zpc.tcp_connect("198.51.100.1", 1, 2, socket_factory=_factory_for(fault))
    assert outcome == zpc.LOCAL


@pytest.mark.parametrize("fault", SETUP_FAULTS)
def test_setup_fault_on_every_port_is_exit_2_never_0(fault):
    inv = units(1)
    factory = _factory_for(fault)
    clock = Clock()
    acc = zpc.scan(
        inv, lambda a, p, t: zpc.tcp_connect(a, p, t, socket_factory=factory),
        zpc.Budget(), reread=lambda: inv, clock=clock, sleep=clock.sleep,
        executor_factory=InlineExecutor,
    )
    assert acc.unique == [zpc.MAX_PORT]
    assert acc.counts[0][zpc.TIMEOUT] == 0
    assert zpc.verdict(acc, 1).code == 2


@pytest.mark.parametrize("fault", sorted(ANSWER_THEN_CLOSE_FAULTS))
def test_a_close_failure_after_an_answer_keeps_the_answer(fault):
    tagged, base = ANSWER_THEN_CLOSE_FAULTS[fault]
    assert zpc.tcp_connect("198.51.100.1", 1, 2, socket_factory=_factory_for(fault)) == tagged
    inv = units(1)
    factory = _factory_for(fault)
    acc = zpc.scan(
        inv, lambda a, p, t: zpc.tcp_connect(a, p, t, socket_factory=factory),
        zpc.Budget(), reread=lambda: inv, executor_factory=InlineExecutor,
        sleep=lambda d: None, ports=range(1, 4),
    )
    assert acc.counts[0][base] == 3 and acc.counts[0][zpc.LOCAL] == 0
    assert acc.cleanup_problems == [3]
    result = zpc.verdict(acc, 1, 3)
    assert result.code == 1, "an answer plus an error stays exit 1"
    assert any("cleanup" in r for r in result.reasons)
    lines = zpc.render(acc, result, zpc.Budget(), 1, 1)
    assert any("cleanup problems: 3" in line for line in lines)


def test_a_close_failure_after_a_timeout_still_prevents_pass():
    acc = zpc.Accounting(("connector-1",))
    for port in range(1, 4):
        acc.record(0, port, zpc.LOCAL)
    assert zpc.verdict(acc, 1, 3).code == 2


def test_a_real_connect_timeout_is_still_a_timeout_and_the_socket_is_closed():
    sock = FaultSocket("timeout")
    sock.fault = "timeout"
    assert zpc.tcp_connect("198.51.100.1", 1, 2, socket_factory=lambda *a: sock) == zpc.TIMEOUT
    assert sock.closed == 1


# Finding 2: the token must not be reachable through exception chaining.


def exception_chain(exc):
    seen, stack, out = set(), [exc], []
    while stack:
        e = stack.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        out.append(e)
        stack.extend([e.__cause__, e.__context__])
    return out


def assert_chain_is_clean(exc, *secrets):
    chain = exception_chain(exc)
    assert chain
    for e in chain:
        for text in (str(e), repr(e), repr(e.args)):
            for secret in secrets:
                assert secret not in text, f"{type(e).__name__} carries a secret"
    assert exc.__cause__ is None and exc.__context__ is None, "a sanitised error keeps no chain"


@pytest.mark.parametrize("token", [CRED + "\n", CRED + " ", "\t" + CRED, CRED + "\r\n", CRED + "\x00"])
def test_token_with_whitespace_or_control_characters_is_refused_with_a_clean_chain(token):
    with pytest.raises(zpc.CheckError) as info:
        zpc.ApiTransport(token, "http://127.0.0.1:1")
    assert_chain_is_clean(info.value, CRED)


def test_urlerror_carrying_the_token_leaves_no_chain():
    class Opener:
        def open(self, req, timeout=None):
            raise urllib.error.URLError(CRED)

    transport = zpc.ApiTransport(CRED, "http://127.0.0.1:1")
    transport._opener = Opener()
    with pytest.raises(zpc.CheckError) as info:
        transport.get("/v2/projects", {})
    assert_chain_is_clean(info.value, CRED)


def test_valueerror_carrying_the_header_leaves_no_chain():
    class Opener:
        def open(self, req, timeout=None):
            raise ValueError("Invalid header value " + req.get_header("Authorization", "?"))

    transport = zpc.ApiTransport(CRED, "http://127.0.0.1:1")
    transport._opener = Opener()
    with pytest.raises(zpc.CheckError) as info:
        transport.get("/v2/projects", {})
    assert_chain_is_clean(info.value, CRED)


def test_http_error_with_a_body_leaves_no_chain(make_site):
    body = b"leaky-body-" + CRED.encode()
    for status in (302, 401, 500):
        site = make_site(lambda h, s=status: (s, {"Location": "http://127.0.0.1:1/x"}, body))
        with pytest.raises(zpc.CheckError) as info:
            zpc.ApiTransport(CRED, site.url).get("/v2/projects", {})
        assert_chain_is_clean(info.value, CRED, "leaky-body")


def test_json_parse_failure_with_token_like_text_leaves_no_chain(make_site):
    for body in (b'{"x": ' + CRED.encode() + b"}", b"\xff" + CRED.encode(), b'{"a":1,"a":2,"t":"' + CRED.encode() + b'"}'):
        site = make_site(lambda h, b=body: (200, {}, b))
        with pytest.raises(zpc.CheckError) as info:
            zpc.ApiTransport(CRED, site.url).get("/v2/projects", {})
        assert_chain_is_clean(info.value, CRED, "SECRET")


def test_connection_failure_leaves_no_chain():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    with pytest.raises(zpc.CheckError) as info:
        zpc.ApiTransport(CRED, f"http://127.0.0.1:{port}").get("/v2/projects", {})
    assert_chain_is_clean(info.value, CRED)


@pytest.mark.parametrize("value", ["999.1.1.1", "1.2.3", "not an ip", "::ffff:198.51.100.10"])
def test_address_parse_failure_leaves_no_chain(value):
    with pytest.raises(zpc.CheckError) as info:
        zpc.parse_public_ipv4(value, OK)
    assert_chain_is_clean(info.value, value)


def test_positive_control_failure_leaves_no_chain():
    def refuse(host, port, timeout):
        raise OSError(errno.ECONNREFUSED, "secret-detail")

    hooks = zpc.Hooks(control_connect=refuse)
    with pytest.raises(zpc.CheckError) as info:
        zpc.positive_control(hooks)
    assert_chain_is_clean(info.value, "secret-detail")


def test_report_write_failure_leaves_no_chain(tmp_path):
    target = zpc.check_out_path(str(tmp_path / "r.txt"))
    (tmp_path / "r.txt").write_text("already")
    try:
        with pytest.raises(zpc.CheckError) as info:
            zpc.write_report(target, ["x"])
    finally:
        zpc.close_report_target(target)
    assert_chain_is_clean(info.value, str(tmp_path))


@pytest.mark.parametrize("region", ["tor1\n", "tor1 ", " tor1"])
def test_region_with_trailing_whitespace_is_refused(region):
    api = FakeAPI()
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 2, region, OK)
    assert api.calls == []


def test_project_id_and_urn_with_trailing_newline_are_refused():
    with pytest.raises(zpc.CheckError):
        zpc.discover(FakeAPI(projects=[{"id": "abc\n", "name": zpc.PROJECT_NAME}]), 2, "tor1", OK)
    api = FakeAPI()
    api.resources = [{"urn": "do:droplet:1001\n"}, {"urn": "do:droplet:1002"}]
    with pytest.raises(zpc.CheckError):  # 1001 is tagged but its project urn does not match
        zpc.discover(api, 2, "tor1", OK)


# Finding 3: the cap applies to connect starts, not to submissions.


class DelayedExecutor:
    """Queues submissions and releases them all at once on real threads."""

    def __init__(self, max_workers=None, release_at=4):
        self.release_at = release_at
        self.pending = []
        self.threads = []

    def submit(self, fn, *args):
        fut = concurrent.futures.Future()
        self.pending.append((fut, fn, args))
        if len(self.pending) == self.release_at:
            barrier = threading.Barrier(self.release_at)

            def go(f, func, a):
                barrier.wait(5)
                try:
                    f.set_result(func(*a))
                except (RuntimeError, OSError, ValueError) as exc:
                    f.set_exception(exc)

            for f, func, a in self.pending:
                t = threading.Thread(target=go, args=(f, func, a))
                t.start()
                self.threads.append(t)
            self.pending = []
        return fut

    def shutdown(self, wait=True, cancel_futures=False):
        for t in self.threads:
            t.join(10)


def test_rate_cap_holds_for_connect_starts_with_delayed_real_threads():
    import time

    stamps = []
    lock = threading.Lock()

    def connect(address, port, timeout):
        with lock:
            stamps.append(time.monotonic())
        return zpc.TIMEOUT

    inv = units(1)
    zpc.scan(inv, connect, zpc.Budget(concurrency=4, rate=20.0, batch=4), reread=lambda: inv,
             executor_factory=DelayedExecutor, ports=range(1, 5))
    stamps.sort()
    assert len(stamps) == 4
    gaps = [b - a for a, b in itertools.pairwise(stamps)]
    assert min(gaps) >= 0.045, f"connect starts bunched: {gaps}"


def test_rate_limiter_is_thread_safe_on_real_threads():
    import time

    limiter = zpc._RateLimiter(50.0, time.monotonic, time.sleep)
    stamps = []
    lock = threading.Lock()

    def work():
        limiter.wait()
        with lock:
            stamps.append(time.monotonic())

    threads = [threading.Thread(target=work) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stamps.sort()
    assert min(b - a for a, b in itertools.pairwise(stamps)) >= 0.015


# Finding 4: the report parent directory cannot be swapped between validation and write.


def test_swapping_the_parent_for_a_symlink_into_the_repo_does_not_write_there(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    safe = tmp_path / "safe"
    safe.mkdir()
    target = zpc.check_out_path(str(safe / "r.txt"))
    try:
        safe.rename(tmp_path / "moved")
        safe.symlink_to(fake_repo)
        zpc.write_report(target, ["line"])
    finally:
        zpc.close_report_target(target)
    assert not (fake_repo / "r.txt").exists(), "the report landed inside the repository"
    assert (tmp_path / "moved" / "r.txt").read_text() == "line\n"
    assert stat.S_IMODE((tmp_path / "moved" / "r.txt").stat().st_mode) == 0o600


def test_a_parent_that_is_a_symlink_into_the_repo_is_refused(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    (fake_repo / "docs").mkdir(parents=True)
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    link = tmp_path / "link"
    link.symlink_to(fake_repo)
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path(str(link / "r.txt"))
    # an intermediate symlink: the physical parent is repo/docs
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path(str(link / "docs" / "r.txt"))
    assert not (fake_repo / "r.txt").exists()


def test_a_parent_directly_inside_or_at_the_repo_is_refused_and_outside_is_allowed(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    (fake_repo / "a" / "b").mkdir(parents=True)
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    for inside in (fake_repo, fake_repo / "a", fake_repo / "a" / "b"):
        with pytest.raises(zpc.CheckError):
            zpc.check_out_path(str(inside / "r.txt"))
    outside = tmp_path / "out"
    outside.mkdir()
    target = zpc.check_out_path(str(outside / "r.txt"))
    zpc.close_report_target(target)


@pytest.mark.parametrize("name", ["", ".", ".."])
def test_report_path_without_a_file_name_is_refused(tmp_path, name):
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path(str(tmp_path) + "/" + name)


# Finding 5: the production workload is 65,535 ports per unit, independent of the generated range.


def test_production_hooks_use_the_full_range_and_a_run_requires_it():
    assert zpc.Hooks().ports is None, "an override must be explicit"
    assert zpc.Hooks().effective_ports() == range(1, 65536)
    assert zpc.ALL_PORTS == range(1, 65536) and zpc.MAX_PORT == 65535


def test_main_without_a_ports_override_attempts_all_65535_ports_per_unit():
    api = FakeAPI(tagged=[droplet(1001, A)], project_droplets=[1001])
    counters = Counters()
    clock = Clock()
    hooks = zpc.Hooks(address_ok=OK, connect=counters.connect, control_connect=counters.control_connect,
                      transport_factory=lambda t: api, executor_factory=InlineExecutor,
                      clock=clock, sleep=clock.sleep)
    out = io.StringIO()
    code = zpc.main(["--expect-connectors", "1"], env={"DIGITALOCEAN_TOKEN": CRED}, hooks=hooks, stdout=out)
    assert code == 0, out.getvalue()
    assert sorted(p for _, p in counters.calls) == list(range(1, 65536))
    assert "attempted 65535" in out.getvalue()


def test_a_shrunken_production_range_cannot_pass(monkeypatch):
    monkeypatch.setattr(zpc, "ALL_PORTS", range(1, zpc.MAX_PORT))
    api = FakeAPI(tagged=[droplet(1001, A)], project_droplets=[1001])
    clock = Clock()
    counters = Counters()
    hooks = zpc.Hooks(address_ok=OK, connect=counters.connect, control_connect=counters.control_connect,
                      transport_factory=lambda t: api, executor_factory=InlineExecutor,
                      clock=clock, sleep=clock.sleep)
    out = io.StringIO()
    code = zpc.main(["--expect-connectors", "1"], env={"DIGITALOCEAN_TOKEN": CRED}, hooks=hooks, stdout=out)
    assert code == 2 and "PASS" not in out.getvalue()


# ------------------------------------------------------------------ extra audit

PRODUCTION_REFUSED = [
    "::ffff:8.8.8.8", "01.2.3.4", "08.8.8.8", "8.8.8.08", "8.8.8.8 ", " 8.8.8.8", "8.8.8.8\n", "8.8.8.8\x00",
    "８.８.８.８", "8.8.8.8/32", "8.8.8", "8.8.8.8.8", "134744072", "0x08080808",
    "0x8.0x8.0x8.0x8", "010.8.8.8", "8.8.8.256", "-8.8.8.8", "+8.8.8.8", "", "localhost",
    "100.64.0.1", "100.127.255.255", "198.18.0.1", "198.19.255.255",
    "192.0.2.1", "198.51.100.1", "203.0.113.1",
    "0.0.0.0", "0.1.2.3", "240.0.0.1", "255.255.255.255", "224.0.0.1", "239.255.255.255",
    "10.0.0.1", "172.16.0.1", "192.168.1.1", "127.0.0.1", "169.254.169.254", "192.0.0.1",
]


@pytest.mark.parametrize("value", PRODUCTION_REFUSED)
def test_production_predicate_refuses_every_odd_spelling_and_special_range(value):
    with pytest.raises(zpc.CheckError):
        zpc.parse_public_ipv4(value, zpc.default_address_ok)


@pytest.mark.parametrize("value", [None, 134744072, 134744072.0, True, b"8.8.8.8", ["8.8.8.8"], {"a": 1}])
def test_production_predicate_refuses_non_strings(value):
    with pytest.raises(zpc.CheckError):
        zpc.parse_public_ipv4(value, zpc.default_address_ok)


def test_production_predicate_accepts_a_plain_public_address():
    # A well-known public resolver address, only parsed here; no connection is ever made to it.
    assert zpc.parse_public_ipv4("8.8.8.8", zpc.default_address_ok) == "8.8.8.8"


def test_argparse_errors_never_echo_the_environment_or_the_token():
    env = {"PATH": os.environ.get("PATH", ""), "DIGITALOCEAN_TOKEN": CRED}
    # Both invocations fail inside argparse, before the token is read or any request is built.
    for args in (["--expect-connectors", "abc"], ["--bogus"], []):
        run = subprocess.run([sys.executable, "-I", str(SCRIPT), *args],
                             capture_output=True, text=True, env=env, timeout=60, check=False)
        assert run.returncode == 2
        assert CRED not in run.stdout and CRED not in run.stderr and "SECRET" not in run.stderr


def open_fd_count():
    return len(os.listdir("/proc/self/fd"))


def test_no_descriptors_leak_on_discovery_scan_and_report_failures(make_site, tmp_path):
    site500 = make_site(lambda h: (500, {}, b"x"))
    site302 = make_site(lambda h: (302, {"Location": "http://127.0.0.1:1/"}, b""))
    sitejson = make_site(lambda h: (200, {}, b"not json"))
    api = FakeAPI()
    before = open_fd_count()
    for _ in range(25):
        for site in (site500, site302, sitejson):
            with pytest.raises(zpc.CheckError):
                zpc.ApiTransport(CRED, site.url).get("/v2/projects", {})
        # report target opened then never written, then closed; and a write that fails
        target = zpc.check_out_path(str(tmp_path / "leak.txt"))
        (tmp_path / "leak.txt").write_text("x")
        with pytest.raises(zpc.CheckError):
            zpc.write_report(target, ["x"])
        zpc.close_report_target(target)
        (tmp_path / "leak.txt").unlink()
        # a refused report path and a failed run through main
        run_main(api, argv=["--out", str(tmp_path / "missing" / "r.txt")])
        run_main(FakeAPI(tagged=[]))
        run_main(api)
    # allow the loopback servers' own per-connection sockets to settle
    for _ in range(50):
        if open_fd_count() <= before + 3:
            break
        threading.Event().wait(0.02)
    assert open_fd_count() <= before + 3, "descriptors accumulate across failing runs"


def test_report_target_is_closed_when_main_ends_on_every_path(tmp_path):
    before = open_fd_count()
    for i in range(10):
        report = tmp_path / f"r{i}.txt"
        run_main(FakeAPI(), argv=["--out", str(report)])  # success
        run_main(FakeAPI(tagged=[]), argv=["--out", str(tmp_path / f"f{i}.txt")])  # discovery failure
        run_main(FakeAPI(), counters=Counters(outcome=zpc.OPEN), argv=["--out", str(tmp_path / f"o{i}.txt")])
    assert open_fd_count() <= before + 1


def test_sockets_do_not_leak_across_many_tcp_connect_failures():
    FakeSocket.created = FakeSocket.closed = 0
    for behaviour in ("ok", "timeout", errno.ECONNREFUSED, errno.EMFILE, "settimeout-fails"):
        for _ in range(50):
            zpc.tcp_connect("192.0.2.1", 80, 1.0, socket_factory=lambda *a, b=behaviour: FakeSocket(b))
    assert FakeSocket.created == FakeSocket.closed == 250


def test_keyboard_interrupt_with_real_threads_leaves_no_workers_and_discards_results():
    started = threading.Event()

    def slow_connect(address, port, timeout):
        started.set()
        threading.Event().wait(0.05)
        return zpc.TIMEOUT

    calls = []

    def interrupting_reread():
        calls.append(1)
        raise KeyboardInterrupt

    api = FakeAPI()
    out = io.StringIO()
    original_get = api.get
    state = {"projects": 0}

    def get(path, params):
        if path == "/v2/projects":
            state["projects"] += 1
        return original_get(path, params)

    api.get = get

    # The first discovery succeeds; the re-read after the first batch is interrupted.
    def transport_factory(token):
        class T:
            def get(self, path, params):
                if path == "/v2/projects" and state["projects"] >= 1:
                    interrupting_reread()
                return get(path, params)

        return T()

    code = zpc.main(
        ["--expect-connectors", "2"], env={"DIGITALOCEAN_TOKEN": CRED}, stdout=out,
        hooks=zpc.Hooks(address_ok=OK, connect=slow_connect, control_connect=lambda h, p, t: None,
                        transport_factory=transport_factory, ports=range(1, 41),
                        budget=zpc.Budget(concurrency=8, rate=1e6, batch=16)))
    assert code == 2 and "interrupted" in out.getvalue()
    assert "PASS" not in out.getvalue() and "attempted" not in out.getvalue()
    assert calls, "the interrupt was delivered"
    for _ in range(100):
        if not [t for t in threading.enumerate() if t.name.startswith("ThreadPoolExecutor")]:
            break
        threading.Event().wait(0.02)
    assert not [t for t in threading.enumerate() if t.name.startswith("ThreadPoolExecutor")]


# DigitalOcean response shapes


def test_total_changing_between_pages_is_refused():
    api = FakeAPI(page_size=1)
    original = api._list

    def list_with_drift(key, items, params, total=None):
        data = original(key, items, params, total)
        if int(params["page"]) >= 2:
            data["meta"]["total"] += 1
        return data

    api._list = list_with_drift
    with pytest.raises(zpc.CheckError, match="total"):
        zpc.discover(api, 2, "tor1", OK)


def test_droplet_without_networks_or_with_odd_networks_is_refused():
    for bad in ({"id": 1001}, {"id": 1001, "networks": None}, {"id": 1001, "networks": {}},
                {"id": 1001, "networks": {"v4": "x"}}, {"id": 1001, "networks": {"v4": [None]}},
                {"id": 1001, "networks": {"v4": [{"type": "other", "ip_address": A}]}}):
        api = FakeAPI(tagged=[bad, droplet(1002, B)])
        with pytest.raises(zpc.CheckError):
            zpc.discover(api, 2, "tor1", OK)


def test_only_private_v4_entries_is_refused_and_a_private_entry_is_never_scanned():
    api = FakeAPI(tagged=[droplet(1001, None), droplet(1002, B)])
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 2, "tor1", OK)
    inv = zpc.discover(FakeAPI(), 2, "tor1", OK)
    assert "10.116.0.2" not in {u.address for u in inv.units}


def test_duplicate_droplet_ids_across_pages_are_refused():
    api = FakeAPI(tagged=[droplet(1001, A), droplet(1001, A)], project_droplets=[1001], page_size=1)
    with pytest.raises(zpc.CheckError, match="repeated"):
        zpc.discover(api, 1, "tor1", OK)


def test_reserved_ip_on_a_non_target_droplet_never_becomes_a_target():
    api = FakeAPI(tagged=[droplet(1001, A), droplet(1002, B), droplet(1003, "198.51.100.99")],
                  project_droplets=[1001, 1002],
                  reserved4=[{"ip": RESERVED, "droplet": {"id": 1003}}, {"ip": "198.51.100.51", "droplet": {"id": 77}}])
    inv = zpc.discover(api, 2, "tor1", OK)
    assert {u.address for u in inv.units} == {A, B}


def test_reserved_ipv6_on_a_non_target_droplet_is_ignored():
    api = FakeAPI(reserved6=[{"ip": "2001:db8::5", "droplet": {"id": 4242}}])
    assert len(zpc.discover(api, 2, "tor1", OK).units) == 2


def test_project_resources_listing_is_paginated_and_complete():
    api = FakeAPI(page_size=1)
    inv = zpc.discover(api, 2, "tor1", OK)
    pages = [p["page"] for path, p in api.calls if path.endswith("/resources")]
    assert pages == [1, 2, 3], "droplet, droplet and the volume are three pages of one"
    assert len(inv.units) == 2


def test_a_project_droplet_found_only_on_a_later_resources_page_still_counts():
    api = FakeAPI(page_size=1)
    api.resources = [{"urn": "do:volume:x"}, {"urn": "do:droplet:1001"}, {"urn": "do:droplet:1002"}]
    assert len(zpc.discover(api, 2, "tor1", OK).units) == 2


# ===================================================================== fix round 2
# Finding 1: overdue sleepers must not connect together.


def test_workers_waking_from_a_long_sleep_do_not_start_together_on_the_fake_clock():
    now = [0.0]
    lock = threading.Lock()
    barrier = threading.Barrier(3)
    sleeps = []

    def sleep(delay):
        with lock:
            first = len(sleeps) < 3
            sleeps.append(delay)
        if first:
            barrier.wait(5)  # three sleepers are in flight together
            with lock:
                now[0] = 10.0  # then the world moves on a long way
        else:
            with lock:
                now[0] += delay

    stamps = []

    def connect(address, port, timeout):
        with lock:
            stamps.append(now[0])
        return zpc.TIMEOUT

    inv = units(1)
    zpc.scan(inv, connect, zpc.Budget(concurrency=4, rate=10.0, batch=4), reread=lambda: inv,
             clock=lambda: now[0], sleep=sleep, executor_factory=DelayedExecutor, ports=range(1, 5))
    stamps.sort()
    assert len(stamps) == 4
    gaps = [b - a for a, b in itertools.pairwise(stamps)]
    assert min(gaps) >= 0.1 - 1e-9, f"overdue reservations accumulated credit: {stamps}"


def test_limiter_grants_are_spaced_from_the_actual_grant_time():
    now = [0.0]
    limiter = zpc._RateLimiter(10.0, lambda: now[0], lambda d: now.__setitem__(0, now[0] + d))
    grants = []
    for _ in range(3):
        limiter.wait()
        grants.append(now[0])
    now[0] = 100.0  # a long idle gap earns no burst of credit
    for _ in range(3):
        limiter.wait()
        grants.append(now[0])
    assert all(b - a >= 0.1 - 1e-9 for a, b in itertools.pairwise(grants)), grants


# Finding 2: cleanup inside an error handler must not escape sanitisation.


class RaisingBody:
    def read(self, *a):
        return b""

    def close(self):
        raise OSError(errno.EIO, "close failed " + CRED)


def test_httperror_whose_close_raises_leaves_a_clean_sanitised_error():
    class Opener:
        def open(self, req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 500, "reason " + CRED, {}, RaisingBody())

    transport = zpc.ApiTransport(CRED, "http://127.0.0.1:1")
    transport._opener = Opener()
    with pytest.raises(zpc.CheckError) as info:
        transport.get("/v2/projects", {})
    assert_chain_is_clean(info.value, CRED, "close failed")


CLEANUP_ATTRS = ("close", "shutdown", "unlink", "release")


def unprotected_cleanup_calls(tree):
    """Line numbers of cleanup calls inside an except body that have no try of their own."""
    found = []

    def walk(node, protected):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                walk(stmt, True)
            for handler in node.handlers:
                for stmt in handler.body:
                    walk(stmt, protected)
            for stmt in node.orelse + node.finalbody:
                walk(stmt, protected)
            return
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in CLEANUP_ATTRS and not protected):
            found.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            walk(child, protected)

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for stmt in node.body:
                walk(stmt, False)
    return found


def test_no_cleanup_call_sits_unprotected_inside_an_except_block():
    offenders = unprotected_cleanup_calls(ast.parse(SCRIPT.read_text()))
    assert offenders == [], f"cleanup inside an except block without its own try: lines {offenders}"


def test_the_cleanup_audit_bites():
    bad = ast.parse("try:\n    pass\nexcept OSError as e:\n    e.close()\n")
    good = ast.parse(
        "try:\n    pass\nexcept OSError as e:\n    try:\n        e.close()\n"
        "    except OSError:\n        pass\n"
    )
    assert unprotected_cleanup_calls(bad) and not unprotected_cleanup_calls(good)


# Finding 3: a pinned report directory moved into the repository is caught before and after.


def test_report_directory_renamed_into_the_repo_after_validation_is_not_written(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    safe = tmp_path / "safe"
    safe.mkdir()
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    target = zpc.check_out_path(str(safe / "r.txt"))
    try:
        safe.rename(fake_repo / "moved")
        with pytest.raises(zpc.CheckError, match="repository"):
            zpc.write_report(target, ["line"])
    finally:
        zpc.close_report_target(target)
    assert not (fake_repo / "moved" / "r.txt").exists()


def test_report_directory_moved_in_during_the_write_is_removed(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    safe = tmp_path / "safe"
    safe.mkdir()
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    target = zpc.check_out_path(str(safe / "r.txt"))
    real = zpc._inside_repo
    calls = []

    def moving(fd):
        calls.append(1)
        answer = real(fd)
        if len(calls) == 1:  # the pre-write check passes, then the directory is moved
            safe.rename(fake_repo / "moved")
        return answer

    monkeypatch.setattr(zpc, "_inside_repo", moving)
    try:
        with pytest.raises(zpc.CheckError, match="repository"):
            zpc.write_report(target, ["line"])
    finally:
        zpc.close_report_target(target)
    assert len(calls) == 2, "checked before creating and again after writing"
    assert not (fake_repo / "moved" / "r.txt").exists(), "the mis-placed report was removed"


def test_main_reports_exit_2_when_the_report_directory_moves_into_the_repo(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    safe = tmp_path / "safe"
    safe.mkdir()
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    real = zpc._inside_repo
    calls = []

    def moving(fd):
        calls.append(1)
        if len(calls) == 2:  # validation was call 1; the pre-write check is call 2
            safe.rename(fake_repo / "moved")
        return real(fd)

    monkeypatch.setattr(zpc, "_inside_repo", moving)
    code, out, _ = run_main(FakeAPI(), argv=["--out", str(safe / "r.txt")])
    assert code == 2 and "PASS" not in out
    assert not (fake_repo / "moved" / "r.txt").exists()


# Finding 4: covered in the edited close-failure tests above.

# Finding 5: no ambient HTTP debug logging.


def test_http_handlers_ignore_the_ambient_debuglevel(monkeypatch, capsys, make_site):
    import http.client

    monkeypatch.setattr(http.client.HTTPConnection, "debuglevel", 1)
    monkeypatch.setattr(http.client.HTTPSConnection, "debuglevel", 1)
    opener = zpc.build_opener()
    handlers = [h for h in opener.handlers if hasattr(h, "_debuglevel")]
    assert handlers and all(h._debuglevel == 0 for h in handlers)
    site = make_site(json_route(FakeAPI()))
    zpc.ApiTransport(CRED, site.url).get("/v2/projects", {"page": 1})
    captured = capsys.readouterr()
    assert "send:" not in captured.out and CRED not in captured.out and CRED not in captured.err


def test_the_default_urllib_would_print_the_header_so_the_debug_test_bites(monkeypatch, capsys, make_site):
    import http.client

    monkeypatch.setattr(http.client.HTTPConnection, "debuglevel", 1)
    site = make_site(lambda h: (200, {"Content-Type": "application/json"}, b"{}"))
    req = urllib.request.Request(site.url + "/x", headers={"Authorization": "Bearer " + CRED})
    with contextlib.closing(urllib.request.build_opener().open(req, timeout=5)):
        pass
    assert CRED in capsys.readouterr().out


# Finding 6: no leaked descriptor when the ancestry walk fails half way.


def test_ancestry_walk_does_not_leak_when_fstat_fails(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.setattr(zpc, "_repo_root", lambda: fake_repo)
    dir_fd = os.open(deep, os.O_RDONLY | os.O_DIRECTORY)
    real = os.fstat
    state = {"n": 0, "active": False}

    def flaky(fd):
        if state["active"]:
            state["n"] += 1
            if state["n"] == 2:
                raise OSError(errno.EIO, "fstat failed")
        return real(fd)

    try:
        before = open_fd_count()
        monkeypatch.setattr(os, "fstat", flaky)
        for _ in range(20):
            state.update(n=0, active=True)
            assert zpc._inside_repo(dir_fd) is True, "doubt counts as inside"
            state["active"] = False
        monkeypatch.setattr(os, "fstat", real)
        assert open_fd_count() == before, "the opened parent descriptor leaked"
    finally:
        os.close(dir_fd)


# Round 4: every returned droplet must itself carry the exact baseline tag.


def _discover_with(tagged):
    api = FakeAPI(tagged=tagged)
    return zpc.discover(api, len(tagged), "tor1", OK)


def test_a_droplet_with_the_baseline_tag_is_accepted():
    assert _discover_with([droplet(1001, A)]).labels == ("connector-1",)


@pytest.mark.parametrize(
    "tags",
    [
        _NO_TAGS,
        [],
        "cah-baseline-tor1",
        7,
        {"cah-baseline-tor1": 1},
        [1],
        [BASELINE_TAG, 1],
        [BASELINE_TAG, BASELINE_TAG],
        ["cah-baseline-ams3"],
        ["cah-baseline-tor1-x"],
        ["CAH-BASELINE-TOR1"],
        [BASELINE_TAG + "\n"],
        [True],
    ],
    ids=lambda v: "no-tags-member" if v is _NO_TAGS else repr(v),
)
def test_a_returned_droplet_without_a_proper_baseline_tag_is_refused(tags):
    tagged = [droplet(1001, "8.8.8.8", tags=tags)]
    with pytest.raises(zpc.CheckError):
        zpc.discover(FakeAPI(tagged=tagged), 1, "tor1", zpc.default_address_ok)


def test_main_stops_before_the_control_and_any_socket_when_a_tag_is_missing():
    counters = Counters()
    api = FakeAPI(tagged=[droplet(1001, A, tags=_NO_TAGS)])
    code, _out, _ = run_main(api, expected=1, counters=counters)
    assert code == 2 and counters.scan == 0 and counters.control == 0


# Round 4: the report directory is walked component by component; no symlink anywhere.


def test_a_symlink_in_an_ancestor_is_refused_even_when_it_leads_to_an_allowed_directory(tmp_path):
    real = tmp_path / "real"
    (real / "sub").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path(str(link / "sub" / "r.txt"))
    # control: the same directory through plain components is accepted
    target = zpc.check_out_path(str(real / "sub" / "r.txt"))
    zpc.close_report_target(target)


def test_dot_dot_through_a_symlink_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "out").mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path(str(link / ".." / "out" / "r.txt"))


def test_a_relative_path_is_walked_too(tmp_path, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(zpc.CheckError):
        zpc.check_out_path("link/r.txt")
    target = zpc.check_out_path("real/r.txt")
    zpc.close_report_target(target)


# Round 5: the baseline tag follows the stack's resource_key when one is set.

KEY = "tor1-b"
KEY_TAG = "cah-baseline-tor1-b"


def _keyed(n=1):
    return [droplet(1000 + i, f"198.51.100.{10 + i}", tags=[KEY_TAG]) for i in range(1, n + 1)]


def test_resource_key_builds_the_tag_the_stack_publishes():
    api = FakeAPI(tagged=_keyed(), tag=KEY_TAG)
    inv = zpc.discover(api, 1, "tor1", OK, KEY)
    assert inv.labels == ("connector-1",)


def test_without_a_resource_key_the_region_tag_is_used():
    api = FakeAPI(tagged=[droplet(1001, A)])
    assert zpc.discover(api, 1, "tor1", OK, "").labels == ("connector-1",)


def test_region_only_query_misses_a_keyed_stack_and_stops():
    # the failure the option exists to fix: the stack tagged cah-baseline-tor1-b
    api = FakeAPI(tagged=_keyed(), tag=BASELINE_TAG)
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 1, "tor1", OK, "")


def test_a_droplet_with_only_the_region_tag_is_refused_when_a_key_is_given():
    api = FakeAPI(tagged=[droplet(1001, A)], tag=KEY_TAG)
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 1, "tor1", OK, KEY)


def test_main_accepts_resource_key_and_scans():
    api = FakeAPI(tagged=_keyed(), tag=KEY_TAG)
    code, out, counters = run_main(api, expected=1, argv=["--resource-key", KEY])
    assert code == 0 and counters.scan == 3 and "198.51.100" not in out


@pytest.mark.parametrize(
    "key",
    ["tor1-b\n", "Tor1", "TOR1-B", "a", "1abc", "-abc", "a" * 25, "a;rm", "a b", "a$(x)", "a`x`",
     "a|b", "a&b", "a/../b", "a_b", "a.b", "tor1-b ", " tor1-b", "tör1"],
)
def test_a_hostile_resource_key_is_refused_before_any_request(key):
    api = FakeAPI()
    with pytest.raises(zpc.CheckError):
        zpc.discover(api, 1, "tor1", OK, key)
    assert api.calls == []


@pytest.mark.parametrize("key", ["ab", "a" * 24, "tor1-b", "x-1-2"])
def test_boundary_resource_keys_are_accepted(key):
    tag = "cah-baseline-" + key
    api = FakeAPI(tagged=[droplet(1001, A, tags=[tag])], tag=tag)
    assert zpc.discover(api, 1, "tor1", OK, key).labels == ("connector-1",)


def test_main_refuses_a_hostile_resource_key_with_no_socket():
    counters = Counters()
    code, _out, _ = run_main(FakeAPI(), expected=1, counters=counters, argv=["--resource-key", "BAD\n"])
    assert code == 2 and counters.scan == 0 and counters.control == 0
