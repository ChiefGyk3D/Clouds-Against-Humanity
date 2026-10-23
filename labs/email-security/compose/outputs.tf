# SPDX-License-Identifier: Apache-2.0
output "box_fqdn" {
  value = module.dns.box_fqdn
}

output "box_address" {
  value = coalesce(module.reserved_ip.ip_address, module.droplet.ipv4, "none yet")
}
