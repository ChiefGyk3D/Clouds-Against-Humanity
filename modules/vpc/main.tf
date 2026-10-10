resource "digitalocean_vpc" "this" {
  name     = "${var.layer}-${var.region}-vpc"
  region   = var.region
  ip_range = var.ip_range
}
