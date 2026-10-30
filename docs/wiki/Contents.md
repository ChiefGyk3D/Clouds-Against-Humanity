<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this
page by hand: add the page to the manifest and re-run the script. CI fails when this
page does not match the manifest. -->

# Contents

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Every page of this wiki appears here once (121 pages), grouped by theme, with a line on what it is for and who it is for. If you do not know where to begin, take the numbered core path; [Reading order](Reading-Order.md) has the same pages with time estimates and checkpoints, and [Start here if you are new](Start-Here-If-You-Are-New.md) is the gentlest first page.

Some pages carry a status marker, copied from the page's own banner:

- **draft**: the page calls itself an unverified draft.
- **est. steps**: the page was written from reading, and its steps were not run.
- **unbuilt**: the page describes something that is not built or not applied yet.

A page with no marker has no such banner. It may still say what was and was not run, so read its status note.

## Groups

- [Start here](#start-here) (5)
- [Core path: read in this order](#core-path-read-in-this-order) (21)
- [Foundations: OS and Linux](#foundations-os-and-linux) (7)
- [Foundations: networking](#foundations-networking) (5)
- [Foundations: identity and secrets](#foundations-identity-and-secrets) (5)
- [Foundations: infrastructure as code](#foundations-infrastructure-as-code) (6)
- [Foundations: web hosting](#foundations-web-hosting) (3)
- [Foundations: security tools and threat modeling](#foundations-security-tools-and-threat-modeling) (6)
- [Foundations: network and host defense](#foundations-network-and-host-defense) (5)
- [Foundations: deception and honeypots](#foundations-deception-and-honeypots) (11)
- [Detection and monitoring](#detection-and-monitoring) (11)
- [Foundations: enterprise practice](#foundations-enterprise-practice) (6)
- [Foundations: data governance](#foundations-data-governance) (1)
- [Stage guides and design](#stage-guides-and-design) (11)
- [Other clouds](#other-clouds) (10)
- [Reference](#reference) (8)
- [Project process](#project-process) (4)

## Start here

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Home](Home.md) | The front door: what the project is, which path fits you, and a short diagram of how it fits together. | everyone |  |
| [Contents](Contents.md) | Every wiki page once, grouped by theme, with what it is for and who it is for. | everyone |  |
| [Reading order](Reading-Order.md) | The core path and every other track as numbered tables with time estimates and checkpoints, for anyone choosing what to read next. | everyone |  |
| [Why this exists](Why-This-Exists.md) | The author's reasons for building open zero trust education, for anyone who wants to know where it comes from. | everyone |  |
| [Give feedback](Give-Feedback-and-Open-an-Issue.md) | How to report a mistake, an outdated claim or a command that failed, for any reader who spots one. | everyone |  |

## Core path: read in this order

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [Start here if you are new](Start-Here-If-You-Are-New.md) | Maps homelab ideas to cloud ideas and sets where zero is, for readers new to cloud, Terraform and zero trust. | newcomer |  |
| 2 | [What is the cloud](What-Is-the-Cloud.md) | What you rent in the cloud, why it has a public address and who is responsible for what, for newcomers. | newcomer |  |
| 3 | [Networking basics](Networking-Basics-for-This-Project.md) | Addresses, ports, firewalls and why a machine can have a public address and still be unreachable, for newcomers. | newcomer |  |
| 4 | [Identity, secrets, zero trust](Identity-Secrets-and-Zero-Trust-Basics.md) | What passwords, tokens and keys are, why they leak and the habits that stop it, for newcomers. | newcomer |  |
| 5 | [Infrastructure as code](What-Is-Infrastructure-as-Code.md) | Why infrastructure is written as code, with plan, apply, state and drift, for anyone who has rebuilt a machine by hand. | newcomer |  |
| 6 | [Git and pull requests](Git-GitHub-and-Pull-Requests.md) | How a change is proposed, checked by automated tests, reviewed and merged, for newcomers to git. | newcomer |  |
| 7 | [Containers and Docker (optional)](Containers-and-Docker-Basics.md) | The ideas under Docker and why moving Pi-style containers to the cloud exposes hidden assumptions; optional, for stage 3 readers. | newcomer |  |
| 8 | [How money works](How-Money-Works-in-the-Cloud.md) | What costs money, how bills get out of hand and how the cost gate prevents it, for anyone about to rent cloud resources. | newcomer |  |
| 9 | [Enterprise habits](Enterprise-Engineering-Habits.md) | Why a tiny lab does things the hard way and which habits to take home, for readers finishing the primers. | newcomer |  |
| 10 | [Architecture overview](Architecture-Overview.md) | The data plane and the control plane and which arrows carry secrets, for anyone starting the core path proper. | everyone |  |
| 11 | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) | Why this project has no VPN, bastion or open port, and where that reasoning stops holding, for anyone weighing the choice. | everyone |  |
| 12 | [Twingate](Twingate.md) | The connectors, resources and groups that are the only way into a droplet here, and why there are two connectors. | everyone |  |
| 13 | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) | Why a droplet's public address cannot be removed and how a tag-attached cloud firewall makes it silent from first boot. | everyone |  |
| 14 | [Droplet hardening](Droplet-Hardening.md) | What cloud-init does to a connector on first boot, before any human could log in, so the firewall is never the only control. | everyone |  |
| 15 | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) | Why every resource is declared in OpenTofu and why the code is split into layered stacks and modules. | everyone |  |
| 16 | [Spacelift](Spacelift.md) | Where plan and apply actually run, who approves them, and why nothing applies from a laptop or from GitHub Actions. | everyone |  |
| 17 | [Doppler and secrets](Doppler-and-Secrets.md) | Where every real value lives, how it reaches a run and how to rotate it, because nothing in the repository is a credential. | everyone |  |
| 18 | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | The checks every pull request runs, the single CI green gate that guards merging, and the cost gate that stops surprise bills. | everyone |  |
| 19 | [Threat model](Threat-Model.md) | The assets, adversaries, trust boundaries and deliberately accepted risks, sized to a one-operator lab. | everyone |  |
| 20 | [Lessons learned](Lessons-Learned.md) | What broke during the build, what was really going on and what fixed it, for anyone who wants to skip the lost evenings. | everyone |  |
| 21 | [Roadmap](Roadmap.md) | The stages from 0 onward, what is built and applied, what is built but unapplied and what is deliberately not planned. | everyone |  |

## Foundations: OS and Linux

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | Snapshot versus backup, RPO and RTO, the 3-2-1 rule and patch cadence, for beginners deciding what to protect and how. | learner |  |
| [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) | The order of a new machine's first hour: updates, automatic updates, a baseline, then everything else, for anyone setting up a system. | learner |  |
| [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) | The Linux families, package managers, services, permissions and logs you meet at work, for beginners; commands were not run by the author. | learner | est. steps |
| [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) | Red, blue and purple teams, the written permission you need before any test, and setting up a lab computer you can safely break. | learner |  |
| [The terminal and your first script](Terminal-and-Your-First-Script.md) | What a terminal, shell and command are, moving around files safely and chaining commands into a first script, for beginners on any operating system. | learner |  |
| [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) | What a virtual machine and a container each isolate, and who patches what under IaaS, PaaS and SaaS, for readers whose terms blur. | learner |  |
| [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) | Domains, Active Directory, Group Policy, Kerberos and managed Macs, for readers heading to help desk or systems administration. | learner |  |

## Foundations: networking

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [How a web request works](How-a-Web-Request-Works.md) | One HTTPS request from DNS to TLS to the page, and how to read a certificate, for readers after networking basics. | learner |  |
| [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) | Who owns what in DNS, the common record types, TTL and putting a site behind Cloudflare, for learners hosting their own website. | learner |  |
| [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | Working out subnets by hand, public versus private addresses, NAT and a default-deny firewall in a local lab, for learners after networking basics. | learner |  |
| [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) | Why a server behind a CDN sees the proxy's address, how the real client address is passed on, and the OSI layers, for people running sites behind one. | learner |  |
| [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md) | IPv6 addressing, why adoption is slow, why this project is IPv4-only and how to handle IPv6 safely in a lab. | learner |  |

## Foundations: identity and secrets

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) | What an API is, how to read a request, a response and JSON, and what a token is, for readers new to all three. | learner |  |
| [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) | Directories, identity providers, SSO, SAML, OAuth and OIDC in plain words, for readers heading into enterprise identity. | learner |  |
| [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | What encoding, hashing, encryption and signing each give you and what they do not, for readers who lump them together. | learner |  |
| [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) | Blast radius, assume breach and defense in depth as one mindset question to ask of any system. | learner |  |
| [Secrets from day one](Secrets-From-Day-One.md) | A password manager, Doppler for every asset and the .env rules, as personal habits for anyone about to start writing code. | learner |  |

## Foundations: infrastructure as code

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Git from zero](Git-From-Zero.md) | Make an account with a second factor, then clone, branch, commit, push and open your first pull request; for people who have never used git. | learner |  |
| [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) | How to recognize, read and write JSON, YAML and HCL and spot the classic mistakes, for readers before the code starts to look like noise. | learner |  |
| [OpenTofu from zero](OpenTofu-From-Zero.md) | Lesson 1 of the infrastructure as code track: init, plan, apply and destroy on your own machine, for first-time users. | learner |  |
| [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) | Reading a plan like a reviewer, what state is, how drift happens and how to recover, for learners after OpenTofu from zero. | learner |  |
| [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) | Why a bigger environment is split into one stack per service, with its costs and benefits, for learners finishing the infrastructure as code track. | learner |  |
| [Spacelift from zero](Spacelift-From-Zero.md) | What a hosted infrastructure runner adds to plan and apply, its plan limits and a first stack run and teardown, for learners. | learner |  |

## Foundations: web hosting

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) | What a web server, an application runtime and a database each do in a LAMP or LEMP stack, for readers who are new to web hosting. | learner |  |
| [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) | Why plugins carry most of a WordPress site's risk, what to harden and what a web application firewall does; also why static sites often win. | learner |  |
| [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) | The path from one web server to a scaled design, with caches, a CDN, a WAF and a pipeline, for engineers who run web fleets. | engineer |  |

## Foundations: security tools and threat modeling

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Threats in plain words](Threats-in-Plain-Words.md) | Vulnerabilities, exploits, phishing, malware and compliance told apart with real dated cases, for readers who meet these words as noise. | learner |  |
| [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) | The rules for using Nmap, OpenVAS, Wireshark, Burp, ZAP and Metasploit, and what each one is for, for learners in an isolated lab. | learner |  |
| [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md) | How a message travels, the DNS records and gateways that protect it and whether to run your own mail server, for learners. | learner |  |
| [Threat model exercise](Threat-Model-Exercise.md) | Build your own threat model of this repository before you open the worked one, for security-minded readers. | security reader |  |
| [Threat Dragon exercise](Threat-Dragon-Exercise.md) | Draw this pipeline's trust boundaries in OWASP Threat Dragon and attach threats to them, for security-minded readers. | security reader |  |
| [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) | The same pipeline viewed through STRIDE, MITRE ATT&CK and MITRE ATLAS, with files to open them, for security-minded readers. | security reader |  |

## Foundations: network and host defense

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) | Lesson D1: stateless versus stateful filtering, then iptables, nftables, UFW and BSD pf compared, for learners with a basic firewall idea. | learner |  |
| [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) | Lesson D2: what an IDS and an IPS are, where a sensor can watch and why an IPS is riskier, for learners. | learner |  |
| [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) | Lesson D3: file integrity monitoring, baselines and what to watch, with Tripwire, AIDE, Wazuh, auditd and fail2ban, for learners. | learner |  |
| [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) | Lesson D4: the main limiting algorithms, what to count by and what each layer can see, for learners who run a service. | learner |  |
| [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) | How to list every inbound port, address, account, token, dependency and person, how this project shrinks each, how to measure from outside, and what to log and alert on. | learner | draft |

## Foundations: deception and honeypots

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) | The hub for the deception track: what it covers, the three tracks of lessons and the safety rules that come first. | learner |  |
| [What deception is](Deception-and-Honeypots-What-Deception-Is.md) | Lessons 1 and 2: decoys, lures, honeytokens and honeypots, and low versus high interaction; reading and paper exercises only. | learner | est. steps |
| [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) | Lesson 6: the eight minimums for running a decoy that attracts real attackers; read it before any hands-on lesson. Not legal advice. | learner | est. steps |
| [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) | Lesson 3: build a local tripwire with a bait document, a link and a fake login and trip it yourself. | learner |  |
| [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) | Lesson 4: build a decoy file and a watcher that alerts when it is touched, on a host you own. | learner |  |
| [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) | Lesson 5: write detection logic over synthetic honeypot events and map it to ATT&CK, for learners wiring decoys into a SIEM. | learner |  |
| [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) | Lesson 10: design an isolated honeynet segment on paper and in a checker before installing anything, for home lab owners. | learner |  |
| [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) | Lesson 11: what the T-Pot honeypot bundle contains and how to keep it internal-only on your own hardware; nothing here was run. | learner | est. steps |
| [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) | Lesson 7: what a small internet-facing honeypot in your own cloud account needs to be safe; written from reading, nothing built. | learner | est. steps |
| [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) | Lesson 8: build, run and tear down a small Cowrie honeypot in your own cloud account for a fixed window; cloud steps were never run. | learner | est. steps |
| [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md) | Lesson 9: read Cowrie logs with jq or PowerShell, count what visitors tried and spot a visitor who touched your decoy. | learner |  |

## Detection and monitoring

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) | What this two-machine example leaves out and how a company would answer the same questions, for readers asking how it would be watched. | everyone |  |
| [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) | Detection after prevention fails, with Wazuh and the wider tool landscape; shipping logs is stage 2 and not built. | engineer | unbuilt |
| [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | What a log, a metric, a trace and an alert are, and how a log line becomes a rule, for learners new to detection. | learner |  |
| [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) | Logs, metrics and traces, and why telemetry crosses a trust boundary; an unverified draft for engineers planning stage 2. | engineer | draft |
| [Multiple sites and identity](Multiple-Sites-and-Identity.md) | What a site is, what breaks at two, and why a new site should be a settings file and not new code; an unverified draft for engineers. | engineer | draft |
| [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) | How telemetry moves between the cloud and the home SIEM without breaking the no-listener promise; an unverified draft for engineers. | engineer | draft |
| [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) | Ask what question each panel answers and what it would look like if the answer were bad; an unverified draft for operators. | operator | draft |
| [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) | A springboard for building a small cloud security monitoring stack with a cost ceiling you set; an unverified draft for builders. | builder | draft |
| [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) | What must exist at home before the cloud sends anything, for operators; the design is merged and nothing is applied. | operator | unbuilt |
| [Grafana dashboards](Grafana-Dashboards.md) | The three dashboards this repository ships and which question each answers; only tried with synthetic data. | operator |  |
| [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) | A hands-on synthetic multi-site monitoring stack where you predict what a silent site does, for builders. | builder |  |

## Foundations: enterprise practice

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) | How companies build campus, branch, data center and cloud networks compared with this one VPC, for engineers. | engineer |  |
| [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md) | How large organizations run infrastructure differently from this one-account project, for engineers. | engineer |  |
| [Enterprise change management (not used here)](Enterprise-Change-Management-for-Beginners.md) | Change tickets, CABs and freezes explained for readers who hear them at work; this project uses none of it. | learner |  |
| [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) | Where this project's Doppler and Twingate choices sit next to enterprise identity and secrets practice, for engineers. | engineer |  |
| [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md) | Write a ticket, a change request and a runbook for a real merged change, for learners preparing for company work. | learner |  |
| [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) | Roles that surround this work and what to learn next, for readers choosing a direction. | everyone |  |

## Foundations: data governance

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md) | Tenants, governance, retention, purge and DLP when data crosses an account boundary, for engineers. | engineer |  |

## Stage guides and design

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) | Make your own private copy, learn which settings are demo values and where the pipeline starts; step 1 of the build track. | builder |  |
| [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) | Five labs where you weaken a safety property on your computer and predict which check will object, for builders. | builder |  |
| [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) | The stage guides put in order, with accounts named early and a check at each step, ending in teardown; for learners replicating the build. | builder |  |
| [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) | Where each value belongs: a variable, a tfvars file, Doppler or the cost file, for builders. | builder |  |
| [Teardown checklist](Teardown-Checklist.md) | The order of destruction, what survives it and the checks that prove the bill is zero, for builders. | builder |  |
| [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md) | Where this project uses a Twingate service account and which plan each use needs; nothing was run against an account. | builder |  |
| [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) | A home lab with two outbound-only connectors that stays reachable when the internet fails over; nothing was tested for this page. | builder |  |
| [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) | The honest reason the connector droplets have public addresses and what going private would change; an unverified draft. | engineer | draft |
| [Why I picked these tools](Why-I-Picked-These-Tools.md) | Which tool choices are personal picks and where each would change at work, for engineers weighing alternatives. | engineer |  |
| [From commit to pipeline](From-Commit-to-Pipeline.md) | What CI, CD, DevOps and DevSecOps mean here and which gate stops what, for engineers. | engineer |  |
| [Trace one change end to end](Trace-One-Change-End-to-End.md) | One real pull request followed through every gate of the pipeline, for engineers. | engineer |  |

## Other clouds

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Why the clouds differ](Why-the-Clouds-Differ.md) | The three differences between AWS, Azure and GCP that change the bill and the design; an unverified draft. | engineer | draft |
| [AWS: account preparation](Provider-AWS-Account-Preparation.md) | Finish with an AWS account that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on AWS; an unverified draft. | builder | draft |
| [AWS: where the money goes](Provider-AWS-Cost-Lesson.md) | The AWS charges that surprise learners, the arithmetic, and how to prove the bill is back to zero; an unverified draft. | builder | draft |
| [Azure: account preparation](Provider-Azure-Account-Preparation.md) | Finish with an Azure subscription that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on Azure; an unverified draft. | builder | draft |
| [Azure: where the money goes](Provider-Azure-Cost-Lesson.md) | The Azure charges that surprise learners, the arithmetic, and how to prove the bill is back to zero; an unverified draft. | builder | draft |
| [GCP: account preparation](Provider-GCP-Account-Preparation.md) | Finish with a Google Cloud project that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on GCP; an unverified draft. | builder | draft |
| [GCP: where the money goes](Provider-GCP-Cost-Lesson.md) | Why GCP's no-public-address design can be cheaper, where that stops being true and how to prove the bill is back to zero; an unverified draft. | builder | draft |

## Reference

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Glossary](Glossary.md) | Every term the wiki uses in plain language with a pointer to the page that explains it, for all readers. | everyone |  |
| [Settings reference](Settings-Reference.md) | Every tunable setting, where it lives and what values it accepts; generated from docs/settings.json. | builder |  |
| [Terraform reference](Terraform-Reference.md) | Every variable, resource, data source, module call and output, file by file with the reason it exists, for engineers. | engineer |  |
| [Troubleshooting index](Troubleshooting-Index.md) | A lookup table from a symptom or error message to the page that has the fix, for anyone stuck. | everyone |  |
| [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) | The recorded prices and the monthly ceiling behind the cost gate; lives in the repository, not the wiki. | everyone |  |
| [Secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) | Where each secret is created and wired into Spacelift and Doppler; lives in the repository, not the wiki. | builder |  |
| [Stage 0 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md) | The author's operating record for stage 0 (project, network, firewall); lives in the repository, not the wiki. | builder |  |
| [Stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) | The author's operating record for stage 1 (Twingate access and two connectors); lives in the repository, not the wiki. | builder |  |

## Project process

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [How this project is planned](How-This-Project-Is-Planned.md) | The written backlog, sprints and definition of done this project uses, for readers curious how the work is run. | everyone |  |
| [Project status](Project-Status.md) | Open issues and pull requests by state, generated from GitHub; a reference page, not a lesson. | everyone |  |
| [Repository growth](Repository-Growth.md) | Stars, forks and weekly merged work drawn from GitHub data, with the as-of date printed. | everyone |  |
| [Screenshots policy](Screenshots-Policy.md) | What may be pictured in the wiki and how to review a picture before it leaks something, for contributors. | builder |  |
