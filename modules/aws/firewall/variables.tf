variable "layer" {
  type        = string
  description = "Stack layer, used in names (for example access)."
}

variable "region" {
  type        = string
  description = "AWS region name (for example us-east-1). Used in names."
}

variable "purpose" {
  type        = string
  description = "Role in the group name (for example connector)."
}

variable "vpc_id" {
  type        = string
  description = "VPC the security group belongs to. From the vpc module's id."
}

variable "extra_outbound_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Outbound rules to any IPv4 address, appended to the five defaults. port_range is a port (443), a range (30000-31000) or \"all\" (ports 0-65535 of that one protocol)."

  validation {
    condition = alltrue([
      for r in var.extra_outbound_rules :
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || try(regex("^(0|[1-9][0-9]{0,4})(-(0|[1-9][0-9]{0,4}))?$", r.port_range) != null && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false))
    ])
    error_message = "Each extra outbound rule needs protocol tcp or udp and a port_range of a port or range between 0 and 65535 in ascending order (443, 30000-31000), or all."
  }
}

variable "inbound_from_member_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Inbound rules that admit only members of this security group itself (a rule whose source is the group). Empty means no inbound rule at all."

  validation {
    condition = alltrue([
      for r in var.inbound_from_member_rules :
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || try(regex("^(0|[1-9][0-9]{0,4})(-(0|[1-9][0-9]{0,4}))?$", r.port_range) != null && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false))
    ])
    error_message = "Each inbound rule needs protocol tcp or udp and a port_range of a port or range between 0 and 65535 in ascending order (443, 30000-31000), or all."
  }
}

variable "inbound_from_other_groups" {
  type = list(object({
    protocol          = string
    port_range        = string
    security_group_id = string
  }))
  default     = []
  description = "Inbound rules that admit only members of the given OTHER security group (one rule per entry, source = that group, never an address, IPv6 range or prefix list). Additive to inbound_from_member_rules. Empty means none. Ports 1 to 65535, tcp or udp."

  validation {
    condition = alltrue([
      for r in var.inbound_from_other_groups :
      contains(["tcp", "udp"], r.protocol) && try(can(regex("^[1-9][0-9]{0,4}(-[1-9][0-9]{0,4})?$", r.port_range)) && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false)
    ])
    error_message = "Each rule needs protocol tcp or udp and a port_range of a port or range between 1 and 65535 in ascending order (9100, 30000-31000)."
  }

  validation {
    condition     = alltrue([for r in var.inbound_from_other_groups : can(regex("^sg-[0-9a-f]{8,17}$", r.security_group_id))])
    error_message = "Each security_group_id must be a security group id (sg- and 8 to 17 hex digits), not an address, a CIDR or an empty value."
  }

  validation {
    condition     = length(distinct([for r in var.inbound_from_other_groups : join("/", [r.protocol, r.port_range, r.security_group_id])])) == length(var.inbound_from_other_groups)
    error_message = "Each (protocol, port_range, security_group_id) may appear only once."
  }
}

variable "outbound_to_member_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Outbound rules that reach only members of this security group itself (a rule whose destination is the group, no address). Empty means none."

  validation {
    condition = alltrue([
      for r in var.outbound_to_member_rules :
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || try(regex("^(0|[1-9][0-9]{0,4})(-(0|[1-9][0-9]{0,4}))?$", r.port_range) != null && tonumber(split("-", r.port_range)[0]) <= tonumber(reverse(split("-", r.port_range))[0]) && tonumber(reverse(split("-", r.port_range))[0]) <= 65535, false))
    ])
    error_message = "Each outbound-to-member rule needs protocol tcp or udp and a port_range of a port or range between 0 and 65535 in ascending order (443, 30000-31000), or all."
  }
}
