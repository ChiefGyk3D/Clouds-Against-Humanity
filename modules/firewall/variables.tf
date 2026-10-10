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
