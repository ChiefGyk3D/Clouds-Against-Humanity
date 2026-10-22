# SPDX-License-Identifier: Apache-2.0
# The public edge (DMZ), design: docs/superpowers/specs/2026-10-19-edge-dmz-design.md.
# UNAPPLIED and DISABLED: every resource below is count 0 unless edge_enabled is
# true, and the stage is not approved. The cost gate does not price a droplet
# here (cost.json is empty), and turning the switch on is refused until it does.

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

  # The one list both firewalls are built from: the Cloud Firewall below and the
  # host's nftables in the module. 8883 (Meshtastic MQTT over TLS) is fixed by
  # the design; the others come from variables. iperf3 (5201) is restricted.
  public_ports = concat(
    [{ protocol = "tcp", port_range = tostring(var.reticulum_port) }],
    var.i2pd_port == null ? [] : [
      { protocol = "tcp", port_range = tostring(var.i2pd_port) },
      { protocol = "udp", port_range = tostring(var.i2pd_port) },
    ],
    [{ protocol = "tcp", port_range = "8883" }],
  )
  restricted_ports = [
    { protocol = "tcp", port_range = "5201", sources = var.iperf3_allowed_sources },
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

# Inbound is the public service ports plus iperf3 from named sources. Trivy
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

  # With no source the rule is not rendered at all: 5201 stays closed. The test
  # that keeps this IPv4-only reads the variable's validation (tests/test_edge_stack.py).
  dynamic "inbound_rule" {
    for_each = nonsensitive(length(var.iperf3_allowed_sources) > 0) ? [1] : []
    content {
      protocol         = "tcp"
      port_range       = "5201"
      source_addresses = var.iperf3_allowed_sources
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

module "edge_host" {
  count  = local.on
  source = "../../modules/edge-host"

  layer            = "edge"
  region           = var.region
  resource_key     = var.resource_key
  vpc_id           = digitalocean_vpc.dmz[0].id
  tags             = [digitalocean_tag.dmz[0].name, digitalocean_tag.transport[0].name]
  size             = var.droplet_size
  public_ports     = local.public_ports
  restricted_ports = local.restricted_ports
  reboot_time      = var.reboot_time
}
