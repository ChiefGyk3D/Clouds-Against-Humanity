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

  # Additional sites (var.sites). Empty unless a flag is true AND a site is
  # listed, so the single-site plan is unchanged. Keys join the site key and the
  # logging server name or scrape pair with a colon, which neither may contain.
  extra_keys    = toset(nonsensitive(keys(var.sites)))
  extra_logging = var.logging_enabled ? local.extra_keys : toset([])
  extra_scrape  = var.metrics_enabled ? local.extra_keys : toset([])

  extra_logging_pairs = {
    for p in setproduct(tolist(local.extra_logging), tolist(local.logging_names)) :
    "${p[0]}:${p[1]}" => { skey = p[0], server = p[1] }
  }

  extra_scrape_pairs = merge([
    for sk in local.extra_scrape : {
      for p in setproduct(var.scrape_allowlist, nonsensitive(keys(var.sites[sk].connector_private_ips))) :
      "${sk}:${p[0].name}-${p[1]}" => {
        skey     = sk
        port     = p[0].port
        instance = p[1]
      }
    }
  ]...)
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

# --- additional sites (var.sites): one service per site per role --------------
# Separate addresses from the single-site resources above, so the default plan
# is unchanged (docs/golden-addresses/20-telemetry.json). Each site's services
# are its own: a stolen key reaches only that site's resources. Keys are issued
# out of band, one per host, as for the first site.
resource "twingate_service_account" "site_logging" {
  for_each = local.extra_logging
  name     = "telemetry-${each.key}-logging"

  lifecycle {
    precondition {
      condition     = each.key != local.resource_key
      error_message = "A sites key must differ from this stack's own resource_key (the default site)."
    }
    precondition {
      condition     = var.home_remote_network_id != "" && length(var.logging_servers) > 0
      error_message = "logging_enabled needs home_remote_network_id and at least one logging_servers element."
    }
  }
}

resource "twingate_service_account" "site_scrape" {
  for_each = local.extra_scrape
  name     = "telemetry-${each.key}-scrape"

  lifecycle {
    precondition {
      condition     = each.key != local.resource_key
      error_message = "A sites key must differ from this stack's own resource_key (the default site)."
    }
    precondition {
      condition     = var.sites[each.key].cloud_remote_network_id != "" && length(var.sites[each.key].connector_private_ips) > 0 && length(var.scrape_allowlist) > 0
      error_message = "metrics_enabled needs, for every sites entry, its own cloud_remote_network_id, connector_private_ips and a non-empty scrape_allowlist."
    }
    precondition {
      condition     = var.metrics_port_connector != null
      error_message = "metrics_enabled needs metrics_port_connector. It has no default because the connector's metrics port is unverified."
    }
  }
}

resource "twingate_resource" "site_logging" {
  for_each          = local.extra_logging_pairs
  name              = "logging-${each.value.skey}-${each.value.server}"
  address           = local.logging_by_name[each.value.server].address
  remote_network_id = var.home_remote_network_id

  protocols = {
    allow_icmp = false
    tcp = {
      policy = local.logging_by_name[each.value.server].protocol == "tcp" ? "RESTRICTED" : "DENY_ALL"
      ports  = local.logging_by_name[each.value.server].protocol == "tcp" ? [tostring(local.logging_by_name[each.value.server].port)] : []
    }
    udp = {
      policy = local.logging_by_name[each.value.server].protocol == "udp" ? "RESTRICTED" : "DENY_ALL"
      ports  = local.logging_by_name[each.value.server].protocol == "udp" ? [tostring(local.logging_by_name[each.value.server].port)] : []
    }
  }

  access_service {
    service_account_id = twingate_service_account.site_logging[each.value.skey].id
  }
}

resource "twingate_resource" "site_scrape" {
  for_each          = local.extra_scrape_pairs
  name              = "scrape-${replace(each.key, ":", "-")}"
  address           = var.sites[each.value.skey].connector_private_ips[each.value.instance]
  remote_network_id = var.sites[each.value.skey].cloud_remote_network_id

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
    service_account_id = twingate_service_account.site_scrape[each.value.skey].id
  }
}
