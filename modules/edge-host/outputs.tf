# SPDX-License-Identifier: Apache-2.0
output "name" {
  description = "Droplet name: <layer>-<resource_key or region>-<service>."
  value       = digitalocean_droplet.edge.name
}

output "droplet_id" {
  value = digitalocean_droplet.edge.id
}

output "droplet_urn" {
  value = digitalocean_droplet.edge.urn
}

output "doppler_config" {
  description = "Name of this service's own Doppler config. Nothing is shared between services."
  value       = local.doppler_config
}

output "reboot_time" {
  value = local.reboot_time
}

output "size" {
  value = digitalocean_droplet.edge.size
}

output "reserved_ip" {
  description = "The public address that survives a rebuild."
  value       = digitalocean_reserved_ip.edge.ip_address
}

# What the host firewall was told, as sorted descriptors, so a test and the
# stack can pin the exact set and compare it with the Cloud Firewall's.
output "host_firewall_rules" {
  value = local.host_rule_descriptors
}
