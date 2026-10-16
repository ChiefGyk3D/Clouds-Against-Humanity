# Clouds Against Humanity: Other Clouds (AWS, Azure, GCP)

Status: DRAFT for review. Date: 2026-10-16. Issue: #22.
Tooling: OpenTofu throughout.
Scope: how to teach and, where it is worth it, build this environment on AWS, Azure and GCP. This is a design, not an approval. Nothing here costs money, changes a stack, or moves a file until the operator approves a phase.

## 1. Purpose and the one rule

The repository is DigitalOcean-first and that is fine for a beginner. The issue asks for the basics of the three large clouds once a learner has the basics, noting that each needs account preparation of its own, that "we will need to fork the terraforms to make versions for each platform", and that the author is a DigitalOcean and AWS person who would have to learn Azure and GCP administration.

The rule that governs this design: **a learner has to come away understanding why the three clouds differ, not holding three copies of the same files.** Copies teach nothing about the differences, drift apart, and become code nobody can vouch for. So the design separates what is the same everywhere from what is genuinely different, builds only what the author can stand behind, and says plainly which pages are verified and which are not.

Success looks like:

- A learner who finishes the DigitalOcean path can read an AWS, Azure or GCP equivalent and name, for each piece, what is the same, what is different, and why.
- AWS has real, tested modules and a stack, written and checked by someone who runs AWS for a living.
- Azure and GCP have lessons and a documented interface mapping first, and code only after someone who runs them has reviewed it.
- The public repository stays safe to publish: no account ids, tenant names or credentials, on any provider.

Non-goals: a provider-abstraction layer that hides the differences (the differences are the lesson); supporting every service on every cloud; managed Kubernetes; moving the author's own environment off DigitalOcean.

## 2. What is already provider-neutral

Most of this project is not DigitalOcean at all. The split matters because the neutral part is the valuable part, and it must not be copied three times.

| Piece | Provider-neutral? | Notes |
|---|---|---|
| Twingate (connectors, resources, groups) | Yes | The connector is a package installed by cloud-init on any Linux VM. The Twingate Terraform provider is the same on every cloud. |
| Doppler as the secret store and the Spacelift hook (`scripts/spacelift/doppler-env.sh`) | Yes | The hook loads named variables; it does not care which cloud they authenticate to. |
| Spacelift run lifecycle, push policy, deletion protection, human confirm | Yes | The push policy matches on branch and changed files, not on provider. |
| The cost gate's structure (manifest, approved total, ceiling, module/manifest match) | The structure, yes | The price table and the resource allow-list are DigitalOcean-specific. See section 6. |
| CI shape (`tofu test` with mocked providers, `CI green`) | Yes | Each provider's directories are added to the `directories` input. |
| Threat model and default-deny stance | The reasoning, yes | The concrete rules differ. See section 4. |
| `modules/vpc`, `modules/firewall`, `modules/twingate-connector` resources | **No** | They create `digitalocean_*` resources. Roughly 40 references today. |
| `stacks/00-foundation`, `stacks/10-access` provider block, tags, project resource | **No** | Same reason. |
| `docs/cost-prices.json`, `scripts/cost_check.py` resource lists | **No** | DigitalOcean sizes and resource types. |

So the work is three modules, two stacks' wiring, and the price table, not the whole project.

## 3. Options considered

| Option | What it is | For | Against |
|---|---|---|---|
| A. Fork the repository per cloud (the issue's wording) | `Clouds-Against-Humanity-aws`, `-azure`, `-gcp` | Simple to explain. Each fork is self-contained. | Three copies of the neutral 60% drift apart. A fix to the hook or the push policy is made three times. Nobody can see the differences side by side, which is the lesson. |
| B. One repository, provider directories | `modules/<provider>/...`, `stacks/<provider>/...` next to the existing DigitalOcean tree | One neutral core. Differences sit in parallel directories a learner can diff. CI and the cost gate see everything. | A bigger repository. Needs a clear module contract so the parallel trees stay parallel. |
| C. Abstraction modules | One `firewall` module with a `provider` switch | Looks tidy. | Hides exactly the semantics learners need to see. Large conditional code. Untestable without all three providers. |
| D. Lessons only | Wiki pages, no code | Cheapest. No false authority on clouds the author does not run. | Nothing to run, so learners cannot practise. |

**Recommendation: B, delivered in the order D then B.** Lessons come first for every cloud (cheap, honest), and code follows only for a cloud once someone who runs it has reviewed the lessons. AWS reaches code first because the author works in it daily.

On the issue's "fork the terraforms": B satisfies the intent, a version per platform with the nuances discussed, without three repositories. Revisit if a community maintainer wants to own a cloud separately; the module contract in section 5 is what would make that easy.

### 3.1 Directory layout

Leave the DigitalOcean tree exactly where it is. Add the others beside it:

```text
modules/                      existing, DigitalOcean (unchanged)
modules/aws/{vpc,firewall,twingate-connector}/
stacks/00-foundation/         existing, DigitalOcean (unchanged)
stacks/10-access/             existing, DigitalOcean (unchanged)
stacks/aws/00-foundation/
stacks/aws/10-access/
docs/wiki/clouds/...          lessons (section 7)
```

Why not move DigitalOcean into `modules/digitalocean/` for symmetry: the two live stacks are locked in Spacelift with their project roots set to today's paths, and the stack-factory design pins them. Moving them changes a Spacelift setting on two production stacks for no behavioural gain. The symmetrical layout can happen later, as its own approved change, if it ever earns its cost. A learner is helped more by a clearly named `aws/` directory than by a tidy tree.

## 4. What genuinely differs, and why it matters

This table is the design's centre and is also the outline of the lesson. Everything here that describes a vendor is **from the author's working knowledge and has not been re-verified against current vendor documentation on this date**; phase 0 in section 8 verifies each row and dates it, as the rest of this repository does for vendor facts.

| Concept | DigitalOcean (built) | AWS | Azure | GCP |
|---|---|---|---|---|
| Account boundary | Team, then Project | Account (often inside an Organization) | Tenant, Subscription, Resource group | Organization, Folder, Project |
| Network | VPC per region | VPC per region, with subnets per availability zone, route tables and an internet gateway you create | Virtual network with subnets, per region | VPC is global; subnets are regional |
| Packet filtering | Cloud firewall attached **by tag** | Security group attached to the instance's network interface; rules can reference **another security group** | Network security group on a subnet or interface; rules can reference **application security groups** or service tags | VPC firewall rules on the network, matched by **network tag or service account** |
| Statefulness and defaults | Stateful; explicit outbound rules in this repo | Stateful; new groups allow all outbound by default | Stateful; default rules allow outbound | Stateful; implied allow egress, implied deny ingress |
| How a "no inbound" VM still reaches the internet | Public IP on the droplet, inbound filtered | Public IPv4 on the instance **or** a NAT gateway | Default outbound access is changing for new virtual networks; plan on an explicit method | A public IP **or** Cloud NAT |
| Machine identity | None needed here | Instance profile (an IAM role) | Managed identity | Service account |
| How Spacelift authenticates to the cloud | One API token from Doppler | An assumable IAM role (Spacelift supports role assumption) or access keys | Service principal or federated credential | Service account key or federated credential |
| Smallest sensible instance | `s-1vcpu-1gb` | a small burstable instance type | a small burstable VM size | a small shared-core machine type |
| Cost shape | Droplet price, nothing hidden | Instance, **plus** public IPv4 address charge, **plus** a NAT gateway if used | VM, plus public IP, plus disk SKU | VM, plus external IP, plus Cloud NAT if used |

Four points in that table reshape the design and are worth stating plainly:

1. **Attachment model.** DigitalOcean attaches a firewall by tag, which is why `modules/firewall` takes a `tag` and the rules in this repo say "only droplets carrying this tag". AWS attaches a security group to an interface, and the idiomatic form of "only from the connectors" is a rule whose source is the connector security group. GCP is closest to DigitalOcean (tags or service accounts). Azure sits in between. The module contract in section 5 therefore speaks of a **membership** ("the set of connectors"), and each provider implements membership its own way. This is the single most instructive difference and the reason option C (one abstract firewall) would hide the lesson.
2. **Egress is a cost decision.** The "zero public inbound ports" design still needs outbound reachability for Twingate. On DigitalOcean that is free: a public address with all inbound filtered. On AWS the same shape costs a public IPv4 address charge per instance, and the "private subnet plus NAT gateway" textbook answer costs far more than the whole current environment. The design must make the cheap, honest choice and explain the expensive one. Both belong in the cost lesson.
3. **The ceiling.** The approved ceiling is $30 a month. Whether a two-connector AWS stack fits under that depends on prices that change and must be measured, not asserted here. If it does not fit, the lesson is the finding, not a failure.
4. **Credentials.** The current Spacelift account has no OIDC token on its plan (see `docs/spacelift-secrets.md`), so cloud access comes from a Doppler secret. AWS role assumption and Azure/GCP federation are better practice where available. The lessons teach the better pattern and the build uses what the plan supports, with the trade-off written down.

## 5. The module contract

Parallel trees stay parallel only if they honour the same interface. Each provider's three modules expose the same variables and outputs, so a learner can diff `modules/vpc` against `modules/aws/vpc` and see only the provider's own nouns change.

| Module | Inputs (shared) | Outputs (shared) |
|---|---|---|
| `vpc` | `layer`, `region`, `ip_range` | `id`, `ip_range`, and whichever provider IDs a stack needs, documented per provider |
| `firewall` | `layer`, `region`, `purpose`, `membership` (replaces the DigitalOcean `tag`), `extra_outbound_rules`, `inbound_from_membership_rules`, `outbound_to_membership_rules` | `id` |
| `twingate-connector` | `name`, `region`, `size`, `reboot_time`, the Twingate inputs, the SSH inputs | the instance identity and its private address |

Two things in the contract are deliberate:

- **`size` is a provider-native string**, not a normalised "small". A learner must meet `s-1vcpu-1gb`, a burstable instance type and a shared-core machine type by name, because the next job will not use the abstraction.
- **Membership, not tag.** Rename carefully: the existing DigitalOcean module keeps its `tag` input unchanged. The contract describes the *concept*; a short mapping table in each provider's module README says "membership = tag" on DigitalOcean and GCP, "membership = security group" on AWS.

**Enforcement.** A test, not a convention. For each provider directory, a `tofu test` with mocked providers asserts the variable and output names match the contract. A test that fails when AWS drifts from DigitalOcean is also a teaching artefact: "why does CI care that these match?" is a good question for page three.

## 6. The cost gate across providers

`scripts/cost_check.py` has `digitalocean_`-prefixed allow-lists and reads `docs/cost-prices.json`. It generalises without losing its safety property (an unknown resource type fails the build):

- Prices move to per-provider tables, `docs/cost-prices/<provider>.json`, each with `retrieved`, `source` and an honest `verified` flag, as the current file already does.
- The free-resource allow-list becomes per provider, keyed by the resource-type prefix (`aws_`, `azurerm_`, `google_`).
- The check stays: modules matched to manifests, planned total at or under the approved total, approved total at or under the ceiling.
- **AWS-specific costed items must be declared**: the public IPv4 address, any NAT gateway, any disk beyond the default. An AWS stack that quietly adds a NAT gateway must fail the gate, the way an unlisted droplet does today.

The gate is the part most worth getting right first, because the main risk of teaching a learner AWS is a surprise bill.

## 7. The lessons: how a learner actually learns this

Structure, so that nobody can finish by pasting commands:

1. **Account preparation page per cloud** (this is the work the issue calls the hardest). Each covers: creating the account and what it costs to do so; securing the root or owner identity; multi-factor authentication; a billing alert and a budget **before** any resource exists; the structure above the project (organization, subscription, folder); and the first non-root identity. Written so a learner finishes with a protected, empty, alarmed account. Nothing in these pages touches this repository's code.
2. **"The same four pieces" page per cloud.** Network, packet filtering, a machine, an identity, mapped to the DigitalOcean originals using the section 4 table. Each ends with predict-then-check exercises of the kind used on the capstone page, for example: *before you read the AWS firewall module, predict what replaces the tag.*
3. **A "why they differ" concept page** (shared across clouds): attachment models, egress cost, identity for machines, global versus regional networks. This is where the comparison lives once, not three times.
4. **A cost lesson per cloud**, with the surprise-bill cases named: the unattached address, the NAT gateway, the forgotten snapshot, the free tier that expires.
5. **A status line at the top of every cloud page**: *Author-verified* (built and applied by the author), *Reviewed* (a named class of reviewer who runs this cloud has read it), or *Unverified draft* (written from documentation, not run). Azure and GCP pages start as unverified drafts and say so. This is the honest answer to the author's own point that those two are not their daily work, and it invites the community review that makes them trustworthy.

Every cloud-specific vendor claim carries a retrieval date, as elsewhere in the wiki.

## 8. Phases

Each phase ends at a review point and a pull request the operator merges. None starts without approval.

| Phase | Deliverable | Cost | Who must be involved |
|---|---|---|---|
| 0. Verify | Re-check every row of the section 4 table against current vendor documentation and date it. Settle the AWS egress choice with measured prices. | None | Author |
| 1. Lessons: AWS | Account preparation, "same four pieces", cost lesson, status line | None | Author reviews, since AWS is their strength |
| 2. Contract and tests | The module contract, the drift test, per-provider cost tables, the generalised cost gate with the DigitalOcean tree unchanged | None (CI only) | Author |
| 3. AWS code | `modules/aws/*`, `stacks/aws/*`, mocked tests, cost manifest, a stage doc. Not applied. | None until applied | Author reviews; adversarial review before any apply |
| 4. AWS apply (optional) | Applied by the operator through Spacelift, torn down after | Real, small, time-boxed | Operator |
| 5. Lessons: Azure and GCP | Same shape as phase 1, labelled Unverified draft | None | A reviewer who runs the cloud, sought openly |
| 6. Azure and GCP code | Only when a reviewer has signed off the lessons | None until applied | Reviewer plus author |

Phases 0 to 3 touch no running infrastructure and cost nothing, so they can proceed ahead of the edge DMZ and stage 1 hardening work without conflict.

## 9. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Code for a cloud the author does not run is wrong in ways that look right | A learner trusts it. The failure may be a bill or an open port. | Lessons before code; the status labels; no Azure or GCP code without a reviewer who runs them; mocked tests plus adversarial review. |
| AWS surprise cost (NAT gateway, public IPv4, forgotten resources) | A hard budget is the founding constraint. | Cost gate declares and fails on these; billing alert is step one of the account lesson; apply is time-boxed and torn down. |
| The three trees drift | The comparison stops being a comparison. | The contract test in phase 2. |
| Static cloud credentials in Doppler | A long-lived key is a bigger target than a role. | Teach role assumption and federation; build with the least-privileged credential the plan supports; rotation dates recorded as for the DigitalOcean token. |
| Vendor facts go stale | The tables are the most perishable text in the repo. | Retrieval dates on every row; a roadmap entry to re-verify on a schedule. |
| The public repository leaks an account id, tenant or subscription | Cloud identifiers are hard to scrub from history. | Same rule as today: identifiers live in Doppler, never in files; gitleaks stays on; the lessons use obvious placeholders such as `123456789012`-style example ids and say so. |
| Scope runs into the edge DMZ and stage 1 hardening work | Both change the same modules. | Phases 0 to 3 leave the DigitalOcean tree alone and are additive. |

## 10. Open questions for the operator

1. **Option B with D first**, as recommended, or do you want separate repositories per cloud as the issue's wording suggests?
2. **AWS code before Azure and GCP lessons**, or all three sets of lessons before any code?
3. **Is a real AWS apply in scope** (phase 4), and under which account? A learner-grade throwaway account is safer than anything near a work account.
4. **Do you want to ask the community for Azure and GCP reviewers** in the issue now, so reviewers exist by the time phase 5 starts?
5. **Cost ceiling for an AWS stage**: the same $30, or a separate approved ceiling per provider?

## 11. What this design does not claim

It does not claim the section 4 vendor facts are current, that a two-connector AWS stack fits the ceiling, or that the module contract survives contact with Azure's network model unchanged. Phase 0 exists to find out, and the design changes if the answers do.
