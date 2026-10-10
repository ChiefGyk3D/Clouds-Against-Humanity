output "connector_private_ips" {
  value = {
    a = module.connector_a.private_ip
    b = module.connector_b.private_ip
  }
}

output "connector_tag" {
  value = digitalocean_tag.connector.name
}
