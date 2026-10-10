output "name" {
  value = digitalocean_firewall.this.name
}

output "inbound_rule_count" {
  value = length(digitalocean_firewall.this.inbound_rule)
}

output "outbound_rule_count" {
  value = length(digitalocean_firewall.this.outbound_rule)
}

# Sorted "<protocol>/<port_range>/<destinations>" descriptors for the
# address-based outbound rules, so tests (and the stacks that call this module)
# can pin the exact set. Tag-scoped rules are in outbound_tag_rules. No secrets.
output "outbound_rules" {
  value = sort([
    for r in digitalocean_firewall.this.outbound_rule :
    "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.destination_addresses)))}"
    if length(coalesce(r.destination_addresses, [])) > 0
  ])
}

# Sorted "<protocol>/<port_range>/<source tags>" descriptors for the inbound rules.
output "inbound_rules" {
  value = sort([
    for r in digitalocean_firewall.this.inbound_rule :
    "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.source_tags)))}"
  ])
}

# Sorted "<protocol>/<port_range>/<destination tags>" descriptors for the outbound
# rules that reach droplets by tag.
output "outbound_tag_rules" {
  value = sort([
    for r in digitalocean_firewall.this.outbound_rule :
    "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.destination_tags)))}"
    if length(coalesce(r.destination_tags, [])) > 0
  ])
}
