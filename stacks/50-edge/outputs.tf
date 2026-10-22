# SPDX-License-Identifier: Apache-2.0
# The two guards live here because an output precondition is checked on every
# plan, including a plan that creates nothing (the switch is off).
output "edge_enabled" {
  description = "Whether the edge is switched on. false means this stack creates nothing."
  value       = var.edge_enabled

  precondition {
    condition     = !local.overlaps_avoided
    error_message = "vpc_ip_range overlaps the core VPC (core_vpc_ip_range) or a range in reserved_ranges. The edge VPC must overlap neither."
  }

  precondition {
    condition     = var.i2pd_port == null ? true : var.i2pd_port != var.reticulum_port
    error_message = "i2pd_port and reticulum_port must differ: two listeners cannot share a port."
  }

  precondition {
    condition = !var.edge_enabled || (
      length([for r in local.cost.resources : r if r.kind == "droplet" && r.size == var.droplet_size]) == 1 &&
      length([for r in local.cost.resources : r if r.kind == "reserved_ip"]) == 1
    )
    error_message = "edge_enabled needs this stack's cost.json to price exactly one droplet of droplet_size and one reserved_ip. It is empty until the stage is approved and the cost gate can price a reserved IP (docs/stages/05-edge.md)."
  }
}

output "vpc_id" {
  value = one(digitalocean_vpc.dmz[*].id)
}

output "reserved_ip" {
  description = "The edge's public address, or null while the edge is off."
  value       = one(module.edge_host[*].reserved_ip)
}

output "region" {
  value = var.region
}
