<!-- GENERATED from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py. Do not edit this
file by hand: add the page to the manifest and re-run the script. CI fails when this
file does not match the manifest. -->

**[Home](Home.md)** | **[Contents](Contents.md)** | **[Reading order](Reading-Order.md)** | **[Why this exists](Why-This-Exists.md)** | **[Give feedback](Give-Feedback-and-Open-an-Issue.md)**

<details open>
<summary><b>Core path: read in this order</b> (21)</summary>

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

</details>

<details>
<summary><b>Foundations: OS and Linux</b> (8)</summary>

- [Backups, recovery and patching](Backups-Recovery-and-Patching.md)
- [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md)
- [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) (est. steps)
- [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md)
- [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md)
- [The terminal and your first script](Terminal-and-Your-First-Script.md)
- [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)
- [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)

</details>

<details>
<summary><b>Foundations: networking</b> (5)</summary>

- [How a web request works](How-a-Web-Request-Works.md)
- [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md)
- [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)
- [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md)
- [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)

</details>

<details>
<summary><b>Foundations: identity and secrets</b> (5)</summary>

- [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)
- [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md)
- [Secrets from day one](Secrets-From-Day-One.md)

</details>

<details>
<summary><b>Foundations: infrastructure as code</b> (7)</summary>

- [Git from zero](Git-From-Zero.md)
- [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
- [OpenTofu from zero](OpenTofu-From-Zero.md)
- [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md)
- [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md)
- [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md) (unbuilt)
- [Spacelift from zero](Spacelift-From-Zero.md)

</details>

<details>
<summary><b>Foundations: web hosting</b> (3)</summary>

- [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md)
- [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md)
- [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md)

</details>

<details>
<summary><b>Foundations: security tools and threat modeling</b> (6)</summary>

- [Threats in plain words](Threats-in-Plain-Words.md)
- [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md)
- [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md)
- [Threat model exercise](Threat-Model-Exercise.md)
- [Threat Dragon exercise](Threat-Dragon-Exercise.md)
- [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)

</details>

<details>
<summary><b>Foundations: network and host defense</b> (8)</summary>

- [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md)
- [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md)
- [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md)
- [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md)
- [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) (draft)
- [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) (draft)
- [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) (draft)
- [DMZ hardening checklist](DMZ-Hardening-Checklist.md) (draft)

</details>

<details>
<summary><b>Foundations: deception and honeypots</b> (11)</summary>

- [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md)
- [What deception is](Deception-and-Honeypots-What-Deception-Is.md) (est. steps)
- [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (est. steps)
- [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md)
- [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md)
- [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md)
- [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md)
- [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) (est. steps)
- [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) (est. steps)
- [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) (est. steps)
- [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md)

</details>

<details>
<summary><b>Detection and monitoring</b> (12)</summary>

- [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md)
- [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) (unbuilt)
- [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)
- [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) (draft)
- [Multiple sites and identity](Multiple-Sites-and-Identity.md) (draft)
- [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) (draft)
- [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) (draft)
- [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) (draft)
- [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) (unbuilt)
- [Grafana dashboards](Grafana-Dashboards.md)
- [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) (est. steps)
- [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md)

</details>

<details>
<summary><b>Foundations: enterprise practice</b> (6)</summary>

- [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md)
- [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md)
- [Enterprise change management (not used here)](Enterprise-Change-Management-for-Beginners.md)
- [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md)
- [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md)
- [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md)

</details>

<details>
<summary><b>Foundations: data governance</b> (1)</summary>

- [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md)

</details>

<details>
<summary><b>Stage guides and design</b> (11)</summary>

- [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md)
- [Labs: break it on purpose](Labs-Break-It-on-Purpose.md)
- [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md)
- [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md)
- [Teardown checklist](Teardown-Checklist.md)
- [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md)
- [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md)
- [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) (draft)
- [Why I picked these tools](Why-I-Picked-These-Tools.md)
- [From commit to pipeline](From-Commit-to-Pipeline.md)
- [Trace one change end to end](Trace-One-Change-End-to-End.md)

</details>

<details>
<summary><b>Other clouds</b> (10)</summary>

- [Why the clouds differ](Why-the-Clouds-Differ.md) (draft)
- [AWS: account preparation](Provider-AWS-Account-Preparation.md) (draft)
- [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md) (draft)
- [AWS: where the money goes](Provider-AWS-Cost-Lesson.md) (draft)
- [Azure: account preparation](Provider-Azure-Account-Preparation.md) (draft)
- [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) (draft)
- [Azure: where the money goes](Provider-Azure-Cost-Lesson.md) (draft)
- [GCP: account preparation](Provider-GCP-Account-Preparation.md) (draft)
- [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) (draft)
- [GCP: where the money goes](Provider-GCP-Cost-Lesson.md) (draft)

</details>

<details>
<summary><b>Reference</b> (8)</summary>

- [Glossary](Glossary.md)
- [Settings reference](Settings-Reference.md)
- [Terraform reference](Terraform-Reference.md)
- [Troubleshooting index](Troubleshooting-Index.md)
- [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)
- [Secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md)
- [Stage 0 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md)
- [Stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)

</details>

<details>
<summary><b>Project process</b> (4)</summary>

- [How this project is planned](How-This-Project-Is-Planned.md)
- [Project status](Project-Status.md)
- [Repository growth](Repository-Growth.md)
- [Screenshots policy](Screenshots-Policy.md)

</details>
