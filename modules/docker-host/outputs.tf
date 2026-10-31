# SPDX-License-Identifier: Apache-2.0
output "instance_id" {
  value = digitalocean_droplet.workload.id
}

output "instance_name" {
  description = "Droplet name: <layer>-<resource_key or region>-docker."
  value       = digitalocean_droplet.workload.name
}

output "droplet_urn" {
  value = digitalocean_droplet.workload.urn
}

output "private_ip" {
  description = "The droplet's VPC address: where the Twingate resources point and the only address Portainer listens on."
  value       = digitalocean_droplet.workload.ipv4_address_private
}

output "size" {
  value = digitalocean_droplet.workload.size
}

output "portainer_port" {
  value = var.portainer_port
}
