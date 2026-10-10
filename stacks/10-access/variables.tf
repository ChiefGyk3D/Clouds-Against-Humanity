variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "project_id" {
  type = string
}

variable "baseline_tag" {
  type = string

  validation {
    condition     = startswith(var.baseline_tag, "cah-baseline-")
    error_message = "baseline_tag must start with \"cah-baseline-\" so the connector droplet is covered by the baseline firewall."
  }
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

variable "admin_ssh_key_name" {
  type        = string
  description = "Name of an SSH key already registered on the DigitalOcean account. Not a secret, but account-specific, so it is supplied from Doppler."

  validation {
    condition     = length(var.admin_ssh_key_name) > 0
    error_message = "admin_ssh_key_name must name an SSH key that is already registered on the DigitalOcean account."
  }
}

variable "admin_user_ids" {
  type        = list(string)
  description = "Twingate user ids placed in the admin group. Required; supplied from Doppler, never committed."

  validation {
    condition     = length(var.admin_user_ids) > 0
    error_message = "admin_user_ids must list at least one Twingate user. A missing Doppler value would otherwise create a host nobody can reach."
  }
}
