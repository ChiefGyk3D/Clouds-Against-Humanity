# Reading order

Pick the row that sounds like you. Every path is a numbered list: read in that order. The tables on this page are the authority. A page's **Next** line follows the core path if the page is on it, and otherwise follows the track that page belongs to (build, security, detection or other clouds); when you are on a different track from a page's Next line, follow the table instead. The first path, the core path, is the one to take if you are unsure; the other paths branch off it.

> **Status honesty.** The pages for DigitalOcean, stages 0 and 1, the labs, the threat model and the settings reference describe things that are built and tested. The pages for AWS, Azure and GCP are **unverified drafts**: written from the vendors' own documentation, not applied in a real account, and labeled that way in their first lines and in the title column below. Stages 3 and 4 are planned, not built. Stage 2 is built on the cloud side and merged but never applied, and the five telemetry pages in the detection path are **unverified drafts**: written from the stage 2 design, and none checked against a real deployment.

## Which path is for me

| Path | Who it is for | Pages | Reading time |
|---|---|---|---|
| [The core path](#the-core-path) | Everyone, and anyone unsure where to start. | 21 | about 3 h 15 min of reading |
| [Build it yourself](#build-it-yourself) | A learner replicating the build in their own accounts. | 6 | about 1 h 20 min of reading |
| [Understand the design](#understand-the-design) | An engineer who wants the design without the primers. | 13 | about 1 h 55 min of reading |
| [Security and threat modeling](#security-and-threat-modeling) | A security-minded reader. | 5 | about 1 h 15 min of reading |
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

**Before you start.** The core path through step 18 (CI, tests and the cost gate). The capstone leans on Spacelift and Doppler. If git commands are new, start with [Git from zero](Git-From-Zero.md) first; [From commit to pipeline](From-Commit-to-Pipeline.md) (in the design path below) has exercises for your private copy.

| # | Page | Read | Checkpoint |
|---|---|---|---|
| 1 | [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) | 20 min | You have a private fork and know which settings are demo values to replace. |
| 2 | [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) | 15 min | Each of the five labs: you predicted the check that would object, and it did. |
| 3 | [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) | 15 min | Stage 0 applied, stage 1 connected, then torn down and the bill proved zero. |
| 4 | [Settings reference](Settings-Reference.md) | lookup | You can find where any value lives (variable, tfvars, Doppler or cost.json). |
| 5 | [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) | 20 min | You can say, for any value, whether it belongs in a variable, a tfvars file, Spacelift, Doppler or cost.json, and why `resource_key` never changes on a live stack. |
| 6 | [Teardown checklist](Teardown-Checklist.md) | 10 min | You can name the order of destruction, what survives it, and the checks that prove the bill is zero. |

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
| 8 | [From commit to pipeline](From-Commit-to-Pipeline.md) | 20 min | You can say what CI, CD and shift left each mean here, and which gate stops a bad change at each step. Doing: three exercises on your own private copy. |
| 9 | [Trace one change end to end](Trace-One-Change-End-to-End.md) | 15 min | You can name each gate one real pull request passed through, in order. |
| 10 | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) | 15 min | You can argue for or against the no-VPN decision with the page's evidence. |
| 11 | [Twingate](Twingate.md) | 10 min |  |
| 12 | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) | 5 min |  |
| 13 | [Droplet hardening](Droplet-Hardening.md) | 5 min |  |

## Security and threat modeling

**Who it is for.** A security-minded reader, or anyone who wants to practice threat modeling on a real, small system.

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
| [Why this exists](Why-This-Exists.md) | You want to know why the project exists, where I am coming from, why Twingate, how the cost model works, and the build, break, detect, evade, defend loop. A side page; opinion, not a lesson; about 10 minutes; not counted in the path totals. |
| [Give feedback and open an issue](Give-Feedback-and-Open-an-Issue.md) | You found a mistake, a command failed, or you have a question, and you have never opened a GitHub issue. A side page; about 15 minutes (est.); free, like all feedback; not counted in the path totals. |
| [Git from zero: your first change](Git-From-Zero.md) | You have never used git, a terminal or GitHub Desktop. A side page to [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md); read it first if those are new. About 90 minutes with the exercise; not counted in the path totals. |
| [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) | The commands on the hardening and container pages look like another language, or you will meet RHEL, Amazon Linux, Ubuntu or SUSE at work. A side page to [Droplet hardening](Droplet-Hardening.md) and [Containers and Docker basics](Containers-and-Docker-Basics.md); about three hours with the lab; not counted in the path totals. |
| [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) | The words API, token, HTTP, JSON, scope or JWT are new or fuzzy. A foundations side page to [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md); read it before that page if those words are new. About 60 minutes with the free exercises (est.); not counted in the path totals. |
| [Spacelift from zero](Spacelift-From-Zero.md) | You have never used a hosted infrastructure-as-code runner, or "stack", "proposed run", "tracked run", "context" or "project root" are only words to you. Lesson I3 of the four-lesson infrastructure-as-code track, a foundations side page to [Spacelift](Spacelift.md) (core step 16); read it after lesson I2, "Plans, state, drift and recovery", and before lesson I4, "Build and destroy a stack per service" (both planned; they are linked from the lesson itself and from this table once they merge); no step is renumbered. About 90 minutes for the reading and free local exercises (est.); the optional own-account path adds about three hours (est.), at $0 on the free plan with no card (pricing page, retrieved 2026-10-22); not counted in the path totals. |
| [How a web request works](How-a-Web-Request-Works.md) | You typed a URL and want to know what happens next, or the words DNS, TLS, certificate, CA or handshake are new. A foundations side page to [Networking basics](Networking-Basics-for-This-Project.md); read it after that page and before [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) if those words are fuzzy. About 90 minutes with the free local lab (est.); the optional own-account path adds about an hour (est.); not counted in the path totals. |
| [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) | You want to understand DNS beyond one lookup (who owns a name, delegation, every record type, TTL, email records, DNSSEC), or you want to put a website on your own domain behind Cloudflare with the server locked to it. A foundations side page to [How a web request works](How-a-Web-Request-Works.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md); the third lesson of a four-lesson web-hosting track. About three hours with the free local DNS lab (est.); the optional own-account path adds an afternoon (est.), and its cost is the learner's own bill; not counted in the path totals, and no step is renumbered. |
| [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | "Hashed", "encrypted", "signed" and "key" sound like the same thing, or you want to know what a salt, a key pair, an SSH key or a certificate is. A foundations side page to [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md); read it alongside that page. About 75 minutes with the free exercises (est.); not counted in the path totals. |
| [The terminal and your first script](Terminal-and-Your-First-Script.md) | You have never used a terminal beyond copying commands, or exit codes, pipes, `PATH` and shell scripts are new. A foundations side page, read after [Git from zero](Git-From-Zero.md) and before [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md); no step is renumbered. About two and a half hours with the exercises (est.), all free and local; not counted in the path totals. |
| [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) | You want to know what a decoy, a honeytoken or a honeypot is, why a decoy alert is different, and how to try it safely with nothing exposed. A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md); the hub for five short lessons (what deception is, safety and law, a canary token, honeyfiles, and rules in the SIEM). About 8 to 10 hours with the local exercises (est.), all free and on your own computer; not counted in the path totals, and no step is renumbered. The on-premises path for your own hardware is two more pages, [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) and [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md), also free to read, with a hands-on part that uses your own machine. The cloud sensor lessons (track 2, three more pages, listed in the hub) use your own cloud account and are optional. |
| [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) | You want to know what running a honeypot on a cloud server of your own involves before you decide: the guardrails, the provider's acceptable-use policy, what it costs and what is not a spending cap. A foundations side page to [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md); the free theory lesson of track 2, followed by [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) (your own account and bill) and [Read what arrived](Deception-and-Honeypots-Read-the-Sensor-Logs.md) (invented logs, no account needed). About 1.5 hours for the reading (est.); not counted in the path totals, and no step is renumbered. |
| [Windows, Active Directory and macOS in the enterprise](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) | Your first job (or the one you want) manages Windows laptops and a domain, or "domain", "Active Directory", "Group Policy", "Kerberos", "Entra ID" or "MDM" are only words to you. A foundations side page, read after [The terminal and your first script](Terminal-and-Your-First-Script.md) and [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md), beside [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md); no step is renumbered. About four hours with the read-only exercises (est.), all free and local; the optional evaluation virtual machine adds about three hours (est.) on your own computer; not counted in the path totals. |
| [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) | "Web server", "PHP-FPM", "LAMP", "LEMP", "MariaDB" or "WordPress stack" are only words to you, or you want to build Apache and Nginx stacks side by side and see the differences. A foundations side page to [Containers and Docker basics](Containers-and-Docker-Basics.md), read after [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md); lesson W1 of the web-hosting track; no step is renumbered. About four hours with the free lab (est.); the optional droplet path adds about an hour (est.) on your own account; not counted in the path totals. |
| [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) | You want to know what a decoy, a honeytoken or a honeypot is, why a decoy alert is different, and how to try it safely with nothing exposed. A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md); the hub for five short lessons (what deception is, safety and law, a canary token, honeyfiles, and rules in the SIEM). About 8 to 10 hours with the local exercises (est.), all free and on your own computer; not counted in the path totals, and no step is renumbered. Cloud and on-premises honeypot lessons are separate and later. |
| [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | You want to do the subnet arithmetic yourself, or the words CIDR, NAT, port forwarding, default deny or stateful are only words to you. A foundations side page to [Networking basics](Networking-Basics-for-This-Project.md) that also prepares you for [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md); read it after the first and before the second. About two and a half hours with the free lab (est.); the optional own-account path adds about an hour (est.); not counted in the path totals. |
| [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) | You can run one WordPress site and want to see how a company runs thousands: caches, a CDN, a WAF, a load balancer, tenant isolation, and a pipeline that manages the servers, the code and the content. Lesson 4 of 4 in the web-hosting track, after the lesson on DNS, Cloudflare and hosting your own website; a foundations side page, no step is renumbered. About three hours with the free local lab (est.); every tier of the design can be built alone or together and is costed on the page; not counted in the path totals. |
| [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | "Snapshot", "backup", "RPO", "RTO" or "patch cadence" are only words to you, you want to time a restore for yourself, or you want to know how to read a CVE entry and what a severity score leaves out. A foundations side page to [Droplet hardening](Droplet-Hardening.md), read after it and before [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md); no step is renumbered. About three hours with the free exercises (est.); the optional own-account path adds about an hour spread over a day or two (est.); not counted in the path totals. |
| [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) | You run or plan to run a LAMP or LEMP site or WordPress and want to know why plugins and the PHP runtime are the risk, how to harden PHP and WordPress, what a WAF can and cannot do, what memory safety means, and why a static site is often better. A foundations side page to [Droplet hardening](Droplet-Hardening.md); lesson 2 of the web-hosting track; about 3 hours with the exercises (est.); free, loopback only; not counted in the path totals. |
| [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) | "Single sign-on", "SAML", "OIDC", "identity provider" or "phishing-resistant MFA" are only words to you, or you want to read a real sign-in message. A foundations side page to [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), read after it and before [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md); no step is renumbered. About two hours with the free exercises (est.); the optional local path adds about an hour (est.); not counted in the path totals. |
| [Working in a company: tickets, change, on-call and documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md) | You are heading for a first job and "put it in the ticket", "that needs a change request", "you are on call" or "request access" are only words to you. A foundations side page, read after [Enterprise engineering habits](Enterprise-Engineering-Habits.md) (core step 9) and [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md); no step is renumbered. About two hours with the free local exercises (est.); the optional own-fork path adds about 45 minutes (est.), at $0; not counted in the path totals. |
| [Data formats and config files: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) | A workflow file, a `.tf` file or a `cost.json` looks like noise, or you want to know why YAML breaks on one space. A foundations side page to [What is infrastructure as code](What-Is-Infrastructure-as-Code.md); read it after that page and before [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) if those files are new. About 2.5 hours with the exercises (est.), all free and local; not counted in the path totals. |
| [Build and destroy a bunch: one stack per service](Build-and-Destroy-Stack-Per-Service.md) | You want to split an environment into one stack per service, wire the stacks together, and build and destroy a whole set without leaving a bill behind. The fourth lesson of the infrastructure-as-code track, after the OpenTofu, state and Spacelift lessons. A foundations side page to [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), read after it (and after the three earlier lessons of the track) when the words stack, state or destroy order are new; no step is renumbered. About 90 minutes of reading and the free lab (est.), all free and local; the optional own-account cloud path adds about an hour (est.); not counted in the path totals. |
| [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) | You can run `tofu plan` but reading one, the state file, drift, `moved` and `import` blocks or a lost state are still guesswork. A foundations side page to [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) (lesson 2 of the infrastructure-as-code track); read it after [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) and before that page; no step is renumbered. About 3 hours with the free local exercises (est.); not counted in the path totals. |
| [OpenTofu from zero: init, plan, apply, destroy](OpenTofu-From-Zero.md) | You want to type `tofu init`, `plan`, `apply` and `destroy` yourself, or the symbols `+`, `~` and `-/+`, the state file, `count`, `for_each`, modules or `tofu test` are only words to you. Lesson I1 of a four-lesson infrastructure-as-code track; a foundations side page read after [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) and before [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md); no step is renumbered. About three hours with the free exercises (est.), all local, with providers that cost nothing; not counted in the path totals. |
| [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) | A virtual machine, a container and a "managed service" blur together, or IaaS, PaaS, SaaS, hypervisor or availability zone are only words to you. A foundations side page to [Containers and Docker basics](Containers-and-Docker-Basics.md); read it after that page and [What is the cloud](What-Is-the-Cloud.md), before [How money works in the cloud](How-Money-Works-in-the-Cloud.md); no step is renumbered. About two hours with the free lab (est.); the optional own-account path adds about 45 minutes (est.); not counted in the path totals. |
| [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | "Log", "SIEM", "rule", "baseline" or "false positive" are only words to you, or you want to read an SSH log line and write a detection rule. A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), read after [Droplet hardening](Droplet-Hardening.md) (core step 14) and before [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md); no step is renumbered. About an hour and a half with the free exercises on invented logs (est.); the optional own-account path is costed on the [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) page; not counted in the path totals. |
| [Threats in plain words](Threats-in-Plain-Words.md) | The sentence "CVE-2018-13379" at core step 11 reads like noise, or vulnerability, exploit, zero-day, phishing, malware, ransomware, lateral movement, CVSS, KEV, SOC 2 or ISO 27001 are only words to you. A foundations side page to [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md); about 90 minutes, free. |
| [Security tools basics: Nmap, OpenVAS, Burp Suite, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) | Nmap, a vulnerability scanner, a proxy or an exploit framework are only names to you, and you want to know what each tells a defender about how to build systems. A foundations side page, read after [Threats in plain words](Threats-in-Plain-Words.md) and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md); isolated local lab only, never a network you do not own; no step is renumbered. About four hours with the free exercises (est.); the Greenbone and Metasploit parts are optional, heavier extras; not counted in the path totals. |
| [Red and blue as yin and yang, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) | You want to know what red, blue and purple teams are, what to have in writing before any test, how to think of one exploit as one box in a whole enterprise, or how to choose and safely isolate a lab OS (Kali or Parrot, in VirtualBox, KVM, WSL or Hyper-V). A foundations side page, read after [Threats in plain words](Threats-in-Plain-Words.md); no step is renumbered. About two and a half hours with the exercises (est.), all free and on your own computer; not counted in the path totals. |
| [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) | You want zero trust shown in a real home lab, and the contrast with a traditional VPN when the home connection fails over to cellular. A side page to [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md). About 45 minutes of reading and 60 minutes for the free exercises (est.); not counted in the path totals. |
| [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md) | You want to know where this project uses a Twingate service account, what a service key and a headless client are, and which Twingate plan each use needs. A foundations side page to [Twingate](Twingate.md); read it after that page. About 45 minutes with the free exercises (est.); not counted in the path totals. |
| [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) | You wonder why the droplets have public addresses and no NAT gateway. A side page to [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md); not counted in the path totals. |
| [How this project is planned](How-This-Project-Is-Planned.md) | You want to know how the work is organized: the board, sprints, sizes, definition of done. |
| [Screenshots policy](Screenshots-Policy.md) | You are adding a picture to a page, or want to know why a console is described but not shown. |
| [Home](Home.md) | You want the short version, the diagram and the current state. |

Operator guides that live in the repository rather than the wiki: [stage 0](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md), [stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md), the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) and the [cost guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

## Keeping this page honest

A test (`tests/test_wiki_navigation.py`) fails if a wiki page is in neither the sidebar nor this page, if the sidebar links to a page that does not exist, if a **Next** line names a page that does not exist, or if a page appears twice within one path above. When you add a wiki page, add it to a path here and to the sidebar in the same pull request.
