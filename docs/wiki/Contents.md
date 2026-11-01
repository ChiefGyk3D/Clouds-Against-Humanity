<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this
page by hand: add the page to the manifest and re-run the script. CI fails when this
page does not match the manifest. -->

# Contents

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Every page of this wiki appears here once (153 pages), grouped by theme, with a line on what it is for and who it is for. If you do not know where to begin, take the numbered core path; [Reading order](Reading-Order.md) has the same pages with time estimates and checkpoints, and [Start here if you are new](Start-Here-If-You-Are-New.md) is the gentlest first page.

Some pages carry a status marker, copied from the page's own banner:

- **draft**: the page calls itself an unverified draft.
- **est. steps**: the page was written from reading, and its steps were not run.
- **unbuilt**: the page describes something that is not built or not applied yet.

A page with no marker has no such banner. It may still say what was and was not run, so read its status note.

## Groups

- [Start here](#start-here) (5)
- [Core path: read in this order](#core-path-read-in-this-order) (21)
- [Track 1: Foundations](#track-1-foundations) (28)
- [Security tools and threat modeling](#security-tools-and-threat-modeling) (6)
- [Track 2: Defend and detect](#track-2-defend-and-detect) (33)
- [Track 3: Privacy, anonymity and cryptocurrency](#track-3-privacy-anonymity-and-cryptocurrency) (16)
- [Track 4: GRC and law](#track-4-grc-and-law) (9)
- [Track 5: Build and operate](#track-5-build-and-operate) (31)
- [Reference](#reference) (8)

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

## Track 1: Foundations

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [Git from zero](Git-From-Zero.md) | Make an account with a second factor, then clone, branch, commit, push and open your first pull request; for people who have never used git. | learner |  |
| 2 | [The terminal and your first script](Terminal-and-Your-First-Script.md) | What a terminal, shell and command are, moving around files safely and chaining commands into a first script, for beginners on any operating system. | learner |  |
| 3 | [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) | The Linux families, package managers, services, permissions and logs you meet at work, for beginners; commands were not run by the author. | learner | est. steps |
| 4 | [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) | The order of a new machine's first hour: updates, automatic updates, a baseline, then everything else, for anyone setting up a system. | learner |  |
| 5 | [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) | What unattended-upgrades does, how to configure it, where updates are logged, which four events deserve an alert, reboots, testing and rollback, for anyone running a Debian or Ubuntu host. | learner |  |
| 6 | [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) | Red, blue and purple teams, the written permission you need before any test, and setting up a lab computer you can safely break. | learner |  |
| 7 | [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) | What a virtual machine is, type 1 and type 2 hypervisors, the desktop and server options, a dated account of the VMware licensing changes, and a first VM with QEMU, for learners who need a lab. | learner | draft |
| 8 | [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) | What a virtual machine and a container each isolate, and who patches what under IaaS, PaaS and SaaS, for readers whose terms blur. | learner |  |
| 9 | [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) | Domains, Active Directory, Group Policy, Kerberos and managed Macs, for readers heading to help desk or systems administration. | learner |  |
| 10 | [How a web request works](How-a-Web-Request-Works.md) | One HTTPS request from DNS to TLS to the page, and how to read a certificate, for readers after networking basics. | learner |  |
| 11 | [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) | Who owns what in DNS, the common record types, TTL and putting a site behind Cloudflare, for learners hosting their own website. | learner |  |
| 12 | [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | Working out subnets by hand, public versus private addresses, NAT and a default-deny firewall in a local lab, for learners after networking basics. | learner |  |
| 13 | [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) | Why a server behind a CDN sees the proxy's address, how the real client address is passed on, and the OSI layers, for people running sites behind one. | learner |  |
| 14 | [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md) | IPv6 addressing, why adoption is slow, why this project is IPv4-only and how to handle IPv6 safely in a lab. | learner |  |
| 15 | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) | What an API is, how to read a request, a response and JSON, and what a token is, for readers new to all three. | learner |  |
| 16 | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | What encoding, hashing, encryption and signing each give you and what they do not, for readers who lump them together. | learner |  |
| 17 | [Secrets from day one](Secrets-From-Day-One.md) | A password manager, Doppler for every asset and the .env rules, as personal habits for anyone about to start writing code. | learner |  |
| 18 | [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) | Directories, identity providers, SSO, SAML, OAuth and OIDC in plain words, for readers heading into enterprise identity. | learner |  |
| 19 | [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) | How to recognize, read and write JSON, YAML and HCL and spot the classic mistakes, for readers before the code starts to look like noise. | learner |  |
| 20 | [OpenTofu from zero](OpenTofu-From-Zero.md) | Lesson 1 of the infrastructure as code track: init, plan, apply and destroy on your own machine, for first-time users. | learner |  |
| 21 | [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) | Reading a plan like a reviewer, what state is, how drift happens and how to recover, for learners after OpenTofu from zero. | learner |  |
| 22 | [Spacelift from zero](Spacelift-From-Zero.md) | What a hosted infrastructure runner adds to plan and apply, its plan limits and a first stack run and teardown, for learners. | learner |  |
| 23 | [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) | Why a bigger environment is split into one stack per service, with its costs and benefits, for learners finishing the infrastructure as code track. | learner |  |
| 24 | [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md) | What local dev, staging and production are for, why each gets its own stack, secrets and cost ceiling, and how a change is promoted; staging is planned and not built. | engineer | unbuilt |
| 25 | [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) | What a web server, an application runtime and a database each do in a LAMP or LEMP stack, for readers who are new to web hosting. | learner |  |
| 26 | [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) | Why plugins carry most of a WordPress site's risk, what to harden and what a web application firewall does; also why static sites often win. | learner |  |
| 27 | [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) | A static and a dynamic site that look the same, how to tell them apart from outside with curl, page source and WhatWeb, what each leaks, and a career note on public work. | learner | draft |
| 28 | [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) | The path from one web server to a scaled design, with caches, a CDN, a WAF and a pipeline, for engineers who run web fleets. | engineer |  |

## Security tools and threat modeling

| Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- |
| [Threats in plain words](Threats-in-Plain-Words.md) | Vulnerabilities, exploits, phishing, malware and compliance told apart with real dated cases, for readers who meet these words as noise. | learner |  |
| [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) | The rules for using Nmap, OpenVAS, Wireshark, Burp, ZAP and Metasploit, and what each one is for, for learners in an isolated lab. | learner |  |
| [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md) | How a message travels, the DNS records and gateways that protect it and whether to run your own mail server, for learners. | learner |  |
| [Threat model exercise](Threat-Model-Exercise.md) | Build your own threat model of this repository before you open the worked one, for security-minded readers. | security reader |  |
| [Threat Dragon exercise](Threat-Dragon-Exercise.md) | Draw this pipeline's trust boundaries in OWASP Threat Dragon and attach threats to them, for security-minded readers. | security reader |  |
| [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) | The same pipeline viewed through STRIDE, MITRE ATT&CK and MITRE ATLAS, with files to open them, for security-minded readers. | security reader |  |

## Track 2: Defend and detect

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) | Lesson D1: stateless versus stateful filtering, then iptables, nftables, UFW and BSD pf compared, for learners with a basic firewall idea. | learner |  |
| 2 | [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) | Lesson D2: what an IDS and an IPS are, where a sensor can watch and why an IPS is riskier, for learners. | learner |  |
| 3 | [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) | Lesson D3: file integrity monitoring, baselines and what to watch, with Tripwire, AIDE, Wazuh, auditd and fail2ban, for learners. | learner |  |
| 4 | [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) | Lesson D4: the main limiting algorithms, what to count by and what each layer can see, for learners who run a service. | learner |  |
| 5 | [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) | Blast radius, assume breach and defense in depth as one mindset question to ask of any system. | learner |  |
| 6 | [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) | How to list every inbound port, address, account, token, dependency and person, how this project shrinks each, how to measure from outside, and what to log and alert on. | learner | draft |
| 7 | [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) | The cloud account, Spacelift and CI, Doppler, Twingate, droplets, telemetry, edge and web tier: what to aim at, the control, the test, and what to log. | learner | draft |
| 8 | [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) | What a DMZ is, what may talk to what in this project's unbuilt edge design, how to harden a public host, and what to log and alert on. | learner | draft |
| 9 | [DMZ hardening checklist](DMZ-Hardening-Checklist.md) | A one-page printable checklist for hardening an internet-facing host, each line naming the repository check that covers it, plus what to log and what should alert. | learner | draft |
| 10 | [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) | The hub for the deception track: what it covers, the three tracks of lessons and the safety rules that come first. | learner |  |
| 11 | [What deception is](Deception-and-Honeypots-What-Deception-Is.md) | Lessons 1 and 2: decoys, lures, honeytokens and honeypots, and low versus high interaction; reading and paper exercises only. | learner | est. steps |
| 12 | [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) | Lesson 6: the eight minimums for running a decoy that attracts real attackers; read it before any hands-on lesson. Not legal advice. | learner | est. steps |
| 13 | [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) | Lesson 3: build a local tripwire with a bait document, a link and a fake login and trip it yourself. | learner |  |
| 14 | [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) | Lesson 4: build a decoy file and a watcher that alerts when it is touched, on a host you own. | learner |  |
| 15 | [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) | Lesson 5: write detection logic over synthetic honeypot events and map it to ATT&CK, for learners wiring decoys into a SIEM. | learner |  |
| 16 | [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) | Lesson 10: design an isolated honeynet segment on paper and in a checker before installing anything, for home lab owners. | learner |  |
| 17 | [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) | Lesson 11: what the T-Pot honeypot bundle contains and how to keep it internal-only on your own hardware; nothing here was run. | learner | est. steps |
| 18 | [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) | Lesson 7: what a small internet-facing honeypot in your own cloud account needs to be safe; written from reading, nothing built. | learner | est. steps |
| 19 | [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) | Lesson 8: build, run and tear down a small Cowrie honeypot in your own cloud account for a fixed window; cloud steps were never run. | learner | est. steps |
| 20 | [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md) | Lesson 9: read Cowrie logs with jq or PowerShell, count what visitors tried and spot a visitor who touched your decoy. | learner |  |
| 21 | [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) | What this two-machine example leaves out and how a company would answer the same questions, for readers asking how it would be watched. | everyone |  |
| 22 | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | What a log, a metric, a trace and an alert are, and how a log line becomes a rule, for learners new to detection. | learner |  |
| 23 | [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) | Detection after prevention fails, with Wazuh and the wider tool landscape; shipping logs is stage 2 and not built. | engineer | unbuilt |
| 24 | [Wazuh SIEM and data pipelines](Wazuh-SIEM-and-Data-Pipelines.md) | What the Wazuh agent, server, indexer and dashboard each do and how a log line becomes an alert, with a free toy pipeline; the Wazuh parts were written from reading. | learner | est. steps |
| 25 | [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) | Logs, metrics and traces, and why telemetry crosses a trust boundary; an unverified draft for engineers planning stage 2. | engineer | draft |
| 26 | [Multiple sites and identity](Multiple-Sites-and-Identity.md) | What a site is, what breaks at two, and why a new site should be a settings file and not new code; an unverified draft for engineers. | engineer | draft |
| 27 | [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) | How telemetry moves between the cloud and the home SIEM without breaking the no-listener promise; an unverified draft for engineers. | engineer | draft |
| 28 | [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) | Ask what question each panel answers and what it would look like if the answer were bad; an unverified draft for operators. | operator | draft |
| 29 | [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) | What a data source is, connecting Grafana to Prometheus, SQL and OpenSearch with a read-only account, then one panel and one alert; written from reading, not run. | builder | est. steps |
| 30 | [Grafana dashboards](Grafana-Dashboards.md) | The three dashboards this repository ships and which question each answers; only tried with synthetic data. | operator |  |
| 31 | [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) | A hands-on synthetic multi-site monitoring stack where you predict what a silent site does, for builders. | builder |  |
| 32 | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) | A springboard for building a small cloud security monitoring stack with a cost ceiling you set; an unverified draft for builders. | builder | draft |
| 33 | [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) | What must exist at home before the cloud sends anything, for operators; the design is merged and nothing is applied. | operator | unbuilt |

## Track 3: Privacy, anonymity and cryptocurrency

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) | Symmetric and asymmetric keys together, MACs, signatures, PKI, at rest versus in transit, key custody, NIST defaults and post-quantum planning, with a free drill. | learner | draft |
| 2 | [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) | Who can see in, who can get in, who can tell it is you: the data you hand out, correlation, a matrix of six tools, the same behavior over a different pipe, and three imaginary people, with six diagrams. | learner | draft |
| 3 | [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md) | Privacy as blinds and security as locks, Monero as a worked example, privacy law basics, physical security and why lockpicking is a hobby, with a free audit of your desk. | learner | draft |
| 4 | [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) | How Tor and I2P work, who uses them, Tor Browser, Tails, Whonix and Qubes compared, and a Monero node as the privacy-versus-security example. | learner | draft |
| 5 | [How a VPN works](How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md) | A packet with and without a VPN, WireGuard, OpenVPN and IPsec in plain terms, what a VPN moves and does not hide, DNS and IPv6 leaks, what no-logs claims and audits prove, with seven diagrams and two free exercises. | learner | draft |
| 6 | [How Tor works in depth](How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md) | Circuits, the three hops, guards, directory authorities and the consensus, bridges, onion services and the dated weaknesses, with six diagrams, for readers who want the machinery under Tor. | learner | draft |
| 7 | [How I2P works](How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md) | One-way tunnels, garlic routing and cloves, the network database and floodfills, reseeding, outproxies, the research on its weak points and an honest comparison with Tor. | learner | draft |
| 8 | [The browsing setups compared](The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix.md) | Tor Browser, Brave's Tor window, Whonix, Tails and Qubes with Whonix: trust boundaries, threat models, a matrix of nine threats, Kali and ParrotOS, and the maintainer's view, with six diagrams. | learner | draft |
| 9 | [The darknet landscape: markets, OPSEC and layering](The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md) | Documented darknet market history and why most fail, the OPSEC trap, clearnet versus onion services, and layering Tor, I2P and a VPN, for learners; educational and defensive only. | learner | draft |
| 10 | [Blockchain fundamentals](Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md) | Page 1 of 5 on cryptocurrency: hashes, blocks, nodes, a transaction's life, proof of work and stake, forks, full nodes and what a blockchain is not, with a dated read of the first two Bitcoin blocks. | learner | draft |
| 11 | [How Bitcoin works](How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md) | Page 2 of 5 on cryptocurrency: keys, UTXOs and change, fees, mining and confirmations, and why Bitcoin is pseudonymous and traceable, with documented tracing cases and a clustering exercise. | learner | draft |
| 12 | [How Monero works](How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md) | Page 3 of 5 on cryptocurrency: Monero's ring signatures, stealth addresses and hidden amounts, Ethereum, DeFi, mixers, Bitcoin-Monero atomic swaps and ransomware, with dated public cases. | learner | draft |
| 13 | [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) | Page 4 of 5 on cryptocurrency: hot and cold wallets, the threat model, hardware wallets and a disclosed Trezor affiliate link, recovery phrases, Shamir, multisig, custody, and a no-funds exercise. | learner | draft |
| 14 | [Paper wallets and offline key generation](Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero.md) | An addition to the cryptocurrency set: what a paper wallet is, why the advice changed, how to judge a generator, offline generation with Tails, Electrum and Monero, and a checklist exercise. | learner | draft |
| 15 | [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md) | Page 5 of 5 on cryptocurrency: a hardware wallet with Monero, the Qubes and Whonix offline-wallet design, PiNodeXMR as an always-on node and how to secure it, with a paper exercise. | learner | draft |
| 16 | [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md) | What still works when the internet and power are down: LoRa mesh, amateur radio, GMRS, FRS and CB, a legal-first SIGINT overview, and what a radio fallback could do for this project. | learner | draft |

## Track 4: GRC and law

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) | Confidentiality, integrity and availability in plain words, how real failures map to each, and this project's controls checked against all three. | learner | draft |
| 2 | [GRC in plain terms](GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations.md) | Page 1 of 3 on GRC: the governance, risk and compliance loop, laws versus frameworks versus attestations, SOX, PCI DSS, HIPAA, GLBA and FISMA in brief, roles, evidence, and a CM-3 exercise. | learner | draft |
| 3 | [US privacy law and the patchwork](US-Privacy-Law-No-General-Right-the-Patchwork-Data-Brokers-Social-Security-Numbers-and-License-Plate-Readers.md) | Page 2 of 3 on GRC: what the Constitution says about privacy, the federal and state patchwork, data brokers, Social Security numbers and license plate readers, with dated sources and a labeled opinion section. | learner | draft |
| 4 | [Privacy law around the world](Privacy-Law-Around-the-World-GDPR-PIPEDA-POPIA-and-PIPL-Compared-With-the-United-States.md) | Page 3 of 3 on GRC: the GDPR, PIPEDA, POPIA and the PIPL compared with the United States, with breach clocks, transfers, dated cases and a four-region exercise. | learner | draft |
| 5 | [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md) | Tenants, governance, retention, purge and DLP when data crosses an account boundary, for engineers. | engineer |  |
| 6 | [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md) | BCP versus DR, business impact analysis, RTO and RPO per system, recovery strategies, runbooks, tabletop exercises, postmortems and a worked plan for this project, for learners planning for the day something big breaks. | learner | draft |
| 7 | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | Snapshot versus backup, RPO and RTO, the 3-2-1 rule and patch cadence, for beginners deciding what to protect and how. | learner |  |
| 8 | [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md) | 3-2-1-1-0, immutable and offline copies, backup key custody, restore testing and what this project would have to back up, with a free restore drill. | learner | draft |
| 9 | [RAID: continuity, not a backup](RAID-Levels-Parity-Rebuilds-and-Why-RAID-Is-Continuity-Not-a-Backup.md) | RAID as a business continuity control and not a backup: levels, parity, the write penalty, rebuilds, the write hole and a computed six-drive exercise, with a free parity drill. | learner | draft |

## Track 5: Build and operate

| Step | Page | What it is for and who it is for | Audience | Status |
| --- | --- | --- | --- | --- |
| 1 | [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) | Make your own private copy, learn which settings are demo values and where the pipeline starts; step 1 of the build track. | builder |  |
| 2 | [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) | Five labs where you weaken a safety property on your computer and predict which check will object, for builders. | builder |  |
| 3 | [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) | The stage guides put in order, with accounts named early and a check at each step, ending in teardown; for learners replicating the build. | builder |  |
| 4 | [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) | Where each value belongs: a variable, a tfvars file, Doppler or the cost file, for builders. | builder |  |
| 5 | [Teardown checklist](Teardown-Checklist.md) | The order of destruction, what survives it and the checks that prove the bill is zero, for builders. | builder |  |
| 6 | [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md) | Where this project uses a Twingate service account and which plan each use needs; nothing was run against an account. | builder |  |
| 7 | [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) | A home lab with two outbound-only connectors that stays reachable when the internet fails over; nothing was tested for this page. | builder |  |
| 8 | [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) | The honest reason the connector droplets have public addresses and what going private would change; an unverified draft. | engineer | draft |
| 9 | [Why I picked these tools](Why-I-Picked-These-Tools.md) | Which tool choices are personal picks and where each would change at work, for engineers weighing alternatives. | engineer |  |
| 10 | [From commit to pipeline](From-Commit-to-Pipeline.md) | What CI, CD, DevOps and DevSecOps mean here and which gate stops what, for engineers. | engineer |  |
| 11 | [Trace one change end to end](Trace-One-Change-End-to-End.md) | One real pull request followed through every gate of the pipeline, for engineers. | engineer |  |
| 12 | [Why the clouds differ](Why-the-Clouds-Differ.md) | The three differences between AWS, Azure and GCP that change the bill and the design; an unverified draft. | engineer | draft |
| 13 | [AWS: account preparation](Provider-AWS-Account-Preparation.md) | Finish with an AWS account that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| 14 | [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on AWS; an unverified draft. | builder | draft |
| 15 | [AWS: where the money goes](Provider-AWS-Cost-Lesson.md) | The AWS charges that surprise learners, the arithmetic, and how to prove the bill is back to zero; an unverified draft. | builder | draft |
| 16 | [Azure: account preparation](Provider-Azure-Account-Preparation.md) | Finish with an Azure subscription that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| 17 | [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on Azure; an unverified draft. | builder | draft |
| 18 | [Azure: where the money goes](Provider-Azure-Cost-Lesson.md) | The Azure charges that surprise learners, the arithmetic, and how to prove the bill is back to zero; an unverified draft. | builder | draft |
| 19 | [GCP: account preparation](Provider-GCP-Account-Preparation.md) | Finish with a Google Cloud project that is protected, empty and watched, before any infrastructure; an unverified draft. | builder | draft |
| 20 | [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) | The network, firewall, machine and machine identity built on GCP; an unverified draft. | builder | draft |
| 21 | [GCP: where the money goes](Provider-GCP-Cost-Lesson.md) | Why GCP's no-public-address design can be cheaper, where that stops being true and how to prove the bill is back to zero; an unverified draft. | builder | draft |
| 22 | [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) | How companies build campus, branch, data center and cloud networks compared with this one VPC, for engineers. | engineer |  |
| 23 | [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md) | How large organizations run infrastructure differently from this one-account project, for engineers. | engineer |  |
| 24 | [Enterprise change management (not used here)](Enterprise-Change-Management-for-Beginners.md) | Change tickets, CABs and freezes explained for readers who hear them at work; this project uses none of it. | learner |  |
| 25 | [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) | Where this project's Doppler and Twingate choices sit next to enterprise identity and secrets practice, for engineers. | engineer |  |
| 26 | [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md) | Write a ticket, a change request and a runbook for a real merged change, for learners preparing for company work. | learner |  |
| 27 | [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) | Roles that surround this work and what to learn next, for readers choosing a direction. | everyone |  |
| 28 | [How this project is planned](How-This-Project-Is-Planned.md) | The written backlog, sprints and definition of done this project uses, for readers curious how the work is run. | everyone |  |
| 29 | [Project status](Project-Status.md) | Open issues and pull requests by state, generated from GitHub; a reference page, not a lesson. | everyone |  |
| 30 | [Repository growth](Repository-Growth.md) | Stars, forks and weekly merged work drawn from GitHub data, with the as-of date printed. | everyone |  |
| 31 | [Screenshots policy](Screenshots-Policy.md) | What may be pictured in the wiki and how to review a picture before it leaks something, for contributors. | builder |  |

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
