variable "region" {
  type        = string
  description = "DigitalOcean region slug, from the foundation stack's region output. Names are built from resource_key, which defaults to this value."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
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

variable "admin_user_ids" {
  type        = list(string)
  description = "Twingate user ids placed in the admin group. Required; supplied from Doppler, never committed."

  validation {
    condition     = length(var.admin_user_ids) > 0
    error_message = "admin_user_ids must list at least one Twingate user. A missing Doppler value would otherwise create a host nobody can reach."
  }
}

variable "reboot_times" {
  type = map(string)
  default = {
    a = "04:00"
    b = "05:00"
  }
  description = "HH:MM (America/New_York, the droplet's local time) when unattended-upgrades may reboot each connector. Keys a and b. The two times must be at least 60 minutes apart around the clock (across midnight too), so the connectors never reboot together and each weekly update, which runs 30 minutes after its connector's reboot, stays at least 30 minutes from the other connector's reboot."

  validation {
    condition     = length(var.reboot_times) == 2 && alltrue([for k in ["a", "b"] : contains(keys(var.reboot_times), k)])
    error_message = "reboot_times must have exactly the keys a and b."
  }

  validation {
    condition     = alltrue([for v in values(var.reboot_times) : can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", v))])
    error_message = "Every reboot_times value must be HH:MM in 24-hour time, for example 04:00."
  }

  # Minutes since midnight for a and b, then the circular distance (the shorter
  # way round the clock) between: the two reboots (at least 60), and each
  # connector's update (reboot + 30) against the other's reboot (at least 30).
  validation {
    condition = try([
      for m in [[for k in ["a", "b"] : tonumber(substr(var.reboot_times[k], 0, 2)) * 60 + tonumber(substr(var.reboot_times[k], 3, 2))]] :
      min(abs(m[0] - m[1]), 1440 - abs(m[0] - m[1])) >= 60 &&
      min(abs(((m[0] + 30) % 1440) - m[1]), 1440 - abs(((m[0] + 30) % 1440) - m[1])) >= 30 &&
      min(abs(((m[1] + 30) % 1440) - m[0]), 1440 - abs(((m[1] + 30) % 1440) - m[0])) >= 30
    ][0], false)
    error_message = "The reboot_times must be at least 60 minutes apart around the clock (23:30 and 00:30 are 60 apart), so the connectors never reboot together and a weekly update never lands within 30 minutes of the other connector's reboot."
  }
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location, for example America/New_York), also the zone reboot_time and the weekly update are read in. Default America/New_York, the zone the live connectors use. Changing it changes the rendered cloud-init and replaces both droplets."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the NAMES and TAGS of cloud and Twingate objects (access-<key>, cah-connector-<key>, droplet names). Empty means region, so every name is identical to a stack that never set it. IMMUTABLE FOR THE LIFE OF A STACK: changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data. A second site in the same region sets its own key on a NEW stack only. Never derived from site_name."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

# Declared for the telemetry stage (stack 20) and deliberately used by no resource,
# name, tag or output until then; wiring it in would show as a plan change.
# tflint-ignore: terraform_unused_declarations
variable "site_name" {
  type        = string
  default     = ""
  description = "Telemetry label only (metrics and log labels in a later stage). Empty means site-<region>. Appears in no resource name, tag or output, and changing it replaces nothing. Unique across your sites."

  validation {
    condition     = var.site_name == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.site_name))
    error_message = "site_name must be empty (meaning site-<region>) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}
