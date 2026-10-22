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

variable "service_packages" {
  type        = map(string)
  default     = {}
  description = "Service packages to install, name to EXACT version (for example { mosquitto = \"2.0.18-1build3\" }). The default installs none. Every entry is pinned: a missing, empty or wildcard version is refused, so no unpinned service package can reach cloud-init. The pins are not chosen here; they are verified against the distribution by whoever fills this in."

  validation {
    condition     = alltrue([for n, v in var.service_packages : can(regex("^[a-z0-9][a-z0-9+.-]*$", n)) && can(regex("^[A-Za-z0-9][A-Za-z0-9.+~:_-]*$", v))])
    error_message = "Each service package needs a plain package name and an exact version (letters, digits and . + ~ : _ - only; no *, no empty string, no latest)."
  }

  validation {
    condition     = alltrue([for n, v in var.service_packages : !contains(["latest", "any"], lower(v))])
    error_message = "latest and any are not versions; pin an exact one."
  }
}

variable "timezone" {
  type        = string
  default     = "UTC"
  description = "IANA time zone name of the machine (UTC or Area/Location). Also the zone reboot_time is read in."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York."
  }
}

variable "reboot_time" {
  type        = string
  description = "HH:MM in `timezone` when unattended-upgrades may reboot the host. Pick a time that does not collide with the connectors' reboot times."

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.reboot_time))
    error_message = "reboot_time must be HH:MM in 24-hour time, for example 05:00."
  }
}
