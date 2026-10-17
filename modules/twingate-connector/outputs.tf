output "droplet_name" {
  value = digitalocean_droplet.connector.name
}

output "droplet_urn" {
  value = digitalocean_droplet.connector.urn
}

output "private_ip" {
  value = digitalocean_droplet.connector.ipv4_address_private
}

output "size" {
  value = digitalocean_droplet.connector.size
}

# The module contract (design section 5): neutral names, the same on every
# provider. droplet_name, droplet_urn, private_ip and size above stay because
# stack 10 uses them.
output "instance_id" {
  value = digitalocean_droplet.connector.id
}

output "instance_name" {
  value = digitalocean_droplet.connector.name
}
