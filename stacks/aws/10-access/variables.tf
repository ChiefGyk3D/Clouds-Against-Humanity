variable "region" {
  type        = string
  description = "AWS region name, the same value as stack 00 (a Spacelift stack dependency passes it)."

  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]$", var.region))
    error_message = "region must look like us-east-1."
  }
}

variable "vpc_id" {
  type        = string
  description = "ID of the VPC created by stack 00."

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must be a VPC id (vpc-...) from stack 00."
  }
}

variable "subnet_id" {
  type        = string
  description = "ID of the public subnet created by stack 00."

  validation {
    condition     = can(regex("^subnet-[0-9a-f]+$", var.subnet_id))
    error_message = "subnet_id must be a subnet id (subnet-...) from stack 00."
  }
}

variable "project_name" {
  type        = string
  default     = "clouds-against-humanity"
  description = "Value of the Project tag that every AWS resource of the stack receives. Same as stack 00."
}

variable "twingate_network" {
  type      = string
  sensitive = true

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.twingate_network))
    error_message = "twingate_network must be the bare Twingate network subdomain (lowercase letters, digits, hyphens), not a URL and with no quotes."
  }
}

variable "admin_ssh_public_key" {
  type = string
}

variable "admin_user_ids" {
  type        = list(string)
  description = "Twingate user ids placed in the admin group. Required; supplied from Doppler, never committed."

  validation {
    condition     = length(var.admin_user_ids) > 0
    error_message = "admin_user_ids must list at least one Twingate user. A missing Doppler value would otherwise create a host nobody can reach."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location, for example America/New_York), also the zone reboot_time and the weekly update are read in. Default America/New_York. Changing it changes the rendered cloud-init and replaces both instances."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
  }
}

variable "connector_telemetry_previous" {
  type = object({
    status_updates_enabled = optional(bool)
    log_level              = optional(number)
    connection_logs        = optional(bool, false)
    metrics_port           = optional(number)
    labels                 = optional(map(string), {})
  })
  default     = {}
  nullable    = false
  description = "What the connectors NOT listed in connector_telemetry_instances keep: the telemetry they run today. Default {} (nothing), right for the first activation. For a later change (say log_level 5 to 7), set connector_telemetry to the new value, this to the old value, and connector_telemetry_instances = [\"a\"]; apply; check SSH through Twingate; then set instances to [\"a\", \"b\"] and clear this. Without it connector b would lose its telemetry and be replaced in the same plan as a. Same fields and checks as connector_telemetry (the bootstrap module validates it)."
}

variable "connector_telemetry_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get connector_telemetry: a, b or both (default both, and only matters once connector_telemetry is set). This is how the rollout goes one connector at a time: set connector_telemetry and [\"a\"], apply, check SSH through Twingate to the new connector, then set [\"a\", \"b\"] and apply again. A connector not listed gets the default (nothing)."

  validation {
    condition     = length(var.connector_telemetry_instances) >= 1 && alltrue([for i in var.connector_telemetry_instances : contains(["a", "b"], i)]) && length(distinct(var.connector_telemetry_instances)) == length(var.connector_telemetry_instances)
    error_message = "connector_telemetry_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "connector_telemetry" {
  type = object({
    status_updates_enabled = optional(bool)
    log_level              = optional(number)
    connection_logs        = optional(bool, false)
    metrics_port           = optional(number)
    labels                 = optional(map(string), {})
  })
  default     = {}
  nullable    = false
  description = "Twingate connector telemetry for both connectors. The default ({}) is the live state and changes nothing. status_updates_enabled is a provider setting that is not sent while unset, and never replaces anything. Setting log_level (3, 4, 5 or 7), connection_logs (true writes TWINGATE_LOG_ANALYTICS=v3), metrics_port (TWINGATE_METRICS_PORT, 1024 to 65535, not 9100) or labels (KEY = value becomes TWINGATE_LABEL_KEY=value, shown in the Twingate Admin Console, so never put a secret in a label) adds lines to /etc/twingate/connector.conf, which changes user_data and REPLACES the instance of every connector listed in connector_telemetry_instances (both by default; user_data_replace_on_change). Roll out one connector at a time: connector_telemetry_instances = [\"a\"] first, then [\"a\", \"b\"], with an SSH-through-Twingate check between (docs/wiki/Trace-One-Change-End-to-End.md, variant C). It opens no security group port by itself: set metrics_source_security_group_id to admit the metrics port from that one security group."

  validation {
    condition     = var.connector_telemetry.log_level == null ? true : contains([3, 4, 5, 7], var.connector_telemetry.log_level)
    error_message = "connector_telemetry.log_level must be 3, 4, 5 or 7 (Twingate's documented levels), or unset."
  }

  validation {
    condition = var.connector_telemetry.metrics_port == null ? true : (
      var.connector_telemetry.metrics_port == floor(var.connector_telemetry.metrics_port) &&
      var.connector_telemetry.metrics_port >= 1024 &&
      var.connector_telemetry.metrics_port <= 65535 &&
      var.connector_telemetry.metrics_port != 9100
    )
    error_message = "connector_telemetry.metrics_port must be a whole number from 1024 to 65535, and not 9100 (kept for the node exporter), or unset."
  }

  validation {
    condition     = alltrue([for k, v in var.connector_telemetry.labels : can(regex("^[A-Z][A-Z0-9_]{0,31}$", k))])
    error_message = "Each connector_telemetry.labels key must be 1 to 32 characters: an uppercase letter, then uppercase letters, digits or underscores (it becomes TWINGATE_LABEL_<KEY>)."
  }

  validation {
    condition     = alltrue([for k, v in var.connector_telemetry.labels : can(regex("^[A-Za-z0-9._-]{1,64}$", v))])
    error_message = "Each connector_telemetry.labels value must be 1 to 64 characters of letters, digits, dot, underscore or hyphen (no spaces, quotes or line breaks, because it is written into the connector config)."
  }

  validation {
    condition     = length(var.connector_telemetry.labels) <= 10
    error_message = "connector_telemetry.labels may hold at most 10 entries."
  }
}

variable "metadata_lock" {
  type        = bool
  default     = false
  nullable    = false
  description = "Lock the metadata endpoint (169.254.169.254, which serves each connector's user-data and so its Twingate tokens) to root and the do-agent user (DigitalOcean's monitoring agent). The default (false) is the live state and changes nothing: merging code with this unset plans no change. true adds an nftables table, a script and a systemd unit through user_data, which REPLACES the instance of every connector listed in metadata_lock_instances (both by default). Roll out one connector at a time: metadata_lock = true with metadata_lock_instances = [\"a\"], apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"]. Not yet tested on a real machine."
}

variable "metadata_lock_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get metadata_lock: a, b or both (default both, and only matters once metadata_lock is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the lock, as it does today."

  validation {
    condition     = length(var.metadata_lock_instances) >= 1 && alltrue([for i in var.metadata_lock_instances : contains(["a", "b"], i)]) && length(distinct(var.metadata_lock_instances)) == length(var.metadata_lock_instances)
    error_message = "metadata_lock_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "node_exporter" {
  type = object({
    enabled = optional(bool, false)
    port    = optional(number, 9100)
  })
  default     = {}
  nullable    = false
  description = "Opt-in node exporter (prometheus-node-exporter from the distro archive) on each connector, bound to its private address only. The default ({}) is the live state and changes nothing: merging code with this unset plans no change (user_data is byte-identical). enabled = true adds a package, a script and a systemd drop-in through user_data, which REPLACES the instance of every connector listed in node_exporter_instances (both by default; user_data_replace_on_change), and with it the instance's public address. port is 1024 to 65535 (default 9100) and must differ from connector_telemetry.metrics_port. It opens no security group port by itself: set metrics_source_security_group_id as well. Roll out one connector at a time: node_exporter = { enabled = true } with node_exporter_instances = [\"a\"], apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"]. NOT applied and NOT tested on a real machine or account yet."

  validation {
    condition     = var.node_exporter.port == floor(var.node_exporter.port) && var.node_exporter.port >= 1024 && var.node_exporter.port <= 65535
    error_message = "node_exporter.port must be a whole number from 1024 to 65535."
  }
}

variable "node_exporter_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get node_exporter: a, b or both (default both, and only matters once node_exporter.enabled is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the exporter, as it does today."

  validation {
    condition     = length(var.node_exporter_instances) >= 1 && alltrue([for i in var.node_exporter_instances : contains(["a", "b"], i)]) && length(distinct(var.node_exporter_instances)) == length(var.node_exporter_instances)
    error_message = "node_exporter_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "metrics_source_security_group_id" {
  type        = string
  default     = ""
  nullable    = false
  description = "Security group id (sg-...) of the machines that may scrape the connectors' metrics ports (the node exporter port and connector_telemetry.metrics_port, tcp), supplied by the operator from the stack that creates the scraping machines. Empty (the default) is the live state: no metrics rule exists and merging code with this unset plans no change. When set, the connector security group gains one inbound rule per enabled metrics port whose source is that group (referenced_security_group_id), never an address, IPv6 range or prefix list; nothing is added for a port that is not enabled. A CIDR, an address or any value that is not a security group id is refused. The group must already exist in the same VPC (this stack does not create it). Changes the security group only; replaces no instance."

  validation {
    condition     = var.metrics_source_security_group_id == "" || can(regex("^sg-[0-9a-f]{8,17}$", var.metrics_source_security_group_id))
    error_message = "metrics_source_security_group_id must be empty or a security group id (sg- and 8 to 17 hex digits). An address or CIDR is refused."
  }
}

variable "host_firewall" {
  type        = bool
  default     = false
  nullable    = false
  description = "A default-drop host firewall (nftables table inet cah_host, input chain only) on each connector, a second layer behind the cloud firewall. Inbound is allowed only for loopback, established traffic, the ICMP and DHCP the network card needs, TCP 22 from host_firewall_ssh_sources and, when connector_telemetry.metrics_port is set, that port from the same sources. The default (false) is the live state and changes nothing: merging code with this unset plans no change. true adds a script, a systemd unit and the nftables package through user_data, which REPLACES the instance of every connector listed in host_firewall_instances (both by default). The script checks the ruleset, applies it, verifies sshd still listens and removes the table if not. Roll out one connector at a time: host_firewall = true with host_firewall_instances = [\"a\"], apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"]. Not yet tested on a real machine."
}

variable "host_firewall_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get host_firewall: a, b or both (default both, and only matters once host_firewall is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the host firewall, as it does today."

  validation {
    condition     = length(var.host_firewall_instances) >= 1 && alltrue([for i in var.host_firewall_instances : contains(["a", "b"], i)]) && length(distinct(var.host_firewall_instances)) == length(var.host_firewall_instances)
    error_message = "host_firewall_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "host_firewall_ssh_sources" {
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  nullable    = false
  description = "IPv4 CIDRs allowed to reach TCP 22 (and the connector metrics port) through the host firewall. Default the three private RFC 1918 blocks: the cloud firewall already limits SSH to the connector tag and this only narrows it to private space, because the module does not know the VPC CIDR. Narrow it to your VPC range if you know it. No leading zeros in octets or prefix and a prefix of 1 to 32; a /0 is refused on purpose because it would defeat the narrowing (the cloud firewall is still the outer layer). Host bits and overlapping entries are allowed. Only matters once host_firewall is true."

  validation {
    condition = length(var.host_firewall_ssh_sources) >= 1 && length(distinct(var.host_firewall_ssh_sources)) == length(var.host_firewall_ssh_sources) && alltrue([
      for c in var.host_firewall_ssh_sources : can(regex("^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])/([1-9]|[12][0-9]|3[0-2])$", c)) && can(cidrnetmask(c))
    ])
    error_message = "host_firewall_ssh_sources must hold at least one IPv4 CIDR (for example 10.0.0.0/8), each at most once, written without leading zeros (nft rejects 10.0.0.0/08) and with a prefix of 1 to 32. A /0 (0.0.0.0/0) is refused on purpose: it would defeat the narrowing to private space, and the cloud firewall stays the outer layer either way."
  }
}
