variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "remote_network_id" {
  type        = string
  description = "Twingate remote network (site) shared by every connector of the stack."
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
  description = "Public key for the cah-admin user: '<algorithm> <key>' with an optional trailing comment of one word of safe characters. The comment is dropped before the key reaches cloud-init, so the machine sees only '<algorithm> <key>'. Key-only access; no password exists."

  validation {
    condition     = can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/]+=*( [A-Za-z0-9@._+:=/-]{1,64})?$", var.admin_ssh_public_key))
    error_message = "admin_ssh_public_key must be '<ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|384|521> <base64 key>' with at most one trailing comment word of letters, digits and @ . _ + : = / - (no spaces or line breaks)."
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

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in resource NAMES in place of region. Empty means region, so every name is the same as before this setting existed. Immutable on a live stack: changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}
