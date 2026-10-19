# Reading order

Pick the row that sounds like you. Every path is a numbered list: read in that order. The tables on this page are the authority. A page's **Next** line follows the core path if the page is on it, and otherwise follows the track that page belongs to (build, security, detection or other clouds); when you are on a different track from a page's Next line, follow the table instead. The first path, the core path, is the one to take if you are unsure; the other paths branch off it.

> **Status honesty.** The pages for DigitalOcean, stages 0 and 1, the labs, the threat model and the settings reference describe things that are built and tested. The pages for AWS, Azure and GCP are **unverified drafts**: written from the vendors' own documentation, not applied in a real account, and labelled that way in their first lines and in the title column below. Stages 3 and 4 are planned, not built. Stage 2 is built on the cloud side and merged but never applied, and the five telemetry pages in the detection path are **unverified drafts**: written from the stage 2 design, and none checked against a real deployment.

## Which path is for me

| Path | Who it is for | Pages | Reading time |
|---|---|---|---|
| [The core path](#the-core-path) | Everyone, and anyone unsure where to start. | 21 | about 3 h 15 min of reading |
| [Build it yourself](#build-it-yourself) | A learner replicating the build in their own accounts. | 5 | about 1 h 10 min of reading |
| [Understand the design](#understand-the-design) | An engineer who wants the design without the primers. | 12 | about 1 h 35 min of reading |
| [Security and threat modelling](#security-and-threat-modelling) | A security-minded reader. | 5 | about 1 h 15 min of reading |
| [Detection and monitoring](#detection-and-monitoring) | Someone asking how it would be watched, and who wants to build a small version. | 9 | about 2 h 10 min of reading |
| [Enterprise context](#enterprise-context) | A reader who wants to see how companies build networks, run infrastructure and handle identity, how they run changes, and what roles and skills surround that work. | 5 | about 1 h 30 min of reading |
| [Other clouds (unverified drafts)](#other-clouds-unverified-drafts) | A multi-cloud reader (unverified drafts). | 10 | about 2 h 15 min of reading |
| [Reference](#reference-look-things-up) | Anyone, at any point. | 7 | lookup, not read through |

**How the times are estimated.** Each page is counted by its word count at 200 words a minute (a deliberately slow, technical-reading pace, because these pages are full of tables and code), rounded up to the next 5 minutes. That is reading time only. Where a page asks you to do something and says how long it takes, that is added separately in the notes under each path: the labs (five at about 15 minutes each, as the page says), the Threat Dragon exercise (the page asks for an hour) and the threat model exercise (a ten-minute predict step and three what-ifs at ten minutes each). The build page states no time, so none is invented; budget for waiting on account sign-ups and Spacelift runs. Lookup pages (the settings reference and the glossary) are marked "lookup" and left out of the totals.

## The core path

**Who it is for.** Everyone. Read this top to bottom and you have the whole design: what it is, why it is shaped this way, how a change reaches the cloud, what can go wrong, and what comes next.

**Before you start.** None. If a word on any page is new, the Glossary and the primers (steps 2 to 9) are there for it.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Start here if you are new](Start-Here-If-You-Are-New.md) | 10 min |  |
| 2 | [What is the cloud](What-Is-the-Cloud.md) | 10 min |  |
| 3 | [Networking basics for this project](Networking-Basics-for-This-Project.md) | 10 min |  |
| 4 | [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) | 10 min |  |
| 5 | [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) | 10 min |  |
| 6 | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) | 10 min |  |
| 7 | [Containers and Docker basics (optional, for stage 3)](Containers-and-Docker-Basics.md) | 10 min | Optional. Skip it unless you plan to read about stage 3. |
| 8 | [How money works in the cloud](How-Money-Works-in-the-Cloud.md) | 10 min |  |
| 9 | [Enterprise engineering habits](Enterprise-Engineering-Habits.md) | 10 min | You can explain, in your own words, why there is no open port, what a plan is, and what the cost gate refuses. |
| 10 | [Architecture overview](Architecture-Overview.md) | 10 min |  |
| 11 | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) | 15 min |  |
| 12 | [Twingate](Twingate.md) | 10 min |  |
| 13 | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) | 5 min |  |
| 14 | [Droplet hardening](Droplet-Hardening.md) | 5 min | You can name the one way in and the two things that make the droplets private. |
| 15 | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) | 5 min |  |
| 16 | [Spacelift](Spacelift.md) | 10 min |  |
| 17 | [Doppler and secrets](Doppler-and-Secrets.md) | 5 min |  |
| 18 | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | 10 min | You can say which gate stops a bad change at each of: pull request, merge, plan, apply. |
| 19 | [Threat model](Threat-Model.md) | 10 min | You can point at one accepted risk and say why it was accepted. |
| 20 | [Lessons learned](Lessons-Learned.md) | 10 min |  |
| 21 | [Roadmap](Roadmap.md) | 10 min | You know what is built and applied (stages 0 and 1), what is built but unapplied (the stage 2 cloud side) and what is only planned. |

## Build it yourself

**Who it is for.** A learner who wants a private copy running, or who wants to see every safety check fail on purpose before trusting it.

**Before you start.** The core path through step 18 (CI, tests and the cost gate). The capstone leans on Spacelift and Doppler.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) | 20 min | You have a private fork and know which settings are demo values to replace. |
| 2 | [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) | 15 min | Each of the five labs: you predicted the check that would object, and it did. |
| 3 | [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) | 15 min | Stage 0 applied, stage 1 connected, then torn down and the bill proved zero. |
| 4 | [Settings reference](Settings-Reference.md) | lookup | You can find where any value lives (variable, tfvars, Doppler or cost.json). |
| 5 | [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) | 20 min | You can say, for any value, whether it belongs in a variable, a tfvars file, Spacelift, Doppler or cost.json, and why `resource_key` never changes on a live stack. |

The settings reference is a lookup page: it is generated from one manifest and meant to be searched, not read through. Doing, not just reading: Labs adds about 75 minutes (five labs at about 15 minutes each, as the page says).

## Understand the design

**Who it is for.** An engineer who already knows Terraform and CI and wants the design without the primers. If a page uses a word you do not know, take the primer named in its first lines.

**Before you start.** Working knowledge of infrastructure as code and pull requests.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1  | [Architecture overview](Architecture-Overview.md) | 10 min |  |
| 2 | [Why I picked these tools](Why-I-Picked-These-Tools.md) | 5 min | You can say which pieces are personal picks and where each would change at a small business or an enterprise. |
| 3 | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) | 5 min |  |
| 4 | [Terraform reference](Terraform-Reference.md) | 25 min | You can read any file in `stacks/` and say what it creates. |
| 5 | [Spacelift](Spacelift.md) | 10 min |  |
| 6 | [Doppler and secrets](Doppler-and-Secrets.md) | 5 min |  |
| 7 | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | 10 min |  |
| 8 | [Trace one change end to end](Trace-One-Change-End-to-End.md) | 15 min | You can name each gate one real pull request passed through, in order. |
| 9 | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) | 15 min | You can argue for or against the no-VPN decision with the page's evidence. |
| 10 | [Twingate](Twingate.md) | 10 min |  |
| 11 | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) | 5 min |  |
| 12 | [Droplet hardening](Droplet-Hardening.md) | 5 min |  |

## Security and threat modelling

**Who it is for.** A security-minded reader, or anyone who wants to practise threat modelling on a real, small system.

**Before you start.** The core path through step 17 (Doppler and secrets), plus the Identity primer.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Threat model exercise: build your own](Threat-Model-Exercise.md) | 20 min | Steps 1 to 3 done before you open the threat model; then compare. |
| 2 | [Threat model](Threat-Model.md) | 10 min | Your list against the worked one: what did you miss, what did you rate differently. |
| 3 | [Threat Dragon exercise: trust boundaries](Threat-Dragon-Exercise.md) | 20 min | You found each trust boundary in the diagram; the last part adds a second cloud and links the unverified AWS drafts. |
| 4 | [Threat frameworks: STRIDE, ATT&CK and ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) | 25 min | You can say which of the three frameworks answers which question, and you imported at least one of the two extra models into Threat Dragon. |
| 5 | [Troubleshooting index](Troubleshooting-Index.md) | lookup | You can go from a symptom to the page that has the fix. |

The exercise page tells you to stop after step 3 and read the threat model only then, so the threat model is listed second. Do not open it first. Doing, not just reading: Threat model exercise adds about 40 minutes (a ten-minute predict step and three what-ifs at ten minutes each, as the page says). Doing, not just reading: Threat Dragon exercise adds about 60 minutes (the page asks for an hour). Threat frameworks adds about an hour (importing two models and the predict-then-check exercises).

## Detection and monitoring

**Who it is for.** Someone asking how a company would watch this, what the lab does and does not detect today, and how to build a small cloud version of the watching. Rows 3 to 9 are unverified drafts: written from the design, with the cloud-side stage 2 pieces built and merged but none of it applied or run.

**Before you start.** The Threat model (core step 19), because the detection page starts from its residual-risk column. Rows 3 to 7 also lean on Twingate (core step 12) and, for the last one, the cost gate (core step 18).

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) | 15 min | You can name what this project is not, and which product class covers each gap. |
| 2 | [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) | 15 min | For each threat T1 to T14 you can name the log line or event that would show it. |
| 3 | [Cloud telemetry: what and why (unverified draft)](Cloud-Telemetry-What-and-Why.md) | 10 min | You can sort a fact into log, metric, trace or alert, and say what a NOC, a SOC and a SIEM each is. |
| 4 | [Multiple sites and identity (unverified draft)](Multiple-Sites-and-Identity.md) | 15 min | You can say why `resource_key` never changes on a live stack and what a second site changes in the cost gate. |
| 5 | [Telemetry crosses the trust boundary (unverified draft)](Telemetry-Crosses-the-Trust-Boundary.md) | 15 min | You can explain why a one-port resource is not read-only and where the secrets still live. |
| 6 | [Reading a dashboard as an operator (unverified draft)](Reading-a-Dashboard-as-an-Operator.md) | 15 min | You can say why `absent()` cannot find a silent site and what does. |
| 7 | [Build your own mini SOC (unverified draft)](Build-Your-Own-Mini-SOC.md) | 20 min | You can fill the cost table for your own ceiling and name what each stage teaches. |
| 8 | [Stage 2 home-side runbook (unverified draft)](Stage-2-Home-Side-Runbook.md) | 15 min | You can say what must exist at home, with a recorded negative test, before any cloud host sends a log. |
| 9 | [Grafana dashboards (unverified draft)](Grafana-Dashboards.md) | 10 min | You can say which of the three dashboards answers "is a site up", "is a droplet healthy" and "did anyone log in", and which panels' field names are still UNVERIFIED. |
| 10 | [Lab: a synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) | 30 min, hands on | You predicted what a silent site does to each panel, then ran `silent-site` and compared. |
| 11 | [Roadmap](Roadmap.md) | 10 min | You know stage 2 is merged on the cloud side and not applied, and that the home side is not done. |

Nothing on these pages is deployed. The cloud hosts do not ship logs anywhere yet; the detection page says so at the top. Doing, not just reading: each telemetry page ends with a predict-then-check set; the times above are reading only.

## Enterprise context

**Who it is for.** A reader who will meet corporate networks, landing zones, identity providers, change tickets and vaults at work and wants the vocabulary, an honest account of what this project does instead, and a map of the roles and skills around it. These pages are orientation, not design guides: claims checked against a vendor page are dated, the rest is marked as general knowledge or UNVERIFIED.

**Before you start.** The core path through step 13 (DigitalOcean network and firewalls) and step 17 (Doppler and secrets), and [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md).

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Enterprise networks: campus, branch, data center and cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) | 15 min | You can say what a hub-and-spoke landing zone adds to this project's one VPC, and why a flat network fails. |
| 2 | [Enterprise infrastructure: how large organizations run it differently](Enterprise-Infrastructure-Differences.md) | 15 min | For each section you can say what this project does instead and when that would stop being fine. |
| 3 | [Enterprise change management for beginners (not used in this project)](Enterprise-Change-Management-for-Beginners.md) | 30 min | You can classify a change as standard, normal or emergency, and name three enterprise controls this project does not have. |
| 4 | [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) | 15 min | You can name where this project's Doppler, Spacelift and Twingate model scales and where it breaks. |
| 5 | [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) | 15 min | You can name three roles that fit your interests and the next three rungs of your own skills ladder. |

Doing, not just reading: each page ends with a predict-then-check set; the times above are reading only, rounded up to 5 minutes (the change management page is about 26 minutes at 200 words a minute, so 30; the others are 10 to 15).

## Other clouds (unverified drafts)

**Who it is for.** A reader curious how AWS, Azure and GCP differ, or planning a port. Every page here is an unverified draft written from vendor documentation, with nothing applied in a real account on those clouds.

**Before you start.** The core path through step 14 (DigitalOcean network and firewalls), so you know what is being compared.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Why the clouds differ (unverified draft)](Why-the-Clouds-Differ.md) | 10 min | You can state the three differences that change the bill and the one that changes the firewall. |
| 2 | [AWS: account preparation (unverified draft)](Provider-AWS-Account-Preparation.md) | 10 min |  |
| 3 | [AWS: the same four pieces (unverified draft)](Provider-AWS-The-Same-Four-Pieces.md) | 15 min |  |
| 4 | [AWS: where the money goes (unverified draft)](Provider-AWS-Cost-Lesson.md) | 10 min |  |
| 5 | [Azure: account preparation (unverified draft)](Provider-Azure-Account-Preparation.md) | 15 min |  |
| 6 | [Azure: the same four pieces (unverified draft)](Provider-Azure-The-Same-Four-Pieces.md) | 20 min |  |
| 7 | [Azure: where the money goes (unverified draft)](Provider-Azure-Cost-Lesson.md) | 15 min |  |
| 8 | [GCP: account preparation (unverified draft)](Provider-GCP-Account-Preparation.md) | 15 min |  |
| 9 | [GCP: the same four pieces (unverified draft)](Provider-GCP-The-Same-Four-Pieces.md) | 15 min |  |
| 10 | [GCP: where the money goes (unverified draft)](Provider-GCP-Cost-Lesson.md) | 10 min |  |

Each cloud has the same three pages in the same order: account preparation, the same four pieces, where the money goes.

## Reference: look things up

Not a path. Open these when you need them; every one is linked from the sidebar.

| Page | Use it when |
|---|---|
| [Glossary](Glossary.md) | A word or acronym is new. Terms marked **(basics)** are the ones to learn first. |
| [Troubleshooting index](Troubleshooting-Index.md) | Something failed and you have a symptom. |
| [Settings reference](Settings-Reference.md) | You want to change a value and need to know where it lives. Generated from one manifest. |
| [Terraform reference](Terraform-Reference.md) | You want every variable, resource and output explained line by line. |
| [Lessons learned](Lessons-Learned.md) | You want the things that broke during the build, and what fixed them. |
| [Roadmap](Roadmap.md) | You want to know what is built and what is only planned. |
| [How this project is planned](How-This-Project-Is-Planned.md) | You want to know how the work is organised: the board, sprints, sizes, definition of done. |
| [Screenshots policy](Screenshots-Policy.md) | You are adding a picture to a page, or want to know why a console is described but not shown. |
| [Home](Home.md) | You want the short version, the diagram and the current state. |

Operator guides that live in the repository rather than the wiki: [stage 0](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md), [stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md), the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) and the [cost guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

## Keeping this page honest

A test (`tests/test_wiki_navigation.py`) fails if a wiki page is in neither the sidebar nor this page, if the sidebar links to a page that does not exist, if a **Next** line names a page that does not exist, or if a page appears twice within one path above. When you add a wiki page, add it to a path here and to the sidebar in the same pull request.
