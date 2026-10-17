variable "layer" {
  type        = string
  description = "Stack layer, used in names (for example foundation)."
}

variable "region" {
  type        = string
  description = "AWS region name (for example us-east-1). Used in names; the stack's provider block decides where the VPC is really created."
}

variable "ip_range" {
  type        = string
  description = "Private IPv4 CIDR for the VPC. The one public subnet uses the whole range."
  validation {
    condition = (
      can(cidrnetmask(var.ip_range)) &&
      can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", var.ip_range)) &&
      can(regex("/(1[6-9]|2[0-8])$", var.ip_range))
    )
    error_message = "ip_range must be a private IPv4 CIDR (10/8, 172.16/12 or 192.168/16) with a prefix length from /16 to /28, the sizes AWS accepts."
  }
}

variable "availability_zone" {
  type        = string
  default     = null
  description = "Availability zone of the subnet (for example us-east-1a). Null lets AWS choose. AWS extension: a subnet lives in exactly one zone."
}
