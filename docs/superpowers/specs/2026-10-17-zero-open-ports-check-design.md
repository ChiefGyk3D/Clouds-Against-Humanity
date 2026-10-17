# External zero-open-ports check: design

Date: 2026-10-17. Issue #91 (stage 1 hardening). Status: design, revised once after an adversarial review (Codex, 2026-10-17). Nothing built.

## What it must prove

The connectors have no public inbound path. The cloud firewall rules, the host firewall (#90) and the plan policy (#88) say so from the inside. This check says it from the outside: from a machine that is not in the VPC, every TCP port on every connector's public address gives no answer at all, as seen from that network.

It is an operator check, run by hand after any change to a firewall or a droplet. It is not run in CI, for the same reason `scripts/plan_noop_check.py` is not: it needs live addresses and a credential.

## The line it must not cross

It scans only machines the maintainer owns. A port scanner that takes an address from an argument or a file is a tool that can be pointed at anyone, so **there is no way to give it an address.** The review's first finding was that an "I own these" flag is a bypass, not a rail. What remains:

1. **Targets come only from the DigitalOcean API, read-only, and only after discovery is complete.** The script builds the request URLs itself (fixed HTTPS origin and path, the tag filter as a query parameter) and never follows a URL the API returns.
2. **Three independent facts must agree** before an address is a target: the droplet carries the baseline tag (`cah-baseline-<region>`), the droplet is a member of the project (`GET /v2/projects/{id}/resources` lists its `do:droplet:<id>` URNs; the project is found by the name `clouds-against-humanity`), and the operator states the expected number of connectors with `--expect-connectors N`. The intersection of tag and project membership must contain exactly N droplets, with N at least 1. A droplet from another project that someone tagged is not in the project; a project droplet without the tag is not scanned and is reported as a mismatch (exit 2). N is a count, not an inventory, so no droplet id or address is ever written down.
3. **Reserved IPs are public paths too.** The script also lists reserved IPv4 and IPv6 addresses (`/v2/reserved_ips`, `/v2/reserved_ipv6`) and treats any that is assigned to a target droplet as one more target (it is ours, and a reserved address can be reassigned). If the listing cannot be completed, the run is "cannot tell". A public IPv6 address on a droplet fails the run (the #89 test and the plan policy keep it absent) instead of being scanned.
4. **Ownership can lapse during a sweep.** DigitalOcean returns a destroyed droplet's address to its pool. The script re-reads the whole inventory before each batch of ports (bounded batches, see the budget) and once more at the end; any change in the set of droplet ids or addresses aborts with "cannot tell" and discards the results. The runbook says: do not destroy, replace or reassign a connector while the check runs. This narrows the race; it cannot remove it without lifecycle coordination, and the doc says so.
5. **Parsing is strict.** An address must be a JSON string in canonical dotted-quad form, parsed with `ipaddress.IPv4Address` from a `str` only (never an int), and must be `is_global`. Anything else (IPv4-mapped IPv6, an integer, decimal, octal or hex spelling, trailing content, private, loopback, link-local, multicast, reserved) fails the whole discovery.
6. **Discovery completes before any socket opens.** Pagination is followed with locally built requests; a repeated page, a cycle, a total that contradicts the pages, an empty inventory, fewer than N matches, or hitting the page cap is "cannot tell". The test suite asserts zero connect calls after any discovery failure.
7. **The API itself is a trust anchor.** A compromised or lying API response defeats an API-only ownership check, and the doc states it. The rails make the intended use the only easy one; they do not stop someone who edits the script.

## The credential

A **separate read-only token**, in its own Doppler config (maintainer's decision, 2026-10-17), not the Spacelift token. Scopes, from DigitalOcean's API documentation: `droplet:read` and `tag:read` for listing droplets by tag; the project, reserved-IP and reserved-IPv6 listings need their own read scopes (`project:read`, `reserved_ip:read`, and the reserved IPv6 equivalent). The exact names are confirmed in the token form when it is created and written here before the tool ships. Creating the token is the maintainer's step.

Handling: read from `DIGITALOCEAN_TOKEN` (or Doppler); never written to a file, never printed, never in a child process's environment. The HTTP client is `urllib` with proxies explicitly disabled (`ProxyHandler({})`; urllib detects proxies from the environment by default), verified TLS, an exact origin check, and every redirect refused. Errors are fixed sanitised strings: no response body, URL or traceback is ever printed.

## How it decides

For each target it attempts a TCP connect to every port from 1 to 65535, exactly once, with no retries.

| Outcome of one port | Meaning |
|---|---|
| Connection succeeds | Open. Fail. |
| Connection refused (a reset came back) | **Fail the silence criterion.** On DigitalOcean a blocked packet is expected to get no reply; a reset or ICMP error means something answered. It may be the droplet or a device on the path (an ISP, a local firewall, a captive network); the report says "an answer was received", not "the droplet replied". |
| Timeout | The expected result: no answer within the deadline. |
| A local error (too many open files, no local addresses, no buffer space, a worker failure), or network or host unreachable | **Cannot tell.** Never counted as a timeout. |

**Exit codes:** 0 only if every expected target and every port was attempted exactly once and every attempt timed out; 1 if any port answered; 2 for everything else (discovery problems, a local error, an inventory change, interruption, a report that could not be written). When a run has both an answer and an error, it exits 1 and lists both; a run never exits 0 with any attempt unaccounted for. The count of attempts is checked against N x 65,535 before the verdict.

### The scan budget (numbers, so it can be reviewed)

Defaults: global concurrency 512, connect timeout 2.0 seconds started when the attempt actually begins, an overall rate cap of 1,500 attempts a second, batches of 4,096 ports with an inventory re-read between batches, sockets closed on every path (success, refusal, timeout, error, cancellation). For an all-timeout target the time is about ceil(65,535 / 512) x 2 s, roughly 4.3 minutes a target, so about 9 minutes for two connectors. Refusals return immediately, so concurrency alone does not bound the rate; the rate cap does. Scanning 65,535 destination ports does not need 65,535 local ports at once: the demand is the concurrency times the socket lifetime. The script raises a clear "cannot tell" if `RLIMIT_NOFILE` is below the concurrency plus a margin instead of failing mid-run. A slow path could turn real answers into timeouts, so the report shows the median connect time of a positive control (see below) and the timeout used.

**Positive control.** Before the sweep, one connection to an address the operator must be able to reach (the Twingate service's public endpoint on 443, or the DigitalOcean API the script already uses) proves the local path works and gives a baseline round-trip time. If it fails the run is "cannot tell".

### What it does not prove

- **UDP.** An absence of reply is `open|filtered`. The check is TCP only and says so in its output. A UDP spot check with `nmap -sU` against a few ports is a manual extra in the runbook.
- **One vantage point.** A silent result is an observation from the operator's network. A middlebox that swallows SYNs would make an exposed port look silent, and an upstream filter could hide an open one. **A clean result is only claimed after a second run from a different network** (a phone hotspot is enough); the runbook requires it after a firewall change, and the output prints "observed from this network only".
- **Time.** A point-in-time result. The standing guard is the plan policy, the host firewall and the tests; this is the occasional proof.

## Output

Per target a label (`connector-1`, `connector-2`), never the address. Counts of ports attempted, timeouts, answers and errors; the list of answering port numbers (a port number is not an identifier); the timeout and concurrency used; the positive control's round-trip time; the verdict. `--out` writes a report with mode 0600 and refuses to overwrite; the path defaults to outside the repository. A failure to write the report is exit 2.

## Shape of the code

`scripts/zero_ports_check.py`, standard library only:

- `discover(transport, expected)`: all API reads, strict parsing, intersection, reserved IPs, returns an immutable inventory or raises a fixed-message error. `transport` is a seam that wraps the real `urllib` opener, so the tests can run the real redirect and proxy machinery against a local server (a test-only base URL parameter that is absent from the command line).
- `scan(inventory, connect, budget)`: the connect function is a parameter; accounting of every attempt; resource errors distinguished from timeouts; re-reads the inventory between batches.
- `verdict(accounting)`: a pure function implementing the table and the exit codes above.
- `main`: argument handling (`--expect-connectors`, `--out`, no address argument of any kind), the positive control, the budget checks.

## Tests (hermetic, `tests/test_zero_ports_check.py`)

- Discovery: pagination cycle, repeated page, total contradicting pages, empty inventory, fewer than N matches, cap hit, a returned next-URL pointing elsewhere (never followed), a redirect to another host (refused, token never sent there, using the real urllib redirect handling against a local server), a proxy environment variable set (ignored), invalid JSON, an oversized body, a non-string address, an integer address, IPv4-mapped IPv6, decimal, octal and hex spellings, private, loopback and reserved addresses, a public IPv6 address on a droplet, a tagged droplet outside the project, a project droplet without the tag, a reserved IP attached to a target. **In every discovery failure, zero connect calls are made.**
- Scan: loopback server (bound and listening) is found open; a port bound but not listening is refused and counts as an answer (the socket stays bound so no port-reuse race); a connect function that always times out gives exit 0 only when every attempt is accounted for; a missing final port, a duplicated port or an interrupted run is exit 2; an `EMFILE`, `EADDRNOTAVAIL` or `ENOBUFS` is exit 2 and not a timeout; the measured peak concurrency never exceeds the budget and the attempt rate never exceeds the cap (a fake clock); sockets are closed on every path (a counting fake); an inventory change between batches discards the results.
- The token never appears in any output, exception text, or child environment.
- Mutations: counting a refusal as a pass fails a test; dropping the cap fails a test; skipping the project-membership intersection fails a test.

## Docs

`docs/stages/01-access.md` verify section: when to run it, the command as a full line, the second-network requirement, the UDP manual extra, what each exit code means, the do-not-destroy-during-a-scan rule. `docs/wiki/Droplet-Hardening.md`: a paragraph on what it proves and what it does not. `docs/settings.json` is untouched (no setting).

## Decisions

1. **Decided (maintainer, 2026-10-17): a separate read-only token** in its own Doppler config.
2. **Proceeding on this default unless the maintainer says otherwise:** a full 65,535-port sweep, because a partial port set weakens a claim of "zero"; about 4.3 minutes a target at the defaults. A smaller set can be an explicit option later.
3. **Proceeding on this default unless the maintainer says otherwise:** the second-network run is part of the runbook after any firewall change, as the review required for any "clean" claim.

## Residual risks

A scan that reports clean from two networks is strong evidence, not a proof. The tool is a port scanner with a safety rail, not a guarantee against misuse by someone who edits it. An attacker with enough access to add tags and project membership in the maintainer's own account is already inside the trust boundary. All three are written down in the guide.
