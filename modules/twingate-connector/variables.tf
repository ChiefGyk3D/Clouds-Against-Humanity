variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline firewall tag. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json."
}

variable "remote_network_id" {
  type        = string
  description = "Twingate remote network (site) shared by every connector of the stack."
}

variable "ssh_key_fingerprint" {
  type        = string
  description = "Fingerprint of the stack's admin SSH key. SSH is reachable only through Twingate."
}

variable "instance" {
  type        = string
  description = "One lowercase letter or digit that tells this connector from its siblings (a, b)."
}

variable "twingate_network" {
  type        = string
  sensitive   = true
  description = "Bare Twingate network subdomain (acme for acme.twingate.com). Sensitive because the tenant slug identifies the tenant."
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public key for the cah-admin user (an optional trailing comment is dropped before cloud-init). Key-only access; no password exists."
}

variable "reboot_time" {
  type        = string
  description = "HH:MM (in `timezone`, the droplet's local time; America/New_York by default) when unattended-upgrades may reboot this droplet. Give each connector a different time so they never reboot together."
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in resource NAMES in place of region. Empty means region, so every name is the same as before this setting existed. Immutable on a live stack: changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location, for example America/New_York), also the zone reboot_time and the weekly update are read in. Default America/New_York. Passed to the bootstrap module; changing it replaces the droplet."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
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
  description = "Connector telemetry, passed to the bootstrap module, which validates it and explains each field. The default ({}) changes nothing. Any of log_level, connection_logs, metrics_port or labels changes user_data and replaces the droplet; status_updates_enabled does not."
}

variable "metadata_lock" {
  type        = bool
  default     = false
  nullable    = false
  description = "Lock the metadata endpoint (169.254.169.254) to root and the do-agent user, passed to the bootstrap module, which explains it. The default (false) changes nothing. true changes user_data and replaces the droplet."
}

variable "node_exporter" {
  type = object({
    enabled = optional(bool, false)
    port    = optional(number, 9100)
  })
  default     = {}
  nullable    = false
  description = "Opt-in node exporter bound to the private address, passed to the bootstrap module, which validates it and explains it. The default ({}) changes nothing. enabled = true changes user_data and replaces the droplet."
}

variable "host_firewall" {
  type        = bool
  default     = false
  nullable    = false
  description = "A default-drop host firewall (nftables, input only), passed to the bootstrap module, which explains it. The default (false) changes nothing. true changes user_data and replaces the droplet."
}

variable "host_firewall_ssh_sources" {
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  nullable    = false
  description = "IPv4 CIDRs allowed to reach SSH (and the metrics port) when host_firewall is true, passed to the bootstrap module, which validates it. Default the three private RFC 1918 blocks."
}
