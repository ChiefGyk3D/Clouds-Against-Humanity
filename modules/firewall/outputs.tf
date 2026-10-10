output "name" {
  value = digitalocean_firewall.this.name
}

output "inbound_rule_count" {
  value = length(digitalocean_firewall.this.inbound_rule)
}

output "outbound_rule_count" {
  value = length(digitalocean_firewall.this.outbound_rule)
}

# Sorted "<protocol>/<port_range>/<destinations>" descriptors, so tests (and the
# stacks that call this module) can pin the exact outbound rule set. No secrets.
output "outbound_rules" {
  value = sort([
    for r in digitalocean_firewall.this.outbound_rule :
    "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.destination_addresses)))}"
  ])
}
