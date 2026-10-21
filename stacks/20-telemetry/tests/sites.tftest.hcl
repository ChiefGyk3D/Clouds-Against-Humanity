mock_provider "twingate" {}

# Two sites: the default one (the top-level values) and one entry in `sites`.
# Documentation and private ranges only.
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

# --- the default single site is untouched -------------------------------------

run "no_sites_plans_no_site_objects_with_flags_on" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
  }

  assert {
    condition     = length(twingate_service_account.site_logging) == 0 && length(twingate_service_account.site_scrape) == 0 && length(twingate_resource.site_logging) == 0 && length(twingate_resource.site_scrape) == 0
    error_message = "With sites empty no additional-site object may be planned."
  }
  assert {
    condition     = length(twingate_service_account.logging) == 1 && length(twingate_service_account.scrape) == 1 && length(twingate_resource.logging) == 2 && length(twingate_resource.scrape) == 4
    error_message = "The single-site objects (addresses and count) must not change when sites is empty."
  }
  assert {
    condition     = output.extra_site_identities == {} && length(output.scrape_targets) == 4
    error_message = "sites empty must add nothing to the outputs."
  }
}

run "sites_with_flags_off_plans_nothing" {
  command = plan

  variables {
    sites = { tor2 = { cloud_remote_network_id = "cloud-two", connector_private_ips = { a = "10.98.0.5" } } }
  }

  assert {
    condition     = length(twingate_service_account.site_logging) == 0 && length(twingate_service_account.site_scrape) == 0 && length(twingate_resource.site_logging) == 0 && length(twingate_resource.site_scrape) == 0 && length(twingate_service_account.logging) == 0
    error_message = "Listing a site must create nothing until a flag is true."
  }
}

# --- two sites ------------------------------------------------------------------

run "two_sites_get_one_logging_and_one_scrape_service_each" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
    sites = {
      tor2 = {
        site_name               = "site-second"
        cloud_remote_network_id = "cloud-two"
        connector_private_ips   = { a = "10.98.0.5", b = "10.98.0.6" }
      }
    }
  }

  assert {
    condition     = twingate_service_account.logging[0].name == "telemetry-tor1-logging" && twingate_service_account.scrape[0].name == "telemetry-tor1-scrape"
    error_message = "The default site's services must keep their names."
  }
  assert {
    condition     = twingate_service_account.site_logging["tor2"].name == "telemetry-tor2-logging" && twingate_service_account.site_scrape["tor2"].name == "telemetry-tor2-scrape"
    error_message = "Each additional site needs its own logging and scrape service, named from its key."
  }
  assert {
    condition     = length(twingate_service_account.logging) + length(twingate_service_account.scrape) + length(twingate_service_account.site_logging) + length(twingate_service_account.site_scrape) == 4
    error_message = "Two sites need two services each: four in all, none shared."
  }
  assert {
    condition     = toset(keys(twingate_resource.site_logging)) == toset(["tor2:siem-home-agent", "tor2:siem-home-syslog"]) && twingate_resource.site_logging["tor2:siem-home-agent"].name == "logging-tor2-siem-home-agent"
    error_message = "Each site gets its own logging resource per server."
  }
  assert {
    condition     = toset(keys(twingate_resource.site_scrape)) == toset(["tor2:node-a", "tor2:node-b", "tor2:connector-a", "tor2:connector-b"]) && twingate_resource.site_scrape["tor2:node-b"].name == "scrape-tor2-node-b"
    error_message = "Each site gets its own scrape resource per endpoint per connector."
  }
  assert {
    condition     = twingate_resource.site_scrape["tor2:node-a"].remote_network_id == "cloud-two" && twingate_resource.site_scrape["tor2:node-b"].address == "10.98.0.6" && twingate_resource.scrape["node-a"].remote_network_id == "cloud-network-id"
    error_message = "A site's scrape resources must use that site's own network and addresses."
  }
  assert {
    condition     = twingate_resource.site_logging["tor2:siem-home-agent"].remote_network_id == "home-network-id"
    error_message = "Logging resources belong in the home remote network."
  }
  assert {
    condition     = length(regexall("second", jsonencode([for r in concat(values(twingate_resource.site_logging), values(twingate_resource.site_scrape)) : r.name]))) == 0
    error_message = "site_name must appear in no resource name."
  }
}

run "each_site_carries_its_own_site_name_label" {
  command = plan

  variables {
    metrics_enabled = true
    sites = {
      tor2 = {
        site_name               = "site-second"
        cloud_remote_network_id = "cloud-two"
        connector_private_ips   = { a = "10.98.0.5" }
      }
      nyc3 = {
        region                  = "nyc3"
        cloud_remote_network_id = "cloud-three"
        connector_private_ips   = { b = "10.97.0.6" }
      }
    }
  }

  assert {
    condition     = output.scrape_targets["tor2:node-a"] == { site = "site-second", instance = "site-second-connector-a", address = "10.98.0.5", port = 9100, role = "connector" }
    error_message = "A site's scrape targets must carry its site_name label."
  }
  assert {
    condition     = output.scrape_targets["nyc3:node-b"].site == "site-nyc3" && output.scrape_targets["node-a"].site == "site-tor1"
    error_message = "An empty site_name must mean site-<key>, and the default site's label must not change."
  }
  assert {
    condition     = output.extra_site_identities == { tor2 = { site = "site-second", region = "tor1" }, nyc3 = { site = "site-nyc3", region = "nyc3" } }
    error_message = "extra_site_identities must list each site's label and region."
  }
  assert {
    condition     = length(output.scrape_targets) == 4 + 2 + 2
    error_message = "scrape_targets must hold the default site plus one entry per endpoint per connector of each site."
  }
  assert {
    condition     = length(twingate_service_account.site_scrape) == 2 && length(twingate_service_account.site_logging) == 0
    error_message = "Metrics only: one scrape service per site, no logging service."
  }
}

# --- refusals -------------------------------------------------------------------

run "a_site_key_equal_to_the_resource_key_is_refused" {
  command = plan
  variables {
    metrics_enabled = true
    sites           = { tor1 = { cloud_remote_network_id = "x", connector_private_ips = { a = "10.98.0.5" } } }
  }
  expect_failures = [twingate_service_account.site_scrape]
}

run "a_site_without_its_own_network_is_refused" {
  command = plan
  variables {
    metrics_enabled = true
    sites           = { tor2 = { connector_private_ips = { a = "10.98.0.5" } } }
  }
  expect_failures = [twingate_service_account.site_scrape]
}

run "a_site_without_connector_addresses_is_refused" {
  command = plan
  variables {
    metrics_enabled = true
    sites           = { tor2 = { cloud_remote_network_id = "cloud-two" } }
  }
  expect_failures = [twingate_service_account.site_scrape]
}

run "a_site_key_must_be_well_formed" {
  command = plan
  variables {
    sites = { "Bad_Key" = {} }
  }
  expect_failures = [var.sites]
}

run "a_site_connector_address_must_be_private" {
  command = plan
  variables {
    sites = { tor2 = { connector_private_ips = { a = "8.8.8.8" } } }
  }
  expect_failures = [var.sites]
}

run "a_site_connector_key_must_be_a_or_b" {
  command = plan
  variables {
    sites = { tor2 = { connector_private_ips = { c = "10.98.0.5" } } }
  }
  expect_failures = [var.sites]
}

# --- the golden addresses (docs/golden-addresses/20-telemetry.json) ------------

run "default_single_site_addresses_are_the_golden_ones" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
    sites           = {}
  }

  assert {
    condition     = toset(keys(twingate_resource.logging)) == toset(["siem-home-agent", "siem-home-syslog"]) && toset(keys(twingate_resource.scrape)) == toset(["node-a", "node-b", "connector-a", "connector-b"])
    error_message = "The single-site resource keys must equal the golden addresses."
  }
  assert {
    condition     = twingate_service_account.logging[0].name == "telemetry-tor1-logging" && twingate_service_account.scrape[0].name == "telemetry-tor1-scrape" && twingate_resource.logging["siem-home-agent"].name == "logging-tor1-siem-home-agent" && twingate_resource.scrape["connector-b"].name == "scrape-tor1-connector-b"
    error_message = "The single-site names must equal the golden names."
  }
}

run "adding_a_site_leaves_the_default_site_addresses_unchanged" {
  command = plan

  variables {
    logging_enabled = true
    metrics_enabled = true
    sites           = { tor2 = { cloud_remote_network_id = "cloud-two", connector_private_ips = { a = "10.98.0.5", b = "10.98.0.6" } } }
  }

  assert {
    condition     = toset(keys(twingate_resource.logging)) == toset(["siem-home-agent", "siem-home-syslog"]) && toset(keys(twingate_resource.scrape)) == toset(["node-a", "node-b", "connector-a", "connector-b"]) && length(twingate_service_account.logging) == 1 && length(twingate_service_account.scrape) == 1
    error_message = "A second site must not change the first site's addresses or count."
  }
}
