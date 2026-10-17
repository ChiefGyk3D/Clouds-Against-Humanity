locals {
  name = "${var.layer}-${var.region}-vpc"
}

# On AWS the VPC is only an address space. A machine reaches the internet only
# when a gateway, a route to it and an association with the subnet all exist,
# so each is a resource here, not a default the module hopes for.
resource "aws_vpc" "this" {
  cidr_block = var.ip_range

  # Both are the AWS defaults, written out so the plan shows the choice.
  # IPv6 stays off: the egress rules and the cost gate assume IPv4 only.
  assign_generated_ipv6_cidr_block = false
  enable_dns_support               = true
  enable_dns_hostnames             = false

  tags = { Name = local.name }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.ip_range
  availability_zone = var.availability_zone

  # Off on purpose: a machine asks for its public address itself
  # (associate_public_ip_address in the connector module), so no other machine
  # ever gets one by accident, and the cost gate can see every address.
  map_public_ip_on_launch = false

  tags = { Name = "${var.layer}-${var.region}-public" }
}

# Free. This is what makes a subnet public rather than private.
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.layer}-${var.region}-igw" }
}

# An explicit route table instead of editing the VPC's main one: the route to
# the internet is visible here and attached to exactly one subnet.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.layer}-${var.region}-public" }
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Every VPC comes with a default security group that allows all traffic between
# its own members and all outbound. Declaring it with no rules empties it, so
# nothing can rely on it by accident (the connector module never uses it).
# The VPC's default network ACL is left as AWS made it (allow all, both ways):
# a custom ACL is stateless and needs return-path ephemeral-port rules, and
# the security group is this project's filter.
resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${var.layer}-${var.region}-default-unused" }
}
