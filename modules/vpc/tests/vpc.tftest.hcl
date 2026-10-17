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

# resource_key goes into the name; the region argument always takes the region.
run "resource_key_changes_the_name_not_the_region" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_vpc.this.name == "foundation-tor1-b-vpc"
    error_message = "A resource_key must replace the region in the name."
  }
  assert {
    condition     = digitalocean_vpc.this.region == "tor1"
    error_message = "The VPC must still be created in the real region."
  }
}

run "an_empty_resource_key_means_the_region" {
  command = plan
  variables {
    resource_key = ""
  }
  assert {
    condition     = digitalocean_vpc.this.name == "foundation-tor1-vpc"
    error_message = "An empty resource_key must leave the name as before."
  }
}

run "rejects_a_bad_resource_key" {
  command = plan
  variables {
    resource_key = "Not Valid"
  }
  expect_failures = [var.resource_key]
}
