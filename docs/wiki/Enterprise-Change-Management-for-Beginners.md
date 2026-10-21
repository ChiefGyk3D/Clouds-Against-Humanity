# Enterprise change management for beginners (not used in this project)

> **Orientation: general industry practice, not used by this project; frameworks cited with retrieval dates or marked UNVERIFIED.** Everything before the section "Is any of this used in this project?" describes how companies work. It is not a description of this repository, and this repository does not do it. Where a fact comes from a source, the source and the date it was read (2026-10-16) are given; where it does not, the page says UNVERIFIED.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) (what a pull request and a CI check are) and [Trace one change end to end](Trace-One-Change-End-to-End.md) (the real change this page re-dresses as an enterprise record). Helpful, not required: [A small example: what an enterprise does differently](Small-Example-Enterprise-Landscape.md).

If you take a job at a company of any size, someone will say "that needs a change ticket" or "we are in a freeze" or "bring it to CAB." This page is the decoder ring. It teaches the vocabulary and the reasoning, then shows honestly that this project uses almost none of it, and why that is fine here and would not be fine at a company.

## What change management is, and why enterprises have it

**Change management** is the set of rules a company uses to decide which changes to its systems are allowed, who has to agree, when they may happen, and how they are undone if they go wrong. A "change" is anything that could alter how a production system behaves: a firewall rule, a software release, a certificate renewal, a database setting, a new account with admin rights.

Two pressures create it.

1. **Changes cause outages.** Most unplanned downtime starts with someone changing something. The people who made the change often cannot see what else depends on it. A firewall rule that looks tidy to the network team can cut off a payroll batch job that another team owns. Change management is mostly a way of making sure the people who would be hurt find out *before* the change, not after.
2. **Auditors and regulators ask for proof.** A company that handles payments, health data, or financial reporting is expected to show that changes to its systems were authorized, tested, and traceable to a person. "We just do it carefully" is not evidence. A ticket with an approver, a test result and a timestamp is.

A third reason is human: when something breaks at 2 a.m., the first question is "what changed?". A reliable record of changes answers it in minutes instead of hours.

The honest counterweight, which engineers raise often and which the research below supports: heavy, slow approval processes do not reliably make systems safer. Modern practice tries to keep the *goals* (an informed decision, evidence, a way back, a record) while moving the *mechanism* from meetings to automation. Both halves matter, and the rest of this page covers both.

## The vocabulary

| Term | What it means | Why it exists |
|---|---|---|
| **Change request / RFC** (request for change) | The written proposal: what will change, why, when, who is affected. It is a ticket or record in a tracking system. | Nothing important should be changed from someone's memory. |
| **Standard change** | A low-risk, well-understood, repeatable change that has been pre-approved as a *type*. Example: rotating a certificate by a documented procedure. Each instance is logged, but nobody re-approves it. | Approving the same safe thing a hundred times is waste, and slow approval teaches people to bypass the process. |
| **Normal change** | A change that is assessed and approved each time, by someone with authority matched to its risk. This is the default. | Unfamiliar or risky changes deserve a fresh look. |
| **Emergency change** | A change that cannot wait for the normal cycle because something is broken or under attack now. It goes through a faster path and is reviewed *after* the fact. | A process with no fast path gets worked around. |
| **Change advisory board (CAB)** | A group that reviews proposed changes, usually the risky ones, and advises or decides. Members typically come from operations, security, the application teams and the business. | A wider view than the author has. |
| **Emergency CAB (ECAB)** | A small, on-call subset that can approve an emergency change in minutes. | Speed with some accountability. |
| **Change window** | The agreed time when a class of change may be applied, often a low-traffic night or weekend slot. | Limits who is affected if it goes wrong. |
| **Freeze period** | A time when ordinary changes are not allowed, for example the weeks around a retailer's peak season or a financial year-end. Emergencies still go through. | The cost of an outage is highest then. |
| **Risk and impact assessment** | Two questions answered in writing: how likely is this to go wrong (risk), and how bad is it if it does (impact: which services, how many users, for how long)? | Puts the approver's attention where it matters. |
| **Back-out / rollback plan** | The exact steps to return to the previous state, and the point at which you decide to use them. | A change you cannot undo is a different, much riskier kind of change. |
| **Test evidence** | Proof that the change was tried somewhere safe first: test results, a staging run, a link to a passing pipeline. | Approval based on a promise is weaker than approval based on a result. |
| **Approvals and separation of duties** | The person who writes a change is not the only person who approves it, and the person who approves is not the one who applies it where the control matters. | One person acting alone can make a mistake or abuse access without anyone noticing. |
| **CMDB / asset links** | A configuration management database: the inventory of systems and how they depend on each other. A change record links to the systems it touches. | Lets the assessor ask "what depends on this?" with data. In practice CMDBs are often incomplete, and an out-of-date one is worse than none. |
| **Post-implementation review (PIR)** | After the change: did it work, did it cause trouble, what do we learn? Done at least for failures and emergencies. | Closes the loop. |
| **Change failure rate** | The share of changes (or deployments) that needed immediate fixing afterwards. See the DORA section. | The measure of whether the process is actually working. |

## How it connects to incident, problem and release management

These are neighboring practices in the ITIL family of IT service management ideas, and the same event often touches several of them.

- **Incident management** restores service when something is broken *now*. An incident is often caused by a change, and fixing it may itself be an emergency change.
- **Problem management** finds and removes the underlying cause of repeated or serious incidents. A problem record often ends in a normal change ("fix the root cause"). This is the formal ancestor of the wiki's [Lessons learned](Lessons-Learned.md).
- **Release management** plans and coordinates what goes live together: bundling several changes into one release, with a schedule.
- **Change management** sits in the middle: it decides whether each proposed alteration, including the fixes that incident and problem management ask for, may go ahead.

ITIL is a widely used set of IT service management practices, published by PeopleCert (which took over from AXELOS; UNVERIFIED here). Version 4 renamed the old "change management" to **change enablement**. The common explanation, in secondary sources read on 2026-10-16, is that the new name signals that the practice should *enable* safe change at speed, not merely gate it, and that the three change types above (standard, normal, emergency) and a "change authority" (the person or group entitled to approve a given kind of change) are part of it. **UNVERIFIED against the primary source:** the official ITIL 4 text is a paid publication and the public AXELOS and PeopleCert pages could not be quoted, so the exact wording and the rename date (secondary sources disagree between late 2018 and early 2019) are not confirmed here. For the exact definition, read the official ITIL 4 publication from PeopleCert. Many companies use ITIL vocabulary without following it to the letter.

## Tooling

Change records live in a tracking system, usually the company's IT service management (ITSM) platform. Examples you may meet: ServiceNow, Jira Service Management, BMC Helix, Freshservice. They are named only so you recognize them in a job description; this page does not rank or recommend any of them, and the author has not operated them. What they have in common: a form for the request, a workflow that routes it to approvers, a calendar, links to inventory, and an audit trail of who did what and when. Many companies also connect the pipeline to the ticket so that a deployment can only start if an approved change record exists.

## What auditors look for

Auditors do not care which tool you use. They sample changes and ask whether the *control* worked. Three frameworks you will hear named, described only in general terms:

- **SOC 2** (an attestation report on a service organization's controls, from the AICPA, covering "trust services criteria"). It includes criteria about how changes to infrastructure and software are authorized, tested, approved and implemented. **UNVERIFIED:** the exact criterion wording and numbering were not retrieved for this page.
- **ISO/IEC 27001** (an information security management standard). Its controls list includes a change management control, and its management-system clauses expect changes to the system itself to be planned. **UNVERIFIED:** the control number and wording in the current edition were not retrieved for this page.
- **SOX IT general controls (ITGC)** (for companies subject to the US Sarbanes-Oxley Act: controls over the systems that produce financial reports). "Program change management" is a conventional ITGC area. **UNVERIFIED:** how any given auditor words the test is not sourced here.

The pattern an auditor tests is the same in all three, and it is worth knowing because it is concrete: pick a sample of production changes from the period; for each one, show that it was **requested, assessed, tested, approved by someone appropriate (not only the author), applied, and recorded**; and show that **nobody can change production by skipping the process** (access to production is limited, and the pipeline enforces the steps). A change that has a ticket written *after* it happened is the classic finding.

## How modern engineering teams do it

Teams that deploy many times a day cannot hold a meeting per deployment. They keep the same goals but turn most of the steps into machinery:

- **Version control and pull requests** are the request and the peer review. The history is the audit trail.
- **CI/CD pipelines** run the tests and produce the test evidence automatically, every time.
- **Branch protection and required checks** make the control something you cannot skip rather than something you promise to follow.
- **Feature flags** separate *deploying* code from *turning it on*. The code ships dark and is enabled for a few users, then more, then all, and switched off in seconds if it misbehaves.
- **Canary and blue-green releases** limit the blast radius. A canary sends a small share of traffic to the new version first. Blue-green keeps the old version running beside the new one so traffic can be switched back.
- **Change approval by automation** (sometimes called a "pipeline-approved standard change"): the organization approves the *pipeline* once, with its tests, scans and policy checks, and then every change that passes through it counts as a pre-approved standard change. Humans are pulled in by exception: a high-risk change type, a failing policy, a production-data migration.

### DORA metrics

DORA (the DevOps Research and Assessment program, now part of Google Cloud) publishes research on which delivery practices go with better outcomes. Its current guide, **retrieved 2026-10-16 from dora.dev/guides/dora-metrics/ (page marked "Last updated: January 5, 2026")**, lists five software delivery performance metrics. Four are the ones people usually quote; the wording below is the guide's, shortened:

| Metric (guide's name) | Definition |
|---|---|
| **Change lead time** (often called lead time for changes) | Time for a change to go from committed to version control to deployed in production. |
| **Deployment frequency** | The number of deployments over a period, or the time between deployments. |
| **Change fail rate** (change failure rate) | The ratio of deployments that require immediate intervention following a deployment. |
| **Failed deployment recovery time** (older name: time to restore service) | The time to recover from a deployment that fails and requires immediate intervention. |
| **Deployment rework rate** (the fifth) | The ratio of deployments that are unplanned but happen as a result of an incident in production. |

Notice the useful point for this page: *change failure rate* is measured from outcomes, not from how many people approved. DORA's research is cited by many teams as evidence that speed and stability go together, and that heavy external approval processes are not associated with better stability. That claim is from memory of the research and **UNVERIFIED** here; read the DORA material itself before quoting it.

## Emergency changes and break-glass

Real systems break at bad times, so every mature process has a fast path:

- An **emergency change** is raised with minimal paperwork, approved by an on-call authority (the ECAB, or a duty manager) over chat or phone, applied, and then documented and reviewed afterwards. The review is not optional: the emergency path is only trustworthy if the next-day paperwork actually happens.
- **Break-glass access** is the access equivalent: a powerful account, normally locked, that an on-call person can open in an emergency. Opening it is loud by design: it alerts security, it is time-limited, every command is recorded, and someone reviews it afterward. The name is from the fire-alarm box: you can break the glass, and everyone will know you did.

The failure mode to watch for: if the emergency path is faster than the normal one, people start declaring emergencies.

## Common failure modes

- **The rubber-stamp CAB.** Thirty changes in a one-hour meeting, one minute each, nobody has read them. The meeting exists, the audit sample passes, and the control does nothing. The sign: approvals that almost never ask a question or say no.
- **Change collisions.** Two teams change related systems in the same window, each safe alone, together broken. A shared calendar and a dependency view (the CMDB, when it is accurate) exist to prevent this.
- **Shadow changes.** Someone changes production directly, with an admin account, outside the process "just this once". The system drifts from the record and the next incident is baffling. Pipelines that are the *only* way to change production, plus drift detection, are the counter.
- **Undocumented or untested rollbacks.** "We can just roll back" without anyone having tried it, or a change (a database migration, a deleted resource) that cannot be rolled back at all. The back-out plan is a claim; test it like one.
- **Paperwork after the fact.** The ticket is written the next morning. It records the story, not a decision.
- **Everything is "emergency".** The fast path becomes the normal path.

## Is any of this used in this project?

**No.** This repository does not use formal change management. There is no change ticket system, no CAB, no change calendar and no freeze. This is not an oversight and it is not a recommendation to copy: it is what a one-maintainer, two-machine teaching project can honestly do. The sections above are here so you can recognize the machinery at work, and see what the project does *instead*.

### What the project has instead

| Enterprise idea | What this project does instead | Where to read it | How close it is |
|---|---|---|---|
| Change request / RFC | A **pull request**, with the four headings *Why*, *Change*, *Testing*, *Not verified*. It is the request and the peer-review place at once. | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) | A fair stand-in for the request; there is no ticket id. |
| Test evidence | **CI gates**: `tofu test` with mocked providers, the cost gate, security scans, and the single required check `CI green`. | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | Close to enterprise "automated test evidence". |
| Approval and change window | The **Spacelift plan, read by a human who then presses confirm**. Autodeploy is off. The person confirming picks the moment, so the window is "whenever the one maintainer decides". | [Spacelift](Spacelift.md#why-autodeploy-is-off) | Real approval of the real diff; the approver is also the author. |
| Back-out plan | **Revert the pull request and run the pipeline again**, or destroy a stack. OpenTofu's plan shows the reverse diff before it applies. | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) | Plausible and visible, but not written in advance per change, and not always possible (a destroyed resource may not come back the same). |
| Post-implementation review | **Lessons learned**: a page of what went wrong, how it was measured, what changed. | [Lessons learned](Lessons-Learned.md) | Lightweight and public, written when something was worth writing, not for every change. |
| Guardrails that make some changes standard | The **cost gate** refuses infrastructure resource types that have not been priced and approved, by name. The Spacelift push policy (OPA) is a different guardrail: it only decides which Git events and paths start a run. | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) | Similar in spirit to "change approval by automation". |

### What is missing, compared with an enterprise

- **No CAB and no emergency CAB.** There is nobody to convene.
- **No ticket ids.** A pull request number is the nearest thing. There is no link from a change to a business reason beyond the description.
- **No change calendar, window or freeze.** Nothing else depends on this environment at a fixed time, so there is nothing to collide with.
- **No separation of duties.** One maintainer writes, reviews, merges and confirms. The repository says so plainly ("one writer"): see [Branch protection and one writer](Git-GitHub-and-Pull-Requests.md#branch-protection-and-one-writer). The controls that remain (required checks, a plan read before apply) protect against mistakes, not against a dishonest maintainer. That is a fact to state, not a thing to hide.
- **No CMDB.** The code *is* the inventory, which works at two machines and fails at two thousand.
- **No formal emergency path and no break-glass procedure.** If something breaks, the maintainer does what is needed and writes it down afterwards.
- **No change failure rate measured.** Nobody counts.

### Why that is appropriate at this size, and where a team would need more

The point of the controls above is to put a second, informed pair of eyes between a change and the people it can hurt, and to leave a trail. Here: nobody depends on the environment, the maintainer is the only person who could be hurt, the infrastructure is two small machines that can be rebuilt from code, and the pipeline already gives automated test evidence and a human-read plan. Adding a CAB would add ceremony without adding a reader.

A team needs more as soon as any of these become true: more than one person can change production (so separation of duties and a shared calendar matter); other people or customers depend on the system (so impact assessment and a window matter); an auditor or contract asks for evidence (so a ticket id, an approver who is not the author, and a retained record matter); or the system is large enough that nobody holds the dependencies in their head (so a CMDB-like view matters). The sensible first steps for a small team are to make the pipeline the only way to change production, require a reviewer who is not the author, and record every emergency afterwards. That covers a surprising share of what auditors sample.

## Worked example: the real change, as an enterprise would record it

Take pull request #8, "fix: let each connector open SSH to the other (outbound rule)", the change traced in [Trace one change end to end](Trace-One-Change-End-to-End.md). Below is the change record an enterprise might require for it. **Everything here is illustrative: the record number and the approvers are invented, because the real project has no change records.** The technical content is taken from the real pull request and the trace page.

| Field | Entry |
|---|---|
| **Change ID** | CHG-000123 (invented) |
| **Title** | Allow connector-to-connector SSH: add outbound TCP 22 rule to the connector firewall |
| **Requester / implementer** | Platform engineer (same person in this project) |
| **Change type** | **Normal.** It alters a firewall, which is a security boundary, so it is not a pre-approved standard change (see exercise 4). |
| **Reason** | Connector-to-connector SSH timed out. Pull request #7 added the inbound half; the first packet of a new connection also needs an outbound rule on this provider. See [Lessons learned, number 2](Lessons-Learned.md#2-connector-to-connector-ssh-timed-out-twice). |
| **Description** | New optional module input `outbound_to_tag_rules`, default empty; one rule in the access stack sending TCP 22 to the connector tag only (a tag, never an address); tests that pin the new rule and the unchanged baseline. |
| **Systems affected** | The connector firewall in the access stack. The foundation stack consumes the changed module but is expected to show no change. (CMDB links: two firewall records, two connector hosts.) |
| **Risk assessment** | Likelihood of harm: low. The rule is scoped to one tag and one port, default off. Main residual risk: opening more than intended. |
| **Impact assessment** | If wrong: peer SSH between connectors stays broken (annoying) or is opened wider than intended (a security regression). SSH through Twingate can take this path: a session targeting one connector can be routed through the other, which must then open TCP 22 to its peer (the cause of the user-visible timeouts this change fixed; see [Lessons learned, number 2](Lessons-Learned.md#2-connector-to-connector-ssh-timed-out-twice)). Other Twingate access does not depend on it. No customer-facing service. |
| **Test evidence** | CI green: `tofu` tests (the connector firewall has exactly one inbound and exactly one tag-scoped outbound rule), cost gate unchanged at the approved total, code and secret scans passing. Author also broke each safety property on purpose and saw a test fail. |
| **Not verified before approval** | Mocked providers only: the real provider behavior is proved only by the apply. |
| **Implementation plan** | Merge. Spacelift tracked run on the access stack and the foundation stack. Read the plan: access stack shows one in-place update to one firewall; foundation shows no changes. Confirm. |
| **Verification plan** | From one connector, open TCP to the other on port 22 (expect open). SSH through Twingate to both, several times, because the symptom was intermittent. From outside the VPC, confirm connectors still look filtered. |
| **Back-out plan** | Revert the pull request, let the pipeline plan, read it (expect one in-place update removing the rule), confirm. Trigger: any external scan shows an unexpected open port after the apply. If the plan shows an unexpected droplet replace, do not roll back: discard the pending run before confirming, because nothing has been applied yet. Rollback time: one pipeline run. |
| **Change window** | Any time outside the approved freeze; no user-facing impact. |
| **Approvals** | Network owner (reads the rule), security (reads that it is tag-scoped). Neither is the author. |
| **Post-implementation review** | Required only if verification fails or the back-out is used; otherwise a one-line closure note. |

### The same change with a CAB: a timeline

Illustrative, assuming a weekly CAB on Tuesdays and a Thursday-night window. These cadences are invented to show the shape; real companies vary a great deal.

| When | What happens |
|---|---|
| Fri 17:00 | The pull request is opened and the RFC is filed. CI is green by 17:15. |
| Mon | Peer review of the pull request; the RFC is triaged and judged "normal, low risk". |
| Tue 10:00 | CAB reviews the RFC in a list of other changes. Someone asks whether the change touches the foundation stack. The answer ("expected no change") is written into the plan. Approved. |
| Thu 22:00 | Change window. Merge, run, read the plan, confirm. Verification steps are run and recorded. |
| Thu 22:30 | The RFC is closed as successful. |
| Next Tue | CAB sees it in the "closed last week" list; no PIR needed. |

**What actually happened:** the real pull request was opened at 23:19 UTC and merged at 23:21 UTC on 2026-10-10 (read with `gh pr view 8`), about two and a half minutes later. Nothing is wrong with that for this project; it shows the cost the CAB version adds (almost a working week of elapsed time for a change whose risk was already well covered by tests) and what it buys (the foundation-stack question, a second reader, a closed record). Whether that trade is worth it depends entirely on who else depends on the system.

## Try it yourself: predict, then check

Cover the reference answer and write your own first.

### Exercise 1: classify five changes

Mark each **standard**, **normal** or **emergency**, and give a one-line reason.

1. Renewing a TLS certificate using the documented renewal procedure the team has done thirty times.
2. Adding a new inbound firewall rule to a production database subnet.
3. The payment service is down since a bad deploy an hour ago; the team wants to redeploy the previous version immediately.
4. Upgrading the database engine's major version.
5. Adding a new employee to a team's group using the standard onboarding form.

**Reference answer.** (1) Standard: repeatable, documented, low risk, pre-approved as a type. (2) Normal: it changes a security boundary around sensitive data; assess and approve each time. (3) Emergency: service is down now; fast path with an ECAB or on-call authority, then review afterwards. (4) Normal, and a high-risk one: a major engine upgrade probably needs the full CAB, test evidence from a staging copy, and a tested back-out plan. (5) Standard: it is a pre-approved request type. Arguments exist for (5) being normal if the group grants privileged access; a good answer says what would change the class.

### Exercise 2: spot the missing back-out plan

Here is a change record excerpt. What is missing, and why does it matter?

> **Title:** Drop unused column `legacy_flag` from the orders table. **Risk:** low, nothing reads it. **Test evidence:** migration ran clean in staging. **Implementation:** run the migration at 23:00 Saturday. **Approvals:** application owner. **Back-out:** "restore from backup if needed".

**Reference answer.** The back-out is a slogan, not a plan. It does not say who restores, from which backup, how long that takes, how much data written since the migration would be lost, or at what point the decision to restore is taken. A dropped column cannot simply be put back, so the real plan needs a verified backup (or a copy of the column's data) taken before the change, a tested restore time, and a stated trigger ("if error rate on the orders service rises above X for 10 minutes"). A second gap worth naming: the only approver is the application owner; the database owner or whoever runs the restore is not asked.

### Exercise 3: compute the change failure rate

Using the guide's definition above (the ratio of deployments that require immediate intervention following a deployment):

| Week | Deployments | Needing immediate intervention |
|---|---|---|
| 1 | 4 | 0 |
| 2 | 6 | 1 |
| 3 | 5 | 1 |
| 4 | 5 | 1 |

What is the change failure rate for the four weeks? Is week 2 or week 4 worse? What does the number not tell you?

**Reference answer.** Total deployments 20, needing intervention 3, so the change failure rate is 3 / 20 = **15%**. Week 2 is 1/6 (about 16.7%), week 3 and week 4 are 1/5 (20%), so weeks 3 and 4 are worse, though with samples this small a single deployment moves the percentage a lot, so do not draw conclusions from one week. The number does not say how bad each failure was, how long recovery took (that is the separate recovery-time metric), or whether the failures were the same cause repeating.

### Exercise 4: a firewall rule change in this repo, in an enterprise

Suppose an engineer at a company wants to make the same kind of change as pull request #8 (one tag-scoped TCP 22 rule on a firewall). Would an enterprise treat it as standard or normal, and why? Could it ever be standard?

**Reference answer.** **Normal** by default, because a firewall rule changes a security boundary and the approver must see this specific rule, its scope and its reason. The qualities of the change are good: narrow, tag-scoped, tested, easy to revert. But a standard change is pre-approved *as a type* before any instance exists, and "any firewall rule" is far too broad a type. It could become standard only if the organization defined a narrow type in advance, for example "add or remove a rule on the internal connector tier, tag-to-tag, one port from a pre-approved list, no address ranges", with a pipeline that enforces those limits, and the security owner approved that type once. That is exactly the "approve the pipeline, not each change" idea. Anything outside the type (an address range, the internet, a new port) falls back to normal.

### Exercise 5: find the control that is not there

Open [Trace one change end to end](Trace-One-Change-End-to-End.md) and name two things an auditor sampling pull request #8 would ask for and not find.

**Reference answer.** Any two of: an approver who is not the author (one writer); a change record id or ticket linking the request to a business reason and a risk rating; a recorded approval timestamp before implementation (CI green and the confirm are logged, but there is no separate sign-off); a documented back-out plan written before the change rather than reconstructed from the revert option; a post-implementation entry (the verification checks are in the description, not recorded as having been run and by whom); a link to an asset inventory.

## Keep learning

- [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) and [Trace one change end to end](Trace-One-Change-End-to-End.md): the project's lightweight version of this page, step by step.
- [Enterprise engineering habits](Enterprise-Engineering-Habits.md): the habits worth taking home from a tiny lab.
- [Lessons learned](Lessons-Learned.md): a worked example of post-implementation review done without ceremony.
- DORA's guide to its metrics at dora.dev, and the research it links to (the claims in this page about DORA were read on 2026-10-16).
- The official ITIL 4 publication on change enablement from PeopleCert, for the primary wording (this page did not read it).
- The text of SOC 2's trust services criteria, ISO/IEC 27001 and your own auditor's SOX test descriptions, if you will work in a regulated company (none were read for this page).
- Ask someone at a company how an emergency change is approved there. The answer is usually more honest than the policy.

Next: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md), or back to [A small example: what an enterprise does differently](Small-Example-Enterprise-Landscape.md) and the [Reading order](Reading-Order.md).
