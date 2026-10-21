# Clouds Against Humanity: Public Edge (DMZ)

Status: DRAFT for review; the section 9 decisions were ruled on 2026-10-19 (decision 4 still PROVISIONAL, decision 9 not ruled), nothing is approved to build or spend yet. Date: 2026-10-19. Issue: #118 (epic #72). Source brief: [the 2026-10-12 edge handoff](../plans/2026-10-12-edge-dmz-handoff.md), sections 3 and 4.
Tooling: OpenTofu throughout.
Scope: the public edge only: one internet-facing host in its own VPC, how it is hardened, how it logs home, and what it costs under four different shapes. This is a design, not an approval. Nothing here costs money, changes a stack or moves a ceiling until the maintainer picks an option in section 5 and approves it. The handoff says the edge lands past the $30 ceiling and the ceiling is not raised by default, so this document lays out options and recommends one; it does not choose for him.

Vendor facts below carry a URL and the date they were read (2026-10-19). Anything I could not verify is marked UNVERIFIED and carries no number. Facts from the repository's own price tables carry the table's retrieval date instead. Section 9 lists what is still open.

## 1. Purpose

Put a small set of internet-facing radio and measurement services on one immutable host, in a VPC of its own, so the core environment keeps zero inbound. The services are Reticulum transport with an LXMF propagation node, i2pd, a Meshtastic MQTT broker over TLS, and an authenticated iperf3 server used to compare a direct path to a Twingate path.

Goals:

- One public host in a separate VPC with no peering to core, tagged `rns-dmz`.
- A public address that survives a rebuild (a reserved IP).
- No SSH, no Twingate connector and no admin path on the host. Every change is a pull request, a Spacelift plan and a rebuild, and a rebuild is the only recovery. The Droplet Console is not a break-glass path in this design (section 4.2).
- Inbound limited to the four service ports the handoff lists, with iperf3 restricted to named sources.
- Logs from the edge land in the stage 2 path at home without a direct line to the SIEM.
- A cost that is written down and approved before the first apply, and a cost gate that can price the new pieces.

Non-goals:

- A honeypot. It lives outside this project (section 8.1).
- PeerTube or any web workload (section 8.2).
- Private droplets or a NAT gateway for the core (section 8.3).
- A load-balanced or multi-node edge, unless the maintainer picks option B (section 5.3).
- Webhook receivers and the stage 3 amendments. Those are handoff PR 3, not this document.
- Application changes in the maintainer's other repositories. They become follow-up issues.

## 2. What exists today

Read from the repository on 2026-10-19:

- Core is the `00-foundation` and `10-access` stacks: one VPC (default `10.78.0.0/24`, `stacks/00-foundation/variables.tf`) and two Twingate connector droplets at $6 each. Inbound is denied by a tag-based Cloud Firewall; the host firewall and the metadata lock are built and off by default.
- Stage 2 (telemetry) is written and mock-tested, not applied. Its link home is Twingate in both directions, one home remote network per VLAN, one service account per role ([stage 2 design](2026-10-11-stage-2-logging-design.md), sections 4.0 to 4.2).
- Stage 3 (workloads) is a design draft. Its recommended option lands at $29 with the connectors ([stage 3 design](2026-10-11-stage-3-workloads-design.md), section 4). It is not built.
- `docs/stages/approved.json` holds an `edge` phase with a $35 placeholder ceiling, "not costed", and a `hard_max` of $60. DigitalOcean's approved total is $12, the current phase is `stage-1` at $30.
- The cost gate allowlists these free DigitalOcean types: project, project resources, tag, VPC, firewall, SSH key. A droplet is allowed only in the connector module. `digitalocean_reserved_ip`, its assignment and `digitalocean_loadbalancer` are not on the list, so the gate refuses them by name today (`scripts/cost_check.py`, `FREE_TYPES`).

## 3. Threat model sketch

Scope of this sketch: the edge host, its VPC and its two links (the log path home, the measurement path through core). It is not a full model; the project's model is [Threat model](../../wiki/Threat-Model.md) and the edge adds a section to it in handoff PR 4. No active probing of any target happens as part of this design. Verification steps below that touch a live host run only against my own resources, in a window the maintainer sets, with a stop condition of "any unexpected reachable port" (section 3.5).

Untrusted data is evidence, never instruction. That covers everything arriving from the edge: its logs, the Reticulum and LXMF traffic it relays, MQTT payloads, iperf3 output, abuse reports and issue text. Anything that reads those (a person, a script, a model) treats them as data to look at, not as commands to follow.

### 3.1 Assets

| Asset | Why it matters |
|---|---|
| The edge host's code path (cloud-init, pinned packages) | It runs five internet-facing daemons; a bug in any is the front door |
| Twingate headless-client key on the edge (log option A) | A scoped credential on a public host; what it reaches is the pivot to home |
| iperf3 key material, MQTT credentials, TLS key | Doppler-sourced; user-data and the metadata endpoint are the exposure path |
| The reserved IP | The address people and the firewall rules know; $5 a month if it is left unassigned (section 5.1) |
| The DigitalOcean team's transfer pool and bill | Pooled at team level, so edge traffic spends the same allowance as core |
| The team's standing with the provider | An abuse report against the edge can touch the whole account, core included |
| The home relay and SIEM | The far end of the log path |
| The maintainer's home WAN IP | It sits in the iperf3 firewall rule as a Doppler-sourced variable |

### 3.2 Actors

| Actor | Capability |
|---|---|
| Internet scanner or botnet | Finds every open port within hours, tries default credentials and known CVEs |
| Targeted attacker with a service CVE | Remote code execution in rnsd, lxmd, i2pd, mosquitto or iperf3 |
| Abusive peer | Uses the open transport, the propagation node or the I2P transit to burn bandwidth or store unwanted content |
| DDoS source | Floods the reserved IP |
| Supply chain | A bad package or a bad pin in cloud-init |
| A pull request author | Edits cloud-init or firewall rules; covered by the existing review and plan policy, not new here |

### 3.3 Trust boundaries

| Boundary | Rule |
|---|---|
| Internet to edge | Four service ports only. Everything else dropped by the Cloud Firewall and again by host nftables |
| Edge to core | No private east-west path and no admin path: separate VPC, no peering, no shared tag, no shared secret, no shared Doppler config. One public flow is allowed on purpose, and it is part of the monitoring design: the iperf3 measurement path, where a home client goes through Twingate to a core connector and the connector forwards to the edge's public IP on 5201 (section 4.3). The edge firewall names its sources |
| Edge to home | One Twingate service account, one resource: the ingest endpoint on the home relay. Never the SIEM. The relay is a security boundary of its own, and its controls are an approval prerequisite (section 4.6.1), not an assumption |
| Repo to edge | cloud-init rendered by OpenTofu. One bootstrap token (a short-lived, read-only Doppler service token for an edge-only config) is the only secret-shaped value in user-data; risk 6 says how it is handled and which copies of it remain |
| Edge account to honeypot | There is no path. The honeypot is another account (section 8.1) |

### 3.4 Abuse cases

1. A scanner finds the iperf3 port and uses the server as a free bandwidth source.
2. An attacker exploits a daemon, gets a shell as the service user and reads the Twingate key.
3. An attacker with that key tries every resource the group can see.
4. A peer pushes the propagation node past its disk or the I2P transit past its share, and the transfer bill climbs.
5. Someone floods the reserved IP until the provider drops traffic to it.
6. An abuse report about relayed content reaches the provider, and the provider acts on the team.
7. A bad pin or a poisoned package lands through cloud-init on the next rebuild.
8. User-data secrets are read from the metadata endpoint by a compromised service.
9. IPv6 is on, and a v4-only rule set leaves the v6 side open.

### 3.5 Ranked risks

Ranked by impact times how easy the first step is. Each has a mitigation and a verification that can be run without a probe of anything I do not own.

| # | Risk | Mitigation | Verification |
|---|---|---|---|
| 1 | Service RCE, then the log credential (abuse cases 2 and 3) | The service account sees one resource, one endpoint, on a relay built to the section 4.6.1 prerequisites (its own VLAN and host, no route back to the edge, unprivileged parser, bounded input); pfSense on that VLAN repeats the single port; services run as unprivileged users under systemd hardening; the key is readable by the client's user only | A test that lists the group's Twingate resources and fails if there is more than one; the section 4.6.1 tests, run from the edge identity and from a compromised-relay model; a pfSense rule review |
| 2 | Bandwidth and bill abuse (abuse case 4, and 1) | i2pd transit and share caps, lxmd storage and transfer limits, iperf3 source rules, a billing alert set before the first apply, `-n` byte caps on every test | The usage page after week one against the section 5.7 figures; a rebuild test that shows the disk limit holds |
| 3 | Pivot from edge to core | Separate VPC, no peering (DigitalOcean's VPCs do not reach each other without peering, section 9), no shared tag, no shared Doppler config | A plan policy that denies any peering resource and any core tag on an edge resource, with policy tests next to the existing ones; the stack test asserts the edge VPC's CIDR does not overlap core's |
| 4 | Provider acts on the account after an abuse report (abuse case 6) | Private MQTT broker by default; propagation-node storage capped; an abuse contact that is read; the decision in section 7 about a separate team | Not testable in advance. The check is a calendar item: read the abuse inbox weekly. Residual risk accepted until decided |
| 5 | Supply chain or unpinned software | Pin by version and checksum, current releases only, OS packages through unattended upgrades, a scheduled monthly rebuild because the host cannot be patched by hand | A test that fails on an unpinned package name in the cloud-init template; a version report in the log stream |
| 6 | Secrets in user-data (abuse case 8) | Depends on the metadata-endpoint restriction from handoff PR 1. user-data carries exactly one recognised secret-shaped field, the Doppler bootstrap token, following the pattern already in `modules/twingate-bootstrap/variables.tf` (`log_shipping_bootstrap_token`): short-lived, read-only, scoped to an edge-only config, written to a root-only file that first boot deletes before using it, and revoked right after the build. Fetched credentials (iperf3 key, MQTT passwords, TLS key, Twingate service key) are never in user-data. The token is still in OpenTofu state, the provider API, the metadata endpoint and cloud-init's own copy of user-data until it expires or is revoked, and a monthly rebuild mints a new one each time. The shortest Doppler token lifetime is UNVERIFIED | A template test that allows exactly one field matching the bootstrap-token shape and fails on any other secret-shaped value or any fetched-credential name; a runbook step that revokes the token after each build; a first-boot check that the temp file is gone |
| 7 | Flood and null-route (abuse case 5) | DigitalOcean's L3 and L4 protection covers droplets and assigned reserved IPs at no charge (section 9). It does not cover layer 7, and past its capacity DigitalOcean blackholes the target IP | Accepted. The measurement path shows the outage and ntfy alerts; no verification beyond that |
| 8 | IPv6 left open (abuse case 9) | Cloud Firewall rules and nftables written for both families; if IPv6 is off on the droplet, a test says so | The existing `test_ipv6_closed.py` pattern extended to the edge; the zero-open-ports check runs against the v6 address too |
| 9 | Log path abused to inject content into the SIEM | The relay treats edge logs as untrusted input: parse, size-limit, never execute, never feed a triage model as instruction | A relay-side test with an oversized and a hostile line |

### 3.6 Residual risk

A public host running five daemons will be scanned and sometimes attacked. The design accepts that the edge can be compromised and limits what that buys: no path to core, one narrow path home, no admin path to steal, and a rebuild from code as the recovery. What it does not remove: loss of the public IP to a flood, an abuse action against the team, and a zero-day in a daemon that exposes the service user's files until the rebuild.

## 4. Architecture

```
                         INTERNET
                            |
        tcp 4242 (Reticulum), i2pd port tcp+udp, tcp 8883 (MQTT TLS),
        tcp 5201 (iperf3) from named sources only
                            |
                    reserved IP (203.0.113.10 in examples)
                            |
  +-------------------- rns-dmz VPC (no peering) --------------------+
  |   edge droplet, tag rns-dmz, nftables default-drop               |
  |   rnsd + lxmd, i2pd (SAM on loopback), mosquitto, iperf3         |
  |   no SSH, no connector, config only from cloud-init              |
  +---------------------------|--------------------------------------+
                              | outbound only: Twingate headless client
                              v
                  Twingate -> home relay ingest port (one resource)

  core VPC (zero inbound) ... connectors dial 203.0.113.10:5201 for the ZTNA path
```

The diagram is text on purpose: the wiki's architecture diagram with zones is handoff PR 4.

### 4.1 The DMZ VPC

A `digitalocean_vpc` named `rns-dmz` in the same region as core, with a CIDR that does not overlap core's (core defaults to `10.78.0.0/24`; the handoff suggests `10.30.0.0/24`; the stack's validation rejects an overlap with `reserved_ranges`). It is a VPC, not a subnet, because the VPC is the isolation unit. DigitalOcean says resources in different VPCs cannot reach each other privately unless the VPCs are peered, and VPC ranges in one account cannot overlap (https://docs.digitalocean.com/products/networking/vpc/details/limits/, read 2026-10-19). No peering resource is ever created, and a plan policy denies one.

One droplet, tagged `rns-dmz`, with a role tag as well (`rns-dmz-transport`) so a second host later gets its own rules, and so a DMZ-to-DMZ rule defaults to deny.

### 4.2 Public versus Twingate

| Surface | Reachable from | How |
|---|---|---|
| Reticulum `TCPServerInterface` (4242 unless config says otherwise) | The internet | Cloud Firewall and nftables |
| i2pd pinned inbound port, TCP and UDP | The internet | Same |
| Meshtastic MQTT over TLS, 8883 | The internet; authentication required, no anonymous access | Same |
| iperf3, 5201 | The maintainer's home WAN IP and the core connectors' egress addresses only | Source-restricted rule; built-in iperf3 RSA auth on top |
| SSH, any admin port | Nowhere | There is none |
| i2pd SAM | Loopback only | Bound to 127.0.0.1 |
| Log path home | Outbound from the edge | Twingate headless client to one home resource |
| Break-glass | Nowhere | None. Rebuild from code is the only recovery. The Droplet Console is not part of this design: a console login needs a local password, and a standing password that works remotely is the admin path this design removes. Whether the console is available is UNVERIFIED and nothing relies on it. Using it would be a separate decision with an authentication and audit procedure written first |

Nothing on the edge is "reachable only through Twingate" inbound, because the edge has no admin plane. Twingate carries two things: the measurement path to the edge's public address, and the edge's own logs going home.

### 4.3 How it relates to the zero-inbound core

Core keeps zero inbound. The edge does touch core in one place, and it is a change to core: the connector firewall's outbound rules today are the module defaults (TCP 443, 80, 53; UDP 53, 123) plus TCP 30000-31000 and UDP 1-65535 (`stacks/10-access/main.tf`, `extra_outbound_rules`). TCP 5201 is not among them, so the ZTNA half of the measurement path needs one added outbound rule on the connector tag. The module's extra rules are port-only, so the rule is "TCP 5201 to anywhere" unless the module grows an address field. That is a stage 1 change and it belongs in the implementation PR with its own review.

The traffic model, per Twingate's docs (read 2026-10-19):

- A Twingate resource can be "any network address" that is resolvable and routable from the connector, and the page lists IP, CIDR and FQDN without limiting them to private ranges; for public destinations, user traffic "will first be routed to the configured Connector" (https://www.twingate.com/docs/resources).
- The client sets up a tunnel to the connector, the connector forwards traffic to the resource, and relays carry no data. A direct client-to-connector link is preferred and relayed is the backup (https://www.twingate.com/docs/how-twingate-works).
- The connector does not initiate anything on its own. The initiating side is a Twingate client: the maintainer's client for manual runs, or a headless service account at home (say `cah-edge-probe`) for scheduled probes. That identity sits in a group that is granted one resource, `edge-iperf3`, in the cloud remote network whose connectors are the core ones. The resource's address is the edge's public IP, TCP 5201, and UDP 5201 for the UDP probes.

What neither page says, and I give no answer: what source address the edge sees when the connector forwards (the connector's public IP, a NAT address, something else), and whether a UDP resource is supported for the iperf3 UDP probes. Both are UNVERIFIED. They are not variable changes. The iperf3 rule is only narrow because its sources are known. If the edge does not see the core connectors' public addresses, the source set of that rule is wrong, and the choices become an architecture change: accept authentication-only on 5201 with tighter caps, find an address the traffic does present, or drop the ZTNA path and keep the direct one. So the implementation of the ZTNA measurement path is conditional on checking both behaviours first, with a test resource pointed at an address the maintainer owns. The direct path from home does not depend on either and can go first.

This path gives the edge one fact about core: the connectors' public addresses. Those are already public. No secret crosses.

### 4.4 Host hardening, reused from stage 1

Reused unchanged where it applies: one non-root user, no password auth, unattended upgrades with a reboot window that does not collide with the connectors', chrony, a sysctl drop-in, the metadata-endpoint lock, and the default-drop nftables host firewall from handoff PR 1 mirroring the Cloud Firewall. Not reused: the Twingate connector, SSH keys, any inbound admin rule. New: every service runs as its own unprivileged user under systemd sandboxing where it works, and the packages are pinned (risk 5).

Cloud Firewall limits that matter here, read from https://docs.digitalocean.com/products/networking/firewalls/details/limits/ on 2026-10-19: 50 rules per firewall, 10 droplets and 5 tags per firewall, and the firewall is free. One droplet is far under all three. The same page says cloud firewalls cannot be applied to load balancers, which matters for option B.

### 4.5 Services

Per the handoff: `rnsd` with `enable_transport = Yes` and a `TCPServerInterface`; `lxmd` as a propagation node with storage and transfer limits; i2pd with SAM on loopback, a pinned inbound port and capped transit; Mosquitto with TLS and authentication, private broker for the maintainer's nodes by default; iperf3 with `--rsa-private-key-path` and `--authorized-users-path`, key material from Doppler. Option names for Reticulum, lxmd and i2pd have changed between releases, and whether the distro's iperf3 is built with OpenSSL auth support is UNVERIFIED. The implementation PR checks each against the version it pins and records the link, as the handoff requires.

Memory is the open fact. Five daemons on 1 GiB, with no swap, has not been measured. It is the reason section 5 prices a 2 GiB variant.

### 4.6 Logging into the stage 2 path

Option A (recommended, from the handoff): a Twingate headless client on the edge with a service account whose only resource is the ingest endpoint on the home relay, the same pattern as the stage 2 cloud service accounts ([stage 2 design](2026-10-11-stage-2-logging-design.md), section 4.0b). Concretely: a new home remote network and connector for the relay (per section 4.0a's one-per-VLAN rule), a service account `cah-edge-logging` in its own group that holds no other resource, and nothing that reaches the SIEM. The relay forwards into the SIEM, so the edge never has a line to it.

What the credential can reach on paper: the one endpoint. What it can reach in practice depends on the relay, and a narrow Twingate resource proves only that the edge can address one socket. If the ingest service on that socket is exploitable, the relay is the next pivot. So the relay's controls are part of the design, and the design is not approvable without them.

Option B: no log shipping at first, DigitalOcean monitoring only. Nothing to put on a compromised host, and nothing to investigate with afterwards. I do not recommend it, and I list it so the choice is visible.

UNVERIFIED: that the Twingate headless client runs unattended under systemd on a host with no admin path, and what outbound access it needs. The repo's own connector rules cite Twingate's allowlist article for TCP 30000-31000 and UDP to any port (`stacks/10-access/main.tf`); I assume the headless client needs the same, TCP 30000-31000 plus UDP any port, and the matrix below carries that assumption. It is the opposite of a narrow outbound policy. If the assumption is dropped instead, approval is blocked on verified headless-client requirements from Twingate's docs.

#### 4.6.1 Relay prerequisites (approval is blocked until each has an owner and a test)

The ingest protocol (Wazuh agent, syslog, Vector or something else) is an open prerequisite. It is the relay's design, in the home-side work, and nothing here picks it. Whatever it is, the relay must meet these before the edge gets a credential:

- Its own host on its own VLAN, with no route back to the edge or to any other home network.
- A SIEM destination on an allowlist of one address and port, and nothing else outbound.
- An unprivileged parser and forwarder; no shell-capable transformation of any field (no templating or command hooks fed from edge data).
- A bounded queue, a maximum message size and a rate limit, so the edge cannot fill the disk or the SIEM.
- Authenticated ingestion, with the edge identity unable to read what it wrote.
- Credentials separate from every other home service, and from the SIEM's.
- A rebuild procedure from code, so a suspect relay is replaced, not repaired.
- Tests from two positions: from the edge identity (it reaches only the ingest endpoint, and oversized or hostile lines are cut off or dropped), and from a compromised-relay model (the relay host cannot reach the edge, the home LAN or the SIEM beyond its one allowed destination).

#### 4.6.2 Outbound policy

The handoff says outbound starts from what each service needs. This is that matrix, proposed. The Cloud Firewall can filter by port and destination class but not by process, so the host's nftables is the fine-grained layer, matching on the service user (`meta skuid`). Every row is a proposal until the implementation checks it against the pinned version; those I have not read are UNVERIFIED.

| Process or user | Destination class | Protocol and port | Notes |
|---|---|---|---|
| DNS (system resolver) | One named resolver | UDP and TCP 53 | Pinned resolver only, no DoH. Which resolver is UNVERIFIED. Query logging on |
| Package updates (`_apt`, unattended upgrades) | OS mirrors (many addresses) | TCP 80, 443 | Cannot be pinned by address; limited by user |
| Time (chrony) | NTP servers | UDP 123 | Limited by user |
| `rnsd` | None initially | none | Inbound `TCPServerInterface` only, replies ride the stateful rule. No `TCPClientInterface`, so no outbound peers. Adding one is a PR with its destination written down |
| `i2pd` | I2P peers (arbitrary addresses and ports), the reseed servers once | TCP and UDP, any port; TCP 443 for reseed | The widest row. UNVERIFIED which ports i2pd needs outbound |
| `mosquitto`, `iperf3`, `lxmd` | None | none | Private broker, no bridges; replies only |
| Twingate headless client | Twingate controller and relays | TCP 443 and TCP 30000-31000; UDP any (assumed, as for the connectors) | UNVERIFIED for the headless client |
| Bootstrap (first boot only) | Doppler API | TCP 443 | Loaded in a first-boot rule set and removed once the bootstrap unit finishes. Whether that is practical with cloud-init is UNVERIFIED |

Compared with a core connector, which opens TCP 30000-31000 and UDP 1-65535 on top of its defaults, this is narrower per process but not narrower at the Cloud Firewall: with i2pd listed for TCP and UDP on any port, the union of the rules is every outbound TCP and UDP port, so the cloud layer's outbound is fully open and adds nothing. The per-user nftables rules are the only filter, and they are a non-root boundary: a root compromise bypasses them. Egress is logged: dropped and new outbound connections are counted per user and shipped over the log path.

Residual risk, recorded as such: a compromised `i2pd` user has arbitrary outbound TCP and UDP, not only HTTPS, and the other daemons' users are held back only by the host rules. That is available for command and control or exfiltration. This design reduces it with per-user rules (a non-root boundary) and logging. It does not close it, and nothing here should be read as an outbound boundary that holds against root.

## 5. Options and cost

Price sources: `docs/cost-prices.json` (DigitalOcean sizes API, retrieved 2026-10-10), `docs/cost-prices/aws.json` (retrieved 2026-10-16), and the DigitalOcean pages named per row, read 2026-10-19. Every row adds to the stage 3 option A running total of $29 (connectors $12, `s-1vcpu-2gb` $12, Spaces $5), which is itself not built or approved. Backups are off in every row. Nothing here includes tax or transfer overage.

### 5.1 Option A: one edge droplet and a reserved IP (recommended)

| Line | Basis | Monthly |
|---|---|---|
| Edge droplet `s-1vcpu-1gb` | `docs/cost-prices.json` | $6.00 |
| Reserved IP, assigned | https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/, 2026-10-19: free when assigned | $0.00 |
| `rns-dmz` VPC | free type in the gate | $0.00 |
| Cloud Firewall | https://docs.digitalocean.com/products/networking/firewalls/details/limits/, 2026-10-19: no additional cost | $0.00 |
| DDoS protection (L3, L4) | https://docs.digitalocean.com/platform/ddos-protection/, 2026-10-19: no additional charge | $0.00 |
| Added | | $6.00 |
| Running total with stage 3 | $29 + $6 | $35.00 |

Two caveats that are not in the number. A reserved IP that is not assigned costs $5.00 a month, $0.01 an hour (same pricing page), so a failed apply that destroys the droplet and leaves the IP costs money until someone notices. And a droplet-pricing page note about "v5 configurations" says public IPv4 addresses on those are billed separately, at an introductory $0.00 that may change (https://docs.digitalocean.com/products/droplets/details/pricing/, 2026-10-19). Whether `s-1vcpu-1gb` here is such a configuration is UNVERIFIED, and I give no number for it.

Variant A2, a 2 GiB droplet in case 1 GiB is not enough: `s-1vcpu-2gb` is $12 in the same table. Added $12, running $41. Variant A0, `s-1vcpu-512mb-10gb` at $4, running $33, is listed in the table and I do not recommend it: five daemons on 512 MiB is not credible and I have no measurement.

### 5.2 Option B: A plus a load balancer in front

DigitalOcean's regional network load balancer is $15.00 per node per month and the regional HTTP one is $12.00 per node per month; a global one is $15.00 a month with 1 TB of transfer included (https://docs.digitalocean.com/products/networking/load-balancers/details/pricing/, read 2026-10-19). The services here are TCP and UDP and an HTTP balancer does not carry them, so the network type is the only fit. It forwards TCP and UDP (https://docs.digitalocean.com/products/networking/load-balancers/details/features/, 2026-10-19), keeps the client source address without PROXY protocol, and TLS passthrough for it is not confirmed on that page, which matters for the MQTT listener. Forwarding rule limits are UNVERIFIED.

| Line | Basis | Monthly |
|---|---|---|
| Option A | section 5.1 | $6.00 |
| Regional network load balancer, 1 node | pricing page above | $15.00 |
| Added | | $21.00 |
| Running total with stage 3 | $29 + $21 | $50.00 |

"Managed firewall": the Cloud Firewall is the managed firewall and it is already free and already in use. I found no separate paid firewall product on the pages I read; I did not verify that none exists.

What the $15 buys: a stable front address (the reserved IP already gives that for $0), health checks, and room for a second edge node. It does not add DDoS coverage, because droplets and assigned reserved IPs already have it, and cloud firewalls cannot be attached to the balancer, so filtering stays on the droplet. Today that is $15 for nothing the design needs. It is worth pricing again the day there are two edge nodes.

### 5.3 Option C: the edge on a second cloud (AWS)

The AWS design is already in the repo: `docs/cost-prices/aws.json`, 730 hours a month, public IPv4 at $0.005 an hour, gp3 at $0.08 a GiB-month, and the arithmetic the gate uses for the twin (2 x $10.42 = $20.84).

| Instance | Compute | Public IPv4 | 8 GiB gp3 | Monthly | Running with stage 3 |
|---|---|---|---|---|---|
| `t4g.nano` | 730 x $0.0042 = $3.07 | 730 x $0.005 = $3.65 | 8 x $0.08 = $0.64 | $7.36 | $36.36 |
| `t4g.micro` | 730 x $0.0084 = $6.13 | $3.65 | $0.64 | $10.42 | $39.42 |
| `t3.micro` | 730 x $0.0104 = $7.59 | $3.65 | $0.64 | $11.88 | $40.88 |

Rounded to cents as the gate does. The table prices a fixed list only: `not_priced` in `aws.json` names data transfer, logging, snapshots and anything created outside OpenTofu. Outbound transfer is the line that matters for this host and it has no figure here. I have not read AWS's current transfer pricing and give none. Memory per type (the nano is the small one) is UNVERIFIED here; the micro is the realistic floor for five daemons, and that is also unmeasured.

What it buys: a different account, a different credential set and a different abuse relationship, so an abuse action against the edge cannot touch the DigitalOcean team where core lives. It costs a second cloud's bill that has no pooled cap and a gate gap (section 6): the AWS approval already carries the twin's $20.84, and the gate prices every manifest under `stacks/aws/` whether it is applied or not. With the twin and the edge both manifested, AWS totals $31.26, and the active sum with DigitalOcean's $29 is $60.26, which is over `hard_max` ($60) and over any ceiling in the table. So this option needs a gate change first: a per-stack applied marker or a per-stack approval, so the twin can be priced as not running while the edge is. That is its own pull request, and it is the multi-cloud design's open item about the gate not seeing what is running ([cost guide](../../cost.md), "What `active` means").

### 5.4 Option D: keep $30 by deferring the bucket

Stage 3's thin droplet without the Spaces bucket is $24 with the connectors ([stage 3 design](2026-10-11-stage-3-workloads-design.md), section 4, option A). Adding the edge droplet:

| Line | Basis | Monthly |
|---|---|---|
| Connectors | stage 1 | $12.00 |
| Workload droplet `s-1vcpu-2gb`, no bucket | stage 3 table | $12.00 |
| Edge droplet and reserved IP | section 5.1 | $6.00 |
| Running total | | $30.00 |

It fits the unchanged $30 ceiling with nothing left. The cost: stage 3 keeps its state on the droplet, which the stage 3 design argues against (a disposable host with versioned state recovers from a bad day in minutes). It defers a piece rather than paying for it.

### 5.5 Side by side, against `approved.json`

| Option | Added | Running (with stage 3) | `edge` ceiling needed | Versus the $35 placeholder | Fits `hard_max` $60? |
|---|---|---|---|---|---|
| A, 1 GiB | $6.00 | $35.00 | $35 | Equal; the placeholder becomes the real number | Yes |
| A2, 2 GiB | $12.00 | $41.00 | $41 | +$6 | Yes |
| B, A plus network LB | $21.00 | $50.00 | $50 | +$15 | Yes |
| C, AWS `t4g.micro` | $10.42 | $39.42 | $40 (chosen headroom of $0.58 over the exact $39.42, not the minimum) | +$5, but blocked by the gate gap above | Only after the gate change |
| D, defer the bucket | $6.00 | $30.00 | $30 | -$5 (the phase is `planned`, so editing it is a normal reviewed change, and $30 does not drop below the phase before it) | Yes |

The exact phase table each option leaves behind. I ran `scripts/cost_raise.py --phase edge --ceiling N` as a dry run on 2026-10-19 for each value; nothing was written. Phases before `edge` stay at $30 in every case (`stage-0` to `aws-twin`).

| Option | `edge` | `second-site` | `learner-soc` | Edit needed beyond the `edge` line |
|---|---|---|---|---|
| Today | 35 | 41 | 53 | none |
| A | 35 | 41 | 53 | none; reason and date of `edge` change |
| A2 | 41 | 41 | 53 | none; equal is allowed |
| B | 50 | 41 fails | 53 | `second-site` is a quiet decrease and the gate fails ("ceiling $41.00 is below edge $50.00"). Either `--cascade`, which raises `second-site` to $50 and appends "Raised to $50.00 together with edge." to its reason with today's date, or mark `second-site` `"lowers": true` with a reason. Either way `second-site` is touched in the same diff |
| C | 40 | 41 | 53 | none |
| D | 30 | 41 | 53 | none |

Phase order is the second cost that the numbers do not show. A ceiling only matters once its phase is `current`, and the phases run in declared order with every earlier phase `done`. `edge` sits after `aws-twin`. What the tooling can do:

- `cost_raise.py --after` only places a phase that does not exist yet. For an existing phase such as `edge` it edits the entry in place and ignores `after` (`scripts/cost_raise.py`, `propose`), and CI forbids removing a phase (`transition_problems`), so delete-and-reinsert is out.
- A hand edit that moves the `edge` entry up to sit right after `stage-1` does pass the gate, including with `--base-approved`, which compares phases by key and not by position. I tried it on a scratch copy on 2026-10-19. But every later planned phase at $30 is then below `edge`'s $35, and the gate fails each as a quiet decrease: `stage-2`, `stage-3`, `stage-4` and `aws-twin` (checked on a scratch copy; raising only the first three still fails on `aws-twin`: "ceiling $30.00 is below stage-4 $35.00"). For `stage-2` to `stage-4`, `"lowers": true` would be untrue, since the edge droplet is still running while they are current, so they are raised to $35 for real. For `aws-twin` there are two ways that both pass the gate. Raise it to $35, the simple one. Or keep $30 with `"lowers": true` and a reason, which is truthful only if that phase's intended state is written down as the AWS twin ($20.84) plus the edge droplet ($6), $26.84, with the stage 3 workload host and its bucket not running; if stage 3 stays up beside the twin it is not true. The resulting table, which I ran through `cost_check.py --base-approved` on a scratch copy with no real file touched: `stage-1` 30, `edge` 35, `stage-2` 35, `stage-3` 35, `stage-4` 35, `aws-twin` 35 (or 30 with `lowers`), `second-site` 41, `learner-soc` 53. That is a reviewed approval of higher ceilings for four phases, not a tidy-up.
- Teaching the helper a phase-move operation, with lifecycle tests, is possible and I think more work than a one-time move is worth.

Recommendation: wait. Build the edge when the phases before it are done, in order, with no change to the tooling. If the maintainer wants the edge sooner, hand-move the entry and raise the three later phases in the same reviewed diff, and say so in the approval. Decision 3 asks which.

### 5.6 Cost gate changes any option needs

What the gate does today, read from `scripts/cost_check.py` (`uncosted_sources`): a DigitalOcean resource type is accepted if it is in `FREE_TYPES`; or if it is in `COSTED_TYPES` and the file it sits in is listed under `allowed_sources` in `approved.json`; anything else fails with "the gate has no price model for it". So an `allowed_sources` entry cannot make an unknown type legal; it only places a priced type in a file. Adding `digitalocean_reserved_ip` to the allowlist, as the first draft of this section said, would still fail. The exact changes:

1. Type model. `digitalocean_reserved_ip_assignment` goes in `FREE_TYPES` (it has no charge of its own). `digitalocean_reserved_ip` goes in `COSTED_TYPES`, not `FREE_TYPES`, because it is free only while assigned: $5.00 a month ($0.01 an hour) when it is not (https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/, 2026-10-19). Its file is listed in `allowed_sources`.
2. Manifest and price table. A `reserved_ip` kind in `cost.json` with `name` and `assigned_to`, the name of a droplet entry in the same manifest. The price table gets `reserved_ip_unassigned_monthly: 5.00` with that URL and date. An entry whose `assigned_to` resolves to a droplet in the same manifest prices at $0.00; an empty, unknown or missing `assigned_to` prices at $5.00, and I would make it fail instead, because an unassigned reserved IP has no use here. The count of `digitalocean_reserved_ip` blocks must equal the `reserved_ip` entries, with no `count` or `for_each`, as the gate already requires for machines.
3. Source check. Each `digitalocean_reserved_ip` block has exactly one `digitalocean_reserved_ip_assignment` block in the same stack, whose `ip_address` is literally a reference to that reserved IP and whose `droplet_id` is a reference to the droplet the manifest names. Zero, two, or a reference the scanner cannot read fail. The scanner does not execute HCL, so the accepted shapes are fixed in the implementation PR once the module's output for the droplet id exists. That output is UNVERIFIED because the module does not exist yet.
4. Plan check, in the trusted run. Today `--plan` reads AWS plans only. A DigitalOcean path is needed. From `tofu show -json plan` it fails when, in the end state, a reserved IP has no assignment, the assignment is being deleted while the IP stays, `droplet_id` is null, or the target is a type the gate does not know. A `droplet_id` that is unknown until apply is normal on the first create and is accepted only when the configuration expression references the manifest's droplet. A droplet replaced with the IP reassigned afterwards leaves the IP unassigned for the length of the apply; at $0.01 an hour that is cents, and the gate cares about the end state. As with AWS, this check is a guarantee only on a plan the trusted run produced.
5. Option B only. `digitalocean_loadbalancer` goes in `COSTED_TYPES`. A `loadbalancer` kind in `cost.json` with `type` (regional network) and `nodes`. Price table entry of $15.00 per node a month with the URL and date. The node count must come from a manifest local the way the connector size does, with `count` and `for_each` forbidden, and the plan check reconciles the planned node count with the manifest. The provider's attribute names for size or node count and any autoscale setting are UNVERIFIED (I did not read the provider docs); the plan check should fail on any sizing attribute it cannot price, as the AWS list does.
6. Option C only: the per-stack applied marker from section 5.3, and an `edge` manifest under `stacks/aws/`.
7. Common to all: a new stack (for example `stacks/50-edge`; the number leaves 40 for stage 4) with `cost.json` and a Spacelift stack `cah-50-edge` in `.spacelift/config.yml`; a new module (for example `modules/edge-host`) in `allowed_sources` for `digitalocean_droplet`, and the stage 3 plan's generalisation of the module count to every costed module, which the edge rides on; `docs/stages/approved.json` updated as in section 5.5, with DigitalOcean's `approved_monthly_total` raised to the sum the pick implies (option A: $12 connectors + $12 workload + $5 bucket + $6 edge = $35) and `hard_max` left alone unless the pick passes $60.
8. Tests: `tests/test_cost_check.py` cases for each rule above (an unassigned IP fails, two assignments fail, an assignment to a missing droplet fails, a destroyed assignment fails in the plan), and the stack's `tofu test`. In the implementation PR, not here.

### 5.7 Transfer

DigitalOcean bills outbound only; inbound is free; the allowance is pooled across every droplet at the team level and does not roll over; the overage is $0.01 per GiB (https://docs.digitalocean.com/products/droplets/details/pricing/, read 2026-10-19). The included amount per plan is not stated on that page. The public pricing page gave 1,000 GiB for the $6 plan and also said bundled plans never exceed the flat price (https://www.digitalocean.com/pricing/droplets, 2026-10-19), which contradicts the overage rate. I read that page through a summarising fetch, not directly, so the included amount is UNVERIFIED and I give no allowance to rely on. Read the real figure off the account's usage page before approving.

What I can bound is my own design, as arithmetic and not measurement. The terms first, because the first draft blurred them:

- A run is one scheduled measurement session against one path. The throughput schedule is two runs a day, at jittered times, on each of two paths (direct and ZTNA), so four path-runs a day.
- Each path-run does four tests: upload single stream, upload `-P 4`, reverse single stream, reverse `-P 4`. "Upload" means the client sends to the edge. "Reverse" (`-R`) means the edge sends to the client.
- `-n N` sets the bytes to transmit. The iperf3 invoking page says only "Set the number of bytes to transmit" and does not say whether that is total or per stream when `-P` is used (https://software.es.net/iperf/invoking.html, 2026-10-19). So I carry both readings: total, where a `-P 4` test moves N; and per stream, where it moves 4N. The pinned version is checked on loopback in the implementation PR. (Its `-b` limit is per stream, same page.)
- Who is billed for what. The edge's outbound is billed. On the direct path only the reverse tests are outbound from the edge. On the ZTNA path an upload leaves the core connector toward the edge (billed on the connector, in the same pool), and a reverse test leaves the edge toward the connector and then the connector toward home, so it is billed twice. That counting assumes traffic between two droplets on their public addresses is billed as ordinary outbound; I did not verify that, so it is UNVERIFIED and I carry it as the worst case.

Bytes per day with `N = 500 MB`, `B4` the bytes of a `-P 4` test (N if `-n` is total, 4N if per stream):

| Path | Billed per path-run | Two runs a day |
|---|---|---|
| Direct | reverse single N + reverse P4 B4 | 2 x (N + B4) |
| ZTNA | uploads (N + B4) once, reverses (N + B4) twice = 3 x (N + B4) | 6 x (N + B4) |
| Both | 4 x (N + B4) per run, so 8 x (N + B4) per day | |

- `-n` total: B4 = 500 MB, N + B4 = 1 GB, 8 GB a day, about 240 GB a month.
- `-n` per stream: B4 = 2 GB, N + B4 = 2.5 GB, 20 GB a day, about 600 GB a month.
- Cheap probes: `-u -b 1M -t 5` is 5 Mbit, about 0.63 MB, a run. Every 5 minutes is 288 runs a day on each path, about 180 MB a day for one path counted once. If every run counted once on the direct path and three times on the ZTNA path, that is 4 x 180 MB = 720 MB a day, about 22 GB a month, as an upper bound.
- The two paths together at the upper bound: about 262 GB a month (total) or about 622 GB a month (per stream), if every test runs to its cap.
- Lowering the cap to `-n 200M` scales the throughput part by 2/5: about 96 GB or 240 GB, plus the probes.

An earlier draft said about 300 GB for the per-stream case. That was one path counted once, so it understated the ZTNA path; the arithmetic above is the one to review. At $0.01 per GiB even 622 GB is about $6 over, if none of it fell inside the allowance; so transfer is a watched line, not an approval line, until the allowance is read.

i2pd: the bound is the cap. A transit cap of 32 KB/s, fully used, is about 83 GB a month (32,000 B/s x 2,592,000 s). The i2pd option names and bandwidth classes are UNVERIFIED and a real rate is not measured.

Reticulum and lxmd: I have no enforceable quota to put a number on. I do not know a Reticulum or lxmd setting that caps outbound bytes per month, and I will not invent one. A host-level rate limit on the `rnsd` user (nftables or `tc`) could enforce a rate, and rate x 2,592,000 s then gives the monthly maximum; whether that works on the chosen host, and what rate to set, are open. Approval is blocked on that: the implementation does not start until Reticulum has a stated rate cap and the monthly maximum it implies, added to the figures above.

The gate cannot see transfer. It goes in `docs/cost.md` as a usage line to check, the way Functions are.

## 6. Cost gate and ceiling mechanics, in one place

- Today the gate would fail an edge branch at three points: a droplet outside the connector module, a reserved IP type it does not know, and a missing manifest. That is the intended behaviour and this design does not weaken it.
- `scripts/cost_raise.py` prints the exact diff for the phase change. The first step of the implementation is a dry run of it, pasted in the PR.
- Whatever is picked, the phase is `planned` until the maintainer makes it current in a reviewed diff. This document changes no JSON.

## 7. Recommendation

Option A at 1 GiB, with the `edge` ceiling set to $35, and a rule that the implementation PR must show a memory measurement on a 1 GiB VM before the cost number is final. If the measurement fails, the pick moves to A2 and the ceiling to $41 in a new reviewed diff, which is cheaper than finding out after a rebuild.

Reasons:

- It is the smallest design that meets the handoff: separate VPC, immutable host, reserved IP, tag firewall, host nftables.
- Every line is priced from the repository's own table or a page I read today, and the $35 it lands on is the placeholder already in `approved.json`, so the number the project was already carrying turns out right.
- B buys nothing the design needs. The reserved IP gives the stable address, droplets already get DDoS protection, and the firewall cannot attach to the balancer.
- C's real value is account separation, and that is a security argument rather than a cost one. It is worth deciding on its merits (decision 4), not as a way to dodge a $6 raise. It also needs a gate change before it can be approved, and it adds a bill with no pooled cap and no figure I can write down.
- D keeps the ceiling but takes the bucket out of stage 3, trading a disposable workload host for $5. I would not make that trade for an edge host that will be scanned. If the maintainer will not raise the ceiling, D is the honest way to hold it.

What this recommendation does not settle: the $35 leaves no headroom for transfer overage, a reserved-IP mishap or a second droplet. A bigger ceiling, say $40, would absorb small surprises; I did not pick it because an unexplained margin is how ceilings drift, and the gate already stops a phase from passing it. The $40 shown for option C is the same kind of choice: chosen headroom over the exact $39.42.

## 8. Out of scope, but constrained

### 8.1 The honeypot (#120)

Design only, and outside this project's apply path. Two lists, kept apart because they are different kinds of statement.

Requirements for the future honeypot design (nothing below is enforced today):

- A separate account or provider, never the CAH project, for abuse reports, token isolation and blast radius.
- No shared DigitalOcean token, no shared Spacelift space, no shared Doppler config, no stack in this repository.
- Logs go one way, over its own Twingate service account scoped to one relay endpoint, and the relay meets the section 4.6.1 prerequisites. It does not reach the edge and the edge does not reach it.
- Its spend is outside the ceiling and carries its own budget. The document for it is #120's, not this one.

Controls that are enforced now: only that the cost gate refuses a provider prefix that is neither a known cloud nor in `SAFE_PREFIXES`. That is all. It does not keep a honeypot out of this repository if it uses a provider the gate already knows, such as DigitalOcean or AWS, once someone edits the allowlist in a reviewed change. It does not enforce separate accounts, spaces or Doppler configs. The separation holds because of review and because the honeypot lives elsewhere. If enforcement is wanted, it is a follow-up: repository policies that reject honeypot-named stacks and resources, cross-project tags, shared credential or context identifiers and DMZ-to-DMZ rules. I list it as a possible issue, not as something this design provides.

### 8.2 PeerTube (#121)

A DMZ-class workload: public web, federation, transcoding and object storage. It gets its own costed design and its own stage.

Choices in this design that leave it room, none of which constrain a future stack on their own: role tags and a default-deny DMZ-to-DMZ rule so a second host does not widen the first one's rules; ports 80 and 443 closed on the transport host; and three reserved IPs per account by default (https://docs.digitalocean.com/products/networking/reserved-ips/details/limits/, 2026-10-19), enough for the edge and one more, with more by request.

Requirements for PeerTube's own design: its own VPC or an explicit reason to share `rns-dmz`, its own account decision (see decision 4), its own firewall relationships, its own credentials, and a cost and exposure analysis. Nothing in this repository enforces any of that today, and this design does not say PeerTube belongs in the same VPC or account.

### 8.3 Why not private droplets (yet) (#119)

A private droplet needs a VPC NAT gateway to reach the internet. DigitalOcean lists it at $40.00 a month per size increment, with 100 GiB of outbound included and $0.01 per GiB after (https://docs.digitalocean.com/products/networking/vpc/details/pricing/, read 2026-10-19). That is more than the whole current ceiling for one gateway, and every Twingate byte from core would pass through it. The handoff also records no in-place conversion, no reserved IPs and no Droplet Console for private droplets; I did not verify those three. One correction to the handoff: it says 25 Mbps per increment, and the pricing page I read says 2 Gbps symmetrical per increment. I follow the page; the throughput point in the handoff is weaker than it said, and the price point is unchanged. This does not touch the edge, which is public by design. The wiki page is #119's.

## 9. Known risks and decisions

Facts verified today (2026-10-19), with where:

| Fact | Source |
|---|---|
| Reserved IP free when assigned, $5.00 a month ($0.01 an hour) when not | https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/ |
| Three reserved IPs per account by default; one per droplet | https://docs.digitalocean.com/products/networking/reserved-ips/details/limits/ |
| Regional network LB $15.00 per node a month; regional HTTP $12.00; global $15.00 | https://docs.digitalocean.com/products/networking/load-balancers/details/pricing/ |
| Network LB carries TCP and UDP, keeps the client source address, no PROXY protocol | https://docs.digitalocean.com/products/networking/load-balancers/details/features/ |
| Cloud Firewall: 50 rules, 10 droplets, 5 tags, free, not attachable to load balancers | https://docs.digitalocean.com/products/networking/firewalls/details/limits/ |
| DDoS protection: L3 and L4, droplets, load balancers and assigned reserved IPs, no extra charge, no L7, blackholes the target IP past capacity, no stated capacity or SLA | https://docs.digitalocean.com/platform/ddos-protection/ |
| Outbound only is billed, $0.01 per GiB over, pooled at team level | https://docs.digitalocean.com/products/droplets/details/pricing/ |
| Different VPCs do not reach each other without peering; ranges cannot overlap | https://docs.digitalocean.com/products/networking/vpc/details/limits/ |
| NAT gateway $40.00 per increment, 100 GiB included | https://docs.digitalocean.com/products/networking/vpc/details/pricing/ |
| A Twingate resource can be a public address; traffic goes client to connector, which forwards to the resource | https://www.twingate.com/docs/resources and https://www.twingate.com/docs/how-twingate-works |
| iperf3 `-n` sets bytes to transmit; docs do not say total or per stream with `-P`; `-b` is per stream | https://software.es.net/iperf/invoking.html |

Not verified, and given no number: the included transfer per droplet plan; whether the `s-1vcpu-1gb` plan carries the separately billed public IPv4 the pricing page mentions for "v5 configurations"; load balancer forwarding-rule limits and TLS passthrough for the network type; AWS outbound transfer pricing and instance memory; whether public-IP traffic between two droplets counts against the pool; the Twingate headless client running unattended with no admin path; the iperf3 package's OpenSSL auth support; current Reticulum, lxmd and i2pd option names; what source address a Twingate-forwarded connection presents to a public resource, and UDP resources; Droplet Console availability (not relied on); memory fit of five daemons on 1 GiB; whether a separate DigitalOcean team is free and how its pooled allowance, credentials and Spacelift wiring would work; the Reticulum and lxmd rate-cap mechanism; `-n` semantics for the pinned iperf3 version; the shortest Doppler service token lifetime.

Decisions the maintainer owed (my pick in the third column, his ruling in the fourth; rulings recorded 2026-10-21 from his 2026-10-19 decisions):

| # | Question | My recommendation | Ruling |
|---|---|---|---|
| 1 | Which option: A, A2, B, C or D | A at 1 GiB, ceiling $35, memory measured first | DECIDED 2026-10-19: option A, a 1 GiB droplet plus a reserved IP, memory measured first |
| 2 | The `edge` ceiling number: $35, $41 (room for A2), or other | $35; raise to $41 only if the measurement fails | DECIDED 2026-10-19: ceiling $35; the A2/$41 variant only if the memory measurement fails |
| 3 | Wait for the phases before `edge` to be done, or hand-move `edge` up and, in the same reviewed diff, raise `stage-2`, `stage-3` and `stage-4` to $35 and either raise `aws-twin` to $35 or mark it `lowers` with its intended state written down (section 5.5) | Wait. No tooling change, no ceilings raised ahead of need | DECIDED 2026-10-19: wait for the earlier phases; no tooling change and no ceiling raise now |
| 4 | Same DigitalOcean team as core, a separate team, or another cloud, for the abuse-report risk | PROVISIONAL: same team for now, and not decided until the list after this table is answered. I do not call Reticulum, LXMF or I2P low-abuse: a private MQTT broker does not change what open transport, propagation storage and I2P transit can be used for. This is a judgment on risk appetite that the code and docs I read cannot settle | PROVISIONAL (ruled 2026-10-19): same DigitalOcean team, until the separate-team facts listed below are verified |
| 5 | Logging: option A (scoped Twingate headless client) or B (none at first) | A, but only once the headless-client question is answered and the relay prerequisites in section 4.6.1 each have an owner | DECIDED 2026-10-19: Twingate headless log shipping only once the headless-client question is answered and each section 4.6.1 relay prerequisite has a named owner |
| 6 | MQTT broker: private or public | Private, per the handoff default | DECIDED 2026-10-19: private MQTT |
| 7 | Stack name and number (`50-edge` is mine) | Accept or rename | DECIDED 2026-10-19: stack name `50-edge` |
| 8 | Transfer: accept it as a watched usage line, with a billing alert before the first apply | Accept, once Reticulum has a stated rate cap (section 5.7) | DECIDED 2026-10-19: tracked as a watched usage line plus a billing alert, once Reticulum has a rate cap |
| 9 | Ingest protocol and relay controls (section 4.6.1) | Not mine to pick; the home-side design owns them, and approval waits for it | NOT ruled: owned by the home-side relay/ingest design |
| 10 | The core connector firewall gets TCP 5201 outbound for the ZTNA path (section 4.3) | Accept in the implementation PR, with the ZTNA path conditional on the two checks there | DECIDED 2026-10-19: TCP 5201 outbound rule on the core connector firewall, added in the implementation PR |

Before decision 4 can be anything but provisional, these have to be confirmed: the price and limits of a separate DigitalOcean team; whether credentials and Spacelift contexts can be isolated per team; how transfer pooling works across teams; how DigitalOcean's abuse handling treats a team and what it can suspend; and how teardown of the edge team works. And an abuse-response runbook has to exist, with measurable thresholds. Proposed starting values, mine, not measured, for the maintainer to set: alert at 80 percent of the monthly transfer cap; alert if two consecutive days each exceed twice the daily share of that cap; alert at 80 percent of the `lxmd` storage cap; any provider abuse notice answered, and the named service switched off by a pull request and a rebuild, within a target of 24 hours (the provider's own response window is UNVERIFIED).

## 10. Changes this stage makes to the repository

Not an implementation plan, and not made by this document. This PR adds only this file and a link in the wiki Roadmap. The implementation, after approval, touches:

- `stacks/50-edge/` (or the chosen name): VPC, tag, firewall, reserved IP and assignment, the module, `cost.json`, tests.
- `modules/edge-host/`: droplet, cloud-init with pinned packages, nftables, tests.
- `docs/stages/approved.json`: provider approval, `allowed_sources`, the `edge` phase.
- `scripts/cost_check.py` and `tests/test_cost_check.py`: the reserved IP rule, the generalised module count, and for option B or C the pieces listed in section 5.6.
- `.spacelift/policies/`: a plan rule denying VPC peering and core tags on edge resources, with tests.
- `.spacelift/config.yml`: stack `cah-50-edge` and its Doppler names.
- `stacks/10-access`: TCP 5201 outbound on the connector firewall for the ZTNA measurement path (section 4.3), reviewed as a core change.
- `docs/stages/approved.json` phase edits per section 5.5, including `second-site` for option B.
- `docs/cost.md`: the edge section and the transfer usage line.
- `docs/stages/05-edge.md` (or similar): the operator guide.
- Wiki: architecture diagram with zones, threat model section, glossary. That is handoff PR 4.

## 11. What this design does not claim

It does not claim that 1 GiB runs the five daemons, that the transfer figures are anything but arithmetic on assumptions, that any DigitalOcean page read today stays true (each fact carries its date), or that the $35 is a hard cap: the gate checks fixed declared infrastructure, and transfer, a stuck reserved IP or a provider price change fall outside it. It does not claim the edge is safe to expose, only that a compromise of it is bounded. It did not probe, apply or plan anything.
