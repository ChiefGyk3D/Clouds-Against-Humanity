# Multi-cloud phase 0: findings

Status: phase 0 of [the multi-cloud design](2026-10-16-multicloud-design.md), run 2026-10-16. Issue: #22.
Evidence: [AWS](2026-10-16-multicloud-phase0-evidence-aws.md) and [Azure and GCP](2026-10-16-multicloud-phase0-evidence-azure-gcp.md), each row with a source URL and retrieval date. Prices were read from the vendors' own price-list files or APIs; rows with no official source are marked UNVERIFIED there and again below.
Nothing here is applied or approved to cost money.

## 1. What phase 0 was for

Re-check every vendor row of the design's difference table, settle the AWS egress choice with measured prices, and answer the gate the maintainer added: is Spacelift's native AWS integration available on the current plan?

## 2. Result in one paragraph

The design's shape holds. The cheapest zero-inbound design on AWS and Azure is **a public address with no inbound rules open to the internet**, not a private subnet with NAT, because a NAT gateway costs more than the whole ceiling. GCP is the exception at low traffic: Cloud NAT is cheaper than external addresses there until roughly 36 GiB a month of processed traffic, after which the per-gigabyte charge makes external addresses cheaper. A two-connector AWS stack lands between **about $15 and $24 a month fixed**, above the DigitalOcean $12 and under the $30 ceiling, with most of the difference being the charge for public IPv4 addresses. One row of the original table was wrong (Azure outbound access) and is corrected in the design.

## 3. Corrections and confirmations to the design's difference table

| Row | Verdict | What the evidence says |
|---|---|---|
| Packet filtering: AWS | Confirmed | Security groups attach to network interfaces, are stateful, and a new group has no inbound rules and one allow-all outbound rule. A group can name another group as a source or destination, but only through private addresses, and only within the same VPC or a peered VPC (inbound also across a transit gateway). |
| Packet filtering: Azure | Confirmed, with a trap | An NSG attaches to a subnet or interface. Its default rules deny inbound from the internet but **allow inbound from inside the virtual network**, so a learner must add a deny if they want connector-to-connector isolation. |
| Packet filtering: GCP | Confirmed | Targets by network tag or service account; tags and service accounts cannot be mixed in one rule. Ingress has an implied deny and egress an implied allow. The exact priority number of the implied rules is not stated in current docs, so lessons must not teach 65535 as sourced. |
| Egress: Azure | **Corrected** | Only subnets in virtual networks created with the API version released after 2026-03-31 default to private (no default outbound access). Older API versions, including a pinned Terraform provider, and every existing network keep the old behaviour. The lesson is to **set it explicitly**. |
| Egress: AWS | Confirmed | A VM in a public subnet needs an internet gateway, a route, and a public address; inbound is blocked by the empty security group. A private subnet needs NAT. |
| Egress: GCP | Confirmed | A VM without an external address reaches the internet through Cloud NAT. |
| Machine identity | Confirmed | AWS instance profile; Azure managed identity (no extra cost); GCP attached service account, with dedicated service accounts and no long-lived keys as the best practice. |
| Hierarchy | Confirmed, with a gap | A GCP learner on a plain personal account has **no organization**, so no folders, organization policy or hierarchical firewall policies unless they set up Cloud Identity. Azure always has a tenant root management group. |
| Spacelift to the cloud | Confirmed | Role assumption on AWS (temporary credentials, needs a trust policy and a per-stack external ID created before the first apply), a managed integration or service principal on Azure, a short-lived service account token on GCP. Plan availability: section 6. |

## 4. What the egress choice costs (the finding that most shapes the build)

All figures are list prices for us-east-1 (AWS), East US (Azure) and us-central1 (GCP), 730 hours a month, retrieved 2026-10-16.

| | Public address per VM | NAT |
|---|---|---|
| AWS | $0.005/h each, **$3.65/mo**; auto-assigned addresses are charged the same as elastic ones | NAT gateway $0.045/h = $32.85/mo, plus $3.65 for its address, plus $0.045/GB: **at least $36.50/mo** |
| Azure | $0.005/h each, $3.65/mo | NAT gateway $0.045/h = $32.85/mo plus address plus $0.045/GB |
| GCP | $0.005/h each, $3.65/mo | Cloud NAT $0.0014 per VM-hour plus $0.005/h for its address plus $0.045/GiB: **about $5.69/mo for two VMs** plus data; cheaper than two addresses only below roughly 36 GiB a month of processed traffic ($1.61 fixed saving divided by $0.045/GiB) |

On AWS and Azure, then, "zero public inbound ports" is enforced by having no inbound rule open to the internet while the machine still has a public address, which is the same trust model as the DigitalOcean firewall. On Azure that is **zero public inbound, not zero inbound**: the NSG's default rules still allow traffic from inside the virtual network, so isolating the two connectors from each other takes an explicit deny rule with a lower priority number. That is worth teaching explicitly: **no inbound rule is not the same as no address.** A truly address-less machine costs more than the whole ceiling there, and less than two addresses on GCP.

## 5. Fixed monthly cost of a two-connector stack

Arithmetic is in the evidence files. Excludes data transfer, logging and any free-tier credit.

| Cloud and sizing | About per month | Notes |
|---|---|---|
| AWS, 2 x t4g.nano + 2 public IPv4 + 2 x 8 GiB gp3 | $14.71 | 0.5 GiB of memory, at the floor of Twingate's smallest documented size. Not recommended. |
| **AWS, 2 x t4g.micro + 2 public IPv4 + 2 x 8 GiB gp3** | **$20.84** | Recommended starting point. Arm; see section 7. |
| AWS, 2 x t3.micro (x86) | $23.76 | Fallback if arm turns out not to work. |
| Azure, 2 x B2ats_v2 + 2 public IPs + 2 x 32 GiB Standard SSD | about $25.82 | Default disk type unverified. B2pts_v2 (Arm) about $24.36. Lessons only, so not decided. |
| GCP, 2 x e2-small + 2 external IPs + disks | about $34 to $36 | **VM prices unverified.** Twingate suggests e2-small on GCP; e2-micro is below its guidance. Lessons only. |

Reference point: the DigitalOcean stage 1 is $12.

## 6. The Spacelift question (the gate from decision 6)

**Not yet answered.** Spacelift's AWS integration documentation explains the mechanism but states nothing about which plans include it. The pricing page lists "Cloud integrations" among the features of its first paid plan and says only that the free plan has 2 users and 1 public worker. That is a hint that it is not on the free plan, not a statement. The maintainer's account is the only authority: the check is to try to start an AWS integration in the Spacelift settings (and stop before saving) and see whether it proceeds or shows an upgrade prompt.

If it is gated, decision 6 applies: come back to the maintainer before using a static key.

## 7. Things phase 0 settled, and things it did not

**Settled**
- The Twingate connector package is published for arm64 in Twingate's own apt repository (the package index lists `twingate-connector` for amd64, arm64 and armhf; the latest version, 1.93.0, has an arm64 package, `twingate-connector-arm64.deb`, checked 2026-10-16; Twingate's connector changelog also documents Linux arm64 support). That removes the main doubt about t4g. Running it on a real t4g instance is still untested.
- AWS public IPv4 is charged on auto-assigned addresses; do not assume a free allowance (the 750-hour allowance is documented only for the old 12-month model).
- The AWS Free Tier for new accounts is credit-based ($100 on signup, up to $100 more for activities), and the free plan ends at six months or when credits run out, then the account closes with content kept 90 days. A time-boxed apply fits; the account itself is time-boxed too.
- No budget on any of the three clouds stops spending. AWS budget actions can apply an IAM policy or a service control policy, and can **stop selected EC2 or RDS instances** (AWS's API lists stop-instance action types), but they act on billing data that updates only a few times a day, cover chosen resources only, and do not delete storage or stop metered charges elsewhere; Azure's only built-in limit is on credit-type subscriptions and deallocates machines; GCP alert budgets never cap, and automation through notifications is delayed and can fail silently. The design's wording (approved fixed infrastructure, not a hard cap) stands.

**Still UNVERIFIED**
- The default root volume size of the Ubuntu image on AWS (assumed 8 GiB from third-party posts; verify in the console launch wizard on the throwaway account).
- Which EC2 instance types the AWS free plan allows.
- GCP e2 on-demand and disk prices (Google's page renders prices with JavaScript; use the pricing calculator).
- Azure memory per B-size, the East US rows for the NAT and load-balancer meters, and whether the free account covers a public IP and a disk.
- Spacelift OIDC specifics for Azure and GCP; GCP 2-step verification and secure-by-default organization policy pages.

## 8. What this changes in the plan

1. **The AWS approved figure.** Decision 5 gave each cloud its own approved fixed figure under the shared ceiling. About **$21 for the t4g.micro stack** is the proposal. But the $30 is defined globally in the repository today: `docs/stages/approved.json` has `ceiling: 30.0`, `docs/cost.md` calls it the ceiling for stages 0 to 4, and the learner-facing How-money-works page calls it the total across all planned stages. With DigitalOcean stage 1 at $12 running, an AWS stack at $21 totals $33. So either the ceiling becomes per cloud, which is a semantic change to the cost gate and to those two documents, or the AWS stage is applied only while DigitalOcean stage 1 is torn down. This needs the maintainer's decision, and phase 2 cannot start the per-cloud structure until it is made.
2. **Phase 2's gate must price public IPv4.** On AWS the public address is an attribute of the instance, not a separate resource; it is a quarter of the cost of a connector and the plan-JSON costing already in the design is the right tool.
3. **Lessons gain a "no inbound is not no address" page** (section 4) and an Azure "set outbound access explicitly" warning. The GCP lesson notes that Cloud NAT is the cheaper pattern there, which reverses the other two clouds.
4. **The AWS account lesson** must put the Spacelift IAM role after the admin identity step, since the role must exist before the first apply, and must say the free-plan account expires.
5. **The Spacelift plan check** (section 6) remains the gate before any AWS stack is created.

## 9. Open questions for the maintainer

1. Run the Spacelift check in section 6 and report what the settings page does.
2. Per-cloud ceiling, or one shared $30 with the clouds never applied together? (Section 8, item 1.)
3. Arm (t4g.micro, $20.84) or x86 (t3.micro, $23.76) for the first AWS stack? The recommendation is arm, with x86 as the fallback.
