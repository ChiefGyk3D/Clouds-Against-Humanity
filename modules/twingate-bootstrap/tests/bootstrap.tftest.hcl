mock_provider "twingate" {}

variables {
  layer             = "access"
  region            = "tor1"
  instance          = "a"
  remote_network_id = "remote-network-test"
  twingate_network  = "acme"

  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  reboot_time          = "03:00"
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

run "cloud_init_installs_connector_for_the_network" {
  command = plan
  assert {
    condition     = strcontains(output.user_data, "TWINGATE_URL=https://acme.twingate.com")
    error_message = "cloud-init must point the connector at the Twingate network."
  }
}

run "network_slug_accepts_bare_subdomain" {
  command = plan
  variables {
    twingate_network = "acme-2"
  }
  assert {
    condition     = strcontains(output.user_data, "TWINGATE_URL=https://acme-2.twingate.com")
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
    condition     = strcontains(output.user_data, "pipefail") && strcontains(output.user_data, "--proto '=https' --tlsv1.2")
    error_message = "The install pipeline must use pipefail and hardened curl."
  }
}

run "cloud_init_is_valid_yaml_with_a_key_only_admin_user" {
  command = plan
  assert {
    condition     = yamldecode(output.user_data).disable_root == true && yamldecode(output.user_data).ssh_pwauth == false
    error_message = "Root login and SSH passwords must be disabled in cloud-init."
  }
  assert {
    condition     = length(yamldecode(output.user_data).users) == 1 && yamldecode(output.user_data).users[0].name == "cah-admin"
    error_message = "Exactly one user, cah-admin, must be declared (no default ubuntu user)."
  }
  assert {
    condition     = yamldecode(output.user_data).users[0].ssh_authorized_keys == ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"]
    error_message = "cah-admin must carry the admin public key."
  }
  assert {
    condition     = yamldecode(output.user_data).users[0].lock_passwd == true && yamldecode(output.user_data).users[0].sudo == "ALL=(ALL) NOPASSWD:ALL"
    error_message = "cah-admin must have a locked password and key-based passwordless sudo."
  }
}

run "sshd_dropin_has_the_hardening_settings" {
  command = plan
  assert {
    condition = alltrue([
      for line in [
        "PermitRootLogin no", "PasswordAuthentication no", "KbdInteractiveAuthentication no",
        "PubkeyAuthentication yes", "X11Forwarding no", "AllowUsers cah-admin",
        "MaxAuthTries 3", "LoginGraceTime 20",
      ] :
      contains(split("\n", one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/ssh/sshd_config.d/99-cah-hardening.conf"])), line)
    ])
    error_message = "The sshd drop-in must contain every hardening line."
  }
  assert {
    condition     = !can(regex("(?i)PermitRootLogin\\s+(yes|prohibit-password|without-password)", output.user_data))
    error_message = "No part of the user_data may allow root login."
  }
}

run "unattended_upgrades_reboot_at_the_instance_time" {
  command = plan
  variables {
    reboot_time = "04:00"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/52cah-unattended-upgrades"]), "Unattended-Upgrade::Automatic-Reboot-Time \"04:00\";")
    error_message = "The reboot time must come from the reboot_time input."
  }
  assert {
    condition = alltrue([
      for line in ["Unattended-Upgrade::Automatic-Reboot \"true\";", "Unattended-Upgrade::Automatic-Reboot-WithUsers \"true\";", "Unattended-Upgrade::Remove-Unused-Dependencies \"true\";"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/52cah-unattended-upgrades"]), line)
    ])
    error_message = "Automatic reboot (with users) and unused-dependency removal must be on."
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "30 4 * * 0 root")
    error_message = "The weekly connector update must run half an hour after the reboot time."
  }
}

run "update_time_carries_across_the_hour_and_midnight" {
  command = plan
  variables {
    reboot_time = "23:45"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "15 0 * * 0 root")
    error_message = "23:45 plus 30 minutes must be 00:15."
  }
}

run "chrony_and_sysctl_are_configured_without_touching_ip_forward" {
  command = plan
  assert {
    condition     = contains(yamldecode(output.user_data).packages, "chrony") && contains(yamldecode(output.user_data).packages, "unattended-upgrades")
    error_message = "chrony and unattended-upgrades must be installed."
  }
  assert {
    condition = alltrue([
      for k in ["net.ipv4.tcp_syncookies = 1", "net.ipv4.conf.all.log_martians = 1", "net.ipv4.conf.all.accept_redirects = 0", "net.ipv4.conf.all.accept_source_route = 0", "net.ipv4.conf.all.rp_filter = 2"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/sysctl.d/99-cah-hardening.conf"]), k)
    ])
    error_message = "The sysctl drop-in must carry the safe hardening settings."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*net\\.ipv[46]\\.(conf\\.[a-z]+\\.)?(ip_)?forwarding\\s*=", output.user_data))
    error_message = "The sysctl drop-in must not change forwarding; the connector may need it."
  }
}

run "tokens_appear_only_in_the_root_only_config" {
  command = apply

  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "FAKE-ACCESS-TOKEN-2"
      refresh_token = "FAKE-REFRESH-TOKEN-2"
    }
  }

  assert {
    condition     = length(regexall("FAKE-ACCESS-TOKEN-2", output.user_data)) == 1 && length(regexall("FAKE-REFRESH-TOKEN-2", output.user_data)) == 1
    error_message = "Each token must appear exactly once, in the connector config."
  }
  assert {
    condition = alltrue([
      for f in yamldecode(output.user_data).write_files :
      f.path == "/etc/twingate/connector.conf" && f.permissions == "0600" && f.owner == "root:root"
      if strcontains(f.content, "FAKE-ACCESS-TOKEN-2") || strcontains(f.content, "FAKE-REFRESH-TOKEN-2")
    ]) && length([for f in yamldecode(output.user_data).write_files : f if strcontains(f.content, "FAKE-ACCESS-TOKEN-2")]) == 1
    error_message = "The tokens may only be written to /etc/twingate/connector.conf, mode 0600, owned by root."
  }
  assert {
    condition     = !anytrue([for c in yamldecode(output.user_data).runcmd : strcontains(jsonencode(c), "FAKE-ACCESS-TOKEN-2") || strcontains(jsonencode(c), "FAKE-REFRESH-TOKEN-2")])
    error_message = "No runcmd step may carry a token."
  }
}

run "reboot_time_rejects_a_bad_hour" {
  command = plan
  variables {
    reboot_time = "24:00"
  }
  expect_failures = [var.reboot_time]
}

run "reboot_time_rejects_a_bad_minute" {
  command = plan
  variables {
    reboot_time = "03:60"
  }
  expect_failures = [var.reboot_time]
}

run "reboot_time_rejects_a_missing_zero_pad" {
  command = plan
  variables {
    reboot_time = "3:00"
  }
  expect_failures = [var.reboot_time]
}

# A normal OpenSSH public key carries a trailing comment. It is accepted, and it
# is dropped before the key reaches cloud-init, so user_data is the same with or
# without it.
run "admin_key_accepts_a_comment_and_renders_without_it" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest user@host.example"
  }
  assert {
    condition     = yamldecode(output.user_data).users[0].ssh_authorized_keys == ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"]
    error_message = "The rendered key must be '<algorithm> <key>' with the comment removed."
  }
  assert {
    condition     = !strcontains(output.user_data, "user@host.example")
    error_message = "The comment must not appear anywhere in user_data."
  }
}

# Golden: the rendered cloud-init for the live connectors, with fixed tokens,
# measured on origin/main before resource_key and the comment-tolerant key
# existed. A change here rebuilds the droplets (user_data is force-new), so it
# must be a deliberate step, never a side effect.
run "user_data_is_byte_identical_to_the_live_connector_a" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time = "04:00"
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "user_data for connector a changed. The golden hash was taken on origin/main; a different value means droplets would be replaced."
  }
}

run "user_data_is_byte_identical_to_the_live_connector_b" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    instance    = "b"
    reboot_time = "05:00"
  }
  assert {
    condition     = sha256(output.user_data) == "de2de6286f955100f199779f2b8a4d0a194b72f28619965c80f858061742790b"
    error_message = "user_data for connector b changed. The golden hash was taken on origin/main; a different value means droplets would be replaced."
  }
}

run "user_data_with_a_comment_matches_the_golden_hash" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time          = "04:00"
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest laptop-2026"
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "A key with a comment must render the same user_data as the key without one."
  }
}

run "admin_key_accepts_rsa_with_padding_and_ecdsa" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAAtest== me"
  }
  assert {
    condition     = yamldecode(output.user_data).users[0].ssh_authorized_keys == ["ssh-rsa AAAAB3NzaC1yc2EAAAAtest=="]
    error_message = "An rsa key with padding must be accepted and rendered without its comment."
  }
}

run "admin_key_accepts_ecdsa" {
  command = plan
  variables {
    admin_ssh_public_key = "ecdsa-sha2-nistp256 AAAAE2VjZHNhtest"
  }
  assert {
    condition     = yamldecode(output.user_data).users[0].ssh_authorized_keys == ["ecdsa-sha2-nistp256 AAAAE2VjZHNhtest"]
    error_message = "An ecdsa key must be accepted."
  }
}

run "admin_key_rejects_a_two_word_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA two words"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_newline_after_the_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA user@host\n  - evil"
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

run "admin_key_rejects_a_tab" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519\tAAAA"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_trailing_space" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA "
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

run "admin_key_rejects_a_quote_in_the_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA us\"er"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_hash_in_the_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA #x"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_dollar_brace_in_the_comment" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA $${x}"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_comment_over_64_characters" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA ${join("", [for i in range(65) : "a"])}"
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

run "admin_key_rejects_an_option_prefix" {
  command = plan
  variables {
    admin_ssh_public_key = "command=\"id\" ssh-ed25519 AAAA"
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

run "admin_key_rejects_a_key_with_no_body" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_non_base64_body" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AA!A"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_a_leading_space" {
  command = plan
  variables {
    admin_ssh_public_key = " ssh-ed25519 AAAA"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "admin_key_rejects_yaml_injection" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA\n  - evil"
  }
  expect_failures = [var.admin_ssh_public_key]
}

# First-boot install resilience. The apt lock race with Ubuntu's own unattended
# upgrades made the one-shot install abort before it wrote the connector config.

run "apt_waits_for_the_dpkg_lock" {
  command = plan
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/99cah-lock-wait"]), "DPkg::Lock::Timeout \"300\";")
    error_message = "apt must wait up to 300 seconds for the dpkg lock."
  }
}

run "installer_does_not_run_the_vendor_script_or_pipe_into_a_shell" {
  command = plan
  assert {
    condition     = !anytrue([for c in yamldecode(output.user_data).runcmd : strcontains(jsonencode(c), "setup.sh")])
    error_message = "Twingate's setup.sh must not be run; piped into bash it can lose the rest of the script to apt."
  }
  assert {
    condition     = !anytrue([for c in yamldecode(output.user_data).runcmd : can(regex("\\|\\s*(ba|da)?sh\\b", jsonencode(c)))])
    error_message = "Nothing may be piped into a shell."
  }
}

run "repository_key_is_pinned_and_service_is_verified" {
  command = plan
  assert {
    condition = alltrue([
      for c in yamldecode(output.user_data).runcmd :
      strcontains(jsonencode(c), "FPR=EC952DEE4701A407A82B0C505C363F09A9174A9E") && strcontains(jsonencode(c), "gpg --show-keys --with-colons") && strcontains(jsonencode(c), "signed-by=$KEYRING") && strcontains(jsonencode(c), "https://packages.twingate.com/apt/")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "The Twingate repository key must be checked against the pinned fingerprint and the repository must be signed-by that key."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(output.user_data).runcmd :
      strcontains(jsonencode(c), "systemctl enable --now twingate-connector") && strcontains(jsonencode(c), "systemctl is-active --quiet twingate-connector") && strcontains(jsonencode(c), "DEBIAN_FRONTEND=noninteractive")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "An attempt only counts as a success when the service is active, and apt must run non-interactively."
  }
}

run "installer_is_retried_a_bounded_number_of_times" {
  command = plan
  assert {
    condition     = length([for c in yamldecode(output.user_data).runcmd : c if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")]) == 1
    error_message = "The connector package must be installed from exactly one runcmd step."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(output.user_data).runcmd :
      strcontains(jsonencode(c), "seq 1 10") && strcontains(jsonencode(c), "sleep 30") && strcontains(jsonencode(c), "exit 1") && strcontains(jsonencode(c), "pipefail")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "The install step must retry 10 times, 30 seconds apart, under pipefail, and exit 1 when every attempt fails."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*(set -[a-z]*x|bash -x)", output.user_data))
    error_message = "Shell tracing would print the tokens into the cloud-init log."
  }
}

run "install_outcome_is_logged_without_tokens" {
  command = apply

  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "FAKE-ACCESS-TOKEN-3"
      refresh_token = "FAKE-REFRESH-TOKEN-3"
    }
  }

  assert {
    condition     = length([for c in yamldecode(output.user_data).runcmd : c if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")]) == 1
    error_message = "Exactly one step must write /var/log/cah-connector-install.log."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(output.user_data).runcmd :
      strcontains(jsonencode(c), "systemctl is-active twingate-connector") && strcontains(jsonencode(c), "journalctl -u twingate-connector -n 50") && strcontains(jsonencode(c), "tail -n 50 /var/log/cloud-init-output.log") && strcontains(jsonencode(c), "chmod 0640")
      if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")
    ])
    error_message = "The log step must record the service state, the last 50 journal lines and the cloud-init output tail, at mode 0640."
  }
  assert {
    condition = !anytrue([
      for c in yamldecode(output.user_data).runcmd :
      strcontains(jsonencode(c), "FAKE-ACCESS-TOKEN-3") || strcontains(jsonencode(c), "FAKE-REFRESH-TOKEN-3") || strcontains(jsonencode(c), "TWINGATE_ACCESS_TOKEN") || strcontains(jsonencode(c), "TWINGATE_REFRESH_TOKEN")
      if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")
    ])
    error_message = "The log step must not read or print a token."
  }
}

run "machine_clock_is_eastern" {
  command = plan
  assert {
    condition     = yamldecode(output.user_data).timezone == "America/New_York"
    error_message = "The reboot window and the weekly update are Eastern time, so the machine timezone must be America/New_York."
  }
}

run "eastern_schedule_for_connector_a_and_b" {
  command = plan
  variables {
    reboot_time = "05:00"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "30 5 * * 0 root")
    error_message = "A 05:00 reboot must put the Sunday connector update at 05:30."
  }
}

run "the_module_exposes_only_a_name_and_the_boot_data_and_creates_no_cloud_resource" {
  command = plan
  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["name", "user_data"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it only after proving it carries no connector secret."
  }
  assert {
    condition     = length(regexall("(?m)^\\s*output \"user_data\"[^}]*sensitive\\s*=\\s*true", file("${path.module}/outputs.tf"))) == 1
    error_message = "user_data carries the connector tokens and must stay sensitive."
  }
  assert {
    condition     = alltrue([for t in flatten(regexall("(?m)^\\s*resource\\s+\"([a-z0-9_]+)\"", file("${path.module}/main.tf"))) : startswith(t, "twingate_")])
    error_message = "The bootstrap module is cloud-neutral: it must create only twingate_* resources."
  }
}

run "connector_joins_the_callers_remote_network_and_is_named_by_instance" {
  command = plan
  variables {
    instance = "b"
  }
  assert {
    condition     = twingate_connector.this.remote_network_id == "remote-network-test" && twingate_connector.this.name == "access-tor1-connector-b" && output.name == "access-tor1-connector-b"
    error_message = "The connector must join the caller's remote network and be named <layer>-<region>-connector-<instance>."
  }
}

# resource_key: the key in NAMES. Empty means region, so the live names stay.

run "resource_key_defaults_to_the_region_in_the_name" {
  command = plan
  assert {
    condition     = output.name == "access-tor1-connector-a"
    error_message = "With no resource_key the connector is named <layer>-<region>-connector-<instance>."
  }
}

run "resource_key_replaces_region_in_the_name_only" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = output.name == "access-tor1-b-connector-a"
    error_message = "A resource_key must replace the region in the name."
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

run "resource_key_accepts_24_characters" {
  command = plan
  variables {
    resource_key = "abcdefghijklmnopqrstuvwx"
  }
  assert {
    condition     = output.name == "access-abcdefghijklmnopqrstuvwx-connector-a"
    error_message = "A 24 character key is the longest allowed."
  }
}

run "resource_key_rejects_an_underscore_and_a_space" {
  command = plan
  variables {
    resource_key = "tor_1"
  }
  expect_failures = [var.resource_key]
}

# --- timezone ----------------------------------------------------------------
# The zone is an input now. The default must render exactly what the literal
# did (the golden hashes above); a different zone may change only that line.

run "default_timezone_renders_the_golden_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time = "04:00"
    timezone    = "America/New_York"
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "Passing the default timezone explicitly must render the golden user_data."
  }
}

run "another_timezone_changes_only_the_timezone_line" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time = "04:00"
    timezone    = "Europe/Paris"
  }
  assert {
    condition     = yamldecode(output.user_data).timezone == "Europe/Paris"
    error_message = "The machine timezone must be the one given."
  }
  assert {
    condition     = sha256(replace(output.user_data, "\ntimezone: Europe/Paris\n", "\ntimezone: America/New_York\n")) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "Changing the timezone must change nothing but the timezone line."
  }
}

run "utc_is_accepted" {
  command = plan
  variables {
    timezone = "UTC"
  }
  assert {
    condition     = yamldecode(output.user_data).timezone == "UTC"
    error_message = "UTC must be accepted."
  }
}

run "three_part_timezone_is_accepted" {
  command = plan
  variables {
    timezone = "America/Argentina/Buenos_Aires"
  }
  assert {
    condition     = yamldecode(output.user_data).timezone == "America/Argentina/Buenos_Aires"
    error_message = "A three-part IANA name must be accepted."
  }
}

run "timezone_rejects_newline_injection" {
  command = plan
  variables {
    timezone = "America/New_York\nruncmd: [\"id\"]"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_trailing_newline" {
  command = plan
  variables {
    timezone = "America/New_York\n"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_yaml_special" {
  command = plan
  variables {
    timezone = "America/New_York: {a: b}"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_comment_marker" {
  command = plan
  variables {
    timezone = "America/New_York # x"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_space" {
  command = plan
  variables {
    timezone = "America/New York"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_no_slash" {
  command = plan
  variables {
    timezone = "Eastern"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_lowercase_utc" {
  command = plan
  variables {
    timezone = "utc"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_empty" {
  command = plan
  variables {
    timezone = ""
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_four_parts" {
  command = plan
  variables {
    timezone = "A/b/c/d"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_template_marker" {
  command = plan
  variables {
    timezone = "America/$${x}"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_a_made_up_zone" {
  command = plan
  variables {
    timezone = "Foo/Bar"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_a_plausible_but_missing_zone" {
  command = plan
  variables {
    timezone = "America/Definitely_Not_A_Zone"
  }
  expect_failures = [var.timezone]
}

run "timezone_rejects_an_out_of_range_etc_zone" {
  command = plan
  variables {
    timezone = "Etc/GMT+99"
  }
  expect_failures = [var.timezone]
}

# ---- connector telemetry (default off) ----

run "explicit_default_telemetry_renders_the_golden_user_data_a" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time         = "04:00"
    connector_telemetry = {}
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "An empty connector_telemetry must render the golden user_data of connector a."
  }
}

run "explicit_default_telemetry_renders_the_golden_user_data_b" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    instance    = "b"
    reboot_time = "05:00"
    connector_telemetry = {
      status_updates_enabled = true
      connection_logs        = false
      labels                 = {}
    }
  }
  assert {
    condition     = sha256(output.user_data) == "de2de6286f955100f199779f2b8a4d0a194b72f28619965c80f858061742790b"
    error_message = "The spelled-out defaults must render the golden user_data of connector b."
  }
}

run "status_updates_is_provider_side_and_never_changes_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time         = "04:00"
    connector_telemetry = { status_updates_enabled = false }
  }
  assert {
    condition     = twingate_connector.this.status_updates_enabled == false
    error_message = "status_updates_enabled must reach the Twingate connector."
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "status_updates_enabled must not touch user_data."
  }
}

run "status_updates_is_not_sent_unless_set" {
  command = plan
  assert {
    condition     = strcontains(file("${path.module}/variables.tf"), "status_updates_enabled = optional(bool)\n") && strcontains(file("${path.module}/main.tf"), "status_updates_enabled = var.connector_telemetry.status_updates_enabled")
    error_message = "status_updates_enabled must be optional(bool) with no default (null when unset) and passed straight to the resource, so the default resource config is what it was before this setting existed."
  }
}

run "status_updates_true_is_sent_when_set" {
  command = plan
  variables {
    connector_telemetry = { status_updates_enabled = true }
  }
  assert {
    condition     = twingate_connector.this.status_updates_enabled == true
    error_message = "An explicit true must reach the Twingate connector."
  }
}

run "an_empty_telemetry_object_plans_and_renders_the_golden_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time         = "04:00"
    connector_telemetry = {}
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "{} must render the golden user_data."
  }
}

run "explicit_null_fields_plan_and_render_the_golden_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time = "04:00"
    connector_telemetry = {
      status_updates_enabled = null
      log_level              = null
      metrics_port           = null
    }
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "Explicit nulls must behave as unset."
  }
}

# nullable = false: OpenTofu replaces a null with the default {} instead of
# letting the attribute accesses crash, so null means "off".
run "a_null_telemetry_object_means_off_not_a_crash" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time         = "04:00"
    connector_telemetry = null
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "A null connector_telemetry must behave as {} and render the golden user_data."
  }
}

run "the_telemetry_variable_is_declared_non_nullable" {
  command = plan
  assert {
    condition     = strcontains(file("${path.module}/variables.tf"), "nullable    = false")
    error_message = "connector_telemetry must declare nullable = false."
  }
}

run "every_telemetry_setting_renders_exactly_its_lines_in_connector_conf" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time = "04:00"
    connector_telemetry = {
      log_level       = 5
      connection_logs = true
      metrics_port    = 9999
      labels          = { SITE = "tor1", DEPLOYED_BY = "opentofu" }
    }
  }
  assert {
    condition = split("\n", one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/twingate/connector.conf"])) == tolist([
      "TWINGATE_URL=https://acme.twingate.com",
      "TWINGATE_ACCESS_TOKEN=fixed-access-token",
      "TWINGATE_REFRESH_TOKEN=fixed-refresh-token",
      "TWINGATE_LOG_LEVEL=5",
      "TWINGATE_LOG_ANALYTICS=v3",
      "TWINGATE_METRICS_PORT=9999",
      "TWINGATE_LABEL_DEPLOYED_BY=opentofu",
      "TWINGATE_LABEL_SITE=tor1",
      "",
    ])
    error_message = "connector.conf must hold the three original lines and then exactly the enabled telemetry lines, labels sorted."
  }
  assert {
    condition     = one([for f in yamldecode(output.user_data).write_files : f.permissions if f.path == "/etc/twingate/connector.conf"]) == "0600"
    error_message = "connector.conf must stay 0600."
  }
  # Nothing else changed: take the five lines out and the golden hash comes back.
  assert {
    condition     = sha256(replace(output.user_data, "      TWINGATE_LOG_LEVEL=5\n      TWINGATE_LOG_ANALYTICS=v3\n      TWINGATE_METRICS_PORT=9999\n      TWINGATE_LABEL_DEPLOYED_BY=opentofu\n      TWINGATE_LABEL_SITE=tor1\n", "")) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "Telemetry may add lines to connector.conf and nothing else to user_data."
  }
  assert {
    condition     = length(regexall("fixed-access-token", output.user_data)) == 1 && length(regexall("fixed-refresh-token", output.user_data)) == 1
    error_message = "Each token must still appear exactly once, in connector.conf."
  }
}

run "only_the_enabled_settings_render" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999 }
  }
  assert {
    condition     = strcontains(output.user_data, "      TWINGATE_METRICS_PORT=9999\n") && !strcontains(output.user_data, "TWINGATE_LOG_") && !strcontains(output.user_data, "TWINGATE_LABEL_")
    error_message = "Only metrics_port was set, so only TWINGATE_METRICS_PORT may be added."
  }
}

run "log_level_3_is_rendered_when_set_explicitly" {
  command = plan
  variables {
    connector_telemetry = { log_level = 3 }
  }
  assert {
    condition     = strcontains(output.user_data, "      TWINGATE_LOG_LEVEL=3\n")
    error_message = "An explicit level is written, even Twingate's default."
  }
}

run "telemetry_user_data_is_still_valid_yaml_with_the_other_files_intact" {
  command = plan
  variables {
    connector_telemetry = {
      log_level = 7
      labels    = { A = "b" }
    }
  }
  assert {
    condition     = length(yamldecode(output.user_data).write_files) == 7
    error_message = "The extra lines must stay inside connector.conf and not start another file."
  }
}

run "log_level_rejects_a_value_twingate_does_not_document" {
  command = plan
  variables {
    connector_telemetry = { log_level = 6 }
  }
  expect_failures = [var.connector_telemetry]
}

run "metrics_port_rejects_a_privileged_port" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 1023 }
  }
  expect_failures = [var.connector_telemetry]
}

run "metrics_port_rejects_65536" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 65536 }
  }
  expect_failures = [var.connector_telemetry]
}

run "metrics_port_rejects_a_fraction" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9999.5 }
  }
  expect_failures = [var.connector_telemetry]
}

run "metrics_port_rejects_the_node_exporter_port" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 9100 }
  }
  expect_failures = [var.connector_telemetry]
}

run "metrics_port_accepts_the_edges" {
  command = plan
  variables {
    connector_telemetry = { metrics_port = 1024 }
  }
  assert {
    condition     = strcontains(output.user_data, "TWINGATE_METRICS_PORT=1024\n")
    error_message = "1024 is allowed."
  }
}

run "labels_reject_a_newline_in_a_value" {
  command = plan
  variables {
    connector_telemetry = { labels = { SITE = "a\nTWINGATE_URL=https://evil.example" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "labels_reject_a_lowercase_key" {
  command = plan
  variables {
    connector_telemetry = { labels = { site = "tor1" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "labels_reject_a_key_that_breaks_the_line" {
  command = plan
  variables {
    connector_telemetry = { labels = { "A=B" = "x" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "labels_reject_a_space_or_quote_in_a_value" {
  command = plan
  variables {
    connector_telemetry = { labels = { SITE = "a b" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "labels_reject_an_empty_value" {
  command = plan
  variables {
    connector_telemetry = { labels = { SITE = "" } }
  }
  expect_failures = [var.connector_telemetry]
}

run "labels_reject_eleven_entries" {
  command = plan
  variables {
    connector_telemetry = { labels = { A = "x", B = "x", C = "x", D = "x", E = "x", F = "x", G = "x", H = "x", I = "x", J = "x", K = "x" } }
  }
  expect_failures = [var.connector_telemetry]
}

# metadata_lock (issue #87): off by default, and off adds nothing at all. The
# golden-hash runs above already prove the default user_data is byte-identical;
# this run names the absent pieces so a failure says what leaked.
run "metadata_lock_default_adds_nothing_to_user_data" {
  command = plan
  assert {
    condition     = !strcontains(output.user_data, "cah-metadata-lock") && !strcontains(output.user_data, "cah_metadata") && !strcontains(output.user_data, "nftables") && !strcontains(output.user_data, "169.254.169.254")
    error_message = "With metadata_lock unset no metadata-lock script, unit, rule or nftables package may appear in user_data."
  }
}

run "metadata_lock_false_is_the_golden_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time   = "04:00"
    metadata_lock = false
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "metadata_lock = false must render the same user_data as before the setting existed."
  }
}

run "metadata_lock_on_installs_script_unit_and_package" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = contains(yamldecode(output.user_data).packages, "nftables") && contains(yamldecode(output.user_data).packages, "chrony")
    error_message = "nftables must be installed next to the existing packages."
  }
  assert {
    condition     = one([for f in yamldecode(output.user_data).write_files : f.permissions if f.path == "/usr/local/sbin/cah-metadata-lock"]) == "0750" && one([for f in yamldecode(output.user_data).write_files : f.owner if f.path == "/usr/local/sbin/cah-metadata-lock"]) == "root:root"
    error_message = "The lock script must be root-owned and 0750."
  }
  assert {
    condition = alltrue([
      for s in ["169.254.169.254", "meta skuid != {", "id -u do-agent", "table inet cah_metadata", "delete table inet cah_metadata", "reject with icmp type admin-prohibited", "set -euo pipefail"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-metadata-lock"]), s)
    ])
    error_message = "The lock script must exempt root and do-agent, use its own idempotent table and reject others."
  }
  assert {
    condition = alltrue([
      for s in ["Type=oneshot", "RemainAfterExit=yes", "After=cloud-final.service network-online.target", "ExecStart=/usr/local/sbin/cah-metadata-lock", "WantedBy=multi-user.target"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/systemd/system/cah-metadata-lock.service"]), s)
    ])
    error_message = "The unit must be a oneshot ordered after cloud-final."
  }
}

run "metadata_lock_on_enables_the_unit_without_blocking" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = contains(yamldecode(output.user_data).runcmd, ["systemctl", "daemon-reload"]) && contains(yamldecode(output.user_data).runcmd, ["systemctl", "enable", "--now", "--no-block", "cah-metadata-lock.service"])
    error_message = "runcmd must daemon-reload and enable the unit with --no-block (cloud-final runs runcmd; blocking would deadlock)."
  }
}

run "metadata_lock_on_keeps_the_rest_of_the_cloud_init" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = length(yamldecode(output.user_data).users) == 1 && strcontains(output.user_data, "TWINGATE_URL=https://acme.twingate.com") && strcontains(output.user_data, "99-cah-hardening")
    error_message = "The lock must be additive."
  }
}

# host_firewall (issue #90): off by default, and off adds nothing at all. The
# golden-hash runs above already prove the default user_data is byte-identical;
# this run names the absent pieces so a failure says what leaked.
run "host_firewall_default_adds_nothing_to_user_data" {
  command = plan
  assert {
    condition     = !strcontains(output.user_data, "cah-host-firewall") && !strcontains(output.user_data, "cah_host") && !strcontains(output.user_data, "nftables") && !strcontains(output.user_data, "policy drop")
    error_message = "With host_firewall unset no firewall script, unit, rule or nftables package may appear in user_data."
  }
}

run "host_firewall_false_is_the_golden_user_data" {
  command = plan
  override_resource {
    target = twingate_connector_tokens.this
    values = {
      access_token  = "fixed-access-token"
      refresh_token = "fixed-refresh-token"
    }
  }
  variables {
    reboot_time   = "04:00"
    host_firewall = false
  }
  assert {
    condition     = sha256(output.user_data) == "3689d9b99f43d41e827f92b183a7ad2f57b5356587060de66bbd1084c0056e0e"
    error_message = "host_firewall = false must render the same user_data as before the setting existed."
  }
}

run "host_firewall_on_installs_script_unit_and_package" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = contains(yamldecode(output.user_data).packages, "nftables") && contains(yamldecode(output.user_data).packages, "chrony")
    error_message = "nftables must be installed next to the existing packages."
  }
  assert {
    condition     = length([for p in yamldecode(output.user_data).packages : p if p == "nftables"]) == 1
    error_message = "nftables must appear exactly once."
  }
  assert {
    condition     = one([for f in yamldecode(output.user_data).write_files : f.permissions if f.path == "/usr/local/sbin/cah-host-firewall"]) == "0750" && one([for f in yamldecode(output.user_data).write_files : f.owner if f.path == "/usr/local/sbin/cah-host-firewall"]) == "root:root"
    error_message = "The firewall script must be root-owned and 0750."
  }
  assert {
    condition = alltrue([
      for s in ["table inet cah_host", "delete table inet cah_host", "policy drop", "ct state established,related accept", "ct state invalid drop", "udp sport 67 udp dport 68 accept", "tcp dport 22 ip saddr", "nft -c -f -", "nft delete table inet cah_host", "set -euo pipefail", "ssh_sources=\"10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16\"", "metrics_port=\"\""] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), s)
    ])
    error_message = "The script must check, load an idempotent drop-by-default table with the default private ssh sources, and roll back."
  }
  assert {
    condition     = !strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), "flush ruleset") && !strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), "cah_metadata")
    error_message = "The firewall must never flush the ruleset or touch the metadata-lock table."
  }
  assert {
    condition = alltrue([
      for s in ["Type=oneshot", "RemainAfterExit=yes", "After=cloud-final.service network-online.target", "ExecStart=/usr/local/sbin/cah-host-firewall", "WantedBy=multi-user.target"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/systemd/system/cah-host-firewall.service"]), s)
    ])
    error_message = "The unit must be a oneshot ordered after cloud-final."
  }
}

run "host_firewall_on_enables_the_unit_without_blocking" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = contains(yamldecode(output.user_data).runcmd, ["systemctl", "daemon-reload"]) && contains(yamldecode(output.user_data).runcmd, ["systemctl", "enable", "--now", "--no-block", "cah-host-firewall.service"])
    error_message = "runcmd must daemon-reload and enable the unit with --no-block (cloud-final runs runcmd; blocking would deadlock)."
  }
}

run "host_firewall_on_keeps_the_rest_of_the_cloud_init" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = length(yamldecode(output.user_data).users) == 1 && strcontains(output.user_data, "TWINGATE_URL=https://acme.twingate.com") && strcontains(output.user_data, "99-cah-hardening")
    error_message = "The firewall must be additive."
  }
}

run "host_firewall_metrics_port_is_empty_without_telemetry" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), "metrics_port=\"\"")
    error_message = "Without connector_telemetry.metrics_port no metrics rule may be configured."
  }
}

run "host_firewall_metrics_port_follows_telemetry" {
  command = plan
  variables {
    host_firewall       = true
    connector_telemetry = { metrics_port = 9999 }
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), "metrics_port=\"9999\"")
    error_message = "connector_telemetry.metrics_port must reach the firewall script."
  }
}

run "host_firewall_custom_sources_are_rendered" {
  command = plan
  variables {
    host_firewall             = true
    host_firewall_ssh_sources = ["10.20.0.0/16", "192.0.2.7/32"]
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/usr/local/sbin/cah-host-firewall"]), "ssh_sources=\"10.20.0.0/16, 192.0.2.7/32\"")
    error_message = "host_firewall_ssh_sources must be rendered into the script."
  }
}

run "host_firewall_sources_reject_a_non_cidr" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.1"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_injection" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.0/8 } accept; ip saddr { 0.0.0.0/0"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_ipv6" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["fd00::/8"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_an_empty_list" {
  command = plan
  variables {
    host_firewall_ssh_sources = []
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_sources_reject_a_repeat" {
  command = plan
  variables {
    host_firewall_ssh_sources = ["10.0.0.0/8", "10.0.0.0/8"]
  }
  expect_failures = [var.host_firewall_ssh_sources]
}

run "host_firewall_and_metadata_lock_render_nftables_once_and_both_tables" {
  command = plan
  variables {
    host_firewall = true
    metadata_lock = true
  }
  assert {
    condition     = length([for p in yamldecode(output.user_data).packages : p if p == "nftables"]) == 1
    error_message = "nftables must be listed once when both features are on."
  }
  assert {
    condition     = strcontains(output.user_data, "table inet cah_metadata") && strcontains(output.user_data, "table inet cah_host")
    error_message = "Both tables must be present when both features are on."
  }
  assert {
    condition     = contains(yamldecode(output.user_data).runcmd, ["systemctl", "enable", "--now", "--no-block", "cah-host-firewall.service"]) && contains(yamldecode(output.user_data).runcmd, ["systemctl", "enable", "--now", "--no-block", "cah-metadata-lock.service"])
    error_message = "Both units must be enabled."
  }
}

run "metadata_lock_alone_still_renders_nftables_once" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition     = length([for p in yamldecode(output.user_data).packages : p if p == "nftables"]) == 1 && !strcontains(output.user_data, "cah_host")
    error_message = "The metadata lock alone must keep one nftables entry and no firewall."
  }
}

# Persistence (issue #90 review): Ubuntu's nftables.service starts with
# `flush ruleset` and is try-restarted by package upgrades, which would drop our
# tables silently. Both units must be ordered after it and be part of it so a
# restart of nftables.service re-runs our script.
run "host_firewall_unit_follows_nftables_service" {
  command = plan
  variables {
    host_firewall = true
  }
  assert {
    condition = alltrue([
      for s in ["After=nftables.service", "PartOf=nftables.service", "ReloadPropagatedFrom=nftables.service", "ExecReload=/usr/local/sbin/cah-host-firewall", "After=cloud-final.service network-online.target"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/systemd/system/cah-host-firewall.service"]), s)
    ])
    error_message = "cah-host-firewall.service must be After= and PartOf= nftables.service."
  }
}

run "metadata_lock_unit_follows_nftables_service" {
  command = plan
  variables {
    metadata_lock = true
  }
  assert {
    condition = alltrue([
      for s in ["After=nftables.service", "PartOf=nftables.service", "ReloadPropagatedFrom=nftables.service", "ExecReload=/usr/local/sbin/cah-metadata-lock", "After=cloud-final.service network-online.target"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == "/etc/systemd/system/cah-metadata-lock.service"]), s)
    ])
    error_message = "cah-metadata-lock.service must be After= and PartOf= nftables.service."
  }
}

run "both_units_follow_nftables_service_when_both_features_are_on" {
  command = plan
  variables {
    host_firewall = true
    metadata_lock = true
  }
  assert {
    condition = alltrue([
      for p in ["/etc/systemd/system/cah-host-firewall.service", "/etc/systemd/system/cah-metadata-lock.service"] :
      strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == p]), "PartOf=nftables.service") && strcontains(one([for f in yamldecode(output.user_data).write_files : f.content if f.path == p]), "After=nftables.service")
    ])
    error_message = "Both units must follow nftables.service."
  }
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
