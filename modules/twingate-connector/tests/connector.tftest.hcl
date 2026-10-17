mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  layer               = "access"
  region              = "tor1"
  vpc_id              = "vpc-test"
  tags                = ["cah-baseline-tor1", "cah-connector-tor1"]
  size                = "s-1vcpu-1gb"
  remote_network_id   = "remote-network-test"
  ssh_key_fingerprint = "aa:bb:cc:dd"
  instance            = "a"
  twingate_network    = "acme"

  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  reboot_time          = "03:00"
}

run "droplet_is_tagged_at_creation_inside_the_vpc" {
  command = plan
  assert {
    condition     = contains(digitalocean_droplet.connector.tags, "cah-baseline-tor1")
    error_message = "The baseline tag must be on the droplet at creation."
  }
  assert {
    condition     = digitalocean_droplet.connector.vpc_uuid == "vpc-test"
    error_message = "The connector must live in the given VPC."
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-tor1-connector-a"
    error_message = "Name must be <layer>-<region>-connector-<instance>."
  }
}

run "connector_and_droplet_names_carry_the_instance" {
  command = plan
  variables {
    instance = "b"
  }
  assert {
    condition     = module.bootstrap.name == "access-tor1-connector-b" && digitalocean_droplet.connector.name == "access-tor1-connector-b"
    error_message = "Both the Twingate connector and the droplet must be named with the instance letter."
  }
}

run "shared_site_and_key_come_from_the_caller" {
  command = plan
  assert {
    condition     = contains(digitalocean_droplet.connector.ssh_keys, "aa:bb:cc:dd")
    error_message = "The connector must use the caller's SSH key fingerprint."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "twingate_remote_network") && !strcontains(file("${path.module}/main.tf"), "digitalocean_ssh_key")
    error_message = "The remote network and SSH key are shared, so the module must not create them."
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

run "tokens_never_leave_the_module" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/outputs.tf"), "token")
    error_message = "No output may mention or expose connector tokens."
  }
}

run "outputs_never_carry_connector_secrets" {
  command = apply

  override_resource {
    target = module.bootstrap.twingate_connector_tokens.this
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
    condition     = length(regexall("output \"", file("${path.module}/outputs.tf"))) == 6
    error_message = "outputs.tf must declare exactly 6 outputs. Add one only after proving it carries no connector secret and extending this test."
  }

  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["droplet_name", "droplet_urn", "instance_id", "instance_name", "private_ip", "size"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it here only after proving it carries no connector secret."
  }

  # Each output must be exactly its intended non-secret source. Searching for
  # the fake tokens alone would miss an output that re-encodes the boot data.
  assert {
    condition = (
      output.droplet_name == digitalocean_droplet.connector.name &&
      output.droplet_urn == digitalocean_droplet.connector.urn &&
      output.private_ip == digitalocean_droplet.connector.ipv4_address_private &&
      output.size == digitalocean_droplet.connector.size &&
      output.instance_id == digitalocean_droplet.connector.id &&
      output.instance_name == digitalocean_droplet.connector.name
    )
    error_message = "Every output must be exactly its droplet attribute, never derived from the boot data."
  }

  assert {
    condition = !anytrue([
      for v in [output.droplet_name, output.droplet_urn, output.instance_id, output.instance_name, output.private_ip, output.size] :
      strcontains(tostring(v), "FAKE-ACCESS-TOKEN-1") || strcontains(tostring(v), "FAKE-REFRESH-TOKEN-1")
    ])
    error_message = "A module output carries a connector access or refresh token."
  }
}

# Hardening of the rendered cloud-init. The yamldecode calls double as the
# valid-YAML check: an invalid document fails the run.


# The hardening itself is tested once, in ../twingate-bootstrap. These two runs
# prove this provider actually uses that module's output and does not carry a
# private copy of the cloud-init.

run "boot_data_is_the_shared_bootstraps_output_with_the_hardening_in_it" {
  command = plan
  assert {
    condition     = digitalocean_droplet.connector.user_data == module.bootstrap.user_data
    error_message = "The droplet's boot data must be exactly the shared bootstrap output."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "99-cah-hardening") && strcontains(digitalocean_droplet.connector.user_data, "PasswordAuthentication no")
    error_message = "The shared hardening must reach the droplet."
  }
}

run "this_module_holds_no_private_copy_of_the_bootstrap" {
  command = plan
  assert {
    condition     = !fileexists("${path.module}/cloud-init.yaml.tftpl") && !strcontains(file("${path.module}/main.tf"), "templatefile") && !can(regex("(?m)^resource\\s+\"twingate_", file("${path.module}/main.tf")))
    error_message = "A provider module must call the bootstrap module, not carry its own cloud-init or Twingate resources."
  }
}

run "the_moved_blocks_keep_the_state_addresses" {
  command = plan
  # The exact legacy address and the exact new address, as pairs. Checking only
  # the destination would pass with a wrong "from" and replace live state.
  assert {
    condition     = strcontains(file("${path.module}/main.tf"), "moved {\n  from = twingate_connector.this\n  to   = module.bootstrap.twingate_connector.this\n}")
    error_message = "twingate_connector.this must move to module.bootstrap.twingate_connector.this, or the live plan replaces the connector."
  }
  assert {
    condition     = strcontains(file("${path.module}/main.tf"), "moved {\n  from = twingate_connector_tokens.this\n  to   = module.bootstrap.twingate_connector_tokens.this\n}")
    error_message = "twingate_connector_tokens.this must move to module.bootstrap.twingate_connector_tokens.this, or the live plan replaces the tokens."
  }
  assert {
    condition     = length(regexall("(?m)^moved \\{", file("${path.module}/main.tf"))) == 2
    error_message = "Exactly the two moved blocks are expected."
  }
}

run "resource_key_names_the_droplet_and_the_connector_but_not_the_region" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-tor1-b-connector-a" && module.bootstrap.name == "access-tor1-b-connector-a"
    error_message = "A resource_key must replace the region in the droplet and Twingate connector names."
  }
  assert {
    condition     = digitalocean_droplet.connector.region == "tor1"
    error_message = "The droplet must still be created in the real region."
  }
}

run "an_empty_resource_key_keeps_the_live_name" {
  command = plan
  variables {
    resource_key = ""
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-tor1-connector-a"
    error_message = "An empty resource_key must leave the live droplet name."
  }
}

run "a_commented_admin_key_is_accepted_through_the_connector_module" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest user@host"
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-tor1-connector-a"
    error_message = "A key with a comment must plan."
  }
}

run "timezone_reaches_the_machine" {
  command = plan
  variables {
    timezone = "Europe/Paris"
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "\ntimezone: Europe/Paris\n")
    error_message = "The timezone input must reach the machine's cloud-init."
  }
}

run "timezone_default_is_eastern" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "\ntimezone: America/New_York\n")
    error_message = "Without a timezone the machine must stay on America/New_York."
  }
}

run "telemetry_default_adds_nothing_to_the_droplet_user_data" {
  command = plan
  assert {
    condition     = !strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_LOG_") && !strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_METRICS_") && !strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_LABEL_")
    error_message = "With connector_telemetry unset no telemetry line may reach the droplet."
  }
}

run "telemetry_reaches_the_droplet_user_data" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999, connection_logs = true }
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "      TWINGATE_LOG_ANALYTICS=v3\n      TWINGATE_METRICS_PORT=9999\n")
    error_message = "connector_telemetry must flow through the module into the droplet's user_data."
  }
}

run "metadata_lock_default_adds_nothing_to_the_droplet_user_data" {
  command = plan
  assert {
    condition     = !strcontains(digitalocean_droplet.connector.user_data, "cah-metadata-lock") && !strcontains(digitalocean_droplet.connector.user_data, "nftables")
    error_message = "With metadata_lock unset nothing about it may reach the droplet."
  }
}

run "metadata_lock_reaches_the_droplet_user_data" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "/usr/local/sbin/cah-metadata-lock") && strcontains(digitalocean_droplet.connector.user_data, "--no-block")
    error_message = "metadata_lock must flow through the module into the droplet's user_data."
  }
}

run "host_firewall_default_adds_nothing_to_the_droplet_user_data" {
  command = plan
  assert {
    condition     = !strcontains(digitalocean_droplet.connector.user_data, "cah-host-firewall") && !strcontains(digitalocean_droplet.connector.user_data, "nftables")
    error_message = "With host_firewall unset nothing about it may reach the droplet."
  }
}

run "host_firewall_reaches_the_droplet_user_data" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "/usr/local/sbin/cah-host-firewall") && strcontains(digitalocean_droplet.connector.user_data, "--no-block") && strcontains(digitalocean_droplet.connector.user_data, "policy drop")
    error_message = "host_firewall must flow through the module into the droplet's user_data."
  }
}

run "host_firewall_sources_reach_the_droplet_user_data" {
  command = plan
  variables {
    host_firewall             = true
    host_firewall_ssh_sources = ["10.20.0.0/16"]
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "ssh_sources=\"10.20.0.0/16\"")
    error_message = "host_firewall_ssh_sources must flow through the module into the droplet's user_data."
  }
}
