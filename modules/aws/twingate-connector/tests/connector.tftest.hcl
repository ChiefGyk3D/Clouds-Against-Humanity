mock_provider "aws" {
  mock_data "aws_ssm_parameter" {
    defaults = {
      insecure_value = "ami-00000000000000000"
    }
  }
}
mock_provider "twingate" {}

variables {
  layer                = "access"
  region               = "us-east-1"
  subnet_id            = "subnet-00000000000000000"
  security_group_id    = "sg-00000000000000000"
  instance_type        = "t4g.micro"
  remote_network_id    = "remote-network-test"
  instance             = "a"
  twingate_network     = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  reboot_time          = "03:00"
}

run "instance_is_named_and_placed_by_the_caller" {
  command = plan
  assert {
    condition     = aws_instance.connector.tags["Name"] == "access-us-east-1-connector-a"
    error_message = "Name must be <layer>-<region>-connector-<instance>."
  }
  assert {
    condition     = aws_instance.connector.subnet_id == "subnet-00000000000000000" && jsonencode(aws_instance.connector.vpc_security_group_ids) == jsonencode(["sg-00000000000000000"])
    error_message = "The instance must launch into the given subnet wearing the given security groups."
  }
}

run "connector_and_instance_names_carry_the_instance_letter" {
  command = plan
  variables {
    instance = "b"
  }
  assert {
    condition     = module.bootstrap.name == "access-us-east-1-connector-b" && aws_instance.connector.tags["Name"] == "access-us-east-1-connector-b"
    error_message = "Both the Twingate connector and the instance must be named with the instance letter."
  }
}

run "image_is_canonical_ubuntu_2404_for_the_chosen_architecture" {
  command = plan
  assert {
    condition     = data.aws_ssm_parameter.ubuntu.name == "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
    error_message = "The AMI must come from Canonical's public Ubuntu 24.04 arm64 parameter."
  }
  assert {
    condition     = aws_instance.connector.ami == "ami-00000000000000000"
    error_message = "The instance must use the looked-up AMI."
  }
}

run "x86_fallback_changes_only_the_image_path" {
  command = plan
  variables {
    architecture  = "amd64"
    instance_type = "t3.micro"
  }
  assert {
    condition     = strcontains(data.aws_ssm_parameter.ubuntu.name, "/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id") && aws_instance.connector.instance_type == "t3.micro"
    error_message = "amd64 must select the amd64 image."
  }
}

run "imds_v2_is_required_with_a_single_hop" {
  command = plan
  assert {
    condition     = aws_instance.connector.metadata_options[0].http_tokens == "required" && aws_instance.connector.metadata_options[0].http_endpoint == "enabled"
    error_message = "The metadata service must require IMDSv2 session tokens."
  }
  assert {
    condition     = aws_instance.connector.metadata_options[0].http_put_response_hop_limit == 1
    error_message = "The metadata token hop limit must be 1."
  }
}

run "public_address_is_requested_and_nothing_else_is_extra" {
  command = plan
  assert {
    condition     = aws_instance.connector.associate_public_ip_address == true
    error_message = "The connector needs a public address to reach Twingate without a NAT gateway."
  }
  assert {
    condition     = aws_instance.connector.ipv6_address_count == 0 && aws_instance.connector.monitoring == false
    error_message = "IPv6 and detailed monitoring must stay off."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*(iam_instance_profile|key_name)\\s*=", file("${path.module}/main.tf")))
    error_message = "The connector has no instance profile and no AWS key pair."
  }
  assert {
    condition     = !can(regex("(?m)^resource\\s+\"aws_(eip|nat_gateway|ebs_volume|security_group|key_pair)", file("${path.module}/main.tf")))
    error_message = "This module creates only the instance; groups, addresses, gateways and extra disks are not its business."
  }
}

run "root_volume_is_explicit_gp3_sized_by_the_variable" {
  command = plan
  assert {
    condition     = aws_instance.connector.root_block_device[0].volume_type == "gp3" && aws_instance.connector.root_block_device[0].volume_size == 8
    error_message = "Default root disk is an explicit 8 GiB gp3."
  }
  assert {
    condition     = aws_instance.connector.root_block_device[0].iops == 3000 && aws_instance.connector.root_block_device[0].throughput == 125 && aws_instance.connector.root_block_device[0].encrypted == true
    error_message = "gp3 at its baseline performance, encrypted."
  }
  assert {
    condition     = length(aws_instance.connector.ebs_block_device) == 0
    error_message = "No extra block devices."
  }
}

run "root_volume_size_follows_the_variable" {
  command = plan
  variables {
    root_volume_size = 20
  }
  assert {
    condition     = aws_instance.connector.root_block_device[0].volume_size == 20
    error_message = "volume_size must come from root_volume_size."
  }
}

run "instance_type_comes_from_the_variable" {
  command = plan
  variables {
    instance_type = "t4g.small"
  }
  assert {
    condition     = aws_instance.connector.instance_type == "t4g.small"
    error_message = "instance_type must come from the variable."
  }
}

run "boot_data_is_the_shared_bootstraps_output_with_the_hardening_in_it" {
  command = plan
  assert {
    condition     = aws_instance.connector.user_data == module.bootstrap.user_data
    error_message = "The instance's boot data must be exactly the shared bootstrap output."
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "99-cah-hardening") && strcontains(aws_instance.connector.user_data, "PasswordAuthentication no")
    error_message = "The shared hardening must reach the instance."
  }
  assert {
    condition     = aws_instance.connector.user_data_replace_on_change == true
    error_message = "A changed cloud-init must replace the instance, since it only runs on first boot."
  }
}

run "this_module_holds_no_private_copy_of_the_bootstrap" {
  command = plan
  assert {
    condition     = !fileexists("${path.module}/cloud-init.yaml.tftpl") && !strcontains(file("${path.module}/main.tf"), "templatefile") && !can(regex("(?m)^resource\\s+\"twingate_", file("${path.module}/main.tf"))) && strcontains(file("${path.module}/main.tf"), "source = \"../../twingate-bootstrap\"")
    error_message = "A provider module must call the bootstrap module, not carry its own cloud-init or Twingate resources."
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

  # Test setup sanity: the fake values really reach the instance's user_data.
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "FAKE-ACCESS-TOKEN-1") && strcontains(aws_instance.connector.user_data, "FAKE-REFRESH-TOKEN-1")
    error_message = "Test setup: fake tokens must flow into user_data."
  }

  # The test can only name outputs it knows, so pin the output set.
  assert {
    condition     = length(regexall("output \"", file("${path.module}/outputs.tf"))) == 4
    error_message = "outputs.tf must declare exactly 4 outputs. Add one only after proving it carries no connector secret and extending this test."
  }

  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["instance_id", "instance_name", "private_ip", "size"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it here only after proving it carries no connector secret."
  }

  # Each output must be exactly its intended non-secret source. Searching for
  # the fake tokens alone would miss an output that re-encodes the boot data.
  assert {
    condition = (
      output.instance_id == aws_instance.connector.id &&
      output.instance_name == aws_instance.connector.tags["Name"] &&
      output.private_ip == aws_instance.connector.private_ip &&
      output.size == aws_instance.connector.instance_type
    )
    error_message = "Every output must be exactly its instance attribute, never derived from the boot data."
  }

  assert {
    condition = !anytrue([
      for v in [output.instance_id, output.instance_name, output.private_ip, output.size] :
      strcontains(tostring(v), "FAKE-ACCESS-TOKEN-1") || strcontains(tostring(v), "FAKE-REFRESH-TOKEN-1")
    ])
    error_message = "A module output carries a connector access or refresh token."
  }
}

run "an_empty_or_malformed_security_group_is_rejected" {
  command = plan
  variables {
    security_group_id = ""
  }
  expect_failures = [var.security_group_id]
}

run "the_module_takes_one_group_never_a_list" {
  command = plan
  # Rules are additive: a second group could carry an open inbound rule. The
  # module must attach exactly the one group it was given and have no list input.
  assert {
    condition     = length(aws_instance.connector.vpc_security_group_ids) == 1
    error_message = "Exactly one security group may be attached."
  }
  assert {
    condition     = !can(regex("variable\\s+\"security_group_ids\"", file("${path.module}/variables.tf"))) && !can(regex("var\\.security_group_ids", file("${path.module}/main.tf"))) && can(regex("vpc_security_group_ids\\s*=\\s*\\[var\\.security_group_id\\]", file("${path.module}/main.tf")))
    error_message = "The input is a single security_group_id and main.tf attaches only [var.security_group_id]."
  }
}

run "t_family_pins_standard_cpu_credits" {
  command = plan
  assert {
    condition     = length(aws_instance.connector.credit_specification) == 1 && aws_instance.connector.credit_specification[0].cpu_credits == "standard"
    error_message = "A T-family instance must set cpu_credits to standard; the default is unlimited and bills surplus credits outside the fixed figure."
  }
}

run "t3_also_pins_standard_credits" {
  command = plan
  variables {
    architecture  = "amd64"
    instance_type = "t3.micro"
  }
  assert {
    condition     = aws_instance.connector.credit_specification[0].cpu_credits == "standard"
    error_message = "t3 must set standard credits too."
  }
}

run "a_non_burstable_type_has_no_credit_block" {
  command = plan
  variables {
    architecture  = "amd64"
    instance_type = "m6i.large"
  }
  assert {
    condition     = length(aws_instance.connector.credit_specification) == 0
    error_message = "EC2 rejects credit_specification outside the T families."
  }
}

run "arm_image_on_an_x86_type_is_rejected" {
  command = plan
  variables {
    architecture  = "arm64"
    instance_type = "t3.micro"
  }
  expect_failures = [data.aws_ssm_parameter.ubuntu]
}

run "x86_image_on_a_graviton_type_is_rejected" {
  command = plan
  variables {
    architecture  = "amd64"
    instance_type = "t4g.micro"
  }
  expect_failures = [data.aws_ssm_parameter.ubuntu]
}

run "a_malformed_instance_type_is_rejected" {
  command = plan
  variables {
    instance_type = "micro"
  }
  expect_failures = [var.instance_type]
}

run "an_unknown_architecture_is_rejected" {
  command = plan
  variables {
    architecture = "x86_64"
  }
  expect_failures = [var.architecture]
}

run "a_root_volume_below_the_image_size_is_rejected" {
  command = plan
  variables {
    root_volume_size = 4
  }
  expect_failures = [var.root_volume_size]
}

run "an_oversized_root_volume_is_rejected" {
  command = plan
  variables {
    root_volume_size = 500
  }
  expect_failures = [var.root_volume_size]
}

run "an_architecture_change_replaces_the_instance_despite_ignored_ami" {
  command = plan
  assert {
    condition     = terraform_data.architecture.input == "arm64"
    error_message = "The trigger must carry the architecture input."
  }
  assert {
    condition     = can(regex("ignore_changes\\s*=\\s*\\[ami\\]", file("${path.module}/main.tf"))) && can(regex("replace_triggered_by\\s*=\\s*\\[terraform_data\\.architecture\\]", file("${path.module}/main.tf")))
    error_message = "Routine image updates stay ignored, but an architecture change must trigger replacement."
  }
}

run "the_trigger_follows_the_architecture_input" {
  command = plan
  variables {
    architecture  = "amd64"
    instance_type = "t3.micro"
  }
  assert {
    condition     = terraform_data.architecture.input == "amd64"
    error_message = "The trigger must follow var.architecture."
  }
}

run "timezone_reaches_the_machine" {
  command = plan
  variables {
    timezone = "Europe/Paris"
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "\ntimezone: Europe/Paris\n")
    error_message = "The timezone input must reach the machine's cloud-init."
  }
}

run "timezone_default_is_eastern" {
  command = plan
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "\ntimezone: America/New_York\n")
    error_message = "Without a timezone the machine must stay on America/New_York."
  }
}

run "telemetry_default_adds_nothing_to_the_instance_user_data" {
  command = plan
  assert {
    condition     = !strcontains(aws_instance.connector.user_data, "TWINGATE_LOG_") && !strcontains(aws_instance.connector.user_data, "TWINGATE_METRICS_") && !strcontains(aws_instance.connector.user_data, "TWINGATE_LABEL_")
    error_message = "With connector_telemetry unset no telemetry line may reach the instance."
  }
}

run "telemetry_reaches_the_instance_user_data" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999, connection_logs = true }
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "      TWINGATE_LOG_ANALYTICS=v3\n      TWINGATE_METRICS_PORT=9999\n")
    error_message = "connector_telemetry must flow through the module into the instance's user_data."
  }
}

run "metadata_lock_default_adds_nothing_to_the_instance_user_data" {
  command = plan
  assert {
    condition     = !strcontains(aws_instance.connector.user_data, "cah-metadata-lock") && !strcontains(aws_instance.connector.user_data, "nftables")
    error_message = "With metadata_lock unset nothing about it may reach the instance."
  }
}

run "metadata_lock_reaches_the_instance_user_data" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "/usr/local/sbin/cah-metadata-lock") && strcontains(aws_instance.connector.user_data, "--no-block")
    error_message = "metadata_lock must flow through the module into the instance's user_data."
  }
}

run "host_firewall_default_adds_nothing_to_the_instance_user_data" {
  command = plan
  assert {
    condition     = !strcontains(aws_instance.connector.user_data, "cah-host-firewall") && !strcontains(aws_instance.connector.user_data, "nftables")
    error_message = "With host_firewall unset nothing about it may reach the instance."
  }
}

run "host_firewall_reaches_the_instance_user_data" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "/usr/local/sbin/cah-host-firewall") && strcontains(aws_instance.connector.user_data, "--no-block") && strcontains(aws_instance.connector.user_data, "policy drop")
    error_message = "host_firewall must flow through the module into the instance's user_data."
  }
}

run "host_firewall_sources_reach_the_instance_user_data" {
  command = plan
  variables {
    host_firewall             = true
    host_firewall_ssh_sources = ["10.20.0.0/16"]
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "ssh_sources=\"10.20.0.0/16\"")
    error_message = "host_firewall_ssh_sources must flow through the module into the instance's user_data."
  }
}

# Golden hashes: with the node exporter at its default the boot data is
# byte-identical to what main rendered before the node_exporter input existed,
# so merging the pass-through plans no change to a live connector. The tokens
# are fixed so the hash is stable.
run "node_exporter_default_user_data_is_the_main_user_data_a" {
  command = plan
  override_resource {
    target = module.bootstrap.twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  assert {
    condition     = sha256(aws_instance.connector.user_data) == "59cc1dfc0a31f5fdec5c03be38420340325ec5ad6570ebe062cf75b1ff78af06"
    error_message = "With node_exporter unset the user_data must be exactly what main rendered (connector a)."
  }
}

run "node_exporter_explicitly_off_is_the_main_user_data_a" {
  command = plan
  override_resource {
    target = module.bootstrap.twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    node_exporter = { enabled = false, port = 9101 }
  }
  assert {
    condition     = sha256(aws_instance.connector.user_data) == "59cc1dfc0a31f5fdec5c03be38420340325ec5ad6570ebe062cf75b1ff78af06"
    error_message = "node_exporter disabled (whatever its port) must render exactly what main rendered."
  }
}

run "node_exporter_enabled_reaches_the_instance_user_data" {
  command = plan
  variables {
    node_exporter = { enabled = true }
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "prometheus-node-exporter") && strcontains(aws_instance.connector.user_data, "cah-node-exporter-run")
    error_message = "node_exporter.enabled must flow through the module into the instance's user_data."
  }
  assert {
    condition     = aws_instance.connector.user_data == module.bootstrap.user_data && aws_instance.connector.user_data_replace_on_change == true
    error_message = "Enabling the exporter changes user_data, which replaces the instance (user_data_replace_on_change)."
  }
}

run "node_exporter_port_reaches_the_instance_user_data" {
  command = plan
  variables {
    node_exporter = { enabled = true, port = 9123 }
    host_firewall = true
  }
  assert {
    condition     = strcontains(aws_instance.connector.user_data, "9123")
    error_message = "node_exporter.port must flow through the module into the instance's user_data."
  }
}

run "node_exporter_default_user_data_is_the_main_user_data_b_with_host_firewall" {
  command = plan
  override_resource {
    target = module.bootstrap.twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    instance      = "b"
    reboot_time   = "05:00"
    host_firewall = true
  }
  assert {
    condition     = sha256(aws_instance.connector.user_data) == "bdd9be07d3ea61f47d8f5ed4da066840142341e3d98eabd9436a00950a4f7332"
    error_message = "With node_exporter unset the user_data must be exactly what main rendered (connector b, host firewall on)."
  }
}
