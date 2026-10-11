mock_provider "digitalocean" {}

variables {
  layer    = "foundation"
  region   = "tor1"
  ip_range = "10.78.0.0/24"
}

run "name_follows_layer_region_role" {
  command = plan
  assert {
    condition     = digitalocean_vpc.this.name == "foundation-tor1-vpc"
    error_message = "VPC name must be <layer>-<region>-vpc."
  }
  assert {
    condition     = digitalocean_vpc.this.region == "tor1"
    error_message = "VPC must be created in the requested region."
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
