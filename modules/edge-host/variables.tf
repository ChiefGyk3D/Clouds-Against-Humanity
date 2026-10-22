# SPDX-License-Identifier: Apache-2.0
variable "layer" {
  type        = string
  description = "Stack layer, used in names (for example edge)."
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug. The reserved IP is created in the same region as the droplet."
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in resource NAMES in place of region. Empty means region. Immutable on a live stack: changing it changes names and may replace resources, including through user_data. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "vpc_id" {
  type        = string
  description = "The edge VPC (rns-dmz). Never the core VPC."
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the one the Cloud Firewall attaches to. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack passes the size it checked against cost.json."
}

variable "public_ports" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Inbound ports open to the whole internet. The host firewall (nftables, default drop) mirrors the Cloud Firewall rule for rule, so the stack passes the same list to both."

  validation {
    condition = alltrue([
      for r in var.public_ports :
      contains(["tcp", "udp"], r.protocol) && can(regex("^[1-9][0-9]{0,4}$", r.port_range)) && try(tonumber(r.port_range) <= 65535, false)
    ])
    error_message = "Each public port needs protocol tcp or udp and a single port_range between 1 and 65535."
  }
}

variable "restricted_ports" {
  type = list(object({
    protocol   = string
    port_range = string
    sources    = list(string)
  }))
  default     = []
  description = "Inbound ports open only to the listed IPv4 source ranges. An entry with no sources renders no rule at all (closed), in the host firewall as in the Cloud Firewall."

  validation {
    condition = alltrue([
      for r in var.restricted_ports :
      contains(["tcp", "udp"], r.protocol) && can(regex("^[1-9][0-9]{0,4}$", r.port_range)) && try(tonumber(r.port_range) <= 65535, false)
    ])
    error_message = "Each restricted port needs protocol tcp or udp and a single port_range between 1 and 65535."
  }

  validation {
    condition     = alltrue([for r in var.restricted_ports : alltrue([for s in r.sources : can(cidrnetmask(s)) && !strcontains(s, ":") && s != "0.0.0.0/0"])])
    error_message = "Restricted sources must be IPv4 ranges (a:b notation is IPv6) and never 0.0.0.0/0; a port open to everyone belongs in public_ports."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location). Also the zone reboot_time is read in. Eastern by default, the zone the connectors' reboot times and reboot-slots.json are written in."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York."
  }
}

variable "service" {
  type        = string
  description = "The one edge service this droplet runs: a key of reboot-slots.json (reticulum, lxmd, i2pd, mosquitto, iperf3). Each service is its own stack and its own droplet; the name, the reboot slot and the Doppler config name follow from it. This module installs no service."

  validation {
    condition     = contains(["reticulum", "lxmd", "i2pd", "mosquitto", "iperf3"], var.service)
    error_message = "service must be one of reticulum, lxmd, i2pd, mosquitto, iperf3 (the keys of reboot-slots.json)."
  }
}

variable "project_id" {
  type        = string
  description = "Id of the existing DigitalOcean project (the foundation stack's project_id output). The droplet and the reserved IP are attached to it."
}

variable "reboot_time" {
  type        = string
  default     = null
  description = "HH:MM in `timezone` when unattended-upgrades may reboot this host. null (the default) takes the service's slot from reboot-slots.json (01:00 to 03:00 Eastern, before the connectors' 04:00 and 05:00). A test keeps the slots distinct from each other and from the connectors."

  validation {
    condition     = var.reboot_time == null ? true : can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.reboot_time))
    error_message = "reboot_time must be null or HH:MM in 24-hour time, for example 02:30."
  }
}
