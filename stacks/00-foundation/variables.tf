variable "region" {
  type        = string
  default     = "tor1"
  description = "DigitalOcean region slug (three lowercase letters and a digit, for example tor1). Names are built from resource_key, which defaults to this value. Check the sizes your account may use in this region (GET /v2/sizes) before changing it."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.78.0.0/24"
  description = "Private CIDR. Must not overlap any homelab range: list those in reserved_ranges and the plan fails on an overlap. Must be the network address (10.78.0.0/24, not 10.78.0.5/24)."

  validation {
    condition     = can(cidrnetmask(var.vpc_ip_range)) && can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", var.vpc_ip_range))
    error_message = "vpc_ip_range must be a private IPv4 CIDR (10/8, 172.16/12 or 192.168/16)."
  }

  validation {
    condition     = try(cidrsubnet(var.vpc_ip_range, 0, 0) == var.vpc_ip_range, false)
    error_message = "vpc_ip_range must be written as its network address, for example 10.78.0.0/24 and not 10.78.0.5/24."
  }

  validation {
    condition     = try(tonumber(split("/", var.vpc_ip_range)[1]) >= 16 && tonumber(split("/", var.vpc_ip_range)[1]) <= 28, false)
    error_message = "vpc_ip_range must have a prefix length between /16 and /28."
  }
}

variable "reserved_ranges" {
  type        = list(string)
  default     = []
  sensitive   = true
  description = "Private CIDRs the VPC range must not overlap (your homelab, other VPCs, anything you connect to). Optional. They identify your network, so never commit them. Today they reach a run as the Spacelift stack environment variable TF_VAR_reserved_ranges (a JSON list) or from a private tfvars. Doppler carries them only once a line in .spacelift/config.yml requests them; the foundation hooks request only DIGITALOCEAN_TOKEN. The check only knows the ranges you list; it prompts the human check, it does not replace it."

  validation {
    condition     = alltrue([for c in var.reserved_ranges : can(cidrnetmask(c))])
    error_message = "Every reserved_ranges entry must be an IPv4 CIDR such as 10.50.0.0/16."
  }
}

variable "project_name" {
  type    = string
  default = "clouds-against-humanity"
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the NAMES and TAGS of cloud objects (cah-baseline-<key>, foundation-<key>-vpc). Empty means region, so every name is identical to a stack that never set it. IMMUTABLE FOR THE LIFE OF A STACK: changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data. A second site in the same region sets its own key on a NEW stack only. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

# Declared for the telemetry stage (stack 20) and deliberately used by no resource,
# name, tag or output until then; wiring it in would show as a plan change.
# tflint-ignore: terraform_unused_declarations
variable "site_name" {
  type        = string
  default     = ""
  description = "Telemetry label only (metrics and log labels in a later stage). Empty means site-<region>. Appears in no resource name, tag or output, and changing it replaces nothing. Unique across your sites."

  validation {
    condition     = var.site_name == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.site_name))
    error_message = "site_name must be empty (meaning site-<region>) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}
