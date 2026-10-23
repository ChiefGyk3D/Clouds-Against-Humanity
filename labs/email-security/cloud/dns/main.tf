# SPDX-License-Identifier: Apache-2.0
# Piece 5: the one record that points the box's hostname at its address, in a DigitalOcean DNS zone.
# Mail-in-a-Box would rather run its own DNS (nsd) and be given glue records at your registrar; this
# piece is the "external DNS" route the setup guide calls advanced. The box's own "System status & DNS"
# page then lists every other record to add (MX, SPF, DKIM, DMARC, and more). Add those by hand, or
# extend this piece, after you have read them from your own box.
variable "enabled" {
  type    = bool
  default = false
}

variable "domain" {
  description = "A domain you own. The default is the reserved example name: replace it."
  type        = string
  default     = "example.com"
}

variable "box_label" {
  type    = string
  default = "box"
}

variable "ip_address" {
  type    = string
  default = "203.0.113.10"
}

resource "digitalocean_domain" "this" {
  count = var.enabled ? 1 : 0
  name  = var.domain
}

resource "digitalocean_record" "box" {
  count  = var.enabled ? 1 : 0
  domain = digitalocean_domain.this[0].name
  type   = "A"
  name   = var.box_label
  value  = var.ip_address
  ttl    = 300
}

output "box_fqdn" {
  value = var.enabled ? "${var.box_label}.${var.domain}" : null
}
