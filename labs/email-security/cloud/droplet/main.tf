# SPDX-License-Identifier: Apache-2.0
# Piece 3: the one machine Mail-in-a-Box needs. It must be a fresh, dedicated machine.
# The Mail-in-a-Box guide (read 2026-10-22) says to name a DigitalOcean droplet after the box's
# hostname, because DigitalOcean then sets the reverse DNS (PTR) to that name.
variable "enabled" {
  type    = bool
  default = false
}

variable "hostname" {
  description = "The box's full hostname, for example box.example.com. Becomes the droplet name and so the PTR."
  type        = string
  default     = "box.example.com"
}

variable "region" {
  type    = string
  default = "nyc3"
}

variable "size" {
  description = "s-1vcpu-1gb is $6 a month in docs/cost-prices.json (retrieved 2026-10-21)."
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "image" {
  description = "The Mail-in-a-Box setup guide names Ubuntu 22.04 (read 2026-10-22). The slug is est.: check it in your account."
  type        = string
  default     = "ubuntu-22-04-x64"
}

variable "ssh_key_fingerprints" {
  description = "Fingerprints of SSH keys already in your account. Required: no password login."
  type        = list(string)
  default     = []
}

variable "tag" {
  type    = string
  default = "mail-lab"
}

resource "digitalocean_droplet" "this" {
  count    = var.enabled ? 1 : 0
  name     = var.hostname
  region   = var.region
  size     = var.size
  image    = var.image
  ssh_keys = var.ssh_key_fingerprints
  tags     = [var.tag]
  ipv6     = false # the setup guide says to disable IPv6 if you can

  lifecycle {
    precondition {
      condition     = length(var.ssh_key_fingerprints) > 0
      error_message = "Give at least one SSH key fingerprint; do not create a droplet that falls back to a password."
    }
  }
}

output "droplet_id" {
  value = try(digitalocean_droplet.this[0].id, "")
}

output "droplet_urn" {
  value = try(digitalocean_droplet.this[0].urn, "")
}

output "ipv4" {
  value = try(digitalocean_droplet.this[0].ipv4_address, "")
}
