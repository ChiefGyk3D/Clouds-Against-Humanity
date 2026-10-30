# SPDX-License-Identifier: Apache-2.0
# The shared edge network (DMZ): the rns-dmz VPC, its tags and the Cloud Firewall.
# Design: docs/superpowers/specs/2026-10-19-edge-dmz-design.md. It holds no
# droplet: every edge service is its own stack (one droplet each, built from
# modules/edge-host), created and approved later.
# UNAPPLIED and DISABLED: every resource below is count 0 unless edge_enabled is
# true, and the stage is not approved. Turning the switch on is refused until
# cost.json says the network is approved.

locals {
  # Names use resource_key when it is set and region otherwise.
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  on = var.edge_enabled ? 1 : 0

  cost = jsondecode(file("${path.module}/cost.json"))

  # First and last address of an IPv4 CIDR as a number, so two ranges can be
  # compared. OpenTofu has no overlap function.
  vpc_bounds = [
    for o in [split(".", cidrhost(var.vpc_ip_range, 0)), split(".", cidrhost(var.vpc_ip_range, -1))] :
    (tonumber(o[0]) * 16777216) + (tonumber(o[1]) * 65536) + (tonumber(o[2]) * 256) + tonumber(o[3])
  ]
  avoid_bounds = [
    for c in concat([var.core_vpc_ip_range], var.reserved_ranges) : [
      for o in [split(".", cidrhost(c, 0)), split(".", cidrhost(c, -1))] :
      (tonumber(o[0]) * 16777216) + (tonumber(o[1]) * 65536) + (tonumber(o[2]) * 256) + tonumber(o[3])
    ]
  ]
  overlaps_avoided = anytrue([
    for b in local.avoid_bounds : local.vpc_bounds[0] <= b[1] && b[0] <= local.vpc_bounds[1]
  ])

  # Public inbound ports of the shared Cloud Firewall. Only Reticulum and MQTT
  # over TLS (8883, fixed by the design) are listed. i2pd stays closed until its
  # own stack exists (it will pick a random port; that is NOT a security measure),
  # and iperf3 (TCP 5201) stays closed to everyone until an iperf3 stack exists
  # and a variable carries the observed connector addresses. No service is
  # installed yet, and no droplet exists in this stack.
  public_ports = [
    { protocol = "tcp", port_range = tostring(var.reticulum_port) },
    { protocol = "tcp", port_range = "8883" },
  ]

  # Outbound starts from what the built pieces need: DNS, apt mirrors (80, 443)
  # and time. Nothing is opened for services that are not built yet.
  outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
}

# A separate VPC, never peered with core. The VPC is the isolation unit.
resource "digitalocean_vpc" "dmz" {
  count = local.on

  name     = "rns-dmz"
  region   = var.region
  ip_range = var.vpc_ip_range
}

resource "digitalocean_tag" "dmz" {
  count = local.on

  name = "rns-dmz"
}

# A role tag so a second DMZ host later gets its own rules.
resource "digitalocean_tag" "transport" {
  count = local.on

  name = "rns-dmz-transport"
}

# Inbound is the public service ports only. Trivy
# DIG-0001 (inbound from anywhere) and DIG-0003 (egress to anywhere) are
# accepted: the host is public by design, every inbound rule names one port,
# nothing else is open, and the hosts it must reach (package mirrors, DNS and NTP
# servers) have no fixed addresses. The plan policy (.spacelift/policies/plan.rego)
# denies a world-open inbound rule until this firewall's exact address is added
# to its inbound_allowlist in a reviewed pull request.
#trivy:ignore:AVD-DIG-0001
#trivy:ignore:AVD-DIG-0003
resource "digitalocean_firewall" "dmz" {
  count = local.on

  name = "edge-${local.resource_key}-dmz"
  tags = [digitalocean_tag.dmz[0].name]

  dynamic "inbound_rule" {
    for_each = local.public_ports
    content {
      protocol         = inbound_rule.value.protocol
      port_range       = inbound_rule.value.port_range
      source_addresses = ["0.0.0.0/0"]
    }
  }

  dynamic "outbound_rule" {
    for_each = local.outbound
    content {
      protocol              = outbound_rule.value.protocol
      port_range            = outbound_rule.value.port_range
      destination_addresses = ["0.0.0.0/0", "::/0"]
    }
  }
}
