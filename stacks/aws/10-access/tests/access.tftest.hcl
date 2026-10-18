mock_provider "aws" {
  mock_data "aws_ssm_parameter" {
    defaults = {
      insecure_value = "ami-00000000000000000"
    }
  }
  mock_resource "aws_security_group" {
    defaults = {
      id = "sg-00000000000000002"
    }
  }
}
mock_provider "twingate" {}

variables {
  region               = "us-east-1"
  vpc_id               = "vpc-00000000000000001"
  subnet_id            = "subnet-00000000000000001"
  twingate_network     = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  admin_user_ids       = ["fake-user-id-1"]
}

run "connector_size_comes_from_the_cost_manifest" {
  command = plan
  assert {
    condition     = module.connector_a.size == one([for r in jsondecode(file("${path.module}/cost.json")).resources : r if r.name == "connector-a"]).type
    error_message = "Connector a's instance type must be read from cost.json so the cost gate is the single source."
  }
  assert {
    condition     = module.connector_b.size == one([for r in jsondecode(file("${path.module}/cost.json")).resources : r if r.name == "connector-b"]).type
    error_message = "Connector b's instance type must be read from cost.json so the cost gate is the single source."
  }
  assert {
    condition     = module.connector_a.size == module.connector_b.size && module.connector_a.size == "t4g.micro"
    error_message = "Both connectors must be the same size, t4g.micro."
  }
  assert {
    condition     = length(regexall("instance_type\\s*=\\s*local\\.connector_[ab]\\.type", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must take instance_type from local.<name>.type."
  }
}

run "the_manifest_states_what_the_gate_prices" {
  command = plan
  assert {
    condition     = alltrue([for r in jsondecode(file("${path.module}/cost.json")).resources : r.kind == "instance" && r.root_gb == 8 && r.public_ip == true])
    error_message = "Each costed instance must state kind instance, an 8 GiB root disk and a public address."
  }
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 2
    error_message = "cost.json must list exactly the two connectors."
  }
  assert {
    condition     = length(regexall("root_volume_size\\s*=\\s*local\\.connector_[ab]\\.root_gb", file("${path.module}/main.tf"))) == 2
    error_message = "The root disk size must come from cost.json so the plan and the price agree."
  }
}

run "two_connectors_with_distinct_names" {
  command = plan
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a" && module.connector_b.instance_name == "access-us-east-1-connector-b"
    error_message = "The instances must be named access-<region>-connector-a and -b."
  }
}

run "both_connectors_wear_the_one_connector_group_and_wait_for_it" {
  command = plan
  assert {
    condition     = length(regexall("security_group_id\\s*=\\s*one\\(module.connector_firewall.rule_targets\\)", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must take the firewall's single rule target as their one security group."
  }
  assert {
    condition     = length(regexall("depends_on\\s*=\\s*\\[module.connector_firewall\\]", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must wait for the connector firewall."
  }
  assert {
    condition     = length(regexall("subnet_id\\s*=\\s*var.subnet_id", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must launch into the subnet from stack 00."
  }
}

run "connector_group_has_member_only_ssh_and_no_internet_inbound" {
  command = plan
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22-22/sg-00000000000000002"])
    error_message = "The only inbound rule must be tcp 22 sourced from the group itself, never an address."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.outbound_member_rules) == jsonencode(["tcp/22-22/sg-00000000000000002"])
    error_message = "The only member outbound rule must be tcp 22 to the group itself, so a connector can open SSH to its peer and nothing else."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.source_members) == jsonencode(["sg-00000000000000002"]) && jsonencode(module.connector_firewall.destination_members) == jsonencode(["sg-00000000000000002"])
    error_message = "Member rules must name the group itself."
  }
  assert {
    condition = jsonencode(module.connector_firewall.outbound_rules) == jsonencode(sort([
      "tcp/443-443/0.0.0.0/0",
      "tcp/80-80/0.0.0.0/0",
      "tcp/53-53/0.0.0.0/0",
      "udp/53-53/0.0.0.0/0",
      "udp/123-123/0.0.0.0/0",
      "tcp/30000-31000/0.0.0.0/0",
      "udp/1-65535/0.0.0.0/0",
    ]))
    error_message = "Connector outbound must be exactly the five defaults plus tcp 30000-31000 and udp 1-65535 (Twingate peer-to-peer needs outbound UDP to any port)."
  }
}

run "no_inbound_from_an_address_anywhere_in_the_stack" {
  command = plan
  assert {
    condition     = alltrue([for r in module.connector_firewall.inbound_rules : !strcontains(r, "/0.0.0.0/0") && !strcontains(r, "::/0") && !strcontains(r, "cidr")])
    error_message = "No inbound rule may name an address."
  }
  assert {
    condition     = length(regexall("(?i)(ingress|inbound_from_cidr|security_group_rule|aws_security_group\"|cidr_ipv)", file("${path.module}/main.tf"))) == 0
    error_message = "The stack must not declare its own security group rules; the firewall module is the only place."
  }
}

run "site_is_created_once_and_shared" {
  command = plan
  assert {
    condition     = twingate_remote_network.this.name == "access-us-east-1" && twingate_remote_network.this.location == "OTHER"
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

run "connector_a_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_a_ssh.name == "cah-us-east-1-connector-a-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.protocols.allow_icmp == false && twingate_resource.connector_a_ssh.protocols.tcp.policy == "RESTRICTED" && twingate_resource.connector_a_ssh.protocols.udp.policy == "DENY_ALL"
    error_message = "No ICMP, TCP restricted, UDP denied."
  }
  assert {
    condition     = toset(twingate_resource.connector_a_ssh.protocols.tcp.ports) == toset(["22"]) && length(twingate_resource.connector_a_ssh.protocols.tcp.ports) == 1
    error_message = "TCP must be restricted to exactly port 22."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.address == module.connector_a.private_ip
    error_message = "The SSH resource must target the private IP."
  }
  assert {
    condition     = one([for g in twingate_resource.connector_a_ssh.access_group : g.group_id]) == twingate_group.admins.id && twingate_group.admins.name == "cah-us-east-1-admins"
    error_message = "Access must be granted to the one named admins group only."
  }
}

run "connector_b_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_b_ssh.name == "cah-us-east-1-connector-b-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.protocols.allow_icmp == false && twingate_resource.connector_b_ssh.protocols.tcp.policy == "RESTRICTED" && twingate_resource.connector_b_ssh.protocols.udp.policy == "DENY_ALL"
    error_message = "No ICMP, TCP restricted, UDP denied."
  }
  assert {
    condition     = toset(twingate_resource.connector_b_ssh.protocols.tcp.ports) == toset(["22"]) && length(twingate_resource.connector_b_ssh.protocols.tcp.ports) == 1
    error_message = "TCP must be restricted to exactly port 22."
  }
  assert {
    condition     = twingate_resource.connector_b_ssh.address == module.connector_b.private_ip
    error_message = "The SSH resource must target the private IP."
  }
  assert {
    condition     = one([for g in twingate_resource.connector_b_ssh.access_group : g.group_id]) == twingate_group.admins.id
    error_message = "Access must be granted to the admins group only."
  }
}

run "ssh_resources_are_two" {
  command = plan
  assert {
    condition     = length(regexall("resource \"twingate_resource\"", file("${path.module}/main.tf"))) == 2
    error_message = "There must be exactly two Twingate resources, one per connector."
  }
}

run "outputs_are_both_connectors_and_the_group" {
  command = plan
  assert {
    condition     = jsonencode(sort(keys(output.connector_private_ips))) == jsonencode(["a", "b"])
    error_message = "connector_private_ips must be keyed a and b."
  }
  assert {
    condition     = output.connector_security_group_id == "sg-00000000000000002"
    error_message = "The connector security group id must be exported."
  }
}

run "bad_inputs_are_rejected_at_the_stack_boundary" {
  command = plan
  variables {
    twingate_network = "acme\"; rm -rf /"
  }
  expect_failures = [var.twingate_network]
}

run "an_empty_admin_list_is_rejected" {
  command = plan
  variables {
    admin_user_ids = []
  }
  expect_failures = [var.admin_user_ids]
}

run "ids_from_stack_00_must_look_like_ids" {
  command = plan
  variables {
    vpc_id    = "not-a-vpc"
    subnet_id = "not-a-subnet"
  }
  expect_failures = [var.vpc_id, var.subnet_id]
}

run "nothing_in_the_stack_names_an_account_profile_or_key" {
  command = plan
  assert {
    condition     = alltrue([for f in ["main.tf", "variables.tf", "outputs.tf"] : length(regexall("(?i)(profile|access_key|secret_key|assume_role|allowed_account_ids|shared_credentials|[0-9]{12})", file("${path.module}/${f}"))) == 0])
    error_message = "No account id, profile, key or role may appear in the stack code."
  }
  assert {
    condition     = length(regexall("(?i)(profile|access_key|secret_key|assume_role|allowed_account_ids|shared_credentials|[0-9]{12})", replace(file("${path.module}/versions.tf"), "/#[^\n]*/", ""))) == 0
    error_message = "The provider blocks must not name a profile, key, role or account (comments excluded)."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "key_name") && !strcontains(file("${path.module}/main.tf"), "iam_instance_profile")
    error_message = "No AWS key pair and no instance profile."
  }
}

# --- timezone ----------------------------------------------------------------
run "timezone_defaults_to_the_live_zone_and_reaches_both_connectors" {
  command = plan
  assert {
    condition     = var.timezone == "America/New_York"
    error_message = "The default timezone must be the zone the live connectors use."
  }
  assert {
    condition     = length(regexall("timezone\\s*=\\s*var\\.timezone", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive var.timezone."
  }
}

run "connector_telemetry_defaults_to_off_and_plans" {
  command = plan
  assert {
    condition     = length(regexall("connector_telemetry\\s*=\\s*contains\\(var\\.connector_telemetry_instances", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive var.connector_telemetry."
  }
  assert {
    condition     = length(regexall("contains\\(var\\.connector_telemetry_instances, \"a\"\\)", file("${path.module}/main.tf"))) == 1 && length(regexall("contains\\(var\\.connector_telemetry_instances, \"b\"\\)", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must be gated on \"a\" and connector b on \"b\" in connector_telemetry_instances."
  }
}

run "connector_telemetry_enabled_plans" {
  command = plan
  variables {
    connector_telemetry = { log_level = 5, connection_logs = true, metrics_port = 9999, labels = { SITE = "us-east-1" } }
  }
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a"
    error_message = "Enabling telemetry must not change names."
  }
}

run "telemetry_instances_a_only_plans" {
  command = plan
  variables {
    connector_telemetry           = { metrics_port = 9999 }
    connector_telemetry_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a"
    error_message = "Rolling telemetry out to one connector must plan."
  }
}

run "staged_update_keeps_the_unlisted_connectors_previous_telemetry" {
  command = plan
  variables {
    connector_telemetry           = { log_level = 7 }
    connector_telemetry_previous  = { log_level = 5 }
    connector_telemetry_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a"
    error_message = "A staged update must plan."
  }
  assert {
    condition     = length(regexall(": var\\.connector_telemetry_previous", file("${path.module}/main.tf"))) == 2 && !strcontains(file("${path.module}/main.tf"), "telemetry_off")
    error_message = "A connector not listed must receive connector_telemetry_previous, not an empty config."
  }
}

run "telemetry_empty_object_and_explicit_nulls_plan" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = null, log_level = null, status_updates_enabled = null }
  }
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a"
    error_message = "Explicit nulls must plan as unset."
  }
}

run "telemetry_null_object_plans_as_off" {
  command = plan
  variables {
    connector_telemetry = null
  }
  assert {
    condition     = module.connector_a.instance_name == "access-us-east-1-connector-a"
    error_message = "A null connector_telemetry must plan as {} (nullable = false)."
  }
}

run "telemetry_instances_rejects_an_empty_list" {
  command = plan
  variables {
    connector_telemetry_instances = []
  }
  expect_failures = [var.connector_telemetry_instances]
}

run "telemetry_instances_rejects_c" {
  command = plan
  variables {
    connector_telemetry_instances = ["c"]
  }
  expect_failures = [var.connector_telemetry_instances]
}

run "telemetry_instances_rejects_a_repeat" {
  command = plan
  variables {
    connector_telemetry_instances = ["a", "a"]
  }
  expect_failures = [var.connector_telemetry_instances]
}

run "connector_telemetry_rejects_log_level_6" {
  command = plan
  variables {
    connector_telemetry = { log_level = 6 }
  }
  expect_failures = [var.connector_telemetry]
}

run "connector_telemetry_rejects_a_low_metrics_port" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 1023 }
  }
  expect_failures = [var.connector_telemetry]
}

run "connector_telemetry_rejects_the_node_exporter_port" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9100 }
  }
  expect_failures = [var.connector_telemetry]
}

run "connector_telemetry_rejects_a_label_with_a_line_break" {
  command = plan
  variables {
    connector_telemetry = { labels = { SITE = "a\nb" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "timezone_rejects_injection" {
  command = plan
  variables {
    timezone = "UTC\nruncmd: [x]"
  }
  expect_failures = [var.timezone]
}

run "metadata_lock_defaults_to_off_and_is_wired_to_both_connectors" {
  command = plan
  assert {
    condition     = length(regexall("metadata_lock\\s*=\\s*var\\.metadata_lock && contains\\(var\\.metadata_lock_instances", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive var.metadata_lock gated on metadata_lock_instances."
  }
  assert {
    condition     = length(regexall("contains\\(var\\.metadata_lock_instances, \"a\"\\)", file("${path.module}/main.tf"))) == 1 && length(regexall("contains\\(var\\.metadata_lock_instances, \"b\"\\)", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must be gated on \"a\" and connector b on \"b\" in metadata_lock_instances."
  }
  assert {
    condition     = var.metadata_lock == false && jsonencode(var.metadata_lock_instances) == jsonencode(["a", "b"])
    error_message = "metadata_lock must default to false with both instances listed."
  }
}

run "metadata_lock_on_plans" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "Enabling the lock for both connectors must plan."
  }
}

run "metadata_lock_instances_a_plans" {
  command = plan
  variables {
    metadata_lock           = true
    metadata_lock_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "Rolling the lock out to one connector must plan."
  }
}

run "metadata_lock_instances_rejects_an_empty_list" {
  command = plan
  variables {
    metadata_lock_instances = []
  }
  expect_failures = [var.metadata_lock_instances]
}

run "metadata_lock_instances_rejects_c" {
  command = plan
  variables {
    metadata_lock_instances = ["c"]
  }
  expect_failures = [var.metadata_lock_instances]
}

run "metadata_lock_instances_rejects_a_repeat" {
  command = plan
  variables {
    metadata_lock_instances = ["a", "a"]
  }
  expect_failures = [var.metadata_lock_instances]
}

run "host_firewall_defaults_to_off_and_is_wired_to_both_connectors" {
  command = plan
  assert {
    condition     = length(regexall("host_firewall\\s*=\\s*var\\.host_firewall && contains\\(var\\.host_firewall_instances", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive var.host_firewall gated on host_firewall_instances."
  }
  assert {
    condition     = length(regexall("contains\\(var\\.host_firewall_instances, \"a\"\\)", file("${path.module}/main.tf"))) == 1 && length(regexall("contains\\(var\\.host_firewall_instances, \"b\"\\)", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must be gated on \"a\" and connector b on \"b\" in host_firewall_instances."
  }
  assert {
    condition     = length(regexall("host_firewall_ssh_sources\\s*=\\s*var\\.host_firewall_ssh_sources", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive var.host_firewall_ssh_sources."
  }
  assert {
    condition     = var.host_firewall == false && jsonencode(var.host_firewall_instances) == jsonencode(["a", "b"]) && jsonencode(var.host_firewall_ssh_sources) == jsonencode(["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"])
    error_message = "host_firewall must default to false, both instances, the three private blocks."
  }
}

run "host_firewall_on_plans" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "Enabling the firewall for both connectors must plan."
  }
}

run "host_firewall_instances_a_plans" {
  command = plan
  variables {
    host_firewall           = true
    host_firewall_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "Rolling the firewall out to one connector must plan."
  }
}

run "host_firewall_with_metrics_port_metadata_lock_and_custom_sources_plans" {
  command = plan
  variables {
    host_firewall             = true
    metadata_lock             = true
    host_firewall_ssh_sources = ["10.20.0.0/16"]
    connector_telemetry       = { metrics_port = 9999 }
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "The firewall together with the metadata lock, a metrics port and custom sources must plan."
  }
}

run "host_firewall_ssh_sources_rejects_a_non_cidr" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.1"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_ssh_sources_rejects_an_empty_list" {
  command = plan
  variables {
    host_firewall_ssh_sources = []
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_instances_rejects_an_empty_list" {
  command = plan
  variables {
    host_firewall_instances = []
  }
  expect_failures = [var.host_firewall_instances]
}

run "host_firewall_instances_rejects_c" {
  command = plan
  variables {
    host_firewall_instances = ["c"]
  }
  expect_failures = [var.host_firewall_instances]
}

run "host_firewall_instances_rejects_a_repeat" {
  command = plan
  variables {
    host_firewall_instances = ["a", "a"]
  }
  expect_failures = [var.host_firewall_instances]
}

# Tightened host_firewall_ssh_sources validation: nft rejects leading zeros, and
# a /0 would defeat the narrowing to private space.
run "host_firewall_sources_reject_a_leading_zero_prefix" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.0/08"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_a_leading_zero_octet" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["010.0.0.0/8"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_slash_zero" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["0.0.0.0/0"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_a_prefix_over_32" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.0/33"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_an_octet_over_255" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.256/32"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_accept_host_bits_overlaps_and_the_extremes" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.1/8", "10.1.0.0/16", "192.0.2.7/32", "128.0.0.0/1"]
  }
}

# Metrics ports on the connector security group (issue #99, AWS half). With the
# new inputs at their defaults nothing changes; with a source security group AND
# a metrics source switched on, the connector group admits those ports from that
# one group and from nothing else. The ids below are fake and built for the test.
# Nothing here was applied or tested against a real account.
run "metrics_rules_defaults_change_nothing" {
  command = plan
  assert {
    condition     = var.metrics_source_security_group_id == "" && var.node_exporter.enabled == false && jsonencode(var.node_exporter_instances) == jsonencode(["a", "b"])
    error_message = "metrics_source_security_group_id, node_exporter and node_exporter_instances must default to off, off and both."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22-22/sg-00000000000000002"])
    error_message = "With the defaults the only inbound rule is the existing tcp 22 from the group itself."
  }
}

run "metrics_ports_are_admitted_from_the_source_group_only" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
    node_exporter                    = { enabled = true, port = 9100 }
    connector_telemetry              = { metrics_port = 9999 }
  }
  assert {
    condition = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(sort([
      "tcp/22-22/sg-00000000000000002",
      "tcp/9100-9100/sg-0abc1230abc123450",
      "tcp/9999-9999/sg-0abc1230abc123450",
    ]))
    error_message = "The inbound rules must be exactly tcp 22 from the group itself and the two metrics ports from the source group."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.source_members) == jsonencode(sort(["sg-00000000000000002", "sg-0abc1230abc123450"]))
    error_message = "Inbound sources must be the connector group and the source group, nothing else."
  }
  assert {
    condition     = alltrue([for d in module.connector_firewall.inbound_rules : can(regex("^tcp/[0-9]+-[0-9]+/sg-[0-9a-f]+$", d))])
    error_message = "Every inbound rule must name a source security group, never an address."
  }
}

run "node_exporter_alone_opens_only_its_port" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
    node_exporter                    = { enabled = true, port = 9200 }
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(sort(["tcp/22-22/sg-00000000000000002", "tcp/9200-9200/sg-0abc1230abc123450"]))
    error_message = "Only the node exporter port may be added."
  }
}

run "connector_metrics_port_alone_opens_only_that_port" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
    connector_telemetry              = { metrics_port = 9999 }
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(sort(["tcp/22-22/sg-00000000000000002", "tcp/9999-9999/sg-0abc1230abc123450"]))
    error_message = "Only the connector metrics port may be added."
  }
}

run "previous_metrics_port_stays_open_during_a_rollout" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
    connector_telemetry              = { metrics_port = 9999 }
    connector_telemetry_previous     = { metrics_port = 8888 }
    connector_telemetry_instances    = ["a"]
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(sort(["tcp/22-22/sg-00000000000000002", "tcp/8888-8888/sg-0abc1230abc123450", "tcp/9999-9999/sg-0abc1230abc123450"]))
    error_message = "While connector b still runs the previous port, both ports must stay admitted."
  }
}

run "the_same_port_in_both_places_makes_one_rule" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
    connector_telemetry              = { metrics_port = 9999 }
    connector_telemetry_previous     = { metrics_port = 9999 }
  }
  assert {
    condition     = length(module.connector_firewall.inbound_rules) == 2
    error_message = "A repeated port must not produce a duplicate rule."
  }
}

run "no_source_group_means_no_metrics_rule_even_when_metrics_are_on" {
  command = plan
  variables {
    node_exporter       = { enabled = true }
    connector_telemetry = { metrics_port = 9999 }
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22-22/sg-00000000000000002"])
    error_message = "Without metrics_source_security_group_id no metrics port may be opened (there is no public or address-sourced fallback)."
  }
}

run "a_source_group_alone_opens_nothing" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg-0abc1230abc123450"
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22-22/sg-00000000000000002"])
    error_message = "A source group with no metrics source on must open nothing."
  }
}

run "metrics_source_security_group_rejects_an_address" {
  command = plan
  variables {
    metrics_source_security_group_id = "192.0.2.10"
  }
  expect_failures = [var.metrics_source_security_group_id]
}

run "metrics_source_security_group_rejects_a_cidr" {
  command = plan
  variables {
    metrics_source_security_group_id = "0.0.0.0/0"
  }
  expect_failures = [var.metrics_source_security_group_id]
}

run "metrics_source_security_group_rejects_a_space" {
  command = plan
  variables {
    metrics_source_security_group_id = "sg 0abc1230abc123450"
  }
  expect_failures = [var.metrics_source_security_group_id]
}

run "node_exporter_is_wired_to_both_connectors_gated_on_its_instances" {
  command = plan
  assert {
    condition     = length(regexall("node_exporter\\s*=\\s*\\{[^}]*enabled\\s*=\\s*var\\.node_exporter\\.enabled && contains\\(var\\.node_exporter_instances", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive node_exporter gated on node_exporter_instances."
  }
  assert {
    condition     = length(regexall("contains\\(var\\.node_exporter_instances, \"a\"\\)", file("${path.module}/main.tf"))) == 1 && length(regexall("contains\\(var\\.node_exporter_instances, \"b\"\\)", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must be gated on \"a\" and connector b on \"b\" in node_exporter_instances."
  }
}

run "node_exporter_on_plans_and_rolls_out_to_one_connector" {
  command = plan
  variables {
    node_exporter           = { enabled = true }
    node_exporter_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.size != "" && module.connector_b.size != ""
    error_message = "Rolling the node exporter out to one connector must plan."
  }
}

run "node_exporter_instances_rejects_an_empty_list" {
  command = plan
  variables {
    node_exporter_instances = []
  }
  expect_failures = [var.node_exporter_instances]
}

run "node_exporter_instances_rejects_c" {
  command = plan
  variables {
    node_exporter_instances = ["c"]
  }
  expect_failures = [var.node_exporter_instances]
}

run "node_exporter_instances_rejects_a_repeat" {
  command = plan
  variables {
    node_exporter_instances = ["a", "a"]
  }
  expect_failures = [var.node_exporter_instances]
}

run "node_exporter_port_rejects_a_privileged_port" {
  command = plan
  variables {
    node_exporter = { enabled = true, port = 22 }
  }
  expect_failures = [var.node_exporter]
}

run "no_metrics_port_number_is_hard_coded_in_the_stack" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999 }
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "9999") && !strcontains(file("${path.module}/main.tf"), "9100")
    error_message = "No metrics port number may be hard-coded in this stack."
  }
}
