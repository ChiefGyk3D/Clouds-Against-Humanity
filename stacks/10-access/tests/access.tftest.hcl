mock_provider "digitalocean" {
  mock_data "digitalocean_ssh_key" {
    defaults = {
      fingerprint = "aa:bb:cc:dd:ee:ff"
    }
  }
}
mock_provider "twingate" {}

variables {
  region               = "nyc3"
  vpc_id               = "vpc-test"
  project_id           = "project-test"
  baseline_tag         = "cah-baseline-nyc3"
  twingate_network     = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  admin_ssh_key_name   = "existing-key-name"
  admin_user_ids       = ["fake-user-id-1"]
}

run "connector_size_comes_from_the_cost_manifest" {
  command = plan
  assert {
    condition     = module.connector_a.size == one([for r in jsondecode(file("${path.module}/cost.json")).resources : r if r.name == "connector-a"]).size
    error_message = "Connector a's droplet size must be read from cost.json so the cost gate is the single source."
  }
  assert {
    condition     = module.connector_b.size == one([for r in jsondecode(file("${path.module}/cost.json")).resources : r if r.name == "connector-b"]).size
    error_message = "Connector b's droplet size must be read from cost.json so the cost gate is the single source."
  }
  assert {
    condition     = module.connector_a.size == module.connector_b.size
    error_message = "Both connectors must be the same size."
  }
}

run "two_connectors_with_distinct_names" {
  command = plan
  assert {
    condition     = module.connector_a.droplet_name == "access-nyc3-connector-a" && module.connector_b.droplet_name == "access-nyc3-connector-b"
    error_message = "The droplets must be named access-<region>-connector-a and -b."
  }
  assert {
    condition     = module.connector_a.droplet_name != module.connector_b.droplet_name
    error_message = "The two connectors must have distinct names."
  }
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 2
    error_message = "cost.json must list exactly the two connector droplets."
  }
}

run "both_droplets_carry_the_baseline_and_connector_tags" {
  command = plan
  # Module outputs deliberately never expose tags, so read what each module block is given.
  assert {
    condition     = length(regexall("tags\\s*=\\s*\\[var.baseline_tag, digitalocean_tag.connector.name\\]", file("${path.module}/main.tf"))) == 2
    error_message = "Both connector modules must be tagged with the baseline tag and the connector tag."
  }
  assert {
    condition     = length(regexall("depends_on\\s*=\\s*\\[module.connector_firewall\\]", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must wait for the connector firewall."
  }
}

run "project_lists_both_droplets" {
  command = plan

  # The mock provider gives every droplet the same URN, so give each its own.
  override_module {
    target = module.connector_a
    outputs = {
      droplet_name = "a"
      droplet_urn  = "do:droplet:a"
      private_ip   = "10.0.0.1"
      size         = "s-1vcpu-1gb-intel"
    }
  }
  override_module {
    target = module.connector_b
    outputs = {
      droplet_name = "b"
      droplet_urn  = "do:droplet:b"
      private_ip   = "10.0.0.2"
      size         = "s-1vcpu-1gb-intel"
    }
  }

  assert {
    condition     = digitalocean_project_resources.access.resources == toset(["do:droplet:a", "do:droplet:b"])
    error_message = "The project must list both connector droplet URNs."
  }
}

run "site_is_created_once_and_shared" {
  command = plan
  assert {
    condition     = twingate_remote_network.this.name == "access-nyc3" && twingate_remote_network.this.location == "OTHER"
    error_message = "The stack creates one remote network named access-<region>."
  }
  assert {
    condition     = length(regexall("resource \"twingate_remote_network\"", file("${path.module}/main.tf"))) == 1
    error_message = "The remote network must be declared exactly once."
  }
  assert {
    condition     = length(regexall("remote_network_id\\s*=\\s*twingate_remote_network.this.id", file("${path.module}/main.tf"))) == 4
    error_message = "Both connectors and both SSH resources must use the one shared remote network."
  }
}

run "admin_ssh_key_is_looked_up_never_registered" {
  command = plan
  assert {
    condition     = data.digitalocean_ssh_key.admin.name == "existing-key-name"
    error_message = "The stack must look the admin key up by the supplied name."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "resource \"digitalocean_ssh_key\"")
    error_message = "The key already exists on the account (a duplicate gets a 422), so the stack must not register it."
  }
  assert {
    condition     = length(regexall("ssh_key_fingerprint\\s*=\\s*data.digitalocean_ssh_key.admin.fingerprint", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must take the looked-up key's fingerprint."
  }
}

run "an_empty_ssh_key_name_is_rejected" {
  command = plan
  variables {
    admin_ssh_key_name = ""
  }
  expect_failures = [var.admin_ssh_key_name]
}

run "connector_has_its_own_tag_and_a_peer_ssh_only_firewall" {
  command = plan
  assert {
    condition     = digitalocean_tag.connector.name == "cah-connector-nyc3"
    error_message = "Connector tag must be cah-connector-<region>."
  }
  assert {
    condition     = module.connector_firewall.inbound_rule_count == 1
    error_message = "The connector firewall must have exactly one inbound rule (tcp 22 from the connector tag)."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22/cah-connector-nyc3"])
    error_message = "The only inbound rule must be tcp 22 sourced from the connector tag, never an address."
  }
  assert {
    condition     = module.connector_firewall.outbound_rule_count == 8
    error_message = "Connector firewall must be the module's 5 default outbound rules, the 2 Twingate extras and the one tag-scoped SSH rule."
  }
  assert {
    condition = jsonencode(module.connector_firewall.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
      "tcp/30000-31000/0.0.0.0/0,::/0",
      "udp/1-65535/0.0.0.0/0,::/0",
    ]))
    error_message = "Connector firewall outbound must be exactly the five defaults plus tcp 30000-31000 and udp 1-65535 (Twingate peer-to-peer needs outbound UDP to any port), each to 0.0.0.0/0 and ::/0."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.outbound_tag_rules) == jsonencode(["tcp/22/cah-connector-nyc3"])
    error_message = "The only tag-scoped outbound rule must be tcp 22 destined to the connector tag, so a connector can open SSH to its peer and nothing else."
  }
}

run "connector_a_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_a_ssh.name == "cah-nyc3-connector-a-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.protocols.allow_icmp == false
    error_message = "ICMP must not be allowed to the SSH resource."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.protocols.tcp.policy == "RESTRICTED"
    error_message = "TCP must be RESTRICTED."
  }
  assert {
    condition     = toset(twingate_resource.connector_a_ssh.protocols.tcp.ports) == toset(["22"]) && length(twingate_resource.connector_a_ssh.protocols.tcp.ports) == 1
    error_message = "TCP must be restricted to exactly port 22."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.protocols.udp.policy == "DENY_ALL"
    error_message = "UDP must be denied."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.address == module.connector_a.private_ip
    error_message = "The SSH resource must target the private IP."
  }
  assert {
    condition     = one([for g in twingate_resource.connector_a_ssh.access_group : g.group_id]) == twingate_group.admins.id
    error_message = "Access must be granted to the admins group only."
  }
  assert {
    condition     = twingate_group.admins.name == "cah-nyc3-admins"
    error_message = "Access is granted to one named group."
  }
}

run "connector_b_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_b_ssh.name == "cah-nyc3-connector-b-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.protocols.allow_icmp == false
    error_message = "ICMP must not be allowed to the SSH resource."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.protocols.tcp.policy == "RESTRICTED"
    error_message = "TCP must be RESTRICTED."
  }
  assert {
    condition     = toset(twingate_resource.connector_b_ssh.protocols.tcp.ports) == toset(["22"]) && length(twingate_resource.connector_b_ssh.protocols.tcp.ports) == 1
    error_message = "TCP must be restricted to exactly port 22."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.protocols.udp.policy == "DENY_ALL"
    error_message = "UDP must be denied."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.address == module.connector_b.private_ip
    error_message = "The SSH resource must target the private IP."
  }
  assert {
    condition     = one([for g in twingate_resource.connector_b_ssh.access_group : g.group_id]) == twingate_group.admins.id
    error_message = "Access must be granted to the admins group only."
  }
  assert {
    condition     = twingate_group.admins.name == "cah-nyc3-admins"
    error_message = "Access is granted to one named group."
  }
}

run "ssh_resources_are_two_and_each_restricted_to_tcp_22" {
  command = plan
  assert {
    condition     = length(regexall("resource \"twingate_resource\"", file("${path.module}/main.tf"))) == 2
    error_message = "There must be exactly two Twingate resources, one per connector."
  }
  assert {
    condition     = alltrue([for r in [twingate_resource.connector_a_ssh, twingate_resource.connector_b_ssh] : toset(r.protocols.tcp.ports) == toset(["22"]) && length(r.protocols.tcp.ports) == 1 && r.protocols.tcp.policy == "RESTRICTED"])
    error_message = "Each SSH resource must be restricted to TCP 22."
  }
}

run "private_ips_output_is_a_map_of_both_connectors" {
  command = plan
  assert {
    condition     = jsonencode(sort(keys(output.connector_private_ips))) == jsonencode(["a", "b"])
    error_message = "connector_private_ips must be keyed a and b."
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

run "the_two_connectors_reboot_at_different_times" {
  command = plan
  assert {
    condition     = length(regexall("reboot_time\\s*=\\s*\"04:00\"", file("${path.module}/main.tf"))) == 1 && length(regexall("reboot_time\\s*=\\s*\"05:00\"", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must reboot at 04:00 and connector b at 05:00 Eastern, so they never reboot together."
  }
  assert {
    condition     = length(regexall("reboot_time\\s*=", file("${path.module}/main.tf"))) == 2
    error_message = "Each connector module block must set its own reboot_time."
  }
  assert {
    condition     = length(regexall("admin_ssh_public_key\\s*=\\s*var.admin_ssh_public_key", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive the admin public key."
  }
}
