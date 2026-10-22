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
| Internet egress | Rules by address range | Outbound rules to `0.0.0.0/0` and `::/0`, or to the rule's own `destinations` list | Same, as address-range rules. |

Contract outputs: `id`, `name`, `rule_targets`, `source_members`, `destination_members`.

## Provider extensions

`tag` is the DigitalOcean way to name the targets and the members at once.
Other providers take separate inputs for each role.

`inbound_from_other_tags` and `outbound_to_other_tags` take `[{protocol, port_range, tag}]`
(default empty) to admit or reach droplets carrying a different tag, one rule per entry,
never an address. They are for tags other than the firewall's own (the own tag goes in the `*_tag_rules` lists; the same tag in both is rejected). They render after the existing rules, so a call that leaves them empty
plans exactly as before.

## Narrowing an outbound rule to addresses

`extra_outbound_rules` takes `[{protocol, port_range, destinations, allow_world_destinations}]`.
The last two are optional.

- No `destinations` (unset or empty): the rule goes to `0.0.0.0/0` and `::/0`, exactly as before.
  Every existing call renders the same plan.
- `destinations = [...]`: the rule goes only to the listed IPv4 and IPv6 CIDRs and plain
  addresses. A list of IPv4 entries adds no IPv6 destination, and the reverse. To reach both
  families, list both.
- A `/0` entry (`0.0.0.0/0`, `::/0`, or an unspecified address) inside the list is refused. To say
  the rule really is open to the world, set `allow_world_destinations = true` on that rule; the
  flag is refused on a rule with no `/0` entry, so it cannot sit there unused.
- Entries are validated as addresses or CIDRs, and a repeated entry is refused. Hostnames are not
  accepted: DigitalOcean firewalls take addresses.

```hcl
extra_outbound_rules = [
  { protocol = "tcp", port_range = "5201", destinations = ["203.0.113.0/24", "2001:db8::/32"] },
]
```

Those are documentation ranges (RFC 5737 and RFC 3849); use your own addresses. The check is on the
literal entry: two ranges that together cover everything (`0.0.0.0/1` and `128.0.0.0/1`) pass, so
review a large range as you would a `/0`.
