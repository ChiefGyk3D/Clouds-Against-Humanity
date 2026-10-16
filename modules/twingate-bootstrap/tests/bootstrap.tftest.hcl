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

run "admin_key_rejects_a_comment_and_a_newline" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAA user@host"
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
