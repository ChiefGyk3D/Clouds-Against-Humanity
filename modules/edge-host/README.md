# edge-host

The public edge host (DMZ): one immutable droplet with no SSH key, no admin
user and no Twingate connector, a reserved IP that survives a rebuild, and a
cloud-init that hardens it (sshd stopped and masked, root password locked,
unattended upgrades, a default-drop nftables host firewall that mirrors the
Cloud Firewall, the metadata-endpoint lock).

**Unapplied.** The stack that calls it, `stacks/50-edge`, ships disabled
(`edge_enabled = false`) and the stage is not approved. Nothing here has run on
a real machine. Design: [edge DMZ design](../../docs/superpowers/specs/2026-10-19-edge-dmz-design.md).

What it does not do, on purpose: it installs no service. Each service
(Reticulum, lxmd, i2pd, Mosquitto, iperf3) is its own stack and droplet, built
and approved later with exact pins verified from that project's releases. There
is no log shipping from the edge until the Twingate headless relay exists.

| Variable | Meaning |
|---|---|
| `public_ports` | Ports open to the internet; the host firewall mirrors them |
| `restricted_ports` | Ports open to named IPv4 ranges only; no source means closed |
| `service` | Which edge service this droplet is for: names the droplet and picks its reboot slot and Doppler config name |
| `project_id` | The existing DigitalOcean project the droplet and reserved IP join |
| `reboot_time` | Default: the service's slot in `reboot-slots.json` (01:00 to 03:00 Eastern) |
| `size` | Droplet size; the stack checks it against `cost.json` |

Outputs: `name`, `droplet_id`, `size`, `reserved_ip`, `host_firewall_rules`
(sensitive), `droplet_urn`, `doppler_config`, `reboot_time`. The rendered user-data is never an output.
