mock_provider "twingate" {}

# Fixture values are documentation and private ranges only. The logging address
# 192.0.2.10 stands for a private home address: no name, tag or output may hold it.
variables {
  region = "tor1"
  logging_servers = [
    { name = "siem-home-agent", address = "192.0.2.10", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    { name = "siem-home-syslog", address = "192.0.2.10", port = 514, protocol = "udp", purpose = "syslog" },
  ]
  home_remote_network_id  = "home-network-id"
  cloud_remote_network_id = "cloud-network-id"
  metrics_port_connector  = 9101
  scrape_allowlist = [
    { name = "node", host_role = "connector", port = 9100 },
    { name = "connector", host_role = "connector", port = 9101 },
  ]
  connector_private_ips = { a = "10.99.0.5", b = "10.99.0.6" }
}

# --- everything off ----------------------------------------------------------

run "defaults_plan_zero_resources" {
  command = plan

  # Only the one required input: every flag is at its default.
  variables {
    logging_servers         = []
    home_remote_network_id  = ""
    cloud_remote_network_id = ""
    metrics_port_connector  = null
    scrape_allowlist        = []
    connector_private_ips   = {}
  }

  assert {
    condition     = length(twingate_service_account.logging) == 0 && length(twingate_service_account.scrape) == 0
    error_message = "With the default flags no Twingate service may be planned."
  }
  assert {
    condition     = length(twingate_resource.logging) == 0 && length(twingate_resource.scrape) == 0
    error_message = "With the default flags no Twingate resource may be planned."
  }
  assert {
    condition     = output.scrape_targets == {}
    error_message = "scrape_targets must be empty when metrics are off."
  }
}

run "flags_false_plan_zero_resources_even_with_every_input_set" {
  command = plan

  variables {
    logging_enabled = false
    metrics_enabled = false
  }

  assert {
    condition     = length(twingate_service_account.logging) == 0 && length(twingate_service_account.scrape) == 0 && length(twingate_resource.logging) == 0 && length(twingate_resource.scrape) == 0
    error_message = "Inputs alone must create nothing: only a true flag creates objects."
  }
  assert {
    condition     = output.scrape_targets == {}
    error_message = "scrape_targets must be empty when metrics are off."
  }
}

run "the_feature_flags_default_to_false" {
  command = plan
  assert {
    condition     = var.logging_enabled == false && var.metrics_enabled == false
    error_message = "Every feature flag must default to false."
  }
}

# --- logging on --------------------------------------------------------------

run "logging_on_plans_one_service_and_one_resource_per_server" {
  command = plan

  variables {
    logging_enabled = true
  }

  assert {
    condition     = length(twingate_service_account.logging) == 1 && length(twingate_service_account.scrape) == 0
    error_message = "Logging on must plan the logging service and no scrape service."
  }
  assert {
    condition     = length(twingate_resource.logging) == 2 && length(twingate_resource.scrape) == 0
    error_message = "Logging on must plan one resource per logging_servers element and no scrape resource."
  }
  assert {
    condition     = twingate_service_account.logging[0].name == "telemetry-tor1-logging"
    error_message = "The logging service must be named from resource_key (region when empty)."
  }
  assert {
    condition     = twingate_resource.logging["siem-home-agent"].name == "logging-tor1-siem-home-agent" && twingate_resource.logging["siem-home-syslog"].name == "logging-tor1-siem-home-syslog"
    error_message = "Logging resources must be named logging-<key>-<server name>."
  }
  assert {
    condition     = twingate_resource.logging["siem-home-agent"].remote_network_id == "home-network-id"
    error_message = "Logging resources belong in the home remote network."
  }
  assert {
    condition     = twingate_resource.logging["siem-home-agent"].protocols.tcp.policy == "RESTRICTED" && twingate_resource.logging["siem-home-agent"].protocols.udp.policy == "DENY_ALL" && twingate_resource.logging["siem-home-syslog"].protocols.udp.policy == "RESTRICTED" && twingate_resource.logging["siem-home-syslog"].protocols.tcp.policy == "DENY_ALL"
    error_message = "Each logging resource must allow only its own protocol."
  }
  assert {
    condition     = output.scrape_targets == {}
    error_message = "Logging alone must leave scrape_targets empty."
  }
}

run "no_name_or_output_holds_the_private_address" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
  }

  assert {
    condition = alltrue([
      for r in concat(values(twingate_resource.logging), values(twingate_resource.scrape)) :
      length(regexall("192[.]0[.]2|10[.]99[.]0", r.name)) == 0
    ])
    error_message = "A resource name must never contain an address."
  }
  assert {
    condition     = length(regexall("192[.]0[.]2", jsonencode(output.site_identity))) == 0 && length(regexall("192[.]0[.]2", jsonencode(output.scrape_targets))) == 0
    error_message = "The private home logging address must appear in no output."
  }
  assert {
    condition     = length(regexall("10[.]99[.]0", jsonencode(output.site_identity))) == 0
    error_message = "The connector addresses may appear only in the sensitive scrape_targets output."
  }
}

# --- metrics on --------------------------------------------------------------

run "metrics_on_plans_one_service_and_a_resource_per_endpoint_per_connector" {
  command = plan

  variables {
    metrics_enabled = true
  }

  assert {
    condition     = length(twingate_service_account.scrape) == 1 && length(twingate_service_account.logging) == 0
    error_message = "Metrics on must plan the scrape service and no logging service."
  }
  assert {
    condition     = length(twingate_resource.scrape) == 4 && length(twingate_resource.logging) == 0
    error_message = "Two endpoints on two connectors must plan four scrape resources."
  }
  assert {
    condition     = twingate_service_account.scrape[0].name == "telemetry-tor1-scrape"
    error_message = "The scrape service must be named from resource_key (region when empty)."
  }
  assert {
    condition     = toset(keys(twingate_resource.scrape)) == toset(["node-a", "node-b", "connector-a", "connector-b"])
    error_message = "Scrape resources must be keyed endpoint-connector."
  }
  assert {
    condition     = twingate_resource.scrape["node-a"].name == "scrape-tor1-node-a" && twingate_resource.scrape["node-a"].remote_network_id == "cloud-network-id"
    error_message = "Scrape resources must be named scrape-<key>-<endpoint>-<connector> and live in the cloud remote network."
  }
  assert {
    condition     = twingate_resource.scrape["connector-b"].address == "10.99.0.6" && twingate_resource.scrape["node-a"].protocols.tcp.ports == toset(["9100"])
    error_message = "Each scrape resource must point at its connector's address and exactly its own port."
  }
  assert {
    condition     = output.scrape_targets["node-a"] == { site = "site-tor1", instance = "site-tor1-connector-a", address = "10.99.0.5", port = 9100, role = "connector" }
    error_message = "scrape_targets must carry site, instance, address, port and role."
  }
  assert {
    condition     = length(output.scrape_targets) == 4
    error_message = "scrape_targets must have one entry per scrape resource."
  }
}

# --- names: resource_key and site_name ---------------------------------------

run "resource_key_names_the_objects_and_site_name_does_not" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
    resource_key    = "tor1-b"
    site_name       = "site-elsewhere"
  }

  assert {
    condition     = twingate_service_account.logging[0].name == "telemetry-tor1-b-logging" && twingate_service_account.scrape[0].name == "telemetry-tor1-b-scrape"
    error_message = "Service names must use resource_key."
  }
  assert {
    condition = alltrue([
      for r in concat(values(twingate_resource.logging), values(twingate_resource.scrape)) :
      length(regexall("elsewhere", r.name)) == 0 && length(regexall("tor1-b", r.name)) == 1
    ])
    error_message = "Resource names must use resource_key and never site_name."
  }
  assert {
    condition     = length(regexall("elsewhere", twingate_service_account.logging[0].name)) == 0 && length(regexall("elsewhere", twingate_service_account.scrape[0].name)) == 0
    error_message = "site_name must appear in no service name."
  }
  assert {
    condition     = output.site_identity.site == "site-elsewhere" && output.scrape_targets["node-a"].site == "site-elsewhere"
    error_message = "site_name must feed the telemetry outputs."
  }
}

run "site_name_defaults_to_site_region" {
  command = plan
  assert {
    condition     = output.site_identity.site == "site-tor1"
    error_message = "An empty site_name must mean site-<region>."
  }
}

# --- preconditions when a flag is on -----------------------------------------

run "logging_without_a_home_network_is_refused" {
  command = plan
  variables {
    logging_enabled        = true
    home_remote_network_id = ""
  }
  expect_failures = [twingate_service_account.logging]
}

run "logging_without_servers_is_refused" {
  command = plan
  variables {
    logging_enabled = true
    logging_servers = []
  }
  expect_failures = [twingate_service_account.logging]
}

run "metrics_without_a_connector_port_is_refused" {
  command = plan
  variables {
    metrics_enabled        = true
    metrics_port_connector = null
  }
  expect_failures = [twingate_service_account.scrape]
}

run "metrics_without_a_cloud_network_is_refused" {
  command = plan
  variables {
    metrics_enabled         = true
    cloud_remote_network_id = ""
  }
  expect_failures = [twingate_service_account.scrape]
}

run "metrics_without_connector_addresses_is_refused" {
  command = plan
  variables {
    metrics_enabled       = true
    connector_private_ips = {}
  }
  expect_failures = [twingate_service_account.scrape]
}

run "metrics_with_an_empty_allowlist_is_refused" {
  command = plan
  variables {
    metrics_enabled  = true
    scrape_allowlist = []
  }
  expect_failures = [twingate_service_account.scrape]
}

run "an_allowlist_port_outside_the_two_metrics_ports_is_refused" {
  command = plan
  variables {
    metrics_enabled  = true
    scrape_allowlist = [{ name = "other", host_role = "connector", port = 9200 }]
  }
  expect_failures = [twingate_service_account.scrape]
}

run "the_two_metrics_ports_must_differ" {
  command = plan
  variables {
    metrics_enabled        = true
    metrics_port_connector = 9100
  }
  expect_failures = [twingate_service_account.scrape]
}

# --- validations -------------------------------------------------------------

run "region_must_be_a_slug" {
  command = plan
  variables {
    region = "Toronto"
  }
  expect_failures = [var.region]
}

run "resource_key_must_be_well_formed" {
  command = plan
  variables {
    resource_key = "Tor_1"
  }
  expect_failures = [var.resource_key]
}

run "site_name_must_be_well_formed" {
  command = plan
  variables {
    site_name = "x"
  }
  expect_failures = [var.site_name]
}

run "logging_server_names_must_be_unique" {
  command = plan
  variables {
    logging_servers = [
      { name = "same", address = "192.0.2.10", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "same", address = "192.0.2.10", port = 1515, protocol = "tcp", purpose = "wazuh-enroll" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "logging_server_names_must_not_be_addresses" {
  command = plan
  variables {
    logging_servers = [
      { name = "192-0-2-10", address = "192.0.2.10", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "a_public_logging_address_is_refused" {
  command = plan
  variables {
    logging_servers = [
      { name = "public", address = "8.8.8.8", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "a_scheme_in_a_logging_address_is_refused" {
  command = plan
  variables {
    logging_servers = [
      { name = "url", address = "https://siem.example.com", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "private_documentation_and_host_name_addresses_are_accepted" {
  command = plan
  variables {
    logging_servers = [
      { name = "rfc1918-a", address = "10.1.2.3", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "rfc1918-b", address = "172.16.5.4", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "rfc1918-c", address = "192.168.1.1", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "doc-two", address = "198.51.100.7", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "doc-three", address = "203.0.113.9", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
      { name = "host", address = "siem.example.com", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    ]
  }
  assert {
    condition     = length(var.logging_servers) == 6
    error_message = "Private, documentation-range and host-name addresses must be accepted."
  }
}

run "a_logging_port_out_of_range_is_refused" {
  command = plan
  variables {
    logging_servers = [
      { name = "bad-port", address = "192.0.2.10", port = 70000, protocol = "tcp", purpose = "wazuh-agent" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "a_logging_protocol_must_be_tcp_or_udp" {
  command = plan
  variables {
    logging_servers = [
      { name = "bad-proto", address = "192.0.2.10", port = 1514, protocol = "icmp", purpose = "wazuh-agent" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "a_logging_purpose_must_be_known" {
  command = plan
  variables {
    logging_servers = [
      { name = "bad-purpose", address = "192.0.2.10", port = 1514, protocol = "tcp", purpose = "other" },
    ]
  }
  expect_failures = [var.logging_servers]
}

run "node_exporter_port_must_be_unprivileged" {
  command = plan
  variables {
    node_exporter_port = 80
  }
  expect_failures = [var.node_exporter_port]
}

run "metrics_port_must_be_unprivileged_when_set" {
  command = plan
  variables {
    metrics_port_connector = 80
  }
  expect_failures = [var.metrics_port_connector]
}

run "scrape_allowlist_names_must_be_unique" {
  command = plan
  variables {
    scrape_allowlist = [
      { name = "node", host_role = "connector", port = 9100 },
      { name = "node", host_role = "connector", port = 9101 },
    ]
  }
  expect_failures = [var.scrape_allowlist]
}

run "scrape_allowlist_host_role_must_be_connector" {
  command = plan
  variables {
    scrape_allowlist = [{ name = "node", host_role = "workload", port = 9100 }]
  }
  expect_failures = [var.scrape_allowlist]
}

run "scrape_allowlist_port_must_be_unprivileged" {
  command = plan
  variables {
    scrape_allowlist = [{ name = "node", host_role = "connector", port = 22 }]
  }
  expect_failures = [var.scrape_allowlist]
}

run "connector_private_ips_keys_are_a_and_b" {
  command = plan
  variables {
    connector_private_ips = { c = "10.99.0.7" }
  }
  expect_failures = [var.connector_private_ips]
}

run "connector_private_ips_must_be_private" {
  command = plan
  variables {
    connector_private_ips = { a = "8.8.8.8" }
  }
  expect_failures = [var.connector_private_ips]
}

run "wazuh_agent_group_must_be_safe" {
  command = plan
  variables {
    wazuh_agent_group = "bad group"
  }
  expect_failures = [var.wazuh_agent_group]
}

run "labels_are_limited_to_the_allow_list" {
  command = plan
  variables {
    labels = { customer = "x" }
  }
  expect_failures = [var.labels]
}

run "label_values_are_short" {
  command = plan
  variables {
    labels = { env = "0123456789012345678901234567890123456789" }
  }
  expect_failures = [var.labels]
}
