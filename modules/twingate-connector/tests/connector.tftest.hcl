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

run "network_slug_accepts_bare_subdomain" {
  command = plan
  variables {
    twingate_network = "acme-2"
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_NETWORK='acme-2'")
    error_message = "A bare subdomain must be accepted."
  }
}

run "network_slug_rejects_single_quote" {
  command = plan
  variables {
    twingate_network = "acme'; id #"
  }
  expect_failures = [var.twingate_network]
}

run "network_slug_rejects_double_quote" {
  command = plan
  variables {
    twingate_network = "acme\"x"
  }
  expect_failures = [var.twingate_network]
}

run "network_slug_rejects_full_url" {
  command = plan
  variables {
    twingate_network = "https://acme.twingate.com"
  }
  expect_failures = [var.twingate_network]
}

run "install_fails_loudly_when_download_fails" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "pipefail") && strcontains(digitalocean_droplet.connector.user_data, "--proto '=https' --tlsv1.2")
    error_message = "The install pipeline must use pipefail and hardened curl."
  }
}

run "outputs_never_carry_connector_secrets" {
  command = apply

  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "FAKE-ACCESS-TOKEN-1"
      refresh_token = "FAKE-REFRESH-TOKEN-1"
    }
  }

  # Test setup sanity: the fake values really reach the droplet user_data.
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "FAKE-ACCESS-TOKEN-1") && strcontains(digitalocean_droplet.connector.user_data, "FAKE-REFRESH-TOKEN-1")
    error_message = "Test setup: fake tokens must flow into user_data."
  }

  # The test can only name outputs it knows, so pin the output set: adding any
  # output (whatever its name) must be a deliberate edit of this list.
  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([a-z_]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["droplet_name", "droplet_urn", "private_ip", "remote_network_id", "size"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it here only after proving it carries no connector secret."
  }

  assert {
    condition = !anytrue([
      for v in [output.droplet_name, output.droplet_urn, output.private_ip, output.remote_network_id, output.size] :
      strcontains(tostring(v), "FAKE-ACCESS-TOKEN-1") || strcontains(tostring(v), "FAKE-REFRESH-TOKEN-1")
    ])
    error_message = "A module output carries a connector access or refresh token."
  }
}
