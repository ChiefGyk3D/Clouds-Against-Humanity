# Clouds Against Humanity: Public Edge (DMZ)

Status: DRAFT for review. Date: 2026-10-19. Issue: #118 (epic #72). Source brief: [the 2026-10-12 edge handoff](../plans/2026-10-12-edge-dmz-handoff.md), sections 3 and 4.
Tooling: OpenTofu throughout.
Scope: the public edge only: one internet-facing host in its own VPC, how it is hardened, how it logs home, and what it costs under four different shapes. This is a design, not an approval. Nothing here costs money, changes a stack or moves a ceiling until the maintainer picks an option in section 5 and approves it. The handoff says the edge lands past the $30 ceiling and the ceiling is not raised by default, so this document lays out options and recommends one; it does not choose for him.

Vendor facts below carry a URL and the date they were read (2026-10-19). Anything I could not verify is marked UNVERIFIED and carries no number. Facts from the repository's own price tables carry the table's retrieval date instead. Section 9 lists what is still open.

## 1. Purpose

Put a small set of internet-facing radio and measurement services on one immutable host, in a VPC of its own, so the core environment keeps zero inbound. The services are Reticulum transport with an LXMF propagation node, i2pd, a Meshtastic MQTT broker over TLS, and an authenticated iperf3 server used to compare a direct path to a Twingate path.

Goals:

- One public host in a separate VPC with no peering to core, tagged `rns-dmz`.
- A public address that survives a rebuild (a reserved IP).
- No SSH, no Twingate connector and no admin path on the host. Every change is a pull request, a Spacelift plan and a rebuild.
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
| Edge to core | None. Separate VPC, no peering, no shared secret, no shared tag. The one connection is core's connectors dialing the edge's public IP for the measurement path (section 4.3) |
| Edge to home | One Twingate service account, one resource: the ingest port on the home disposable relay. Never the SIEM |
| Repo to edge | cloud-init rendered by OpenTofu; Doppler is read at boot with a token scoped to the edge config only |
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
| 1 | Service RCE, then the log credential (abuse cases 2 and 3) | The service account sees one resource, one port, on a relay that is one-way and disposable; pfSense on the relay's VLAN repeats the same single port; services run as unprivileged users under systemd hardening; the key lives in a file readable by the client's user only | A test that lists the group's Twingate resources and fails if there is more than one; a pfSense rule review; from my own throwaway test host in a set window, confirm no other home port answers |
| 2 | Bandwidth and bill abuse (abuse case 4, and 1) | i2pd transit and share caps, lxmd storage and transfer limits, iperf3 source rules, a billing alert set before the first apply, `-n` byte caps on every test | The usage page after week one against the section 5.7 figures; a rebuild test that shows the disk limit holds |
| 3 | Pivot from edge to core | Separate VPC, no peering (DigitalOcean's VPCs do not reach each other without peering, section 9), no shared tag, no shared Doppler config | A plan policy that denies any peering resource and any core tag on an edge resource, with policy tests next to the existing ones; the stack test asserts the edge VPC's CIDR does not overlap core's |
| 4 | Provider acts on the account after an abuse report (abuse case 6) | Private MQTT broker by default; propagation-node storage capped; an abuse contact that is read; the decision in section 7 about a separate team | Not testable in advance. The check is a calendar item: read the abuse inbox weekly. Residual risk accepted until decided |
| 5 | Supply chain or unpinned software | Pin by version and checksum, current releases only, OS packages through unattended upgrades, a scheduled monthly rebuild because the host cannot be patched by hand | A test that fails on an unpinned package name in the cloud-init template; a version report in the log stream |
| 6 | Secrets in user-data (abuse case 8) | Depends on the metadata-endpoint restriction from handoff PR 1; only tokens scoped to the edge Doppler config go in; secrets are fetched at boot rather than written into the template | The existing `metadata_lock` tests extended to the edge template; a check that the rendered user-data has no secret-shaped value |
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
| Break-glass | The DigitalOcean control panel's Droplet Console | The handoff states this is available for a standard droplet; I did not verify it and the plan should not rely on it until the first build proves it |

Nothing on the edge is "reachable only through Twingate" inbound, because the edge has no admin plane. Twingate carries two things: the measurement path to the edge's public address, and the edge's own logs going home.

### 4.3 How it relates to the zero-inbound core

Core keeps zero inbound. The edge changes nothing there. The measurement path is a Twingate resource whose address is the edge's public IP, granted to the admin group; the core connectors dial it, so the edge sees the connectors' public egress addresses and allows them on 5201. Whether Twingate supports a resource aimed at a public address this way, and what source address the edge then sees, is UNVERIFIED (the handoff flags it VERIFY; I did not confirm it against Twingate's docs). The firewall rule uses the connectors' addresses as a variable, so a wrong assumption is a variable change, not a redesign.

This path does give the edge one fact about core: the connectors' public addresses. Those are already public. No secret crosses.

### 4.4 Host hardening, reused from stage 1

Reused unchanged where it applies: one non-root user, no password auth, unattended upgrades with a reboot window that does not collide with the connectors', chrony, a sysctl drop-in, the metadata-endpoint lock, and the default-drop nftables host firewall from handoff PR 1 mirroring the Cloud Firewall. Not reused: the Twingate connector, SSH keys, any inbound admin rule. New: every service runs as its own unprivileged user under systemd sandboxing where it works, and the packages are pinned (risk 5).

Cloud Firewall limits that matter here, read from https://docs.digitalocean.com/products/networking/firewalls/details/limits/ on 2026-10-19: 50 rules per firewall, 10 droplets and 5 tags per firewall, and the firewall is free. One droplet is far under all three. The same page says cloud firewalls cannot be applied to load balancers, which matters for option B.

### 4.5 Services

Per the handoff: `rnsd` with `enable_transport = Yes` and a `TCPServerInterface`; `lxmd` as a propagation node with storage and transfer limits; i2pd with SAM on loopback, a pinned inbound port and capped transit; Mosquitto with TLS and authentication, private broker for the maintainer's nodes by default; iperf3 with `--rsa-private-key-path` and `--authorized-users-path`, key material from Doppler. Option names for Reticulum, lxmd and i2pd have changed between releases, and whether the distro's iperf3 is built with OpenSSL auth support is UNVERIFIED. The implementation PR checks each against the version it pins and records the link, as the handoff requires.

Memory is the open fact. Five daemons on 1 GiB, with no swap, has not been measured. It is the reason section 5 prices a 2 GiB variant.

### 4.6 Logging into the stage 2 path

Option A (recommended, from the handoff): a Twingate headless client on the edge with a service account whose only resource is the ingest port on the home disposable relay, the same pattern as the stage 2 cloud service accounts ([stage 2 design](2026-10-11-stage-2-logging-design.md), section 4.0b). Concretely: a new home remote network and connector for the relay (per section 4.0a's one-per-VLAN rule), a service account `cah-edge-logging` in its own group that holds no other resource, and nothing that reaches the SIEM. The relay forwards into the SIEM, so the edge never has a line to it.

What the credential can reach: the one ingest port. What it cannot: the SIEM, the AI VLAN, the other service accounts' resources, core. A compromised edge holds the key, can write junk to the relay and can try to flood it; the relay rate-limits and caps input (risk 9).

Option B: no log shipping at first, DigitalOcean monitoring only. It leaves nothing to put on a compromised host, and nothing to investigate with afterwards. The cost: a public host with no logs. I do not recommend it, and I list it so the choice is visible.

UNVERIFIED: that the Twingate headless client runs unattended under systemd on a host with no admin path and what outbound access it needs. The outbound firewall cannot name Twingate relay addresses individually, so outbound 443 stays open; section 9 asks for this to be checked. The ingest protocol (Wazuh agent, syslog, Vector) is the relay's, decided in the home-side work, and is not priced here.

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
| C, AWS `t4g.micro` | $10.42 | $39.42 | $40 | +$5, but blocked by the gate gap above | Only after the gate change |
| D, defer the bucket | $6.00 | $30.00 | $30 | -$5 (a lower ceiling than the placeholder; the phase is `planned`, so editing it is a normal reviewed change, and $30 does not drop below the phase before it) | Yes |

A ceiling only matters once its phase is current, and the phases run in declared order: `edge` sits after `aws-twin` in `approved.json`, and every phase before the current one must be `done` (the lifecycle rule in the [cost guide](../../cost.md), "Ceilings per phase"). So building the edge before stages 2 to 4 and the AWS twin are `done` means either marking those done or reordering the phases with `cost_raise.py --after`, as its own reviewed diff. That is a process cost the numbers do not show.

### 5.6 Cost gate changes any option needs

- A new stack, for example `stacks/50-edge` (the number leaves 40 for stage 4; the name is a choice for the maintainer), with a `cost.json` and a Spacelift stack `cah-50-edge` in `.spacelift/config.yml`. The gate refuses a stack with no manifest.
- A new module, for example `modules/edge-host`, listed under `allowed_sources` for `digitalocean_droplet`. The existing count-equals-machine-entries rule covers `twingate-connector` blocks only; the stage 3 design already plans to generalise it to every costed module, and the edge rides on that change.
- `digitalocean_reserved_ip` and `digitalocean_reserved_ip_assignment` added as allowed types, with a new rule that every reserved IP has an assignment in the same stack, because an unassigned one is $5.00. The manifest prices an assigned one at $0.00.
- Option B only: `digitalocean_loadbalancer` as a priced type with a node count, since today the gate refuses it.
- Option C only: the per-stack applied marker above, and an `edge` manifest under `stacks/aws/`.
- `docs/stages/approved.json`: raise DigitalOcean's `approved_monthly_total` to the sum the pick implies (option A: $12 connectors + $12 workload + $5 bucket + $6 edge = $35), add the edge module to `allowed_sources`, set the `edge` phase ceiling to the picked number with a real reason, and leave `hard_max` alone unless the pick passes $60.
- Tests: `tests/test_cost_check.py` and the stack's own `tofu test` for the edge manifest, in the implementation PR, not here.

### 5.7 Transfer

DigitalOcean bills outbound only; inbound is free; the allowance is pooled across every droplet at the team level and does not roll over; the overage is $0.01 per GiB (https://docs.digitalocean.com/products/droplets/details/pricing/, read 2026-10-19). The included amount per plan is not stated on that page. The public pricing page gave 1,000 GiB for the $6 plan and also said bundled plans never exceed the flat price (https://www.digitalocean.com/pricing/droplets, 2026-10-19), which contradicts the overage rate. I read that page through a summarising fetch, not directly, so I treat the included amount as UNVERIFIED and give no allowance to rely on. Read the real figure off the account's usage page before approving.

What I can bound is my own design, as arithmetic and not measurement:

- Cheap probes: `-u -b 1M -t 5` is 5 Mbit, about 0.63 MB, a run. Every 5 minutes on two paths is 576 runs a day, about 360 MB a day, about 11 GB a month, if every run were billed outbound. In practice only `-R` runs count outbound, so this is the ceiling.
- Throughput tests, outbound direction only, twice a day, two paths, single stream and `-P 4`: eight outbound tests a day. With `-n 500M` as the cap that is 4 GB a day, about 120 GB a month. If `-n` is a per-stream cap the `-P 4` tests are four times larger and the figure is about 300 GB a month. I have not checked which it is. Lowering the cap to `-n 200M` divides both by 2.5.
- On the Twingate path the traffic also leaves a core connector, so it can count twice in the pool. Whether public-IP traffic between two droplets in one account is counted is UNVERIFIED.
- i2pd and Reticulum: no measured rate exists for either and I will not invent one. The bound is the cap: a transit cap of 32 KB/s, fully used, is about 83 GB a month (32,000 B/s x 2,592,000 s). The real number is what the caps are set to, and the first month's usage page is the measurement.

At the $0.01 per GiB overage even 300 GB is $3 over, so transfer is a watched line, not an approval line. It is also a line the gate cannot see. It goes in `docs/cost.md` as a usage line to check, the way Functions are.

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

What this recommendation does not settle: the $35 leaves no headroom for transfer overage, a reserved-IP mishap or a second droplet. A bigger ceiling, say $40, would absorb small surprises; I did not pick it because an unexplained margin is how ceilings drift, and the gate already stops a phase from passing it.

## 8. Out of scope, but constrained

### 8.1 The honeypot (#120)

Design only, and outside this project's apply path. The constraints this design puts on it:

- A separate account or provider, never the CAH project, for abuse reports, token isolation and blast radius. No shared DigitalOcean token, no shared Spacelift space, no shared Doppler config, no stack in this repository.
- Its logs go one way, over its own Twingate service account scoped to the relay ingest port, and land in the same relay as the edge's. It must not reach the edge, and the edge must not reach it.
- The cost gate backs this: a provider prefix not in `SAFE_PREFIXES` or the known clouds fails, so a honeypot stack cannot slip into this repository unnoticed.
- Its spend is outside the ceiling and carries its own budget. The document for it is #120's, not this one.

### 8.2 PeerTube (#121)

A DMZ-class workload: public web, federation, transcoding and object storage. It gets its own costed design and its own stage. What this design does to leave it room: role tags and a default-deny DMZ-to-DMZ rule so a second host does not widen the first one's rules; ports 80 and 443 stay closed on the transport host; the three reserved IPs a DigitalOcean account gets by default (https://docs.digitalocean.com/products/networking/reserved-ips/details/limits/, 2026-10-19) are enough for the edge and one more, and more can be requested. It does not say PeerTube belongs in the same VPC, or the same account (see the abuse-report risk).

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

Not verified, and given no number: the included transfer per droplet plan; whether the `s-1vcpu-1gb` plan carries the separately billed public IPv4 the pricing page mentions for "v5 configurations"; load balancer forwarding-rule limits and TLS passthrough for the network type; AWS outbound transfer pricing and instance memory; whether public-IP traffic between two droplets counts against the pool; Twingate resources aimed at a public IP and the source address they present; the Twingate headless client running unattended with no admin path; the iperf3 package's OpenSSL auth support; current Reticulum, lxmd and i2pd option names; Droplet Console availability as a break-glass path; memory fit of five daemons on 1 GiB; whether a separate DigitalOcean team is free and how its pooled allowance and Spacelift wiring would work.

Decisions the maintainer owes (my pick in the right-hand column):

| # | Question | My recommendation |
|---|---|---|
| 1 | Which option: A, A2, B, C or D | A at 1 GiB, ceiling $35, memory measured first |
| 2 | The `edge` ceiling number: $35, $41 (room for A2), or other | $35; raise to $41 only if the measurement fails |
| 3 | Reorder `approved.json` phases so the edge can be built before stages 2 to 4 and the AWS twin are done, or wait | Reorder with `cost_raise.py --after`, as its own reviewed diff, once the pick is made |
| 4 | Same DigitalOcean team as core, or a separate team, or another cloud, for the abuse-report risk | Same team for this edge (low abuse profile with a private broker and capped propagation); revisit before PeerTube. This is a judgment on risk appetite that I did not resolve |
| 5 | Logging: option A (scoped Twingate headless client) or B (none at first) | A, once the headless-client question is answered |
| 6 | MQTT broker: private or public | Private, per the handoff default |
| 7 | Stack name and number (`50-edge` is mine) | Accept or rename |
| 8 | Transfer: accept it as a watched usage line, with a billing alert before the first apply | Accept |

## 10. Changes this stage makes to the repository

Not an implementation plan, and not made by this document. This PR adds only this file and a link in the wiki Roadmap. The implementation, after approval, touches:

- `stacks/50-edge/` (or the chosen name): VPC, tag, firewall, reserved IP and assignment, the module, `cost.json`, tests.
- `modules/edge-host/`: droplet, cloud-init with pinned packages, nftables, tests.
- `docs/stages/approved.json`: provider approval, `allowed_sources`, the `edge` phase.
- `scripts/cost_check.py` and `tests/test_cost_check.py`: the reserved IP rule, the generalised module count, and for option B or C the pieces listed in section 5.6.
- `.spacelift/policies/`: a plan rule denying VPC peering and core tags on edge resources, with tests.
- `.spacelift/config.yml`: stack `cah-50-edge` and its Doppler names.
- `docs/cost.md`: the edge section and the transfer usage line.
- `docs/stages/05-edge.md` (or similar): the operator guide.
- Wiki: architecture diagram with zones, threat model section, glossary. That is handoff PR 4.

## 11. What this design does not claim

It does not claim that 1 GiB runs the five daemons, that the transfer figures are anything but arithmetic on assumptions, that any DigitalOcean page read today stays true (each fact carries its date), or that the $35 is a hard cap: the gate checks fixed declared infrastructure, and transfer, a stuck reserved IP or a provider price change fall outside it. It does not claim the edge is safe to expose, only that a compromise of it is bounded. It did not probe, apply or plan anything.
