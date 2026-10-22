# Enterprise infrastructure: how large organizations run it differently

> **Orientation, not a design guide: verified claims dated.** Claims checked against a vendor page carry the date they were checked (2026-10-16) and the source in the claims register at the bottom. Everything else is general industry knowledge or marked UNVERIFIED. Nothing here has been built in this repository.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Enterprise engineering habits](Enterprise-Engineering-Habits.md), [Architecture overview](Architecture-Overview.md) and [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md). [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) is a useful companion for the network sections.

This project is one account, one environment, one operator and two machines. The habits it practices are the right ones. What changes at a company is **how many of everything there is** and **how many people must agree**. Almost every practice below exists because something went wrong when there were too many accounts, too many engineers or too many years for informal agreement to work.

Each section ends with what this project does instead and why that is fine at its size.

## Contrast at a glance

| Topic | In this project | In an enterprise |
|---|---|---|
| Accounts | One DigitalOcean account | Many cloud accounts, subscriptions or projects arranged in a hierarchy |
| Guardrails | Cost gate and CI checks in the repository | Organization-level policy that applies whether or not the repository's checks ran |
| Cost tracking | A cap checked on every pull request | Tags, allocation to teams, budgets and a FinOps practice |
| Servers | Two identical droplets, rebuilt from cloud-init | Hundreds to thousands, built from golden images, patched on a schedule |
| Inventory | `stacks/` is the inventory | A CMDB or asset inventory fed by discovery |
| IaC | Two stacks in one repository | Module registries, a state per environment, policy-as-code, drift detection |
| Delivery | PR, CI, Spacelift, human confirm | Environments (dev, test, prod), approvals, change windows |
| Resilience | Rebuild from code; no promises | Recovery objectives, multi-region, tested backups |
| Watching | Planned: Wazuh at home | NOC, SOC, a SIEM, on-call rotations |
| Vendors | Free tiers, no contracts | Procurement, security reviews, contracts, renewals |

## Many accounts, in a hierarchy: landing zones

A **landing zone** is a pre-built, governed place for teams to put workloads: accounts or subscriptions already wired to central logging, networking and identity, with guardrails already attached. Providers describe the hierarchy in their own words: AWS Organizations groups accounts into organizational units; Azure uses management groups above subscriptions; Google Cloud uses an organization, folders and projects. Why many accounts? An account is the strongest boundary a cloud offers for permissions, quotas, billing and blast radius. One account per application per environment is common.

**What this project does instead.** One account, one project, tags and a firewall for separation. At two machines, a hierarchy would cost more attention than it protects.

## Organization policy and guardrails

IAM answers "who may do this." A guardrail answers "what may be done at all, by anyone in this part of the organization." The three big clouds each have one.

- **AWS service control policies (SCPs)** set the maximum permissions available to IAM users and roles in member accounts; an SCP never grants anything, and does not apply to the management account (verified in the register).
- **Azure Policy** evaluates resources against rules (allowed regions, required tags, diagnostics enabled) at a management group, subscription, resource group or resource scope, with effects such as deny, audit or modify.
- **Google Cloud Organization Policy** sets constraints on how resources may be configured, inherited down the organization, folders and projects; the docs contrast it with IAM as "what" versus "who".

All three can stop a change that CI would have approved, because the guardrail sits in the cloud, not in the repository. That is a feature: the check cannot be skipped by a pipeline that was edited.

**What this project does instead.** The cost gate and the CI checks live in the repository and in Spacelift. A person with the provider's console could ignore them; the [threat model](Threat-Model.md) accepts that for a one-person lab. It is fine because the only person who could bypass the guardrail is the owner.

## Tagging, cost allocation and FinOps

At scale the bill is split among teams, and nobody can split what is not labeled. Organizations enforce tags (owner, cost center, environment, application) with the guardrails above, set budgets with alerts, and have a **FinOps** practice: engineers, finance and product reviewing spend together, rightsizing, buying commitments and removing waste. The FinOps Foundation publishes a framework; this page has not checked its current text, so treat the name as a pointer.

**What this project does instead.** One bill, one owner, and a [cost gate](CI-Tests-and-Cost-Gate.md) that refuses a pull request whose monthly estimate exceeds the approved ceiling. It is fine because the gate answers the question FinOps answers, "should this be allowed to cost that?", before the money is spent, for the one stakeholder who exists.

## Golden images and patching

A **golden image** is a pre-built, pre-hardened machine image that every server starts from, built by a pipeline (Packer is a common tool) and versioned. Patching then becomes "build a new image, roll it out, retire the old" instead of logging in to each machine. The same ideas run in parallel with regulated windows, vulnerability scanning, severity timelines and exceptions that someone signs.

**What this project does instead.** The droplets are rebuilt from cloud-init on a stock Ubuntu image, and hardening is code ([Droplet hardening](Droplet-Hardening.md)). Rebuilding is cheap because there are two of them and nothing on them is precious. A golden-image pipeline is the next step if the count ever reaches double digits.

## CMDB and asset inventory

A **configuration management database (CMDB)** records what exists, who owns it, what depends on what. Real ones are often wrong, because they are fed by humans or by discovery tools that see only part of the estate. Auditors, incident responders and patch teams all start from "what do we have?" and a bad answer costs time everywhere. Cloud inventory services, EDR agent lists and network scans are the usual sources, reconciled against each other.

**What this project does instead.** The code is the inventory: if it is not in `stacks/`, it should not exist, and the plan shows any difference. That is infrastructure as code doing the CMDB's job, and it works until someone creates something by hand, which is what [drift detection](#iac-at-scale) is for. Be careful what a plan can see: it compares code with resources tracked in state, so an extra droplet created in the console is invisible to a clean plan and can stay billable or exposed. The intended inventory (code) and the actual inventory (what the cloud account contains) are different things; finding the difference needs separate discovery and reconciliation, such as listing the account's resources and comparing them with state.

## IaC at scale

Everything on [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) still holds. What grows around it:

- **Module registries.** Shared modules versioned and published internally, so a team uses the approved network module rather than writing its own. This repository's `modules/` directory is the small version.
- **State per environment, and per blast radius.** One state file for a whole company would be unusable and dangerous. States are split by environment and by component, with locking and tight access (state can contain secrets, as [Doppler and secrets](Doppler-and-Secrets.md) notes for connector tokens).
- **Policy as code.** Rules about what a plan may contain, evaluated automatically on the plan. Open Policy Agent (OPA) and HashiCorp Sentinel are the two names you will meet most; Spacelift, used here, supports OPA-based policies (see its docs for specifics).
- **Drift detection.** A scheduled plan that reports when the real world differs from the code.
- **Review gates.** Required reviewers, code owners for sensitive paths, signed commits.

**What this project does instead.** Two stacks, two states in Spacelift, a push policy, a human reading every plan. It is fine because the plan fits on a screen; the practices above exist for plans that do not.

## CI/CD with environments and approvals

The pipeline here has seven gates ([capstone](Fork-Private-Stacks-and-the-Pipeline.md#where-the-pipeline-actually-starts)). Enterprises add **environments** (dev, test, staging, production) with different people allowed to promote between them, **approvals** that name the roles required, deployment strategies (canary, blue-green, feature flags) and **change windows**. Many regulated organizations require a change record before production changes; that is the subject of [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md), and [Trace one change end to end](Trace-One-Change-End-to-End.md) shows this project's version.

**What this project does instead.** One environment, which is production, with a human confirm at apply. Fine because there are no users to protect from a bad change except the author.

## High availability, disaster recovery and backups

| Term | Meaning |
|---|---|
| **RTO** (recovery time objective) | How long the business can tolerate a service being down |
| **RPO** (recovery point objective) | How much recent data it can tolerate losing, measured in time |
| **HA** (high availability) | Design that survives the failure of a component without an outage |
| **DR** (disaster recovery) | The plan and capacity to restore service after losing a site or region |

To work these out from a schedule and time a restore yourself, see [Backups, recovery and patching](Backups-Recovery-and-Patching.md#rpo-and-rto-in-plain-words). An RTO of four hours and an RPO of fifteen minutes lead to specific, costly designs: replicas, a second region, frequent backups. Backups are only real once restored in a test; many organizations keep an **immutable** copy that ransomware cannot encrypt, and test restores on a schedule. Multi-region deployment is the usual answer to a regional outage, and it doubles a lot of what this project calls its cost.

**What this project does instead.** Two connectors in one region give a little redundancy (Twingate can use either), and the whole thing is rebuilt from code with a state in Spacelift. The recovery objective is, in effect, "an evening". That is fine for a teaching lab, and exactly the thing to write down as an accepted risk.

## Observability: SIEM, NOC, SOC and on-call

A **NOC** keeps the service up; a **SOC** keeps it safe; a **SIEM** collects the events both want. Someone has to be woken when an alert fires, so there is an **on-call rotation** with a runbook, an escalation path and a post-incident review. The lessons for this are on [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md).

**What this project does instead.** Planned: a Wazuh agent on each host reporting to a home SIEM, and the operator as the on-call rotation. Fine because the cost of an hour of silence is zero; the lesson is the shape, not the staffing.

## Vendor management and procurement

Buying a product at a company involves a security questionnaire, a review of the vendor's own certifications (a SOC 2 report or ISO 27001 certificate are the ones asked for most often), a data-processing agreement, legal and finance sign-off, and a renewal date someone must remember. The decision is rarely purely technical: "we already pay for that" settles many arguments. Exit planning matters too: how do you get your data and configuration out?

**What this project does instead.** Free or small tiers, public pricing, and a stated preference for open and replaceable parts. Fine because switching away from any of them costs hours, not a project.

## Shared responsibility

Cloud providers publish a **shared responsibility model**: they secure the platform; you secure what you put on it. The line moves with the service: you patch the operating system on a virtual machine, but not on a managed database. The practical effect is that "the cloud is secure" is half a sentence. Every enterprise audit asks who owns each control.

**What this project does instead.** The droplets are your responsibility down to the operating system, and that is why [hardening](Droplet-Hardening.md) exists. Fine, and instructive: the example is built to show which layer is yours.

## Hybrid, mergers and legacy

Few large organizations are cloud-only. They run data centers, colocation space and several clouds at once, often because of **mergers**: when two companies join, so do their networks, identity providers, ticket systems and security tools, none of which were designed to meet. Legacy systems nobody dares touch are found in every estate, and their risk is managed with isolation, compensating controls and a retirement plan. The skills that matter are inventory, careful change, and writing things down.

**What this project does instead.** Nothing old, nothing merged, nothing hybrid. This is the biggest thing a small example cannot teach, as the landscape page says.

## Predict, then check

1. A developer with full administrator rights in a cloud account tries to create a resource in a region the company has banned. The CI checks passed. What stops it, and where does that control live?
2. A company's finance team cannot tell which team caused a bill increase. Name the control that is missing, and a guardrail that would enforce it.
3. A server cannot be patched this month because the application owner cannot be found. Which two records from this page are probably weak?
4. Name two reasons one state file for the whole company would be a bad idea.
5. An RTO of 15 minutes is requested for a service this project runs. What is the first thing you would say about the design?

### Reference answers

1. An organization-level guardrail: an SCP, Azure Policy or Organization Policy constraint, depending on cloud. It lives in the cloud provider's organization layer, outside the repository, so it applies however the change was made. (Which exact policy type depends on the cloud; the register has the sources.)
2. Cost allocation: required tags (owner, cost center) and budgets per team. A policy that denies or flags resource creation without the tags enforces it.
3. The CMDB or asset inventory (no owner recorded) and the golden-image or patch process (no accountable owner for exceptions).
4. Locking and speed: every change by every team queues behind one lock. Blast radius and secrets: anyone with access to read it reads everything, and one corruption affects everything. Split by environment and component.
5. Two connectors in one region cannot promise a 15-minute RTO against a regional or account-level failure. It needs a second region or a tested automated rebuild and a clear statement of which failures it covers.

## Try it yourself

- For each section above, write the one sentence from "what this project does instead" in your own words, then say what event would make it stop being fine.
- Take one of the guardrails (SCP, Azure Policy or Organization Policy) and read its first documentation page. Write down one thing it can do that a pull-request check cannot.
- Draw the account layout you would want if this project had three environments and two teams.
- Write the RTO and RPO you would honestly accept for this lab, and what you would have to change to halve each.

## Claims register

Status is one of: `Verified <date>`, `General knowledge` (widely held industry usage, not checked here), or `UNVERIFIED`.

| Claim | Status | Source |
|---|---|---|
| AWS SCPs set the maximum permissions for IAM users and roles in member accounts, never grant permissions, and do not affect the management account | Verified 2026-10-16 | https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html |
| Azure Policy evaluates resources against rules at management group, subscription, resource group or resource scope, with effects including deny and audit, and can enforce allowed regions and tag requirements | Verified 2026-10-16 | https://learn.microsoft.com/en-us/azure/governance/policy/overview |
| Google Cloud Organization Policy sets constraints on how resources are configured, inherited from organization to folders to projects; IAM decides who, Organization Policy what | Verified 2026-10-16 | https://docs.cloud.google.com/resource-manager/docs/organization-policy/overview |
| An account or subscription is the strongest boundary a cloud offers for permissions, quotas and billing | General knowledge | not checked |
| AWS uses organizational units, Azure management groups, Google Cloud folders | General knowledge | the Azure and Google terms appear in the sources above; AWS OU term not re-checked |
| Spacelift supports OPA-based policies | UNVERIFIED | see the Spacelift page and its documentation; not re-checked for this page |
| The FinOps Foundation publishes a FinOps framework | UNVERIFIED | name given as a pointer only |
| Packer is a common golden-image tool | General knowledge | not checked |
| OPA and Sentinel are the common policy-as-code engines | General knowledge | not checked |
| SOC 2 and ISO 27001 are the certifications vendors are most often asked for | General knowledge | not checked |
| Providers publish a shared responsibility model | General knowledge | not checked |

Next: [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md), then [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md). Back to the [Reading order](Reading-Order.md).
