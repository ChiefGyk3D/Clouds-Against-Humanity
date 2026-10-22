# Stage 5: Public edge (DMZ) (code written, DISABLED, NOT APPLIED)

> **Unbuilt and unapplied.** `stacks/50-edge` and `modules/edge-host` are written and tested with mocked providers only. The switch `edge_enabled` defaults to `false`, so the stack plans zero resources. The stage is not approved: the `edge` phase in `docs/stages/approved.json` is `planned`, `cost.json` prices nothing and says `edge_network_approved: false`, and the stack is not registered in `.spacelift/config.yml`. Nothing here has run on a real machine or against any cloud API.

Design: [2026-10-19 edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md) (rulings in section 9) and the maintainer's answers on issue #122 (rework tracked in #247). Layout rule: one stack per service ([wiki: build and destroy a stack per service](../wiki/Build-and-Destroy-Stack-Per-Service.md)): each stack boundary is a trust boundary.

## 1. What exists

| Piece | Where | Note |
|---|---|---|
| Shared edge network: VPC `rns-dmz` (default `10.30.0.0/24`), tags `rns-dmz` and `rns-dmz-transport`, Cloud Firewall | `stacks/50-edge` | Own VPC, never peered; the plan refuses a range that overlaps core or `reserved_ranges`. Holds **no droplet** |
| Cloud Firewall rules | `stacks/50-edge` | Inbound: Reticulum (default TCP 4242) and MQTT over TLS (TCP 8883) only. Outbound: DNS, HTTP and HTTPS for packages, NTP. No SSH rule |
| Reusable edge host | `modules/edge-host` | One droplet (no SSH key, IPv6 off, backups off), its reserved IP and assignment, attachment of both to the existing `clouds-against-humanity` project, and a small cloud-init: sshd stopped and masked, root password locked, unattended upgrades, sysctl hardening, metadata-endpoint lock, a default-drop nftables host firewall |

No stack calls `modules/edge-host` yet, and a test keeps it that way until a service stack is approved. The module installs **no service** and has no package-install hook: each service stack brings its own install, with exact versions verified from that project's releases.

Cost: $0.00 while off. The network stack's resources are free types and `cost.json` lists no resources.

## 2. Rulings applied (issue #122 answers)

| # | Ruling | Where it shows |
|---|---|---|
| 1 | i2pd stays closed (no port) until its own stack exists; i2pd then picks a random port. **A random port is not a security measure** (security through obscurity is a flawed one-trick idea). The port is closed in the Cloud Firewall and the host firewall because nothing needs it, not because it is hidden | No i2pd variable or rule exists; a test checks it |
| 2 | No service is installed by this code | No `service_packages`, no install step; test on the template |
| 3 | One Doppler config and one short-lived, read-only token per edge service (the telemetry pattern), nothing shared | The module computes the config name `cah-edge-<service>`; no token is rendered or fetched yet. Each service stack adds its own |
| 4 | iperf3 (TCP 5201) is closed to everyone until an iperf3 stack exists; then its sources come from a variable set to **observed** connector addresses, never guessed | No 5201 rule or iperf3 variable anywhere |
| 5 | Reboot slots, staggered, before the connectors' 04:00 and 05:00 Eastern | `modules/edge-host/reboot-slots.json`: reticulum 01:00, lxmd 01:30, i2pd 02:00, mosquitto 02:30, iperf3 03:00 (Eastern, the default timezone). `reboot_time` is a per-droplet variable that defaults to the service's slot. A test checks that no two slots share a minute, none equals a connector's, and all lie in 01:00 to 03:00 |
| 6 | No Spacelift stanza until each service stack is approved | `.spacelift/config.yml` is untouched; a test keeps the stanza absent |
| 7 | Plan-policy allowlists are keyed by stack id plus resource address and apply per resource or group | **Dependency, not done here:** issue #246 changes `.spacelift/policies/plan.rego`. Until it lands, the existing policy denies a world-open inbound rule, so this firewall would be denied on a tracked run. The peering and core-tag deny rules are part of that work |
| 8 | Droplet and reserved IP join the existing project | `digitalocean_project_resources` in the module, behind the service stack's switch. A service stack takes `project_id` from the foundation stack's `project_id` output, as stack 10 does |
| 9 | No log shipping from the edge until the Twingate headless relay exists | See section 4 |
| 10 | TCP 5201 egress on the core connector firewall | **Dependency, not done here:** waits for the address-aware firewall module change (issue #245). No rule is added |
| 11 | Droplet console and root password behavior | See section 4 (gate, issue #248). No code |

## 3. Migration: per-service stacks (not created yet)

The edge ceiling stays at its existing value in `approved.json` and is raised one approved service at a time. Each service stack is one droplet (built with `modules/edge-host`), a switch that defaults to off, and an empty `cost.json` until approved. For each one, in its own reviewed pull request:

1. The stack (`stacks/5N-edge-<service>`), calling `modules/edge-host` with `count = local.on` and `size = local.edge_droplet.size` (the cost gate holds edge-host calls to the connector's rules), plus the stack's own firewall rules for that service only.
2. The service's install and configuration, with exact versions verified from the project's releases, and its own Doppler config and short-lived read-only token.
3. Cost-gate support for a `reserved_ip` manifest kind and its price (design section 5.6), then a priced `cost.json` and the DigitalOcean total.
4. The `edge` ceiling raise for that service (`scripts/cost_raise.py` prints the diff).
5. The plan-policy allowlist entry (after #246), the Spacelift stanza and Doppler names.
6. The switch.

Planned service stacks, with their slots: Reticulum (01:00), lxmd (01:30), i2pd (02:00, random port), Mosquitto (02:30), iperf3 (03:00, after observed connector addresses and #245). Only the shared network stack exists today.

## 4. Gates and what is not built

- **No log shipping from the edge until the Twingate headless relay exists.** There is no Twingate headless client, relay, or log path home. Until then the edge sends no logs.
- **Droplet console and root password: unverified (issue #248).** The droplet has no SSH key; DigitalOcean may email a root password, and the cloud-init locks root, but neither behavior has been verified. This is a gate before any apply, not a code task.
- No fetched credentials: the one allowed secret-shaped field in user-data (a short-lived, read-only Doppler token for the service's own config) arrives with each service stack; a test pins the allowed set to empty.

## 5. How the switch is guarded

1. Every resource in `stacks/50-edge/main.tf` has `count = local.on`; a test fails if one lacks it.
2. An output precondition refuses `edge_enabled = true` unless `cost.json` carries `edge_network_approved = true`, which changes only in the reviewed change that approves the stage.
3. For service stacks the cost gate already holds `modules/edge-host` calls to the connector's rules: no `for_each`, `count` only as `local.on`, a plain `size` reference, and manifest entries that are 0 only when the switch is verified (defined as `var.<x> ? 1 : 0` and tied to the manifest by a precondition), otherwise equal to the number of calls. It cannot price a reserved IP yet, so no service stack can be switched on.

## 6. Settings and tests

Every variable is typed, validated and listed in [the settings reference](../wiki/Settings-Reference.md). `terraform.tfvars.example` shows the shape with documentation-range values and the switch off. Tests: `tofu test` in `stacks/50-edge` and `modules/edge-host` (mocked providers), `tests/test_edge_stack.py`, `tests/test_cost_check_reserved_ip.py`. Nothing here calls DigitalOcean, Twingate or Spacelift.
