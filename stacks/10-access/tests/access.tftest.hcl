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
  vpc_id               = "vpc-test"
  project_id           = "project-test" # identifier-check: ignore (mocked DigitalOcean project, not a GCP id)
  baseline_tag         = "cah-baseline-tor1"
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
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a" && module.connector_b.droplet_name == "access-tor1-connector-b"
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
      size         = "s-1vcpu-1gb"
    }
  }
  override_module {
    target = module.connector_b
    outputs = {
      droplet_name = "b"
      droplet_urn  = "do:droplet:b"
      private_ip   = "10.0.0.2"
      size         = "s-1vcpu-1gb"
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
    condition     = twingate_remote_network.this.name == "access-tor1" && twingate_remote_network.this.location == "OTHER"
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
    condition     = digitalocean_tag.connector.name == "cah-connector-tor1"
    error_message = "Connector tag must be cah-connector-<region>."
  }
  assert {
    condition     = module.connector_firewall.inbound_rule_count == 1
    error_message = "The connector firewall must have exactly one inbound rule (tcp 22 from the connector tag)."
  }
  assert {
    condition     = jsonencode(module.connector_firewall.inbound_rules) == jsonencode(["tcp/22/cah-connector-tor1"])
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
    condition     = jsonencode(module.connector_firewall.outbound_tag_rules) == jsonencode(["tcp/22/cah-connector-tor1"])
    error_message = "The only tag-scoped outbound rule must be tcp 22 destined to the connector tag, so a connector can open SSH to its peer and nothing else."
  }
}

run "connector_a_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_a_ssh.name == "cah-tor1-connector-a-ssh"
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
    condition     = twingate_group.admins.name == "cah-tor1-admins"
    error_message = "Access is granted to one named group."
  }
}

run "connector_b_ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_b_ssh.name == "cah-tor1-connector-b-ssh"
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
    condition     = twingate_group.admins.name == "cah-tor1-admins"
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
    condition     = length(regexall("reboot_time\\s*=\\s*var.reboot_times\\[\"a\"\\]", file("${path.module}/main.tf"))) == 1 && length(regexall("reboot_time\\s*=\\s*var.reboot_times\\[\"b\"\\]", file("${path.module}/main.tf"))) == 1
    error_message = "Connector a must take reboot_times[\"a\"] and connector b reboot_times[\"b\"]."
  }
  assert {
    condition     = length(regexall("reboot_time\\s*=", file("${path.module}/main.tf"))) == 2
    error_message = "Each connector module block must set its own reboot_time."
  }
  assert {
    condition     = length(regexall("admin_ssh_public_key\\s*=\\s*var.admin_ssh_public_key", file("${path.module}/main.tf"))) == 2
    error_message = "Both connectors must receive the admin public key."
  }
  assert {
    condition     = var.reboot_times["a"] == "04:00" && var.reboot_times["b"] == "05:00" && var.reboot_times["a"] != var.reboot_times["b"]
    error_message = "The defaults must be the times the live connectors use today: 04:00 and 05:00 Eastern."
  }
}

# --- golden names ------------------------------------------------------------
# The names the live stack has today, with the default settings.

run "golden_names_with_defaults" {
  command = plan
  assert {
    condition     = twingate_remote_network.this.name == "access-tor1"
    error_message = "The Twingate remote network name changed."
  }
  assert {
    condition     = digitalocean_tag.connector.name == "cah-connector-tor1"
    error_message = "The connector tag name changed."
  }
  assert {
    condition     = twingate_group.admins.name == "cah-tor1-admins"
    error_message = "The admin group name changed."
  }
  assert {
    condition     = twingate_resource.connector_a_ssh.name == "cah-tor1-connector-a-ssh" && twingate_resource.connector_b_ssh.name == "cah-tor1-connector-b-ssh"
    error_message = "A Twingate SSH resource name changed."
  }
  assert {
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a" && module.connector_b.droplet_name == "access-tor1-connector-b"
    error_message = "A droplet name changed."
  }
  assert {
    condition     = module.connector_firewall.name == "access-tor1-connector"
    error_message = "The connector firewall name changed."
  }
  assert {
    condition     = output.connector_tag == "cah-connector-tor1"
    error_message = "The connector_tag output changed."
  }
}

run "an_empty_resource_key_means_the_region" {
  command = plan
  variables {
    resource_key = ""
  }
  assert {
    condition = alltrue([
      twingate_remote_network.this.name == "access-tor1",
      digitalocean_tag.connector.name == "cah-connector-tor1",
      twingate_group.admins.name == "cah-tor1-admins",
      twingate_resource.connector_a_ssh.name == "cah-tor1-connector-a-ssh",
      twingate_resource.connector_b_ssh.name == "cah-tor1-connector-b-ssh",
      module.connector_a.droplet_name == "access-tor1-connector-a",
      module.connector_b.droplet_name == "access-tor1-connector-b",
      module.connector_firewall.name == "access-tor1-connector",
    ])
    error_message = "An empty resource_key must leave every name as it is today."
  }
}

run "resource_key_names_every_object_and_the_region_stays_the_region" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition = alltrue([
      twingate_remote_network.this.name == "access-tor1-b",
      digitalocean_tag.connector.name == "cah-connector-tor1-b",
      twingate_group.admins.name == "cah-tor1-b-admins",
      twingate_resource.connector_a_ssh.name == "cah-tor1-b-connector-a-ssh",
      twingate_resource.connector_b_ssh.name == "cah-tor1-b-connector-b-ssh",
      module.connector_a.droplet_name == "access-tor1-b-connector-a",
      module.connector_b.droplet_name == "access-tor1-b-connector-b",
      module.connector_firewall.name == "access-tor1-b-connector",
    ])
    error_message = "A resource_key must replace the region in every name."
  }
  assert {
    condition     = length(regexall("region\\s*=\\s*var.region", file("${path.module}/main.tf"))) == 3
    error_message = "The two connector modules and the firewall module must still receive the real region."
  }
  assert {
    condition     = length(regexall("(?m)resource_key\\s*=\\s*var.resource_key$", file("${path.module}/main.tf"))) == 3
    error_message = "The two connector modules and the firewall module must receive the resource_key."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "-$${var.region}")
    error_message = "No name may be built from var.region directly; use local.resource_key."
  }
}

run "site_name_changes_no_name" {
  command = plan
  variables {
    site_name = "site-tor1"
  }
  assert {
    condition = alltrue([
      twingate_remote_network.this.name == "access-tor1",
      digitalocean_tag.connector.name == "cah-connector-tor1",
      twingate_group.admins.name == "cah-tor1-admins",
      module.connector_a.droplet_name == "access-tor1-connector-a",
      module.connector_firewall.name == "access-tor1-connector",
    ])
    error_message = "site_name is a telemetry label and must change no name."
  }
}

run "no_source_file_uses_site_name" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "site_name") && !strcontains(file("${path.module}/outputs.tf"), "site_name")
    error_message = "site_name must not appear in main.tf or outputs.tf: it is for telemetry labels only."
  }
}

run "resource_key_rejects_uppercase" {
  command = plan
  variables {
    resource_key = "Tor1"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_a_leading_digit" {
  command = plan
  variables {
    resource_key = "1tor"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_one_character" {
  command = plan
  variables {
    resource_key = "a"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_25_characters" {
  command = plan
  variables {
    resource_key = "abcdefghijklmnopqrstuvwxy"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_a_space" {
  command = plan
  variables {
    resource_key = "tor 1"
  }
  expect_failures = [var.resource_key]
}

run "site_name_rejects_uppercase" {
  command = plan
  variables {
    site_name = "Site-Tor1"
  }
  expect_failures = [var.site_name]
}

run "site_name_rejects_a_leading_hyphen" {
  command = plan
  variables {
    site_name = "-site"
  }
  expect_failures = [var.site_name]
}

# --- region ------------------------------------------------------------------

run "region_rejects_uppercase" {
  command = plan
  variables {
    region = "Tor1"
  }
  expect_failures = [var.region]
}

run "region_rejects_a_city_name" {
  command = plan
  variables {
    region = "toronto"
  }
  expect_failures = [var.region]
}

run "region_rejects_empty" {
  command = plan
  variables {
    region = ""
  }
  expect_failures = [var.region]
}

# --- reboot_times ------------------------------------------------------------

run "reboot_times_default_to_the_live_values" {
  command = plan
  assert {
    condition     = jsonencode(var.reboot_times) == jsonencode({ a = "04:00", b = "05:00" })
    error_message = "The default reboot_times must be a = 04:00 and b = 05:00."
  }
}

run "reboot_times_accepts_other_distinct_times" {
  command = plan
  variables {
    reboot_times = { a = "03:15", b = "23:59" }
  }
  assert {
    condition     = var.reboot_times["b"] == "23:59"
    error_message = "Two distinct valid times must be accepted."
  }
}

run "reboot_times_exactly_60_minutes_apart_pass" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "05:00" }
  }
  assert {
    condition     = var.reboot_times["b"] == "05:00"
    error_message = "Exactly 60 minutes apart must be accepted."
  }
}

run "reboot_times_60_apart_across_midnight_pass" {
  command = plan
  variables {
    reboot_times = { a = "23:30", b = "00:30" }
  }
  assert {
    condition     = var.reboot_times["a"] == "23:30"
    error_message = "60 minutes apart across midnight must be accepted."
  }
}

run "reboot_times_60_apart_across_midnight_pass_reversed" {
  command = plan
  variables {
    reboot_times = { a = "00:30", b = "23:30" }
  }
  assert {
    condition     = var.reboot_times["b"] == "23:30"
    error_message = "60 minutes apart across midnight must be accepted either way round."
  }
}

run "reboot_times_accepts_the_times_swapped" {
  command = plan
  variables {
    reboot_times = { a = "05:00", b = "04:00" }
  }
  assert {
    condition     = var.reboot_times["a"] == "05:00"
    error_message = "Swapped times are still distinct."
  }
}

run "reboot_times_rejects_identical_times" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "04:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_a_bad_hour" {
  command = plan
  variables {
    reboot_times = { a = "24:00", b = "05:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_a_bad_minute" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "05:60" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_no_zero_pad" {
  command = plan
  variables {
    reboot_times = { a = "4:00", b = "05:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_seconds" {
  command = plan
  variables {
    reboot_times = { a = "04:00:00", b = "05:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_a_missing_key" {
  command = plan
  variables {
    reboot_times = { a = "04:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_an_extra_key" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "05:00", c = "06:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_wrong_keys" {
  command = plan
  variables {
    reboot_times = { a = "04:00", c = "05:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_rejects_an_empty_map" {
  command = plan
  variables {
    reboot_times = {}
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_reject_one_minute_apart" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "04:01" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_reject_59_minutes_apart" {
  command = plan
  variables {
    reboot_times = { a = "04:00", b = "04:59" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_reject_across_midnight_one_minute_apart" {
  command = plan
  variables {
    reboot_times = { a = "23:59", b = "00:00" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_reject_across_midnight_59_apart" {
  command = plan
  variables {
    reboot_times = { a = "23:31", b = "00:30" }
  }
  expect_failures = [var.reboot_times]
}

run "reboot_times_reject_across_midnight_59_apart_reversed" {
  command = plan
  variables {
    reboot_times = { a = "00:30", b = "23:31" }
  }
  expect_failures = [var.reboot_times]
}

# --- admin_ssh_public_key ----------------------------------------------------

run "admin_key_accepts_a_comment_at_the_stack" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest laptop-2026"
  }
  assert {
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a"
    error_message = "A key with a trailing comment must plan at the stack."
  }
}

run "admin_key_rejects_a_two_word_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA two words"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_newline" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA\n  - evil"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_trailing_newline" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA\n"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_unsafe_comment_characters" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA user;id"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_an_unknown_algorithm" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-dss AAAA"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_an_empty_key" {
  command = plan
  variables {
    admin_ssh_public_key = ""
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_an_option_prefix" {
  command = plan
  variables {
    admin_ssh_public_key = "command=\"id\" ssh-ed25519 AAAA"
  }
  expect_failures = [var.admin_ssh_public_key]
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

run "connector_telemetry_defaults_to_off_and_is_wired_to_both_connectors" {
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

run "connector_telemetry_enabled_plans_without_renaming_anything" {
  command = plan
  variables {
    connector_telemetry = { log_level = 5, connection_logs = true, metrics_port = 9999, labels = { SITE = "tor1" } }
  }
  assert {
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a" && module.connector_b.droplet_name == "access-tor1-connector-b"
    error_message = "Enabling telemetry must not change names."
  }
}

run "enabling_telemetry_opens_no_firewall_port" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999 }
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "9999") && length(regexall("port_range\\s*=", file("${path.module}/main.tf"))) == 4
    error_message = "This stack must not add a firewall rule for the metrics port; that is a separate change."
  }
}

run "telemetry_instances_a_only_plans" {
  command = plan
  variables {
    connector_telemetry           = { metrics_port = 9999 }
    connector_telemetry_instances = ["a"]
  }
  assert {
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a"
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
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a"
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
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a"
    error_message = "Explicit nulls must plan as unset."
  }
}

run "telemetry_null_object_plans_as_off" {
  command = plan
  variables {
    connector_telemetry = null
  }
  assert {
    condition     = module.connector_a.droplet_name == "access-tor1-connector-a"
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
