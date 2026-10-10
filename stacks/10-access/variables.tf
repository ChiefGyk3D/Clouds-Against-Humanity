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
  default     = []
  description = "Twingate user ids placed in the admin group. Supplied from Doppler, never committed."
}
