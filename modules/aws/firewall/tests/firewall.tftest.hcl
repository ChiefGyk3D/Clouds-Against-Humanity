mock_provider "aws" {}

variables {
  layer   = "access"
  region  = "us-east-1"
  purpose = "connector"
  vpc_id  = "vpc-00000000000000000"
}

run "name_follows_layer_region_purpose_inside_the_vpc" {
  command = plan
  assert {
    condition     = aws_security_group.this.name == "access-us-east-1-connector" && output.name == "access-us-east-1-connector"
    error_message = "Name must be <layer>-<region>-<purpose>."
  }
  assert {
    condition     = aws_security_group.this.vpc_id == "vpc-00000000000000000"
    error_message = "The group must belong to the given VPC."
  }
}

run "default_has_no_inbound_rule_at_all" {
  command = apply
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.member) == 0 && length(output.inbound_rules) == 0
    error_message = "With no member rules the group must have zero inbound rules."
  }
  assert {
    condition     = length(output.source_members) == 0 && length(output.destination_members) == 0
    error_message = "A group with only address-based rules has no members."
  }
}

run "no_inline_rules_and_no_allow_all_anywhere" {
  command = plan
  # Inline ingress/egress blocks would fight the separate rule resources, and
  # protocol "-1" is the shape of AWS's default allow-all egress rule. Neither
  # may appear in the module's source.
  assert {
    condition     = !can(regex("(?m)^\\s*(ingress|egress)\\s*(=|\\{)", file("${path.module}/main.tf")))
    error_message = "Rules must be separate aws_vpc_security_group_*_rule resources, never inline blocks."
  }
  assert {
    condition     = !can(regex("\"-1\"|ip_protocol\\s*=\\s*-1", file("${path.module}/main.tf")))
    error_message = "No every-protocol rule may exist: it would be an allow-all."
  }
  assert {
    condition     = alltrue([for r in values(aws_vpc_security_group_egress_rule.internet) : contains(["tcp", "udp"], r.ip_protocol)])
    error_message = "Every egress rule must be tcp or udp."
  }
  assert {
    condition     = alltrue([for r in values(aws_vpc_security_group_egress_rule.internet) : !(r.from_port == 0 && r.to_port == 65535)])
    error_message = "By default no egress rule may open every port."
  }
}

run "default_outbound_is_exactly_these_five_rules" {
  command = plan
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443-443/0.0.0.0/0",
      "tcp/80-80/0.0.0.0/0",
      "tcp/53-53/0.0.0.0/0",
      "udp/53-53/0.0.0.0/0",
      "udp/123-123/0.0.0.0/0",
    ]))
    error_message = "Default outbound must be exactly tcp 443/80/53 and udp 53/123 to 0.0.0.0/0."
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.internet) == 5 && length(aws_vpc_security_group_egress_rule.member) == 0
    error_message = "Exactly five any-address egress rules and no member egress by default."
  }
  assert {
    condition     = alltrue([for r in values(aws_vpc_security_group_egress_rule.internet) : r.cidr_ipv4 == "0.0.0.0/0" && r.cidr_ipv6 == null && r.referenced_security_group_id == null])
    error_message = "Internet egress is IPv4 only and names an address, not a group."
  }
}

run "extra_outbound_is_appended_and_ranges_and_all_parse" {
  command = plan
  variables {
    extra_outbound_rules = [
      { protocol = "tcp", port_range = "30000-31000" },
      { protocol = "udp", port_range = "all" },
    ]
  }
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443-443/0.0.0.0/0",
      "tcp/80-80/0.0.0.0/0",
      "tcp/53-53/0.0.0.0/0",
      "udp/53-53/0.0.0.0/0",
      "udp/123-123/0.0.0.0/0",
      "tcp/30000-31000/0.0.0.0/0",
      "udp/0-65535/0.0.0.0/0",
    ]))
    error_message = "Extra rules are appended; a range keeps its bounds and all means ports 0-65535 of that one protocol."
  }
}

run "inbound_member_rules_name_the_group_never_an_address" {
  command = apply
  variables {
    inbound_from_member_rules = [
      { protocol = "tcp", port_range = "22" },
      { protocol = "udp", port_range = "9999" },
    ]
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.member) == 2
    error_message = "Exactly the listed inbound rules must render."
  }
  assert {
    condition = alltrue([
      for r in values(aws_vpc_security_group_ingress_rule.member) :
      r.referenced_security_group_id == aws_security_group.this.id && r.cidr_ipv4 == null && r.cidr_ipv6 == null && r.prefix_list_id == null
    ])
    error_message = "Every inbound rule must have this group as its source and no address, IPv6 range or prefix list."
  }
  assert {
    condition     = jsonencode(output.inbound_rules) == jsonencode(sort(["tcp/22-22/${aws_security_group.this.id}", "udp/9999-9999/${aws_security_group.this.id}"]))
    error_message = "inbound_rules must describe the resource's real rules."
  }
  assert {
    condition     = jsonencode(output.source_members) == jsonencode([aws_security_group.this.id])
    error_message = "source_members must name the group that is the source."
  }
  assert {
    condition     = length(output.outbound_rules) == 5
    error_message = "Inbound member rules must not change the internet egress set."
  }
}

run "no_ingress_rule_references_the_internet" {
  command = apply
  variables {
    inbound_from_member_rules = [{ protocol = "tcp", port_range = "22" }, { protocol = "udp", port_range = "all" }]
    outbound_to_member_rules  = [{ protocol = "tcp", port_range = "22" }]
  }
  assert {
    condition = length([
      for r in values(aws_vpc_security_group_ingress_rule.member) : r
      if r.cidr_ipv4 == "0.0.0.0/0" || r.cidr_ipv6 == "::/0"
    ]) == 0
    error_message = "No ingress rule may reference 0.0.0.0/0 or ::/0."
  }
  assert {
    condition     = alltrue([for r in values(aws_vpc_security_group_ingress_rule.member) : r.cidr_ipv4 == null && r.cidr_ipv6 == null])
    error_message = "Ingress rules carry no CIDR at all."
  }
}

run "outbound_member_rules_name_the_group_never_an_address" {
  command = apply
  variables {
    outbound_to_member_rules = [{ protocol = "tcp", port_range = "22" }]
  }
  assert {
    condition     = length(aws_vpc_security_group_egress_rule.member) == 1 && length(output.outbound_rules) == 5
    error_message = "One member egress rule beside the five internet ones."
  }
  assert {
    condition = alltrue([
      for r in values(aws_vpc_security_group_egress_rule.member) :
      r.referenced_security_group_id == aws_security_group.this.id && r.cidr_ipv4 == null && r.cidr_ipv6 == null
    ])
    error_message = "Member egress must reach this group, with no address."
  }
  assert {
    condition     = jsonencode(output.destination_members) == jsonencode([aws_security_group.this.id]) && length(output.source_members) == 0
    error_message = "destination_members names the group; source_members stays empty without inbound member rules."
  }
}

run "contract_outputs_are_their_sources" {
  command = apply
  assert {
    condition     = output.id == aws_security_group.this.id && jsonencode(output.rule_targets) == jsonencode([aws_security_group.this.id])
    error_message = "id and rule_targets must be the security group id: the thing machines attach to."
  }
  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["destination_members", "id", "inbound_rules", "name", "outbound_member_rules", "outbound_rules", "rule_targets", "source_members"])
    error_message = "The output set is pinned: add one only deliberately."
  }
}

run "an_inbound_rule_with_an_unknown_protocol_is_rejected" {
  command = plan
  variables {
    inbound_from_member_rules = [{ protocol = "icmp", port_range = "22" }]
  }
  expect_failures = [var.inbound_from_member_rules]
}

run "an_inbound_rule_with_a_bad_port_range_is_rejected" {
  command = plan
  variables {
    inbound_from_member_rules = [{ protocol = "tcp", port_range = "" }]
  }
  expect_failures = [var.inbound_from_member_rules]
}

run "an_outbound_member_rule_with_a_bad_protocol_is_rejected" {
  command = plan
  variables {
    outbound_to_member_rules = [{ protocol = "-1", port_range = "22" }]
  }
  expect_failures = [var.outbound_to_member_rules]
}

run "an_extra_outbound_rule_cannot_be_every_protocol" {
  command = plan
  variables {
    extra_outbound_rules = [{ protocol = "-1", port_range = "all" }]
  }
  expect_failures = [var.extra_outbound_rules]
}

run "an_extra_outbound_rule_with_a_bad_port_is_rejected" {
  command = plan
  variables {
    extra_outbound_rules = [{ protocol = "tcp", port_range = "ssh" }]
  }
  expect_failures = [var.extra_outbound_rules]
}
