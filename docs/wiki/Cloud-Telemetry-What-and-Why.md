# Cloud telemetry: what it is and why it crosses a trust boundary

> **Unverified draft: the stage 2 telemetry pieces this page describes are built and merged (opt-in node exporter, Wazuh agent with auditd, metrics firewall rules, Grafana dashboards), but none of it has been applied or run against real infrastructure, and nothing has been measured.** Sources: the [stage 2 logging design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-11-stage-2-logging-design.md) (2026-10-11) and the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) (2026-10-16). Nothing on this page describes something running. Where a vendor fact was not checked, the page says so.

**Prerequisites:** [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) (the four jobs: collect, store, detect, respond) and [Networking basics for this project](Networking-Basics-for-This-Project.md).

This is the first of five pages that take one question as far as it will go: **how does a cloud machine tell you what it is doing, and what does that cost you?** This page gives the vocabulary and the reason telemetry is a security decision. The later pages take it across a trust boundary, give each site an identity, teach you to read the result, and then ask you to build a small version yourself.

## Four words that are not synonyms

| Word | What it is | Shape | Good at | Bad at | In this project |
|---|---|---|---|---|---|
| **Log** | One event, written when something happens | A line of text or a record with a time stamp | Answering "what exactly happened" | Cheap summaries; volume grows with activity | The connector's journal, `sshd` and `sudo` lines. Built, opt-in and off: a Wazuh agent reads them (not applied) |
| **Metric** | A number sampled over time | A name, labels, a value, a time | Answering "how much" and "since when" cheaply; volume grows with the number of series, not with activity | Saying *why* | CPU, memory, bytes in and out (the node exporter, built, opt-in and off), and whether a target answered (the `up` series Prometheus writes itself on every scrape, not an exporter metric). The Prometheus scrape at home is not built |
| **Trace** | The path of one request through several services, with the time spent in each | A tree of timed spans | Answering "where did this request spend 4 seconds" | Anything that is not a request | **None.** Two connectors and a few daemons do not have a request that crosses services. Stage 3 may |
| **Alert** | A decision made from logs or metrics: "this needs a person" | A rule that fired, a message, a recipient | Turning data into attention | It is *derived*: an alert on bad data is a bad alert | Two Prometheus rules exist in the synthetic lab; no Wazuh rule is written |

An alert is the odd one out. Logs, metrics and traces are raw material; an alert is what a rule makes of them. That is why "we have monitoring" and "someone would find out" are different sentences: the first is about collecting, the second is about the alert, the recipient and the five minutes after.

Two quick tests that sort most confusion:

- **Does the volume follow activity?** Yes: logs and traces. No: metrics (one sample per series per scrape, whether or not anything happened).
- **Would you still want it a year from now, once the machine is gone?** Logs, usually (evidence). Metrics, usually in summary (trends).

## NOC, SOC and SIEM: a team, a team and a tool

These three get mixed up because they share data. They are not the same kind of thing.

| Aspect | NOC | SOC | SIEM |
|---|---|---|---|
| Stands for | Network operations center | Security operations center | Security information and event management |
| It is a... | Function, usually a team | Function, usually a team | **Tool** (a product or a stack) |
| Its question | "Is it up, and is it fast enough?" | "Is anything here hostile, and what do we do?" | "Can I search and correlate what every source said?" |
| Main data | Metrics, uptime checks, a few logs | Logs, endpoint and identity events, threat intelligence | Logs from everywhere, normalized |
| Paged for | A connector is down; the link is saturated | A login from a new place; a changed config file | Nothing by itself: it feeds the other two |
| Clock | Minutes to restore service | Minutes to hours to contain, days to investigate | Retention measured in months |

The honest overlap: a connector that stops answering is a NOC problem, and it could also be the first sign of something a SOC cares about. The difference is the **question you ask of the data and who is expected to act**, not the data. A small team (this project has one operator) wears both hats, which is why the lessons put the NOC first: you need a baseline of normal before an alert for abnormal means anything. [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) places the commercial products on the same map.

## Why telemetry has to leave the machine

A machine cannot be trusted to report on its own compromise. If an attacker gets a shell on a connector, the first thing worth doing is editing or deleting the local log. Evidence that stays on the host lasts exactly as long as the host does. So the useful copy lives somewhere the host cannot reach to rewrite: here, the SIEM at home.

That decision has a consequence that is easy to miss. **The monitoring path is a new route between two places that were deliberately kept apart.** This repository's whole shape is "no inbound path, one narrow tunnel for people". Telemetry adds a tunnel for machines, in both directions:

- the home side needs to read metrics from the cloud hosts;
- the cloud hosts need to send logs home.

The [stage 2 design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-11-stage-2-logging-design.md) and the next page handle that with Twingate resources of one port each. The point for this page is that visibility has a price in exposure, and the price is paid in the same currency as everything else here: trust boundaries.

## What it costs

| Cost | What it is | Where the design says it |
|---|---|---|
| **New code as root** | A Wazuh agent and a metrics exporter run on a machine you wanted to keep small | Stage 2 design, section 6 |
| **A new secret per host** | Each agent has an enrollment key; each host has a Twingate service key | Settings design, section 2.8 |
| **A new path** | A compromised droplet can reach the logging ports of the SIEM, and nothing else if the design holds | [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) |
| **Memory** | The two connector droplets are `s-1vcpu-1gb`. The stage 2 design guesses the agent at 50 to 100 MB and the exporter at about 20 MB, labeled estimates, and says to measure on one connector first | Stage 2 design, section 8 |
| **Bandwidth** | Metered use that the cost gate does not see (`docs/cost.md`, "Not yet verified": bandwidth overage). Small is an assumption until measured | Settings design, section 8 item 15 |
| **Logs hold secrets** | If a service logs a token or a command line, the SIEM becomes a place to find it | [Detection page](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#things-this-project-should-say-out-loud) |
| **Silence** | A dead collector produces no alerts. Absence of alerts looks the same as health | [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) |

None of these is a reason not to collect telemetry. Each is a reason to collect it deliberately, and to be able to say what you accepted.

## Predict, then check

Write your answers before opening the reference.

1. Sort these into log, metric, trace or alert: (a) "sshd accepted a public key for the admin user at 03:12"; (b) bytes sent per second on a connector; (c) "CPU above 90 percent for ten minutes" paged someone; (d) one request that took 4 seconds across three services.
2. For each, say whether a NOC or a SOC would ask it first: (a) "Is connector b answering?" (b) "Did anyone log in over SSH at 03:00?" (c) "Is traffic using the relay instead of a direct connection?"
3. An attacker gets root on a droplet that keeps its logs only on the droplet. A second droplet ships its logs home as they are written. What does each give the investigator?
4. Which cost in the table above does the cost gate not see, and where does `docs/cost.md` say so?

<details>
<summary>Reference answers</summary>

1. (a) log; (b) metric; (c) alert (made from a metric by a rule); (d) trace. Nothing in this project produces (d) today.
2. (a) NOC. (b) SOC. (c) Either, and that is the point: the relay question is about performance, but a sudden change in how traffic flows could matter to security. The team differs; the data may not. (The source of the relay metric is the connector's own metrics, per the stage 2 design, which says only that it splits bytes into direct and relay.)
3. The first: whatever the attacker left, which is exactly what they chose to leave. The second: everything written up to the moment the agent was stopped or the path was cut, and a gap that starts at that moment, which is itself a signal. The [detection page](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#try-it-yourself) makes the same point: how long until anything tells you a sensor has gone quiet is usually the number nobody has.
4. Bandwidth. `docs/cost.md` lists "Bandwidth overage" under "Not yet verified".

</details>

## Try it yourself

- **No cost.** Pick three things that went wrong in [Lessons learned](Lessons-Learned.md) and write which signal (log, metric, trace) would have shown each one first, and which would have been an alert.
- **Say it in one sentence each.** Without the table, explain NOC, SOC and SIEM to someone who has not read this page. If your SIEM sentence mentions a team, rewrite it.
- **Read one.** If you have never read a log line, [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) takes you through an SSH line and a web access line field by field, on invented logs.
- **Find the cheapest signal.** For "is connector a up", name the cheapest signal that answers it, and then the one that would also tell you *why* it is down.

Next: [Multiple sites and identity](Multiple-Sites-and-Identity.md). Back to the [Reading order](Reading-Order.md).

Where this is built: the [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md) describes the telemetry stack and the opt-in exporter and agent on the connectors (everything off by default, nothing applied).
