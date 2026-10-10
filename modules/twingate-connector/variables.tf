variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline firewall tag. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json."
}

variable "ssh_public_key" {
  type        = string
  description = "Admin public key. SSH is reachable only through Twingate."
}

variable "twingate_network" {
  type      = string
  sensitive = true
}
