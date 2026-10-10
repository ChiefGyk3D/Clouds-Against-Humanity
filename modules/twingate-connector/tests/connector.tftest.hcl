mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  layer            = "access"
  region           = "nyc3"
  vpc_id           = "vpc-test"
  tags             = ["cah-baseline-nyc3", "cah-connector-nyc3"]
  size             = "s-1vcpu-1gb"
  ssh_public_key   = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest test"
  twingate_network = "acme"
}

run "droplet_is_tagged_at_creation_inside_the_vpc" {
  command = plan
  assert {
    condition     = contains(digitalocean_droplet.connector.tags, "cah-baseline-nyc3")
    error_message = "The baseline tag must be on the droplet at creation."
  }
  assert {
    condition     = digitalocean_droplet.connector.vpc_uuid == "vpc-test"
    error_message = "The connector must live in the given VPC."
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-nyc3-connector"
    error_message = "Name must be <layer>-<region>-connector."
  }
}

run "no_paid_extras_and_no_ipv6" {
  command = plan
  assert {
    condition     = digitalocean_droplet.connector.size == "s-1vcpu-1gb"
    error_message = "Size must come from the variable."
  }
  assert {
    condition     = digitalocean_droplet.connector.backups == false && digitalocean_droplet.connector.ipv6 == false
    error_message = "Backups and IPv6 must stay off (they are unpriced)."
  }
}

run "cloud_init_installs_connector_for_the_network" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_NETWORK='acme'")
    error_message = "cloud-init must set the Twingate network."
  }
}

run "tokens_never_leave_the_module" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/outputs.tf"), "token")
    error_message = "No output may mention or expose connector tokens."
  }
}
