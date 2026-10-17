locals {
  # Names use resource_key when it is set and region otherwise; the region
  # argument below always takes the real region.
  name_key = var.resource_key != "" ? var.resource_key : var.region
}

resource "digitalocean_vpc" "this" {
  name     = "${var.layer}-${local.name_key}-vpc"
  region   = var.region
  ip_range = var.ip_range
}
