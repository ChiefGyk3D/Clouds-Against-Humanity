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
