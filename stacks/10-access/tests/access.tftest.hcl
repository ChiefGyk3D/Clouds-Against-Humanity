mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  region               = "nyc3"
  vpc_id               = "vpc-test"
  project_id           = "project-test"
  baseline_tag         = "cah-baseline-nyc3"
  twingate_network     = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest test"
}

run "connector_size_comes_from_the_cost_manifest" {
  command = plan
  assert {
    condition     = module.connector.size == jsondecode(file("${path.module}/cost.json")).resources[0].size
    error_message = "The droplet size must be read from cost.json so the cost gate is the single source."
  }
}

run "connector_has_its_own_tag_and_outbound_only_firewall" {
  command = plan
  assert {
    condition     = digitalocean_tag.connector.name == "cah-connector-nyc3"
    error_message = "Connector tag must be cah-connector-<region>."
  }
  assert {
    condition     = module.connector_firewall.inbound_rule_count == 0
    error_message = "The connector firewall must also have zero inbound rules."
  }
}

run "ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_ssh.name == "cah-nyc3-connector-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_group.admins.name == "cah-nyc3-admins"
    error_message = "Access is granted to one named group."
  }
}

run "a_quoted_network_value_is_rejected_at_the_stack_boundary" {
  command = plan
  variables {
    twingate_network = "acme\"; rm -rf /"
  }
  expect_failures = [var.twingate_network]
}
