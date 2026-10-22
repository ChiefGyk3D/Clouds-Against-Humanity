locals {
  default_outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
  # The defaults carry no destinations, so they keep the any-address pair below.
  outbound = concat(
    [for r in local.default_outbound : merge(r, { destinations = [] })],
    var.extra_outbound_rules,
  )

  # Names use resource_key when it is set and region otherwise.
  name_key = var.resource_key != "" ? var.resource_key : var.region
}

# Inbound is deny-all: DigitalOcean denies all inbound traffic that no rule
# allows, and inbound_from_tag_rules is empty by default. When it lists
# something, each rule admits only droplets that carry this firewall's own tag
# (source_tags), never an address. inbound_from_other_tags does the same for
# another group's tag (one tag per rule), so nothing outside the tagged group gets in.
# The sending side is the other half: DigitalOcean allows outbound traffic only
# when an outbound rule permits it (replies to an admitted connection are
# stateful, a new connection is not), so outbound_to_tag_rules opens the same
# kind of rule outward, to droplets carrying this firewall's own tag
# (destination_tags), never to an address.
#
# Trivy DIG-0003 flags egress to any address. It is accepted here: the
# any-address outbound rules are restricted to specific ports (never "all"),
# an extra rule may name destinations to narrow itself to known addresses,
# inbound is zero unless a rule admits the firewall's own tag, tag-scoped
# outbound rules name no address at all, and the hosts these droplets must
# reach (Twingate relays, package mirrors, DNS and NTP servers) have no fixed
# addresses, so there is no address list to pin.
#trivy:ignore:AVD-DIG-0003
resource "digitalocean_firewall" "this" {
  name = "${var.layer}-${local.name_key}-${var.purpose}"
  tags = [var.tag]

  # A precondition rather than a variable validation: it compares two variables,
  # which a validation cannot do on older OpenTofu. A rule for the firewall's own
  # tag in an "other" list would duplicate one in the own-tag lists (rules are
  # set-like), so it is rejected.
  lifecycle {
    precondition {
      condition     = alltrue([for r in concat(var.inbound_from_other_tags, var.outbound_to_other_tags) : r.tag != var.tag])
      error_message = "inbound_from_other_tags and outbound_to_other_tags are for OTHER tags; use inbound_from_tag_rules or outbound_to_tag_rules for the firewall's own tag."
    }
  }

  dynamic "inbound_rule" {
    for_each = var.inbound_from_tag_rules
    content {
      protocol    = inbound_rule.value.protocol
      port_range  = inbound_rule.value.port_range
      source_tags = [var.tag]
    }
  }

  # Appended after the existing inbound rules so a call that leaves
  # inbound_from_other_tags at its default renders exactly what it did before.
  dynamic "inbound_rule" {
    for_each = var.inbound_from_other_tags
    content {
      protocol    = inbound_rule.value.protocol
      port_range  = inbound_rule.value.port_range
      source_tags = [inbound_rule.value.tag]
    }
  }

  dynamic "outbound_rule" {
    for_each = local.outbound
    content {
      protocol   = outbound_rule.value.protocol
      port_range = outbound_rule.value.port_range
      # No destinations listed (every default rule, and any extra rule that
      # leaves the list out) renders the any-address pair exactly as before.
      # A list renders only what it names, so an IPv4-only list opens no IPv6.
      destination_addresses = length(outbound_rule.value.destinations) == 0 ? ["0.0.0.0/0", "::/0"] : outbound_rule.value.destinations
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
  # Appended last, for the same reason as the inbound block above.
  dynamic "outbound_rule" {
    for_each = var.outbound_to_other_tags
    content {
      protocol         = outbound_rule.value.protocol
      port_range       = outbound_rule.value.port_range
      destination_tags = [outbound_rule.value.tag]
    }
  }
}
