output "connector_private_ips" {
  value = {
    a = module.connector_a.private_ip
    b = module.connector_b.private_ip
  }
}

output "connector_security_group_id" {
  value = module.connector_firewall.id
}
