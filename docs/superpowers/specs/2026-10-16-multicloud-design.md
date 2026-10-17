# Clouds Against Humanity: Other Clouds (AWS, Azure, GCP)

Status: DRAFT for review. Date: 2026-10-16, revised the same day after an adversarial review (Codex) that found the cost-gate, contract, credential and Azure points now reflected below. Issue: #22. Phase 0 (vendor fact check) is done: see [the findings](2026-10-16-multicloud-phase0-findings.md); where they differ from this document, the findings win.
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
| `modules/vpc`, `modules/firewall`, `modules/twingate-connector` resources | **No** | They create `digitalocean_*` resources. The `digitalocean_` name appears in every production `.tf` file of the three modules and two stacks. |
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
| Packet filtering | Cloud firewall attached **by tag** | Security group attached to the instance's network interface; a rule's source or destination can be **another security group** (resolved to private addresses, with topology limits) | Network security group attached to a subnet or interface; **application security groups** separately group interfaces for use in rules | VPC firewall rules on the network; a rule's **target** is chosen by network tag or service account, and its ingress **source** by address range, tag or service account, with restrictions on mixing them |
| Statefulness and defaults | Stateful; explicit outbound rules in this repo | Stateful; new groups allow all outbound by default | Stateful; default rules allow outbound | Stateful; implied allow egress, implied deny ingress |
| How a "no inbound" VM still reaches the internet | Public IP on the droplet, inbound filtered | Public IPv4 on the instance **or** a NAT gateway | Only subnets in virtual networks created with the API version released after 2026-03-31 default to private; older API versions (including a pinned Terraform provider) and all existing networks keep default outbound access, so **set it explicitly** and choose a method (public IP, NAT gateway or load-balancer outbound rule); verified in phase 0 (2026-10-16) | A public IP **or** Cloud NAT; Cloud NAT is the cheaper pattern on GCP only at low traffic (below roughly 36 GiB a month processed) |
| Machine identity | None needed here | Instance profile (an IAM role) | Managed identity | Service account |
| How Spacelift authenticates to the cloud | One API token from Doppler | Spacelift's native AWS integration (an assumable role, short-lived credentials), or access keys | Native Azure integration, or a service principal | Native GCP integration, or a service account key |
| Smallest sensible instance | `s-1vcpu-1gb` | a small burstable instance type | a small burstable VM size | a small shared-core machine type |
| Cost shape | Droplet price, nothing hidden | Instance, **plus** public IPv4 address charge, **plus** a NAT gateway if used | VM, plus public IP, plus disk SKU | VM, plus external IP, plus Cloud NAT if used |

Four points in that table reshape the design and are worth stating plainly:

1. **Three different firewall ideas, not one.** Every cloud's filtering answers three separate questions: *which machines does this rule set attach to* (the target), *who is allowed to reach them* (the source), and *what can they reach* (the destination). DigitalOcean answers all three with one tag, which is why `modules/firewall` takes a single `tag` and the rules in this repo say "only droplets carrying this tag". AWS attaches a security group to an interface and writes the source as a reference to another group. Azure attaches an NSG to a subnet or interface and uses application security groups to name sets of interfaces. GCP chooses targets and sources by tag or service account with restrictions on combining them. Hiding that behind one abstract "membership" input would erase the most instructive difference in the whole project, so the contract in section 5 names the three roles separately and lets each provider fill them with its own objects.
2. **Egress is a cost decision.** The "zero public inbound ports" design still needs outbound reachability for Twingate. On DigitalOcean that is free: a public address with all inbound filtered. On AWS the same shape costs a public IPv4 address charge per instance, and the "private subnet plus NAT gateway" textbook answer costs far more than the whole current environment. The design must make the cheap, honest choice and explain the expensive one. Both belong in the cost lesson. Under a $30 ceiling a NAT gateway on AWS (an hourly charge that alone is about the size of the whole ceiling, before address and per-gigabyte processing charges) is **rejected outright**, not merely declared.
3. **What the ceiling can promise.** The $30 is an **approved fixed monthly infrastructure** figure: the sum of the prices of the things the stack declares. It is not a hard cap. Data transfer, NAT or gateway processing, logging, snapshots and anything created outside OpenTofu are metered by use, and cloud budgets and alerts notify without stopping spending. The documents say so in those words. If a stage needs a real cap, that is a separate control (quotas, deny policies, automated teardown) with its own residual risk written down. Whether a two-connector AWS stack fits the fixed figure depends on prices that change and must be measured at phase 0; if it does not fit, the lesson is the finding, not a failure.
4. **Credentials are a trust-boundary change, not a variable.** The secrets hook loads names, but the Doppler token attached to a Spacelift context can read the whole Doppler config, and the runbook already records that code on a tracked run could read it directly. Putting AWS, Azure and GCP credentials in the same config would turn a compromise from one DigitalOcean environment into four cloud control planes. So: **one Doppler project/config and one Spacelift context per cloud**, each with its own narrow token, attached only to that cloud's stacks; and prefer Spacelift's native AWS, Azure and GCP integrations, which issue short-lived credentials, over static keys. Phase 0 checks what the current Spacelift plan allows (the DigitalOcean setup used Doppler because the plan had no run-level OIDC token, which is a separate matter from cloud integrations). Verification is a test, not a promise: from one stack, request another cloud's secret and show the secret store refuses it.

## 5. The module contract

Parallel trees stay comparable only if they agree on what a stack consumes. The contract is **semantic, not an exact variable-for-variable match**, because the clouds really do need different inputs (an SSH key is a fingerprint plus a key on DigitalOcean and a key-pair name, or none, on AWS) and the existing DigitalOcean modules already differ from any idealised interface.

The contract has three parts:

1. **Outputs a stack consumes**, named the same on every provider: for `vpc`, an `id` and the address range; for a connector, the instance identity and its private address; for the firewall, an identifier a stack can depend on. The existing DigitalOcean modules will gain these outputs (additively, no input changes) so the contract is true of them too.
2. **The three firewall roles** from section 4: `rule_targets` (what the rules attach to), `source_members` and `destination_members` (who may reach it and what it may reach). On DigitalOcean the target and the member-to-member source and destination are the tag the module takes today; **internet egress is separate**, because the module sends its default and extra outbound rules to `0.0.0.0/0` and `::/0` and only the connector-to-connector rules use tags. The contract therefore keeps *internet egress rules* (address ranges) apart from *member rules* (`source_members`, `destination_members`), and each provider maps both; on AWS the first is a security group and the others are references to groups; and so on. Each provider's module README has a short table: *role, DigitalOcean object, this provider's object*.
3. **A provider-extension namespace**: inputs that exist only on one cloud (the DigitalOcean account key fingerprint, an AWS key-pair name) are documented as extensions, not forced into a shared shape.

`size` stays a provider-native string, not a normalised "small": a learner must meet `s-1vcpu-1gb`, a burstable instance type and a shared-core machine type by name, because the next job will not use the abstraction.

**What is shared in code, not just in name.** The Twingate resources and the cloud-init bootstrap (hardening, connector install, update schedule, token handling) are the same on every cloud. Today they live inside the DigitalOcean connector module. Before a second provider exists, phase 2 **extracts them** into a neutral module that every provider's connector module calls. Otherwise each provider copies the security-relevant part, and a hardening fix reaches only one of them. **Moving the Twingate resources into a nested module changes their state addresses** (for example `module.connector_a.twingate_connector_tokens.this`), so a plain extraction would make the live DigitalOcean plan propose replacing connector tokens. Phase 2 therefore includes explicit `moved` blocks for every moved resource, and its gate is a plan on both live stacks that shows **no changes**, not just a passing test.

**Enforcement is two tests, not one.**
- A *structural* test per provider (mocked providers): the outputs in part 1 exist, the extensions are declared.
- A *behaviour* test on the shared bootstrap: the rendered cloud-init contains the expected hardening and update lines, and the test runs against every provider's rendered output. Proving it works means changing the bootstrap and watching every provider path receive the change.

Why this is also a lesson: "why does CI care that these match, and what can it not tell you?" is a good question for page three.

## 6. The cost gate across providers

`scripts/cost_check.py` has three limits that matter here, each found in review and each shown against the design as first written:

- **It only finds manifests at `stacks/*/cost.json`.** A manifest at `stacks/aws/10-access/cost.json` would be invisible, and the gate would keep reporting the DigitalOcean total while an expensive AWS stack existed. The fix is recursive discovery, an assignment of every stack directory to exactly one provider, and a failure if any stack directory has no manifest. Verification: a fixture AWS manifest over the ceiling must fail the gate.
- **It reads resource types from source, and the expensive AWS items are attributes.** A public IPv4 address on an instance and a root volume size are settings inside `aws_instance`, not separate resources, and `for_each` and `count` multiply things the source does not show. Declaring "AWS charges must be declared" is not enough. For non-DigitalOcean providers the gate must cost the **planned values from an OpenTofu plan as JSON**, where those attributes and counts are resolved. The plan has to come from somewhere trustworthy: the credentialless pull-request CI cannot produce a real AWS, Azure or GCP plan, and a hand-edited or checked-in JSON file goes stale. So the design offers two routes, to be chosen in phase 0: (a) a **declarative cost input** reviewed in the pull request and **reconciled against the plan** produced by the trusted Spacelift run before anything is applied (a mismatch fails the run); or (b) a plan generated in CI with mocked providers and fixed values, used only to test the gate itself. Either way the gate that protects spending runs where the real plan exists, and the pull-request check is the early warning, not the guarantee. Also scope the existing module-to-manifest reconciliation (it currently counts every `twingate-connector` module against every `droplet` entry across the repository) by provider and stack, or define a provider-specific equivalent, otherwise valid AWS resources will be miscounted against DigitalOcean entries. Verification: fixtures for an implicit public IP, a large root volume, an explicit elastic IP, a NAT gateway, and a `for_each` must each be priced or rejected correctly.
- **It prices only fixed things.** See section 4, point 3.

With those fixed, the rest generalises as before: prices move to per-provider tables, `docs/cost-prices/<provider>.json`, each with `retrieved`, `source` and a `verified` flag; the free-resource allow-list is per provider by resource-type prefix (`aws_`, `azurerm_`, `google_`); an unknown resource type still fails the build; the planned total must be at or under the approved total, and the approved total at or under the ceiling. A NAT gateway on AWS is on the reject list at the current ceiling.

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
| 0. Verify | **Done 2026-10-16**, see [the findings](2026-10-16-multicloud-phase0-findings.md). Re-checked the section 4 table against vendor documentation and price lists, and settled the AWS egress choice with measured prices. The Spacelift plan gate is still open. | None | Author |
| 1. Lessons: AWS | Account preparation, "same four pieces", cost lesson, status line | None | Author reviews, since AWS is their strength |
| 2. Contract, shared bootstrap, gate (**split: 2a shared bootstrap, 2b contract outputs and tests, 2c cost gate and identifier check**) | Extract the shared Twingate and cloud-init module; the semantic contract and its two tests; recursive manifest discovery; plan-JSON costing; per-provider price tables; the identifier check; per-cloud secret separation. The DigitalOcean stacks must produce an unchanged plan. | None (CI only) | Author; adversarial review |
| 3. AWS code | `modules/aws/*`, `stacks/aws/*`, mocked tests, cost manifest, a stage doc. Not applied. | None until applied | Author reviews; adversarial review before any apply |
| 4. AWS apply (in scope, throwaway account) | Applied by the operator through Spacelift, torn down after | Real, small, time-boxed | Operator |
| 5. Lessons: Azure and GCP | Same shape as phase 1, labelled Unverified draft | None | A reviewer who runs the cloud, sought openly |
| 6. Azure and GCP code | Only when a reviewer has signed off the lessons | None until applied | Reviewer plus author |

Phases 0 to 3 touch no running infrastructure and cost nothing. Phase 2 does edit the DigitalOcean connector module (extracting the shared part), so it must be sequenced with the edge DMZ and stage 1 hardening work, and its acceptance test is that the two live stacks plan with no changes.

## 9. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Code for a cloud the author does not run is wrong in ways that look right | A learner trusts it. The failure may be a bill or an open port. | Lessons before code; the status labels; no Azure or GCP code without a reviewer who runs them; mocked tests plus adversarial review. |
| AWS surprise cost (NAT gateway, public IPv4, forgotten resources) | The founding constraint is a small budget. The approved figure covers declared fixed infrastructure only, not metered use. | The gate rejects or prices the declared fixed items; the billing alert is step one of the account lesson; apply is time-boxed and torn down. **Residual:** alerts notify, they do not stop spending, and variable charges (transfer, processing, logging) stay outside the guarantee. |
| The three trees drift | The comparison stops being a comparison, and a security fix reaches one provider only. | The shared bootstrap module and both contract tests in phase 2. |
| Several clouds' credentials reachable from one place | One compromised tracked run would reach every control plane. | Section 4, point 4: a Doppler config and Spacelift context per cloud, native short-lived integrations preferred, a test that one stack cannot read another cloud's secret. |
| Vendor facts go stale | The tables are the most perishable text in the repo. | Retrieval dates on every row; a roadmap entry to re-verify on a schedule. |
| The public repository leaks an account id, tenant or subscription | Cloud identifiers are hard to scrub from history, and a secret scanner does not flag them: they are mostly not secrets. | Identifiers live in the secret store, never in files. Add an identifier check built on structural patterns (ARNs, subscription UUID fields, project ids) that runs in pull-request CI with no secret values. Searching for the author's *real* identifiers would need them as CI secrets, and pull-request workflows run branch-controlled code that can print environment values, so that variant runs only in a trusted post-merge or protected environment, never on pull requests. Lessons use obviously synthetic placeholders that the check allow-lists by name, and avoid realistic-looking twelve-digit account numbers. Verification: seed a fixture with each real form and see CI reject it. |
| Scope runs into the edge DMZ and stage 1 hardening work | Both change the same modules. | Phases 0, 1 and 3 are additive. Phase 2 edits the connector module and is sequenced after that work, with a no-change plan on the live stacks as its gate. |

## 10. Decisions

Answered by the maintainer on 2026-10-16. The original questions and the options considered are in the history of this file.

| # | Question | Decision |
|---|---|---|
| 1 | Repository layout | **One repository with provider directories.** The DigitalOcean tree stays where it is. A cloud can move to its own repository later if a maintainer shows up to own it. |
| 2 | Sequencing | **AWS lessons, then AWS code, then Azure and GCP lessons.** Azure and GCP pages are labelled Unverified draft until a reviewer who runs the cloud has read them. |
| 3 | A real AWS apply | **In scope, in a throwaway personal AWS account**: time-boxed, torn down afterwards, with a billing alert set first and nothing else in the account. |
| 4 | Reviewers for Azure and GCP | **Ask now**, in the issue. |
| 5 | AWS cost limit | **A separate approved figure per cloud**, for fixed declared infrastructure only, under the shared ceiling. The documents say plainly this is not a hard cap: metered use is outside the guarantee and billing alerts only notify. |
| 6 | Credentials | **Wait until Spacelift's native AWS integration is confirmed on the current plan** (phase 0), so no long-lived AWS key is needed. If it is not available, return to the maintainer before falling back to a static key in a separate Doppler config. |

Consequences for the phases in section 8: phase 0 gains a gate (confirm the Spacelift AWS integration on the current plan before any AWS stack is created), phase 4 is in scope but waits for phase 2's gate and per-cloud secret separation, and `docs/stages/approved.json` will need a per-cloud structure in phase 2.

## 11. What this design does not claim

As of phase 0 (2026-10-16) the section 4 vendor facts were checked against vendor documentation and price lists; rows still marked UNVERIFIED in the [evidence files](2026-10-16-multicloud-phase0-evidence-aws.md) are not claimed, and vendor facts go stale, so each carries its retrieval date. The design does not claim that the budget is a hard cap, that the AWS stack has ever been applied in a real account (the measured fixed cost is an estimate from list prices), that the Spacelift AWS integration is available on the maintainer's plan (still the open gate), or that the module contract survives contact with Azure's network model unchanged. The design changes if any of those answers do.

## 12. Phase 2a: what was built and how it was checked

`modules/twingate-bootstrap` now holds the Twingate connector, its tokens and the cloud-init template; `modules/twingate-connector` (DigitalOcean) calls it, with two `moved` blocks. The template is byte-identical, so the droplet's `user_data` does not change. The 27 hardening and token tests moved to the bootstrap module and run against its `user_data` output; the DigitalOcean module keeps tests that its droplet uses that output and carries no private copy.

Evidence, not assertion:
- Changing one hardening line in the shared template fails the bootstrap tests **and** the DigitalOcean module's test, so a fix or a regression reaches every provider path.
- Dropping either `moved` block fails the DigitalOcean module's test.
- A rehearsal of the state move: a hand-written state with the connector and tokens at their old addresses, planned with the new code and `-refresh=false`, shows both as "moved" and nothing destroyed or replaced. The same state planned with the old code shows the identical remaining in-place note on the tokens, so that note comes from the hand-written state, not from the move.
- **Not yet done, and the real gate:** a plan on the two live stacks in Spacelift showing no changes. A hand-written state cannot prove that. It needs a proposed run on this branch, which only the maintainer can read.

## 13. Phase 2b: the contract as built

The contract is enforced in two places. Per provider, mocked-provider `tofu test` runs pin each output to its source. Across providers, `tests/test_module_contract.py` finds every `modules/vpc`, `modules/firewall` and `modules/twingate-connector` directory under the repository (so `aws/modules/...` too) and requires the contract outputs, a README with a role table, and a "Provider extensions" section.

| Role | Contract outputs |
|---|---|
| network | `id`, `ip_range`, `name` |
| firewall | `id`, `name`, `rule_targets`, `source_members`, `destination_members` |
| connector | `instance_id`, `instance_name`, `private_ip`, `size` |

What this cannot tell you: that the semantics match. A module can export `source_members` and fill it with something that does not mean "who may reach the targets". That is what review and the READMEs' role tables are for.

