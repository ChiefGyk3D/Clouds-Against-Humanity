resource "digitalocean_project" "this" {
  name        = var.project_name
  purpose     = "Service or API"
  environment = "Production"
  description = "Managed by OpenTofu through Spacelift."
}

resource "digitalocean_tag" "baseline" {
  name = "cah-baseline-${var.region}"
}

module "vpc" {
  source   = "../../modules/vpc"
  layer    = "foundation"
  region   = var.region
  ip_range = var.vpc_ip_range
}

module "baseline_firewall" {
  source  = "../../modules/firewall"
  layer   = "foundation"
  region  = var.region
  purpose = "baseline"
  tag     = digitalocean_tag.baseline.name
}
