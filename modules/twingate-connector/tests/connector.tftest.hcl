mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  layer               = "access"
  region              = "nyc3"
  vpc_id              = "vpc-test"
  tags                = ["cah-baseline-nyc3", "cah-connector-nyc3"]
  size                = "s-1vcpu-1gb"
  remote_network_id   = "remote-network-test"
  ssh_key_fingerprint = "aa:bb:cc:dd"
  instance            = "a"
  twingate_network    = "acme"
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
    condition     = digitalocean_droplet.connector.name == "access-nyc3-connector-a"
    error_message = "Name must be <layer>-<region>-connector-<instance>."
  }
}

run "connector_and_droplet_names_carry_the_instance" {
  command = plan
  variables {
    instance = "b"
  }
  assert {
    condition     = twingate_connector.this.name == "access-nyc3-connector-b" && digitalocean_droplet.connector.name == "access-nyc3-connector-b"
    error_message = "Both the Twingate connector and the droplet must be named with the instance letter."
  }
}

run "shared_site_and_key_come_from_the_caller" {
  command = plan
  assert {
    condition     = twingate_connector.this.remote_network_id == "remote-network-test" && contains(digitalocean_droplet.connector.ssh_keys, "aa:bb:cc:dd")
    error_message = "The connector must use the caller's remote network and SSH key fingerprint."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "twingate_remote_network") && !strcontains(file("${path.module}/main.tf"), "digitalocean_ssh_key")
    error_message = "The remote network and SSH key are shared, so the module must not create them."
  }
}

run "instance_rejects_uppercase" {
  command = plan
  variables {
    instance = "A"
  }
  expect_failures = [var.instance]
}

run "instance_rejects_more_than_one_character" {
  command = plan
  variables {
    instance = "ab"
  }
  expect_failures = [var.instance]
}

run "instance_rejects_empty" {
  command = plan
  variables {
    instance = ""
  }
  expect_failures = [var.instance]
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
    condition     = length(regexall("output \"", file("${path.module}/outputs.tf"))) == 4
    error_message = "outputs.tf must declare exactly 4 outputs. Add one only after proving it carries no connector secret and extending this test."
  }

  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["droplet_name", "droplet_urn", "private_ip", "size"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it here only after proving it carries no connector secret."
  }

  assert {
    condition = !anytrue([
      for v in [output.droplet_name, output.droplet_urn, output.private_ip, output.size] :
      strcontains(tostring(v), "FAKE-ACCESS-TOKEN-1") || strcontains(tostring(v), "FAKE-REFRESH-TOKEN-1")
    ])
    error_message = "A module output carries a connector access or refresh token."
  }
}
