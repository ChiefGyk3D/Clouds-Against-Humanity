mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  layer               = "access"
  region              = "nyc3"
  vpc_id              = "vpc-test"
  tags                = ["cah-baseline-nyc3", "cah-connector-nyc3"]
  size                = "s-1vcpu-1gb-intel"
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
    condition     = contains(digitalocean_droplet.connector.tags, "cah-baseline-nyc3")
    error_message = "The baseline tag must be on the droplet at creation."
  }
  assert {
    condition     = digitalocean_droplet.connector.vpc_uuid == "vpc-test"
    error_message = "The connector must live in the given VPC."
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-nyc3-connector-a"
    error_message = "Name must be <layer>-<region>-connector-<instance>."
  }
}

run "connector_and_droplet_names_carry_the_instance" {
  command = plan
  variables {
    instance = "b"
  }
  assert {
    condition     = twingate_connector.this.name == "access-nyc3-connector-b" && digitalocean_droplet.connector.name == "access-nyc3-connector-b"
    error_message = "Both the Twingate connector and the droplet must be named with the instance letter."
  }
}

run "shared_site_and_key_come_from_the_caller" {
  command = plan
  assert {
    condition     = twingate_connector.this.remote_network_id == "remote-network-test" && contains(digitalocean_droplet.connector.ssh_keys, "aa:bb:cc:dd")
    error_message = "The connector must use the caller's remote network and SSH key fingerprint."
  }
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "twingate_remote_network") && !strcontains(file("${path.module}/main.tf"), "digitalocean_ssh_key")
    error_message = "The remote network and SSH key are shared, so the module must not create them."
  }
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

run "no_paid_extras_and_no_ipv6" {
  command = plan
  assert {
    condition     = digitalocean_droplet.connector.size == "s-1vcpu-1gb-intel"
    error_message = "Size must come from the variable."
  }
  assert {
    condition     = digitalocean_droplet.connector.backups == false && digitalocean_droplet.connector.ipv6 == false
    error_message = "Backups and IPv6 must stay off (they are unpriced)."
  }
}

run "cloud_init_installs_connector_for_the_network" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_URL=https://acme.twingate.com")
    error_message = "cloud-init must point the connector at the Twingate network."
  }
}

run "tokens_never_leave_the_module" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/outputs.tf"), "token")
    error_message = "No output may mention or expose connector tokens."
  }
}

run "network_slug_accepts_bare_subdomain" {
  command = plan
  variables {
    twingate_network = "acme-2"
  }
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_URL=https://acme-2.twingate.com")
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
    condition     = strcontains(digitalocean_droplet.connector.user_data, "pipefail") && strcontains(digitalocean_droplet.connector.user_data, "--proto '=https' --tlsv1.2")
    error_message = "The install pipeline must use pipefail and hardened curl."
  }
}

run "outputs_never_carry_connector_secrets" {
  command = apply

  override_resource {
    target = twingate_connector_tokens.this
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
    condition     = length(regexall("output \"", file("${path.module}/outputs.tf"))) == 4
    error_message = "outputs.tf must declare exactly 4 outputs. Add one only after proving it carries no connector secret and extending this test."
  }

  assert {
    condition     = jsonencode(sort(flatten(regexall("output \"([A-Za-z0-9_-]+)\"", file("${path.module}/outputs.tf"))))) == jsonencode(["droplet_name", "droplet_urn", "private_ip", "size"])
    error_message = "outputs.tf declares an output this test does not inspect. Add it here only after proving it carries no connector secret."
  }

  assert {
    condition = !anytrue([
      for v in [output.droplet_name, output.droplet_urn, output.private_ip, output.size] :
      strcontains(tostring(v), "FAKE-ACCESS-TOKEN-1") || strcontains(tostring(v), "FAKE-REFRESH-TOKEN-1")
    ])
    error_message = "A module output carries a connector access or refresh token."
  }
}

# Hardening of the rendered cloud-init. The yamldecode calls double as the
# valid-YAML check: an invalid document fails the run.

run "cloud_init_is_valid_yaml_with_a_key_only_admin_user" {
  command = plan
  assert {
    condition     = yamldecode(digitalocean_droplet.connector.user_data).disable_root == true && yamldecode(digitalocean_droplet.connector.user_data).ssh_pwauth == false
    error_message = "Root login and SSH passwords must be disabled in cloud-init."
  }
  assert {
    condition     = length(yamldecode(digitalocean_droplet.connector.user_data).users) == 1 && yamldecode(digitalocean_droplet.connector.user_data).users[0].name == "cah-admin"
    error_message = "Exactly one user, cah-admin, must be declared (no default ubuntu user)."
  }
  assert {
    condition     = yamldecode(digitalocean_droplet.connector.user_data).users[0].ssh_authorized_keys == ["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"]
    error_message = "cah-admin must carry the admin public key."
  }
  assert {
    condition     = yamldecode(digitalocean_droplet.connector.user_data).users[0].lock_passwd == true && yamldecode(digitalocean_droplet.connector.user_data).users[0].sudo == "ALL=(ALL) NOPASSWD:ALL"
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
      contains(split("\n", one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/ssh/sshd_config.d/99-cah-hardening.conf"])), line)
    ])
    error_message = "The sshd drop-in must contain every hardening line."
  }
  assert {
    condition     = !can(regex("(?i)PermitRootLogin\\s+(yes|prohibit-password|without-password)", digitalocean_droplet.connector.user_data))
    error_message = "No part of the user_data may allow root login."
  }
}

run "unattended_upgrades_reboot_at_the_instance_time" {
  command = plan
  variables {
    reboot_time = "04:00"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/52cah-unattended-upgrades"]), "Unattended-Upgrade::Automatic-Reboot-Time \"04:00\";")
    error_message = "The reboot time must come from the reboot_time input."
  }
  assert {
    condition = alltrue([
      for line in ["Unattended-Upgrade::Automatic-Reboot \"true\";", "Unattended-Upgrade::Automatic-Reboot-WithUsers \"true\";", "Unattended-Upgrade::Remove-Unused-Dependencies \"true\";"] :
      strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/52cah-unattended-upgrades"]), line)
    ])
    error_message = "Automatic reboot (with users) and unused-dependency removal must be on."
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "30 4 * * 0 root")
    error_message = "The weekly connector update must run half an hour after the reboot time."
  }
}

run "update_time_carries_across_the_hour_and_midnight" {
  command = plan
  variables {
    reboot_time = "23:45"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "15 0 * * 0 root")
    error_message = "23:45 plus 30 minutes must be 00:15."
  }
}

run "chrony_and_sysctl_are_configured_without_touching_ip_forward" {
  command = plan
  assert {
    condition     = contains(yamldecode(digitalocean_droplet.connector.user_data).packages, "chrony") && contains(yamldecode(digitalocean_droplet.connector.user_data).packages, "unattended-upgrades")
    error_message = "chrony and unattended-upgrades must be installed."
  }
  assert {
    condition = alltrue([
      for k in ["net.ipv4.tcp_syncookies = 1", "net.ipv4.conf.all.log_martians = 1", "net.ipv4.conf.all.accept_redirects = 0", "net.ipv4.conf.all.accept_source_route = 0", "net.ipv4.conf.all.rp_filter = 2"] :
      strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/sysctl.d/99-cah-hardening.conf"]), k)
    ])
    error_message = "The sysctl drop-in must carry the safe hardening settings."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*net\\.ipv[46]\\.(conf\\.[a-z]+\\.)?(ip_)?forwarding\\s*=", digitalocean_droplet.connector.user_data))
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
    condition     = length(regexall("FAKE-ACCESS-TOKEN-2", digitalocean_droplet.connector.user_data)) == 1 && length(regexall("FAKE-REFRESH-TOKEN-2", digitalocean_droplet.connector.user_data)) == 1
    error_message = "Each token must appear exactly once, in the connector config."
  }
  assert {
    condition = alltrue([
      for f in yamldecode(digitalocean_droplet.connector.user_data).write_files :
      f.path == "/etc/twingate/connector.conf" && f.permissions == "0600" && f.owner == "root:root"
      if strcontains(f.content, "FAKE-ACCESS-TOKEN-2") || strcontains(f.content, "FAKE-REFRESH-TOKEN-2")
    ]) && length([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f if strcontains(f.content, "FAKE-ACCESS-TOKEN-2")]) == 1
    error_message = "The tokens may only be written to /etc/twingate/connector.conf, mode 0600, owned by root."
  }
  assert {
    condition     = !anytrue([for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd : strcontains(jsonencode(c), "FAKE-ACCESS-TOKEN-2") || strcontains(jsonencode(c), "FAKE-REFRESH-TOKEN-2")])
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
    condition     = strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/apt/apt.conf.d/99cah-lock-wait"]), "DPkg::Lock::Timeout \"300\";")
    error_message = "apt must wait up to 300 seconds for the dpkg lock."
  }
}

run "installer_does_not_run_the_vendor_script_or_pipe_into_a_shell" {
  command = plan
  assert {
    condition     = !anytrue([for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd : strcontains(jsonencode(c), "setup.sh")])
    error_message = "Twingate's setup.sh must not be run; piped into bash it can lose the rest of the script to apt."
  }
  assert {
    condition     = !anytrue([for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd : can(regex("\\|\\s*(ba|da)?sh\\b", jsonencode(c)))])
    error_message = "Nothing may be piped into a shell."
  }
}

run "repository_key_is_pinned_and_service_is_verified" {
  command = plan
  assert {
    condition = alltrue([
      for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd :
      strcontains(jsonencode(c), "FPR=EC952DEE4701A407A82B0C505C363F09A9174A9E") && strcontains(jsonencode(c), "gpg --show-keys --with-colons") && strcontains(jsonencode(c), "signed-by=$KEYRING") && strcontains(jsonencode(c), "https://packages.twingate.com/apt/")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "The Twingate repository key must be checked against the pinned fingerprint and the repository must be signed-by that key."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd :
      strcontains(jsonencode(c), "systemctl enable --now twingate-connector") && strcontains(jsonencode(c), "systemctl is-active --quiet twingate-connector") && strcontains(jsonencode(c), "DEBIAN_FRONTEND=noninteractive")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "An attempt only counts as a success when the service is active, and apt must run non-interactively."
  }
}

run "installer_is_retried_a_bounded_number_of_times" {
  command = plan
  assert {
    condition     = length([for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd : c if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")]) == 1
    error_message = "The connector package must be installed from exactly one runcmd step."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd :
      strcontains(jsonencode(c), "seq 1 10") && strcontains(jsonencode(c), "sleep 30") && strcontains(jsonencode(c), "exit 1") && strcontains(jsonencode(c), "pipefail")
      if strcontains(jsonencode(c), "apt-get install -yq twingate-connector")
    ])
    error_message = "The install step must retry 10 times, 30 seconds apart, under pipefail, and exit 1 when every attempt fails."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*(set -[a-z]*x|bash -x)", digitalocean_droplet.connector.user_data))
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
    condition     = length([for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd : c if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")]) == 1
    error_message = "Exactly one step must write /var/log/cah-connector-install.log."
  }
  assert {
    condition = alltrue([
      for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd :
      strcontains(jsonencode(c), "systemctl is-active twingate-connector") && strcontains(jsonencode(c), "journalctl -u twingate-connector -n 50") && strcontains(jsonencode(c), "tail -n 50 /var/log/cloud-init-output.log") && strcontains(jsonencode(c), "chmod 0640")
      if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")
    ])
    error_message = "The log step must record the service state, the last 50 journal lines and the cloud-init output tail, at mode 0640."
  }
  assert {
    condition = !anytrue([
      for c in yamldecode(digitalocean_droplet.connector.user_data).runcmd :
      strcontains(jsonencode(c), "FAKE-ACCESS-TOKEN-3") || strcontains(jsonencode(c), "FAKE-REFRESH-TOKEN-3") || strcontains(jsonencode(c), "TWINGATE_ACCESS_TOKEN") || strcontains(jsonencode(c), "TWINGATE_REFRESH_TOKEN")
      if strcontains(jsonencode(c), "/var/log/cah-connector-install.log")
    ])
    error_message = "The log step must not read or print a token."
  }
}

run "droplet_clock_is_eastern" {
  command = plan
  assert {
    condition     = yamldecode(digitalocean_droplet.connector.user_data).timezone == "America/New_York"
    error_message = "The reboot window and the weekly update are Eastern time, so the droplet timezone must be America/New_York."
  }
}

run "eastern_schedule_for_connector_a_and_b" {
  command = plan
  variables {
    reboot_time = "05:00"
  }
  assert {
    condition     = strcontains(one([for f in yamldecode(digitalocean_droplet.connector.user_data).write_files : f.content if f.path == "/etc/cron.d/twingate-connector-update"]), "30 5 * * 0 root")
    error_message = "A 05:00 reboot must put the Sunday connector update at 05:30."
  }
}
