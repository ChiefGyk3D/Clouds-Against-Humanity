# SPDX-License-Identifier: Apache-2.0
# The guard lives here because an output precondition is checked on every plan,
# including a plan that creates nothing (the switch is off).
output "workload_enabled" {
  description = "Whether the workload host is switched on. false means this stack creates nothing."
  value       = var.workload_enabled

  precondition {
    condition     = !var.workload_enabled || try(local.cost.workload_approved, false) == true
    error_message = "workload_enabled needs this stack's cost.json to carry workload_approved = true. It is false until stage 3 is approved in a reviewed change (docs/stages/03-workloads.md)."
  }

  precondition {
    condition     = !var.workload_enabled || length([for r in local.cost.resources : r if r.name == "workload" && r.kind == "droplet"]) == 1
    error_message = "workload_enabled needs exactly one priced droplet entry named workload in this stack's cost.json, so the cost gate sees the host."
  }
}

output "workload_tag" {
  description = "The tag the workload firewall attaches to."
  value       = one(digitalocean_tag.workload[*].name)
}

output "droplet_name" {
  value = one(module.workload[*].instance_name)
}

output "onion_service_enabled" {
  description = "Whether the optional onion service is switched on: true only when both this flag and workload_enabled are true. It never carries the onion address, which only exists on the host."
  value       = var.workload_enabled && var.onion_service_enabled
}

output "workload_web_resource_names" {
  description = "Names of the Twingate resources made for workload_web_ports. Empty when the list is empty or the master switch is off."
  value       = sort([for r in twingate_resource.workload_web : r.name])
}

output "private_ip" {
  description = "The droplet's VPC address, where the two Twingate resources point."
  value       = one(module.workload[*].private_ip)
}
