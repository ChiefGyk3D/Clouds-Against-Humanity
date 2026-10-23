# SPDX-License-Identifier: Apache-2.0
# Piece 2: a cloud firewall matched by tag, so it exists before the droplet and can never be missed.
# The inbound ports are the ones the Mail-in-a-Box setup guide lists (22, 25, 53 tcp and udp, 80, 443,
# 465, 993, 995, 4190), read 2026-10-22. SSH is limited to the one address you give it.
variable "enabled" {
  type    = bool
  default = false
}

variable "tag" {
  type    = string
  default = "mail-lab"
}

variable "admin_cidr" {
  description = "The one address (a /32) allowed to use SSH. The default is a documentation address (RFC 5737): replace it."
  type        = string
  default     = "192.0.2.10/32"
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.admin_cidr)) && can(cidrhost(var.admin_cidr, 0))
    error_message = "admin_cidr must be a single IPv4 address written as a.b.c.d/32 (the droplet has no IPv6), never a range or the whole internet."
  }
}

locals {
  mail_tcp = ["25", "53", "80", "443", "465", "993", "995", "4190"]
}

resource "digitalocean_firewall" "this" {
  count = var.enabled ? 1 : 0
  name  = "${var.tag}-fw"
  tags  = [var.tag]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = [var.admin_cidr]
  }

  dynamic "inbound_rule" {
    for_each = local.mail_tcp
    content {
      protocol         = "tcp"
      port_range       = inbound_rule.value
      source_addresses = ["0.0.0.0/0", "::/0"]
    }
  }

  inbound_rule {
    protocol         = "udp"
    port_range       = "53"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Outbound is open so the box can reach package mirrors, Let's Encrypt and DNS. DigitalOcean blocks
  # outbound SMTP (25, 465, 587) on droplets by default no matter what this says.
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

output "firewall_id" {
  value = try(digitalocean_firewall.this[0].id, "")
}
