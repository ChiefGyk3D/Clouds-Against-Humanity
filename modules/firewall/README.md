# firewall

Packet filtering for a group of machines. Part of the provider module contract
([design section 5](../../docs/superpowers/specs/2026-10-16-multicloud-design.md)).

Every cloud's filtering answers three questions. DigitalOcean answers all three
with one tag; the others split them, so the contract names the roles separately.

| Role | Meaning | DigitalOcean object | Another provider's object |
|---|---|---|---|
| `rule_targets` | What the rules attach to | The tag the firewall applies to (`tags`) | AWS: the security group attached to an interface. Azure: a network security group on a subnet or interface. GCP: a network tag or service account the rule targets. |
| `source_members` | Who may reach the targets, by membership | `source_tags` of the inbound rules: this firewall's own tag (`inbound_from_tag_rules`) and any other tags (`inbound_from_other_tags`) | AWS: another security group as the rule's source. Azure: an application security group. GCP: a source tag or service account (ingress only). |
| `destination_members` | What the targets may reach, by membership | `destination_tags` of the outbound rules: this firewall's own tag (`outbound_to_tag_rules`) and any other tags (`outbound_to_other_tags`) | AWS: another security group as the destination. Azure: an application security group. GCP: not available, egress destinations are address ranges only. |
| Internet egress | Rules by address range | Outbound rules to `0.0.0.0/0` and `::/0` | Same, as address-range rules. |

Contract outputs: `id`, `name`, `rule_targets`, `source_members`, `destination_members`.

## Provider extensions

`tag` is the DigitalOcean way to name the targets and the members at once.
Other providers take separate inputs for each role.

`inbound_from_other_tags` and `outbound_to_other_tags` take `[{protocol, port_range, tag}]`
(default empty) to admit or reach droplets carrying a different tag, one rule per entry,
never an address. They are for tags other than the firewall's own (the own tag goes in the `*_tag_rules` lists; the same tag in both is rejected). They render after the existing rules, so a call that leaves them empty
plans exactly as before.
