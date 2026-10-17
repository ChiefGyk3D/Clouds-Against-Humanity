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
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || can(regex("^[0-9]{1,5}(-[0-9]{1,5})?$", r.port_range)))
    ])
    error_message = "Each extra outbound rule needs protocol tcp or udp and a port_range of a port, a range such as 30000-31000, or all."
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
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || can(regex("^[0-9]{1,5}(-[0-9]{1,5})?$", r.port_range)))
    ])
    error_message = "Each inbound rule needs protocol tcp or udp and a port_range of a port, a range such as 30000-31000, or all."
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
      contains(["tcp", "udp"], r.protocol) && (r.port_range == "all" || can(regex("^[0-9]{1,5}(-[0-9]{1,5})?$", r.port_range)))
    ])
    error_message = "Each outbound-to-member rule needs protocol tcp or udp and a port_range of a port, a range such as 30000-31000, or all."
  }
}
