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
    condition     = !var.edge_enabled || try(local.cost.edge_network_approved, false) == true
    error_message = "edge_enabled needs this stack's cost.json to carry edge_network_approved = true. It is false until the stage is approved in a reviewed change (docs/stages/05-edge.md)."
  }
}

output "vpc_id" {
  value = one(digitalocean_vpc.dmz[*].id)
}

output "dmz_tag" {
  description = "The tag the Cloud Firewall attaches to; every edge service droplet carries it."
  value       = one(digitalocean_tag.dmz[*].name)
}

output "transport_tag" {
  value = one(digitalocean_tag.transport[*].name)
}

output "region" {
  value = var.region
}
