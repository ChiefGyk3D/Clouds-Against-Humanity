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

  # A subnet is only usable once its route table sends traffic to the gateway,
  # so a consumer in the same apply waits for the route and the association.
  depends_on = [
    aws_route.internet,
    aws_route_table_association.public,
  ]
}
