output "name" {
  value = aws_security_group.this.name
}

# Sorted "<protocol>/<from>-<to>/<cidr>" descriptors for the any-address
# outbound rules, so tests (and stacks) can pin the exact set. No secrets.
output "outbound_rules" {
  value = sort([
    for r in aws_vpc_security_group_egress_rule.internet :
    "${r.ip_protocol}/${r.from_port}-${r.to_port}/${r.cidr_ipv4}"
  ])
}

# Sorted "<protocol>/<from>-<to>/<source group>" descriptors for the inbound rules.
output "inbound_rules" {
  value = sort([
    for r in aws_vpc_security_group_ingress_rule.member :
    "${r.ip_protocol}/${r.from_port}-${r.to_port}/${r.referenced_security_group_id}"
  ])
}

# Sorted descriptors for the outbound rules that reach group members.
output "outbound_member_rules" {
  value = sort([
    for r in aws_vpc_security_group_egress_rule.member :
    "${r.ip_protocol}/${r.from_port}-${r.to_port}/${r.referenced_security_group_id}"
  ])
}

# The module contract (design section 5). Same names on every provider; see
# README.md for the role table.
output "id" {
  description = "Identifier a stack can depend on."
  value       = aws_security_group.this.id

  # Wait for every rule, not just the group: a machine that launches with this
  # group must find its egress rules already in place, or cloud-init's package
  # install races them. (UNVERIFIED ordering until an apply.)
  depends_on = [
    aws_vpc_security_group_ingress_rule.member,
    aws_vpc_security_group_egress_rule.internet,
    aws_vpc_security_group_egress_rule.member,
  ]
}

# What the rules attach to. On AWS this is the security group a machine lists
# in vpc_security_group_ids when it launches.
output "rule_targets" {
  value = [aws_security_group.this.id]

  # Wait for every rule, not just the group: a machine that launches with this
  # group must find its egress rules already in place, or cloud-init's package
  # install races them. (UNVERIFIED ordering until an apply.)
  depends_on = [
    aws_vpc_security_group_ingress_rule.member,
    aws_vpc_security_group_egress_rule.internet,
    aws_vpc_security_group_egress_rule.member,
  ]
}

# Who may reach the targets by membership rather than by address. Here: the
# security groups named as the source of an inbound rule (this group itself).
output "source_members" {
  value = sort(distinct([for r in aws_vpc_security_group_ingress_rule.member : r.referenced_security_group_id]))
}

# What the targets may reach by membership. Here: the security groups named as
# the destination of an outbound rule (this group itself).
output "destination_members" {
  value = sort(distinct([for r in aws_vpc_security_group_egress_rule.member : r.referenced_security_group_id]))
}
