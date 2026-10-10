mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  region               = "nyc3"
  vpc_id               = "vpc-test"
  project_id           = "project-test"
  baseline_tag         = "cah-baseline-nyc3"
  twingate_network     = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  admin_user_ids       = ["fake-user-id-1"]
}

run "connector_size_comes_from_the_cost_manifest" {
  command = plan
  assert {
    condition     = module.connector.size == one([for r in jsondecode(file("${path.module}/cost.json")).resources : r if r.name == "connector"]).size
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
  assert {
    condition     = module.connector_firewall.outbound_rule_count == 8
    error_message = "Connector firewall must be the module's 5 default outbound rules plus the 3 Twingate extras."
  }
  assert {
    condition = jsonencode(module.connector_firewall.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
      "tcp/30000-31000/0.0.0.0/0,::/0",
      "udp/19302-19308/0.0.0.0/0,::/0",
      "udp/443/0.0.0.0/0,::/0",
    ]))
    error_message = "Connector firewall outbound must be exactly the five defaults plus tcp 30000-31000, udp 19302-19308 and udp 443, each to 0.0.0.0/0 and ::/0."
  }
}

run "ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_ssh.name == "cah-nyc3-connector-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_resource.connector_ssh.protocols.allow_icmp == false
    error_message = "ICMP must not be allowed to the SSH resource."
  }
  assert {
    condition     = twingate_resource.connector_ssh.protocols.tcp.policy == "RESTRICTED"
    error_message = "TCP must be RESTRICTED."
  }
  assert {
    condition     = toset(twingate_resource.connector_ssh.protocols.tcp.ports) == toset(["22"]) && length(twingate_resource.connector_ssh.protocols.tcp.ports) == 1
    error_message = "TCP must be restricted to exactly port 22."
  }
  assert {
    condition     = twingate_resource.connector_ssh.protocols.udp.policy == "DENY_ALL"
    error_message = "UDP must be denied."
  }
  assert {
    condition     = twingate_resource.connector_ssh.address == module.connector.private_ip
    error_message = "The SSH resource must target the private IP."
  }
  assert {
    condition     = one([for g in twingate_resource.connector_ssh.access_group : g.group_id]) == twingate_group.admins.id
    error_message = "Access must be granted to the admins group only."
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

run "a_baseline_tag_without_the_cah_prefix_is_rejected" {
  command = plan
  variables {
    baseline_tag = "some-other-tag"
  }
  expect_failures = [var.baseline_tag]
}

run "an_empty_admin_list_is_rejected" {
  command = plan
  variables {
    admin_user_ids = []
  }
  expect_failures = [var.admin_user_ids]
}
