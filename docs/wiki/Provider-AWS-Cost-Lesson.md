# AWS: where the money goes

> **Status: unverified draft.** Prices were read from AWS's own price-list files and documentation on 2026-10-16 (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-aws.md)) and will change. Nothing was applied in a real account, so every figure is a list price, not an invoice. Not yet reviewed by the maintainer. Read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

The most common way a learner is surprised by AWS is not an attack or a mistake in the code. It is a charge for something they did not know was billed. This page names the charges that matter for a project like this one, shows the arithmetic, and ends with how to prove the bill is back to zero.

All figures: US East (N. Virginia), on-demand list prices, 730 hours in a month, as of 2026-10-16.

## What a two-connector stack costs

| Item | Rate | Two of them, per month |
|---|---|---|
| Small arm instance (`t4g.micro`, 1 GiB: below Twingate's 2 GB guidance, so an experiment) | $0.0084 per hour | $12.26 |
| Public IPv4 address | $0.005 per hour | $7.30 |
| Root disk, 8 GiB general-purpose SSD (size unverified) | $0.08 per GiB-month | $1.28 |
| **Total, fixed** | | **about $20.84** |

Variants priced the same way: a half-gigabyte arm instance (`t4g.nano`) comes to about $14.71 but is well below Twingate's guidance; an x86 instance (`t3.micro`) comes to about $23.76. DigitalOcean's version of this project is $12.

Now read the middle row again. **The addresses cost more than half of what DigitalOcean charges for the whole thing.** An address is not a cost most people think of as a cost, and it is charged for every public address in use, including the ones AWS assigns automatically when a machine starts. The old "free hours of public IPv4" allowance belonged to the previous twelve-month free offer; the current price page lists none, so do not plan around it.

This is a **fixed** cost: what the stack costs just by existing. It does not include data leaving AWS, logging, or anything created by hand. See "what the number does not cover" below.

## The charge that would break the budget

The textbook design for a machine with no inbound access puts it in a *private* subnet and gives the subnet a **NAT gateway** so it can still reach out. On AWS that gateway costs about $0.045 an hour, **$32.85 a month**, plus a charge for its own public address (about $3.65) and about $0.045 per gigabyte processed. Together, **at least $36.50 a month before a byte of traffic**. That is more than this whole project's shared $30 budget and more than three times the entire DigitalOcean stack.

So this project would not build the textbook design on AWS. It would use a public subnet and give each machine a public address, with **no inbound rule open to the internet**. The address exists; no rule lets anything use it to get in. That is the same trust model as the DigitalOcean firewall, and it is honest to name that trade-off: a machine with an address and a good rule set is not the same as a machine with no address.

Two more places charges appear:

- **An address you forgot.** AWS charges for public addresses whether they are in use or idle. An elastic address left behind after the machine is gone is still billed.
- **Anything that quietly adds a gateway.** A tutorial's "also create a NAT gateway for the private subnet" is a $32.85-a-month line item hidden in a copy-paste. This is exactly what this repository's cost gate exists to refuse: it rejects a NAT gateway outright at this ceiling, whether it appears in the source or in a plan, and it prices the instances and addresses of an AWS stack from a manifest that must match the plan. There is no AWS stack in the repository yet, so this is tested against fixtures, not a live stack.

## The shared $30

This project's budget is **$30 a month for everything**, not $30 per cloud. The DigitalOcean stage 1 is $12 and the AWS stack above is about $21, which together is $33, over the line.

That does not make AWS impossible; it changes how you use it:

- Apply the AWS stack **only while the DigitalOcean stage is torn down**, or accept a higher approved total deliberately and write that down.
- Keep an AWS experiment **time-boxed**: apply, learn, destroy, check the bill.
- Remember that the *approved* number in this repository is a statement about fixed, declared infrastructure. It is not a spending limit.

## What the number does not cover

| Not in the $20.84 | Why it matters |
|---|---|
| Data transfer out | Internet-bound traffic from AWS is metered after any monthly allowance that applies. A connector relaying heavy traffic can add up. |
| Logging and monitoring | Metrics, logs and any managed security service bill by volume. |
| Snapshots, extra disks, forgotten resources | Billed until deleted. |
| Anything created outside the code | Not in the repository, so not in the cost gate. |
| Taxes and currency conversion | Real invoices. |

And a point that is worth saying plainly: **no AWS budget is a hard cap on your spending.** A budget notifies. A budget *action* can attach a restrictive policy or stop selected instances, but it works on billing data that updates only a few times a day, so a cost can pass the line before anything happens, and it cannot reach every kind of charge. Azure and GCP have the same limitation. A budget is an alarm, not a brake.

## The free offer, again

New AWS customers get credits rather than a year of free service, and the free plan ends after six months or when the credits run out, then the account closes (content kept for 90 days). Credits can soften a learning bill. They also create a cliff, and they are no reason to skip the billing alert.

## Prove it is zero

The same discipline as the DigitalOcean teardown, with the AWS names:

1. Destroy the stacks in the reverse order you built them, so the instances go before the network.
2. In the AWS console, look for what survived: instances, volumes, snapshots, elastic addresses, gateways and any NAT gateway.
3. Open the billing and cost pages and look at today's and yesterday's usage by service.
4. Look again the next day. Billing data lags; a resource you forgot shows up on the second look.
5. Delete the budgets last, not first.

## Try it yourself

- **Predict, then check.** Before you read the table, estimate the monthly cost of two small instances with public addresses. Then compute it from the rates. Which line was the biggest surprise?
- Open the AWS pricing calculator and build the stack above. Compare its answer with the table, and write down what it includes that the table does not.
- Replace the public addresses with one NAT gateway. What is the new fixed cost? (Reference: about $50 a month for the stack, which is the two instances and disks, about $13.54, plus about $36.50 for the gateway and its address, before any data.) What does that tell you about the break-even between "an address per machine" and "one gateway for many"? AWS's own documentation gives a formula for this. At two machines, which side wins?
- Look at the [cost gate](CI-Tests-and-Cost-Gate.md). Which of the charges on this page would it catch today, and which would pass silently?

Next: [Azure account preparation](Provider-Azure-Account-Preparation.md), the same three lessons for Azure (unverified drafts). Back to [Why the clouds differ](Why-the-Clouds-Differ.md) or the [Reading order](Reading-Order.md).
