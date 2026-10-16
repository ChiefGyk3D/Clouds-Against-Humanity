# Why the clouds differ

> **Status: unverified draft.** Written 2026-10-16 from the vendors' own documentation and price lists (sources and dates in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-findings.md)). Nothing here has been applied in a real account, and no one who runs these clouds professionally has reviewed it yet. Vendor facts go stale; every figure carries its date. If you run AWS, Azure or GCP and find an error, please say so on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22).

Read [What is the cloud](What-Is-the-Cloud.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) first. This page is the comparison: it does not teach any one cloud. The pages that do are [AWS account preparation](Provider-AWS-Account-Preparation.md), [the same four pieces on AWS](Provider-AWS-The-Same-Four-Pieces.md), and [the AWS cost lesson](Provider-AWS-Cost-Lesson.md).

Every large cloud sells the same few things: a private network, a way to filter traffic, a machine, and an identity for the machine. They differ in how those are shaped, and the shapes are where jobs and bills go wrong. This project already built the four pieces on DigitalOcean. The point of this page is to give you the questions to ask of any cloud, so that a fifth one is not a surprise.

## Four questions to ask of any cloud

### 1. What is the boundary of "my stuff"?

| | DigitalOcean (built) | AWS | Azure | GCP |
|---|---|---|---|---|
| The top | A team | An account | A tenant (the identity directory) | An organization, if you have one |
| The box things live in | A project | The account, often one of many under an organization | A subscription, then a resource group | A project |
| What a brand-new learner starts with | An account and a team | An account | A tenant and a free-trial subscription (the exact signup result is unverified) | A project with no organization, on a plain personal account |

Why it matters: the boundary decides where you put an expensive mistake. Separate accounts, subscriptions or projects for experiments are the cheapest safety feature any of these clouds has. On GCP a learner without an organization cannot use folders, organization policy or hierarchical firewall policies at all, so the safety has to come from habits instead.

### 2. Who gets a path to the internet, and who pays?

This is the question that surprises people most. In this project the machines need to reach out to the internet (the Twingate relays, package mirrors) and nothing must reach in.

| | A public address on each machine | A NAT service so machines can stay address-less |
|---|---|---|
| DigitalOcean | Free, built into the droplet | Not part of this project |
| AWS | $0.005/hour each, about $3.65 a month, **including** addresses assigned automatically | At least about $36.50 a month for one NAT gateway with its address, plus a per-gigabyte charge |
| Azure | $0.005/hour each, about $3.65 a month | About $32.85 a month for a NAT gateway, plus its address and a per-gigabyte charge |
| GCP | $0.005/hour each, about $3.65 a month | Cloud NAT: about $5.69 a month for two machines, plus a per-gigabyte charge |

(List prices, us-east-1 / East US / us-central1, 730 hours a month, retrieved 2026-10-16. Check the vendor before you rely on any of them.)

Two lessons sit in this table.

- **"No inbound ports" does not mean "no public address."** On AWS and Azure, the cheapest way to build this project is to give each machine a public address and to have **no inbound rule open to the internet**. The address exists; nothing may use it to reach in. A truly address-less machine needs NAT, which on AWS alone costs more than the whole $30 budget. On Azure it is also true that this means *zero public* inbound, not zero inbound: the default rules still let machines inside the same virtual network talk to each other, so isolating the two connectors needs an explicit deny.
- **The cheapest pattern is not the same on every cloud.** On GCP, NAT is cheaper than two public addresses at low traffic (the break-even is roughly 36 GiB a month of processed traffic, after which the per-gigabyte charge flips it). Learning a rule like "NAT is expensive" from one cloud and applying it to another gives the wrong answer.

### 3. How do you say which machines a rule is about?

A firewall rule answers three questions: which machines does this set of rules apply to (the **target**), who may reach them (the **source**), and what may they reach (the **destination**). DigitalOcean answers all three with one thing, a tag. The others split them:

| | Target | Source or destination |
|---|---|---|
| DigitalOcean | The firewall applies to droplets with a tag | A tag (so "only droplets with this tag") or an address range |
| AWS | A security group is attached to a machine's network interface | A range, **or another security group**. Works through private addresses, within the same VPC or a peered one (and, for inbound rules only, across a transit gateway) |
| Azure | A network security group attached to a subnet or a network interface | A range, a service tag, or an *application security group* (a named set of interfaces) |
| GCP | Firewall rules on the VPC network, aimed by network tag or by service account | A range, a tag, or a service account. Tags and service accounts cannot be mixed in one rule |

Why it matters: the module in this repository takes a single `tag`. That is a DigitalOcean shortcut. A module that speaks to AWS has to say "attach this group to these machines" and "allow traffic from that group" as two separate things. Any design that hides this behind one friendly word loses the most useful thing a learner can see.

### 4. Who is the machine?

The machine itself needs an identity when it calls the cloud's own APIs. In this project the droplets do not, so the question has not come up yet. It will the moment a workload reads a secret or writes to a bucket.

| | The machine's identity |
|---|---|
| DigitalOcean | None needed here |
| AWS | An *instance profile*, which attaches an IAM role to the machine |
| Azure | A *managed identity*, with no credential to store |
| GCP | An attached *service account* (use a dedicated one, never the default with broad rights; avoid downloaded keys) |

The shared idea is the one from [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md): give the machine an identity the platform vouches for, so it never holds a long-lived secret. All three do that; the names and the rules around them differ.

## And a fifth, for later: how does the cloud's own console get misused?

The usual cloud incident is not a clever attack on the network. It is a leaked key, an over-broad role, or a forgotten resource. Account preparation is the cheapest security work on each cloud, and it is why every cloud lesson here starts there.

## Try it yourself

- **Predict, then check.** Without looking above, write down, for each cloud, whether you expect a NAT service or a public address per machine to be the cheaper way to give two machines outbound access. Then check the egress table. Which cloud surprised you? (The table cannot say which *cloud* is cheapest overall: it leaves out the machines, disks and traffic.)
- Pick a cloud you use. Fill in the four-question tables for it, from its documentation, with the date you read it.
- Read [Provider-AWS-The-Same-Four-Pieces](Provider-AWS-The-Same-Four-Pieces.md). For each of the four questions, find the resource that answers it.

Next: [AWS account preparation](Provider-AWS-Account-Preparation.md).
