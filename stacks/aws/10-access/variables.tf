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

variable "connector_telemetry_previous" {
  type = object({
    status_updates_enabled = optional(bool)
    log_level              = optional(number)
    connection_logs        = optional(bool, false)
    metrics_port           = optional(number)
    labels                 = optional(map(string), {})
  })
  default     = {}
  nullable    = false
  description = "What the connectors NOT listed in connector_telemetry_instances keep: the telemetry they run today. Default {} (nothing), right for the first activation. For a later change (say log_level 5 to 7), set connector_telemetry to the new value, this to the old value, and connector_telemetry_instances = [\"a\"]; apply; check SSH through Twingate; then set instances to [\"a\", \"b\"] and clear this. Without it connector b would lose its telemetry and be replaced in the same plan as a. Same fields and checks as connector_telemetry (the bootstrap module validates it)."
}

variable "connector_telemetry_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get connector_telemetry: a, b or both (default both, and only matters once connector_telemetry is set). This is how the rollout goes one connector at a time: set connector_telemetry and [\"a\"], apply, check SSH through Twingate to the new connector, then set [\"a\", \"b\"] and apply again. A connector not listed gets the default (nothing)."

  validation {
    condition     = length(var.connector_telemetry_instances) >= 1 && alltrue([for i in var.connector_telemetry_instances : contains(["a", "b"], i)]) && length(distinct(var.connector_telemetry_instances)) == length(var.connector_telemetry_instances)
    error_message = "connector_telemetry_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "connector_telemetry" {
  type = object({
    status_updates_enabled = optional(bool)
    log_level              = optional(number)
    connection_logs        = optional(bool, false)
    metrics_port           = optional(number)
    labels                 = optional(map(string), {})
  })
  default     = {}
  nullable    = false
  description = "Twingate connector telemetry for both connectors. The default ({}) is the live state and changes nothing. status_updates_enabled is a provider setting that is not sent while unset, and never replaces anything. Setting log_level (3, 4, 5 or 7), connection_logs (true writes TWINGATE_LOG_ANALYTICS=v3), metrics_port (TWINGATE_METRICS_PORT, 1024 to 65535, not 9100) or labels (KEY = value becomes TWINGATE_LABEL_KEY=value, shown in the Twingate Admin Console, so never put a secret in a label) adds lines to /etc/twingate/connector.conf, which changes user_data and REPLACES the instance of every connector listed in connector_telemetry_instances (both by default; user_data_replace_on_change). Roll out one connector at a time: connector_telemetry_instances = [\"a\"] first, then [\"a\", \"b\"], with an SSH-through-Twingate check between (docs/wiki/Trace-One-Change-End-to-End.md, variant C). It opens no security group port: scraping the metrics port needs a separate change."

  validation {
    condition     = var.connector_telemetry.log_level == null ? true : contains([3, 4, 5, 7], var.connector_telemetry.log_level)
    error_message = "connector_telemetry.log_level must be 3, 4, 5 or 7 (Twingate's documented levels), or unset."
  }

  validation {
    condition = var.connector_telemetry.metrics_port == null ? true : (
      var.connector_telemetry.metrics_port == floor(var.connector_telemetry.metrics_port) &&
      var.connector_telemetry.metrics_port >= 1024 &&
      var.connector_telemetry.metrics_port <= 65535 &&
      var.connector_telemetry.metrics_port != 9100
    )
    error_message = "connector_telemetry.metrics_port must be a whole number from 1024 to 65535, and not 9100 (kept for the node exporter), or unset."
  }

  validation {
    condition     = alltrue([for k, v in var.connector_telemetry.labels : can(regex("^[A-Z][A-Z0-9_]{0,31}$", k))])
    error_message = "Each connector_telemetry.labels key must be 1 to 32 characters: an uppercase letter, then uppercase letters, digits or underscores (it becomes TWINGATE_LABEL_<KEY>)."
  }

  validation {
    condition     = alltrue([for k, v in var.connector_telemetry.labels : can(regex("^[A-Za-z0-9._-]{1,64}$", v))])
    error_message = "Each connector_telemetry.labels value must be 1 to 64 characters of letters, digits, dot, underscore or hyphen (no spaces, quotes or line breaks, because it is written into the connector config)."
  }

  validation {
    condition     = length(var.connector_telemetry.labels) <= 10
    error_message = "connector_telemetry.labels may hold at most 10 entries."
  }
}
