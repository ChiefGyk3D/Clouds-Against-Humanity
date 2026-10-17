# firewall (AWS)

Packet filtering for a group of machines. Part of the provider module contract
([design section 5](../../../docs/superpowers/specs/2026-10-16-multicloud-design.md)).
Mocked-provider tests only: this module has never been applied to a real AWS
account.

DigitalOcean answers the three filtering questions with one tag. AWS splits
them: a security group is attached to a machine's network interface, and a rule
names its source or destination as an address range or as another security group.

| Role | Meaning | DigitalOcean object | AWS object |
|---|---|---|---|
| `rule_targets` | What the rules attach to | The tag the firewall applies to (`tags`) | The security group's id. A machine lists it in `vpc_security_group_ids` when it launches. |
| `source_members` | Who may reach the targets, by membership | `source_tags` of the inbound rules | The security group named as the source of an `aws_vpc_security_group_ingress_rule` (`referenced_security_group_id`). Here, this group itself. |
| `destination_members` | What the targets may reach, by membership | `destination_tags` of the outbound rules | The security group named as the destination of an `aws_vpc_security_group_egress_rule`. Here, this group itself. |
| Internet egress | Rules by address range | Outbound rules to `0.0.0.0/0` and `::/0` | `aws_vpc_security_group_egress_rule` to `0.0.0.0/0`: tcp 443, 80, 53 and udp 53, 123, plus `extra_outbound_rules`. IPv4 only; the VPC has no IPv6. |

Contract outputs: `id`, `name`, `rule_targets`, `source_members`, `destination_members`.

## Provider extensions

`vpc_id` (input): a security group belongs to one VPC. Member rules are
`inbound_from_member_rules` and `outbound_to_member_rules`; both name this group
itself, never an address, so only machines wearing the group can use them.

Inbound is deny-all: the group has no inbound rule unless a member rule asks for
one. Every rule is a separate rule resource and the group has no inline
`ingress` or `egress` block. AWS gives a new group one allow-all outbound rule;
the AWS provider removes it when it creates a group in a VPC, so the only egress
is what the module lists. **UNVERIFIED against a live account.** The tests prove
the module declares no every-protocol rule (a protocol outside tcp and udp is
rejected by validation) and no inline rule block; whether the allow-all rule is
really gone is only provable by an apply and `describe-security-group-rules`,
which the phase 4 apply must record.

A security group does not filter Amazon's DNS resolver, DHCP, the instance
metadata service or the time service.
