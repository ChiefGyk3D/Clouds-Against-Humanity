# SPDX-License-Identifier: Apache-2.0
variable "layer" {
  type        = string
  description = "Stack layer, used in the droplet name (for example workload)."
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug."
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the droplet NAME in place of region. Empty means region. Immutable on a live stack: changing it changes the name and may replace the droplet. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "vpc_id" {
  type        = string
  description = "The VPC the droplet joins. Its private address is the only address Portainer is bound to."
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline tag and the tag the workload firewall attaches to. Set at creation so both firewalls apply from the first second."

  validation {
    condition     = length(var.tags) > 0
    error_message = "tags must not be empty: a droplet with no tag has no firewall."
  }
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json, the cost gate's single source."
}

variable "ssh_key_fingerprint" {
  type        = string
  description = "Fingerprint of the admin SSH key registered on the account. SSH is reachable only through Twingate."

  validation {
    condition     = length(var.ssh_key_fingerprint) > 0
    error_message = "ssh_key_fingerprint must name the admin SSH key; without one the droplet would have no way in."
  }
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public key for the cah-admin user: '<algorithm> <key>' with an optional trailing comment of one word of safe characters. The comment is dropped before the key reaches cloud-init. Key-only access; no password exists."

  validation {
    condition     = can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/]+=*( [A-Za-z0-9@._+:=/-]{1,64})?$", var.admin_ssh_public_key))
    error_message = "admin_ssh_public_key must be '<ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|384|521> <base64 key>' with at most one trailing comment word of letters, digits and @ . _ + : = / - (no spaces or line breaks)."
  }
}

variable "reboot_time" {
  type        = string
  description = "HH:MM (in `timezone`) when unattended-upgrades may reboot this droplet. Choose a time that does not meet the connectors' windows."

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.reboot_time))
    error_message = "reboot_time must be HH:MM in 24-hour time, for example 03:30."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location). Also the zone reboot_time is read in. Changing it replaces the droplet."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
  }
}

variable "docker_apt_key_fingerprint" {
  type        = string
  default     = "9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
  description = "Primary fingerprint of Docker's apt signing key. The cloud-init refuses a key file that does not hold exactly this one key before it trusts the repository. Changing it changes user_data and replaces the droplet."

  validation {
    condition     = can(regex("^[0-9A-F]{40}$", var.docker_apt_key_fingerprint))
    error_message = "docker_apt_key_fingerprint must be a full 40-character fingerprint in uppercase hexadecimal, with no spaces."
  }
}

variable "portainer_version" {
  type        = string
  default     = "2.45.3"
  description = "Exact Portainer CE image tag (an LTS release from Portainer's releases page, read 2026-10-31). Never latest or a range: Portainer updates only when this is bumped in a reviewed change, which replaces the droplet."

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.portainer_version))
    error_message = "portainer_version must be an exact version such as 2.45.3, never latest, a range or a variant."
  }
}

variable "portainer_port" {
  type        = number
  default     = 9443
  nullable    = false
  description = "Host port Portainer's HTTPS UI is published on, bound to the private address only."

  validation {
    condition     = var.portainer_port == floor(var.portainer_port) && var.portainer_port >= 1024 && var.portainer_port <= 65535 && var.portainer_port != 22
    error_message = "portainer_port must be a whole port from 1024 to 65535 (never a privileged port, and never SSH's 22)."
  }
}
