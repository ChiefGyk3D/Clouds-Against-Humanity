# Azure: the same four pieces

> **Status: unverified draft.** Written 2026-10-16 from Microsoft's documentation and public price API (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md); most claims were read again on the same day, and what is still unconfirmed is marked UNVERIFIED). **No Azure version of this project has been built yet.** The resource lists below are a teaching map of what such a build would need, not code in this repository, and the real build may differ. Resource type names are the usual OpenTofu `azurerm` names from memory of that provider, not checked against its current documentation. Never applied, and not reviewed by anyone who runs Azure: corrections are welcome on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22).

Read [Why the clouds differ](Why-the-Clouds-Differ.md) and [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) first, and skim [the AWS version of this page](Provider-AWS-The-Same-Four-Pieces.md) if you want the comparison. This page walks the four pieces that this project builds on DigitalOcean (a private network, a firewall, a machine, an identity for the machine), points at the DigitalOcean file where each lives, and says what you would build on Azure instead and why it is not a one-line rename.

The method is the exercise: for each piece, **read the DigitalOcean file, predict the Azure resources, then check your list against the reference at the bottom of the piece.**

## Piece 1: the private network

**On DigitalOcean.** `modules/vpc/main.tf` is one resource, `digitalocean_vpc`, with a name, a region and an address range. Droplets reach the internet through their own public interfaces, which DigitalOcean supplies without any routing for you to build.

**On Azure.** A **virtual network** is a regional private network with one or more **subnets** inside it. Both span all availability zones of the region, so you do not split them by zone. The virtual network itself costs nothing (Microsoft's virtual network overview, read 2026-10-16). Two differences from AWS are worth seeing:

- **There is no internet gateway or route table to build.** Azure routes traffic between subnets and to the internet by default. What you have to think about is not "is there a path" but "what gives this machine its outbound address", which is the next section.
- **Everything lives in a resource group**, a container you create first. That is the thing DigitalOcean's "project" and AWS's "account" are closest to, and you create it as a resource.

### The outbound-access trap (re-verified 2026-10-16)

This is the part of Azure most likely to teach you something that is already out of date. Until recently, a VM in a virtual network with no explicit outbound method still got **default outbound access**: Azure quietly gave it an outbound public address, owned by Microsoft and liable to change without notice. Microsoft is retiring that. The default outbound access page (Microsoft Learn, updated 2026-09-10, read 2026-10-16) says:

- **For the API version released after 2026-03-31, subnets in *new* virtual networks have `defaultOutboundAccess` set to `false` by default** (private subnets). A VM there cannot reach the internet unless you give it an explicit outbound method. The Azure portal already defaulted to private subnets.
- **Earlier API versions keep the old behaviour.** The page names ARM templates and "tools like Terraform that can specify older versions". So the same code can give you a private subnet or an open one depending on which API version the tool is using, with no change you can see in the code.
- **Existing virtual networks are not changed**, and Microsoft says this is not a blanket shutdown.
- The supported explicit methods are: a NAT gateway on the subnet (recommended for most cases), a Standard load balancer with outbound rules, **a Standard public IP on the VM's network interface**, or a firewall or appliance reached by a user-defined route.
- To change a subnet for machines that already exist, you must **stop and deallocate** them for the change to reach their network interface.

Microsoft's own pages are not all the same age. The virtual network overview (updated 2026-02-13) still says "all resources in a virtual network can communicate outbound with the internet, by default." That is the old rule. When two pages disagree, check the date, and the default outbound access page (2026-09-10) is the newer.

**What this means for this project.** The connectors only make outbound connections (Twingate's documentation lists TCP 443, TCP 30000-31000 and UDP/QUIC outbound, read 2026-10-16). The cheapest build gives each connector a Standard public IP on its network interface with no inbound rule open to the internet. A public IP on the NIC *is* an explicit outbound method, so the build works whichever way the default goes. The trap is leaving the choice to the default: a connector with no explicit method works on an old API version and **silently has no outbound path on a new one**, and a connector that cannot reach out looks like a Twingate problem, not a network one. So the build should (1) set the subnet's default outbound access explicitly instead of relying on the tool's default, and (2) attach the explicit method. **UNVERIFIED:** the exact name of the argument for this on the `azurerm` subnet resource in your provider version. Look it up before you rely on it.

**Why it matters.** DigitalOcean gave outbound access for free, AWS needed a gateway, a route and an address, and Azure used to give it silently and is now changing that. Three clouds, three different default answers to "can this machine reach out?", and one of them changed this year.

**Predict, then check.** List the Azure resource types you would need to replace `modules/vpc` and to make the connectors able to reach out. Include the one Azure makes you create first, and say what you would set on the subnet.

*Reference (one reasonable answer): a resource group, a virtual network, a subnet with default outbound access explicitly set to false, and a Standard public IP associated with each connector's network interface (the network interface and public IP belong to Piece 3). No gateway and no route table are needed for this design.*

## Piece 2: the firewall

**On DigitalOcean.** `modules/firewall/main.tf` makes a cloud firewall that applies to every droplet carrying a tag, allows nothing in by default, and lists explicit outbound rules. It is attached **by tag, at creation**, so there is no moment when a new droplet is unprotected.

**On Azure.** The filter is a **network security group (NSG)**. It is associated with a **subnet** or with a **network interface** (Microsoft's documentation shows both). The details that matter, from the NSG overview (read 2026-10-16):

- **Rules have a priority from 100 to 4096.** The lowest number is processed first, and the first match stops processing. You cannot have two rules with the same priority and direction.
- **Stateful.** A reply to allowed traffic is allowed without a rule. Changing or removing a rule only affects *new* connections; an existing SSH session survives the rule that allowed it being deleted.
- **Default rules exist in every NSG and cannot be removed**, only overridden by a rule with a lower number:

  | Direction | Name | Priority | What it does |
  |---|---|---|---|
  | Inbound | AllowVNetInBound | 65000 | Allow from the virtual network to the virtual network |
  | Inbound | AllowAzureLoadBalancerInBound | 65001 | Allow from the Azure load balancer |
  | Inbound | DenyAllInbound | 65500 | Deny everything else |
  | Outbound | AllowVnetOutBound | 65000 | Allow to the virtual network |
  | Outbound | AllowInternetOutBound | 65001 | Allow to the internet |
  | Outbound | DenyAllOutBound | 65500 | Deny everything else |

- **The trap: traffic from inside the virtual network is allowed by default.** The internet cannot reach the connectors (DenyAllInbound), but one connector can reach the other, and so can anything else you later put in the same virtual network, because AllowVNetInBound sits above the deny. On DigitalOcean the firewall allows nothing in unless a rule says so. **On Azure, "no inbound from the internet" is the default and "no inbound from the neighbours" is something you add.** Isolating the two connectors from each other needs an **explicit deny with a priority number lower than 65000**.
- **Application security groups (ASGs)** group network interfaces so a rule can name an application tier instead of addresses. An ASG is attached by making a NIC a member. All NICs in an ASG must be in the same virtual network, and a rule can name only one ASG as its source and one as its destination (you cannot list several ASGs or several service tags in one rule). Microsoft's own example uses exactly the pattern this project needs: an allow rule from one ASG to another at a low priority number, and a deny-all rule just below it, "because the AllowVNetInBound default security rule allows all communication between resources in the same virtual network."
- **Standard public IPs are closed by default.** A Standard SKU public IP is "secure by default": closed to inbound traffic until an NSG allows it. Basic SKU public IPs, which were open by default, were retired on 2025-09-30. So a Standard public IP with an NSG that has no allow rule is the Azure form of "an address that nothing can use to get in."
- **What an NSG does not filter.** The platform's DHCP, DNS, instance metadata (IMDS) and health-monitoring services use two Microsoft-owned addresses (168.63.129.16 and 169.254.169.254), and "by default these services aren't subject to the configured network security groups". You can override that with deny rules on specific service tags. This is the same lesson as the metadata service on AWS: a network filter does not protect what sits beside the network.
- **Cost.** **UNVERIFIED:** the Microsoft pages read here mention no charge for NSGs or ASGs, but the retail price API was not searched for one, so the cost lesson counts them as zero without proof.

**UNVERIFIED:** whether an NSG on a *subnet* filters traffic between two machines in that *same* subnet. The documentation read here shows subnet-to-subnet examples and a NIC-level case, and does not say. Do not assume it either way: test it (see the exercises), or associate the NSG with each network interface, which the documentation does show.

**Why it matters.** The module in this repository takes a single `tag`. On Azure the equivalent splits into three decisions: what the NSG is attached to (subnet or NIC), who is allowed (source, destination, ASG or service tag), and the priorities, which an AWS or DigitalOcean user has never had to order.

**Predict, then check.** The two connectors must be able to reach each other on SSH and nothing else may reach them, including a third machine someone adds later to the same virtual network. Write the rules (direction, priority, source, destination, port, action) you would add to the NSG. Then say what the default rules already do for you.

*Reference (one reasonable answer): inbound, priority 100, source the connector ASG, destination the connector ASG, TCP 22, allow; inbound, priority 200, source VirtualNetwork, destination any, any port, deny. The deny is above AllowVNetInBound (65000), so only the connectors' own rule gets through. The default DenyAllInbound already refuses everything from the internet, so you add no internet rule at all. Outbound the defaults allow internet and virtual network traffic, which the connectors need to reach Twingate; a project that wants explicit outbound rules, as the DigitalOcean one does, would add allow rules and an outbound deny below them. Priorities 100 and 200 are arbitrary, any numbers 100 to 4096 in that order work.*

## Piece 3: the machine

**On DigitalOcean.** `modules/twingate-connector/main.tf` creates a droplet from an Ubuntu image, in the VPC, with an SSH key, and passes a boot script (cloud-init) that installs and hardens the Twingate connector.

**On Azure.** A **Linux virtual machine** created from an Ubuntu image, with the same cloud-init data. Compared with DigitalOcean it is several objects, not one:

- **A network interface (NIC)** is its own resource. The VM does not attach to a subnet directly. The NIC is in the subnet, holds the private address, is what the NSG or ASG attaches to, and is what the public IP is associated with.
- **A public IP** is its own resource. Use the **Standard SKU, static**. As of 2026-10-16, a Standard IPv4 address costs $0.005 an hour (about $3.65 a month) in East US from the retail price API. IPv6 is free. Basic public IPs were retired on 2025-09-30.
- **The OS disk** is a separate billed object (managed disk). **UNVERIFIED:** the default size and disk type for the Ubuntu image the portal or OpenTofu chooses. The cost lesson assumes a 32 GiB Standard SSD; a Premium SSD would cost more.
- **Size and architecture.** Prices are East US, pay-as-you-go, non-Windows, from the retail API on 2026-10-16:

  | Size | vCPU | Memory | $/hour | Notes |
  |---|---|---|---|---|
  | `Standard_B2pts_v2` | 2 | 1 GiB | 0.0084 | Arm64 (Ampere Altra). Cheapest here. |
  | `Standard_B2ats_v2` | 2 | 1 GiB | 0.0094 | AMD x86. |
  | `Standard_B2ts_v2` | 2 | not read | 0.0104 | Intel x86. |
  | `Standard_B1s` | 1 | 1 GiB | 0.0104 | **End of Life** series (Microsoft, 2026-09-27). Do not use. |
  | `Standard_B1ms` | 1 | 2 GiB | 0.0207 | Same End of Life series. |
  | `Standard_B2pls_v2` | 2 | 4 GiB | 0.0336 | Arm64. |
  | `Standard_B2als_v2` | 2 | 4 GiB | 0.0376 | AMD x86. |

  **The cheapest current-generation sizes have 1 GiB of memory, below Twingate's general guidance** of 1 CPU and 2 GB of memory (Twingate connector best practices, read 2026-10-16). Treat a 1 GiB machine as an experiment to test, not a recommendation. The Arm size also needs a Generation 2 image (Microsoft lists Generation 1 as not supported on this series) and Twingate publishes the connector package for arm64, but nobody has run it on Azure here. The next size up that is not End of Life has 4 GiB and costs four times as much. The cost lesson shows what that does to the ceiling. **UNVERIFIED:** whether any other current Azure family has a 2 GiB size that is cheaper. Only the B-series was priced.
- **Boot data (`custom_data`).** Azure's field for cloud-init data is called custom data. It must be Base64-encoded (the CLI does that for you), can be at most 64 KB, and on Linux the cloud-init agent processes it by default. Two facts from Microsoft's custom data page (updated 2026-07-01) matter for the threat model: Microsoft **advises against putting sensitive data in custom data**, and a failure inside the script is **not** a fatal provisioning failure, so a VM can report "ready" with the connector not installed. Custom data is **not** exposed through the instance metadata service, but it is written to the machine (the Linux agent copies it under `/var/lib/waagent`). Azure also has a separate *user data* feature that **is** readable from the metadata service; do not put the connector token there. This project accepts the boot-data risk on DigitalOcean (threat T5); the same acceptance would apply here, with the same limits.
- **SSH key.** DigitalOcean registers a key at the account level. Azure takes the admin's public key on the VM itself. **UNVERIFIED:** exactly how a Linux VM's required admin user and this project's `cah-admin` user from cloud-init would interact; check when the build is written. The rule is unchanged: SSH is reached only through Twingate, and the public key is still required.

**Predict, then check.** List the Azure resources for **one** connector, from the resource group down, including the two that are not separate resources on DigitalOcean and cost or control money every hour.

*Reference: a network interface in the subnet; a Standard static public IP associated with the interface (billed hourly); the Linux VM with the interface and cloud-init custom data; the OS disk (billed monthly). Membership in an application security group and, if the NSG is on the interface, its association, are two more small objects. The resource group, virtual network, subnet and NSG are shared by both connectors.*

## Piece 4: the machine's identity, and Spacelift's

**On DigitalOcean.** There is none. The connectors do not call the cloud's API, and the cloud-init data carries their one secret.

**On Azure.** The platform's answer to "who is this machine?" is a **managed identity**: a credential-free identity in Microsoft Entra, either *system-assigned* (tied to one VM, deleted with it) or *user-assigned* (a standalone resource you can attach to several machines). There is no extra charge for either (Microsoft documentation, read 2026-10-16). This project's connectors do not call Azure, so the right amount of machine identity is **none**: no managed identity. The safest permission is the one that is not granted.

A different identity matters in this project: the one that lets **Spacelift** act in your subscription. Spacelift's Azure documentation (read 2026-10-16) describes three ways:

1. **The Spacelift-managed integration**, configured in Spacelift's settings, which "handles automatic secret creation and rotation" and needs an administrator in your tenant to grant consent.
2. **A static service principal**, supplied as `ARM_CLIENT_ID`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID` and either `ARM_CLIENT_SECRET` or a certificate. Spacelift calls it "simple to setup, but requires you to manually manage secret rotation." Its example grants the service principal the **Contributor** role on the subscription.
3. **A managed identity (`ARM_USE_MSI=true`)**, which needs a **private worker hosted in Azure**. This project's Spacelift setup uses the public worker pool (the phase 0 findings record that the free plan has one public worker), so this option does not apply.

That page documents no plan restriction, and **does not say which Spacelift plans include the managed integration**: check your own plan, and if it is not available, come back to the maintainer before using a static secret (decision 6 in the design). The page also links to a separate OIDC guide that this wiki **did not read**; OIDC for Azure is UNVERIFIED. If a build ever uses the `azuread` provider, the same page says it needs Microsoft Graph application permissions that cannot be granted in the portal; this project's build does not.

Least privilege is a choice here: the example uses Contributor on the whole subscription, but a pre-created resource group with the role granted only on it would be narrower. Whether the build can work with a role scoped that narrowly is not established.

**Predict, then check.** Which of these needs a managed identity: a connector installing packages from the internet; a workload on a VM that reads a secret from Azure Key Vault; Spacelift's public worker running a plan? Why?

*Reference: only the workload that calls Key Vault. The package install uses the public internet through the explicit outbound method. Spacelift's public worker is outside your subscription; it authenticates with the managed integration or a service principal, and the managed-identity route requires a worker hosted in Azure.*

## Putting the pieces together

On DigitalOcean, `stacks/00-foundation` and `stacks/10-access` are two layers, and the second depends on outputs of the first. The same layering makes sense on Azure: a foundation layer (resource group, virtual network, subnet, NSG) and an access layer (network interfaces, public IPs, VMs, the connector ASG and its rules). The shared parts, the Twingate resources, the boot script, the Doppler hook and the cost gate, are provider-neutral and are not rewritten. [The design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-design.md) explains how the trees would sit side by side.

## Try it yourself

- Draw the Azure network for two connectors on paper: the resource group, virtual network, subnet, NSG, the two NICs, their public IPs, the two VMs. Mark which arrows are allowed and which blocked. Then read the NSG's *default* rules and mark the one that makes your drawing wrong without an extra deny.
  *Reference: AllowVNetInBound (65000) allows connector-to-connector traffic unless a rule with a lower number denies it.*
- A teammate says "the connector is not reachable from the internet, so the two connectors cannot talk to each other." Is that right on Azure? How would you prove your answer without changing anything in production?
  *Reference: no. Inside the virtual network the default rules allow it. To prove it, from one connector try a connection to the other's private address on a port that is listening and see it succeed with only the defaults. After adding the deny, repeat and expect it to fail. This also settles the UNVERIFIED same-subnet question above for your setup.*
- Name one thing that was automatic on DigitalOcean and on Azure you must build. Name one that is the other way round.
  *One reasonable answer: DigitalOcean gave outbound access for free and Azure now needs an explicit method; Azure gave you routing for free and AWS made you build it, and Azure's resource group is a thing you create that DigitalOcean's project largely hides.*
- Find, on Microsoft's NSG page, what an NSG does *not* filter by default. Which threat in the [Threat model](Threat-Model.md) does that touch?
  *Reference: platform services on the two Microsoft-owned addresses (DHCP, DNS, instance metadata, health monitoring). It touches the boot-data exposure threat (T5), because the metadata address is outside what the NSG controls by default.*

Next: [the Azure cost lesson](Provider-Azure-Cost-Lesson.md).
