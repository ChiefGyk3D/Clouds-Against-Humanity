output "name" {
  value = digitalocean_firewall.this.name
}

output "inbound_rule_count" {
  value = length(digitalocean_firewall.this.inbound_rule)
}

output "outbound_rule_count" {
  value = length(digitalocean_firewall.this.outbound_rule)
}
