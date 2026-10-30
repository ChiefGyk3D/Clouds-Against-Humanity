# SPDX-License-Identifier: Apache-2.0
variable "edge_enabled" {
  type        = bool
  default     = false
  nullable    = false
  description = "Master switch for the shared edge network (VPC, tags and Cloud Firewall; no droplet). false (the default) creates nothing. The stage is not approved; turning this on also needs this stack's cost.json to carry edge_network_approved = true, set in the reviewed change that approves the stage (see docs/stages/05-edge.md)."
}

variable "region" {
  type        = string
  default     = "tor1"
  description = "DigitalOcean region slug (three lowercase letters and a digit). The edge is in the same region as core. Check the sizes your account may use in this region (GET /v2/sizes) before changing it."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the NAMES of the firewall and droplet in place of region. Empty means region. IMMUTABLE for the life of a stack: changing it changes names and may replace resources, including through user_data. The VPC and the tags keep their fixed design names (rns-dmz). Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.30.0.0/24"
  description = "Private CIDR of the rns-dmz VPC, written as its network address. Must not overlap the core VPC (core_vpc_ip_range) or any range in reserved_ranges; the plan fails on an overlap."

  validation {
    condition     = can(cidrnetmask(var.vpc_ip_range)) && can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", var.vpc_ip_range))
    error_message = "vpc_ip_range must be a private IPv4 CIDR (10/8, 172.16/12 or 192.168/16)."
  }

  validation {
    condition     = try(cidrsubnet(var.vpc_ip_range, 0, 0) == var.vpc_ip_range, false)
    error_message = "vpc_ip_range must be written as its network address, for example 10.30.0.0/24 and not 10.30.0.5/24."
  }

  validation {
    condition     = try(tonumber(split("/", var.vpc_ip_range)[1]) >= 16 && tonumber(split("/", var.vpc_ip_range)[1]) <= 28, false)
    error_message = "vpc_ip_range must have a prefix length between /16 and /28."
  }
}

variable "core_vpc_ip_range" {
  type        = string
  default     = "10.78.0.0/24"
  description = "The core VPC's range (stack 00-foundation vpc_ip_range). Only used to refuse an edge range that overlaps it. The edge is never peered with core."

  validation {
    condition     = can(cidrnetmask(var.core_vpc_ip_range))
    error_message = "core_vpc_ip_range must be an IPv4 CIDR."
  }
}

variable "reserved_ranges" {
  type        = list(string)
  default     = []
  sensitive   = true
  description = "Private CIDRs the edge range must not overlap (your homelab, other VPCs). Optional. They identify your network, so never commit them; they arrive as TF_VAR_reserved_ranges in the Spacelift stack environment or from a private tfvars."

  validation {
    condition     = alltrue([for c in var.reserved_ranges : can(cidrnetmask(c))])
    error_message = "Every reserved_ranges entry must be an IPv4 CIDR such as 10.50.0.0/16."
  }
}

variable "reticulum_port" {
  type        = number
  default     = 4242
  nullable    = false
  description = "Public TCP port of the Reticulum TCPServerInterface (4242 unless the Reticulum config says otherwise)."

  validation {
    condition     = var.reticulum_port == floor(var.reticulum_port) && var.reticulum_port >= 1 && var.reticulum_port <= 65535
    error_message = "reticulum_port must be a whole port number from 1 to 65535."
  }
}
