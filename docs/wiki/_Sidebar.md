**[Home](Home.md)** | **[Reading order](Reading-Order.md)** | **[Why this exists](Why-This-Exists.md)**

<details open>
<summary><b>Core path: read in this order</b></summary>

1. [Start here if you are new](Start-Here-If-You-Are-New.md)
2. [What is the cloud](What-Is-the-Cloud.md)
3. [Networking basics](Networking-Basics-for-This-Project.md)
    - Side page: [How a web request works](How-a-Web-Request-Works.md)
    - Foundations side page: [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)
4. [Identity, secrets, zero trust](Identity-Secrets-and-Zero-Trust-Basics.md)
    - Side page: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)
    - Side page: [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
    - Foundations side page: [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
5. [Infrastructure as code](What-Is-Infrastructure-as-Code.md)
    - Foundations side page: [Data formats and config files: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
    - Foundations side page: [Build and destroy a bunch: one stack per service](Build-and-Destroy-Stack-Per-Service.md)
6. [Git and pull requests](Git-GitHub-and-Pull-Requests.md)
    - Side page: [Git from zero: your first change](Git-From-Zero.md)
    - Foundations side page: [The terminal and your first script](Terminal-and-Your-First-Script.md)
7. [Containers and Docker (optional)](Containers-and-Docker-Basics.md)
    - Side page: [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md)
    - Foundations side page: [Windows, Active Directory and macOS in the enterprise](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)
    - Foundations side page: [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)
8. [How money works](How-Money-Works-in-the-Cloud.md)
9. [Enterprise habits](Enterprise-Engineering-Habits.md)
    - Foundations side page: [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md)
10. [Architecture overview](Architecture-Overview.md)
11. [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md)
    - Side page: [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md)
    - Foundations side page: [Threats in plain words](Threats-in-Plain-Words.md)
12. [Twingate](Twingate.md)
    - Side page: [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md)
13. [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md)
    - Side page: [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md)
14. [Droplet hardening](Droplet-Hardening.md)
    - Foundations side page: [Backups, recovery and patching](Backups-Recovery-and-Patching.md)
15. [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md)
16. [Spacelift](Spacelift.md)
17. [Doppler and secrets](Doppler-and-Secrets.md)
18. [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)
19. [Threat model](Threat-Model.md)
20. [Lessons learned](Lessons-Learned.md)
21. [Roadmap](Roadmap.md)

</details>

<details>
<summary><b>Track: build it yourself</b></summary>

- [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md)
- [Labs: break it on purpose](Labs-Break-It-on-Purpose.md)
- [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md)
- [Teardown checklist](Teardown-Checklist.md)
- [Settings reference](Settings-Reference.md)
- [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md)

</details>

<details>
<summary><b>Track: understand the design</b></summary>

- [Why I picked these tools](Why-I-Picked-These-Tools.md)
- [Terraform reference](Terraform-Reference.md)
- [From commit to pipeline](From-Commit-to-Pipeline.md)
- [Trace one change end to end](Trace-One-Change-End-to-End.md)

The rest of this track is on the core path; see [Reading order](Reading-Order.md#understand-the-design).

</details>

<details>
<summary><b>Track: security and threat modeling</b></summary>

- [Threat model exercise](Threat-Model-Exercise.md)
- [Threat Dragon exercise](Threat-Dragon-Exercise.md)
- [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)
- [Troubleshooting index](Troubleshooting-Index.md)

The [Threat model](Threat-Model.md) is core step 19.

</details>

<details>
<summary><b>Track: detection and monitoring</b></summary>

- [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md)
- [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)
    - Foundations side page: [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)
    - Side page: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md)
        - [What deception is](Deception-and-Honeypots-What-Deception-Is.md)
        - [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md)
        - [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md)
        - [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md)
        - [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md)
        - [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md)
        - [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md)
- [Cloud telemetry: what and why (unverified draft)](Cloud-Telemetry-What-and-Why.md)
- [Multiple sites and identity (unverified draft)](Multiple-Sites-and-Identity.md)
- [Telemetry crosses the trust boundary (unverified draft)](Telemetry-Crosses-the-Trust-Boundary.md)
- [Reading a dashboard as an operator (unverified draft)](Reading-a-Dashboard-as-an-Operator.md)
- [Build your own mini SOC (unverified draft)](Build-Your-Own-Mini-SOC.md)
- [Stage 2 home-side runbook (unverified draft)](Stage-2-Home-Side-Runbook.md)
- [Grafana dashboards (unverified draft)](Grafana-Dashboards.md)
- [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md)

</details>

<details>
<summary><b>Enterprise context</b></summary>

- [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md)
- [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md)
- [Enterprise change management for beginners (not used here)](Enterprise-Change-Management-for-Beginners.md)
- [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md)
- [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md)

</details>

<details>
<summary><b>Track: other clouds (unverified drafts)</b></summary>

- [Why the clouds differ](Why-the-Clouds-Differ.md)
- [AWS: account preparation](Provider-AWS-Account-Preparation.md)
- [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md)
- [AWS: where the money goes](Provider-AWS-Cost-Lesson.md)
- [Azure: account preparation](Provider-Azure-Account-Preparation.md)
- [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md)
- [Azure: where the money goes](Provider-Azure-Cost-Lesson.md)
- [GCP: account preparation](Provider-GCP-Account-Preparation.md)
- [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md)
- [GCP: where the money goes](Provider-GCP-Cost-Lesson.md)

</details>

<details>
<summary><b>Reference and operator guides</b></summary>

- [Glossary](Glossary.md)
- [Troubleshooting index](Troubleshooting-Index.md)
- [Settings reference](Settings-Reference.md)
- [Terraform reference](Terraform-Reference.md)
- [How this project is planned](How-This-Project-Is-Planned.md)
- [Screenshots policy](Screenshots-Policy.md)
- [Stage 0 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md)
- [Stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)
- [Secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md)
- [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)

</details>
