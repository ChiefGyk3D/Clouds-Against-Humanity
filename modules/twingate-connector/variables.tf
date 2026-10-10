variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline firewall tag. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json."
}

variable "remote_network_id" {
  type        = string
  description = "Twingate remote network (site) shared by every connector of the stack."
}

variable "ssh_key_fingerprint" {
  type        = string
  description = "Fingerprint of the stack's admin SSH key. SSH is reachable only through Twingate."
}

variable "instance" {
  type        = string
  description = "One lowercase letter or digit that tells this connector from its siblings (a, b)."

  validation {
    condition     = can(regex("^[a-z0-9]$", var.instance))
    error_message = "instance must be a single lowercase letter or digit."
  }
}

variable "twingate_network" {
  type        = string
  sensitive   = true
  description = "Bare Twingate network subdomain (acme for acme.twingate.com). Sensitive because the tenant slug identifies the tenant."

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.twingate_network))
    error_message = "twingate_network must be the bare Twingate network subdomain (lowercase letters, digits, hyphens), not a URL and with no quotes."
  }
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public key (type and key, no comment) for the cah-admin user. Key-only access; no password exists."

  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) [A-Za-z0-9+/=]+$", var.admin_ssh_public_key))
    error_message = "admin_ssh_public_key must be '<ssh-ed25519|ssh-rsa> <key>' with no comment field."
  }
}

variable "reboot_time" {
  type        = string
  description = "HH:MM (America/New_York, the droplet's local time) when unattended-upgrades may reboot this droplet. Give each connector a different time so they never reboot together."

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.reboot_time))
    error_message = "reboot_time must be HH:MM in 24-hour time, for example 04:00."
  }
}
