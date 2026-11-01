<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this
file by hand: add the page to the manifest and re-run the script. CI fails when this
file does not match the manifest. -->

**[Home](Home.md)** | **[Contents](Contents.md)** | **[Reading order](Reading-Order.md)** | **[Why this exists](Why-This-Exists.md)** | **[Give feedback](Give-Feedback-and-Open-an-Issue.md)**

<details open><summary><b>Core path: read in this order</b> (21)</summary>

1. [Start here if you are new](Start-Here-If-You-Are-New.md)
2. [What is the cloud](What-Is-the-Cloud.md)
3. [Networking basics](Networking-Basics-for-This-Project.md)
4. [Identity, secrets, zero trust](Identity-Secrets-and-Zero-Trust-Basics.md)
5. [Infrastructure as code](What-Is-Infrastructure-as-Code.md)
6. [Git and pull requests](Git-GitHub-and-Pull-Requests.md)
7. [Containers and Docker (optional)](Containers-and-Docker-Basics.md)
8. [How money works](How-Money-Works-in-the-Cloud.md)
9. [Enterprise habits](Enterprise-Engineering-Habits.md)
10. [Architecture overview](Architecture-Overview.md)
11. [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md)
12. [Twingate](Twingate.md)
13. [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md)
14. [Droplet hardening](Droplet-Hardening.md)
15. [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md)
16. [Spacelift](Spacelift.md)
17. [Doppler and secrets](Doppler-and-Secrets.md)
18. [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)
19. [Threat model](Threat-Model.md)
20. [Lessons learned](Lessons-Learned.md)
21. [Roadmap](Roadmap.md)
- [Full list (21)](Contents.md#core-path-read-in-this-order)
</details>
<details><summary><b>Foundations: OS and Linux</b> (12)</summary>

- [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) (est. steps)
- [The terminal and your first script](Terminal-and-Your-First-Script.md)
- [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) (draft)
<details><summary>Recovery, patching, virtual machines and Windows (9)</summary>

- [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md) (draft) · [Backups, recovery and patching](Backups-Recovery-and-Patching.md) · [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md) (draft) · [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md)
- [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) · [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md) (draft) · [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md)
- [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) · [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)
</details>

- [Full list (12)](Contents.md#foundations-os-and-linux)
</details>
<details><summary><b>Foundations: networking</b> (5)</summary>

- [How a web request works](How-a-Web-Request-Works.md)
- [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)
- [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md)
- [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md)
- [Full list (5)](Contents.md#foundations-networking)
</details>
<details><summary><b>Foundations: identity and secrets</b> (9)</summary>

- [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)
- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [Secrets from day one](Secrets-From-Day-One.md)
<details><summary>Identity, risk and privacy (6)</summary>

- [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) (draft) · [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) · [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) · [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md) (draft)
- [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) (draft) · [US privacy law and the patchwork](US-Privacy-Law-No-General-Right-the-Patchwork-Data-Brokers-Social-Security-Numbers-and-License-Plate-Readers.md) (draft)
</details>

- [Full list (9)](Contents.md#foundations-identity-and-secrets)
</details>
<details><summary><b>Foundations: infrastructure as code</b> (7)</summary>

- [Git from zero](Git-From-Zero.md)
- [OpenTofu from zero](OpenTofu-From-Zero.md)
- [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md) (unbuilt)
- [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
- [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md)
- [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md)
- [Spacelift from zero](Spacelift-From-Zero.md)
- [Full list (7)](Contents.md#foundations-infrastructure-as-code)
</details>
<details><summary><b>Foundations: web hosting</b> (4)</summary>

- [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md)
- [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md)
- [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) (draft)
- [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md)
- [Full list (4)](Contents.md#foundations-web-hosting)
</details>
<details><summary><b>Foundations: security tools and threat modeling</b> (16)</summary>

<details><summary>Threats, privacy networks and cryptocurrency (16)</summary>

- [Threats in plain words](Threats-in-Plain-Words.md) · [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) · [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) · [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md) · [Threat model exercise](Threat-Model-Exercise.md)
- [Threat Dragon exercise](Threat-Dragon-Exercise.md) · [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) (draft) · [How a VPN works](How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md) (draft) · [How Tor works in depth](How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md) (draft) · [How I2P works](How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md) (draft)
- [Blockchain fundamentals](Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md) (draft) · [The darknet landscape: markets, OPSEC and layering](The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md) (draft) · [How Bitcoin works](How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md) (draft) · [How Monero works](How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md) (draft)
- [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) (draft) · [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md) (draft)
</details>

- [Full list (16)](Contents.md#foundations-security-tools-and-threat-modeling)
</details>
<details><summary><b>Foundations: network and host defense</b> (8)</summary>

- [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md)
- [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md)
- [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) (draft)
<details><summary>More defense lessons and checklists (5)</summary>

- [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) · [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) · [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) (draft) · [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) (draft)
- [DMZ hardening checklist](DMZ-Hardening-Checklist.md) (draft)
</details>

- [Full list (8)](Contents.md#foundations-network-and-host-defense)
</details>
<details><summary><b>Foundations: deception and honeypots</b> (11)</summary>

- [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md)
- [What deception is](Deception-and-Honeypots-What-Deception-Is.md) (est. steps)
- [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md)
<details><summary>Safety, hands-on and cloud honeypot lessons (8)</summary>

- [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (est. steps) · [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) · [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) · [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) · [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) (est. steps)
- [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) (est. steps) · [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) (est. steps) · [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md)
</details>

- [Full list (11)](Contents.md#foundations-deception-and-honeypots)
</details>
<details><summary><b>Detection and monitoring</b> (13)</summary>

- [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)
- [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) (draft)
- [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) (est. steps)
- [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md)
- [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) (unbuilt)
- [Wazuh SIEM and data pipelines](Wazuh-SIEM-and-Data-Pipelines.md) (est. steps)
<details><summary>Telemetry, sites and dashboards (7)</summary>

- [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) (draft) · [Multiple sites and identity](Multiple-Sites-and-Identity.md) (draft) · [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) (draft) · [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) (draft)
- [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) (unbuilt) · [Grafana dashboards](Grafana-Dashboards.md) · [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md)
</details>

- [Full list (13)](Contents.md#detection-and-monitoring)
</details>
<details><summary><b>Foundations: enterprise practice</b> (7)</summary>

- [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md)
- [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md)
- [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md)
- [Enterprise change management (not used here)](Enterprise-Change-Management-for-Beginners.md)
- [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md)
- [GRC in plain terms](GRC-Governance-Risk-and-Compliance-in-Plain-Terms-Laws-Frameworks-and-Attestations.md) (draft)
- [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md)
- [Full list (7)](Contents.md#foundations-enterprise-practice)
</details>
<details><summary><b>Foundations: data governance</b> (1)</summary>

- [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md)
- [Full list (1)](Contents.md#foundations-data-governance)
</details>
<details><summary><b>Stage guides and design</b> (11)</summary>

- [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md)
- [Labs: break it on purpose](Labs-Break-It-on-Purpose.md)
- [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md)
<details><summary>Build notes, design choices and the pipeline (8)</summary>

- [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) · [Teardown checklist](Teardown-Checklist.md) · [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md) · [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md)
- [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) (draft) · [Why I picked these tools](Why-I-Picked-These-Tools.md) · [From commit to pipeline](From-Commit-to-Pipeline.md) · [Trace one change end to end](Trace-One-Change-End-to-End.md)
</details>

- [Full list (11)](Contents.md#stage-guides-and-design)
</details>
<details><summary><b>Other clouds</b> (10)</summary>

- [Why the clouds differ](Why-the-Clouds-Differ.md) (draft)
- [AWS: account preparation](Provider-AWS-Account-Preparation.md) (draft)
- [Azure: account preparation](Provider-Azure-Account-Preparation.md) (draft)
- [GCP: account preparation](Provider-GCP-Account-Preparation.md) (draft)
<details><summary>The same four pieces and the cost lessons (6)</summary>

- [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md) (draft) · [AWS: where the money goes](Provider-AWS-Cost-Lesson.md) (draft) · [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) (draft) · [Azure: where the money goes](Provider-Azure-Cost-Lesson.md) (draft)
- [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) (draft) · [GCP: where the money goes](Provider-GCP-Cost-Lesson.md) (draft)
</details>

- [Full list (10)](Contents.md#other-clouds)
</details>
<details><summary><b>Reference</b> (8)</summary>

- [Glossary](Glossary.md)
- [Settings reference](Settings-Reference.md)
- [Troubleshooting index](Troubleshooting-Index.md)
- [Terraform reference](Terraform-Reference.md)
- [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)
- [Secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md)
- [Stage 0 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md)
- [Stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)
- [Full list (8)](Contents.md#reference)
</details>
<details><summary><b>Project process</b> (4)</summary>

- [Project status](Project-Status.md)
- [Repository growth](Repository-Growth.md)
- [Screenshots policy](Screenshots-Policy.md)
- [How this project is planned](How-This-Project-Is-Planned.md)
- [Full list (4)](Contents.md#project-process)
</details>
