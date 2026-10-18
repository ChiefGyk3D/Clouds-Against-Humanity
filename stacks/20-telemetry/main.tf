locals {
  # Names use resource_key when it is set and region otherwise, as in stacks 00
  # and 10. site_name never reaches this file: it is a telemetry label (site.tf).
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  # Every object below is gated on its flag, so with both flags false this stack
  # plans zero resources. The logging names are not private (they are validated
  # not to be an address), so they may key a for_each; the servers themselves
  # stay sensitive and are only looked up by name.
  logging_names   = var.logging_enabled ? toset(nonsensitive([for s in var.logging_servers : s.name])) : toset([])
  logging_by_name = { for s in var.logging_servers : s.name => s }

  # One scrape resource per allowlisted endpoint per connector. The connector
  # keys (a, b) are not private; the addresses stay sensitive.
  connector_keys = var.metrics_enabled ? nonsensitive(keys(var.connector_private_ips)) : []
  scrape_pairs = {
    for p in setproduct(var.scrape_allowlist, local.connector_keys) :
    "${p[0].name}-${p[1]}" => {
      port     = p[0].port
      instance = p[1]
    }
  }
}

# One Twingate service per site per role, each granted only that role's
# resources (design section 3.4). The service keys are NOT created here: they
# are issued out of band, one per host, so no key is ever in state.
resource "twingate_service_account" "logging" {
  count = var.logging_enabled ? 1 : 0
  name  = "telemetry-${local.resource_key}-logging"

  lifecycle {
    precondition {
      condition     = var.home_remote_network_id != "" && length(var.logging_servers) > 0
      error_message = "logging_enabled needs home_remote_network_id and at least one logging_servers element."
    }
  }
}

resource "twingate_service_account" "scrape" {
  count = var.metrics_enabled ? 1 : 0
  name  = "telemetry-${local.resource_key}-scrape"

  lifecycle {
    precondition {
      condition     = var.cloud_remote_network_id != "" && length(var.scrape_allowlist) > 0 && length(var.connector_private_ips) > 0
      error_message = "metrics_enabled needs cloud_remote_network_id, a non-empty scrape_allowlist and connector_private_ips."
    }
    precondition {
      condition     = var.metrics_port_connector != null
      error_message = "metrics_enabled needs metrics_port_connector. It has no default because the connector's metrics port is unverified."
    }
    precondition {
      condition     = var.metrics_port_connector != var.node_exporter_port
      error_message = "metrics_port_connector must differ from node_exporter_port."
    }
    precondition {
      condition     = var.metrics_port_connector != 9100
      error_message = "metrics_port_connector must not be 9100: the access stack keeps 9100 for the node exporter and refuses it as connector_telemetry.metrics_port."
    }
    precondition {
      condition     = alltrue([for s in var.scrape_allowlist : contains(compact([tostring(var.node_exporter_port), var.metrics_port_connector == null ? "" : tostring(var.metrics_port_connector)]), tostring(s.port))])
      error_message = "Every scrape_allowlist port must be node_exporter_port or metrics_port_connector."
    }
  }
}

# One resource per logging endpoint and port, in the home remote network, named
# from the validated name and never from the address.
resource "twingate_resource" "logging" {
  for_each          = local.logging_names
  name              = "logging-${local.resource_key}-${each.key}"
  address           = local.logging_by_name[each.key].address
  remote_network_id = var.home_remote_network_id

  protocols = {
    allow_icmp = false
    tcp = {
      policy = local.logging_by_name[each.key].protocol == "tcp" ? "RESTRICTED" : "DENY_ALL"
      ports  = local.logging_by_name[each.key].protocol == "tcp" ? [tostring(local.logging_by_name[each.key].port)] : []
    }
    udp = {
      policy = local.logging_by_name[each.key].protocol == "udp" ? "RESTRICTED" : "DENY_ALL"
      ports  = local.logging_by_name[each.key].protocol == "udp" ? [tostring(local.logging_by_name[each.key].port)] : []
    }
  }

  access_service {
    service_account_id = twingate_service_account.logging[0].id
  }
}

# One resource per allowlisted endpoint per connector, in this site's cloud
# remote network, granted only to the scrape service.
resource "twingate_resource" "scrape" {
  for_each          = local.scrape_pairs
  name              = "scrape-${local.resource_key}-${each.key}"
  address           = var.connector_private_ips[each.value.instance]
  remote_network_id = var.cloud_remote_network_id

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = [tostring(each.value.port)]
    }
    udp = {
      policy = "DENY_ALL"
      ports  = []
    }
  }

  access_service {
    service_account_id = twingate_service_account.scrape[0].id
  }
}
