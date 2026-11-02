# SPDX-License-Identifier: Apache-2.0
# modules/docker-host: one hardened droplet running Docker Engine and Portainer
# CE. Every run plans with mocked providers; nothing reaches DigitalOcean.

mock_provider "digitalocean" {}

variables {
  layer                = "workload"
  region               = "tor1"
  vpc_id               = "00000000-0000-0000-0000-000000000000"
  tags                 = ["cah-baseline-tor1", "cah-workload-tor1"]
  size                 = "s-1vcpu-2gb"
  ssh_key_fingerprint  = "aa:bb:cc:dd:ee:ff"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest"
  reboot_time          = "03:30"
}

# --- the droplet --------------------------------------------------------------

run "names_follow_layer_key_role" {
  command = plan
  assert {
    condition     = digitalocean_droplet.workload.name == "workload-tor1-docker"
    error_message = "The droplet must be named <layer>-<region>-docker."
  }
  assert {
    condition     = output.instance_name == "workload-tor1-docker"
    error_message = "The instance_name output must be the droplet name."
  }
}

run "resource_key_replaces_the_region_in_the_name_only" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_droplet.workload.name == "workload-tor1-b-docker" && digitalocean_droplet.workload.region == "tor1"
    error_message = "resource_key names the droplet; the region argument stays the real region."
  }
}

run "the_droplet_is_private_key_only_and_unbacked" {
  command = plan
  assert {
    condition     = digitalocean_droplet.workload.ipv6 == false && digitalocean_droplet.workload.backups == false && digitalocean_droplet.workload.monitoring == true
    error_message = "ipv6 and backups stay off (backups are not priced); monitoring stays on."
  }
  assert {
    condition     = digitalocean_droplet.workload.ssh_keys == toset(["aa:bb:cc:dd:ee:ff"])
    error_message = "The droplet must carry exactly the admin SSH key."
  }
  assert {
    condition     = digitalocean_droplet.workload.image == "ubuntu-24-04-x64" && digitalocean_droplet.workload.size == "s-1vcpu-2gb" && digitalocean_droplet.workload.vpc_uuid == "00000000-0000-0000-0000-000000000000"
    error_message = "Image, size and VPC must be as declared."
  }
  assert {
    condition     = toset(digitalocean_droplet.workload.tags) == toset(["cah-baseline-tor1", "cah-workload-tor1"])
    error_message = "Tags are set at creation, so both firewalls apply from the first second."
  }
}

run "the_contract_outputs_exist" {
  command = apply
  assert {
    condition     = output.instance_id != "" && output.droplet_urn != "" && output.private_ip != "" && output.size == "s-1vcpu-2gb" && output.portainer_port == 9443
    error_message = "The module must output instance_id, droplet_urn, private_ip, size and portainer_port."
  }
}

# --- the cloud-init -----------------------------------------------------------

run "first_hour_order_update_baseline_harden_then_applications" {
  command = plan
  assert {
    condition     = can(regex("(?s)package_update: true.*package_upgrade: true.*unattended-upgrades", digitalocean_droplet.workload.user_data))
    error_message = "The package update, upgrade and unattended-upgrades come first."
  }
  assert {
    condition     = can(regex("(?s)write_files:.*sshd_config\\.d/99-cah-hardening\\.conf.*runcmd:.*sshd -t && systemctl restart ssh.*apt-get install -yq docker-ce", digitalocean_droplet.workload.user_data))
    error_message = "The baseline files are written, then sshd is hardened and restarted, and only then is Docker installed."
  }
  assert {
    condition     = can(regex("(?s)apt-get install -yq docker-ce.*cah-portainer-up", digitalocean_droplet.workload.user_data))
    error_message = "Portainer starts after Docker is installed."
  }
}

run "ssh_is_key_only" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "PasswordAuthentication no") && strcontains(digitalocean_droplet.workload.user_data, "PermitRootLogin no") && strcontains(digitalocean_droplet.workload.user_data, "KbdInteractiveAuthentication no") && strcontains(digitalocean_droplet.workload.user_data, "AllowUsers cah-admin")
    error_message = "sshd must refuse passwords and root and admit only cah-admin."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "ssh_pwauth: false") && strcontains(digitalocean_droplet.workload.user_data, "disable_root: true") && strcontains(digitalocean_droplet.workload.user_data, "lock_passwd: true")
    error_message = "cloud-init must lock the passwords too."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "- ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest\n")
    error_message = "The admin public key must be the only authorized key, rendered without a comment."
  }
}

run "a_key_comment_is_dropped" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest admin@example.com"
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "admin@example.com")
    error_message = "A trailing comment must not reach user_data."
  }
}

run "docker_comes_from_the_signed_repository_with_a_pinned_key" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "https://download.docker.com/linux/ubuntu/gpg") && strcontains(digitalocean_droplet.workload.user_data, "cah-apt-key-check /root/docker.gpg.key \"$FPR\"") && strcontains(digitalocean_droplet.workload.user_data, "FPR=9DC858229FC7DD38854AE2D88D81803C0EBFCD88")
    error_message = "The Docker key must be checked against the pinned fingerprint before it is trusted."
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "get.docker.com")
    error_message = "No piped installer script."
  }
  assert {
    condition     = !can(regex("(?i)curl[^\\n]*\\|\\s*(ba)?sh", digitalocean_droplet.workload.user_data))
    error_message = "Nothing may be piped from curl into a shell."
  }
}

run "the_docker_daemon_has_no_network_socket_and_binds_loopback_by_default" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "\"live-restore\": true") && strcontains(digitalocean_droplet.workload.user_data, "\"ip\": \"127.0.0.1\"") && strcontains(digitalocean_droplet.workload.user_data, "\"max-size\": \"10m\"")
    error_message = "daemon.json needs live-restore, a loopback default bind address and capped logs."
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "\"hosts\"") && !strcontains(digitalocean_droplet.workload.user_data, "tcp://") && !strcontains(digitalocean_droplet.workload.user_data, "2375") && !strcontains(digitalocean_droplet.workload.user_data, "2376")
    error_message = "The Docker API must stay on the local socket: no hosts entry, no tcp://, no 2375 or 2376."
  }
}

run "portainer_is_pinned_bound_to_the_private_address_and_limited" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "image: portainer/portainer-ce:2.45.3@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96e")
    error_message = "Portainer CE must be pinned to an exact version tag and to its image digest."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "- \"$${PORTAINER_BIND:?}:9443:9443\"")
    error_message = "Portainer's only published port must be bound to the private address, with no default for the address."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "mem_limit:") && strcontains(digitalocean_droplet.workload.user_data, "no-new-privileges:true")
    error_message = "Every compose service needs a memory limit and no-new-privileges."
  }
}

run "no_published_port_is_unbound" {
  command = plan
  # Every list item under a ports: key in the compose file names an address.
  assert {
    condition     = length(regexall("(?m)^\\s+- \"[0-9]+:[0-9]+\"", digitalocean_droplet.workload.user_data)) == 0 && length(regexall("(?m)^\\s+- [0-9]+:[0-9]+\\s*$", digitalocean_droplet.workload.user_data)) == 0
    error_message = "A published port without an address would listen on every interface."
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "0.0.0.0") && !strcontains(digitalocean_droplet.workload.user_data, "[::]") && !strcontains(digitalocean_droplet.workload.user_data, "\"::\"") && !strcontains(digitalocean_droplet.workload.user_data, "network_mode: host")
    error_message = "No wildcard address and no host networking anywhere in the cloud-init."
  }
}

run "the_portainer_address_comes_from_the_vpc_metadata_and_fails_closed" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "/metadata/v1/interfaces/private/0/ipv4/address") && strcontains(digitalocean_droplet.workload.user_data, "refusing to start Portainer")
    error_message = "The private address is read from the metadata endpoint, and a missing address stops the start instead of falling back to a wildcard."
  }
}

run "unattended_upgrades_reboot_in_the_given_window" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "Unattended-Upgrade::Automatic-Reboot-Time \"03:30\";") && strcontains(digitalocean_droplet.workload.user_data, "timezone: America/New_York")
    error_message = "The reboot window and time zone must render."
  }
}

run "user_data_carries_no_secret" {
  command = plan
  assert {
    condition     = !can(regex("(?i)token|api[_-]?key|secret|password:", digitalocean_droplet.workload.user_data))
    error_message = "User-data is readable from the metadata endpoint and lands in state: it carries no secret-shaped value."
  }
}

# --- inputs are validated -----------------------------------------------------

run "latest_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "latest"
  }
  expect_failures = [var.portainer_version]
}

run "a_range_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "2.45@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96e"
  }
  expect_failures = [var.portainer_version]
}

run "a_tag_without_a_digest_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "2.45.3"
  }
  expect_failures = [var.portainer_version]
}

run "a_short_or_uppercase_digest_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "2.45.3@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96"
  }
  expect_failures = [var.portainer_version]
}

run "a_digest_alone_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96e"
  }
  expect_failures = [var.portainer_version]
}

run "a_second_image_reference_is_not_a_portainer_version" {
  command = plan
  variables {
    portainer_version = "2.45.3@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96e\n  other: image"
  }
  expect_failures = [var.portainer_version]
}

run "the_docker_key_pin_must_be_a_full_fingerprint" {
  command = plan
  variables {
    docker_apt_key_fingerprint = "0EBFCD88"
  }
  expect_failures = [var.docker_apt_key_fingerprint]
}

run "portainer_port_is_a_unprivileged_port" {
  command = plan
  variables {
    portainer_port = 443
  }
  expect_failures = [var.portainer_port]
}

run "portainer_port_is_not_the_ssh_port" {
  command = plan
  variables {
    portainer_port = 22
  }
  expect_failures = [var.portainer_port]
}

run "a_bad_reboot_time_is_refused" {
  command = plan
  variables {
    reboot_time = "25:00"
  }
  expect_failures = [var.reboot_time]
}

run "a_bad_admin_key_is_refused" {
  command = plan
  variables {
    admin_ssh_public_key = "not a key"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "a_key_with_a_line_break_is_refused" {
  command = plan
  variables {
    admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest\nruncmd: evil"
  }
  expect_failures = [var.admin_ssh_public_key]
}

run "a_bad_resource_key_is_refused" {
  command = plan
  variables {
    resource_key = "Bad Key"
  }
  expect_failures = [var.resource_key]
}

run "a_bad_timezone_is_refused" {
  command = plan
  variables {
    timezone = "America/New York\nevil: 1"
  }
  expect_failures = [var.timezone]
}

run "an_empty_ssh_key_fingerprint_is_refused" {
  command = plan
  variables {
    ssh_key_fingerprint = ""
  }
  expect_failures = [var.ssh_key_fingerprint]
}

run "an_empty_tag_list_is_refused" {
  command = plan
  variables {
    tags = []
  }
  expect_failures = [var.tags]
}

# --- the optional onion service (issue #391; default off, nothing applied) -------

run "the_onion_service_is_off_by_default_and_the_user_data_says_nothing_about_it" {
  command = plan
  assert {
    condition     = var.onion_service_enabled == false
    error_message = "onion_service_enabled must default to false."
  }
  assert {
    condition     = !can(regex("(?i)hiddenservice|onion|/etc/tor|cah-onion|torrc", digitalocean_droplet.workload.user_data))
    error_message = "With the flag off the user_data must not mention Tor or the onion origin at all."
  }
}

run "the_onion_flag_renders_a_loopback_origin_and_a_tor_that_only_forwards_to_it" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "HiddenServiceDir /var/lib/tor/cah-site/") && strcontains(digitalocean_droplet.workload.user_data, "HiddenServicePort 80 127.0.0.1:8080") && strcontains(digitalocean_droplet.workload.user_data, "HiddenServiceVersion 3")
    error_message = "The torrc must define one version 3 service whose only target is the loopback origin."
  }
  assert {
    condition     = length(regexall("(?m)^\\s*HiddenServicePort ", digitalocean_droplet.workload.user_data)) == 1
    error_message = "Exactly one HiddenServicePort line."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "- \"127.0.0.1:8080:8080\"")
    error_message = "The origin's only published port must name the loopback address."
  }
  assert {
    condition     = !can(regex("(?m)^\\s*(ORPort|DirPort|ExitRelay|BridgeRelay|ControlPort|HiddenServiceNonAnonymousMode|HiddenServiceSingleHopMode)\\b", digitalocean_droplet.workload.user_data))
    error_message = "The torrc must not make this host a relay, a bridge, an exit, a single-hop service or open a control port."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "SocksPort 0")
    error_message = "A service host needs no SOCKS listener."
  }
}

run "the_onion_flag_keeps_tors_outbound_inside_the_firewalls_default_ports" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "ReachableAddresses *:443,*:80")
    error_message = "Tor must be told it may reach out on 443 and 80 only, the outbound ports the firewall module allows by default."
  }
}

run "the_onion_flag_adds_no_wildcard_no_secret_and_no_key_or_address_to_the_user_data" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "0.0.0.0") && !strcontains(digitalocean_droplet.workload.user_data, "[::]") && !strcontains(digitalocean_droplet.workload.user_data, "\"::\"") && !strcontains(digitalocean_droplet.workload.user_data, "network_mode: host")
    error_message = "No wildcard address and no host networking, with the flag on."
  }
  assert {
    condition     = length(regexall("(?m)^\\s+- \"[0-9]+:[0-9]+\"", digitalocean_droplet.workload.user_data)) == 0 && length(regexall("(?m)^\\s+- [0-9]+:[0-9]+\\s*$", digitalocean_droplet.workload.user_data)) == 0
    error_message = "A published port without an address would listen on every interface."
  }
  assert {
    # The same pattern as user_data_carries_no_secret above, applied to the flag-on text. The one
    # nginx directive that contains the word "token" (server_tokens, which hides the version) is
    # removed first, by name, so any other occurrence still fails.
    condition     = !can(regex("(?i)token|api[_-]?key|secret|password:", replace(digitalocean_droplet.workload.user_data, "server_tokens off;", "")))
    error_message = "The user_data still carries no secret-shaped value with the flag on."
  }
  assert {
    condition     = !can(regex("hs_ed25519|[a-z2-7]{16,56}\\.onion", digitalocean_droplet.workload.user_data))
    error_message = "No service key file name and no onion address in the user_data: the key is made on the host and the address is never known to the plan."
  }
  assert {
    condition     = !strcontains(digitalocean_droplet.workload.user_data, "\"hosts\"") && !strcontains(digitalocean_droplet.workload.user_data, "tcp://") && !strcontains(digitalocean_droplet.workload.user_data, "2375") && !strcontains(digitalocean_droplet.workload.user_data, "2376")
    error_message = "The Docker API still has no network socket with the flag on."
  }
}

run "the_onion_origin_is_pinned_by_tag_and_digest_and_limited" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = can(regex("image: docker\\.io/library/nginx:[0-9]+\\.[0-9]+\\.[0-9]+-alpine@sha256:[0-9a-f]{64}", digitalocean_droplet.workload.user_data))
    error_message = "The origin image must be pinned by tag and by digest."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "server_tokens off;") && !strcontains(digitalocean_droplet.workload.user_data, "stub_status") && !strcontains(digitalocean_droplet.workload.user_data, "autoindex on")
    error_message = "The origin must not print its version, expose a status page or list directories."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.workload.user_data, "read_only: true") && strcontains(digitalocean_droplet.workload.user_data, "cap_drop:")
    error_message = "The origin container is read-only with its capabilities dropped."
  }
}

run "the_onion_install_verifies_the_config_before_it_starts_tor_and_never_prints_the_address" {
  command = plan
  variables {
    onion_service_enabled = true
  }
  assert {
    condition     = can(regex("(?s)tor --verify-config.*systemctl (restart|enable --now|start) tor", digitalocean_droplet.workload.user_data))
    error_message = "tor --verify-config must run before Tor is started."
  }
  assert {
    condition     = !can(regex("cat[^\\n]*hostname|hostname[^\\n]*>>?[^\\n]*(log|install)", digitalocean_droplet.workload.user_data))
    error_message = "The install log is not a place for the onion address."
  }
}

run "a_floating_onion_origin_image_is_refused" {
  command = plan
  variables {
    onion_service_enabled = true
    onion_origin_image    = "nginx:latest"
  }
  expect_failures = [var.onion_origin_image]
}

run "a_tag_without_a_digest_is_not_a_pinned_onion_origin_image" {
  command = plan
  variables {
    onion_service_enabled = true
    onion_origin_image    = "nginx:1.30.6-alpine"
  }
  expect_failures = [var.onion_origin_image]
}
