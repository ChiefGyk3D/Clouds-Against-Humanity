output "connector_private_ip" {
  value = module.connector.private_ip
}

output "connector_tag" {
  value = digitalocean_tag.connector.name
}
