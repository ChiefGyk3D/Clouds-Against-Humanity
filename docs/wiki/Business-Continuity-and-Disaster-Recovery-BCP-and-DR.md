# Business continuity and disaster recovery: BCP, DR and a plan for this project

Side page to the backup and recovery pages. Read it after [Backups, recovery and patching](Backups-Recovery-and-Patching.md), which teaches you to take a backup, lose the original and time the restore, and after [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md), which teaches you to recover from a lost state file. This page zooms out: when something big breaks, **what must keep working, who does what, and in what order does it come back**. It does not repeat the table on the Enterprise page about [high availability, disaster recovery and backups](Enterprise-Infrastructure-Differences.md#high-availability-disaster-recovery-and-backups); it builds a plan on top of those words and applies it to this project's own pieces.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Written from reading; no recovery procedure on this page was run.** On **2026-10-31** I read the sources in the [claims register](#claims-register) and the repository files named in the project plan, and I ran exactly one thing: the small table checker in [Exercise 1](#exercise-1-check-a-recovery-table-for-contradictions), on the sample tables printed there. I did **not** restore anything, rebuild a stack, rotate a token, fail over a connector or run a tabletop with other people. Every RTO and RPO for this project below is a **proposal** for a hobby project, not a measurement, and no number on this page has ever been timed. Where the repository has no document or test for a piece, the plan says **None** and does not invent one.

> **Prerequisites.** [Backups, recovery and patching](Backups-Recovery-and-Patching.md) for RPO, RTO and the difference between a backup and a restore, and [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) for what lives outside the code. Pencil and paper, or a plain text file. About two hours for the reading and the paper exercises (est.). The tabletop takes another 45 to 60 minutes (est.). Everything is free; no account is needed.

> **Where this runs.** On paper and on your own computer. Nothing here touches a cloud account, a token or a running service. The tabletop is a conversation: it deploys nothing and changes nothing, which is the point of it.

## What you will be able to do

- Say what a business continuity plan covers, what a disaster recovery plan covers, and why a team needs both, using the definitions in NIST SP 800-34.
- Run a business impact analysis on a small system: list what it does, who depends on it, what an hour, a day and a week of downtime cost, and what must come back first.
- Set an RTO and an RPO for each system, tie each to a copy or a standby that can actually meet it, and explain why a dependency cannot recover faster than the thing it needs.
- Choose between cold, warm and hot recovery, and between backup and restore, pilot light, warm standby and active-active, by cost and by time.
- Write a one-page runbook, a contact tree and a short communications plan, and say who does what during an incident.
- Run a free tabletop exercise on one scenario from this project and write the findings down.
- Tell a backup from a recovery, and say why the second is the only one anyone should count.
- Say what ransomware changes about a recovery plan, and what four public incidents teach about backups, restores, contacts, and other people's software.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| RPO and RTO in plain words | [Backups, recovery and patching](Backups-Recovery-and-Patching.md#rpo-and-rto-in-plain-words) works both out from a backup schedule. | Choosing them per system, from the cost of being down, and in dependency order. |
| A table of DR words | [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md#high-availability-disaster-recovery-and-backups) defines RTO, RPO and DR in one table and says this project's objective is "in effect, an evening". | Where "an evening" comes from, what is actually promised, and for which piece. |
| Rebuild from code | [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) lists what a destroy leaves alone, and [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) recovers a lost state file in a local lab. | The pieces outside the code, put in one recovery order with an owner and a test for each. |
| Contain, detect, recover | The lesson on planning for failure (blast radius and assuming breach) has a "recover" row. | The people side: roles, contacts, messages, and practicing it. |
| Incident wording | The [Glossary](Glossary.md) defines incident and runbook. | A communications plan and a tabletop. |

## BCP and DR: two plans, not one

The two are often used as one word. They are not, and the difference decides what you write.

NIST SP 800-34 Rev. 1 ("Contingency Planning Guide for Federal Information Systems", May 2010) separates several plans. Two matter most here:

- A **business continuity plan (BCP)** "focuses on sustaining an organization's mission/business processes during and after a disruption". Its example of a process is payroll or customer service. It is about **the work**, and it may cover one team or the whole organization. Because processes run on information systems, the planner "must coordinate with information system owners" so the plan's expectations and the systems' abilities match.
- A **disaster recovery plan (DRP)** is "an information system-focused plan designed to restore operability of the target system, application, or computer facility infrastructure at an alternate site after an emergency". It is about **the computers**, and it can support a BCP by recovering the systems the business process depends on.

A short way to hold it: **BCP asks "how do we keep doing the job?" DR asks "how do we get the machines back?"** If the payroll system is down for three days, the BCP is the paper process or the manual advance that still pays people; the DR plan is how the payroll server is rebuilt. A company with a perfect DR plan and no BCP can restore every server and still not know who tells customers what, or what people do for the three days it takes.

Two cautions. First, NIST wrote for US federal agencies, and it defines DR narrowly: its DRP "only addresses information system disruptions that require relocation" to an alternate facility. Cloud teams use "disaster recovery" for any serious recovery, with or without a second site. Use the word the people around you use, and write down what you mean. Second, other standards (ISO 22301 for business continuity, for example) use their own vocabulary; I read none of them for this page, so I do not quote them.

NIST lists more plans than these two, and a small organization still needs the idea behind each, even if all of them fit on three pages:

| Plan (NIST's name) | What it is for | Where it shows up below |
|---|---|---|
| Business continuity plan | Keep the work going | The whole page |
| Disaster recovery plan | Restore systems after a major disruption | [Recovery strategies](#recovery-strategies-cold-warm-hot-pilot-light-active-active) |
| Information system contingency plan (ISCP) | Procedures to assess and recover one system, with roles and contacts | [Runbooks](#runbooks-contact-trees-roles-and-communications) |
| Crisis communications plan | Who may say what to whom, inside and outside | [Communications](#communications-who-says-what-and-through-what) |
| Cyber incident response plan | Detect, contain and eradicate a security incident | [Ransomware](#ransomware-as-a-dr-scenario) |
| Continuity of operations plan (COOP) | A US government plan to keep essential functions going at an alternate site for up to 30 days | Not covered; it is a federal concept |
| Occupant emergency plan | Evacuating people from a building | Not covered |

## Business impact analysis

A **business impact analysis (BIA)** is "an analysis of an information system's requirements, functions, and interdependencies used to characterize system contingency requirements and priorities in the event of a significant disruption" (NIST SP 800-34 Rev. 1, glossary). The US Ready.gov page puts it in plainer words: a BIA "predicts the consequences of a disruption to your business, and gathers information needed to develop recovery strategies".

NIST's three steps, in its own order:

1. **Determine mission/business processes and recovery criticality.** Name each process the system supports, what a disruption does to it, and how long it can be down "while still maintaining the mission". That longest tolerable gap is the **maximum tolerable downtime (MTD)**: "the amount of time mission/business process can be disrupted without causing significant harm to the organization's mission".
2. **Identify resource requirements.** What does it take to run again: people, facilities, equipment, software, data files, and the other systems it needs.
3. **Identify recovery priorities for system resources.** Link resources to the critical processes and put them in an order, so recovery work is sequenced.

Ready.gov adds the question list that makes a BIA practical: ask the people who run each process what happens if it stops, and count impacts such as lost or delayed income, extra expenses, regulatory fines, contractual penalties and customer defection. It also tells you to compare those costs with the cost of each recovery option, and to restore first the processes with the greatest operational and financial impact. It lists scenarios to consider: damage to a building, equipment failure, restricted access to a site, a supplier failing, a utility outage, and "damage to, loss or corruption of information technology".

**How the numbers relate.** The BIA gives an **MTD** (how long the business can live without it). Your **RTO** (how long recovery is allowed to take) must be **shorter** than the MTD, or the plan promises a recovery that arrives after the harm is done. NIST defines RTO as "the overall length of time an information system's components can be in the recovery phase before negatively impacting the organization's mission", and RPO as "the point in time to which data must be recovered after an outage". The honest part: a BIA for a small project is mostly a few people (or one person) answering "what would we miss, and when?" in writing.

## RTO, RPO and the time nobody counts

[Backups, recovery and patching](Backups-Recovery-and-Patching.md#rpo-and-rto-in-plain-words) works through the arithmetic. Two additions for planning across several systems.

**Tie each number to a real thing that can deliver it.** An RPO of one hour needs a copy at least hourly; the table in [Exercise 1](#exercise-1-check-a-recovery-table-for-contradictions) checks that. An RTO of four hours needs a restore that fits inside four hours, which means somebody timed it. A number with no copy and no timed restore behind it is a wish.

**An RTO runs from the failure, not from the start of the restore.** The restore command is often the shortest part. Before it come noticing, deciding, finding the backup, finding the credential that opens it, and getting people on a call. After it come starting the service and checking it is right. Atlassian's public review of its April 2022 outage shows the gap at scale: it says it "missed our RTO but met our RPO". Customers lost almost no data (no more than five minutes, it says) and still waited up to 14 days.

**A system cannot come back before what it needs.** If the web application needs the database and the database needs the network, the application's RTO is at least the database's, and the database's is at least the network's. The recovery **order** is the dependency graph, read from the bottom. This is the single most useful output of a BIA, and it is the reason "RTO per system" is meaningless without a "depends on" column.

### Criticality tiers

Many plans sort systems into **tiers** so the same answers are not worked out afresh for every machine. A common shape is below. **The tier names and numbers are illustrative: I read no standard that fixes them,** and NIST's own sorting is by the impact of the system (low, moderate, high) for choosing a plan template, not by these tier numbers.

| Tier | Meaning | Typical target (illustrative) | Typical strategy |
|---|---|---|---|
| 0 | Everything else needs it first: identity, secrets, the way in, the code | Hours | The best protection you can afford; tested most often |
| 1 | The business stops without it | Hours | Warm or hot standby, or very fast restore |
| 2 | Painful, workable around for days | A day or two | Restore from backup, rebuilt from code |
| 3 | Convenience; can wait | A week | Rebuild when time allows |

Tier 0 is the part beginners miss. The things you recover **first** are rarely the things users see. They are the things you need in order to recover anything: the place the code lives, the secret store, the sign-in, the network path in. This project's plan below puts exactly those first.

## Recovery strategies: cold, warm, hot, pilot light, active-active

Two vocabularies, one idea: **the more you keep ready ahead of time, the faster you come back and the more you pay every month.**

NIST describes alternate **sites** by readiness (SP 800-34 Rev. 1, table 3-34, "Sample Alternate Site Criteria"):

| Site | Cost | Hardware | Telecommunications | Setup time |
|---|---|---|---|---|
| Cold | Low | None | None | Long |
| Warm | Medium | Partial | Partial or full | Medium |
| Hot | Medium to high | Full | Full | Short |

NIST's text: a cold site has the space and infrastructure (power, telecommunications, environmental controls) but not the computers; a warm site is partly equipped; a hot site "configured with the necessary system hardware, supporting infrastructure, and support personnel". It adds mirrored sites, "identical to the primary site in all technical respects", as the most expensive choice, with virtually 100 percent availability.

For cloud workloads, AWS's disaster recovery whitepaper names four approaches, "ranging from the low cost and low complexity of making backups to more complex strategies using multiple active Regions":

| Approach | In AWS's words, shortened | Recovery is | Costs you |
|---|---|---|---|
| Backup and restore | Back up data and configuration, rebuild in a recovery location when needed | Slowest | Storage, plus the work of rebuilding |
| Pilot light | Data is replicated and core infrastructure exists; application servers are loaded but "switched off" | Faster | A small always-on core |
| Warm standby | "A scaled down, but fully functional, copy of your production environment" always on in another Region | Faster again | A small copy running all the time |
| Multi-site active/active | The workload runs in several Regions at once | "Near zero" for most disasters | "The most complex and costly" |

Read the same table as a staircase. Each step buys a shorter RTO with money and with complexity, and none of them cures **corruption or deletion**: a replica copies a mistake as faithfully as good data, so even AWS says that for data corruption "a non-zero recovery point" from backups is usual. Two more points from the same page. It says that for a failure that is the loss of one data center, backup and restore may be enough for a well-architected, highly available workload; it points to pilot light, warm standby or active-active only when your definition of disaster is a whole Region or a regulation requires it. And it separates the **control plane** (the tools that configure the environment) from the **data plane** (the part that serves traffic), advising that for resilience a failover "use only data plane operations", because control planes are the first thing a regional failure is likely to take with it. That sentence matters for this project, whose control plane is Spacelift and Doppler.

**For a hobby project the honest strategy is the cheapest one that works:** keep the code safe, keep what is not code written down, rebuild on demand, and pay for nothing that sits idle. That is "backup and restore" in the table, with the code as the backup. The rest of this page is about making that choice deliberately instead of by accident.

## Runbooks, contact trees, roles and communications

### Runbooks

A **runbook** is the written steps for one job, written so that someone tired, scared, and not the author can do it. For recovery, one runbook per system, each with the same bones (these headings are common practice, not a quote from a standard):

1. **What this protects, and its tier, RTO and RPO.**
2. **Who owns it, and who to call if they cannot be reached.**
3. **Before you start:** what you need in hand (accounts, tokens, where each is kept, the hardware) and what else must be up first.
4. **The steps,** numbered, each with the expected output, so a wrong turn is noticed.
5. **How you know it worked:** one or two checks that cannot pass by accident.
6. **How to back out.**
7. **When it was last run, by whom, and how long it took.** If this line is empty the runbook is a draft.

NIST's information system contingency plan follows the same logic with three phases: Activation and Notification, Recovery, and Reconstitution (SP 800-34 Rev. 1, chapter 4). Reconstitution is the one people forget: testing and validating that the system is whole before declaring the incident over, and returning to normal operation.

### Contact trees

A **contact tree** (also call tree) is the list of who calls whom: the person who raises the alarm, the person with authority to decide, the person who can fix the thing, and a backup for each, with more than one way to reach them. Three rules, one learned the hard way:

- **Keep an offline copy.** CISA's #StopRansomware Guide says to keep "a hard copy of the plan and an offline version" of the incident response plan, and to keep IT asset and network documentation as offline backups and hard copies. A contact list that lives only on the system that just failed does not help.
- **Use a channel the attacker or the outage cannot reach.** The same guide advises "out-of-band communication methods such as phone calls" when an attacker may be watching your normal channels.
- **Back up the customer contacts too.** In Atlassian's April 2022 incident, "some customer contact information was deleted", so customers "could not file support tickets as they normally would" and the company did not have immediate access to key contacts. Its list of fixes includes better backup of key contacts. Contacts are data, and data needs a recovery plan.

### Roles during an incident

One person cannot fix the problem, keep notes, update the people who are waiting and decide when to stop. Common practice assigns separate roles (this is general practice, not a NIST quotation):

| Role | Does |
|---|---|
| Incident lead | Makes the decisions, sets the pace, decides when to escalate or call it over. Does not type commands. |
| Technical lead (and helpers) | Diagnoses and does the recovery steps, reports what they see and what they plan to do before they do it. |
| Scribe | Writes a timestamped log of what was seen, decided and done. This becomes the review. |
| Communications lead | Sends the updates to the people affected, on a schedule, whether or not there is news. |

In a one-person project you play all four in turn. Say it out loud as you switch; it keeps the log honest. Atlassian's review describes its larger version: a cross-functional incident team that met every three hours, a code freeze across engineering to avoid unrelated change during the recovery, and a tracking project with one item per affected site.

### Communications: who says what, and through what

NIST's **crisis communications plan** "typically designates specific individuals as the only authority for answering questions from or providing information to the public", and may include procedures for reporting status to staff and templates for public statements. For a small project the plan fits on a card:

- **Who may speak** for the project.
- **Where updates go** (a status page, the project's issue tracker, a post on the project's social account) and **how often** (say every hour while down, even to say "no change").
- **A holding statement** written in advance: what is affected, what you know, what you do not know, when the next update comes. Fill the blanks in during the incident; do not write it from scratch while it is happening.
- **What you will not say** until you know it: a cause, a number, a promise of a time.
- **A second channel,** because the first may be the thing that is down.

The two public postmortems that explain their communications are instructive. GitLab kept public notes in a document and streamed its recovery live, and its own review says it will redact engineers' names next time. Atlassian's review says it will "acknowledge incidents early, through multiple channels" and release public communications "within hours".

## Testing: a backup is not a recovery

The central rule of the whole subject: **until it has been restored, it is a hope.** [Backups, recovery and patching](Backups-Recovery-and-Patching.md#a-backup-you-have-not-restored-is-a-hope) lists how a backup can succeed and a restore fail. Put it in plan terms:

| What you have | What it proves | What it does not prove |
|---|---|---|
| A backup job that exited 0 | The job ran | That the file is complete, readable, or the right thing |
| A backup file that checks out (checksum, size) | The bytes arrived intact | That the software can use them, or that anyone can open them |
| A **restore** into a fresh place, checked against a record written before the disaster | The data comes back correct, and how long that took | That the *whole service* comes back (network, secrets, dependencies, people) |
| A **recovery exercise** of the whole service, with the clock running, by the people who would do it in a real event | The plan works end to end, and the true RTO | That it works for a disaster you did not rehearse |

CISA's ransomware guide says the same in a few words: "regularly test the availability and integrity of backups in a disaster recovery scenario", and test backup procedures on a regular basis.

NIST SP 800-34 (citing SP 800-84) names two kinds of exercise: **tabletop** (discussion only) and **functional** (people perform their duties in a simulated environment, from a narrow part of the plan up to a full-scale exercise). It says a tabletop at an organization-defined frequency is enough for a low-impact system. So start with a tabletop, and move to a real, timed restore of the most important thing as soon as you can.

## Tabletop exercises, and how to run one for free

A **tabletop exercise** is, in NIST's wording (quoting SP 800-84), a discussion-based exercise where "personnel meet ... to discuss their roles during an emergency and their responses to a particular emergency situation". A facilitator presents a scenario and asks questions; the exercise "is discussion-based only and does not involve deploying equipment or other resources". Nothing is switched off, restored or changed.

It is the cheapest test there is, and it finds a surprising amount: missing contacts, a step only one person knows, two plans that each assume the other will act first, a recovery that needs the thing that just broke. The aim is **not** to pass. The aim is to find the gaps while nobody is hurt.

CISA publishes tabletop exercise packages (CTEPs); the page I read states no charge and I did not look for one. They include template exercise objectives, scenarios and discussion questions, plus planning documents, a feedback form and an after action report template. Its page lists scenarios including natural disasters, ransomware, insider threats and others, and says over 100 are available (read 2026-10-31). A tabletop needs no package at all; the steps below work with a sheet of paper. They are written for larger organizations and fit a team better than one person, but the structure transfers.

### Running one, step by step

1. **Pick one scenario and one question.** "What do we do when the secret store is gone?" is better than "what if everything breaks?"
2. **Set a time box.** 45 to 60 minutes; stop on time.
3. **Cast the roles.** Facilitator (reads the scenario and the injects, keeps time, does not play), incident lead, technical lead, scribe, communications lead. Alone, write one card per role and answer as each in turn; a friend or colleague can read the injects so that you do not know what comes next.
4. **Set the ground rules.** No blame. Play the scenario straight. **Only what is written down counts:** if the answer is "I would remember where that is", the answer is that it is not written down, and the scribe records a gap.
5. **Read the scenario, then one inject at a time.** An inject is a new fact: "the first fix fails", "the person you would call does not answer". After each, ask the three questions: what do we do, who does it, and where is that written?
6. **Record decisions and gaps** as they happen, in two columns.
7. **Afterward, take 15 minutes** to turn the gaps into at most three findings, each with one owner and one date. A tabletop that ends with fifteen findings fixes none of them.
8. **Fix them, then run it again** in a few months with a different scenario.

## Third-party and cloud dependencies

Your recovery plan depends on other people's recovery plans. A modern system leans on a cloud provider, a code host, a secret store, a sign-in provider, a DNS provider, a certificate authority, and software that updates itself. For each dependency ask four questions:

- **What do I lose if it is down, and for how long can I live without it?** (It goes in the BIA.)
- **Is there a workaround that does not need it?** If recovery needs a service to be up, and that service is the one that failed, you have a loop.
- **What does its provider promise, and what has it done?** A service-level promise is a goal the provider chose; read it, and read its postmortems.
- **Is the thing I need to recover it (an account, a key, a token) kept somewhere that does not depend on it?**

Two public incidents show the pattern from opposite ends:

- **A provider's own defect reaches everyone who depends on it.** Amazon's summary of the 19 to 20 October 2025 disruption in its US-EAST-1 (Northern Virginia) region says the event ran from 11:48 PM PDT on 19 October to 2:20 PM PDT on 20 October, was triggered by a "latent defect within the service's automated DNS management system" that caused DynamoDB endpoint resolution failures, and services that depend on DynamoDB could not make new connections; in the same event, new EC2 instance launches failed for several hours. If your recovery plan is "launch new instances in that region", it fails in exactly that event. This is the practical meaning of the AWS advice to avoid control-plane operations in a failover.
- **A vendor's update runs inside your systems without your change process.** CrowdStrike's root cause analysis of the July 2024 incident says a content update delivered on 19 July 2024 contained a new template instance that the sensor's content interpreter could not handle (an out-of-bounds read), and that its fixes include staged deployment of such content through rings and canary testing, and giving customers control over the deployment of that kind of update. The report says about 99 percent of Windows sensors were back online by 29 July 2024. The lesson for planners is not about that company: **any auto-updating agent is a way for someone else to change your production at the same time, everywhere.** Know which ones you run.

## Ransomware as a DR scenario

Ransomware is the disaster plans are most often tested by now, and it is worse than a fire in one way: **the attacker is trying to destroy your recovery.** CISA's #StopRansomware Guide says it plainly: maintain offline, encrypted backups of critical data, because "many ransomware variants attempt to find and subsequently delete or encrypt accessible backups to make restoration impossible unless the ransom is paid". A replica or a backup reachable with the same credentials is not a backup in this scenario.

What the guide adds that belongs in any recovery plan (read 2026-10-31):

- **Golden images and infrastructure as code.** Keep image templates and version-controlled infrastructure code, with backups of the template files kept offline, so resources can be rebuilt quickly.
- **Software too.** Store the installers and the source code with the offline backups, because some images will not install on different hardware or platforms.
- **Cloud-to-cloud backup,** with the suggestion to avoid depending on one vendor so an incident in one set of accounts does not reach every copy, and immutable storage where it fits (the guide warns that immutable storage "does not meet compliance criteria for certain regulations and misconfiguration can impose significant cost").
- **Harden the hypervisors and management tools.** It warns that ransomware actors now target hypervisors so that the infrastructure is encrypted at scale.
- **Response order:** determine which systems are affected and "immediately isolate them", taking the network offline at the switch if several are hit; use out-of-band communication so the attacker is not tipped off; restore "from offline, encrypted backups based on a prioritization of critical services", and "take care not to re-infect clean systems" (for example by adding only clean systems to a new recovery network).
- **Ask for help early:** the guide tells you to consult law enforcement even when you can mitigate, since decryptors may exist for some variants. Whether to pay is a decision for the people with authority and legal advice, and the guide does not recommend it; this lesson takes no position beyond that.

The recovery plan for ransomware has a property the others do not: you cannot trust the **restore source** until you know when the attacker got in. Restoring a backup that already contains the intruder's access restores the intruder. So the plan must say how you will choose a restore point, and who decides. [Backups, recovery and patching](Backups-Recovery-and-Patching.md) covers the backup side in words only; nothing in this repository simulates ransomware, and nothing on this page does.

## Lessons from public postmortems

Four reports I read in full or in part on **2026-10-31**, with their dates. What I read is stated for each; where I did not read to the end, I say so. These are summaries of what each company wrote, not my verdict on them.

**GitLab, "Postmortem of database outage of January 31" (published 10 February 2017; read through the recovery and data-loss sections).** An engineer working on a lagging replica wiped the data directory on the production primary by mistake (about 300 GB removed). The team then discovered that none of the recovery routes they had counted on worked as assumed: the daily `pg_dump` backup had been failing because the tool's version did not match the database's (so the storage bucket was empty), and the failure emails were rejected by the receiver, so nobody knew; disk snapshots had not been enabled for the database servers; the only usable copy was a snapshot an engineer had taken about six hours earlier, for the staging environment. Copying it back took around 18 hours because the staging disks were slow and throttled. Database changes between 17:20 UTC and roughly midnight on 31 January were lost, which it estimated at about 5,000 projects, 5,000 comments and 700 user accounts. *Lessons:* a backup that fails silently is no backup; alert on **absence** of a good result; the slow part of a restore may be the disk you chose to save money on; replication is for staying up, not for going back (the report itself says so).

**Atlassian, "Post-Incident Review on the Atlassian April 2022 outage" (published 29 April 2022; read the summary, the architecture and DR sections, and the support and communications sections).** A deletion script was given the identifiers of whole sites instead of one app, and an API that accepted both kinds of identifier with no warning deleted 883 sites (775 customers) in 23 minutes on 5 April 2022. The company says no cyberattack was involved and no customer lost more than five minutes of data, but restoration took up to 14 days for some customers because it could restore one data store at a time and had no automated way to restore many sites across many products. Internal monitoring did not detect it, because the deletion went through a standard workflow; the first signal was a customer's support ticket. *Lessons:* RPO and RTO are separate promises, and it met one; recovery at scale needs automation that was **tested at scale**; deletion needs a soft-delete step; contact data was lost too; a deliberate destructive action is invisible to monitoring built for failures.

**Amazon Web Services, "Summary of the Amazon DynamoDB Service Disruption in the Northern Virginia (US-EAST-1) Region" (event 19 to 20 October 2025; read the DynamoDB, load balancer and EC2 sections' introduction).** See [third-party and cloud dependencies](#third-party-and-cloud-dependencies). *Lessons:* a regional dependency is a single point of failure for everything in the region; a recovery plan that needs the provider's control plane to launch new capacity can fail in the same event; "the DNS record is wrong" can break every service that looks up that name.

**CrowdStrike, "External Technical Root Cause Analysis: Channel File 291" (August 2024; read the whole report's findings and mitigations headings).** See above. *Lessons:* staged rollout and canary rings are not only for your own releases; ask vendors whose agents run on your machines how they stage updates; and plan a manual recovery path for machines that will not start (my inference, not a finding of the report).

I looked for a fifth, OVHcloud's March 2021 Strasbourg fire. The vendor page I tried (a corporate newsroom address) returned "404 - Page not found", so I read nothing and cite nothing about it.

**What the four share:** the most expensive failure was not the first event but the discovery that the recovery path did not work, or took far longer than anyone assumed, or needed something that was also down.

## A worked plan for this project

This is the section to read with the repository open. The pieces are the ones outside, or underneath, the code, because [the code is the backup for the machines](Backups-Recovery-and-Patching.md#where-this-shows-up-in-this-project) and everything else needs its own answer.

**How to read the table.** *Protects* is what the piece is for. The **proposed RTO and RPO** are what a hobby project run by one person in their spare time could honestly **promise**, set low on purpose; they are my proposals, are **est.**, and were never timed. *Recovery steps* are only those the repository already writes; where there are none, the cell says **None**. *Covered by* names the repository document or test, and whether it has been run; I have checked that the files exist and what they say, not that the steps work.

**The recovery order** follows the dependencies, bottom first:

1. The repository (the code and these documents).
2. The secret store (everything that runs needs a token from it).
3. Spacelift (state, and the only place a plan or apply runs).
4. Twingate (the way in) and the DigitalOcean account.
5. The connectors (rebuilt by a Spacelift run, which needs 1 to 4).
6. The wiki (generated from the repository, so it can come back any time after 1).
7. The home logging server (receives from the connectors; last).

The checker in [Exercise 1](#exercise-1-check-a-recovery-table-for-contradictions) turns this order into a table and tests that no piece promises to come back before something it needs.

### 1. The repository

| | |
|---|---|
| **Protects** | The code, the documents, the tests and the CI definitions: everything that rebuilds the rest. Also the issues, the project board and the pull-request history, which are not in a clone of the code. |
| **Tier** | 0 |
| **Proposed RTO / RPO** | RTO a day (est.). RPO: whatever was last pushed; open pull requests, issues and the board have no copy. |
| **Recovery steps** | Clone from the hosting service, or from any machine that has a clone. A clone holds the full history of the branches it fetched (general git knowledge). For loss of the hosting account: **None.** |
| **Covered by** | Branch protection on `main` is mentioned in the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) (section 8). A backup or mirror of the repository, the issues or the board: **None.** |
| **Gap** | Nothing is written down about a copy outside the hosting service, or about exporting issues and the board. |

### 2. The secret store (Doppler)

| | |
|---|---|
| **Protects** | The values every run needs: the DigitalOcean token, the Twingate API token, the tenant name and the administrator key values. The inventory table in the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) (section 2) lists them and their 90-day lifetimes. |
| **Tier** | 0 |
| **Proposed RTO / RPO** | RTO an evening (est.), because the credentials are reissued, not restored. RPO: not applicable for the tokens (they are regenerated); the values that are **not** credentials (the tenant name, the administrator key name and user ids) are the data that would actually be lost, and the runbook does not say where else they are kept. |
| **Recovery steps** | Rotation steps for each token are written (secrets runbook, section 5), including creating a new DigitalOcean token with the scopes in section 4a and a new Doppler service token and replacing the value in the Spacelift context. Recreating a lost Doppler project and config from nothing: **None.** |
| **Covered by** | The rotation steps; troubleshooting table (section 7) names the "could not read NAME from Doppler" failure. `tests/test_doppler_env.py` exercises the hook script that reads the secrets (with fakes, offline). Real loss of the Doppler account, run end to end: **None.** |
| **Gap** | If the store is unavailable, the hook script has no alternative source, and the runbook gives none. |

### 3. Spacelift state (and the Spacelift account)

| | |
|---|---|
| **Protects** | The OpenTofu **state**: the record of which real droplet, firewall, network and Twingate object each resource in the code corresponds to. Also the stack settings, contexts and policies, which are not in the code (the policy bodies are, the live copy is a paste). |
| **Tier** | 0 |
| **Proposed RTO / RPO** | RTO a weekend (est.). RPO: **no promise**, because I found no documented copy of the state outside Spacelift. |
| **Recovery steps** | In a local lab only: [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) shows losing a state file and recovering with a saved copy (Exercise 8), `import` and `state rm` (Exercise 9) and a break-and-recover drill (Exercise 11). Those Bash exercises were run on a scratch folder on 2026-10-22 per that page; none was run against this project's real state. For the real state: **None.** |
| **Covered by** | [Spacelift](Spacelift.md) says Spacelift holds the state; [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) lists contexts and policies as outside the stacks. A procedure for restoring the stacks if the Spacelift account is lost: **None.** Whether Spacelift offers state history or download for this plan: **not checked on 2026-10-31**; find out first. |
| **Gap** | The most important single-copy item in the project has no recorded copy and no drill. The cheap fix, if the plan allows it, is a periodic encrypted export kept in a second place; I have not checked that it can be done. |

### 4. Twingate (the account and the access layer)

| | |
|---|---|
| **Protects** | The only way in. The droplets have no public SSH, and the stage 1 guide says the account has no console password by design, so with Twingate down there is no remote access to them. |
| **Tier** | 0 |
| **Proposed RTO / RPO** | RTO an evening (est.) for the access layer, rebuilt from code. RPO: what the code declares comes back; objects made by hand in the console and the identity-provider link do not (the [teardown page](Teardown-Checklist.md#2-what-survives-a-destroy) says the stacks destroy and create only what they made). |
| **Recovery steps** | Stack 10 builds the remote network, groups, resources and connectors from code ([stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)). A lost Twingate **account** (new account, new API key, identity-provider link, then a run): **None.** |
| **Covered by** | [Twingate](Twingate.md) and the [two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) page (a failover test is written, status: nothing applied or tested for that page). Tests of the code run with a mocked provider only. |
| **Gap** | There is no break-glass path if Twingate and both connectors are unavailable. The stage 1 guide says the Droplet web console is not an option. |

### 5. The connectors

| | |
|---|---|
| **Protects** | Private access to the droplets. They hold no data of their own: the stage 1 guide calls them stateless. |
| **Tier** | 1 |
| **Proposed RTO / RPO** | RTO: a few minutes for one connector once a run can start; a few hours if everything above also has to come back (est.). RPO: not applicable (nothing is kept on them). |
| **Recovery steps** | [Stage 1 guide, section 6a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md): "If a connector shows offline", including the case where both are down: in a Spacelift run, replace the affected droplet and its connector token, read the plan, confirm; "expect a few minutes of outage for that connector". Also written: the rotate-the-token steps. |
| **Covered by** | Section 6a (written; I found no record that it was drilled). The lessons-learned entry on a [rebuilt account](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true) is the nearest thing to a real full rebuild: the account was rebuilt and everything redeployed, the first apply found four limits, and the page records no time. The by-hand outside check for zero open ports ([stage 1, 6b](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)) verifies a rebuild did not open anything. Golden-hash `tofu test` checks pin the rendered first-boot configuration. |
| **Gap** | The redeploy was done, but its duration was not recorded, so the RTO has no measurement behind it. |

### 6. The wiki

| | |
|---|---|
| **Protects** | The lessons, published to the repository's GitHub wiki. |
| **Tier** | 3 |
| **Proposed RTO / RPO** | RTO a day (est.). RPO: the last merge to `main`, because the pages are written in the repository and the wiki is generated from them. |
| **Recovery steps** | The publish workflow runs on a push to `main` and can be started by hand (`.github/workflows/wiki.yml`), regenerating the whole tree with `scripts/gen-wiki.sh`. That script's own header says edits made in the wiki editor are overwritten on the next publish. A lost wiki is therefore re-published, not restored; this was **not run for this page**. |
| **Covered by** | `tests/test_gen_wiki.py` and the navigation tests under `tests/` cover generation and links. Re-publishing into an empty wiki: **None** (not run). |

### 7. The home logging server

| | |
|---|---|
| **Protects** | A place for the connectors' logs to go (a log manager at home that is not part of this repository). Convenience and, later, detection. |
| **Tier** | 3 |
| **Proposed RTO / RPO** | RTO a week (est.), and nobody is waiting. RPO: logs sent while it is down are lost unless the sending agent keeps them; I did not check whether it does. |
| **Recovery steps** | **None** for the server itself: the [stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) is about what you set up at home before the cloud sends anything, and it says the home SIEM repository's own changes are out of scope. |
| **Covered by** | The log shipping to it is opt-in, off by default and, per the [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md), "nothing here is applied". `tests/test_log_shipping_script.py` and related tests cover the shipping script with fake binaries only. |
| **Gap** | Everything about recovering the server is outside this repository. Treat it as tier 3 until it is built and written up. |

**What the plan says about the project, in plain words.** The machines are the easy part: stateless, rebuilt from code, with a written procedure. The hard part is the **control plane that rebuilds them**: the secret store, Spacelift and its state, the Twingate account, and the repository's non-code content. Each is a single copy at a vendor with no recorded export, and none has been drilled. The honest sentence for the project is: **we can rebuild the machines in an evening if the control plane survives; if the control plane is lost, there is no written way back, and the first job is to write one.**

## Free exercises

Every exercise follows four steps: **predict**, **do**, **check**, **undo**.

### Exercise 1: check a recovery table for contradictions

**Predict.** Look at the project table below. How many of the seven rows will the checker flag, and what kind of problem do you expect for each?

**Do.** Save the script as `bia_check.py` and the table as `recovery.csv` in an empty folder. The script only reads the file you name. It is Python 3 using the standard library.

```python
# bia_check.py FILE [--today YYYY-MM-DD] : read a recovery table (CSV) and print what does not add up.
# FAIL = the table contradicts itself. WARN = a promise nobody has proved. NOTE = a gap you chose.
# Exit code 1 when there is any FAIL, else 0. It reads one file and changes nothing.
import argparse
import csv
import datetime
import sys

parser = argparse.ArgumentParser()
parser.add_argument("file")
parser.add_argument("--today", default=datetime.date.today().isoformat())
args = parser.parse_args()
today = datetime.date.fromisoformat(args.today)


def num(text):
    return float(text) if text.strip() else None


with open(args.file, newline="", encoding="utf-8") as fh:
    rows = {r["system"]: r for r in csv.DictReader(fh)}

findings = []
for name, r in rows.items():
    rto, rpo, copy = num(r["rto_hours"]), num(r["rpo_hours"]), num(r["copy_every_hours"])
    if rpo is None:
        findings.append(("NOTE", name, "no RPO promised"))
    elif copy is None:
        findings.append(("WARN", name, f"promises an RPO of {rpo:g} h but no separate copy is made on a schedule"))
    elif copy > rpo:
        findings.append(("FAIL", name, f"a copy every {copy:g} h cannot meet an RPO of {rpo:g} h"))
    if copy is not None:
        tested = r["last_restore_test"].strip()
        if not tested:
            findings.append(("WARN", name, "a copy is made but it has never been restored"))
        elif (today - datetime.date.fromisoformat(tested)).days > 365:
            findings.append(("WARN", name, f"the last restore test ({tested}) is more than a year old"))
    for dep in [d for d in r["depends_on"].split(";") if d.strip()]:
        if dep not in rows:
            findings.append(("FAIL", name, f"depends on '{dep}', which is not in the table"))
        elif rto is not None and num(rows[dep]["rto_hours"]) is not None and rto < num(rows[dep]["rto_hours"]):
            findings.append(("FAIL", name, f"RTO {rto:g} h is shorter than {dep}'s {num(rows[dep]['rto_hours']):g} h, and it needs {dep} first"))

for level, name, message in sorted(findings, key=lambda f: ("FAIL", "WARN", "NOTE").index(f[0])):
    print(f"{level:4}  {name}: {message}")
print(f"{len(rows)} systems, {sum(1 for f in findings if f[0] == 'FAIL')} fail, {sum(1 for f in findings if f[0] == 'WARN')} warn")
sys.exit(1 if any(f[0] == "FAIL" for f in findings) else 0)
```

```text
system,tier,rto_hours,rpo_hours,copy_every_hours,last_restore_test,depends_on
repository,0,24,24,,,
secret_store,0,24,,,,
spacelift,0,48,,,,repository;secret_store
twingate,0,48,,,,
connectors,1,72,,,,spacelift;twingate;secret_store
wiki,3,72,24,,,repository
logging_server,3,168,,,,connectors
```

The table is the proposal from the project plan above (the checker does not read the tier column; it is there for you); `copy_every_hours` is blank where the repository documents no scheduled separate copy. Run it:

```bash
python3 -I bia_check.py recovery.csv --today 2026-10-31
echo "exit code: $?"
```

**Check.** On 2026-10-31 (Python 3.13.5) this printed:

```text
WARN  repository: promises an RPO of 24 h but no separate copy is made on a schedule
WARN  wiki: promises an RPO of 24 h but no separate copy is made on a schedule
NOTE  secret_store: no RPO promised
NOTE  spacelift: no RPO promised
NOTE  twingate: no RPO promised
NOTE  connectors: no RPO promised
NOTE  logging_server: no RPO promised
7 systems, 0 fail, 2 warn
exit code: 0
```

Read it as a plan, not a score. Two warnings: the table promises a 24-hour RPO for the repository and the wiki with no scheduled copy, which is true to what the repository documents (a clone is made when someone chooses to). Five notes: for these pieces the honest answer today is that **no recovery point is promised**, and it is better to print that than to leave it silently blank. Nothing failed because every RTO is at least that of what the piece depends on. Now break it on purpose with this second table, saved as `broken.csv`:

```text
system,tier,rto_hours,rpo_hours,copy_every_hours,last_restore_test,depends_on
shop,1,2,4,24,2024-01-05,database
database,1,8,4,4,2026-09-01,
cache,2,1,,,,database;queue
```

```bash
python3 -I bia_check.py broken.csv --today 2026-10-31
echo "exit code: $?"
```

It printed four FAIL lines (a daily copy cannot meet a 4-hour RPO; `shop` and `cache` each promise to recover faster than the database they need; `cache` depends on `queue`, which is not in the table), one WARN (a restore test from January 2024 is stale), one NOTE, and `exit code: 1`.

**Undo.** Delete the folder.

**Then, on paper.** Fix the project table: put your own honest numbers in, and for every NOTE decide whether it is a choice or an oversight. A NOTE you cannot justify is a finding.

### Exercise 2: write a one-page runbook for the thing you could least afford to lose

**Predict.** Which one thing in your own setup (a laptop, a phone, a small server, a cloud account, a password manager) would hurt most to lose? Who besides you could recover it?

**Do.** Fill in the seven headings from [Runbooks](#runbooks) for that one thing, on one page. For each item you cannot fill in, write "unknown" and do not guess.

**Check.** Count the "unknown" lines. Then do the part that matters: ask someone who is not you to read the page and tell you where they would get stuck.

**Undo.** Keep it; it is real.

### Exercise 3: a contact tree and a holding statement

**Predict.** If your main way to reach people were down for a day, how many of your important contacts could you reach another way?

**Do.** On a card: the people to call (at least two ways each), who decides, and a holding statement with blanks: "At TIME we found PROBLEM. It affects THING. We do not yet know CAUSE. We are doing ACTION. Next update at TIME."

**Check.** Is the card somewhere that survives the loss of the system it is about? Put a printed copy in a drawer.

**Undo.** Nothing to undo.

### Exercise 4: a free tabletop on a scenario from this project

This is the exercise the lesson has been building toward. It is discussion only: nothing is run, restored or changed, and no account is touched. You need this page, the repository open at the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) and the [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md), pencil and paper, and 45 to 60 minutes.

**Scenario: "The locked secret store."** It is a Saturday morning. You open a small pull request that changes a firewall rule and it merges. The Spacelift run that follows fails in its first seconds. The scenario is invented; every message below is the one the secrets runbook's troubleshooting table gives for the failure it names, and everything else is an assumption the facilitator reads out.

**Cast.** Facilitator (a friend, or you reading the cards in order with the next one face down), incident lead, technical lead, scribe, communications lead. Alone: play each role in turn and write what each would say.

**Ground rules.** No blame. Play it straight. **Only what is written down counts.** If you would have to remember or guess, the scribe writes GAP.

**The injects, one at a time.** After each one answer: *what do we do, who does it, where is that written?*

1. **The failure.** The run log says `could not read DIGITALOCEAN_TOKEN from Doppler`. *What does the runbook say this means?* (Look in the troubleshooting table.) *What do you check first?*
2. **The cause is not an expiry.** You try to sign in to the secret store and your account is locked after a security review. The vendor says a person will answer within two days (an assumption of this scenario, not a fact about any vendor). *Can anyone else get in? Is there a second administrator? Where is that written?*
3. **A second thing breaks.** A connector shows offline in the Twingate console. *What does the stage 1 guide, section 6a, say to do?* Read the steps. *What does each step need?* (A Spacelift run; the run needs the secrets.) *Do you have a loop?*
4. **No way in.** The second connector goes offline too. *What does the guide say about getting onto the droplets by another route?* (Read the paragraph in 6a.) *Write down what you can still do.*
5. **A message to send.** A friend who uses the lessons asks on a public channel why the wiki is not updating. *Who answers, what do they say, and where is the holding statement?*

**Questions for the whole group at the end.** What was recovered first, and why that order? What did the plan need that was itself down? What single fact, if written down in advance, would have saved the most time?

**What to expect to find** (these are readings of the repository on 2026-10-31, to check against your own reading): the troubleshooting table covers the failure message and says to rotate the service token or add the secret; the rotation steps assume you can sign in to Doppler and to Spacelift; the repository documents **no second administrator, no alternative source for the secrets and no break-glass path to the droplets**; and the project has no written communications plan. If you find different, believe your reading and open an issue.

**Check.** Turn the scribe's gaps into **at most three findings**, each with an owner and a date. A good set from this scenario would be of the form: "write down who else can recover the secret store", "decide what the break-glass path is, or accept the risk in writing", "write the holding statement". They are examples of the form; yours may differ.

**Undo.** Nothing to undo. Keep the findings.

## Checkpoint

You are done when you can answer these without looking:

1. In one sentence each, what do BCP and DR cover, and which one asks "how do we keep doing the job"?
2. What is the relationship between MTD and RTO, and why must RTO be shorter?
3. A database has an RPO of one hour. Name two things that would have to be true for the promise to hold.
4. Why can a system's RTO not be shorter than that of a system it depends on?
5. Name the four AWS approaches in order of cost, and say what none of them fixes on its own.
6. What is the difference between a restore and a recovery exercise?
7. Why is a replica not a backup, and why does ransomware make that worse?
8. Name three things a runbook needs that a list of commands does not.
9. In this project's plan, which pieces are tier 0, and what is the project's honest one-sentence summary?

## Common mistakes

- **Writing an RTO for a system and forgetting its dependencies.** The order of recovery is the order of dependencies.
- **Counting a backup you never restored.** Count restores.
- **Putting the plan where the outage will hide it.** The runbook for the secret store should not live only in the secret store.
- **Giving every system the same tier.** If everything is critical, nothing is.
- **A tabletop that tries to fix things.** The exercise finds gaps; the fixing is a separate task with an owner and a date.
- **Treating a vendor's promise as your promise.** A provider's uptime goal is not your RTO.
- **Planning for a fire and not for a deletion.** A mistake or an attacker deleting things looks like a disaster that no standby will cure.

## Claims register

Every vendor and standards claim on this page, with where it was read. Statuses: "Read" means I read the page or document on that date; "Observed" means I ran it; **est.** means an estimate or my own proposal; "General knowledge" means common practice that I did not check against a source for this page.

| Claim | Source | Status |
|---|---|---|
| BCP, BIA, RTO, RPO, MTD, DRP, cold, warm and hot site definitions quoted, the BCP and DRP descriptions in section 2.2, the three BIA steps, the sample alternate site table, the tabletop and functional exercise definitions, and the crisis communications plan paragraph | [NIST SP 800-34 Rev. 1, DOI 10.6028/NIST.SP.800-34r1](https://doi.org/10.6028/NIST.SP.800-34r1), May 2010, updated 2010-11-11; catalog page at csrc.nist.gov/pubs/sp/800/34/r1/upd1/final and the full PDF | Read 2026-10-31. The catalog page also shows a planning note dated 2023-03-17 whose text did not appear in my copy; check it for a newer revision. |
| BIA description, impacts to count, and "restore first the processes with the greatest impact" | [Ready.gov, Business Impact Analysis](https://www.ready.gov/business-impact-analysis) | Read 2026-10-31; page showed "Last Updated: 03/25/2026" |
| The four DR approaches, pilot light and warm standby wording, "near zero" for active/active, backup for corruption, control plane versus data plane advice | [AWS Well-Architected, Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html) | Read 2026-10-31 |
| Offline encrypted backups, test restores, golden images, infrastructure as code backed up offline, hypervisor targeting, hard-copy plan, out-of-band communication, isolate then restore from offline backups by priority, "do not re-infect" | [CISA #StopRansomware Guide](https://www.cisa.gov/stopransomware/ransomware-guide) | Read 2026-10-31 (page revision date not shown in my copy) |
| CTEPs: templates, over 100 scenarios, no charge mentioned on the page, after action report template | [CISA Tabletop Exercise Packages](https://www.cisa.gov/resources-tools/services/cisa-tabletop-exercise-packages) | Read 2026-10-31 |
| GitLab January 2017 outage: dates, 300 GB, four recovery routes, `pg_dump` version mismatch, failure mail rejected, 18-hour copy, estimated data lost | [GitLab, Postmortem of database outage of January 31](https://about.gitlab.com/blog/postmortem-of-database-outage-of-january-31/), published 2017-02-10 | Read 2026-10-31 (through the data-loss section; not the "improvements" section) |
| Atlassian April 2022: 883 sites, 775 customers, up to 14 days, missed RTO and met RPO, contact data deleted, four learnings, three-hour cadence, code freeze | [Atlassian, Post-Incident Review on the April 2022 outage](https://www.atlassian.com/engineering/post-incident-review-april-2022-outage), 2022-04-29 | Read 2026-10-31 (summary, DR program, incident and communications sections; not the full recovery workstreams) |
| AWS US-EAST-1 disruption: times, DNS management defect, dependent services, EC2 launches | [AWS, Summary of the Amazon DynamoDB Service Disruption in the Northern Virginia (US-EAST-1) Region](https://aws.amazon.com/message/101925/) | Read 2026-10-31 (opening summary and DynamoDB section only) |
| CrowdStrike July 2024: content update on 2024-07-19, out-of-bounds read, staged deployment and customer control as mitigations, about 99 percent of Windows sensors online by 2024-07-29 | [CrowdStrike, External Technical Root Cause Analysis: Channel File 291](https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf) (file name carries 08.06.2024; the folder is August 2024) | Read 2026-10-31 (introduction, what happened, findings 6 and the mitigations list) |
| OVHcloud March 2021 fire | `corporate.ovhcloud.com` newsroom address I tried | Not read: the page returned "404 - Page not found" |
| ISO 22301 and other business continuity standards | None | Not read; not quoted |
| Roles table, runbook headings, contact tree and holding statement shapes | Common practice | General knowledge |
| Tier table (0 to 3) and its targets | My illustration | **est.**; no standard read |
| Every RTO and RPO for this project | My proposals from the repository documents named | **est.**; never timed |
| Secrets inventory, rotation steps, troubleshooting messages, known limits | [`docs/spacelift-secrets.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md), sections 2, 4a, 5, 7, 8 | Read 2026-10-31 in this repository; no step run |
| Connector offline and rebuild steps, "stateless", no console password by design | [`docs/stages/01-access.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md), sections 6a and 6b | Read 2026-10-31 in this repository; no step run |
| Stage 2 telemetry: nothing applied, opt-in log shipping | [`docs/stages/02-telemetry.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md), section 2.4 | Read 2026-10-31 in this repository |
| What survives a destroy | [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) | Read 2026-10-31 in this repository |
| State lives in Spacelift; local state lab results | [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) | Read 2026-10-31 in this repository; its own status says the Bash exercises were run on 2026-10-22 |
| The wiki publish workflow and generator | `.github/workflows/wiki.yml`, `scripts/gen-wiki.sh` | Read 2026-10-31 (headers and triggers); not run |
| The checker script and both sample tables | This page, Exercise 1 | Observed 2026-10-31, Python 3.13.5 |
| Whether Spacelift offers state download or history on this plan | None | **est.**: not checked |
| Whether the Wazuh agent buffers events while the manager is down | None | **est.**: not checked |

## Where to next

- [Backups, recovery and patching](Backups-Recovery-and-Patching.md) for the restore drill, if you skipped it.
- [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md), whose emergency changes are what an incident looks like from the change process.
- [Teardown checklist](Teardown-Checklist.md), which is a recovery plan for a planned ending.
- [Threat model](Threat-Model.md), to ask which of these scenarios are the likely ones.
