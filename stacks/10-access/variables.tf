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
  description = "Twingate connector telemetry for both connectors. The default ({}) is the live state and changes nothing: merging code with this unset plans no change. status_updates_enabled is a provider setting that is not sent while unset, and never replaces anything. Setting log_level (3, 4, 5 or 7), connection_logs (true writes TWINGATE_LOG_ANALYTICS=v3), metrics_port (TWINGATE_METRICS_PORT, 1024 to 65535, not 9100) or labels (KEY = value becomes TWINGATE_LABEL_KEY=value, shown in the Twingate Admin Console, so never put a secret in a label) adds lines to /etc/twingate/connector.conf, which changes user_data and REPLACES the droplet of every connector listed in connector_telemetry_instances (both by default). Roll out one connector at a time: connector_telemetry_instances = [\"a\"] first, then [\"a\", \"b\"], with an SSH-through-Twingate check between (docs/wiki/Trace-One-Change-End-to-End.md, variant C). It opens no firewall port by itself: set metrics_source_tag to admit the metrics port from that one tag."

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

variable "metadata_lock" {
  type        = bool
  default     = false
  nullable    = false
  description = "Lock the metadata endpoint (169.254.169.254, which serves each connector's user-data and so its Twingate tokens) to root and the do-agent user (DigitalOcean's monitoring agent). The default (false) is the live state and changes nothing: merging code with this unset plans no change. true adds an nftables table, a script and a systemd unit through user_data, which REPLACES the droplet of every connector listed in metadata_lock_instances (both by default). Roll out one connector at a time: metadata_lock = true with metadata_lock_instances = [\"a\"], apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"]. Not yet tested on a real machine."
}

variable "metadata_lock_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get metadata_lock: a, b or both (default both, and only matters once metadata_lock is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the lock, as it does today."

  validation {
    condition     = length(var.metadata_lock_instances) >= 1 && alltrue([for i in var.metadata_lock_instances : contains(["a", "b"], i)]) && length(distinct(var.metadata_lock_instances)) == length(var.metadata_lock_instances)
    error_message = "metadata_lock_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "node_exporter" {
  type = object({
    enabled = optional(bool, false)
    port    = optional(number, 9100)
  })
  default     = {}
  nullable    = false
  description = "Opt-in node exporter (prometheus-node-exporter from the distro archive) on each connector, bound to its private address only. The default ({}) is the live state and changes nothing: merging code with this unset plans no change. enabled = true adds a package, a script and a systemd drop-in through user_data, which REPLACES the droplet of every connector listed in node_exporter_instances (both by default). port is 1024 to 65535 (default 9100) and must differ from connector_telemetry.metrics_port. It opens no firewall port by itself: set metrics_source_tag as well, which admits the port from that one tag. Roll out one connector at a time: node_exporter = { enabled = true } with node_exporter_instances = [\"a\"], apply, check SSH through Twingate to the new connector and the memory headroom of the 1 GB droplet, then [\"a\", \"b\"]. NOT applied and NOT tested on a real machine yet."

  validation {
    condition     = var.node_exporter.port == floor(var.node_exporter.port) && var.node_exporter.port >= 1024 && var.node_exporter.port <= 65535
    error_message = "node_exporter.port must be a whole number from 1024 to 65535."
  }
}

variable "node_exporter_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get node_exporter: a, b or both (default both, and only matters once node_exporter.enabled is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the exporter, as it does today."

  validation {
    condition     = length(var.node_exporter_instances) >= 1 && alltrue([for i in var.node_exporter_instances : contains(["a", "b"], i)]) && length(distinct(var.node_exporter_instances)) == length(var.node_exporter_instances)
    error_message = "node_exporter_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "metrics_source_tag" {
  type        = string
  default     = ""
  nullable    = false
  description = "DigitalOcean tag of the droplets that may scrape the connectors' metrics ports (the node exporter port and connector_telemetry.metrics_port, tcp). Empty (the default) is the live state: no metrics rule exists and merging code with this unset plans no change. When set, the connector firewall gains one tag-sourced inbound rule per enabled metrics port (source_tags = [this tag], never an address, never a public source); nothing is added for a port that is not enabled. The tag must be a tag name, so an address or CIDR is refused. It must already exist on the account (the stack that creates the scraping droplets owns it); this stack does not create it. Changes the firewall only; replaces no droplet."

  validation {
    condition     = var.metrics_source_tag == "" || can(regex("^[A-Za-z0-9:_-]{1,255}$", var.metrics_source_tag))
    error_message = "metrics_source_tag must be empty or a DigitalOcean tag name: 1 to 255 letters, digits, colon, hyphen or underscore. An address or CIDR is refused."
  }
}

variable "log_shipping" {
  type = object({
    enabled             = optional(bool, false)
    manager_address     = optional(string, "")
    manager_port        = optional(number, 1514)
    enroll_port         = optional(number, 1515)
    agent_name_prefix   = optional(string, "")
    agent_group         = optional(string, "")
    apt_key_fingerprint = optional(string, "")
    agent_version       = optional(string, "")
  })
  default     = {}
  nullable    = false
  sensitive   = true
  description = "Opt-in log shipping: the Wazuh agent (from Wazuh's apt repository, key checked against apt_key_fingerprint) and auditd on each connector, enrolled at first boot with a secret pulled from Doppler. The default ({}) is the live state and changes nothing: merging code with this unset plans no change (the golden user_data hashes in the bootstrap tests prove it). enabled = true changes user_data and REPLACES the droplet of every connector listed in log_shipping_instances (both by default). Roll out one connector at a time: log_shipping_instances = [\"a\"], apply, check SSH through Twingate and the memory headroom of the 1 GB droplet (UNMEASURED), then [\"a\", \"b\"]. Required when enabled: manager_address (the Wazuh manager as reached through Twingate; a host name or IPv4 address), agent_name_prefix (each agent is named <prefix>-connector-<a or b>; use the same value as site_name, but it is a separate input on purpose, because it lands in user_data and changing it replaces the droplet while site_name replaces nothing), apt_key_fingerprint (the 40 uppercase hex digits of Wazuh's repository signing key; no default on purpose) and log_shipping_bootstrap_token. agent_group must already exist on the manager (empty means none). agent_version pins the agent package (for example 4.9.2-1) and should match the manager's version. manager_port (1514) and enroll_port (1515) must match the logging_servers ports in stack 20. Sensitive because the manager address identifies your network. NOT applied and NOT tested on a real machine. The Twingate headless client the agent needs to reach the manager is NOT part of this change, so an enabled agent cannot connect yet."

  validation {
    condition     = alltrue([for p in [var.log_shipping.manager_port, var.log_shipping.enroll_port] : p == floor(p) && p >= 1 && p <= 65535])
    error_message = "log_shipping.manager_port and log_shipping.enroll_port must be whole numbers from 1 to 65535."
  }

  validation {
    condition     = can(regex("^([a-z][a-z0-9-]{1,40})?$", var.log_shipping.agent_name_prefix))
    error_message = "log_shipping.agent_name_prefix must be empty or 2 to 41 characters: a lowercase letter, then lowercase letters, digits or hyphens (each agent is named <prefix>-connector-<a or b>)."
  }

  validation {
    condition     = !var.log_shipping.enabled || var.log_shipping.agent_name_prefix != ""
    error_message = "log_shipping.agent_name_prefix is required when log_shipping is enabled (for example site-tor1, the same as site_name)."
  }

  validation {
    condition     = !var.log_shipping.enabled || can(regex("^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$", var.log_shipping.manager_address))
    error_message = "log_shipping.manager_address is required when enabled: a host name or IPv4 address of letters, digits, dots and hyphens (no scheme, port, path or spaces)."
  }

  validation {
    condition     = !var.log_shipping.enabled || can(regex("^[0-9A-F]{40}$", var.log_shipping.apt_key_fingerprint))
    error_message = "log_shipping.apt_key_fingerprint is required when enabled: the 40 uppercase hex digits of Wazuh's repository signing key, no spaces. There is no default on purpose: read it from Wazuh's documentation and compare it before you set it."
  }

  validation {
    condition     = can(regex("^([A-Za-z0-9_][A-Za-z0-9_.-]{0,63})?$", var.log_shipping.agent_group))
    error_message = "log_shipping.agent_group must be empty or 1 to 64 letters, digits, dot, underscore or hyphen, not starting with a dot or hyphen."
  }

  validation {
    condition     = can(regex("^([0-9]+[.][0-9]+[.][0-9]+-[0-9]+)?$", var.log_shipping.agent_version))
    error_message = "log_shipping.agent_version must be empty or a package version such as 4.9.2-1."
  }
}

variable "log_shipping_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get log_shipping: a, b or both (default both, and only matters once log_shipping.enabled is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector and its memory headroom, then [\"a\", \"b\"] and apply again. A connector not listed runs without the agent, as it does today."

  validation {
    condition     = length(var.log_shipping_instances) >= 1 && alltrue([for i in var.log_shipping_instances : contains(["a", "b"], i)]) && length(distinct(var.log_shipping_instances)) == length(var.log_shipping_instances)
    error_message = "log_shipping_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "log_shipping_bootstrap_token" {
  type        = string
  default     = ""
  nullable    = false
  sensitive   = true
  description = "The one secret-shaped value log shipping puts in user_data: a short-lived, read-only Doppler service token for the config cah-<resource_key>-hostboot, created out of band by the maintainer (not by OpenTofu) and set as a sensitive Spacelift stack environment variable (TF_VAR_log_shipping_bootstrap_token). The first-boot script deletes the token file before using it; the token expires on its own (the shortest lifetime Doppler allows is UNVERIFIED, so revoke it after the first boot if that is long). It is still in the state, the provider API, the metadata endpoint and cloud-init's own copy of user_data until it expires or is revoked. Required when log_shipping.enabled; never rendered otherwise. 16 to 512 characters of letters, digits, dot, underscore and hyphen."

  validation {
    condition     = var.log_shipping_bootstrap_token == "" || can(regex("^[A-Za-z0-9._-]{16,512}$", var.log_shipping_bootstrap_token))
    error_message = "log_shipping_bootstrap_token must be empty or 16 to 512 characters of letters, digits, dot, underscore and hyphen."
  }

  validation {
    condition     = var.log_shipping_bootstrap_token != "" || !var.log_shipping.enabled
    error_message = "log_shipping.enabled needs log_shipping_bootstrap_token (a short-lived, read-only Doppler token for the hostboot config)."
  }
}

variable "host_firewall" {
  type        = bool
  default     = false
  nullable    = false
  description = "A default-drop host firewall (nftables table inet cah_host, input chain only) on each connector, a second layer behind the cloud firewall. Inbound is allowed only for loopback, established traffic, the ICMP and DHCP the network card needs, TCP 22 from host_firewall_ssh_sources and, when connector_telemetry.metrics_port is set, that port from the same sources. The default (false) is the live state and changes nothing: merging code with this unset plans no change. true adds a script, a systemd unit and the nftables package through user_data, which REPLACES the droplet of every connector listed in host_firewall_instances (both by default). The script checks the ruleset, applies it, verifies sshd still listens and removes the table if not. Roll out one connector at a time: host_firewall = true with host_firewall_instances = [\"a\"], apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"]. Not yet tested on a real machine."
}

variable "host_firewall_instances" {
  type        = list(string)
  default     = ["a", "b"]
  nullable    = false
  description = "Which connectors get host_firewall: a, b or both (default both, and only matters once host_firewall is true). Set [\"a\"] first, apply, check SSH through Twingate to the new connector, then [\"a\", \"b\"] and apply again. A connector not listed runs without the host firewall, as it does today."

  validation {
    condition     = length(var.host_firewall_instances) >= 1 && alltrue([for i in var.host_firewall_instances : contains(["a", "b"], i)]) && length(distinct(var.host_firewall_instances)) == length(var.host_firewall_instances)
    error_message = "host_firewall_instances must hold a, b or both, each at most once (at least one entry)."
  }
}

variable "host_firewall_ssh_sources" {
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  nullable    = false
  description = "IPv4 CIDRs allowed to reach TCP 22 (and the connector metrics port) through the host firewall. Default the three private RFC 1918 blocks: the cloud firewall already limits SSH to the connector tag and this only narrows it to private space, because the module does not know the VPC CIDR. Narrow it to your VPC range if you know it. No leading zeros in octets or prefix and a prefix of 1 to 32; a /0 is refused on purpose because it would defeat the narrowing (the cloud firewall is still the outer layer). Host bits and overlapping entries are allowed. Only matters once host_firewall is true."

  validation {
    condition = length(var.host_firewall_ssh_sources) >= 1 && length(distinct(var.host_firewall_ssh_sources)) == length(var.host_firewall_ssh_sources) && alltrue([
      for c in var.host_firewall_ssh_sources : can(regex("^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])/([1-9]|[12][0-9]|3[0-2])$", c)) && can(cidrnetmask(c))
    ])
    error_message = "host_firewall_ssh_sources must hold at least one IPv4 CIDR (for example 10.0.0.0/8), each at most once, written without leading zeros (nft rejects 10.0.0.0/08) and with a prefix of 1 to 32. A /0 (0.0.0.0/0) is refused on purpose: it would defeat the narrowing to private space, and the cloud firewall stays the outer layer either way."
  }
}
