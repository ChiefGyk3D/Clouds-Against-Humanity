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
    condition     = !var.workload_enabled || length(local.priced_workload) == 1
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

output "private_ip" {
  description = "The droplet's VPC address, where the two Twingate resources point."
  value       = one(module.workload[*].private_ip)
}
