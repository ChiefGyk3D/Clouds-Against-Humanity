# GCP: where the money goes

> **Status: unverified draft.** Network prices were read from Google's own pricing pages on 2026-10-16 (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md)) and will change. **The machine prices are NOT verified:** Google's VM price page renders its numbers with JavaScript and the figures here are working estimates to be confirmed in Google's pricing calculator. Nothing was applied in a real project, so every figure is a list price, not an invoice. Not reviewed by anyone who runs GCP; corrections welcome on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22). Read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first.

GCP is the one cloud of the three where the textbook design, machines with no public address behind a NAT service, can be the cheaper one. This page shows the arithmetic, shows where that stops being true, and ends with how to prove the bill is back to zero.

All figures: `us-central1` where a region matters, on-demand list prices in US dollars, 730 hours in a month, as of 2026-10-16.

## What is verified and what is not

| Row | Rate | Status |
|---|---|---|
| External IPv4 address, in use on a standard VM | $0.005 per hour | Read from Google's [network pricing](https://cloud.google.com/vpc/network-pricing) page, 2026-10-16 |
| Same, on a Spot or preemptible VM | $0.0025 per hour | Same page and date |
| Cloud NAT, up to 32 VMs | $0.0014 per VM per hour, plus $0.045 per GiB processed (inbound and outbound), plus $0.005 per hour for each external IP the gateway uses | Read from Google's [Cloud NAT pricing](https://cloud.google.com/nat/pricing) and network pricing pages, 2026-10-16 |
| `e2-micro` (1 GB), on demand | about $0.0084 per hour | **UNVERIFIED.** Working figure; third-party sites disagreed |
| `e2-small` (2 GB), on demand | about $0.0168 per hour | **UNVERIFIED.** Working figure |
| Persistent disk | Balanced: $0.000136986 per GiB-hour (about $0.10 per GiB-month); standard: $0.000054795 per GiB-hour (about $0.04 per GiB-month) | Read from Google's disk pricing page on 2026-10-16, but the table I read was one regional table and I could not tie it to `us-central1`: **UNVERIFIED for this region** |
| Cloud Router (Cloud NAT needs one) | not checked | **UNVERIFIED** whether it adds a charge |

Everything in the table below that depends on an UNVERIFIED row is marked.

## What a two-connector stack costs

Two instances, two 10 GiB balanced boot disks, with a public address on each machine:

| Item | Rate | Two of them, per month |
|---|---|---|
| `e2-micro` (1 GB: below Twingate's 2 GB guidance, so an experiment) | $0.0084 per hour (UNVERIFIED) | $12.26 |
| External IPv4 address | $0.005 per hour | $7.30 |
| Boot disk, 10 GiB balanced (size and region UNVERIFIED) | about $0.10 per GiB-month | $2.00 |
| **Total, fixed** | | **about $21.56** |

The same stack with `e2-small`, which is what Twingate suggests on GCP: VMs $24.53, addresses $7.30, disks $2.00, **about $33.83**. That is above the project's whole $30 budget on its own.

For comparison, DigitalOcean's version of this project is $12. (The evidence file's own estimate for the `e2-small` stack was "roughly $34 to $36" with disks at $2 to $4; the difference is the disk price assumption.)

Now read the address row again. **The two addresses cost more than half of what DigitalOcean charges for the whole thing.** The Always Free allowance does not remove the address charge.

This is a **fixed** cost: what the stack costs just by existing. It does not include data leaving Google Cloud, logging, or anything created by hand. See "what the number does not cover" below.

## The break-even: addresses or Cloud NAT

Unlike AWS and Azure, GCP's NAT service is cheap at small scale. For two machines that share one NAT gateway with one external IP and next to no traffic:

- gateway: 2 VMs x $0.0014 x 730 = $2.04
- its address: $0.005 x 730 = $3.65
- **total: about $5.69 a month**, against $7.30 for two addresses on the machines. The saving is about **$1.61 a month**.

Then the per-gigabyte charge arrives. Cloud NAT bills **$0.045 per GiB processed, in both directions**. The gateway wins only while the traffic it processes costs less than the saving:

> $1.61 / $0.045 = about **35.7 GiB** a month

Below roughly 36 GiB a month, private machines behind Cloud NAT are cheaper than a public address per machine. Above it, the addresses are cheaper. (This repeats the arithmetic in the earlier findings, re-checked on 2026-10-16: $7.30 minus $5.694 is $1.606, and $1.606 divided by $0.045 is 35.7.)

Four cautions:

- The comparison is only about the NAT path versus the address path. Charges for data leaving Google's network apply either way, and Google's NAT page says so ("data transfer costs to send traffic from the VM out of the network also apply"). Neither side of the comparison includes them.
- A connector that relays user traffic can pass 36 GiB without trying. The break-even is a **question about your traffic**, which this page cannot answer.
- With the NAT design the machines have no public address at all, which is a real security difference, not just a cost one. Cloud NAT only translates replies to connections a machine started; it does not accept unsolicited inbound traffic.
- Cloud NAT needs a Cloud Router resource. Whether the router itself is billed was not checked: UNVERIFIED.

So on GCP the fixed cost of the NAT design, with `e2-micro` machines, is $12.26 + $5.69 + $2.00 = **about $19.95**, and with `e2-small` about $32.22, each before any traffic.

## The Always Free corner

Google's Always Free tier includes one non-preemptible `e2-micro` per month in `us-west1`, `us-central1` or `us-east1`, with 30 GB-months of standard persistent disk and 1 GB of outbound transfer. Applied to this stack (UNVERIFIED because the `e2-micro` price is a working figure): one machine is free, the second costs about $6.13 a month, the two addresses cost $7.30, and the disks fit inside the 30 GB only if they are standard, not balanced. That is **about $13.43**, which is near the DigitalOcean stage. Two warnings. The free allowance is counted in hours across the three regions combined and per billing account, so a second `e2-micro` anywhere else in the account uses it up. And the machine has 1 GB of memory, below Twingate's guidance.

## The shared $30

This project's budget is **$30 a month for everything**, not $30 per cloud. DigitalOcean stage 1 is $12. Added to the GCP numbers above:

| GCP variant (fixed) | Plus DigitalOcean $12 | Under $30? |
|---|---|---|
| `e2-micro`, public addresses, about $21.56 | about $33.56 | No |
| `e2-micro`, Cloud NAT, about $19.95 | about $31.95 | No |
| `e2-small`, public addresses, about $33.83 | about $45.83 | No |
| One free `e2-micro` and standard disks, about $13.43 (UNVERIFIED) | about $25.43 | Yes |

That does not make GCP impossible; it changes how you use it:

- Apply the GCP stack **only while the DigitalOcean stage is torn down**, or accept a higher approved total deliberately and write that down.
- Keep a GCP experiment **time-boxed**: apply, learn, destroy, check the bill.
- Remember that the *approved* number in this repository is a statement about fixed, declared infrastructure. It is not a spending limit. This repository's cost gate has no GCP prices yet and no GCP stack exists, so none of this is tested against a live stack.

## What the number does not cover

| Not in the $21.56 | Why it matters |
|---|---|
| Data transfer out of Google's network | Internet-bound traffic is metered beyond any free allowance (the Always Free tier gives 1 GB a month from North America). |
| Cloud NAT data processing | $0.045 per GiB in both directions, once you use the NAT design. |
| Logging and monitoring | Volume-billed. |
| Snapshots, extra disks, unattached static addresses | Billed until deleted. Google charges a higher rate for a reserved static address that is not attached to anything. A static address attached to a stopped VM still counts as in use, and an ephemeral address is charged only while the VM runs. |
| Anything created outside the code | Not in the repository, so not in the cost gate. |
| Taxes and currency conversion | Real invoices. |

And a point worth saying plainly: **no GCP budget is a hard cap on your spending.** An alerts-only budget "doesn't automatically cap" usage or spending. Automation through Pub/Sub notifications is delayed (the first notification may take hours) and can fail silently; a "spend cap" budget exists only for eligible services. A budget is an alarm, not a brake.

## The free offer, again

New Google Cloud users get a $300 credit over 90 days, after which the trial billing account closes, resources stop, and there is a 30-day window to upgrade before deletion (see [account preparation](Provider-GCP-Account-Preparation.md)). Credits can soften a learning bill. They also create a cliff, and they are no reason to skip the billing alert.

## Prove it is zero

The same discipline as the DigitalOcean teardown, with the GCP names:

1. Destroy the stacks in the reverse order you built them, so the instances go before the network.
2. In the console, look for what survived: VM instances, disks and snapshots, reserved external addresses, Cloud NAT gateways and Cloud Routers.
3. Open the billing reports and look at yesterday's and today's usage by service, in the project.
4. Look again two days later. Billing data lags, and Google's monthly budgets keep tracking for two days into the next month. A resource you forgot shows up on the second look.
5. If this was a throwaway project, you can delete the whole project, which removes what is in it. Confirm in the billing report that nothing is still being charged, and delete the budgets last, not first.

## Try it yourself

- **Predict, then check.** Before you read the table, estimate the monthly cost of two small VMs with public addresses. Then compute it from the rates. Which line was the biggest surprise?
- **Break-even.** Compute the monthly cost of both designs at 100 GiB of processed traffic a month. (Reference: addresses stay at $7.30; Cloud NAT is $5.69 + 100 x $0.045 = $10.19, so the addresses win by $2.89. At 20 GiB NAT is $6.59 and wins by $0.71.) What is the break-even, and what do you know about your own traffic?
- **Re-verify.** Open Google's Cloud NAT pricing page and check the three rates. Write down the date. If any has changed, recompute the break-even. (The formula is the saving divided by the per-GiB rate.)
- **Close the gap.** Use the pricing calculator to get the real `e2-micro` and `e2-small` hourly prices in `us-central1` and replace the two UNVERIFIED rows. How far off was the working figure?
- Look at the [cost gate](CI-Tests-and-Cost-Gate.md). Which of the charges on this page would it catch today, and which would pass silently? (Reference, one honest answer: its free list is an allowlist of DigitalOcean resource types and it has no GCP prices, so a GCP stack would be refused by name rather than priced.)

That is the last of the other-clouds pages. Back to [Why the clouds differ](Why-the-Clouds-Differ.md) or the [Reading order](Reading-Order.md).
