# External zero-open-ports check: design

Date: 2026-10-17. Issue #91 (stage 1 hardening). Status: design for review, nothing built.

## What it must prove

The connectors have no public inbound path. The cloud firewall rules, the host firewall (#90) and the plan policy (#88) say so from the inside. This check says it from the outside: from a machine that is not in the VPC, every TCP port on every connector's public address gives no answer at all.

It is an operator check, run by hand after any change to a firewall or a droplet. It is not run in CI, for the same reason `scripts/plan_noop_check.py` is not: it needs live addresses and a credential.

## The line it must not cross

It scans only machines the maintainer owns. A port scanner that takes an address from an argument is a tool that can be pointed at anyone. So:

1. The default source of targets is the DigitalOcean API, read-only, never a typed address. The script lists droplets, keeps only those carrying the baseline tag (`cah-baseline-<region>`), and scans their public IPv4 addresses. A droplet without the tag, or any address the API did not return, is never scanned.
2. An explicit target list (a file) exists for the one case where the API is not reachable, and it needs a flag that says the operator owns every address in it. It is for the operator's own use and is refused unless every address is public IPv4 (never loopback, private, link-local, multicast, reserved or a range).
3. A hard cap on targets (ten), on concurrency and on the connect timeout, so a bug cannot turn it into a flood.
4. The token comes from `DIGITALOCEAN_TOKEN` in the environment (or Doppler, per the repository's rule that a keyed tool accepts a local environment variable or Doppler). It is a read-only droplet token, never written anywhere, never printed, never sent to any host but the DigitalOcean API, and redirects are refused so it cannot be carried to another host.

## How it decides

For each target it attempts a TCP connect to every port from 1 to 65535 with a short timeout, a bounded number at a time.

| Outcome of one port | Meaning here |
|---|---|
| Connection succeeds | Open. Fail. |
| Connection refused (a reset came back) | **Fail too.** A closed port that answers means the packet reached the host and the host replied: the path is open even though nothing listens. A dropped packet gives silence. |
| Timeout | The expected result: nothing answered. |
| Network unreachable, host unreachable, or any other error | Cannot tell. Exit 2, not a pass. |

Exit codes follow SAFO's audit: 0 clean, 1 a port answered, 2 cannot tell. Anything other than every port timing out is not a clean result.

### What it does not prove

- **UDP.** An absence of reply is `open|filtered`; a connect cannot tell them apart, and a full UDP sweep is slow and unreliable. The check is TCP only and says so in its output. The Twingate connector is outbound-only and the cloud firewall has no inbound rule for any protocol; a UDP spot check with `nmap -sU` against a few ports is a manual extra in the runbook, not part of this tool.
- **IPv6.** The droplets have none (the #89 test and the plan policy keep it so). The check lists the droplet's addresses from the API and fails if the API reports a public IPv6 address, instead of scanning it.
- **One vantage point.** The result is as seen from the operator's network. An upstream filter at that network could make a port look closed that is open from elsewhere. The runbook asks for a second run from a different network (a phone hotspot is enough) after a change.
- **Time.** It is a point-in-time result. The standing guard is the plan policy and the tests; this is the occasional proof.

## Output

Per target, a label (`connector-1`, `connector-2`), never the address: public addresses of the infrastructure do not belong in a log, a pull request or a wiki page. Counts of ports probed, timeouts, answers and errors, the list of answering port numbers (a port number is not an identifier) and the verdict. A report may be saved with `--out`, which refuses to overwrite and writes mode 0600; the saved file also carries labels, not addresses. Nothing the script writes is committed (the path is outside the repository by default).

## Shape of the code

`scripts/zero_ports_check.py`, standard library only, in the style of `scripts/cost_check.py` and `scripts/plan_noop_check.py`:

- `fetch_targets(token, opener)`: GET the droplets of the project's tag from `api.digitalocean.com`, a redirect-refusing opener, a bounded response size, pagination capped and followed only to the same host. Validates every address with `ipaddress`, keeps public IPv4 only, refuses an API response that includes anything surprising (a non-list, a missing field) as "cannot tell".
- `scan(target, ports, connect, concurrency, timeout)`: the connect function is a parameter so tests never touch a real network.
- `verdict(results)`: pure function, the table above.
- `main`: argument handling, the consent flag, the caps, the exit code.

## Tests (hermetic, in `tests/test_zero_ports_check.py`)

- A loopback server on an ephemeral port: the scan of `127.0.0.1` with the loopback allowance on (a test-only parameter, absent from the command line) finds it open. A closed loopback port answers with a reset and counts as a failure. A connect function that always times out gives a clean verdict.
- A hostile API: a redirect to another host is refused and the token is never sent there; an oversized body, invalid JSON, a droplet with a private or loopback "public" address, a public IPv6 address, more droplets than the cap, and an untagged droplet are each refused or skipped as specified.
- The token never appears in any output, error or exception text.
- The target file path: needs the ownership flag, rejects ranges, private and reserved addresses, duplicates beyond the cap.
- Mutations: swapping "refused counts as a failure" to "refused counts as a pass" fails a test; dropping the cap fails a test.

## Docs

`docs/stages/01-access.md` verify section: when to run it, the command as a full line, the second vantage point, the UDP manual extra, and what each exit code means. `docs/wiki/Droplet-Hardening.md`: one paragraph on what the check proves and what it does not. `docs/settings.json` is untouched (no setting).

## Decisions for the maintainer

1. **Decided (maintainer, 2026-10-17): a separate read-only token**, in its own Doppler config, not the Spacelift token. It needs only the scope that lists droplets (the exact minimum scope is confirmed in the design review and recorded here before the tool is built). Creating it is the maintainer's step; the tool reads it from `DIGITALOCEAN_TOKEN` or Doppler and never from a file in the repository.
2. Is a full 65,535-port TCP sweep acceptable from the home connection (about two minutes per target at the proposed concurrency) or should the default be a smaller set with the full sweep as an option?
3. Run it from home, or also from a second vantage point as a standing step after every firewall change?

## Residual risks

A scan that reports clean from one network is evidence, not a proof. The tool is a port scanner with a safety rail, not a guarantee against misuse by someone who edits it; the rail is to make the intended use the only easy one. Both are written down in the guide.
