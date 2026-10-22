# SPDX-License-Identifier: Apache-2.0
# Composition root (mode C): calls every piece. Every flag is false, so a plain `tofu plan` creates
# nothing. Read docs/wiki/Email-Security-DNS-Gateways-and-API-Driven-Protection.md first: the cost box
# is there. The token comes from your environment (DIGITALOCEAN_TOKEN); it is never a variable.
provider "digitalocean" {}

variable "enable_project" {
  type    = bool
  default = false
}
variable "enable_firewall" {
  type    = bool
  default = false
}
variable "enable_droplet" {
  type    = bool
  default = false
}
variable "enable_reserved_ip" {
  type    = bool
  default = false
}
variable "enable_dns" {
  type    = bool
  default = false
}
variable "domain" {
  type    = string
  default = "example.com"
}
variable "box_label" {
  type    = string
  default = "box"
}
variable "admin_cidr" {
  type    = string
  default = "192.0.2.10/32"
}
variable "ssh_key_fingerprints" {
  type    = list(string)
  default = []
}
variable "region" {
  type    = string
  default = "nyc3"
}

module "firewall" {
  source     = "../cloud/firewall"
  enabled    = var.enable_firewall
  admin_cidr = var.admin_cidr
}

module "droplet" {
  source               = "../cloud/droplet"
  enabled              = var.enable_droplet
  hostname             = "${var.box_label}.${var.domain}"
  region               = var.region
  ssh_key_fingerprints = var.ssh_key_fingerprints
}

module "reserved_ip" {
  source     = "../cloud/reserved-ip"
  enabled    = var.enable_reserved_ip
  region     = var.region
  droplet_id = module.droplet.droplet_id
}

module "dns" {
  source     = "../cloud/dns"
  enabled    = var.enable_dns
  domain     = var.domain
  box_label  = var.box_label
  ip_address = coalesce(module.reserved_ip.ip_address, module.droplet.ipv4, "203.0.113.10")
}

module "project" {
  source    = "../cloud/project"
  enabled   = var.enable_project
  resources = compact([module.droplet.droplet_urn, module.reserved_ip.urn])
}
