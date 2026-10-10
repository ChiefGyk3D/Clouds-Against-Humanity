output "droplet_name" {
  value = digitalocean_droplet.connector.name
}

output "droplet_urn" {
  value = digitalocean_droplet.connector.urn
}

output "private_ip" {
  value = digitalocean_droplet.connector.ipv4_address_private
}

output "remote_network_id" {
  value = twingate_remote_network.this.id
}

output "size" {
  value = digitalocean_droplet.connector.size
}
