variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "purpose" {
  type        = string
  description = "Role in the firewall name (for example baseline or connector)."
}

variable "tag" {
  type        = string
  description = "Droplet tag this firewall attaches to."
}

variable "extra_outbound_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Outbound rules appended to the defaults."
}

variable "inbound_from_tag_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Inbound rules that admit only droplets carrying this firewall's own tag. Empty means deny-all inbound."

  validation {
    condition     = alltrue([for r in var.inbound_from_tag_rules : contains(["tcp", "udp"], r.protocol) && length(r.port_range) > 0])
    error_message = "Each inbound rule needs protocol tcp or udp and a non-empty port_range."
  }
}

variable "outbound_to_tag_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Outbound rules that reach only droplets carrying this firewall's own tag (no addresses). Empty means none."

  validation {
    condition     = alltrue([for r in var.outbound_to_tag_rules : contains(["tcp", "udp"], r.protocol) && length(r.port_range) > 0])
    error_message = "Each outbound-to-tag rule needs protocol tcp or udp and a non-empty port_range."
  }
}

variable "inbound_from_other_tags" {
  type = list(object({
    protocol   = string
    port_range = string
    tag        = string
  }))
  default     = []
  description = "Inbound rules that admit only droplets carrying the given OTHER tag (one rule per entry, source_tags = [tag], never an address). Additive to inbound_from_tag_rules. Empty means none."

  validation {
    condition = alltrue([
      for r in var.inbound_from_other_tags :
      contains(["tcp", "udp"], r.protocol) && try(can(regex("^[1-9][0-9]{0,4}(-[1-9][0-9]{0,4})?$", r.port_range)) && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false)
    ])
    error_message = "Each rule needs protocol tcp or udp and a port_range of a port or range between 1 and 65535 in ascending order (443, 30000-31000)."
  }

  validation {
    condition     = alltrue([for r in var.inbound_from_other_tags : can(regex("^[A-Za-z0-9:_-]{1,255}$", r.tag))])
    error_message = "Each tag must be 1 to 255 characters: letters, digits, colon, hyphen or underscore (the DigitalOcean tag shape)."
  }

  validation {
    condition     = length(distinct([for r in var.inbound_from_other_tags : join("/", [r.protocol, r.port_range, r.tag])])) == length(var.inbound_from_other_tags)
    error_message = "Each (protocol, port_range, tag) may appear only once."
  }
}

variable "outbound_to_other_tags" {
  type = list(object({
    protocol   = string
    port_range = string
    tag        = string
  }))
  default     = []
  description = "Outbound rules that reach only droplets carrying the given OTHER tag (one rule per entry, destination_tags = [tag], never an address). Additive to outbound_to_tag_rules. Empty means none."

  validation {
    condition = alltrue([
      for r in var.outbound_to_other_tags :
      contains(["tcp", "udp"], r.protocol) && try(can(regex("^[1-9][0-9]{0,4}(-[1-9][0-9]{0,4})?$", r.port_range)) && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false)
    ])
    error_message = "Each rule needs protocol tcp or udp and a port_range of a port or range between 1 and 65535 in ascending order (443, 30000-31000)."
  }

  validation {
    condition     = alltrue([for r in var.outbound_to_other_tags : can(regex("^[A-Za-z0-9:_-]{1,255}$", r.tag))])
    error_message = "Each tag must be 1 to 255 characters: letters, digits, colon, hyphen or underscore (the DigitalOcean tag shape)."
  }

  validation {
    condition     = length(distinct([for r in var.outbound_to_other_tags : join("/", [r.protocol, r.port_range, r.tag])])) == length(var.outbound_to_other_tags)
    error_message = "Each (protocol, port_range, tag) may appear only once."
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
