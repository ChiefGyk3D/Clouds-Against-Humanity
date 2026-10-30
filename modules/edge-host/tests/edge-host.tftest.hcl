# SPDX-License-Identifier: Apache-2.0
mock_provider "digitalocean" {
  # The real droplet id is numeric; the reserved IP assignment needs a number.
  mock_resource "digitalocean_droplet" {
    defaults = {
      id = "12345678"
    }
  }
  mock_resource "digitalocean_reserved_ip" {
    defaults = {
      ip_address = "203.0.113.10"
    }
  }
}

variables {
  layer      = "edge"
  region     = "tor1"
  vpc_id     = "00000000-0000-0000-0000-000000000000"
  tags       = ["rns-dmz", "rns-dmz-transport"]
  size       = "s-1vcpu-1gb"
  service    = "reticulum"
  project_id = "00000000-0000-0000-0000-000000000001"
}

run "names_follow_layer_key_role" {
  command = plan
  assert {
    condition     = digitalocean_droplet.edge.name == "edge-tor1-reticulum"
    error_message = "Droplet name must be <layer>-<region>-transport."
  }
}

run "resource_key_replaces_the_region_in_the_name_only" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_droplet.edge.name == "edge-tor1-b-reticulum" && digitalocean_droplet.edge.region == "tor1" && digitalocean_reserved_ip.edge.region == "tor1"
    error_message = "resource_key names the droplet; the region argument stays the real region."
  }
}

run "the_droplet_has_no_admin_path_and_no_public_v6" {
  command = plan
  assert {
    condition     = digitalocean_droplet.edge.ipv6 == false && digitalocean_droplet.edge.backups == false && digitalocean_droplet.edge.monitoring == true
    error_message = "ipv6 and backups stay off; monitoring stays on."
  }
  assert {
    condition     = length(coalesce(digitalocean_droplet.edge.ssh_keys, [])) == 0
    error_message = "The edge droplet must have no SSH key."
  }
  assert {
    condition     = digitalocean_droplet.edge.image == "ubuntu-24-04-x64" && digitalocean_droplet.edge.size == "s-1vcpu-1gb"
    error_message = "Image and size must be as declared."
  }
}

run "the_reserved_ip_is_assigned_to_the_droplet" {
  command = plan
  assert {
    condition     = digitalocean_reserved_ip.edge.region == "tor1"
    error_message = "The reserved IP must be created in the droplet's region."
  }
}

run "no_ports_means_no_accept_rules_and_a_default_drop_table" {
  command = plan
  assert {
    condition     = length(output.host_firewall_rules) == 0
    error_message = "With no ports there are no accept descriptors."
  }
  assert {
    condition     = strcontains(digitalocean_droplet.edge.user_data, "policy drop;") && !strcontains(digitalocean_droplet.edge.user_data, "tcp dport")
    error_message = "The host firewall must default to drop, with no port accepted."
  }
}

run "public_and_restricted_ports_render_into_the_host_firewall" {
  command = plan
  variables {
    public_ports = [
      { protocol = "tcp", port_range = "4242" },
      { protocol = "tcp", port_range = "8883" },
    ]
    restricted_ports = [
      { protocol = "tcp", port_range = "5201", sources = ["192.0.2.10/32", "198.51.100.0/24"] },
    ]
  }
  assert {
    condition     = join(",", nonsensitive(output.host_firewall_rules)) == "tcp/4242/any,tcp/5201/restricted,tcp/8883/any"
    error_message = "The descriptors must list every open port once."
  }
  assert {
    condition     = strcontains(nonsensitive(digitalocean_droplet.edge.user_data), "tcp dport 4242 accept") && strcontains(nonsensitive(digitalocean_droplet.edge.user_data), "tcp dport 5201 ip saddr { 192.0.2.10/32, 198.51.100.0/24 } accept")
    error_message = "The nftables accepts must match the lists."
  }
}

run "a_restricted_port_with_no_source_is_closed" {
  command = plan
  variables {
    restricted_ports = [
      { protocol = "tcp", port_range = "5201", sources = [] },
    ]
  }
  assert {
    condition     = length(nonsensitive(output.host_firewall_rules)) == 0 && !strcontains(nonsensitive(digitalocean_droplet.edge.user_data), "5201")
    error_message = "A restricted port with no source must render no rule."
  }
}

run "restricted_sources_reject_ipv6" {
  command = plan
  variables {
    restricted_ports = [
      { protocol = "tcp", port_range = "5201", sources = ["2001:db8::/32"] },
    ]
  }
  expect_failures = [var.restricted_ports]
}

run "restricted_sources_reject_the_whole_internet" {
  command = plan
  variables {
    restricted_ports = [
      { protocol = "tcp", port_range = "5201", sources = ["0.0.0.0/0"] },
    ]
  }
  expect_failures = [var.restricted_ports]
}

run "restricted_sources_reject_a_malformed_range" {
  command = plan
  variables {
    restricted_ports = [
      { protocol = "tcp", port_range = "5201", sources = ["not-a-cidr"] },
    ]
  }
  expect_failures = [var.restricted_ports]
}

run "public_ports_reject_a_range_and_an_out_of_range_port" {
  command = plan
  variables {
    public_ports = [{ protocol = "tcp", port_range = "30000-31000" }]
  }
  expect_failures = [var.public_ports]
}

run "public_ports_reject_port_65536" {
  command = plan
  variables {
    public_ports = [{ protocol = "tcp", port_range = "65536" }]
  }
  expect_failures = [var.public_ports]
}

run "public_ports_reject_an_unknown_protocol" {
  command = plan
  variables {
    public_ports = [{ protocol = "icmp", port_range = "1" }]
  }
  expect_failures = [var.public_ports]
}

run "no_service_is_installed" {
  command = plan
  assert {
    condition     = !strcontains(digitalocean_droplet.edge.user_data, "mosquitto") && !strcontains(digitalocean_droplet.edge.user_data, "iperf3") && !strcontains(digitalocean_droplet.edge.user_data, "i2pd") && !strcontains(digitalocean_droplet.edge.user_data, "lxmd") && !strcontains(digitalocean_droplet.edge.user_data, "rnsd")
    error_message = "The module installs no service; each service is its own stack."
  }
}

run "the_user_data_has_no_ssh_path" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.edge.user_data, "mask, ssh.service, ssh.socket") && strcontains(digitalocean_droplet.edge.user_data, "passwd, -l, root") && !strcontains(digitalocean_droplet.edge.user_data, "ssh_authorized_keys") && !strcontains(digitalocean_droplet.edge.user_data, "dport 22")
    error_message = "sshd must be masked, root locked, and no key or port 22 rule present."
  }
}

run "the_reboot_time_defaults_to_the_services_slot_in_eastern" {
  command = plan
  assert {
    condition     = output.reboot_time == "01:00" && strcontains(digitalocean_droplet.edge.user_data, "Automatic-Reboot-Time \"01:00\"") && strcontains(digitalocean_droplet.edge.user_data, "timezone: America/New_York")
    error_message = "reticulum reboots in its 01:00 Eastern slot by default."
  }
}

run "each_service_has_its_own_slot" {
  command = plan
  variables {
    service = "iperf3"
  }
  assert {
    condition     = output.reboot_time == "03:00" && output.doppler_config == "cah-edge-iperf3" && digitalocean_droplet.edge.name == "edge-tor1-iperf3"
    error_message = "iperf3 takes the 03:00 slot, its own Doppler config and its own droplet name."
  }
}

run "an_explicit_reboot_time_overrides_the_slot" {
  command = plan
  variables {
    reboot_time = "03:15"
  }
  assert {
    condition     = strcontains(digitalocean_droplet.edge.user_data, "Automatic-Reboot-Time \"03:15\"")
    error_message = "reboot_time must reach unattended-upgrades."
  }
}

run "an_unknown_service_is_refused" {
  command = plan
  variables {
    service = "web"
  }
  expect_failures = [var.service]
}

run "the_droplet_and_reserved_ip_join_the_existing_project" {
  command = plan
  assert {
    condition     = digitalocean_project_resources.edge.project == "00000000-0000-0000-0000-000000000001" && length(digitalocean_project_resources.edge.resources) == 2
    error_message = "Both the droplet and the reserved IP must be attached to the project."
  }
}

run "reboot_time_rejects_a_bad_value" {
  command = plan
  variables {
    reboot_time = "25:00"
  }
  expect_failures = [var.reboot_time]
}

run "timezone_rejects_a_bad_value" {
  command = plan
  variables {
    timezone = "not a zone"
  }
  expect_failures = [var.timezone]
}

run "resource_key_rejects_uppercase" {
  command = plan
  variables {
    resource_key = "Tor1"
  }
  expect_failures = [var.resource_key]
}
