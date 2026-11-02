# SPDX-License-Identifier: Apache-2.0
# The workload stack ships DISABLED. These tests plan with mocked providers only.
#
# Turning it on is refused while cost.json does not say workload_approved, by a
# precondition on output.workload_enabled. The runs that look at the ENABLED
# shape therefore expect that one failure and still assert on the planned
# resources: the plan is evaluated, it is just never allowed to apply.

mock_provider "digitalocean" {
  mock_data "digitalocean_ssh_key" {
    defaults = {
      fingerprint = "aa:bb:cc:dd:ee:ff"
    }
  }
}
mock_provider "twingate" {}

variables {
  region               = "tor1"
  vpc_id               = "00000000-0000-0000-0000-000000000000"
  project_id           = "00000000-0000-0000-0000-000000000001"
  baseline_tag         = "cah-baseline-tor1"
  connector_tag        = "cah-connector-tor1"
  remote_network_id    = "remote-network-test"
  admin_group_id       = "admin-group-test"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  admin_ssh_key_name   = "existing-key-name"
}

# --- disabled by default -----------------------------------------------------

run "the_stack_is_off_by_default_and_plans_nothing" {
  command = plan
  assert {
    condition     = var.workload_enabled == false
    error_message = "workload_enabled must default to false."
  }
  assert {
    condition     = length(digitalocean_tag.workload) == 0 && length(module.workload_firewall) == 0 && length(module.workload) == 0 && length(digitalocean_project_resources.workload) == 0 && length(twingate_resource.ssh) == 0 && length(twingate_resource.portainer) == 0
    error_message = "With the switch off no tag, firewall, droplet, project attachment or Twingate resource may exist."
  }
  assert {
    condition     = length(data.digitalocean_ssh_key.admin) == 0
    error_message = "With the switch off even the SSH key lookup must not run."
  }
  assert {
    condition     = output.workload_enabled == false && output.workload_tag == null && output.private_ip == null && output.droplet_name == null
    error_message = "With the switch off the outputs are null."
  }
}

run "the_cost_manifest_prices_nothing_and_the_stage_is_unapproved" {
  command = plan
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 0 && jsondecode(file("${path.module}/cost.json")).workload_approved == false
    error_message = "cost.json must stay empty and unapproved until the maintainer approves stage 3."
  }
}

# --- the switch is guarded -----------------------------------------------------

run "turning_the_stack_on_is_refused_while_cost_json_is_unapproved" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
}

# --- the enabled shape (plan is evaluated, apply is refused above) ------------

run "enabled_plan_creates_the_expected_resources" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = length(digitalocean_tag.workload) == 1 && length(module.workload_firewall) == 1 && length(module.workload) == 1 && length(digitalocean_project_resources.workload) == 1 && length(twingate_resource.ssh) == 1 && length(twingate_resource.portainer) == 1
    error_message = "Enabled, the stack plans one tag, one firewall, one droplet module, one project attachment and two Twingate resources."
  }
  assert {
    condition     = digitalocean_tag.workload[0].name == "cah-workload-tor1"
    error_message = "The workload tag must be cah-workload-<key>."
  }
  assert {
    condition     = module.workload[0].size == "s-1vcpu-2gb"
    error_message = "The droplet size must come from cost.json."
  }
  assert {
    condition     = module.workload[0].instance_name == "workload-tor1-docker"
    error_message = "The droplet must be named workload-<key>-docker."
  }
}

run "enabled_resource_key_names_everything_but_the_region" {
  command = plan
  variables {
    workload_enabled = true
    resource_key     = "tor1-b"
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = digitalocean_tag.workload[0].name == "cah-workload-tor1-b" && module.workload[0].instance_name == "workload-tor1-b-docker" && twingate_resource.ssh[0].name == "cah-tor1-b-workload-ssh"
    error_message = "resource_key must name the tag, droplet and Twingate resources."
  }
}

run "the_droplet_is_in_the_vpc_with_both_tags" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = length(regexall("tags\\s*=\\s*\\[var.baseline_tag, digitalocean_tag.workload\\[0\\].name\\]", file("${path.module}/main.tf"))) == 1
    error_message = "The droplet must carry the baseline tag and the workload tag, and no other (in particular not the connector tag)."
  }
  assert {
    condition     = length(regexall("vpc_id\\s*=\\s*var.vpc_id", file("${path.module}/main.tf"))) == 1
    error_message = "The droplet must sit in the VPC the stack is given."
  }
}

# --- the firewall: inbound only from the connector tag --------------------------

run "the_firewall_admits_only_the_connector_tag_on_two_ports" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = module.workload_firewall[0].inbound_rules == tolist(["tcp/22/cah-connector-tor1", "tcp/9443/cah-connector-tor1"])
    error_message = "Inbound must be exactly SSH and Portainer, each sourced from the connector tag."
  }
  assert {
    condition     = module.workload_firewall[0].source_members == tolist(["cah-connector-tor1"])
    error_message = "The only source of any inbound rule is the connector tag."
  }
  assert {
    condition     = module.workload_firewall[0].rule_targets == tolist(["cah-workload-tor1"])
    error_message = "The firewall attaches to the workload tag."
  }
}

run "the_firewall_has_no_address_based_inbound_and_no_wildcard" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = length(regexall("source_addresses|0\\.0\\.0\\.0|::/0|source_droplet_ids|source_load_balancer_uids|source_kubernetes_ids", file("${path.module}/main.tf"))) == 0
    error_message = "The stack must not name any inbound source but a tag."
  }
  assert {
    condition     = length(regexall("inbound_from_tag_rules", file("${path.module}/main.tf"))) == 0
    error_message = "inbound_from_tag_rules admits the firewall's own tag; this stack admits the connector tag only (inbound_from_other_tags)."
  }
}

run "the_firewall_keeps_the_default_outbound_set_and_adds_none" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = module.workload_firewall[0].outbound_rules == tolist(["tcp/443/0.0.0.0/0,::/0", "tcp/53/0.0.0.0/0,::/0", "tcp/80/0.0.0.0/0,::/0", "udp/123/0.0.0.0/0,::/0", "udp/53/0.0.0.0/0,::/0"])
    error_message = "Outbound must be the firewall module's five defaults and nothing else (no connector 30000-31000 or udp 1-65535)."
  }
  assert {
    condition     = length(regexall("extra_outbound_rules", file("${path.module}/main.tf"))) == 0
    error_message = "The workload firewall adds no outbound rule."
  }
}

# --- Twingate: one narrow resource per port -----------------------------------

run "twingate_gets_one_resource_per_port_and_nothing_else" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = twingate_resource.ssh[0].name == "cah-tor1-workload-ssh" && twingate_resource.portainer[0].name == "cah-tor1-workload-portainer"
    error_message = "Resources must be cah-<key>-workload-ssh and cah-<key>-workload-portainer."
  }
  assert {
    condition     = twingate_resource.ssh[0].protocols.tcp.policy == "RESTRICTED" && twingate_resource.ssh[0].protocols.tcp.ports == toset(["22"]) && twingate_resource.ssh[0].protocols.udp.policy == "DENY_ALL" && twingate_resource.ssh[0].protocols.allow_icmp == false
    error_message = "The SSH resource must allow TCP 22 only."
  }
  assert {
    condition     = twingate_resource.portainer[0].protocols.tcp.policy == "RESTRICTED" && twingate_resource.portainer[0].protocols.tcp.ports == toset(["9443"]) && twingate_resource.portainer[0].protocols.udp.policy == "DENY_ALL" && twingate_resource.portainer[0].protocols.allow_icmp == false
    error_message = "The Portainer resource must allow TCP 9443 only."
  }
  assert {
    condition     = twingate_resource.ssh[0].remote_network_id == "remote-network-test" && twingate_resource.portainer[0].remote_network_id == "remote-network-test"
    error_message = "Both resources live in the given remote network."
  }
  assert {
    condition     = length(regexall("\"twingate_resource\"", file("${path.module}/main.tf"))) + length(regexall("\"twingate_resource\"", file("${path.module}/workload_web.tf"))) + length(regexall("\"twingate_resource\"", file("${path.module}/outputs.tf"))) + length(regexall("\"twingate_resource\"", file("${path.module}/variables.tf"))) == 3
    error_message = "Exactly three Twingate resource blocks across the stack's files (ssh and Portainer in main.tf, the for_each web resource in workload_web.tf): no Docker API resource, ever."
  }
  assert {
    condition     = length(setintersection(twingate_resource.ssh[0].protocols.tcp.ports, toset(["2375", "2376"]))) == 0 && length(setintersection(twingate_resource.portainer[0].protocols.tcp.ports, toset(["2375", "2376"]))) == 0
    error_message = "No planned Twingate resource may allow the Docker API ports 2375 or 2376."
  }
  assert {
    condition     = length(regexall("(?i)2375|2376|ALLOW_ALL|[01]\\s*-\\s*65535", file("${path.module}/main.tf"))) + length(regexall("(?i)2375|2376|ALLOW_ALL|[01]\\s*-\\s*65535", file("${path.module}/workload_web.tf"))) == 0
    error_message = "No rule in the stack may allow the Docker API ports or every port."
  }
}

# --- inputs are validated -----------------------------------------------------

run "a_bad_region_is_refused" {
  command = plan
  variables {
    region = "Toronto"
  }
  expect_failures = [var.region]
}

run "the_baseline_tag_must_be_a_baseline_tag" {
  command = plan
  variables {
    baseline_tag = "something-else"
  }
  expect_failures = [var.baseline_tag]
}

run "the_connector_tag_must_be_a_connector_tag" {
  command = plan
  variables {
    connector_tag = "cah-workload-tor1"
  }
  expect_failures = [var.connector_tag]
}

run "an_empty_remote_network_is_refused" {
  command = plan
  variables {
    remote_network_id = ""
  }
  expect_failures = [var.remote_network_id]
}

run "an_empty_admin_group_is_refused" {
  command = plan
  variables {
    admin_group_id = ""
  }
  expect_failures = [var.admin_group_id]
}

run "a_bad_admin_key_is_refused" {
  command = plan
  variables {
    admin_ssh_public_key = "not a key"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "a_bad_reboot_time_is_refused" {
  command = plan
  variables {
    reboot_time = "3:30"
  }
  expect_failures = [var.reboot_time]
}

run "the_reboot_time_may_not_sit_on_a_connector_window" {
  command = plan
  variables {
    reboot_time = "04:00"
  }
  expect_failures = [var.reboot_time]
}

run "a_bad_resource_key_is_refused" {
  command = plan
  variables {
    resource_key = "Bad Key"
  }
  expect_failures = [var.resource_key]
}

run "a_floating_portainer_version_is_refused" {
  command = plan
  variables {
    portainer_version = "latest"
  }
  expect_failures = [var.portainer_version]
}

run "a_portainer_tag_without_a_digest_is_refused" {
  command = plan
  variables {
    portainer_version = "2.45.3"
  }
  expect_failures = [var.portainer_version]
}

# --- the optional onion service flag (issue #391; default off, nothing applied) --

run "the_onion_flag_defaults_to_off_and_the_effective_output_is_false" {
  command = plan
  assert {
    condition     = var.onion_service_enabled == false && output.onion_service_enabled == false
    error_message = "onion_service_enabled must default to false."
  }
}

run "the_onion_flag_is_handed_to_the_module_and_to_nothing_else" {
  command = plan
  assert {
    condition     = length(regexall("onion_service_enabled\\s*=\\s*var\\.onion_service_enabled", file("${path.module}/main.tf"))) == 1
    error_message = "main.tf must pass onion_service_enabled to the docker-host module, once."
  }
  assert {
    condition     = length(regexall("onion_origin_image", file("${path.module}/main.tf"))) == 0
    error_message = "The stack does not choose the origin image: the module's pinned default applies."
  }
}

run "the_onion_flag_alone_creates_nothing" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = length(module.workload) == 0 && length(module.workload_firewall) == 0 && length(digitalocean_tag.workload) == 0
    error_message = "With the master switch off the onion flag must create nothing."
  }
  assert {
    condition     = output.onion_service_enabled == false
    error_message = "The effective output is true only when both switches are on."
  }
}

run "the_onion_flag_with_the_master_switch_changes_no_firewall_rule" {
  command = plan
  variables {
    workload_enabled      = true
    onion_service_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = output.onion_service_enabled == true
    error_message = "Both switches on: the effective output is true."
  }
  assert {
    condition     = module.workload_firewall[0].inbound_rules == tolist(["tcp/22/cah-connector-tor1", "tcp/9443/cah-connector-tor1"]) && module.workload_firewall[0].outbound_rules == tolist(["tcp/443/0.0.0.0/0,::/0", "tcp/53/0.0.0.0/0,::/0", "tcp/80/0.0.0.0/0,::/0", "udp/123/0.0.0.0/0,::/0", "udp/53/0.0.0.0/0,::/0"])
    error_message = "The onion flag must not add, remove or widen any firewall rule."
  }
  assert {
    condition     = length(regexall("\"twingate_resource\"", file("${path.module}/main.tf"))) + length(regexall("\"twingate_resource\"", file("${path.module}/workload_web.tf"))) == 3
    error_message = "The onion flag adds no Twingate resource."
  }
}

# --- the optional workload web ports (issue #437; default empty, nothing applied) --

run "the_web_port_list_defaults_to_empty_and_creates_nothing" {
  command = plan
  assert {
    condition     = length(var.workload_web_ports) == 0 && length(twingate_resource.workload_web) == 0
    error_message = "workload_web_ports must default to empty and create no Twingate resource."
  }
}

run "ports_with_the_master_switch_off_create_nothing" {
  command = plan
  variables {
    workload_web_ports = [8080, 8081]
  }
  assert {
    condition     = length(twingate_resource.workload_web) == 0 && length(module.workload_firewall) == 0
    error_message = "With the master switch off the port list must create no resource and no rule."
  }
}

run "an_empty_list_leaves_the_enabled_rule_set_unchanged" {
  command = plan
  variables {
    workload_enabled = true
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = length(twingate_resource.workload_web) == 0 && module.workload_firewall[0].inbound_rules == tolist(["tcp/22/cah-connector-tor1", "tcp/9443/cah-connector-tor1"])
    error_message = "With the list empty the inbound set is exactly SSH and Portainer and no web resource exists."
  }
}

run "ports_plan_one_narrow_resource_each" {
  command = plan
  variables {
    workload_enabled   = true
    workload_web_ports = [8080, 8443]
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = length(twingate_resource.workload_web) == 2 && twingate_resource.workload_web["8080"].name == "cah-tor1-workload-web-8080" && twingate_resource.workload_web["8443"].name == "cah-tor1-workload-web-8443"
    error_message = "One resource per port, named cah-<key>-workload-web-<port>."
  }
  assert {
    condition     = twingate_resource.workload_web["8080"].protocols.tcp.policy == "RESTRICTED" && twingate_resource.workload_web["8080"].protocols.tcp.ports == toset(["8080"]) && twingate_resource.workload_web["8080"].protocols.udp.policy == "DENY_ALL" && twingate_resource.workload_web["8080"].protocols.allow_icmp == false
    error_message = "A web resource allows its one TCP port only."
  }
  assert {
    condition     = output.workload_web_resource_names == tolist(["cah-tor1-workload-web-8080", "cah-tor1-workload-web-8443"])
    error_message = "The output lists the web resource names."
  }
  assert {
    condition     = twingate_resource.workload_web["8443"].remote_network_id == "remote-network-test"
    error_message = "Web resources live in the given remote network."
  }
}

run "the_firewall_allowance_is_the_connector_tag_and_the_listed_ports_only" {
  command = plan
  variables {
    workload_enabled   = true
    workload_web_ports = [8080, 8443]
  }
  expect_failures = [output.workload_enabled]
  assert {
    condition     = module.workload_firewall[0].inbound_rules == tolist(["tcp/22/cah-connector-tor1", "tcp/8080/cah-connector-tor1", "tcp/8443/cah-connector-tor1", "tcp/9443/cah-connector-tor1"])
    error_message = "Inbound is SSH, Portainer and exactly the listed ports, each from the connector tag."
  }
  assert {
    condition     = module.workload_firewall[0].source_members == tolist(["cah-connector-tor1"])
    error_message = "The only source of any inbound rule is the connector tag."
  }
  assert {
    condition     = module.workload_firewall[0].outbound_rules == tolist(["tcp/443/0.0.0.0/0,::/0", "tcp/53/0.0.0.0/0,::/0", "tcp/80/0.0.0.0/0,::/0", "udp/123/0.0.0.0/0,::/0", "udp/53/0.0.0.0/0,::/0"])
    error_message = "The ports add no outbound rule."
  }
}

run "port_22_is_refused" {
  command = plan
  variables {
    workload_web_ports = [22]
  }
  expect_failures = [var.workload_web_ports]
}

run "the_portainer_port_is_refused" {
  command = plan
  variables {
    workload_web_ports = [9443]
  }
  expect_failures = [var.workload_web_ports]
}

run "a_privileged_port_is_refused" {
  command = plan
  variables {
    workload_web_ports = [1023]
  }
  expect_failures = [var.workload_web_ports]
}

run "a_port_above_65535_is_refused" {
  command = plan
  variables {
    workload_web_ports = [65536]
  }
  expect_failures = [var.workload_web_ports]
}

run "a_fractional_port_is_refused" {
  command = plan
  variables {
    workload_web_ports = [8080.5]
  }
  expect_failures = [var.workload_web_ports]
}

run "duplicate_ports_are_refused" {
  command = plan
  variables {
    workload_web_ports = [8080, 8080]
  }
  expect_failures = [var.workload_web_ports]
}

run "more_than_eight_ports_are_refused" {
  command = plan
  variables {
    workload_web_ports = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009]
  }
  expect_failures = [var.workload_web_ports]
}

run "eight_ports_are_accepted" {
  command = plan
  variables {
    workload_web_ports = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008]
  }
  assert {
    condition     = length(var.workload_web_ports) == 8
    error_message = "Eight ports is the cap and must be accepted."
  }
}
