locals {
  # Names and tags use resource_key when it is set and region otherwise. The
  # region argument of every resource and of the modules stays var.region.
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  # First and last address of an IPv4 CIDR as a number, so two ranges can be
  # compared. OpenTofu has no overlap function. cidrhost(range, -1) is the last
  # address. Invalid entries are caught by the variables' own validation.
  vpc_bounds = [
    for o in [split(".", cidrhost(var.vpc_ip_range, 0)), split(".", cidrhost(var.vpc_ip_range, -1))] :
    (tonumber(o[0]) * 16777216) + (tonumber(o[1]) * 65536) + (tonumber(o[2]) * 256) + tonumber(o[3])
  ]
  reserved_bounds = [
    for c in var.reserved_ranges : [
      for o in [split(".", cidrhost(c, 0)), split(".", cidrhost(c, -1))] :
      (tonumber(o[0]) * 16777216) + (tonumber(o[1]) * 65536) + (tonumber(o[2]) * 256) + tonumber(o[3])
    ]
  ]
  # Two ranges overlap when each starts no later than the other ends.
  overlaps_reserved = anytrue([
    for b in local.reserved_bounds : local.vpc_bounds[0] <= b[1] && b[0] <= local.vpc_bounds[1]
  ])
}

resource "digitalocean_project" "this" {
  name        = var.project_name
  purpose     = "Service or API"
  environment = "Production"
  description = "Managed by OpenTofu through Spacelift."

  # A precondition, not a variable validation: OpenTofu 1.8 (the pinned minimum)
  # cannot compare one variable with another in a validation. It changes no plan.
  lifecycle {
    precondition {
      condition     = !local.overlaps_reserved
      error_message = "vpc_ip_range overlaps a range in reserved_ranges. Pick a range that overlaps none of them."
    }
  }
}

resource "digitalocean_tag" "baseline" {
  name = "cah-baseline-${local.resource_key}"
}

module "vpc" {
  source       = "../../modules/vpc"
  layer        = "foundation"
  region       = var.region
  resource_key = var.resource_key
  ip_range     = var.vpc_ip_range
}

module "baseline_firewall" {
  source       = "../../modules/firewall"
  layer        = "foundation"
  region       = var.region
  resource_key = var.resource_key
  purpose      = "baseline"
  tag          = digitalocean_tag.baseline.name
}
