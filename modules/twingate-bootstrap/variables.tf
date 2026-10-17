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
  description = "HH:MM (in `timezone`, the droplet's local time; America/New_York by default) when unattended-upgrades may reboot this droplet. Give each connector a different time so they never reboot together."

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

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location, for example America/New_York), also the zone reboot_time and the weekly update are read in. Default America/New_York. Rendered into cloud-init, so changing it changes user_data and replaces the droplet."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone)) && contains(split("\n", file(join("/", [path.module, "timezones.txt"]))), var.timezone)
    error_message = "timezone must be a name in modules/twingate-bootstrap/timezones.txt (the IANA zones, for example America/New_York or UTC): no spaces or line breaks, and the zone must exist."
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
  description = "Connector telemetry. The default ({}) is the live state: it adds no line to the connector config, so user_data is byte-identical and nothing is replaced. status_updates_enabled is a Twingate provider setting; unset (the default) it is not sent at all, so the connector keeps what it has today (Twingate's default, true), and set to true or false it is sent. It never touches user_data. The other four add lines to /etc/twingate/connector.conf and therefore change user_data, which REPLACES the machine: log_level (TWINGATE_LOG_LEVEL, 3 4 5 or 7; unset leaves Twingate's default of 3), connection_logs (true adds TWINGATE_LOG_ANALYTICS=v3, real-time connection logs to the journal), metrics_port (TWINGATE_METRICS_PORT, Prometheus metrics on that port, 1024 to 65535 and not 9100) and labels (a map; KEY=value becomes TWINGATE_LABEL_KEY=value, shown in the Twingate Admin Console, so never put a secret in a label). No firewall port is opened here: that is a separate change."

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

variable "metadata_lock" {
  type        = bool
  default     = false
  nullable    = false
  description = "Lock the droplet metadata endpoint (169.254.169.254, which serves this machine's user-data, connector tokens included) to root and to the do-agent user (DigitalOcean's monitoring agent reads it; the user is allowed only when it exists, so AWS needs no special case). Default false is the live state: user_data is byte-identical (golden hashes in the tests) and nothing is replaced. true adds an nftables table, a script, a systemd unit and the nftables package to user_data, which REPLACES the machine. Not tested on a real machine yet: roll out one connector at a time."
}

variable "host_firewall" {
  type        = bool
  default     = false
  nullable    = false
  description = "A default-drop host firewall (nftables table inet cah_host, input chain only) as a second layer behind the cloud firewall. Inbound is allowed only for loopback, established traffic, the ICMP and DHCP the network card needs, TCP 22 from host_firewall_ssh_sources and, when connector_telemetry.metrics_port is set, that one port from the same sources. Outbound and forwarding are untouched. The script checks the ruleset first, applies it, then verifies sshd still listens and the ssh rule is loaded, and deletes the table if not. Default false is the live state: user_data is byte-identical (golden hashes in the tests) and nothing is replaced. true adds a script, a systemd unit and the nftables package to user_data, which REPLACES the machine. Provider-neutral (DigitalOcean and AWS). Not tested on a real machine yet: roll out one connector at a time."
}

variable "host_firewall_ssh_sources" {
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  nullable    = false
  description = "IPv4 CIDRs allowed to reach TCP 22 (and the telemetry metrics port) when host_firewall is true. Default the three private RFC 1918 blocks: the cloud firewall already limits SSH to the connector tag, and this only narrows it to private space, because this module does not know the VPC CIDR. Narrow it to the VPC range if you know it. IPv4 only (the machines have no public IPv6). Ignored while host_firewall is false."

  validation {
    condition = length(var.host_firewall_ssh_sources) >= 1 && length(distinct(var.host_firewall_ssh_sources)) == length(var.host_firewall_ssh_sources) && alltrue([
      for c in var.host_firewall_ssh_sources : can(regex("^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}/[0-9]{1,2}$", c)) && can(cidrnetmask(c))
    ])
    error_message = "host_firewall_ssh_sources must hold at least one IPv4 CIDR (for example 10.0.0.0/8), each at most once."
  }
}
