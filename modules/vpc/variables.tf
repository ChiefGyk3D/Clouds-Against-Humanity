variable "layer" {
  type        = string
  description = "Stack layer, used in names (for example foundation)."
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug."
}

variable "ip_range" {
  type        = string
  description = "Private IPv4 CIDR for the VPC."
  validation {
    condition     = can(cidrnetmask(var.ip_range)) && can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", var.ip_range))
    error_message = "ip_range must be a private IPv4 CIDR (10/8, 172.16/12 or 192.168/16)."
  }
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
