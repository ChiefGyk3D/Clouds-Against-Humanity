# vpc

A private network for one region. Part of the provider module contract
([design section 5](../../docs/superpowers/specs/2026-10-16-multicloud-design.md)).

| Role | DigitalOcean object | Another provider's object |
|---|---|---|
| The private network | `digitalocean_vpc` | AWS: a VPC plus the subnet, internet gateway and route that make it usable. Azure: a virtual network and subnet. GCP: a VPC network and regional subnet. |
| Address range | `ip_range` | Same idea, different resource arguments. |

Contract outputs (same names on every provider): `id`, `ip_range`, `name`.

## Provider extensions

None. Everything this module takes is part of the contract. A provider that
needs more (an availability zone, a subnet layout) documents it here, in its own
copy of this README, rather than adding it to the shared shape.
