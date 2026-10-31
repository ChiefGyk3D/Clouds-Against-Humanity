# SPDX-License-Identifier: Apache-2.0
variable "workload_enabled" {
  type        = bool
  default     = false
  nullable    = false
  description = "Master switch for the workload host (tag, firewall, droplet, project attachment and the two Twingate resources). false (the default) creates nothing. Stage 3 is not approved; turning this on also needs this stack's cost.json to carry workload_approved = true and a priced droplet entry, set in the reviewed change that approves the stage (see docs/stages/03-workloads.md)."
}

variable "region" {
  type        = string
  default     = "tor1"
  description = "DigitalOcean region slug (three lowercase letters and a digit), the same as the access stack. Names are built from resource_key, which defaults to this value."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the NAMES and TAGS of cloud and Twingate objects (cah-workload-<key>, workload-<key>-docker, cah-<key>-workload-ssh). Empty means region. IMMUTABLE FOR THE LIFE OF A STACK: changing it changes names and may replace resources, including through tags or user_data. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "vpc_id" {
  type        = string
  description = "The core VPC, from the foundation stack's vpc_id output. The droplet joins it."
}

variable "project_id" {
  type        = string
  description = "Id of the existing DigitalOcean project (the foundation stack's project_id output). The droplet is attached to it."
}

variable "baseline_tag" {
  type        = string
  description = "The baseline firewall's tag, from the foundation stack. The droplet carries it as well as its own workload tag."

  validation {
    condition     = startswith(var.baseline_tag, "cah-baseline-")
    error_message = "baseline_tag must start with \"cah-baseline-\" so the droplet is covered by the baseline firewall."
  }
}

variable "connector_tag" {
  type        = string
  description = "The Twingate connectors' tag, from the access stack's connector_tag output. The only source the workload firewall admits."

  validation {
    condition     = startswith(var.connector_tag, "cah-connector-")
    error_message = "connector_tag must start with \"cah-connector-\": it is the access stack's connector tag, the only source the workload firewall admits."
  }
}

variable "remote_network_id" {
  type        = string
  description = "Id of the Twingate remote network (site) of the access stack. Both Twingate resources live in it, behind its connectors."

  validation {
    condition     = length(var.remote_network_id) > 0
    error_message = "remote_network_id must be the Twingate remote network of the access stack."
  }
}

variable "admin_group_id" {
  type        = string
  description = "Id of the Twingate admins group of the access stack (cah-<key>-admins). The only group granted access to the two resources."

  validation {
    condition     = length(var.admin_group_id) > 0
    error_message = "admin_group_id must be the Twingate admins group of the access stack; without it nobody could reach the host."
  }
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public key for the cah-admin user: '<algorithm> <key>' with an optional trailing comment of one word of safe characters. The comment is dropped before the key reaches cloud-init. Supplied from Doppler."

  validation {
    condition     = can(regex("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/]+=*( [A-Za-z0-9@._+:=/-]{1,64})?$", var.admin_ssh_public_key))
    error_message = "admin_ssh_public_key must be '<ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|384|521> <base64 key>' with at most one trailing comment word of letters, digits and @ . _ + : = / - (no spaces or line breaks)."
  }
}

variable "admin_ssh_key_name" {
  type        = string
  description = "Name of an SSH key already registered on the DigitalOcean account. Not a secret, but account-specific, so it is supplied from Doppler."

  validation {
    condition     = length(var.admin_ssh_key_name) > 0
    error_message = "admin_ssh_key_name must name an SSH key that is already registered on the DigitalOcean account."
  }
}

variable "reboot_time" {
  type        = string
  default     = "03:30"
  description = "HH:MM (in `timezone`) when unattended-upgrades may reboot the droplet. Must sit at least 30 minutes from the connectors' reboots (04:00 and 05:00) and their weekly updates (04:30 and 05:30), so the host never reboots while Twingate is restarting its only way in. The default is outside the edge slots (01:00 to 03:00) too."

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.reboot_time))
    error_message = "reboot_time must be HH:MM in 24-hour time, for example 03:30."
  }

  # Circular distance, in minutes, to each connector window (04:00, 04:30,
  # 05:00, 05:30 America/New_York) must be at least 30.
  validation {
    condition = try(alltrue([
      for c in [240, 270, 300, 330] :
      min(abs((tonumber(substr(var.reboot_time, 0, 2)) * 60 + tonumber(substr(var.reboot_time, 3, 2))) - c), 1440 - abs((tonumber(substr(var.reboot_time, 0, 2)) * 60 + tonumber(substr(var.reboot_time, 3, 2))) - c)) >= 30
    ]), false)
    error_message = "reboot_time must be at least 30 minutes from every connector window (04:00, 04:30, 05:00 and 05:30)."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location), also the zone reboot_time is read in. Default America/New_York, the zone the connectors' windows are written in. Changing it replaces the droplet."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
  }
}

variable "portainer_version" {
  type        = string
  default     = "2.45.3"
  description = "Exact Portainer CE image tag, an LTS release from Portainer's releases page (read 2026-10-31). Bumped in a reviewed change, which replaces the droplet."

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.portainer_version))
    error_message = "portainer_version must be an exact version such as 2.45.3, never latest, a range or a variant."
  }
}
