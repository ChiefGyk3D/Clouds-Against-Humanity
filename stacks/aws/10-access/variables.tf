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
