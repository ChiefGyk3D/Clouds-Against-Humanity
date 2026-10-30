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
  description = "IPv4 CIDRs allowed to reach TCP 22 (and the telemetry metrics port) when host_firewall is true. Default the three private RFC 1918 blocks: the cloud firewall already limits SSH to the connector tag, and this only narrows it to private space, because this module does not know the VPC CIDR. Narrow it to the VPC range if you know it. IPv4 only (the machines have no public IPv6). No leading zeros in octets or prefix and a prefix of 1 to 32; a /0 is refused on purpose because it would defeat the narrowing (the cloud firewall is still the outer layer). Host bits and overlapping entries are allowed. Ignored while host_firewall is false."

  validation {
    condition = length(var.host_firewall_ssh_sources) >= 1 && length(distinct(var.host_firewall_ssh_sources)) == length(var.host_firewall_ssh_sources) && alltrue([
      for c in var.host_firewall_ssh_sources : can(regex("^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])/([1-9]|[12][0-9]|3[0-2])$", c)) && can(cidrnetmask(c))
    ])
    error_message = "host_firewall_ssh_sources must hold at least one IPv4 CIDR (for example 10.0.0.0/8), each at most once, written without leading zeros (nft rejects 10.0.0.0/08) and with a prefix of 1 to 32. A /0 (0.0.0.0/0) is refused on purpose: it would defeat the narrowing to private space, and the cloud firewall stays the outer layer either way."
  }
}

variable "node_exporter" {
  type = object({
    enabled = optional(bool, false)
    port    = optional(number, 9100)
  })
  default     = {}
  nullable    = false
  description = "Opt-in host metrics: installs prometheus-node-exporter from the distro archive and binds it to the machine's private IPv4 address only (--web.listen-address=<private address>:<port>; a boot-time script picks the first RFC 1918 address and refuses to start the exporter when it finds none, so it never falls back to a wildcard address). The default ({}, enabled false) is the live state: user_data is byte-identical (golden hashes in the tests) and nothing is replaced. enabled = true adds a package, a script and a systemd drop-in to user_data, which REPLACES the machine (roll out one connector at a time). port is 1024 to 65535 (default 9100), is checked even while disabled, and must differ from connector_telemetry.metrics_port. Opens no cloud firewall port: that is the access stack's separate, tag-sourced rule; with host_firewall the port is allowed from host_firewall_ssh_sources. NOT applied and NOT tested on a real machine yet."

  validation {
    condition     = var.node_exporter.port == floor(var.node_exporter.port) && var.node_exporter.port >= 1024 && var.node_exporter.port <= 65535
    error_message = "node_exporter.port must be a whole number from 1024 to 65535."
  }
}

variable "log_shipping" {
  type = object({
    enabled             = optional(bool, false)
    manager_address     = optional(string, "")
    manager_port        = optional(number, 1514)
    enroll_port         = optional(number, 1515)
    agent_name          = optional(string, "")
    agent_group         = optional(string, "")
    apt_key_fingerprint = optional(string, "")
    agent_version       = optional(string, "")
  })
  default     = {}
  nullable    = false
  sensitive   = true
  description = "Opt-in log shipping: installs the Wazuh agent from Wazuh's apt repository (the repository key is checked against apt_key_fingerprint before it is trusted), adds auditd with a short watch-only rule set (identity and sudo files, /etc/twingate; no execve), collects journald for the twingate-connector, ssh and sudo units plus /var/log/auth.log, and enrolls the agent at first boot with a secret pulled from Doppler (see log_shipping_bootstrap_token). The default ({}, enabled false) is the live state: user_data is byte-identical (golden hashes in the tests) and nothing is replaced. enabled = true adds packages, scripts and files to user_data, which REPLACES the machine (roll out one connector at a time). Required when enabled: manager_address (a host name or IPv4 literal; the manager as reached through Twingate), agent_name (<site>-connector-<instance>, for example site-tor1-connector-a, ending in -connector- and this machine's instance), and apt_key_fingerprint (the 40 hex digits of Wazuh's repository signing key; deliberately no default: read it from Wazuh's documentation and compare it yourself). agent_group is optional and must already exist on the manager. agent_version pins the agent package (for example 4.9.2-1); empty takes the newest 4.x, and an agent newer than the manager is unsupported by Wazuh, so pin it to the manager's version. manager_port (default 1514) and enroll_port (default 1515) are checked even while disabled and must agree with the logging_servers ports in stack 20. Sensitive because the manager address identifies the owner's network. No secret is an input here: the enrollment password, any Twingate service key and any Doppler secret value are never rendered into user_data. The Twingate headless client the agent needs to reach the manager is NOT part of this change. NOT applied and NOT tested on a real machine; the 1 GB droplet's memory headroom with the agent is UNMEASURED."

  validation {
    condition     = alltrue([for p in [var.log_shipping.manager_port, var.log_shipping.enroll_port] : p == floor(p) && p >= 1 && p <= 65535])
    error_message = "log_shipping.manager_port and log_shipping.enroll_port must be whole numbers from 1 to 65535."
  }

  validation {
    condition     = !var.log_shipping.enabled || can(regex("^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$", var.log_shipping.manager_address))
    error_message = "log_shipping.manager_address is required when enabled: a host name or IPv4 address of letters, digits, dots and hyphens (no scheme, port, path or spaces)."
  }

  validation {
    condition     = !var.log_shipping.enabled || can(regex("^[a-z][a-z0-9-]{0,55}-connector-[a-z0-9]$", var.log_shipping.agent_name))
    error_message = "log_shipping.agent_name is required when enabled and must look like <site>-connector-<instance> (lowercase letters, digits and hyphens, for example site-tor1-connector-a)."
  }

  validation {
    condition     = can(regex("^([A-Za-z0-9_][A-Za-z0-9_.-]{0,63})?$", var.log_shipping.agent_group))
    error_message = "log_shipping.agent_group must be empty or 1 to 64 letters, digits, dot, underscore or hyphen, not starting with a dot or hyphen."
  }

  validation {
    condition     = !var.log_shipping.enabled || can(regex("^[0-9A-F]{40}$", var.log_shipping.apt_key_fingerprint))
    error_message = "log_shipping.apt_key_fingerprint is required when enabled: the 40 uppercase hex digits of Wazuh's repository signing key, no spaces. There is no default on purpose: read it from Wazuh's documentation and compare it before you set it."
  }

  validation {
    condition     = can(regex("^([0-9]+[.][0-9]+[.][0-9]+-[0-9]+)?$", var.log_shipping.agent_version))
    error_message = "log_shipping.agent_version must be empty or a package version such as 4.9.2-1."
  }
}

variable "log_shipping_bootstrap_token" {
  type        = string
  default     = ""
  nullable    = false
  sensitive   = true
  description = "The one secret-shaped value that reaches user_data when log_shipping is enabled: a short-lived, read-only Doppler service token for the config cah-<resource_key>-hostboot, created by the maintainer out of band (not by OpenTofu). It is written to a root-only file that the first-boot script deletes before using it, and it expires on its own (the shortest lifetime Doppler allows is UNVERIFIED; revoke it after the first boot if that is long). Required when log_shipping.enabled, ignored (and never rendered) otherwise. It is still in the state, the provider API, the metadata endpoint and cloud-init's own copy of user_data until it expires or is revoked. Letters, digits, dot, underscore and hyphen only, 16 to 512 characters."

  validation {
    condition     = var.log_shipping_bootstrap_token == "" || can(regex("^[A-Za-z0-9._-]{16,512}$", var.log_shipping_bootstrap_token))
    error_message = "log_shipping_bootstrap_token must be empty or 16 to 512 characters of letters, digits, dot, underscore and hyphen."
  }

  # The one placeholder rule of scripts/secret_rule.py, as an RE2 pattern
  # (tests/test_secret_rule.py pins it to that file).
  validation {
    condition     = !can(regex("(?i)(^(your[_-]|changeme|change-me|replace[_-]with|xxx|dp[.]st[.]your|(todo|tbd|admin|password|secret|test)$)|^<.*>$|example|placeholder|changeme)", var.log_shipping_bootstrap_token))
    error_message = "log_shipping_bootstrap_token looks like a placeholder (your_*, changeme*, replace-with*, xxx*, <...>, example, placeholder). Set the real short-lived Doppler token, or leave it empty when log_shipping is off."
  }
}
