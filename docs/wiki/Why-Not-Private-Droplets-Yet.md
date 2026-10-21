# Why not private droplets (yet)

> **Status: unverified draft.** The figures come from this repository's own notes (the [phase 0 findings](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-findings.md), read 2026-10-16, and the [edge design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-19-edge-dmz-design.md), read 2026-10-19) and will change. Nothing here was applied in a real account. Not yet reviewed by the maintainer. Read [Networking basics](Networking-Basics-for-This-Project.md), [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) and [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first.

A common first reaction to this project's design is: "Why do the connector droplets have public IP addresses? Shouldn't servers like these be private?" It is a fair question. This page gives the honest answer: it is mostly about money, the exposure ends up the same, and there are real tradeoffs.

## The two designs

- **What this project does:** each droplet has a public IP address (DigitalOcean gives every droplet one and you cannot remove it). The baseline Cloud Firewall attached to it has **zero inbound rules from the internet**. The connector droplets add one narrow exception, written in `stacks/10-access/main.tf`: TCP 22 between the connectors, allowed only from the connector tag, never from an address range. So the accurate wording is "zero inbound from the internet", not "zero inbound at all". Nothing on the internet can start a connection to the droplet, and the droplet itself makes outbound connections, for example to Twingate.
- **The "private droplet" alternative:** the droplet has only a private address inside the VPC, and a **NAT gateway** (a shared exit door) lets it reach the internet outbound. In plain terms, NAT lets many private machines share one public address for outbound traffic.

Both designs aim at the same goal: nothing from the internet can connect in. They differ in whether the machine has a public address at all.

## Cost: the NAT gateway costs more than the whole budget

This project has a hard monthly ceiling of $30 (see [How this project is planned](How-This-Project-Is-Planned.md) and the [Roadmap](Roadmap.md)). Stage 3 already sits at $29 in the plan.

| Option | What it costs | Source |
|---|---|---|
| Public IP on each droplet, firewall with no inbound rules from the internet | Not priced in this project's notes. Whether the plan carries a separately billed public IPv4 is UNVERIFIED (edge design, section 9); no number is given | Edge design, section 9 |
| DigitalOcean NAT gateway | $40.00 per increment, 100 GiB included | Edge design, section 9, DigitalOcean VPC pricing page read 2026-10-19 |
| AWS NAT gateway, for comparison | $0.045/h = $32.85 a month, plus $3.65 for its address, plus $0.045/GB: at least $36.50 a month | Phase 0 findings, section 4, list prices read 2026-10-16 |
| AWS public address per VM, for comparison | $0.005/h each, $3.65 a month | Phase 0 findings, section 4 |

A NAT gateway at $40 a month is more than the entire $30 ceiling, so it cannot fit at all. On AWS and Azure the findings say the same thing: the cheapest design with no inbound from the internet is a public address with no inbound rules, "because a NAT gateway costs more than the whole ceiling".

One cloud is the exception: on GCP, Cloud NAT is cheaper than external addresses at low traffic (about $5.69 a month for two VMs, against $3.65 each for addresses), until roughly 36 GiB a month of processed traffic. That is why the answer is "it depends on the cloud", not "NAT is always bad".

## Exposure: the firewall gives the same result

People worry that a public address means a public target. What matters is whether anything answers. A stateful firewall with no inbound rules from the internet drops every unsolicited packet before it reaches the machine. The droplet's own connections, such as the one to Twingate, are allowed back in as replies, because the firewall remembers that the droplet started them. Seen from the internet, the public address and a private address behave the same way: nothing opens a connection to it.

This is also why the project checks it from the outside: an external zero-open-ports check, and a plan policy (`.spacelift/policies/plan.rego`) that allows inbound rules on core tags only when they are scoped to a tag, and denies any rule that is open to the whole internet or not scoped to a tag. The design relies on the firewall being right, so it tests the firewall.

## The honest tradeoffs

A public address is not identical to a private one. What you give up:

- **One more thing that has to stay correct.** With a private droplet, a mistaken firewall rule still leaves the machine unreachable, because there is no route in. With a public address, a mistaken rule (say `0.0.0.0/0` on a port) really does expose the machine. This project answers with rules written against tags rather than addresses, policy tests and an external check, but that is a control you must keep running, not a property you get for free.
- **The address is visible.** Scanners will find the address and see that it answers nothing. That is noise, not an attack, but it shows up in logs.
- **IPv6 needs checking too.** An open IPv6 rule is the classic way to undo a "no inbound" design; the Stage 1 hardening list includes an IPv6 check.
- **No stable outbound address.** NAT would give a single, fixed outbound address you could allow-list elsewhere. Without it, outbound traffic comes from each droplet's own address, which changes when a droplet is rebuilt.
- **Droplet Console (open question).** The Roadmap says a NAT gateway design removes the Droplet Console, but the edge design records that as unverified for private droplets ("I did not verify those three"). Whether private droplets keep console access is therefore an open question, not a settled loss.
- **Compliance.** Some rules say workloads must not have public addresses at all. This project has no such rule, but a company copying it might.

## What would change the answer

The Roadmap already names when to revisit this: when the ceiling passes roughly $75 to $80, when a static egress IP is needed, or when a compliance reason appears. Two parts of the plan bear on it directly:

- **The edge (DMZ) phase.** It adds a deliberately public host in a VPC of its own, with inbound ports open on purpose. That host is a different case from the connectors, which take no inbound from the internet; the edge design keeps the connectors that way and puts the public services somewhere separate. Note the edge phase's ceiling is $35 (ruled 2026-10-19, nothing approved to spend yet), which still does not buy a $40 NAT gateway. The design's own NAT figure is the same $40 increment.
- **A ceiling raise.** The ceiling can only rise on purpose, in a reviewed change. If it passed the roughly $75 to $80 range the Roadmap names, private-only droplets behind NAT become affordable and worth another look.

## What to take away

- A public address plus a firewall with no inbound rules from the internet gives the same "nothing connects in" result as a private droplet. Whether the public IPv4 carries its own charge is UNVERIFIED, so no figure is claimed.
- A NAT gateway ($40 a month on DigitalOcean) costs more than this project's whole $30 ceiling.
- The tradeoff is real: you rely on the firewall staying correct, so the project tests it from the outside.

Back to [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md), [How money works in the cloud](How-Money-Works-in-the-Cloud.md) or the [Roadmap](Roadmap.md).
