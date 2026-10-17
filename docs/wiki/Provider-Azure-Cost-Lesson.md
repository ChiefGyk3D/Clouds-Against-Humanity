# Azure: where the money goes

> **Status: unverified draft.** Prices were read from Microsoft's public retail price API and documentation on 2026-10-16 (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md); the VM, public IP, disk and NAT figures were queried again the same day) and will change. Nothing was applied in a real subscription, so every figure is a list price, not an invoice. Not reviewed by anyone who runs Azure: corrections are welcome on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22). Read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first, and compare [the AWS cost lesson](Provider-AWS-Cost-Lesson.md).

The most common way a learner is surprised by a cloud bill is not an attack or a mistake in the code. It is a charge for something they did not know was billed. This page names the charges that matter for a project like this one, shows the arithmetic, and ends with how to prove the bill is back to zero.

All figures: East US, pay-as-you-go list prices in US dollars for non-Windows machines, 730 hours in a month, as of 2026-10-16. No other region was priced.

## What a two-connector stack costs

The cheapest design on Azure gives each connector a Standard public IP and opens no inbound rule to the internet (see [the same four pieces](Provider-Azure-The-Same-Four-Pieces.md)).

| Item | Rate | Two of them, per month |
|---|---|---|
| Small AMD burstable VM, `Standard_B2ats_v2` (2 vCPU, **1 GiB**: below Twingate's 2 GB guidance, so an experiment) | $0.0094 per hour | $13.72 |
| Standard static public IPv4 address | $0.005 per hour | $7.30 |
| OS disk, 32 GiB Standard SSD (`E4`, locally redundant; size and type assumed, **UNVERIFIED**) | $2.40 per month | $4.80 |
| **Total, fixed** | | **about $25.82** |

Variants priced the same way, all with two addresses and two 32 GiB Standard SSD disks:

| VM size | Memory | Per month, two VMs | Total fixed | Comment |
|---|---|---|---|---|
| `Standard_B2pts_v2` (Arm64) | 1 GiB | $12.26 | about $24.36 | Cheapest current size. Twingate publishes an arm64 package; untested on Azure. |
| `Standard_B2ats_v2` (AMD) | 1 GiB | $13.72 | about $25.82 | The row above. |
| `Standard_B1ms` | 2 GiB | $30.22 | about $42.32 | Meets Twingate's guidance, but this series is **End of Life** (Microsoft, 2026-09-27). |
| `Standard_B2pls_v2` (Arm64) | 4 GiB | $49.06 | about $61.16 | Current generation with more memory. |

DigitalOcean's version of this project is $12; the AWS version in this wiki is about $20.84 at the same 1 GiB.

Three things in these tables:

- **The memory is a real constraint, not a footnote.** Microsoft's size pages (read 2026-10-16) give 1 GiB for both cheap current sizes. Twingate's general guidance is 1 CPU and 2 GB. A stack that meets that guidance costs about $42 (using a retiring series) or about $61 (using a current one), which is over the whole $30 ceiling by itself. **Not priced:** any other family, and whether a smaller-than-guidance connector runs well is untested.
- **The addresses are over a quarter of the cheapest stack's cost** ($7.30 of $25.82). An address is not a cost most people think of as a cost. Standard public IPv4 is billed every hour it exists, whether or not anything uses it. The cheaper Basic SKU was retired on 2025-09-30.
- **A Virtual Network, an NSG and a resource group are not in the tables.** The virtual network is free (Microsoft's overview, read 2026-10-16). **UNVERIFIED:** that NSGs and ASGs are free; nothing read mentions a charge, but the price API was not searched for one.

The disk row has one more uncertainty. The price API also lists, for the same disk size, a "disk mount" meter at $0.26 a month and an operations meter at $0.002 per 10,000 operations. This wiki could not confirm whether either applies to an ordinary OS disk. If the mount meter applies, two disks add about $0.52. **UNVERIFIED.**

This is a **fixed** cost: what the stack costs just by existing. It does not include data leaving Azure, logging, or anything created by hand. See "what the number does not cover" below.

## The charge that would break the budget

The textbook design for a machine with no inbound access puts it in a *private* subnet and gives the subnet a **NAT gateway** so it can still reach out. Microsoft recommends the NAT gateway as the explicit outbound method for most cases, and since the default has changed, you will meet it in a lot of tutorials. On Azure that gateway costs **$0.045 an hour, about $32.85 a month**, plus **$0.045 per gigabyte processed**, plus its own Standard public IP ($0.005 an hour, $3.65 a month). That is at least about **$36.50 a month** before a byte of traffic.

Replace the two per-machine addresses with one gateway and the AMD stack goes from about $25.82 to about **$55.02** (13.72 + 4.80 + 32.85 + 3.65), or about $53.56 on Arm. The gateway adds about $29.20 a month over the two addresses it replaces, plus the per-gigabyte charge. That is more than this project's whole $30 shared budget and more than four times the entire DigitalOcean stack. The Standard and StandardV2 gateway are the same price in the price API.

Two honest caveats on that number:

- The price API returned the NAT gateway rate only under the region "Global", with no East US row, when queried on 2026-10-16. **UNVERIFIED:** that an East US gateway costs the same.
- A **Standard load balancer with outbound rules** is the other documented method that avoids a per-machine address. The price API listed its rule meter at $0.025 an hour (about $18.25 a month) plus $0.005 per gigabyte, again only under "Global". **UNVERIFIED** for East US, and a public load balancer has its own front-end address, so it was not carried further.

**On Azure, as on AWS, a NAT gateway does not beat per-machine addresses at this size.** The comparison table in [Why the clouds differ](Why-the-Clouds-Differ.md) shows GCP flipping that at low traffic. Read the cost shape for the cloud you are on, not the lesson from the last one.

So this project would not build the textbook design on Azure. It would use a public IP on each interface and an NSG with no inbound rule open to the internet, and an explicit setting that the subnet does not rely on default outbound access. It is the same trust model as the DigitalOcean firewall, and it is honest to name the trade-off: a machine with an address and a good rule set is not the same as a machine with no address.

Where else charges appear:

- **An address you forgot.** A Standard static public IP is billed while it exists and is released only when you delete it. Documentation says a static address "is released when the resource is deleted and can't be recovered", which also means the address you tested with is not one you can get back.
- **Disks outlive machines.** Microsoft states that disk storage is billed separately from virtual machines. Whether a disk or a public IP goes away with its VM depends on how each was created, and this wiki did not verify the defaults, so check for both.
- **Anything that quietly adds a gateway.** A tutorial's "also associate a NAT gateway with the subnet" is a $32.85-a-month line item hidden in a copy-paste. This repository's cost gate exists to refuse that: it rejects a NAT gateway outright at this ceiling, in source or in a plan. There is no Azure stack in the repository yet, so this is tested against fixtures and not a live stack.
- **Marketplace items** can be billed separately even when a spending limit is on.

## The shared $30

This project's budget is **$30 a month for everything**, not $30 per cloud. DigitalOcean stage 1 is $12; the Azure stack above is about $25.82. Together that is about **$37.82**, over the line.

That does not make Azure impossible; it changes how you use it:

- Apply the Azure stack **only while the DigitalOcean stage is torn down**, or accept a higher approved total deliberately and write it down. (Azure alone, at 1 GiB, is under $30; any larger machine is not.)
- Keep an Azure experiment **time-boxed**: apply, learn, destroy, check the bill.
- Remember that the *approved* number in this repository is a statement about fixed, declared infrastructure. It is not a spending limit.
- The maintainer has not decided whether the ceiling becomes per cloud. Until it is decided, treat $30 as the sum.

## What the number does not cover

| Not in the $25.82 | Why it matters |
|---|---|
| Data leaving Azure | Internet-bound traffic is metered. Egress was not priced on this page, so there is no figure to quote. A connector relaying heavy traffic can add up. |
| NAT and load balancer processing | Per-gigabyte charges apply if you use either. |
| Logging and monitoring | Logs, metrics and any managed security service bill by volume. |
| Snapshots, extra disks, forgotten resources | Billed until deleted. |
| Anything created outside the code | Not in the repository, so not in the cost gate. |
| Taxes and currency conversion | Real invoices. |

And, plainly: **no Azure budget is a hard cap on your spending.** A budget notifies. Microsoft's documentation says "resources aren't affected, and your consumption isn't stopped"; cost data arrives 8 to 24 hours late and budgets are evaluated every 24 hours. A budget can call an action group that runs automation, so a stop can be *built*, but it is not built in. The one built-in limit is the **spending limit** on credit-type subscriptions such as the free account: when it is reached, VMs are stopped and deallocated. It does not exist on pay-as-you-go, upgrading removes it, and some Marketplace charges are billed regardless. AWS and GCP have the same basic limitation in different forms. A budget is an alarm, not a brake.

## The free account, again

A new Azure customer gets a $200 credit for 30 days and 12 months of 750 hours each of three burstable VM sizes (`B1s`, `B2pts v2`, `B2ats v2`), per the free account page read 2026-10-16. To keep the 12-month services you must move to pay-as-you-go within the 30 days. Some arithmetic you can check: an always-on VM is about 730 hours a month, so one machine of a given size fits inside 750 hours, but two always-on machines of one size need about 1,460, which is more than one allowance if the hours are pooled per size (the page does not say how they pool). **UNVERIFIED:** whether the free hours cover the public IP and the disk. Credits and free hours can soften a learning bill. They also create a cliff, and they are no reason to skip the budget.

## Prove it is zero

The same discipline as the DigitalOcean teardown, with the Azure names:

1. Destroy the stacks in the reverse order you built them, so the machines go before the network.
2. In the portal, open **Resource groups** and list **every** resource group in the subscription, not just yours. Anything you did not create is worth a look. Deleting a resource group deletes every resource in it, which is the fast way to remove an experiment that lived in its own group.
3. Look in particular for what survives a machine's deletion: public IP addresses, disks, network interfaces, NAT gateways and load balancers.
4. Open **Cost Management** and look at today's and yesterday's cost by service. Data arrives 8 to 24 hours late, so one look is not proof.
5. Look again the next day. A resource you forgot shows up on the second look.
6. Delete the budgets last, not first.

## Try it yourself

- **Predict, then check.** Before you read the first table, estimate the monthly cost of two small VMs with public addresses. Then compute it from the rates. Which line was the biggest surprise?
  *Reference: from the rates above, 2 x $0.0094 x 730 = $13.72 for the VMs, 2 x $0.005 x 730 = $7.30 for the addresses, 2 x $2.40 = $4.80 for the disks, about $25.82 in all. For many people the addresses are the surprise; the disks are the cheapest line.*
- Replace the public addresses with one NAT gateway. What is the new fixed cost, before any data?
  *Reference: the VMs and disks are 13.72 + 4.80 = $18.52, and the gateway with its address is 32.85 + 3.65 = $36.50, so about $55.02 a month. The gateway costs about $29.20 more than the two addresses it replaces, so at two machines the addresses win by a wide margin, before counting the $0.045 per gigabyte.*
- Your teammate wants a 2 GiB machine "to follow Twingate's guidance". Using this page only, what are two ways that choice changes the plan, and what does neither of them settle?
  *Reference: the retiring `B1ms` brings the stack to about $42.32, over the $30 ceiling on its own; a current 4 GiB size brings it to about $61.16. Neither settles whether the 1 GiB machine would have been enough, which is untested, nor whether another family has a cheaper 2 GiB size, which was not priced.*
- With DigitalOcean stage 1 running, how much room is left under $30 for another cloud, and does the cheapest Azure stack fit?
  *Reference: $30 - $12 = $18. The cheapest priced Azure stack, about $24.36, does not fit; the project would have to apply it only with DigitalOcean torn down, or change the ceiling.*
- Look at the [cost gate](CI-Tests-and-Cost-Gate.md). Which of the charges on this page would it catch today, and which would pass silently?
  *Reference: it rejects a NAT gateway at this ceiling (as this page and the AWS lesson describe it). There is no Azure stack in the repository to price yet. A fixed-cost gate prices only what the code declares, so data transfer, logging, a forgotten disk or anything created outside the code would pass silently. Check the gate page for its current behaviour.*

Back to [Why the clouds differ](Why-the-Clouds-Differ.md), or to [Home](Home.md).
