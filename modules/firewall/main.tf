locals {
  default_outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
  outbound = concat(local.default_outbound, var.extra_outbound_rules)
}

# Inbound is deny-all: DigitalOcean denies all inbound traffic that no rule
# allows, and inbound_from_tag_rules is empty by default. When it lists
# something, each rule admits only droplets that carry this firewall's own tag
# (source_tags), never an address, so nothing outside the tagged group gets in.
# The sending side is the other half: DigitalOcean allows outbound traffic only
# when an outbound rule permits it (replies to an admitted connection are
# stateful, a new connection is not), so outbound_to_tag_rules opens the same
# kind of rule outward, to droplets carrying this firewall's own tag
# (destination_tags), never to an address.
#
# Trivy DIG-0003 flags egress to any address. It is accepted here: the
# any-address outbound rules are restricted to specific ports (never "all"),
# inbound is zero unless a rule admits the firewall's own tag, tag-scoped
# outbound rules name no address at all, and the hosts these droplets must
# reach (Twingate relays, package mirrors, DNS and NTP servers) have no fixed
# addresses, so there is no address list to pin.
#trivy:ignore:AVD-DIG-0003
resource "digitalocean_firewall" "this" {
  name = "${var.layer}-${var.region}-${var.purpose}"
  tags = [var.tag]

  dynamic "inbound_rule" {
    for_each = var.inbound_from_tag_rules
    content {
      protocol    = inbound_rule.value.protocol
      port_range  = inbound_rule.value.port_range
      source_tags = [var.tag]
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

  dynamic "outbound_rule" {
    for_each = var.outbound_to_tag_rules
    content {
      protocol         = outbound_rule.value.protocol
      port_range       = outbound_rule.value.port_range
      destination_tags = [var.tag]
    }
  }
}
