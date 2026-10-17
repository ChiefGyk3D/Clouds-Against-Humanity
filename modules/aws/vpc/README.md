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
