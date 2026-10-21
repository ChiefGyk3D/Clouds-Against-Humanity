# Seeing what happened: detection, Wazuh and the wider landscape

> Read [Threat model](Threat-Model.md) first. Its right-hand column, "residual risk", is a list of things this project's controls do **not** stop. This page is about the control that covers them: noticing.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Most of this wiki is about **prevention**: no open ports, narrow tokens, reviewed changes. Prevention fails eventually, through a bug nobody knew about, a stolen credential, or a mistake. The question that decides how bad that day is: **would you know, and how fast?** That is detection, and it needs data (telemetry), a place that collects it, rules that say what is suspicious, and a person who gets the alert.

This page teaches those four pieces using Wazuh, which this project plans to use, and then places the commercial products you will meet at work (CrowdStrike, SentinelOne, Bitdefender GravityZone, Datadog, Wiz and others) on the same map.

**Status, so you do not look for something that is not there:** the cloud hosts in this repository do **not** ship logs anywhere today. Shipping to Wazuh is stage 2, which is designed (`docs/superpowers/specs/2026-10-11-stage-2-logging-design.md`) and not built. The Wazuh described below is the author's existing home setup and the plan for connecting the cloud to it. This is the honest reason the connectors are, for now, a blind spot, and the page about them says so.

## Four jobs, and the words people mix up

| Job | Question it answers | Examples |
|---|---|---|
| **Collect** | What is happening on this machine? | Logs (events written by software), metrics (numbers over time), file and process activity, cloud audit logs |
| **Store and search** | Can I look back and find it? | A log store or index; a SIEM |
| **Detect** | Is any of it suspicious? | Rules, baselines, threat intelligence, behavior analytics |
| **Respond** | Who is told, and what happens? | Alerts, tickets, paging, blocking, isolating a machine |

The product categories you will hear are different mixes of those four jobs, aimed at different places:

| Category | Watches | Typical shape |
|---|---|---|
| **SIEM** (security information and event management) | Logs from everywhere | Collects, stores, correlates and alerts. Wazuh, Splunk, Elastic, Microsoft Sentinel and others fill this role (Wazuh also does more, below). |
| **EDR** (endpoint detection and response) | Activity on laptops, servers, VMs: processes, files, network, with the power to isolate a machine | An agent on every machine and a cloud console. CrowdStrike Falcon, SentinelOne and Bitdefender GravityZone are in this space. |
| **XDR** (extended detection and response) | EDR plus other sources (identity, email, cloud, network) joined together | Largely a marketing and packaging term; ask what data is actually correlated. |
| **MDR** (managed detection and response) | The same, watched by someone else's analysts around the clock | A service, not a product. |
| **CNAPP / CSPM** (cloud-native application protection, cloud security posture management) | The **cloud account itself**: misconfigurations, exposed storage, risky permissions, vulnerable images | Often **agentless**: it reads the cloud's APIs instead of installing software. Wiz is a well-known example. |
| **Observability / monitoring** | Health and performance of applications and infrastructure | Metrics, logs and traces for engineers, with security products added by some. Datadog is a well-known example; Prometheus and Grafana in this project's plan are the open-source equivalents. |
| **SOAR** (security orchestration, automation and response) | Nothing directly: it runs the response steps | Automates "when this alert fires, do these things." |

Vendors blur these lines in marketing and keep adding to their products, so treat this table as the shape of the categories, not a feature list, and read a vendor's own documentation for what a product does now.

## Wazuh, piece by piece

Wazuh is open-source security monitoring. It is useful to learn on because every piece is visible and you can run all of it yourself.

| Piece | What it is | In this project |
|---|---|---|
| **Agent** | A small program on each monitored machine that reads logs and files and sends events to the manager | Planned on each cloud host. The agent connects **out** to the manager, which is the direction the zero-inbound design allows. |
| **Manager (server)** | Receives events, decodes them, applies rules, raises alerts | At home, in the author's SIEM stack (`siem-docker-stack`). |
| **Indexer and dashboard** | Store and search alerts; the web interface | At home, alongside OpenSearch and Grafana. |
| **Decoders and rules** | XML that turns a raw log line into fields, then decides if the fields are worth an alert, at what level | The home setup already has rules for Twingate connector logs written for the Docker log format; the cloud connectors log to journald instead, so the rules need a version for that shape. |

Beyond log analysis, Wazuh includes file integrity monitoring (tell me when `/etc/ssh/sshd_config` changes), configuration assessment against hardening benchmarks, vulnerability detection for installed packages, and active response (run a command when a rule fires). Which of these this project turns on is a stage 2 decision.

### Why it fits here

- **It matches the zero-inbound rule.** The agent dials out to the manager. Nothing listens on the droplet for it.
- **It answers a specific residual risk.** The [Threat model](Threat-Model.md) accepts that someone holding both a stolen identity and the SSH key gets a shell on a connector (T2). Prevention is exhausted at that point. The stage 2 design plans to watch SSH and sudo activity through the journal, file integrity on `/etc/twingate`, `/etc/ssh` and `/etc/sudoers.d`, and a small set of rules for connector logs, so a login at an unexpected time or a changed config file is how you would find out. Things like a new key added to the admin user's `authorized_keys` or an unusual outbound connection are *not* in that plan; they would be additional telemetry to add, and noticing the gap is part of the exercise below.
- **Per-host keys limit the damage.** Each agent has its own enrollment key, so one compromised host does not hand over another's identity.
- **It costs nothing in the cloud.** The agent is small and the manager is already running at home. The stage 2 design lists it at $0 added cloud cost and keeps the approved total at $12.

### Why it is not obviously right

Be wary of the answer that sounds best:

- **The cloud has no route home yet.** Sending logs home is itself a new path across a trust boundary. The design makes it a narrow Twingate resource per port, and treats a compromised droplet as something that must be able to reach exactly the manager ports and nothing else.
- **An agent is code running as root on a machine you want to keep small.** It also has a secret (its enrollment key) that has to get onto a rebuildable droplet without sitting in a public repository.
- **Detection you do not read is a log file.** An alert that goes to a dashboard nobody opens has not detected anything.

## Where the commercial products fit

Placing a product means asking three things: **what does it watch, how does it see it, and who acts on the alert?**

| Product (examples) | Watches | How it sees it | Notes for this project |
|---|---|---|---|
| **Wazuh** | Logs, files, configuration and packages on each host | Agent, plus ingest of syslog and cloud logs | The one this plan uses: open source, self-hosted, you own the rules. |
| **CrowdStrike Falcon, SentinelOne, Bitdefender GravityZone** | Process, file, network and identity activity on endpoints and servers, with automated containment | A kernel-level or privileged sensor on each machine, managed from a vendor cloud console | Built for fleets of laptops and servers with a team to run them. Check each vendor's supported systems and sensor requirements before assuming one runs well on a 1 GB droplet; that is a question for their documentation, not something this page claims. |
| **Wiz** (and similar CNAPP/CSPM tools) | The **cloud account**: public storage, over-broad roles, exposed ports, vulnerable images, how they combine | Mostly agentless, through the provider's APIs | On a one-person DigitalOcean account this adds little. In a large AWS, Azure or GCP estate it is how you find the thing nobody remembered creating. |
| **Datadog** (and similar observability platforms) | Application and infrastructure health, and with extra products, security signals | Agents and integrations, a vendor-hosted backend | Overlaps with the Prometheus and Grafana plan on the metrics side; the security products are an add-on. |
| **Splunk, Elastic, Microsoft Sentinel** | Whatever logs you send | Collectors and connectors | The SIEM role. Wazuh plus OpenSearch is the self-hosted version of the same idea. |

The useful distinction is **agent versus agentless, and host versus cloud control plane**. An EDR or Wazuh agent sees *inside* a machine: it can tell you a process spawned a shell. A CNAPP sees the *account*: it can tell you a storage bucket is public. Neither sees the other's world. That is why enterprises run several, and why the integration between them (and the question of who owns each alert) is most of the work.

## How an enterprise differs

- **Volume and cost.** Telemetry is priced and stored by the gigabyte. Deciding what *not* to collect, and for how long to keep it, is a budget and compliance decision as much as a technical one.
- **People.** A security operations center (SOC), a managed provider (MDR) or an on-call engineer reads the alerts. The product is the smaller half of the capability.
- **Alert fatigue.** A system that raises a thousand low-value alerts a day teaches people to ignore it. Tuning rules, and deleting the ones that never matter, is the unglamorous main task.
- **Overlap and sprawl.** Several tools see the same machine, disagree, and each has its own console. Consolidation projects are common.
- **Retention and evidence.** Auditors and incident responders need logs that were kept, were not altered, and can be produced. Where the logs live matters as much as having them.
- **Protecting the sensor.** Attackers disable or blind security agents. Tamper protection and alerting when an agent goes quiet are standard concerns.

## Things this project should say out loud

- **The first compromise is invisible until stage 2 lands.** The connectors are a detection blind spot today. The honest status belongs next to the controls.
- **A monitoring agent expands the attack surface** even as it improves visibility: more code, a new secret and a new network path. Weigh it, do not assume it is free.
- **Logs can contain secrets.** If a connector logs a token or a command line, the SIEM becomes a place to find it. Collect deliberately.

## Try it yourself

- **No cost, no install.** Open the [Threat model](Threat-Model.md). For each of T1 to T14, write the **one log line, file or event** that would tell you it was happening, and **where it is recorded**: on a host, in a vendor's audit log (GitHub, Doppler, Spacelift, Twingate), or in the billing system. Some threats, like a malicious pull request or a runaway bill, never touch a droplet. If you cannot name any place that records one, that threat is undetectable as designed. Then compare with the stage 2 design's list. 
- **Read a rule.** Open `wazuh/twingate_rules.xml` in the author's public [siem-docker-stack](https://github.com/ChiefGyk3D/siem-docker-stack) repository (the Twingate rules the stage 2 design refers to are numbered 120700 to 120750) and answer: rule 120700 is a **silent parent** (level 0). What decoded shape of event does it require (which decoder, which field and value), why is it deliberately silent, and how do the child rules such as 120701 build on it? Then: what would you change so the rules work on the journald format instead of the Docker JSON format? Predict first, then read.
- **Design the 3 a.m. alert.** Pick one threat. Write the alert you would want: what it says, who receives it, what they do in the first five minutes, and what makes it a false alarm. Then ask whether you would still want to be woken up for it in a month.
- **Agent or agentless?** For each of: a public storage bucket, a process on a droplet launching `/bin/sh`, an IAM role with admin rights, a modified `sshd_config`. Say which kind of tool could see it and why the other kind could not.
- **Break it on purpose, later.** When stage 2 exists in your own copy, change a monitored file on a throwaway host and find the alert. Then stop the agent and find out how long it takes anything to tell you it has gone quiet. That second number is usually the one nobody has.

Next: [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md), the first of five unverified-draft pages on telemetry, sites and a small SOC of your own; the stage 2 section of the [Roadmap](Roadmap.md#stage-2-logging-and-the-link-home-design-merged-cloud-side-in-progress-not-applied) is where it becomes a build. Back to [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) or the [Reading order](Reading-Order.md).
