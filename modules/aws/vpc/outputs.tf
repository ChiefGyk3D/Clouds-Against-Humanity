# The module contract (design section 5): id, ip_range, name.
output "id" {
  value = aws_vpc.this.id
}

output "ip_range" {
  value = aws_vpc.this.cidr_block
}

output "name" {
  value = local.name
}

# AWS extension: machines launch into a subnet, not into the VPC itself.
output "subnet_id" {
  value = aws_subnet.public.id
}
