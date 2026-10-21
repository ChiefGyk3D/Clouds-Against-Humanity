variable "region" {
  type        = string
  description = "DigitalOcean region slug of the site this stack serves, from the foundation stack's region output. Names are built from resource_key, which defaults to this value."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the NAMES of the Twingate objects this stack creates (telemetry-<key>-logging and so on). Empty means region. Use the same value as the site's foundation and access stacks. IMMUTABLE FOR THE LIFE OF A STACK: changing it renames, and so replaces, every object. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "site_name" {
  type        = string
  default     = ""
  description = "Telemetry label only: the site field of scrape_targets and site_identity. Empty means site-<region>. Appears in no resource name or tag, and changing it replaces nothing. Unique across your sites (a rule for the person; one stack cannot test it)."

  validation {
    condition     = var.site_name == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.site_name))
    error_message = "site_name must be empty (meaning site-<region>) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "logging_enabled" {
  type        = bool
  default     = false
  description = "Create the logging Twingate service and one Twingate resource per element of logging_servers. False creates nothing. Verify the Twingate plan allows the services first (UNVERIFIED; see docs/stages/02-telemetry.md)."
}

variable "metrics_enabled" {
  type        = bool
  default     = false
  description = "Create the scrape Twingate service and one Twingate resource per scrape_allowlist entry per connector. False creates nothing. Needs metrics_port_connector, cloud_remote_network_id and connector_private_ips."
}

variable "logging_servers" {
  type = list(object({
    name     = string
    address  = string
    port     = number
    protocol = string
    purpose  = string
  }))
  default     = []
  sensitive   = true
  description = "Home logging endpoints, reached only through Twingate; one Twingate resource per element, named from name and resource_key, never from the address. PRIVATE: the real list comes from the site's Doppler config (JSON). The address is accepted as a private IPv4 literal (RFC 1918), a documentation-range literal (RFC 5737, so the committed example is valid and not routable) or a host name. The address appears in no name, tag or output."

  validation {
    condition     = length(distinct([for s in var.logging_servers : s.name])) == length(var.logging_servers)
    error_message = "Every logging_servers name must be unique."
  }

  validation {
    condition     = alltrue([for s in var.logging_servers : can(regex("^[a-z][a-z0-9-]{0,40}$", s.name))])
    error_message = "Every logging_servers name must start with a lowercase letter and then use lowercase letters, digits and hyphens (at most 41 characters). The name is used in resource names, so it must not be an address."
  }

  validation {
    condition = alltrue([
      for s in var.logging_servers :
      can(regex("^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])[.]){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$", s.address))
      ? anytrue([for c in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"] : try(cidrcontains(c, s.address), false)])
      : can(regex("^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?([.][A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*[.][A-Za-z][A-Za-z0-9-]*$|^[A-Za-z][A-Za-z0-9-]{0,62}$", s.address))
    ])
    error_message = "Every logging_servers address must be a private (RFC 1918) or documentation-range (RFC 5737) IPv4 literal, or a host name with no scheme, port or path whose last label starts with a letter. A public IPv4 literal is refused."
  }

  validation {
    condition     = alltrue([for s in var.logging_servers : s.port >= 1 && s.port <= 65535 && s.port == floor(s.port)])
    error_message = "Every logging_servers port must be a whole number from 1 to 65535."
  }

  validation {
    condition     = alltrue([for s in var.logging_servers : contains(["tcp", "udp"], s.protocol)])
    error_message = "Every logging_servers protocol must be tcp or udp."
  }

  validation {
    condition     = alltrue([for s in var.logging_servers : contains(["wazuh-agent", "wazuh-enroll", "syslog", "metrics-remote-write"], s.purpose)])
    error_message = "Every logging_servers purpose must be one of wazuh-agent, wazuh-enroll, syslog, metrics-remote-write."
  }
}

variable "home_remote_network_id" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Id of the Twingate remote network that holds the home logging connector, where the logging resources are created. Required when logging_enabled. It identifies part of the owner's network, so it comes from the site's Doppler config or Spacelift environment."
}

variable "cloud_remote_network_id" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Id of this site's cloud Twingate remote network (stack 10 creates access-<resource_key>), where the scrape resources are created. Required when metrics_enabled. Stack 10 does not output it today, so it is supplied by hand until a later step adds the output."
}

variable "node_exporter_port" {
  type        = number
  default     = 9100
  description = "TCP port the node exporter listens on, on each connector. 1024 to 65535. Must equal node_exporter.port in the access stack (stack 10), which installs the exporter (opt-in, off by default) and opens this port from metrics_source_tag; the stacks are separate, so keep the values in step by hand."

  validation {
    condition     = var.node_exporter_port >= 1024 && var.node_exporter_port <= 65535 && var.node_exporter_port == floor(var.node_exporter_port)
    error_message = "node_exporter_port must be a whole number from 1024 to 65535."
  }
}

variable "metrics_port_connector" {
  type        = number
  default     = null
  description = "TCP port of the Twingate connector's own metrics endpoint. Must equal connector_telemetry.metrics_port in the access stack (stack 10), which is what makes the connector listen and what the connector firewall admits from metrics_source_tag; the two stacks are separate, so keep the values in step by hand. No default: the connector's metrics bind address is UNVERIFIED and must be tested on one connector first. Required when metrics_enabled; 1024 to 65535, different from node_exporter_port and never 9100 (kept for the node exporter, as in the access stack)."

  validation {
    condition     = var.metrics_port_connector == null || try(var.metrics_port_connector >= 1024 && var.metrics_port_connector <= 65535 && var.metrics_port_connector == floor(var.metrics_port_connector), false)
    error_message = "metrics_port_connector must be unset or a whole number from 1024 to 65535."
  }
}

variable "scrape_allowlist" {
  type = list(object({
    name      = string
    host_role = string
    port      = number
  }))
  default     = []
  description = "Which connector endpoints become Twingate resources for scraping. Each port must be node_exporter_port or metrics_port_connector (checked when metrics_enabled), so adding a port is a reviewed value change. Required non-empty when metrics_enabled."

  validation {
    condition     = length(distinct([for s in var.scrape_allowlist : s.name])) == length(var.scrape_allowlist)
    error_message = "Every scrape_allowlist name must be unique."
  }

  validation {
    condition     = alltrue([for s in var.scrape_allowlist : can(regex("^[a-z][a-z0-9-]{0,30}$", s.name))])
    error_message = "Every scrape_allowlist name must start with a lowercase letter and then use lowercase letters, digits and hyphens (at most 31 characters)."
  }

  validation {
    condition     = alltrue([for s in var.scrape_allowlist : s.host_role == "connector"])
    error_message = "Every scrape_allowlist host_role must be connector (the only role with a private address today)."
  }

  validation {
    condition     = alltrue([for s in var.scrape_allowlist : s.port >= 1024 && s.port <= 65535 && s.port == floor(s.port)])
    error_message = "Every scrape_allowlist port must be a whole number from 1024 to 65535."
  }
}

variable "connector_private_ips" {
  type        = map(string)
  default     = {}
  sensitive   = true
  description = "Private addresses of the site's connectors, keyed a and b: the connector_private_ips output of the access stack, passed in by hand or by a stack dependency (a map through a dependency is UNVERIFIED). Required when metrics_enabled. Private: used for the scrape resources and the scrape_targets output only, which is sensitive."

  validation {
    condition     = alltrue([for k in keys(var.connector_private_ips) : contains(["a", "b"], k)])
    error_message = "connector_private_ips may only have the keys a and b."
  }

  validation {
    condition = alltrue([
      for v in values(var.connector_private_ips) :
      can(regex("^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])[.]){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$", v))
      && anytrue([for c in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] : try(cidrcontains(c, v), false)])
    ])
    error_message = "Every connector_private_ips value must be a private IPv4 address (10/8, 172.16/12 or 192.168/16)."
  }
}

variable "wazuh_agent_group" {
  type        = string
  default     = "cloud"
  description = "Wazuh agent group for this site's cloud hosts. Telemetry label only: read by the host bootstrap in a later step, exposed here in site_identity."

  validation {
    condition     = can(regex("^[a-zA-Z0-9_.-]+$", var.wazuh_agent_group))
    error_message = "wazuh_agent_group may only use letters, digits, underscores, dots and hyphens."
  }
}

variable "labels" {
  type        = map(string)
  default     = {}
  description = "Extra telemetry labels. Only the keys env, role and owner_team are allowed and no value may be longer than 32 characters, to keep metric cardinality bounded."

  validation {
    condition     = alltrue([for k in keys(var.labels) : contains(["env", "role", "owner_team"], k)])
    error_message = "labels may only use the keys env, role and owner_team."
  }

  validation {
    condition     = alltrue([for v in values(var.labels) : length(v) <= 32])
    error_message = "No labels value may be longer than 32 characters."
  }
}

variable "sites" {
  type = map(object({
    site_name               = optional(string, "")
    region                  = optional(string, "")
    cloud_remote_network_id = optional(string, "")
    connector_private_ips   = optional(map(string), {})
  }))
  default     = {}
  sensitive   = true
  description = "Additional sites served by this stack, keyed by each site's resource_key (immutable once applied: it is in the names). Empty, the default, adds nothing and leaves the single-site plan unchanged. Each entry gets its OWN logging and scrape Twingate service (one per site per role, never shared), a logging resource per logging_servers element and a scrape resource per scrape_allowlist entry per connector, all gated on the same two flags. site_name is the telemetry label (empty means site-<key>) and appears in no name; region is a label too (empty means region). cloud_remote_network_id and connector_private_ips are the site's own, as for the single site, and are private. Service keys are still issued out of band, one per host. The home logging servers are shared by every site."

  validation {
    condition     = alltrue([for k in nonsensitive(keys(var.sites)) : can(regex("^[a-z][a-z0-9-]{1,23}$", k))])
    error_message = "Every sites key must be 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }

  validation {
    condition     = alltrue([for k, v in nonsensitive(var.sites) : v.site_name == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", v.site_name))])
    error_message = "Every sites site_name must be empty (meaning site-<key>) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }

  validation {
    condition     = alltrue([for k, v in nonsensitive(var.sites) : v.region == "" || can(regex("^[a-z]{3}[0-9]$", v.region))])
    error_message = "Every sites region must be empty or a DigitalOcean region slug such as tor1."
  }

  validation {
    condition     = alltrue([for k, v in nonsensitive(var.sites) : alltrue([for ck in keys(v.connector_private_ips) : contains(["a", "b"], ck)])])
    error_message = "A sites connector_private_ips may only have the keys a and b."
  }

  validation {
    condition = alltrue([
      for k, v in nonsensitive(var.sites) : alltrue([
        for ip in values(v.connector_private_ips) :
        can(regex("^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])[.]){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$", ip))
        && anytrue([for c in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] : try(cidrcontains(c, ip), false)])
      ])
    ])
    error_message = "Every sites connector_private_ips value must be a private IPv4 address (10/8, 172.16/12 or 192.168/16)."
  }
}
