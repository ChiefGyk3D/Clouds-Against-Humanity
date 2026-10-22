# edge-host

The public edge host (DMZ): one immutable droplet with no SSH key, no admin
user and no Twingate connector, a reserved IP that survives a rebuild, and a
cloud-init that hardens it (sshd stopped and masked, root password locked,
unattended upgrades, a default-drop nftables host firewall that mirrors the
Cloud Firewall, the metadata-endpoint lock).

**Unapplied.** The stack that calls it, `stacks/50-edge`, ships disabled
(`edge_enabled = false`) and the stage is not approved. Nothing here has run on
a real machine. Design: [edge DMZ design](../../docs/superpowers/specs/2026-10-19-edge-dmz-design.md).

What it does not do yet, on purpose: it installs no service. The service
packages (Reticulum, lxmd, i2pd, Mosquitto, iperf3), their configuration and
the log path home are open questions in the design (sections 4.5, 4.6, 9);
`service_packages` takes exact pins and installs nothing by default.

| Variable | Meaning |
|---|---|
| `public_ports` | Ports open to the internet; the host firewall mirrors them |
| `restricted_ports` | Ports open to named IPv4 ranges only; no source means closed |
| `service_packages` | Name to exact version; the default installs none |
| `size` | Droplet size; the stack checks it against `cost.json` |

Outputs: `name`, `droplet_id`, `size`, `reserved_ip`, `host_firewall_rules`
(sensitive). The rendered user-data is never an output.
