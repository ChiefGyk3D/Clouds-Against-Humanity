# CAH handoff: public edge (DMZ), hardening, and future private networking

You are working in the Clouds-Against-Humanity repo (OpenTofu + DigitalOcean + Spacelift + Doppler + Twingate). Before changing anything, read the existing stacks and modules, `docs/stages/`, `docs/superpowers/specs/` (especially the 2026-10-11 stage 2 and stage 3 design drafts), `docs/cost.md`, the cost gate, the test suites, `.spacelift/policies/`, and `docs/wiki/`. Follow the existing conventions for stage numbering, layering, naming, tags, tests, docs, and Mermaid styling (dark classDefs already used in the wiki).

## Ground rules

- Never run `tofu apply` or trigger a tracked Spacelift run. PRs only; plans come from Spacelift on the PR.
- One logical change per PR, in the order below. Design docs get their own PR and wait for my approval before any implementation PR.
- Secrets come only from Doppler. Nothing secret in variables that land in state if avoidable, nothing in user-data that is not already covered by the metadata-endpoint restriction.
- Do not raise the $30 cost ceiling yourself. If something exceeds it, the cost gate must fail and the design doc must lay out the options.
- No em dashes anywhere (code comments, docs, wiki, commit messages).
- No force pushes, no destructive git operations, keep the noreply commit email already used in the repo.
- Run the existing pytest suite, `tofu test` (mocked providers), shellcheck, Mermaid parse checks, and the cost gate before opening each PR.
- Anything below marked VERIFY must be checked against current official docs before it is written into code. If a doc contradicts this handoff, follow the doc and call it out in the PR description.
- Changes to my app repos (Stream-Daemon, Boon-Tube-Daemon, Star-Daemon, penguin-overlord, solarstorm_scout) are out of scope. List them as follow-up issues in the PR description instead.

## Decisions already made

### 1. Keep standard droplets for core (connectors, workload host)

Private Droplets are rejected for now, for documented reasons:
- Outbound requires a VPC NAT gateway: about $40/month for size 1 (100 GiB included, $0.01/GiB after), which exceeds the whole ceiling.
- Each NAT increment is 25 Mbps symmetrical; all Twingate traffic would squeeze through it.
- No conversion in place (recreate only), no reserved IPs, no Droplet Console for break-glass.

Instead, "public IP but nothing listening" is enforced in layers:
1. Tag-based Cloud Firewall deny-all inbound (exists).
2. Host firewall: nftables default-drop inbound, set by cloud-init, on every core droplet. Allow established/related and loopback only.
3. Spacelift plan policy (Rego) that denies any inbound rule attached to core tags. Add tests next to the existing push policy tests.
4. Continuous proof: an external check that core public IPs show zero open ports (Uptime Kuma TCP monitors expected to fail, or a scheduled scan from home). Document how it alerts (ntfy, `homelab-critical`).
5. IPv6: confirm whether it is enabled on droplets; if it is, every layer above must cover it.

### 2. Private Droplets go on the roadmap as "later, not never"

Add to the Roadmap and a new wiki page ("Why Not Private Droplets (Yet)"):
- Triggers to revisit: ceiling past roughly $75 to $80, a need for a static egress IP for allowlisting, or a compliance-style reason.
- Migration plan: recreate connectors one at a time (two-connector setup keeps access up), NAT gateway as VPC default route, break-glass runbook that assumes no Droplet Console (access through the surviving connector, or rebuild from code).
- Note the 25 Mbps per increment limit and how it would distort the iperf3 ZTNA measurements.
- VERIFY: the `digitalocean_droplet` argument for disabling public networking and the minimum provider version that supports it.

### 3. New stage: public edge (DMZ)

Separate VPC, not a subnet (DO VPCs are flat; the VPC is the isolation unit).
- `digitalocean_vpc` named `rns-dmz`, same region, CIDR that does not overlap core (for example 10.30.0.0/24; check what core uses).
- No VPC peering to core.
- One droplet, smallest sensible size (around $6, VERIFY current price), tagged `rns-dmz`.
- Immutable: no SSH, no Twingate connector, no admin path. All config through cloud-init from the repo. Changing anything means a PR, a Spacelift plan, and a rebuild. Break-glass is the DO Droplet Console (it is a standard droplet).
- Reserved IP in its own resource plus `digitalocean_reserved_ip_assignment`, so rebuilds keep the address.
- Tag-based Cloud Firewall. Inbound only:
  - Reticulum `TCPServerInterface` port (4242 unless the config says otherwise)
  - i2pd pinned inbound port (TCP and UDP)
  - Meshtastic MQTT over TLS (8883)
  - iperf3 5201, sourced ONLY from my home WAN IP (a variable sourced from Doppler) and the core connectors' egress IPs
- Outbound: start from what each service needs, not 1-65535. Document what remains open and why.
- East-west: if more droplets join the DMZ later, deny DMZ-to-DMZ by default with tag rules.
- nftables default-drop on the host as well, mirroring the Cloud Firewall.

Services on the DMZ droplet, all via cloud-init:
- `rnsd` with `enable_transport = Yes` and a `TCPServerInterface`.
- `lxmd` as an LXMF propagation node, with storage and transfer limits set so it cannot fill the disk.
- i2pd: SAM bound to 127.0.0.1 only, inbound port pinned, transit bandwidth capped (low bandwidth class and share percentage) so it does not eat the transfer allowance. Reticulum's I2P interface points at the local SAM.
- Mosquitto for Meshtastic: TLS plus authentication, no anonymous access. Open decision for the design doc: private broker for my nodes only, or a public broker. Default to private.
- iperf3 server: built-in auth (`--rsa-private-key-path`, `--authorized-users-path`), key material from Doppler. VERIFY the distro package is built with OpenSSL auth support. Pin a current version; iperf3 has had memory-safety CVEs.
- Run every service as an unprivileged user with systemd hardening where practical.
- VERIFY current Reticulum, lxmd and i2pd config option names against their docs; they have changed between releases.

Logging from the DMZ (open decision for the design doc):
- Option A (recommended): Twingate headless client with a service account whose only resource is the ingest port on the home disposable relay (the same pattern as the malware net and honeypot paths). Never straight to the SIEM.
- Option B: no log shipping at first, DO monitoring only.
- Note that option A puts a scoped credential on an internet-facing host, and say what that credential can and cannot reach.

Cost: this stage pushes the running total past $30 (Stage 3 already lands at $29). The design doc must present: raise the ceiling (to what), defer something, or move pieces elsewhere. Add a monthly transfer estimate for i2pd, Reticulum and iperf3, since transfer does not appear in plans.

### 4. iperf3 measurement design (DMZ plus Stage 4)

- Same endpoint, two paths: a direct path from home to the DMZ public IP, and a ZTNA path through a Twingate resource whose address is the DMZ droplet's public IP, reached through the core connectors. VERIFY that Twingate resources can target a public IP this way and how egress appears.
- Cheap and frequent: UDP at a low fixed bitrate (for example `-u -b 1M -t 5`) or blackbox TCP probes on both paths every few minutes, for latency, jitter and loss.
- Expensive and rare: full throughput once or twice a day at a jittered time, capped with `-n` bytes, single stream and `-P 4`, upload and `-R`.
- Serialize tests (iperf3 serves one client at a time).
- Home side (document only, it lives on-prem): Prometheus iperf3 exporter (VERIFY the maintained option), labels `path`, `direction`, `proto`, `streams`, `twingate_mode` (p2p or relay, read from the Twingate client).
- Transfer math in `docs/cost.md`. DO bills outbound only, so `-R` and connector egress are the costly directions. VERIFY the current allowance.
- Note in the docs that shared-vCPU droplets will cap absolute throughput below my 1 Gbps line; the value is the delta and the trend.

### 5. Stage 3 design amendments (workload host)

Amend the existing Stage 3 draft; do not start a new one.
- Cloud Uptime Kuma on the workload host, viewed over Twingate. It probes only public surfaces (Pixelfed, Lemmy, Reticulum port, MQTT, Function URLs) and never checks anything over Twingate, so it stays an outside view. The home Uptime Kuma and the cloud one heartbeat each other, alerting to ntfy.
- LLM access: the Twingate resource for the daemons points at a LiteLLM proxy on the home AI VLAN, never at Ollama directly. One virtual key per daemon, scoped to one model and rate limited. LiteLLM itself is on-prem and out of scope; document the contract (host, port, key per daemon in Doppler).
- Discord: penguin-overlord uses the gateway (outbound websocket, slash commands included), so no inbound.
- Stream-Daemon follow-up issue: Twitch EventSub over the WebSocket transport (outbound) instead of webhooks. VERIFY current EventSub WebSocket support for `stream.online`.
- Discord-to-Matrix bridge, decision order:
  1. etke.cc's hosted bridge (no inbound, preferred).
  2. Self-hosted mautrix-discord using mautrix-wsproxy, so the bridge dials out. VERIFY that etke.cc will run wsproxy.
  3. Self-hosted behind DMZ ingress: TLS, inbound restricted to etke.cc server IPs, `hs_token` checked. Last resort.

### 6. Webhook receivers on DO Functions (not a droplet)

- Each Function verifies the sender's signature, writes the event to the Spaces bucket from Stage 3, and returns. Consumers poll the bucket. The workload host keeps zero inbound.
- Initial receivers to design: YouTube WebSub (Boon-Tube-Daemon), Kick webhooks (Stream-Daemon), GitHub webhooks for the home findings platform (home pulls from the bucket; GitHub never reaches my LAN).
- Star-Daemon keeps polling (stars I give cannot come from webhooks).
- VERIFY DO Functions free allowance, how Functions are managed (OpenTofu provider support versus `doctl serverless`), and how the cost gate can see them.

### 7. Honeypot: design doc only, outside CAH's apply path

- Separate account or provider, never the CAH project, for abuse reports, API token isolation and blast radius.
- Options to compare: T-Pot CE sensor (about 8 GB RAM and 128 GB disk; too expensive on DO, so price Oracle Always Free ARM and Hetzner; VERIFY T-Pot arm64 support), or single-purpose honeypots on a small droplet (Cowrie, OpenCanary, Dionaea, Conpot). Beelzebub is acceptable only if it does not use my home LLM.
- Logs: one-way push to the home disposable relay over a Twingate service account scoped to the relay ingest port only, feeding the on-prem T-Pot Hive and SIEM from there.
- VERIFY each candidate provider's acceptable use policy on honeypots.

### 8. PeerTube

Note in the Roadmap that PeerTube is a DMZ-class workload (public web plus federation, transcoding, object storage) and needs its own costed stage. No design work now.

## PR order

1. Stage 1 hardening follow-ups: nftables default-drop in cloud-init, the inbound-deny Rego policy with tests, IPv6 check, external zero-open-ports check documented. Include the existing open follow-up of restricting the metadata endpoint to root if it is not done yet, since the DMZ and iperf3 credentials depend on it.
2. Design doc for the public edge stage (sections 3 and 4), with costs, open decisions and the VERIFY results. Doc only.
3. Stage 3 design amendments (sections 5 and 6). Doc only.
4. Wiki and Roadmap: the new stage, "Why Not Private Droplets (Yet)", the honeypot design doc, the PeerTube note, an updated architecture diagram showing the zones (core, DMZ, Functions, separate-account honeypot, home), and Threat Model updates for the new internet-facing surface.
5. After I approve PR 2 and the cost decision: the DMZ stack implementation (OpenTofu layer, cloud-init, firewall, reserved IP, tests, cost gate update).

## Each PR description must include

- What changed and why, in plain language.
- Plan expectation: which resources are created, changed or destroyed. If anything existing would be modified or replaced unexpectedly, stop and flag it.
- Cost delta and the new running total.
- VERIFY items checked, with the doc links used, and anything that could not be confirmed.
- Follow-up issues for app repos.
