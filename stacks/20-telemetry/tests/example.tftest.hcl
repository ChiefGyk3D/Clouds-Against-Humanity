# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "twingate" {}

variables {
  # Example values for stacks/20-telemetry. Copy this file to terraform.tfvars
  # (which git ignores) for a local plan. Never put a token or key in a value file:
  # those live in Doppler. Every value here is a placeholder. The feature flags
  # are false here on purpose: this stack creates nothing until both a flag is
  # true and the Twingate plan has been checked (docs/stages/02-telemetry.md).

  # DigitalOcean region slug of the site, from the foundation stack's region output.
  region = "tor1"

  # Used in the NAMES of the Twingate objects. Empty means region. IMMUTABLE for the
  # life of a stack: changing it renames, and so replaces, every object. Use the
  # same value as the site's foundation and access stacks.
  resource_key = ""

  # A label for telemetry only (empty means "site-<region>"). It appears in no
  # resource name or tag, and changing it replaces nothing.
  site_name = "site-tor1"

  # Create the logging service and one Twingate resource per logging_servers element.
  logging_enabled = false

  # Create the scrape service and one Twingate resource per scrape_allowlist entry
  # per connector.
  metrics_enabled = false

  # The home logging endpoints, reached only through Twingate. Private: the real
  # list comes from the site's Doppler config, not this file. The validation accepts
  # a documentation range on purpose so this example is valid; 192.0.2.0/24 is one.
  logging_servers = [
    { name = "siem-home-agent", address = "192.0.2.10", port = 1514, protocol = "tcp", purpose = "wazuh-agent" },
    { name = "siem-home-enroll", address = "192.0.2.10", port = 1515, protocol = "tcp", purpose = "wazuh-enroll" },
  ]

  # Id of the Twingate remote network that holds the home logging connector. Private:
  # the real one comes from your secret store. Required when logging_enabled.
  home_remote_network_id = "example-home-remote-network-id"

  # Id of this site's cloud remote network (access-<resource_key>, made by stack 10).
  # Required when metrics_enabled.
  cloud_remote_network_id = "example-cloud-remote-network-id"

  # TCP port of the node exporter on each connector.
  node_exporter_port = 9100

  # TCP port of the connector's own metrics endpoint. Illustrative only: the real
  # bind port is unverified and has no default. Test it on one connector first.
  metrics_port_connector = 9101

  # Which connector endpoints become Twingate resources for scraping. Each port must
  # be one of the two ports above.
  scrape_allowlist = [
    { name = "node", host_role = "connector", port = 9100 },
  ]

  # The access stack's connector_private_ips output (keys a and b). Private, so
  # empty here; it arrives from the stack dependency or by hand.
  connector_private_ips = {}

  # Wazuh agent group for this site's cloud hosts (telemetry label only).
  wazuh_agent_group = "cloud-site-tor1"

  # Extra telemetry labels. Only env, role and owner_team are allowed.
  labels = { env = "example" }
}

run "the_example_values_are_valid" {
  command = plan
}
