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
