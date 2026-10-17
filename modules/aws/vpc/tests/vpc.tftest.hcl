mock_provider "aws" {}

variables {
  layer    = "foundation"
  region   = "us-east-1"
  ip_range = "10.88.0.0/24"
}

run "names_follow_layer_region_role" {
  command = plan
  assert {
    condition     = aws_vpc.this.tags["Name"] == "foundation-us-east-1-vpc" && output.name == "foundation-us-east-1-vpc"
    error_message = "VPC name must be <layer>-<region>-vpc."
  }
  assert {
    condition     = aws_vpc.this.cidr_block == "10.88.0.0/24" && aws_subnet.public.cidr_block == "10.88.0.0/24"
    error_message = "The VPC and its one subnet use the given range."
  }
}

run "internet_path_is_explicit_and_complete" {
  command = apply
  assert {
    condition     = aws_internet_gateway.this.vpc_id == aws_vpc.this.id
    error_message = "The internet gateway must be attached to this VPC."
  }
  assert {
    condition     = aws_route.internet.destination_cidr_block == "0.0.0.0/0" && aws_route.internet.gateway_id == aws_internet_gateway.this.id && aws_route.internet.route_table_id == aws_route_table.public.id
    error_message = "The explicit route table must send 0.0.0.0/0 to the internet gateway."
  }
  assert {
    condition     = aws_route_table_association.public.subnet_id == aws_subnet.public.id && aws_route_table_association.public.route_table_id == aws_route_table.public.id
    error_message = "The route table must be associated with the public subnet."
  }
  assert {
    condition     = aws_route_table.public.vpc_id == aws_vpc.this.id && aws_subnet.public.vpc_id == aws_vpc.this.id
    error_message = "Subnet and route table belong to this VPC."
  }
}

run "no_implicit_public_addresses_and_no_ipv6" {
  command = plan
  assert {
    condition     = aws_subnet.public.map_public_ip_on_launch == false
    error_message = "The subnet must not hand out public addresses on its own."
  }
  assert {
    condition     = aws_vpc.this.assign_generated_ipv6_cidr_block == false
    error_message = "IPv6 must stay off."
  }
}

run "availability_zone_is_optional_and_passed_through" {
  command = plan
  variables {
    availability_zone = "us-east-1b"
  }
  assert {
    condition     = aws_subnet.public.availability_zone == "us-east-1b"
    error_message = "availability_zone must reach the subnet."
  }
}

run "no_nat_gateway_or_elastic_address" {
  command = plan
  assert {
    condition     = !can(regex("(?m)^resource\\s+\"aws_(nat_gateway|eip)\"", file("${path.module}/main.tf")))
    error_message = "A NAT gateway or elastic address is a recurring charge the cost gate rejects or prices; the VPC module must not create one."
  }
}

run "contract_outputs_are_their_sources" {
  command = apply
  assert {
    condition     = output.id == aws_vpc.this.id && output.ip_range == aws_vpc.this.cidr_block && output.subnet_id == aws_subnet.public.id
    error_message = "Outputs must be exactly their resource attributes."
  }
  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["id", "ip_range", "name", "subnet_id"])
    error_message = "The output set is pinned: the contract three plus subnet_id."
  }
}

run "rejects_public_range" {
  command = plan
  variables {
    ip_range = "8.8.8.0/24"
  }
  expect_failures = [var.ip_range]
}

run "rejects_malformed_range" {
  command = plan
  variables {
    ip_range = "not-a-cidr"
  }
  expect_failures = [var.ip_range]
}

run "rejects_range_aws_cannot_accept" {
  command = plan
  variables {
    ip_range = "10.0.0.0/8"
  }
  expect_failures = [var.ip_range]
}

run "rejects_a_host_address_instead_of_the_network_address" {
  command = plan
  variables {
    ip_range = "10.0.0.1/24"
  }
  expect_failures = [var.ip_range]
}

run "accepts_the_network_address" {
  command = plan
  variables {
    ip_range = "172.16.0.0/16"
  }
  assert {
    condition     = aws_vpc.this.cidr_block == "172.16.0.0/16"
    error_message = "A canonical range must be accepted."
  }
}

run "default_security_group_is_managed_with_no_rules" {
  command = apply
  assert {
    condition     = aws_default_security_group.this.vpc_id == aws_vpc.this.id
    error_message = "The VPC's default security group must be managed by this module."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*(ingress|egress)\\s*(=|\\{)", file("${path.module}/main.tf")))
    error_message = "The default security group must declare no ingress or egress rule."
  }
}
