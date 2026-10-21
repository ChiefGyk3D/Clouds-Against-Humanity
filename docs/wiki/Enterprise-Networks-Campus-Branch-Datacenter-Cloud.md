# Enterprise networks: campus, branch, data center and cloud

> **Orientation, not a design guide: verified claims dated.** Claims checked against a vendor or standards page carry the date they were checked (2026-10-16) and the source in the claims register at the bottom. Everything else is general industry knowledge or marked UNVERIFIED. Nothing here has been built in this repository; the enterprise side of every table is a description, not a deployment.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Networking basics for this project](Networking-Basics-for-This-Project.md) (addresses, CIDR, ports, stateful firewalls), [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) and [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md).

This repository has one network: a VPC with a range of 256 addresses, two small machines in it, and a firewall that lets nothing in. A company has hundreds of networks of several different kinds, and most of the work of a network engineer is deciding how those networks join, what may cross between them, and how anyone can tell. This page names the shapes and the vocabulary. It is the page to read before a job interview that says "hybrid network" in the description.

## The shapes of a corporate network

| Shape | What it is | Typical contents | Who cares about it |
|---|---|---|---|
| **Campus** | A large site with many floors or buildings, usually one organization's own | Access switches in wiring closets, a distribution or core layer above them, wireless access points, printers, phones, badge readers | Network engineers, help desk, physical security |
| **Branch** | A small site (a shop, a clinic, a regional office) | A router or firewall, maybe one switch and some wireless, a link to somewhere bigger | Network engineers; often managed centrally because nobody on site is a network person |
| **Data center** | A room or building of servers the organization runs, or rents space in | Racks, top-of-rack switches, a spine-and-leaf fabric, storage networks, firewalls and load balancers at the edge | Network, systems and storage engineers |
| **Colocation (colo)** | Someone else's data center building where you rent racks, power and cooling and bring your own equipment | Your hardware, plus cross-connects to carriers and clouds | The same people, plus procurement |
| **Cloud network** | A VPC (AWS, GCP, DigitalOcean) or VNet (Azure): software-defined network inside a provider | Subnets, route tables, security groups or firewalls, gateways | Cloud and platform engineers |
| **Remote worker** | One person on their own network, anywhere | A laptop and a client | Everyone, because this is now most people |

The **campus** design most often described is three layers: **access** (where devices plug in), **distribution** (where access switches aggregate and policy is applied) and **core** (fast transport between distributions). Smaller sites collapse distribution and core into one layer. In a data center the common shape is **spine and leaf**: every leaf switch connects to every spine switch, so any server is the same small number of hops from any other. Both are general industry descriptions; vendors publish their own reference designs that differ in detail.

This project is a cloud network and, in the language above, nothing else.

## How the shapes connect

Joining networks is a separate problem from reaching one resource as a person. The same few tools show up everywhere.

| Link type | What it is | Encrypted by itself? | Typical use |
|---|---|---|---|
| **MPLS** | A carrier sells you a private, routed service between your sites over their network | Not by default; check the contract | Older and larger WANs, predictable quality |
| **Internet VPN (IPsec)** | An encrypted tunnel across the public internet between two gateways | Yes: that is its purpose | Branch to data center, site to cloud |
| **GRE tunnel** | A way to wrap packets so two routers behave as if directly cabled | **No.** Often paired with IPsec | Carrying routing protocols or multicast across a path |
| **SD-WAN** | Software that manages many links per site (internet, LTE, MPLS) and steers traffic by policy | Typically uses IPsec between sites; verify per product | Replacing or supplementing MPLS at many branches |
| **Dedicated cloud link** | A physical circuit from your network (or colo) to a cloud provider: AWS Direct Connect, Azure ExpressRoute, Google Cloud Interconnect | A private circuit is not automatically encrypted; add encryption if you need it | Steady heavy traffic, lower and steadier latency than the internet |
| **Managed site-to-site VPN** | The cloud provider's own IPsec endpoint | Yes | Quick, cheap first link into a cloud |
| **Transit hub** | A central router in the cloud (a transit gateway, a virtual WAN hub) that many VPCs and links attach to | Depends on the attachment | Avoiding a mesh of point-to-point links |

Two ideas explain most of the design arguments.

**Mesh versus hub-and-spoke.** Connecting every network to every other grows quickly: ten networks need 45 pairwise links, a hundred need 4,950. A hub means each network connects once, to the hub, and policy and inspection live in one place. The price is that the hub becomes critical, and traffic between two spokes takes an extra hop.

**Routing is a negotiation.** Networks that connect have to agree which addresses live where. Inside one organization that is done with a routing protocol; between organizations and with the big clouds it is usually **BGP**. Two networks that use the same private range cannot be joined without translation tricks, which is why [the VPC range here is a demo value](Fork-Private-Stacks-and-the-Pipeline.md#step-2-which-values-are-demo-values) and why large companies keep an address plan (IPAM) as a record of who owns which block.

## Segmentation: how a network is divided on purpose

A **flat network** is one where any device can reach any other. It is easy to build, and it is the reason a single infected laptop can end up with a path to the payroll database. Segmentation is the family of techniques that make the network less flat.

| Technique | What it does | Scale |
|---|---|---|
| **VLAN** | Splits one physical switch network into separate Layer 2 networks, tagged with a number | Within a site |
| **VRF** | A separate routing table on one router, so two networks can even reuse the same addresses | Across a site or WAN |
| **Firewall zones** | Interfaces grouped as "inside", "outside", "DMZ" and so on, with rules between zones | At the boundary between segments |
| **DMZ / edge** | A segment for things that must be reachable from the internet, kept apart from the interior | Between internet and inside |
| **Management network** | A separate network for the administrative interfaces of devices, reachable only from controlled places | Whole estate |
| **Micro-segmentation** | Rules at each workload (host firewall, cloud security group, agent) instead of at a network boundary | Per workload |
| **NAC / 802.1X** | Network access control: a device or person authenticates **before** the port or wireless network gives them a place on the network, and the result chooses their VLAN or policy | Per port or wireless user |

Two of these are worth a closer look because you have already met their cousins.

- The [baseline firewall here](DigitalOcean-Network-and-Firewalls.md#two-firewalls-layered-by-tag) is micro-segmentation in a small form: the rule is about a **tag** on a workload, not about a subnet. Cloud security groups and tags are why micro-segmentation is more practical in cloud than on physical switches.
- A DMZ is the opposite design to this project's. This project has **no** exposed segment. An enterprise often has public services (a website, a mail gateway) and so needs somewhere to put them where a compromise does not hand over the interior.

## North-south and east-west

**North-south** traffic crosses the boundary of a network: in from the internet, or out to it. **East-west** traffic stays inside, between servers or services. Old security spent its effort on north-south (a strong perimeter), and the common finding in incident reports is that once something is inside, east-west is wide open. Zero trust architecture, as the NIST publication describes it, moves the defenses from the perimeter toward users, assets and resources, and says that location on a network does not by itself grant trust (see the register). That is the reasoning behind [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md).

Here, north-south inbound traffic is zero by design. East-west is two connectors that may SSH to each other, and nothing else.

## Services every network shares

These are boring until they break, and then everything looks broken at once.

| Service | What it does | What happens when it fails |
|---|---|---|
| **DNS** | Turns names into addresses; an internal zone holds private names | "The network is down" is often "DNS is down" |
| **DHCP** | Hands out addresses and settings to devices | New devices cannot connect; existing ones keep working until their lease ends |
| **NTP** | Keeps clocks in agreement | Logs do not line up, certificates look expired, Kerberos-style logins fail |
| **PKI** | Issues and revokes certificates so devices, servers and people can prove who they are | Expired internal certificates are a classic cause of an outage on a quiet morning |
| **Directory / identity** | The list of people and devices | Nobody can sign in |

This project has the minimum: the baseline firewall allows outbound DNS and NTP on its five narrow rules, and the cloud provides DHCP-like address assignment itself.

## Proxies, secure web gateways, SASE and SSE

Outbound traffic is controlled too. A **forward proxy** sits between users and the internet and can log or block. A **secure web gateway (SWG)** is the modern version: it inspects web traffic by category, malware and policy. **SASE** (secure access service edge) is an industry term for combining wide-area networking (SD-WAN) with security delivered from the cloud; **SSE** (security service edge) is the security half of that without the WAN part. The [landscape page](Small-Example-Enterprise-Landscape.md#remote-access-ztna-sse-and-the-vpn) names Zscaler, Netskope and Palo Alto's Prisma Access as examples. The definitions are industry usage and vendors market overlapping bundles, so check what a given product actually includes before comparing two of them.

## Why flat networks fail

1. **Lateral movement.** An attacker who lands on one machine tries to reach the next. Without internal boundaries, the first foothold is the whole network.
2. **Blast radius.** A worm, ransomware or a misconfigured backup job spreads at the speed of the network.
3. **Unreadable rules.** If everything can talk to everything, nobody knows what depends on what, and so nobody dares tighten it.
4. **No evidence.** With no boundaries there are no choke points to log. You cannot answer "did anything talk to the payroll server last Tuesday?"

Segmentation is not magic either. Each boundary is a rule set someone must own, review and test, and a segmented network with unexplained exceptions is a flat network with extra steps.

## Worked comparison: one VPC with two connectors versus a hub-and-spoke landing zone

| Question | In this project | In an enterprise |
|---|---|---|
| How many networks? | One VPC, `10.78.0.0/24`, one region | Many VPCs or VNets across many accounts, regions and clouds, each with an owner |
| How do networks join? | They do not; nothing to join | Each spoke attaches to a transit hub; the hub connects to on-premises by dedicated link and VPN |
| Where is traffic inspected? | At each droplet's firewall, default deny inbound | Also at the hub: a shared firewall or inspection layer that all spoke-to-spoke and spoke-to-internet traffic passes |
| Who may reach a server? | One named group, via Twingate, on one port | A mix: ZTNA for people, private links for systems, rules written as groups and tags |
| Address plan | One range, checked by hand against the home network | An address plan (IPAM), non-overlapping blocks assigned per spoke |
| Shared services | Provider DNS and NTP, nothing else | Central DNS resolvers, a directory, PKI, logging and monitoring in a shared-services spoke |
| Outbound to the internet | Baseline: five narrow rules. The connectors also carry the connector firewall, which allows outbound TCP 30000 to 31000 and UDP on any port to any destination (Twingate needs it for peer-to-peer), so their effective outbound is broader than the baseline. Direct, no proxy | Through a proxy or SWG, often via the hub |
| Change | A pull request, plan, human confirm | The same, often plus a change ticket, a network team's review and a maintenance window |
| Cost | About 12 dollars a month for the connectors | Link fees, hub data-processing charges and licenses are a real budget line |
| What breaks first | An expired token or a rule too narrow | Overlapping ranges, an asymmetric route, a rule nobody can explain, a certificate nobody renewed |

A hub-and-spoke landing zone is the **same four ideas** as this repository, repeated: a boundary around each workload, default deny, a way in that is not an open port, and everything described as code. It adds two: a place where policy is centralized, and an address plan so that joining stays possible. If this project grew a second region, the first step would be the same modules again (see [Multiple sites and identity](Multiple-Sites-and-Identity.md)); the hub only appears when the number of networks makes pairwise links impractical.

## Predict, then check

Answer these before reading the reference answers.

1. A branch office has a router and an internet line. Headquarters wants all of the branch's traffic to reach a data center securely. Name two ways, and say which one needs extra work to be encrypted.
2. A company has 12 VPCs and wants any VPC to reach any other. How many point-to-point links does a full mesh need, and how many attachments does a hub need?
3. Two networks to be joined both use `10.0.0.0/16`. What is the first problem and what are two ways out?
4. A contractor's laptop is plugged into a conference-room port. With 802.1X in place, what happens before the laptop gets any network access?
5. In this repository, which of the segmentation techniques above is already present, and which is deliberately absent?

### Reference answers

1. An IPsec VPN tunnel from branch gateway to the data center (encrypted by design), or a carrier private circuit such as MPLS (private, but not automatically encrypted, so encryption is an add-on that depends on the contract). GRE alone is not encryption either.
2. A full mesh of 12 networks needs 12 x 11 / 2 = 66 links; a hub needs 12 attachments, one per VPC.
3. Routing cannot tell them apart. Options: renumber one side (the clean answer, but costly if hosts are static), or translate addresses (NAT) at the join, which works but complicates troubleshooting. Prevention is an address plan.
4. The port allows only authentication traffic until the laptop (or the person) proves who it is to an authentication server; the result may then place it on a guest VLAN, a corporate VLAN, or nowhere.
5. Present: micro-segmentation by tag (the firewalls attach to workload tags) and default deny. Absent on purpose: VLANs, VRFs, a DMZ, NAC, a hub; there is one network and nothing public to isolate.

## Try it yourself

- Draw this project's network the way an enterprise diagram would: a spoke with a firewall zone, an "internet" cloud, and a Twingate controller outside. Mark every arrow north-south or east-west.
- Pick a private range for a pretend second region and write down the rule that would stop you picking an overlapping one.
- Look up the "landing zone" or "hub and spoke" reference architecture on one cloud provider's own architecture center. List what it has that the diagram above does not, and decide which items would still be overkill at two machines.
- Read the glossary entries for the terms in the segmentation table and write one sentence for each in your own words.

## Claims register

Status is one of: `Verified <date>` (checked against the named source on that date), `General knowledge` (widely held industry usage, not checked here), or `UNVERIFIED`.

| Claim | Status | Source |
|---|---|---|
| AWS Direct Connect links your network to a Direct Connect location over Ethernet fiber, with virtual interfaces to public services or to a VPC, bypassing internet service providers in the path | Verified 2026-10-16 | https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html |
| Direct Connect has private, public and transit virtual interface types, and requires BGP on the customer device | Verified 2026-10-16 | https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html |
| NIST SP 800-207 (August 2020) describes zero trust as moving defenses from fixed network perimeters toward users, assets and resources, and says network location does not by itself grant trust | Verified 2026-10-16 | https://csrc.nist.gov/pubs/sp/800/207/final |
| Azure ExpressRoute and Google Cloud Interconnect are the Azure and Google equivalents of a dedicated cloud link | General knowledge | not checked |
| A private circuit is not automatically encrypted | General knowledge | not checked; the landscape page makes the same point |
| Campus access/distribution/core and data center spine-and-leaf descriptions | General knowledge | not checked |
| SASE and SSE definitions | General knowledge | industry usage; vendors differ |
| Full mesh of n networks needs n(n-1)/2 links | General knowledge | arithmetic |
| SD-WAN products use IPsec between sites | UNVERIFIED | varies by product |

Next: [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md). Back to the [Reading order](Reading-Order.md).
