# vpc (AWS)

A private network for one region, made usable. Part of the provider module
contract
([design section 5](../../../docs/superpowers/specs/2026-10-16-multicloud-design.md)).
Mocked-provider tests only: this module has never been applied to a real AWS
account.

| Role | DigitalOcean object | AWS object |
|---|---|---|
| The private network | `digitalocean_vpc` | `aws_vpc`, plus the pieces that make it usable: `aws_subnet`, `aws_internet_gateway`, an explicit `aws_route_table`, an `aws_route` for `0.0.0.0/0` and an `aws_route_table_association`. |
| Address range | `ip_range` | `ip_range` (the VPC's `cidr_block`; the one subnet uses the same range). |

Contract outputs (same names on every provider): `id`, `ip_range`, `name`.

## Provider extensions

`subnet_id` (output): an AWS machine launches into a subnet, not into the VPC,
so the connector module takes this. `availability_zone` (optional input): a
subnet lives in exactly one zone; null lets AWS choose. The subnet is public
(its route table sends `0.0.0.0/0` to the internet gateway) because the textbook
private subnet needs a NAT gateway, which costs more than the whole stack
([cost lesson](../../../docs/wiki/Provider-AWS-Cost-Lesson.md)). It does not hand
out public addresses by itself (`map_public_ip_on_launch` is off), and IPv6 is
off. The module creates no NAT gateway and no elastic address.

`ip_range` must be the network address (`10.0.0.0/24`, not `10.0.0.1/24`);
AWS rejects anything else.

The VPC's default security group is managed with no rules (`aws_default_security_group`),
so AWS's self-allow and allow-all-outbound defaults are removed. **UNVERIFIED
against a live account.** What stays as AWS made it: the default network ACL
(allow all, both directions). Replacing it needs stateless return-path rules
and is not done; the security group is this project's filter.

## Phase 4 acceptance record

Mocked tests cannot show what AWS does. The first real apply must record each
of these, with the command output kept with the apply notes, before the module
is called verified:

- The VPC's default security group has no rules (`describe-security-group-rules` filtered to it).
- The subnet's route table is the explicit one, with the `0.0.0.0/0` route to the internet gateway, and the subnet does not use the main table.
- The default network ACL is still allow-all, as documented.
