# Careers, roles and what to learn next

> **Orientation, not a design guide: verified claims dated.** Nothing on this page was checked against an employer, a certification body or a salary survey; job titles, duties and certification names are general industry knowledge unless the claims register says otherwise. Titles mean different things at different companies. Treat this as a map to ask questions with, not a promise about any job.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Start here if you are new](Start-Here-If-You-Are-New.md) and at least the first half of the [core path](Reading-Order.md#the-core-path). The companion pages [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md), [Enterprise infrastructure](Enterprise-Infrastructure-Differences.md) and [Enterprise identity and secrets](Enterprise-Identity-and-Secrets-at-Scale.md) give the vocabulary used below.

The maintainer's reason for this group of pages is simple: the field this repository lives in is wide, the small example shows one slice of it, and it is a good thing to learn for a career. This page lists the roles around the work, what each does on an ordinary day, and which pages here build which skills. It endorses no certification and no employer.

## Contrast at a glance

| Topic | In this project | In a company |
|---|---|---|
| Who does the work | One person wearing every hat | Many roles, each owning part of what one person does here |
| What "done" means | It applies, the checks pass, the bill is under the cap | A ticket is closed, a service-level target is met, an auditor is satisfied |
| Who you ask | Documentation and your own notes | A named colleague, a team channel, an on-call engineer |
| What you are measured on | Whether you learned it | Reliability, risk reduced, time saved, cost controlled, tickets closed |

## The roles around this work

Duties overlap and the names shift. Read each as a **cluster of tasks**, not a job title you must match.

| Role | A day, roughly | Skills it leans on | Pages here that build them |
|---|---|---|---|
| **Help desk / IT support** | Resets passwords, fixes sign-in and device problems, triages, escalates, writes down what fixed it | Troubleshooting, identity basics, patience, clear writing | [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), [Troubleshooting index](Troubleshooting-Index.md) |
| **Systems administrator** | Builds, patches and monitors servers and services, manages accounts and backups | Linux or Windows, scripting, patching, backup and restore | [Droplet hardening](Droplet-Hardening.md), [Containers and Docker basics](Containers-and-Docker-Basics.md) |
| **Network engineer** | Designs and runs switches, routers, firewalls, wireless and links between sites | Addressing, routing, segmentation, firewalls, DNS and DHCP | [Networking basics](Networking-Basics-for-This-Project.md), [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md), [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) |
| **Cloud engineer** | Builds and runs workloads and networks in a cloud, controls cost, applies guardrails | One cloud deeply, IaC, IAM, cost control | [What is the cloud](What-Is-the-Cloud.md), [Why the clouds differ](Why-the-Clouds-Differ.md), [Enterprise infrastructure](Enterprise-Infrastructure-Differences.md) |
| **DevOps / platform / SRE** | Builds the pipeline and platform other engineers use; keeps services reliable; handles on-call and post-incident reviews | IaC, CI/CD, observability, automation, reliability thinking | [What is infrastructure as code](What-Is-Infrastructure-as-Code.md), [OpenTofu](OpenTofu-Stacks-and-Modules.md), [Spacelift](Spacelift.md), [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) |
| **Security engineer** | Designs and builds controls: identity, network, secrets, hardening; reviews designs; fixes findings | Threat modeling, least privilege, secrets, cloud security | [Threat model](Threat-Model.md), [Doppler and secrets](Doppler-and-Secrets.md), [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md), [Enterprise identity and secrets](Enterprise-Identity-and-Secrets-at-Scale.md) |
| **Security analyst / SOC** | Watches alerts, triages, investigates, escalates, writes up incidents | Logs, detection logic, attack techniques, calm under pressure | [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) |
| **Detection engineer** | Writes and tunes the rules and queries that turn telemetry into alerts; measures false positives | Log formats, query languages, adversary behavior, testing | [Cloud telemetry](Cloud-Telemetry-What-and-Why.md), [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) |
| **GRC / auditor** | Maps controls to standards and laws, gathers evidence, runs risk registers and access reviews | Frameworks, policy writing, evidence, asking good questions | [Enterprise engineering habits](Enterprise-Engineering-Habits.md), [Threat model](Threat-Model.md), [Enterprise identity and secrets](Enterprise-Identity-and-Secrets-at-Scale.md) |
| **Architect** | Decides how the pieces fit across teams and years; weighs cost, risk, constraints and people; writes the decision down | Breadth, trade-offs, communication | [Architecture overview](Architecture-Overview.md), [Small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md), [Enterprise infrastructure](Enterprise-Infrastructure-Differences.md) |

Two honest notes. First, people move between these clusters, and many start in support or administration. Second, the roles that sound narrow (detection engineer, for example) usually need a broad base underneath: networking, operating systems and how services fail.

## A skills ladder

A ladder is a sequence of things you can **do**, each resting on the one below. The rungs are not job levels.

1. **Use it.** Explain, in your own words, what an address, a port, a firewall, a secret and a pull request are. Read the first six core path pages.
2. **Read it.** Open any file in `stacks/` and say what it creates; read a plan and say what will change. See [Terraform reference](Terraform-Reference.md) and [Trace one change end to end](Trace-One-Change-End-to-End.md).
3. **Run it.** Build your own copy and operate it: the build track and the [labs](Labs-Break-It-on-Purpose.md), where you predict which check will object.
4. **Break it, then fix it.** Fault-find from symptoms; use the [Troubleshooting index](Troubleshooting-Index.md) and the [Lessons learned](Lessons-Learned.md).
5. **Defend it.** Write a threat model before you read the worked one ([Threat model exercise](Threat-Model-Exercise.md)), and argue for what you accept.
6. **Watch it.** Collect logs, build a dashboard, write one detection ([Build your own mini SOC](Build-Your-Own-Mini-SOC.md)).
7. **Scale it on paper.** Redesign the project for ten teams and three environments, using the enterprise pages as the checklist. Notice which of your answers are products and which are habits.
8. **Teach it.** Explain one page to someone who has not read it. The gaps you find are the next thing to learn.

## Certifications as signposts

Certifications are one way an employer or hiring manager gets a quick signal and one way you get a structured syllabus. They are not a substitute for having built something, and they differ greatly in cost, rigour and how much employers value them locally. This page does not endorse any of them, and nothing here has been checked against the current exam objectives. The categories below are general knowledge, offered so the names are familiar:

| Area | Examples people commonly mention | Notes |
|---|---|---|
| General IT and networking foundations | CompTIA A+, Network+, Security+; Cisco CCNA | Vendor-neutral and vendor-specific options exist; check current objectives |
| Cloud fundamentals and associate level | Entry and associate certifications offered by AWS, Microsoft (Azure) and Google Cloud | Each covers its own cloud; this wiki's cloud pages are a starting comparison |
| Infrastructure as code and containers | HashiCorp Terraform Associate; Kubernetes certifications from the CNCF | Terraform's and OpenTofu's languages are close but not identical; check the exam |
| Security | CISSP, GIAC certifications, CompTIA Security+ and others | Several have experience requirements; some are management-oriented |
| Audit and governance | ISACA's CISA and CISM | Aimed at audit, risk and governance roles |

Ask people in the role you want which ones they actually saw matter, and look at job postings in your area for a month before you pay for anything. Some of these credentials expire and need renewal fees or continuing education; check the issuer.

## Keep tinkering: home-lab ideas that extend this repository

Each idea names the wiki pages it builds on. Do them in your own accounts and keep the cost gate in mind.

1. **Build the second site.** Add a second region or provider with the same modules and watch what the cost gate says ([Multiple sites and identity](Multiple-Sites-and-Identity.md), [Why the clouds differ](Why-the-Clouds-Differ.md)).
2. **Add a hub.** Sketch, and if you can afford it build, a transit pattern between two small networks, with non-overlapping address ranges ([Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md)).
3. **Break the flat network.** Put a pretend "internal" machine and a pretend "public" machine in separate segments and prove with a test that the public one cannot reach the other.
4. **Replace a stored token with OIDC.** Pick one long-lived token and find out whether the platform can issue a short-lived credential instead ([Enterprise identity and secrets](Enterprise-Identity-and-Secrets-at-Scale.md)).
5. **Write a policy as code.** Write a plan check that rejects a rule opening a port to the world, and a test that it fires ([CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)).
6. **Run the watcher.** Stand up the mini SOC at home and write one detection per accepted risk in the threat model ([Build your own mini SOC](Build-Your-Own-Mini-SOC.md)).
7. **Practice a restore.** Back something up, destroy it, restore it, and time the whole thing. That number is your real recovery time.
8. **Run an access review.** List every identity and token in the project, its owner and expiry, and remove one.
9. **Write a runbook and hand it to a friend.** If they cannot follow it, it is not finished.
10. **Do a mock audit.** Pick three claims in the wiki and gather the evidence that each is true.

## Predict, then check

1. A friend says "I want to work in security." Name three different roles from the table that fit, and say how their days differ.
2. Which rungs of the ladder can you complete without spending any money? Which ones need a cloud account?
3. A job posting lists four certifications as "required." What are two sensible things to check before you decide?
4. Why does the table list the same wiki page against more than one role?
5. Which role's work does the cost gate in this repository most resemble, and which role's work does the threat model most resemble?

### Reference answers

1. For example: security analyst (watches alerts and triages), security engineer (builds controls and reviews designs), GRC (gathers evidence against standards). Analyst work is reactive and time-boxed, engineering is design and implementation, GRC is documentation and conversation.
2. Rungs 1, 2 and mostly 5 and 8 need no spend (reading, reading plans, threat modeling). Rungs 3, 4 and 6 need an account or hardware; the cost gate exists to keep that bounded.
3. Whether "required" really means required or is a wish list, and what the people already in the role hold. Also check whether the credential expires and what renewing costs.
4. Because the roles share foundations; a network engineer and a security engineer both need the firewall page, for different reasons.
5. The cost gate resembles cloud engineering and FinOps work (a control that blocks spend before it happens); the threat model resembles security engineering and GRC work (naming risks, deciding what to accept, and writing it down).

## Try it yourself

- Pick two roles from the table and read three job postings for each. Mark every skill that appears in the "pages here" column.
- Write your own ladder: the next three rungs for you, with a date each.
- Choose one "keep tinkering" idea, write the acceptance test first, and then do it.
- Ask someone in a role above what they would do differently if they were starting again, and write down the answer.

## Claims register

Status is one of: `Verified <date>`, `General knowledge` (widely held industry usage, not checked here), or `UNVERIFIED`.

| Claim | Status | Source |
|---|---|---|
| Role descriptions and day-to-day duties in the roles table | General knowledge | job titles and duties vary by employer; not checked against any employer or survey |
| The named certifications exist and are commonly discussed for the areas listed | General knowledge | not checked against current issuer pages or exam objectives |
| Some certifications have experience requirements and renewal fees or continuing education | General knowledge | varies by issuer; check the issuer |
| CISA and CISM are ISACA certifications aimed at audit and governance | General knowledge | not checked |
| Certifications' value to employers varies by region and role | UNVERIFIED | anecdotal; ask people in the role |
| Terraform and OpenTofu languages are close but not identical | General knowledge | see the OpenTofu page; not re-checked |

Next: [Reading order](Reading-Order.md). Back to the [Home](Home.md) page.
