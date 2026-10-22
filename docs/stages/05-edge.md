# Stage 5: Public edge (DMZ) (code written, DISABLED, NOT APPLIED)

> **Unbuilt and unapplied.** `stacks/50-edge` and `modules/edge-host` are written and tested with mocked providers only. The switch `edge_enabled` defaults to `false`, so the stack plans zero resources. The stage is not approved: the `edge` phase in `docs/stages/approved.json` is `planned`, the cost manifest prices nothing, and the stack is not registered in `.spacelift/config.yml`. Nothing here has run on a real machine or against any cloud API.

Design: [2026-10-19 edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md) (rulings in section 9). Issue: #122, epic #72.

## 1. What the code builds when the switch is on

| Piece | Where | Note |
|---|---|---|
| VPC `rns-dmz` (default `10.30.0.0/24`) | `stacks/50-edge` | Own VPC, never peered; the plan refuses a range that overlaps core or `reserved_ranges` |
| Tags `rns-dmz` and `rns-dmz-transport` | `stacks/50-edge` | The firewall attaches to the first; the second is the role tag |
| Cloud Firewall | `stacks/50-edge` | Inbound: Reticulum (default 4242), MQTT over TLS (8883), the i2pd port if one is set (TCP and UDP), iperf3 (5201) from named sources only. Outbound: DNS, HTTP and HTTPS for packages, NTP. No SSH rule |
| Droplet, reserved IP and its assignment | `modules/edge-host` | `s-1vcpu-1gb` (design option A), no SSH key, no admin user, IPv6 off, backups off |
| cloud-init | `modules/edge-host/cloud-init.yaml.tftpl` | sshd stopped and masked, root password locked, unattended upgrades, sysctl hardening, metadata-endpoint lock, a default-drop nftables host firewall rendered from the same port lists as the Cloud Firewall |

Cost: $0.00 while off. `cost.json` lists no resources. Design option A adds a $6 droplet (`docs/cost-prices.json`, retrieved 2026-10-21) and a reserved IP that is free while assigned and $5.00 a month when not (design section 5.1, read 2026-10-19), for a running total of $35 with the unbuilt stage 3. See [cost](../cost.md#edge-dmz-estimate-not-approved).

## 2. What it deliberately does not do yet

- **No service is installed or configured.** Reticulum, lxmd, i2pd, Mosquitto and iperf3 need pinned packages and option names checked against the pinned versions (design sections 4.5 and 9). `service_packages` accepts exact pins and installs nothing by default.
- **No log path home.** The Twingate headless client and the relay prerequisites (design 4.6, decisions 5 and 9) are not built.
- **No fetched credentials.** The one allowed secret-shaped field in user-data (a short-lived, read-only Doppler bootstrap token, risk 6) is not part of the template yet; a test pins the allowed set to empty.
- **No plan policy change.** `.spacelift/policies/plan.rego` denies a world-open inbound rule, so this stack's firewall would be denied on a tracked run until its exact address is added to `inbound_allowlist` in a reviewed pull request. The peering and core-tag deny rules from design section 10 are not added either.
- **No Spacelift stack and no Doppler mapping.** A stanza in `.spacelift/config.yml` is what lets a stack load secrets and apply; a test keeps it absent.
- **No TCP 5201 outbound rule on the core connector firewall** (design decision 10).

## 3. How the switch is guarded

1. Every resource and module call in `stacks/50-edge/main.tf` has `count = local.on`; a test fails if one lacks it.
2. An output precondition refuses `edge_enabled = true` unless `cost.json` prices exactly one droplet of `droplet_size` and one `reserved_ip`.
3. The cost gate cannot price those yet: it has no `reserved_ip` manifest kind, and a priced droplet in this stack fails the connector-module count check. So turning the stage on is blocked until the cost-gate change lands (design section 5.6) and the stage is approved.

To approve the stage later, in this order and each as its own reviewed change: the cost-gate support (manifest kind, price table entry, plan check), the `edge` phase and the DigitalOcean total in `approved.json` (`scripts/cost_raise.py` prints the diff), the plan policy allowlist, the Spacelift stanza and Doppler names, then the switch.

## 4. Settings

Every variable is typed, validated and listed in [the settings reference](../wiki/Settings-Reference.md). `terraform.tfvars.example` shows the shape with documentation-range values and the switch off. The owner's home address belongs in `iperf3_allowed_sources`, which is sensitive and comes from Doppler, never from a committed file.

## 5. Tests

`tofu test` in `stacks/50-edge` and `modules/edge-host` (mocked providers), plus `tests/test_edge_stack.py` and `tests/test_cost_check_reserved_ip.py`. Nothing in this stage calls DigitalOcean, Twingate or Spacelift.
