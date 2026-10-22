# SPDX-License-Identifier: Apache-2.0
# The edge ships DISABLED. These tests plan with mocked providers only.
#
# Turning the edge on is refused while cost.json prices nothing, by a
# precondition on output.edge_enabled. The runs below that look at the ENABLED
# shape therefore expect that one failure and still assert on the planned
# resources: the plan is evaluated, it is just never allowed to apply.

mock_provider "digitalocean" {
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

# --- disabled by default -----------------------------------------------------

run "the_edge_is_off_by_default_and_creates_nothing" {
  command = plan
  assert {
    condition     = var.edge_enabled == false
    error_message = "edge_enabled must default to false."
  }
  assert {
    condition     = length(digitalocean_vpc.dmz) == 0 && length(digitalocean_tag.dmz) == 0 && length(digitalocean_tag.transport) == 0 && length(digitalocean_firewall.dmz) == 0 && length(module.edge_host) == 0
    error_message = "With the switch off no VPC, tag, firewall or droplet module may exist."
  }
  assert {
    condition     = output.vpc_id == null && output.reserved_ip == null && output.edge_enabled == false
    error_message = "With the switch off the outputs are null."
  }
}

run "the_cost_manifest_prices_nothing_while_the_stage_is_unapproved" {
  command = plan
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 0
    error_message = "cost.json must stay empty until the stage is approved: the edge is not in the approved total."
  }
}

# --- the switch is guarded -----------------------------------------------------

run "turning_the_edge_on_is_refused_while_cost_json_is_empty" {
  command = plan
  variables {
    edge_enabled = true
  }
  expect_failures = [output.edge_enabled]
}

# --- the enabled shape (plan is evaluated, apply is refused above) ------------

run "enabled_plan_names_and_isolation" {
  command = plan
  variables {
    edge_enabled = true
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = digitalocean_vpc.dmz[0].name == "rns-dmz" && digitalocean_vpc.dmz[0].ip_range == "10.30.0.0/24" && digitalocean_vpc.dmz[0].region == "tor1"
    error_message = "The VPC must be rns-dmz, 10.30.0.0/24, in the core region."
  }
  assert {
    condition     = digitalocean_tag.dmz[0].name == "rns-dmz" && digitalocean_tag.transport[0].name == "rns-dmz-transport"
    error_message = "The tags must be rns-dmz and rns-dmz-transport."
  }
  assert {
    condition     = digitalocean_firewall.dmz[0].name == "edge-tor1-dmz" && contains(digitalocean_firewall.dmz[0].tags, "rns-dmz")
    error_message = "The firewall must attach to the rns-dmz tag."
  }
  assert {
    condition     = module.edge_host[0].name == "edge-tor1-transport"
    error_message = "The droplet name changed."
  }
  assert {
    condition     = length([for r in digitalocean_firewall.dmz[0].inbound_rule : r if r.port_range == "22"]) == 0
    error_message = "There must be no SSH rule."
  }
}

run "enabled_with_defaults_opens_reticulum_and_mqtt_only" {
  command = plan
  variables {
    edge_enabled           = true
    iperf3_allowed_sources = []
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = join(",", sort([for r in digitalocean_firewall.dmz[0].inbound_rule : "${r.protocol}/${r.port_range}"])) == "tcp/4242,tcp/8883"
    error_message = "By default only the Reticulum and MQTT TLS ports are open: iperf3 has no source and i2pd has no port."
  }
  assert {
    condition     = join(",", nonsensitive(module.edge_host[0].host_firewall_rules)) == "tcp/4242/any,tcp/8883/any"
    error_message = "The host firewall must mirror the Cloud Firewall."
  }
}

run "iperf3_opens_only_for_the_named_sources" {
  command = plan
  variables {
    edge_enabled           = true
    iperf3_allowed_sources = ["203.0.113.10/32"]
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = length([for r in digitalocean_firewall.dmz[0].inbound_rule : r if r.port_range == "5201"]) == 1
    error_message = "iperf3 must have exactly one rule once a source is given."
  }
  assert {
    condition     = length([for r in digitalocean_firewall.dmz[0].inbound_rule : r if r.port_range == "5201" && contains(nonsensitive(r.source_addresses), "0.0.0.0/0")]) == 0
    error_message = "The iperf3 rule must never name the whole internet."
  }
  assert {
    condition     = join(",", nonsensitive(module.edge_host[0].host_firewall_rules)) == "tcp/4242/any,tcp/5201/restricted,tcp/8883/any"
    error_message = "The host firewall must mirror the Cloud Firewall, iperf3 included."
  }
}

run "the_i2pd_port_opens_tcp_and_udp_together" {
  command = plan
  variables {
    edge_enabled = true
    i2pd_port    = 24680
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = join(",", sort([for r in digitalocean_firewall.dmz[0].inbound_rule : "${r.protocol}/${r.port_range}"])) == "tcp/24680,tcp/4242,tcp/8883,udp/24680"
    error_message = "i2pd needs the same port on tcp and udp."
  }
}

run "outbound_is_not_all_ports" {
  command = plan
  variables {
    edge_enabled = true
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = join(",", sort([for r in digitalocean_firewall.dmz[0].outbound_rule : "${r.protocol}/${r.port_range}"])) == "tcp/443,tcp/53,tcp/80,udp/123,udp/53"
    error_message = "Outbound is DNS, apt mirrors and time only until a built service needs more."
  }
}

run "every_public_inbound_rule_is_ipv4_only" {
  command = plan
  variables {
    edge_enabled = true
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = alltrue([for r in digitalocean_firewall.dmz[0].inbound_rule : !contains(nonsensitive(r.source_addresses), "::/0")])
    error_message = "No inbound rule may open IPv6."
  }
}

# --- ranges ------------------------------------------------------------------

run "an_edge_range_equal_to_core_is_refused" {
  command = plan
  variables {
    vpc_ip_range = "10.78.0.0/24"
  }
  expect_failures = [output.edge_enabled]
}

run "an_edge_range_inside_core_is_refused" {
  command = plan
  variables {
    vpc_ip_range      = "10.78.0.128/25"
    core_vpc_ip_range = "10.78.0.0/24"
  }
  expect_failures = [output.edge_enabled]
}

run "an_edge_range_around_core_is_refused" {
  command = plan
  variables {
    vpc_ip_range      = "10.78.0.0/16"
    core_vpc_ip_range = "10.78.4.0/24"
  }
  expect_failures = [output.edge_enabled]
}

run "an_edge_range_overlapping_a_reserved_range_is_refused" {
  command = plan
  variables {
    reserved_ranges = ["10.30.0.64/26"]
  }
  expect_failures = [output.edge_enabled]
}

run "an_adjacent_range_is_fine" {
  command = plan
  variables {
    vpc_ip_range      = "10.78.1.0/24"
    core_vpc_ip_range = "10.78.0.0/24"
  }
  assert {
    condition     = output.edge_enabled == false
    error_message = "A range that starts right after core does not overlap it."
  }
}

run "vpc_range_rejects_a_public_range" {
  command = plan
  variables {
    vpc_ip_range = "8.8.8.0/24"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_host_address" {
  command = plan
  variables {
    vpc_ip_range = "10.30.0.5/24"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_slash_29" {
  command = plan
  variables {
    vpc_ip_range = "10.30.0.0/29"
  }
  expect_failures = [var.vpc_ip_range]
}

run "reserved_ranges_must_be_cidrs" {
  command = plan
  variables {
    reserved_ranges = ["nonsense"]
  }
  expect_failures = [var.reserved_ranges]
}

# --- ports and sources ---------------------------------------------------------

run "i2pd_and_reticulum_cannot_share_a_port" {
  command = plan
  variables {
    i2pd_port = 4242
  }
  expect_failures = [output.edge_enabled]
}

run "reticulum_port_rejects_zero_and_65536" {
  command = plan
  variables {
    reticulum_port = 0
  }
  expect_failures = [var.reticulum_port]
}

run "reticulum_port_rejects_a_fraction" {
  command = plan
  variables {
    reticulum_port = 4242.5
  }
  expect_failures = [var.reticulum_port]
}

run "i2pd_port_rejects_65536" {
  command = plan
  variables {
    i2pd_port = 65536
  }
  expect_failures = [var.i2pd_port]
}

run "iperf3_sources_reject_the_whole_internet" {
  command = plan
  variables {
    iperf3_allowed_sources = ["0.0.0.0/0"]
  }
  expect_failures = [var.iperf3_allowed_sources]
}

run "iperf3_sources_reject_ipv6" {
  command = plan
  variables {
    iperf3_allowed_sources = ["2001:db8::/32"]
  }
  expect_failures = [var.iperf3_allowed_sources]
}

run "iperf3_sources_reject_a_malformed_range" {
  command = plan
  variables {
    iperf3_allowed_sources = ["nonsense"]
  }
  expect_failures = [var.iperf3_allowed_sources]
}

# --- names ---------------------------------------------------------------------

run "resource_key_names_the_firewall_and_droplet_not_the_vpc_or_tags" {
  command = plan
  variables {
    edge_enabled = true
    resource_key = "tor1-b"
  }
  expect_failures = [output.edge_enabled]
  assert {
    condition     = digitalocean_firewall.dmz[0].name == "edge-tor1-b-dmz" && module.edge_host[0].name == "edge-tor1-b-transport"
    error_message = "resource_key must name the firewall and droplet."
  }
  assert {
    condition     = digitalocean_vpc.dmz[0].name == "rns-dmz" && digitalocean_tag.dmz[0].name == "rns-dmz" && digitalocean_vpc.dmz[0].region == "tor1"
    error_message = "The VPC and tags keep their fixed design names, and the region stays the real region."
  }
}

run "resource_key_rejects_uppercase" {
  command = plan
  variables {
    resource_key = "Tor1"
  }
  expect_failures = [var.resource_key]
}

run "region_rejects_a_city_name" {
  command = plan
  variables {
    region = "toronto"
  }
  expect_failures = [var.region]
}

run "reboot_time_rejects_a_bad_value" {
  command = plan
  variables {
    reboot_time = "5am"
  }
  expect_failures = [var.reboot_time]
}
