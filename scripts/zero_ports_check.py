#!/usr/bin/env python3
"""External zero-open-ports check for the stage 1 connectors (issue #91).

Run by hand, from a machine that is NOT in the VPC, after any firewall or
droplet change. It attempts one TCP connect to every port (1 to 65535) of every
connector's public address and passes only if every attempt timed out: no
answer at all, as seen from this network.

There is no way to give it an address. It takes no host, address, target or
file argument and reads no environment variable except DIGITALOCEAN_TOKEN (the
credential). Targets come only from the DigitalOcean API, read-only, and only
after discovery is complete: a droplet is a target only if it carries the
baseline tag AND is a member of the project `clouds-against-humanity`, and the
operator states how many such droplets must exist (--expect-connectors N). The
API is a trust anchor: a lying API defeats this rail, and a person who edits
this script defeats it too. The rails make the intended use the only easy one.

Usage (the token comes from Doppler, in its own read-only config):

  doppler run -- python3 -I scripts/zero_ports_check.py --expect-connectors 2 [--region tor1] [--out PATH]

Exit codes: 0 only if every expected address and every port was attempted
exactly once and every attempt timed out; 1 if any port answered (a connection,
or a refusal, which means something answered); 2 for everything else
(discovery problems, a local error, unreachable, an inventory change,
interruption, a report that could not be written).

Output is a fixed set of strings and counts: connector labels (connector-1),
never an address; the token never appears anywhere. TCP only, one vantage point,
one moment in time. See docs/stages/01-access.md.

Standard library only; spawns no subprocess.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import errno
import http.client
import ipaddress
import itertools
import json
import os
import re
import resource
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

API_ORIGIN = "https://api.digitalocean.com"
PROJECT_NAME = "clouds-against-humanity"
TOKEN_ENV = "DIGITALOCEAN_TOKEN"
TAG_PREFIX = "cah-baseline-"
CONTROL_TARGET = ("api.digitalocean.com", 443)

MAX_BODY = 4 * 1024 * 1024
MAX_PAGES = 20
PER_PAGE = 200
API_TIMEOUT = 15.0
MAX_PORT = 65535
ALL_PORTS = range(1, MAX_PORT + 1)
NOFILE_MARGIN = 64

OPEN = "open"
REFUSED = "refused"
TIMEOUT = "timeout"
UNREACHABLE = "unreachable"
LOCAL = "local_error"
ERROR = "error"
OPEN_CLEANUP = "open_cleanup_problem"
REFUSED_CLEANUP = "refused_cleanup_problem"
_CLEANUP_TAGGED = {OPEN: OPEN_CLEANUP, REFUSED: REFUSED_CLEANUP}
_CLEANUP_BASE = {OPEN_CLEANUP: OPEN, REFUSED_CLEANUP: REFUSED}
OUTCOMES = frozenset({OPEN, REFUSED, TIMEOUT, UNREACHABLE, LOCAL, ERROR, OPEN_CLEANUP, REFUSED_CLEANUP})

_SAFE_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
_DROPLET_URN = re.compile(r"do:droplet:([0-9]{1,18})")
_REGION = re.compile(r"[a-z0-9]{2,16}")
_TOKEN = re.compile(r"[\x21-\x7e]{8,256}")


# Anything unexpected that is still a program or system fault, not a test assertion.
_INTERNAL_ERRORS = (
    OSError,
    LookupError,
    ArithmeticError,
    ValueError,
    TypeError,
    AttributeError,
    RuntimeError,
    http.client.HTTPException,
)


class CheckError(Exception):
    """Every expected failure. The message is a fixed string: no URL, body or value."""


class InventoryChanged(CheckError):
    pass


class Interrupted(CheckError):
    pass


# ----------------------------------------------------------------- transport


class _Secret:
    __slots__ = ("_v",)

    def __init__(self, value: str) -> None:
        self._v = value

    def reveal(self) -> str:
        return self._v

    def __repr__(self) -> str:
        return "<redacted>"

    __str__ = __repr__


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # urllib signature
        return None


def _origin(url: str) -> tuple[str, str]:
    parts = urllib.parse.urlsplit(url)
    return parts.scheme, parts.netloc


def build_opener() -> urllib.request.OpenerDirector:
    """No proxy from the environment, verified TLS, every redirect refused."""
    # debuglevel=0 is explicit: left unset, a handler copies http.client's class attribute, and an
    # importing process that set it to 1 would make urllib print the Authorization header.
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _RefuseRedirect(),
        urllib.request.HTTPHandler(debuglevel=0),
        urllib.request.HTTPSHandler(debuglevel=0, context=ssl.create_default_context()),
    )


class ApiTransport:
    """Read-only GETs against one fixed origin. URLs are built here, never taken from a response."""

    def __init__(self, token: str, base_url: str = API_ORIGIN, max_body: int = MAX_BODY) -> None:
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise CheckError("the API token is missing or malformed")
        if base_url != API_ORIGIN:
            # Test seam only (never reachable from the command line): loopback http.
            parts = urllib.parse.urlsplit(base_url)
            if parts.scheme != "http" or parts.hostname != "127.0.0.1":
                raise CheckError("refusing a non-default API origin")
        self._token = _Secret(token)
        self._base = base_url
        self._max_body = max_body
        self._opener = build_opener()

    def __repr__(self) -> str:
        return "ApiTransport(<redacted>)"

    def get(self, path: str, params: dict[str, str | int]) -> dict:
        url = self._base + path
        if params:
            url += "?" + urllib.parse.urlencode(sorted(params.items()))
        req = urllib.request.Request(url, method="GET")  # fixed origin, checked above
        req.add_unredirected_header("Authorization", "Bearer " + self._token.reveal())
        req.add_unredirected_header("Accept", "application/json")
        # A sanitised error is raised only AFTER the except block has ended, so it carries
        # no __context__ or __cause__ that could still hold the request, the header or the body.
        failure = None
        raw = b""
        try:
            with self._opener.open(req, timeout=API_TIMEOUT) as resp:
                if _origin(resp.geturl()) != _origin(self._base):
                    failure = "the API answered from an unexpected origin"
                elif resp.status != 200:
                    failure = "the API answered with an unexpected status"
                else:
                    raw = resp.read(self._max_body + 1)
        except urllib.error.HTTPError as exc:
            code = exc.code
            try:
                exc.close()
            except _INTERNAL_ERRORS:
                pass  # cleanup trouble must not replace the sanitised error raised below
            if 300 <= code < 400:
                failure = "the API tried to redirect; redirects are refused"
            elif code in (401, 403):
                failure = "the API refused the token or its scopes"
            else:
                failure = "the API answered with an error status"
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError):
            failure = "the API could not be reached or the connection failed"
        if failure is not None:
            raise CheckError(failure)
        if len(raw) > self._max_body:
            raise CheckError("the API response was larger than the limit")
        return _parse_json(raw)


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _reject_constant(_name: str) -> None:
    raise ValueError("non-finite number")


def _parse_json(raw: bytes) -> dict:
    data = None
    failed = False
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError):  # UnicodeDecodeError is a ValueError
        failed = True
    if failed:
        raise CheckError("the API response was not valid JSON")
    if not isinstance(data, dict):
        raise CheckError("the API response had an unexpected shape")
    return data


# ----------------------------------------------------------------- discovery


@dataclass(frozen=True)
class Unit:
    """One address to scan. The address is never printed; the label is."""

    label: str
    address: str = field(repr=False)
    droplet_id: int = field(repr=False)


@dataclass(frozen=True)
class Inventory:
    units: tuple[Unit, ...]

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(u.label for u in self.units)


def default_address_ok(addr: ipaddress.IPv4Address) -> bool:
    # is_global is True for multicast (224.0.0.0/4), so the other classes are excluded by name too.
    return addr.is_global and not (
        addr.is_multicast
        or addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_unspecified
    )


def parse_public_ipv4(value: object, address_ok: Callable[[ipaddress.IPv4Address], bool]) -> str:
    """JSON string, canonical dotted quad, parsed from a str only, and public."""
    if not isinstance(value, str):
        raise CheckError("an address was not a JSON string")
    addr = None
    try:
        addr = ipaddress.IPv4Address(value)
    except ValueError:
        pass
    if addr is None:
        raise CheckError("an address was not a dotted-quad IPv4 address")
    if str(addr) != value:
        raise CheckError("an address was not in canonical form")
    if not address_ok(addr):
        raise CheckError("an address was not a public address")
    return value


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fetch_all(transport, path: str, params: dict, key: str, ident: str) -> list[dict]:
    """Follow pages with locally built requests; never follow a returned URL."""
    items: list[dict] = []
    seen: set = set()
    total = None
    for page in range(1, MAX_PAGES + 1):
        data = transport.get(path, {**params, "page": page, "per_page": PER_PAGE})
        batch = data.get(key)
        if not isinstance(batch, list) or not all(isinstance(i, dict) for i in batch):
            raise CheckError("an API listing had an unexpected shape")
        meta = data.get("meta")
        if not isinstance(meta, dict) or not _is_int(meta.get("total")) or meta["total"] < 0:
            raise CheckError("an API listing had no usable total")
        if total is not None and meta["total"] != total:
            raise CheckError("an API listing total changed between pages")
        total = meta["total"]
        for item in batch:
            ident_value = item.get(ident)
            if not isinstance(ident_value, (str, int)) or isinstance(ident_value, bool):
                raise CheckError("an API listing item had no usable identifier")
            if ident_value in seen:
                raise CheckError("an API listing repeated an item")
            seen.add(ident_value)
        items.extend(batch)
        links = data.get("links")
        pages = links.get("pages") if isinstance(links, dict) else None
        more = bool(pages.get("next")) if isinstance(pages, dict) else False
        if not more:
            break
        if not batch:
            raise CheckError("an API listing promised more pages after an empty page")
    else:
        raise CheckError("an API listing exceeded the page limit")
    if len(items) != total:
        raise CheckError("an API listing total contradicts its pages")
    return items


def discover(
    transport,
    expected: int,
    region: str = "tor1",
    address_ok: Callable[[ipaddress.IPv4Address], bool] = default_address_ok,
) -> Inventory:
    """All API reads, strict parsing and the intersection. Raises CheckError; opens no socket."""
    if not _is_int(expected) or expected < 1:
        raise CheckError("--expect-connectors must be at least 1")
    if not isinstance(region, str) or not _REGION.fullmatch(region):
        raise CheckError("the region is malformed")
    tag = TAG_PREFIX + region

    projects = _fetch_all(transport, "/v2/projects", {}, "projects", "id")
    named = [p for p in projects if p.get("name") == PROJECT_NAME]
    if len(named) != 1:
        raise CheckError("the project was not found exactly once")
    project_id = named[0]["id"]
    if not isinstance(project_id, str) or not _SAFE_ID.fullmatch(project_id):
        raise CheckError("the project identifier was malformed")

    resources = _fetch_all(
        transport, f"/v2/projects/{project_id}/resources", {}, "resources", "urn"
    )
    project_droplets: set[int] = set()
    for res in resources:
        urn = res["urn"]
        if not isinstance(urn, str):
            raise CheckError("a project resource identifier was malformed")
        match = _DROPLET_URN.fullmatch(urn)
        if match:
            project_droplets.add(int(match.group(1)))

    tagged = _fetch_all(transport, "/v2/droplets", {"tag_name": tag}, "droplets", "id")
    by_id: dict[int, dict] = {}
    for droplet in tagged:
        if not _is_int(droplet["id"]):
            raise CheckError("a droplet identifier was not an integer")
        _require_baseline_tag(droplet, tag)
        by_id[droplet["id"]] = droplet

    if project_droplets - set(by_id):
        raise CheckError("a droplet in the project does not carry the baseline tag")
    targets = sorted(set(by_id) & project_droplets)
    if len(targets) != expected:
        raise CheckError("the number of tagged project droplets is not the expected number")

    reserved_by_droplet = _reserved_for(transport, set(targets), address_ok)

    units: list[Unit] = []
    for index, droplet_id in enumerate(targets, start=1):
        label = f"connector-{index}"
        addresses = _droplet_public_v4(by_id[droplet_id], address_ok)
        if not addresses:
            raise CheckError("a droplet has no public IPv4 address")
        units.append(Unit(label, addresses[0], droplet_id))
        extra = sorted((set(addresses) | set(reserved_by_droplet.get(droplet_id, ()))) - {addresses[0]})
        for number, address in enumerate(extra, start=1):
            units.append(Unit(f"{label}-extra-{number}", address, droplet_id))
    if len({u.address for u in units}) != len(units):
        raise CheckError("two scan units share an address")
    return Inventory(tuple(units))


def _require_baseline_tag(droplet: dict, tag: str) -> None:
    """The tag filter is a request parameter, not proof: check the droplet itself."""
    tags = droplet.get("tags")
    if (
        not isinstance(tags, list)
        or not all(isinstance(t, str) for t in tags)
        or len(set(tags)) != len(tags)
        or tag not in tags
    ):
        raise CheckError("a droplet does not carry the exact baseline tag")


def _droplet_public_v4(droplet: dict, address_ok) -> list[str]:
    networks = droplet.get("networks")
    if not isinstance(networks, dict):
        raise CheckError("a droplet had no network information")
    v4 = networks.get("v4", [])
    v6 = networks.get("v6", [])
    if not isinstance(v4, list) or not isinstance(v6, list):
        raise CheckError("a droplet had malformed network information")
    for entry in v6:
        if not isinstance(entry, dict) or entry.get("type") not in ("public", "private"):
            raise CheckError("a droplet had a malformed IPv6 entry")
        if entry["type"] == "public":
            raise CheckError("a droplet has a public IPv6 address")
    out: list[str] = []
    for entry in v4:
        if not isinstance(entry, dict) or entry.get("type") not in ("public", "private"):
            raise CheckError("a droplet had a malformed IPv4 entry")
        if entry["type"] == "public":
            out.append(parse_public_ipv4(entry.get("ip_address"), address_ok))
    return sorted(set(out))


def _reserved_for(transport, droplet_ids: set[int], address_ok) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    v4 = _fetch_all(transport, "/v2/reserved_ips", {}, "reserved_ips", "ip")
    for item in v4:
        owner = _reserved_owner(item)
        if owner in droplet_ids:
            found.setdefault(owner, []).append(parse_public_ipv4(item.get("ip"), address_ok))
    v6 = _fetch_all(transport, "/v2/reserved_ipv6", {}, "reserved_ipv6s", "ip")
    for item in v6:
        if _reserved_owner(item) in droplet_ids:
            raise CheckError("a droplet has a reserved IPv6 address")
    return found


def _reserved_owner(item: dict) -> int | None:
    droplet = item.get("droplet")
    if droplet is None:
        return None
    if not isinstance(droplet, dict) or not _is_int(droplet.get("id")):
        raise CheckError("a reserved address had a malformed assignment")
    return droplet["id"]


# ------------------------------------------------------------------- scanning


@dataclass(frozen=True)
class Budget:
    concurrency: int = 512
    timeout: float = 2.0
    rate: float = 1500.0
    batch: int = 4096


def classify_errno(code: int | None) -> str:
    if code in (errno.ECONNREFUSED, errno.ECONNRESET, errno.ECONNABORTED):
        return REFUSED
    if code == errno.ETIMEDOUT:
        return TIMEOUT
    if code in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ENETDOWN, errno.EHOSTDOWN):
        return UNREACHABLE
    if code in (
        errno.EMFILE,
        errno.ENFILE,
        errno.EADDRNOTAVAIL,
        errno.ENOBUFS,
        errno.ENOMEM,
        errno.EAGAIN,
    ):
        return LOCAL
    return ERROR


def _attempt(sock, address: str, port: int) -> str:
    """The connect call itself: the only place where a TimeoutError means "no answer"."""
    try:
        sock.connect((address, port))
    except TimeoutError:
        return TIMEOUT
    except OSError as exc:
        return classify_errno(exc.errno)
    return OPEN


def tcp_connect(address: str, port: int, timeout: float, *, socket_factory=socket.socket) -> str:
    """One attempt. The timeout starts here, when the attempt begins. The socket is always closed.

    Socket creation, setup and close failures of any type are LOCAL errors (exit 2), never a
    timeout: only a TimeoutError raised by connect() itself counts as silence.
    """
    sock = None
    outcome = LOCAL
    try:
        sock = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        ready = True
    except _INTERNAL_ERRORS:
        ready = False
    if ready:
        outcome = _attempt(sock, address, port)
    if sock is not None:
        try:
            sock.close()
        except _INTERNAL_ERRORS:
            # An observed answer stays an answer, with the cleanup problem recorded beside it.
            # After silence (or any other result) a failed close means we cannot tell.
            outcome = _CLEANUP_TAGGED.get(outcome, LOCAL)
    return outcome


class Accounting:
    def __init__(self, labels: tuple[str, ...]) -> None:
        self.labels = labels
        self._lock = threading.Lock()
        n = len(labels)
        self.counts = [dict.fromkeys(OUTCOMES, 0) for _ in range(n)]
        self.open_ports: list[list[int]] = [[] for _ in range(n)]
        self.refused_ports: list[list[int]] = [[] for _ in range(n)]
        self._seen = [bytearray(MAX_PORT + 1) for _ in range(n)]
        self.unique = [0] * n
        self.cleanup_problems = [0] * n
        self.duplicates = 0
        self.invalid = 0

    def record(self, unit: int, port: int, outcome: str) -> None:
        with self._lock:
            if not (0 <= unit < len(self.labels)) or not (1 <= port <= MAX_PORT):
                self.invalid += 1
                return
            if outcome not in OUTCOMES:
                outcome = ERROR
            if self._seen[unit][port]:
                self.duplicates += 1
                return
            self._seen[unit][port] = 1
            self.unique[unit] += 1
            if outcome in _CLEANUP_BASE:
                self.cleanup_problems[unit] += 1
                outcome = _CLEANUP_BASE[outcome]
            self.counts[unit][outcome] += 1
            if outcome == OPEN:
                self.open_ports[unit].append(port)
            elif outcome == REFUSED:
                self.refused_ports[unit].append(port)


class _RateLimiter:
    """Spaces connect starts at least 1/rate apart. Called by each worker right before connect().

    A grant loop: eligibility is re-checked under the lock after every sleep and the next
    allowed time comes from the ACTUAL grant time, so a worker that slept past its slot earns
    no credit for the others. The lock is never held while sleeping.
    """

    def __init__(self, rate: float, clock, sleep) -> None:
        self._gap = 1.0 / rate
        self._clock = clock
        self._sleep = sleep
        self._next = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                if self._next is None or now >= self._next:
                    self._next = now + self._gap
                    return
                delay = self._next - now
            self._sleep(delay)


def check_nofile(concurrency: int, getrlimit=resource.getrlimit) -> None:
    soft, _hard = getrlimit(resource.RLIMIT_NOFILE)
    if soft != resource.RLIM_INFINITY and soft < concurrency + NOFILE_MARGIN:
        raise CheckError("the open-file limit is too low for the concurrency; cannot tell")


def scan(
    inventory: Inventory,
    connect: Callable[[str, int, float], str],
    budget: Budget,
    *,
    reread: Callable[[], Inventory],
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    executor_factory=concurrent.futures.ThreadPoolExecutor,
    ports=None,
) -> Accounting:
    """Attempt every (unit, port) once. Re-read the inventory after each batch; a change raises."""
    acc = Accounting(inventory.labels)
    limiter = _RateLimiter(budget.rate, clock, sleep)
    gate = threading.BoundedSemaphore(budget.concurrency)
    units = inventory.units
    attempts = itertools.product(ALL_PORTS if ports is None else ports, range(len(units)))

    def run(ui: int, port: int) -> str:
        # An exception here lands in the future; done() counts it as ERROR, never a timeout.
        limiter.wait()  # the cap applies to connect starts, however the pool schedules workers
        outcome = connect(units[ui].address, port, budget.timeout)
        return outcome if outcome in OUTCOMES else ERROR

    def done(fut, ui: int, port: int) -> None:
        if fut.cancelled() or fut.exception() is not None:
            outcome = ERROR
        else:
            outcome = fut.result()
        acc.record(ui, port, outcome)
        gate.release()

    executor = executor_factory(max_workers=budget.concurrency)
    try:
        while True:
            chunk = list(itertools.islice(attempts, budget.batch))
            if not chunk:
                break
            futures = []
            for port, ui in chunk:
                gate.acquire()
                fut = None
                try:
                    fut = executor.submit(run, ui, port)
                except RuntimeError:  # the interpreter could not start a worker thread
                    fut = None
                if fut is None:
                    acc.record(ui, port, LOCAL)
                    gate.release()
                    continue
                fut.add_done_callback(lambda f, u=ui, p=port: done(f, u, p))
                futures.append(fut)
            concurrent.futures.wait(futures)
            # A done callback runs after its future is marked done: take every permit
            # back so all results are recorded before the batch is judged.
            for _ in range(budget.concurrency):
                gate.acquire()
            for _ in range(budget.concurrency):
                gate.release()
            if reread() != inventory:
                raise InventoryChanged("the droplet inventory changed during the scan; results discarded")
    except KeyboardInterrupt:
        raise Interrupted("interrupted; results discarded") from None
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    return acc


@dataclass(frozen=True)
class Verdict:
    code: int
    reasons: tuple[str, ...]


def verdict(acc: Accounting, expected_units: int, expected_ports: int = MAX_PORT) -> Verdict:
    """Pure: the table and the exit codes of the design."""
    answered = any(acc.open_ports) or any(acc.refused_ports)
    reasons: list[str] = []
    if any(acc.cleanup_problems):
        reasons.append("closing a socket failed after an answer (cleanup problems)")
    if answered:
        if any(acc.open_ports):
            reasons.append("a port accepted a connection")
        if any(acc.refused_ports):
            reasons.append("an answer was received on a port (a refusal)")
    problems: list[str] = []
    if len(acc.labels) != expected_units:
        problems.append("the number of scanned addresses is not the expected number")
    for ui in range(len(acc.labels)):
        c = acc.counts[ui]
        if c[LOCAL]:
            problems.append("a local resource error occurred; it is not a timeout")
        if c[UNREACHABLE]:
            problems.append("the network or host was unreachable")
        if c[ERROR]:
            problems.append("an attempt failed for another reason")
        if acc.unique[ui] != expected_ports:
            problems.append("not every port was attempted exactly once")
    if acc.duplicates or acc.invalid:
        problems.append("a port was recorded twice or out of range")
    # Exact accounting: expected_units * expected_ports attempts, each timing out.
    timeouts = sum(c[TIMEOUT] for c in acc.counts)
    all_timed_out = (
        not answered
        and not problems
        and timeouts == expected_units * expected_ports
        and len(acc.labels) == expected_units
    )
    if answered:
        return Verdict(1, tuple(dict.fromkeys(reasons + problems)))
    if all_timed_out:
        return Verdict(0, ())
    if not problems:
        problems.append("the attempt count does not add up")
    return Verdict(2, tuple(dict.fromkeys(problems)))


# --------------------------------------------------------------------- output


def render(
    acc: Accounting,
    result: Verdict,
    budget: Budget,
    control_ms: int,
    expected: int,
) -> list[str]:
    lines = [
        "zero-ports-check: TCP only; observed from this network only; a point in time",
        f"connectors expected: {expected}",
        (
            f"timeout {budget.timeout:g} s, concurrency {budget.concurrency}, "
            f"control round trip {control_ms} ms"
        ),
    ]
    for ui, label in enumerate(acc.labels):
        c = acc.counts[ui]
        errors = c[LOCAL] + c[UNREACHABLE] + c[ERROR]
        lines.append(
            f"{label}: attempted {acc.unique[ui]}, timeouts {c[TIMEOUT]}, "
            f"answers {c[OPEN] + c[REFUSED]}, errors {errors}"
        )
        if acc.cleanup_problems[ui]:
            lines.append(f"{label}: cleanup problems: {acc.cleanup_problems[ui]}")
        if acc.open_ports[ui]:
            lines.append(f"{label}: open ports: " + ", ".join(map(str, sorted(acc.open_ports[ui]))))
        if acc.refused_ports[ui]:
            lines.append(
                f"{label}: ports that answered with a refusal: "
                + ", ".join(map(str, sorted(acc.refused_ports[ui])))
            )
    if result.code == 0:
        lines.append("verdict: PASS: no answer was received on any port (TCP, this network only)")
    elif result.code == 1:
        lines.append("verdict: FAIL: an answer was received")
        lines.extend(f"  {r}" for r in result.reasons)
    else:
        lines.append("verdict: CANNOT TELL")
        lines.extend(f"  {r}" for r in result.reasons)
    return lines


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass
class ReportTarget:
    """A validated, already-open parent directory and a file name inside it."""

    dir_fd: int
    name: str


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)


def _inside_repo(dir_fd: int) -> bool:
    """Walk the physical ancestry of an open directory; True if the repository is on the way.

    Uses descriptors only (no path is re-resolved), so a path swapped after validation cannot
    change the answer. Any doubt (an unreadable ancestor, absurd depth) counts as inside.
    Limits: a descriptor pins a directory object, not its place in the tree, so callers re-ask
    this just before and just after writing; and a bind mount of a repository subdirectory
    elsewhere has a different ancestry and is not seen.
    """
    root = os.stat(_repo_root())
    root_id = (root.st_dev, root.st_ino)
    cur = os.dup(dir_fd)  # owned: always closed in finally
    up = -1  # owned only while it is open and not yet promoted to cur
    try:
        for _ in range(4096):
            st = os.fstat(cur)
            if (st.st_dev, st.st_ino) == root_id:
                return True
            up = os.open("..", _DIR_FLAGS, dir_fd=cur)
            up_st = os.fstat(up)
            if (up_st.st_dev, up_st.st_ino) == (st.st_dev, st.st_ino):
                return False  # reached the filesystem root
            old, cur, up = cur, up, -1  # ownership moves before anything else can fail
            os.close(old)
        return True
    except OSError:
        return True
    finally:
        if up >= 0:
            os.close(up)
        os.close(cur)


def close_report_target(target: ReportTarget) -> None:
    if target.dir_fd >= 0:
        try:
            os.close(target.dir_fd)
        except OSError:
            pass
        target.dir_fd = -1


def _open_plain_directory(path: str) -> int:
    """Open a directory by walking every component with O_NOFOLLOW: a symlink anywhere on the way
    (not only the last component) is refused. Returns -1 on any failure."""
    cur = -1
    try:
        cur = os.open("/" if path.startswith("/") else ".", _DIR_FLAGS)
        for part in path.split("/"):
            if part in ("", "."):
                continue
            nxt = os.open(part, _DIR_FLAGS | os.O_NOFOLLOW, dir_fd=cur)
            os.close(cur)
            cur = nxt
        result, cur = cur, -1
        return result
    except OSError:
        return -1
    finally:
        if cur >= 0:
            os.close(cur)


def check_out_path(raw: str) -> ReportTarget:
    """Validate before any network use and keep the parent open: outside the repository, a plain
    (non-symlink) directory, and no existing file. The caller must close_report_target()."""
    expanded = os.path.expanduser(raw)
    name = os.path.basename(expanded)
    if name in ("", ".", ".."):
        raise CheckError("the report path has no file name")
    parent = os.path.dirname(expanded) or "."
    dir_fd = _open_plain_directory(parent)
    if dir_fd < 0:
        raise CheckError("the report directory does not exist or is not a plain directory")
    exists = True
    kept = False
    try:
        if _inside_repo(dir_fd):
            raise CheckError("the report path is inside the repository; refused")
        try:
            os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            exists = False
        except OSError:
            exists = True  # cannot tell: treat as present and refuse
        if exists:
            raise CheckError("the report path already exists; not overwriting")
        kept = True
    finally:
        if not kept:
            os.close(dir_fd)
    return ReportTarget(dir_fd, name)


def write_report(target: ReportTarget, lines: list[str]) -> None:
    """Create the file through the pinned directory. The directory is checked against the
    repository just before creating and again after writing; if it moved in, the file is removed."""
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    if _inside_repo(target.dir_fd):
        raise CheckError("the report directory is inside the repository; refused")
    failed = False
    try:
        fd = os.open(target.name, flags, 0o600, dir_fd=target.dir_fd)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fd = -1
                fh.write("\n".join(lines) + "\n")
        finally:
            if fd >= 0:
                os.close(fd)
    except (OSError, ValueError):
        failed = True
    if failed:
        raise CheckError("the report could not be written")
    if _inside_repo(target.dir_fd):
        try:
            os.unlink(target.name, dir_fd=target.dir_fd)
        except OSError:
            pass  # the fixed message below is raised either way
        raise CheckError("the report directory moved inside the repository; the report was removed")


# ----------------------------------------------------------------------- main


@dataclass
class Hooks:
    """Test seams. None of these is reachable from the command line."""

    base_url: str = API_ORIGIN
    address_ok: Callable = default_address_ok
    connect: Callable[[str, int, float], str] = tcp_connect
    control_connect: Callable[[str, int, float], None] | None = None
    control_target: tuple[str, int] = CONTROL_TARGET
    budget: Budget = field(default_factory=Budget)
    ports: range | list | None = None  # None is production: every port, 1 to 65535
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    executor_factory: Callable = concurrent.futures.ThreadPoolExecutor
    transport_factory: Callable[[str], object] | None = None
    getrlimit: Callable = resource.getrlimit

    def effective_ports(self):
        return ALL_PORTS if self.ports is None else self.ports


def _default_control(host: str, port: int, timeout: float) -> None:
    with socket.create_connection((host, port), timeout):
        pass


def positive_control(hooks: Hooks) -> int:
    fn = hooks.control_connect or _default_control
    start = hooks.clock()
    failed = False
    try:
        fn(hooks.control_target[0], hooks.control_target[1], hooks.budget.timeout)
    except OSError:  # any control failure means the local path cannot be trusted
        failed = True
    if failed:
        raise CheckError("the positive control failed; this network path cannot be trusted")
    return max(0, round((hooks.clock() - start) * 1000))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zero_ports_check.py",
        description="External zero-open-ports check for the connectors. Targets come only "
        "from the DigitalOcean API (token in DIGITALOCEAN_TOKEN); no address can be given.",
    )
    parser.add_argument(
        "--expect-connectors",
        type=int,
        required=True,
        metavar="N",
        help="how many tagged project droplets must exist (N >= 1)",
    )
    parser.add_argument("--region", default="tor1", help="region of the baseline tag (default tor1)")
    parser.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="write the report here (mode 0600, never overwrites, outside the repository)",
    )
    return parser


def main(argv=None, *, env=None, hooks: Hooks | None = None, stdout=None) -> int:
    out = stdout if stdout is not None else sys.stdout
    hooks = hooks or Hooks()
    env = os.environ if env is None else env
    try:
        args = build_parser().parse_args(argv)
        return _run(args, env, hooks, out)
    except InventoryChanged as exc:
        print(f"zero-ports-check: {exc}", file=out)
        return 2
    except Interrupted as exc:
        print(f"zero-ports-check: {exc}", file=out)
        return 2
    except CheckError as exc:
        print(f"zero-ports-check: {exc}", file=out)
        return 2
    except KeyboardInterrupt:
        print("zero-ports-check: interrupted; results discarded", file=out)
        return 2
    except _INTERNAL_ERRORS:  # never print a traceback: it could carry request data
        print("zero-ports-check: an internal error occurred; cannot tell", file=out)
        return 2


def _run(args, env, hooks: Hooks, out) -> int:
    if args.expect_connectors < 1:
        raise CheckError("--expect-connectors must be at least 1")
    target = check_out_path(args.out) if args.out else None
    try:
        return _run_checked(args, env, hooks, out, target)
    finally:
        if target is not None:
            close_report_target(target)


def _run_checked(args, env, hooks: Hooks, out, out_target) -> int:
    expected = args.expect_connectors
    token = env.get(TOKEN_ENV, "")
    check_nofile(hooks.budget.concurrency, hooks.getrlimit)
    if hooks.transport_factory is not None:
        transport = hooks.transport_factory(token)
    else:
        transport = ApiTransport(token, hooks.base_url)

    def fresh() -> Inventory:
        return discover(transport, expected, args.region, hooks.address_ok)

    inventory = fresh()
    control_ms = positive_control(hooks)
    acc = scan(
        inventory,
        hooks.connect,
        hooks.budget,
        reread=fresh,
        clock=hooks.clock,
        sleep=hooks.sleep,
        executor_factory=hooks.executor_factory,
        ports=hooks.effective_ports(),
    )
    # Completeness is judged against the constant, not against whatever range was generated.
    expected_ports = MAX_PORT if hooks.ports is None else len(hooks.ports)
    result = verdict(acc, len(inventory.units), expected_ports)
    lines = render(acc, result, hooks.budget, control_ms, expected)
    code = result.code
    if out_target is not None:
        try:
            write_report(out_target, lines)
        except CheckError:
            if code == 0:
                # A pass nobody can read back is not reported as a pass.
                result = Verdict(2, ("the report could not be written",))
                code = 2
                lines = render(acc, result, hooks.budget, control_ms, expected)
            else:
                # An answer stays exit 1: it is the stronger signal.
                lines.append("the report could not be written")
    for line in lines:
        print(line, file=out)
    return code


if __name__ == "__main__":
    sys.exit(main())
