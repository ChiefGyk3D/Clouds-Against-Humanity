locals {
  name = "${var.layer}-${var.region}-${var.purpose}"

  # The same five outbound ports as the DigitalOcean firewall. Never "all".
  default_outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
  outbound = concat(local.default_outbound, var.extra_outbound_rules)

  # "443" -> 443..443, "30000-31000" -> 30000..31000, "all" -> 0..65535.
  # The protocol stays tcp or udp: the every-protocol rule that would
  # re-create AWS's default allow-all is not expressible through this module.
  address_rules = {
    for r in local.outbound : "${r.protocol}-${r.port_range}" => {
      protocol = r.protocol
      from     = r.port_range == "all" ? 0 : tonumber(split("-", r.port_range)[0])
      to       = r.port_range == "all" ? 65535 : tonumber(reverse(split("-", r.port_range))[0])
    }
  }
  member_ingress_rules = {
    for r in var.inbound_from_member_rules : "${r.protocol}-${r.port_range}" => {
      protocol = r.protocol
      from     = r.port_range == "all" ? 0 : tonumber(split("-", r.port_range)[0])
      to       = r.port_range == "all" ? 65535 : tonumber(reverse(split("-", r.port_range))[0])
    }
  }
  # Keyed by protocol, ports and source group so a reorder changes nothing.
  # The ports are already validated as a number or an ascending range.
  other_group_ingress_rules = {
    for r in var.inbound_from_other_groups : "${r.protocol}-${r.port_range}-${r.security_group_id}" => {
      protocol = r.protocol
      from     = tonumber(split("-", r.port_range)[0])
      to       = tonumber(reverse(split("-", r.port_range))[0])
      source   = r.security_group_id
    }
  }
  member_egress_rules = {
    for r in var.outbound_to_member_rules : "${r.protocol}-${r.port_range}" => {
      protocol = r.protocol
      from     = r.port_range == "all" ? 0 : tonumber(split("-", r.port_range)[0])
      to       = r.port_range == "all" ? 65535 : tonumber(reverse(split("-", r.port_range))[0])
    }
  }
}

# One security group, attached to the machine's network interface when the
# machine launches (vpc_security_group_ids), so there is no unprotected moment.
#
# No ingress or egress block is declared inline. Every rule is its own
# aws_vpc_security_group_*_rule resource below. AWS gives a new group one
# allow-all outbound rule; the AWS provider removes that default when it creates
# a group inside a VPC, so the only egress that exists is what is listed here.
# (UNVERIFIED against a live account: the tests prove the module declares no
# allow-all rule, not what AWS shows after an apply. See the README.)
resource "aws_security_group" "this" {
  name        = local.name
  description = "${var.purpose} machines of ${var.layer} in ${var.region}: no inbound from the internet"
  vpc_id      = var.vpc_id

  tags = { Name = local.name }
}

# Inbound is deny-all: a security group allows nothing in that no rule allows,
# and inbound_from_member_rules is empty by default. When it lists something,
# the source is this group itself (referenced_security_group_id), never an
# address, so only machines wearing this group can connect.
resource "aws_vpc_security_group_ingress_rule" "member" {
  for_each = local.member_ingress_rules

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = aws_security_group.this.id
  ip_protocol                  = each.value.protocol
  from_port                    = each.value.from
  to_port                      = each.value.to
  description                  = "from members of this group, ${each.key}"
}

# Inbound from ANOTHER security group (the telemetry source group, for the
# metrics ports). The source is always referenced_security_group_id; the
# resource sets no cidr_ipv4, cidr_ipv6 or prefix_list_id, and no input of this
# module feeds one, so a rule from an address cannot be written here.
resource "aws_vpc_security_group_ingress_rule" "other_group" {
  for_each = local.other_group_ingress_rules

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = each.value.source
  ip_protocol                  = each.value.protocol
  from_port                    = each.value.from
  to_port                      = each.value.to
  description                  = "from members of ${each.value.source}, ${each.value.protocol} ${each.value.from}-${each.value.to}"

  # This resource is for OTHER groups. A source equal to the target group would
  # admit every machine wearing it (for connectors: connector-to-connector
  # metrics), which is the member rules' job and a separate decision. The id of
  # a group that does not exist yet is unknown at plan time, so this is checked
  # at apply for a first creation and at plan afterwards.
  lifecycle {
    precondition {
      condition     = each.value.source != aws_security_group.this.id
      error_message = "inbound_from_other_groups names this security group itself (${each.value.source}) as a source. Use a different group; rules that admit the group's own members belong in inbound_from_member_rules."
    }
  }
}

# Trivy AWS-0104 flags egress to any address. It is accepted here for the same
# reason as on DigitalOcean: the any-address rules name specific ports (never
# all protocols), inbound is zero unless a rule admits this group's own
# members, and the hosts these machines must reach (Twingate relays, package
# mirrors, DNS and NTP servers) have no fixed addresses to pin. IPv4 only: the
# VPC has no IPv6.
#trivy:ignore:AVD-AWS-0104
resource "aws_vpc_security_group_egress_rule" "internet" {
  for_each = local.address_rules

  security_group_id = aws_security_group.this.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = each.value.protocol
  from_port         = each.value.from
  to_port           = each.value.to
  description       = "internet, ${each.key}"
}

# The sending half of the member rule. A security group is stateful for
# replies, but opening a connection needs an outbound rule at the sender
# whenever the default allow-all is gone.
resource "aws_vpc_security_group_egress_rule" "member" {
  for_each = local.member_egress_rules

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = aws_security_group.this.id
  ip_protocol                  = each.value.protocol
  from_port                    = each.value.from
  to_port                      = each.value.to
  description                  = "to members of this group, ${each.key}"
}
