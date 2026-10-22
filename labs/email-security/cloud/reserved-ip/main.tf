# SPDX-License-Identifier: Apache-2.0
# Piece 4: a reserved (static) IPv4 address, so the address you build reputation on survives a rebuild.
# DigitalOcean's pricing page (read 2026-10-22): free while assigned to a droplet; $5.00 a month
# ($0.01 an hour) when reserved but NOT assigned. Whether the PTR follows a reserved address is est.:
# check it with `dig -x` after assigning.
variable "enabled" {
  type    = bool
  default = false
}

variable "region" {
  type    = string
  default = "nyc3"
}

variable "droplet_id" {
  description = "The droplet to attach to. Leave empty and the address is reserved but unassigned, which is billed."
  type        = string
  default     = ""
}

resource "digitalocean_reserved_ip" "this" {
  count  = var.enabled ? 1 : 0
  region = var.region
}

resource "digitalocean_reserved_ip_assignment" "this" {
  count      = var.enabled && var.droplet_id != "" ? 1 : 0
  ip_address = digitalocean_reserved_ip.this[0].ip_address
  droplet_id = var.droplet_id
}

output "ip_address" {
  value = try(digitalocean_reserved_ip.this[0].ip_address, "")
}

output "urn" {
  value = try(digitalocean_reserved_ip.this[0].urn, "")
}
