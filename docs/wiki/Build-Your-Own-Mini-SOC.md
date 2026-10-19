# Build your own mini SOC: a springboard, not a product

> **Unverified draft: the stage 2 telemetry pieces this page describes are built and merged (opt-in node exporter, Wazuh agent with auditd, metrics firewall rules, Grafana dashboards), but none of it has been applied or run against real infrastructure, and nothing has been measured.** Sources: the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) sections 1.3, 5 and 6 (2026-10-16), `docs/cost-prices.json` (DigitalOcean regular droplets, retrieved 2026-10-10) and `docs/cost.md`. No cloud Grafana, Prometheus or Wazuh manager exists in this repository. The memory each piece needs is an **estimate to be measured**; the droplet prices are the only hard numbers on this page.

**Prerequisites:** [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md), [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md), [How money works in the cloud](How-Money-Works-in-the-Cloud.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).

The on-premises version of this idea is a working security-monitoring stack. This page is the version you build **yourself, in the cloud, in your own account, under your own budget**, in stages that each stand alone. It is a springboard: the point is to keep tinkering and learning, not to reproduce a product.

Two decisions frame it:

- **The reference environment of this repository stays at stage 3** (about $29 a month, see below) and uses the maintainer's existing Grafana at home for the cloud's dashboards. It does not build the cloud mini SOC.
- **The cloud mini SIEM, NOC and SOC is the learner's own build.** The cost rows below are worked examples against the $30 ceiling of the current phase; your copy sets its own, per phase (the `learner-soc` phase in `docs/stages/approved.json` carries a proposed $53).

## How it maps to the home stack, by role

The home stack is described here by **role and technology only**. The mapping is the lesson: each job has a name, and each job has a cheaper, smaller cousin.

| Job | Role at home (technology) | The mini version in this page |
|---|---|---|
| Metrics and uptime | Prometheus, with Alertmanager for routing | N0 uses yours; N1 adds a small Prometheus in the cloud |
| Dashboards | Grafana | N0 extends yours; N1 puts one in the cloud |
| Security alerts | A Wazuh manager with an indexer and dashboard | S1: a lab-scale manager, no indexer |
| Log search | OpenSearch | **Not built in the cloud.** Use a local machine or your own SIEM |
| Log transport | A syslog pipeline | S1's `syslog_output` forwarding |
| Retention | An index lifecycle policy | `metrics_retention_days` and `log_retention_days` |

Order matters: **NOC first, SOC second, SIEM last.** Alerts need the baseline a NOC gives you; search needs the alerts to tell you what to search for.

## The stages

| Stage | Role | Question it answers | What you build | Cost row |
|---|---|---|---|---|
| **N0** | NOC at home | "Is it up, and how busy is it?" | Nothing in the cloud. Your own Prometheus pulls the cloud hosts over Twingate; your Grafana gets the `site` and `instance` variables | $0 |
| **N1** | NOC in the cloud | The same, from a cloud Grafana, working even when the link home is down | One droplet with Grafana and a small Prometheus, scraping the VPC. **No path into home** | See the cost table |
| **N2** | The cloud NOC sees all sites | The same view with selected home and other-site metrics | Your Prometheus `remote_write`s a filtered set to the cloud Prometheus. You initiate; the cloud still has no way to query you | Same droplet, $0 more |
| **S1** | SOC | "Is anything suspicious?" | A lab-scale Wazuh manager in the cloud whose alerts are forwarded to a syslog destination | See the cost table |
| **S2** | SIEM | "What exactly happened?" | Not built in the cloud. The full Wazuh stack does not fit the ceiling | Your own SIEM, or a local machine |

### N0: start with nothing

The cheapest stage teaches the most. Build the labels and the variables first ([Multiple sites and identity](Multiple-Sites-and-Identity.md)), read the dashboard until you can predict its failures ([Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md)), and write the expected-target inventory alerts. If you have no Prometheus and Grafana, run both on a laptop. Everything after this stage is optional.

**Measure:** the scrape success ratio per site, the time from stopping a target to the Silent alert, and the memory the metrics exporter takes on a connector (the design's guess is about 20 MB; it is an estimate to check).

### N1: a small cloud Grafana, reachable only through Twingate

The design's shape, none of it built:

- One droplet in the VPC, tagged for its role. Grafana and Prometheus listen on the **private** address only.
- Its firewall has **one** inbound rule: TCP on the Grafana port, with the connector **tag** as the source. No rule has an address source. Twingate does not bypass the destination's firewall; the connector opens an ordinary connection inside the VPC.
- **Scraping the connectors takes rules on both sides**, and the SOC droplet does **not** get the connector tag (that would put it inside the connectors' trust group). Today the firewall module (`modules/firewall`) only admits and permits the firewall's own tag, and its default outbound rules are tcp 443, 80 and 53 and udp 53 and 123 (`default_outbound` in `modules/firewall/main.tf`), which do not include the exporter ports. So you need: (a) on the **connector** firewall, an inbound rule for the exporter ports whose source is the **SOC tag**; (b) on the **SOC** firewall, an outbound rule for the same ports, ideally with the connector tag as the destination. The design plans an additive `inbound_from_other_tags` input (and an `outbound_to_other_tags` one) for the module; as of this page's last check those inputs are being added in a separate pull request and are **not on the main branch**. The design lists the connector-side outbound input but is silent on the SOC-side egress, so (b) is this page's inference from the module's stateful-reply behaviour: a new outbound connection needs an outbound rule. Until the inputs exist, `extra_outbound_rules` can open the port but has no tag scope, so prefer waiting for the tag-scoped input.
- A Twingate resource of one port, TCP only, UDP denied, ICMP off, granted to a SOC admin group, the same form as the SSH resources on the [Twingate page](Twingate.md).
- Grafana's own accounts, anonymous access off, sign-up off, admin password from Doppler. HTTP inside the tunnel for the first build, which is a trade-off, not a recommendation.
- Dashboards come from files in git, so the same JSON installs here and at home. Prefer rebuilding over restoring: a droplet is disposable.

**Measure:** memory headroom on the droplet before and after (you predict it first, below), the series count and the disk growth per day (it decides retention), and which ports answer from the public Internet (the answer to prove is none).

### N2: push, don't open a path

A cloud Grafana pointed at your home Prometheus would reach Prometheus's whole HTTP surface, because a one-port resource is not read-only. So home pushes. `remote_write` with filtering (`write_relabel_configs`) sends only the series you choose, and the cloud Prometheus's write receiver accepts it. The receiver is a write endpoint (enabled by a flag; UNVERIFIED), so its Twingate resource is granted only to your Prometheus's service.

A Twingate resource does not bypass the firewall here either. N1 admitted only the Grafana port, so N2 needs one more rule pair: on the **SOC** firewall, an inbound rule for the receiver port with the **connector tag** as the source (the home Prometheus's traffic leaves a connector and enters the VPC as an ordinary connection), and on the **connector** firewall the matching outbound rule to the SOC tag on that port. Both are tag-scoped, which needs the same planned `other_tags` inputs, and the assertion from the design still holds: no inbound rule has an address source. Without them the push fails at the firewall while the Twingate resource looks correct.

This stage moves data about your home **out** to the cloud. Decide what that data is before you send it. If a series name or label would tell a stranger something about your network, filter it.

**Measure:** bandwidth between the two (it is metered use outside the cost gate), and what the cloud Grafana shows when you cut the link (it should keep working for cloud hosts, because its local Prometheus does).

### S1: a lab-scale SOC, and its honest limits

A Wazuh manager owns its agents. In S1 the **cloud manager** owns the site's agents and forwards alerts onward. The facts, from Wazuh's documentation page on alert management (https://documentation.wazuh.com/current/user-manual/manager/alert-management.html , fetched 2026-10-16): the manager can send alerts to a syslog server (`syslog_output`), by default over UDP on port 514, with a minimum alert level filter, and several destinations by repeating the block. That page does **not** document TCP or TLS for the forwarding, a JSON format, buffering, filters by rule id or group, or joining two managers across networks. The design assumes none of those. It is not federation.

| What happens | Consequence |
|---|---|
| Only **alerts** at or above the minimum level forward | **Raw events stay on the cloud manager.** You can see an alert at home and be unable to see the event behind it. That is a loss, not a bug |
| The forwarded line is syslog text | The destination must decode it; its rule ids are its own, so rules for the forwarded format are written from captured lines, not assumed |
| A destination that also copies syslog to its own Wazuh | A **duplicate**: the same event can alert twice, once at the source and once at the destination |
| UDP syslog has no buffering | Alerts during a link outage are lost at the destination, and remain in the cloud manager's alert file for its retention. Backfill is by hand |
| The cloud manager owns the agents | The destination's agent-health views do not list them |

For a learner these are the lesson: reproduce each on purpose. The design recommends that the reference environment does **not** build S1 and keeps agents reporting directly to the home manager, which preserves agent health, raw events and one alert pipeline.

One more honest note. Earlier stages have **no path into home**. S1's forwarding is a path from the cloud toward a destination; if that destination is at home it needs its own Twingate resource and ends the "no path into home" property for that stage. You can instead forward to a lab collector in the same cloud site and keep the property. Decide it knowingly.

**Measure:** memory (the manager's needs are an estimate to check on a 2 GB droplet), time from changing a monitored file on a throwaway host to the alert, time from stopping the agent to anything noticing, and the count of alerts at the source versus received at the destination.

## What it costs

Prices are the regular-droplet list prices in `docs/cost-prices.json`, retrieved 2026-10-10. A DigitalOcean site carries two `s-1vcpu-1gb` connectors, $6 + $6 = $12 (`stacks/10-access/cost.json`). "Stage 3 A" is the reference environment's planned stage 3 option: a `s-1vcpu-2gb` droplet at $12, a $5 bucket and the $12 of connectors, $29 in total (`docs/cost.md`, prices read 2026-10-11). Memory sizes of the droplets below are **estimates**: pick the size that measured memory justifies. Block storage and droplet backups are not in the table: the price file has no volume price, and weekly backups are 20 percent of a droplet (verified against DigitalOcean's pricing page on 2026-10-19; `backups_fraction_verified` is `true`; daily and usage-based backup plans are unverified and not modelled).

Each cell shows the arithmetic: the site connectors, plus the SOC droplet(s) (one in total, not one per site), equals the monthly total. Two sites mean two sets of connectors, so $24 before any SOC droplet.

<!-- cost-table ceiling=30 -->

| Option | Droplet(s) | One site | Two sites | One site + stage 3 A | Fits (one / two / one + stage 3 A) |
|---|---|---|---|---|---|
| N0, nothing new | none | $12 + $0 = $12 | $24 + $0 = $24 | $29 + $0 = $29 | Yes / Yes / Yes |
| N1, small | `s-1vcpu-1gb` | $12 + $6 = $18 | $24 + $6 = $30 | $29 + $6 = $35 | Yes / Yes / No |
| N1, 2 GB | `s-1vcpu-2gb` | $12 + $12 = $24 | $24 + $12 = $36 | $29 + $12 = $41 | Yes / No / No |
| S1 with NOC, one droplet | `s-2vcpu-2gb` | $12 + $18 = $30 | $24 + $18 = $42 | $29 + $18 = $47 | Yes / No / No |
| S1 with NOC, one droplet, more room | `s-2vcpu-4gb` | $12 + $24 = $36 | $24 + $24 = $48 | $29 + $24 = $53 | No / No / No |
| N1 small and S1 on two droplets | `s-1vcpu-1gb`, `s-2vcpu-2gb` | $12 + $24 = $36 | $24 + $24 = $48 | $29 + $24 = $53 | No / No / No |
| Full Wazuh stack (S2 in the cloud) | `s-4vcpu-8gb` | $12 + $48 = $60 | $24 + $48 = $72 | $29 + $48 = $77 | No / No / No |

What the table says, plainly:

- **At the $30 ceiling**, two sites fit only with N0 ($24) or the small N1 ($30, with nothing left). Two sites and any bigger SOC do not fit.
- **Stage 3 A and any cloud SOC droplet do not fit together** ($29 + $6 = $35 is already over). That is why the reference environment uses N0.
- **The full Wazuh stack does not fit and will not.** It is the home build's job.
- Splitting N1 and S1 across two droplets costs more than one larger droplet ($24 against $18 for the SOC part) in exchange for isolation.
- The same arithmetic on a larger ceiling, to show it is yours to set:

<!-- cost-table ceiling=45 -->

| Option | Droplet(s) | One site | Two sites | One site + stage 3 A | Fits (one / two / one + stage 3 A) |
|---|---|---|---|---|---|
| N0, nothing new | none | $12 + $0 = $12 | $24 + $0 = $24 | $29 + $0 = $29 | Yes / Yes / Yes |
| N1, small | `s-1vcpu-1gb` | $12 + $6 = $18 | $24 + $6 = $30 | $29 + $6 = $35 | Yes / Yes / Yes |
| N1, 2 GB | `s-1vcpu-2gb` | $12 + $12 = $24 | $24 + $12 = $36 | $29 + $12 = $41 | Yes / Yes / Yes |
| S1 with NOC, one droplet | `s-2vcpu-2gb` | $12 + $18 = $30 | $24 + $18 = $42 | $29 + $18 = $47 | Yes / Yes / No |
| S1 with NOC, one droplet, more room | `s-2vcpu-4gb` | $12 + $24 = $36 | $24 + $24 = $48 | $29 + $24 = $53 | Yes / No / No |
| N1 small and S1 on two droplets | `s-1vcpu-1gb`, `s-2vcpu-2gb` | $12 + $24 = $36 | $24 + $24 = $48 | $29 + $24 = $53 | Yes / No / No |
| Full Wazuh stack (S2 in the cloud) | `s-4vcpu-8gb` | $12 + $48 = $60 | $24 + $48 = $72 | $29 + $48 = $77 | No / No / No |

The approved figure is a fixed monthly infrastructure price, not a cap. Bandwidth between cloud and home is metered use the gate does not see, and small is an assumption until you measure it. The gate's job for you is to refuse a change that raises the total without your approving the new figure (see [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)).

## What to measure, in one list

Measuring is half the point. Each item turns a guess in this page into a number you own.

| Measure | Why | How you would find it |
|---|---|---|
| Memory headroom on each droplet, before and after each stage | The sizes above are estimates | `free -m` on the host, available column, before and after |
| Number of series in the cloud Prometheus | It sets disk and memory | Prometheus's own head series metric |
| Disk growth per day | Sets the retention you can afford | Directory size on two days |
| Bandwidth between the sites | Metered, outside the gate | The provider's usage page, a week of data |
| Time to the Silent alert | The number nobody has | Stop a target on a throwaway host and watch |
| Alert counts at source and at destination (S1) | Shows loss and duplicates | The manager's alert file and the destination's received count |

## Tear it down

A stage you cannot remove is a bill you cannot stop.

1. Destroy the SOC stack with OpenTofu (the plan should delete only that stack's objects).
2. Revoke the Twingate service keys and delete the services the stage created; revoke any Doppler token it used.
3. Remove the agent registrations on the manager if you built S1.
4. Check that the droplet is gone from the provider's console and that the bill goes to zero for it, as [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) does at the end of stage 1. Backups and volumes are billed separately; check for them.

## Keep tinkering

The stages end, but the learning does not. Each of these is a project:

- **Alerts as code.** Put alert rules in a file under version control, test them with `promtool test rules` on fixtures (the five scenarios in [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md)), and let CI run them. A rule nobody tests will not fire on the day it matters.
- **Dashboards as code.** Provision dashboards from files, and generate the repetitive ones. Review dashboard changes like code changes.
- **Log pipelines.** Parse the journal into fields, write a decoder and a rule from lines you actually captured, and test it with the manager's logtest tool. Drop the noisiest lines on purpose and count what you saved.
- **ATT&CK-driven coverage.** Map each rule to the MITRE ATT&CK technique it detects (https://attack.mitre.org/), then list the techniques you have no rule for. A dedicated Threat-Frameworks page was not on the main branch of this repository when this page was written (2026-10-16); when it exists, link your coverage table to it.
- **Another cloud.** Run the same stages on AWS, Azure or GCP and notice what changes: [Why the clouds differ](Why-the-Clouds-Differ.md) is the map, and the budget lessons differ most.
- **A black-box check.** Add an uptime probe from outside, so something other than the host itself can say the host is not answering.

## Predict, then check

1. Fill the cost table for a ceiling of $36. Which options fit at one site, at two sites, and with stage 3 A?
2. Predict the memory headroom on the droplet you pick for N1, then measure. Where was your guess wrong, and by how much?
3. The link to home is cut. What does the cloud Grafana show for the cloud hosts, and what does it show for home series sent by N2?
4. A level-5 alert occurs on a cloud host and S1's forwarding minimum is level 7. What does the destination receive? What if the level is 9 and the destination also copies syslog into its own Wazuh?
5. From outside, which ports of the N1 droplet should answer? How do you prove it?

<details>
<summary>Reference answers</summary>

1. The totals do not change, only the comparison. At $36: one site, every row up to and including the 4 GB S1 ($36) and the two-droplet row ($36) fits; the full stack ($60) does not. Two sites: N0 ($24), the small N1 ($30) and the 2 GB N1 ($36) fit; S1 ($42 and up) does not. With stage 3 A: only N0 ($29) and the small N1 ($35) fit; $41 and above do not.
2. No reference answer exists: the design gives no memory figure for Grafana, Prometheus or the Wazuh manager, only that they must be measured. The gap between your guess and the measurement is the lesson.
3. The cloud hosts: normal, because the local Prometheus keeps scraping inside the VPC. Home series: they stop updating, and the panel shows the last data and then nothing, because `remote_write` is pushed from home and the push cannot arrive.
4. Level 5: nothing arrives; it stays in the cloud manager's alerts. Level 9: it forwards as a syslog line. If the destination also copies syslog into its own Wazuh, the same event can alert twice, once there and once at the source, each with its own rule id.
5. None. The firewall has one inbound rule at N1 (two at N2, when the receiver port is added), all tag-sourced from the connectors, and Twingate reaches the droplet through them. Prove it as stage 1 did: scan the droplet's public address from outside and expect every port filtered.

</details>

## Try it yourself

- **No cost.** Fill the cost table for your own ceiling with the arithmetic shown, and write one sentence for each row you cannot afford saying what you would give up to afford it.
- Choose one "keep tinkering" item and write its first pull request as a plan: files, test, how you would prove it works.
- Write the three questions you would ask of your N1 Grafana on a quiet Sunday morning, and the panel that would answer each.

Next: the [Roadmap](Roadmap.md), which says what is built and what is planned. Back to the [Reading order](Reading-Order.md).

Build status: the cloud-side pieces (the telemetry stack with every flag off, the opt-in node exporter, the Wazuh agent and auditd) are written and described in the [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md). Nothing in them is applied.
