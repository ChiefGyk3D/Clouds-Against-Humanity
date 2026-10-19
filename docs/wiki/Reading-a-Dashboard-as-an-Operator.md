# Reading a dashboard as an operator

> **Unverified draft: written from the design, none of stage 2 has been built or applied.** Sources: the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) sections 3.2 and 3.5 (2026-10-16). There is no cloud dashboard, no real target inventory and no production alert rule file in this repository. The synthetic [monitoring lab](Lab-Demo-Monitoring-Stack.md) does carry an inventory, two alert rules and the `promtool` fixtures this page describes, in `labs/demo-monitoring/`; they are checked against invented data only, not against a real deployment. Metric names marked "Prometheus convention" are general Prometheus knowledge and were not checked against this project's exporters.

**Prerequisites:** [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) and [Multiple sites and identity](Multiple-Sites-and-Identity.md).

A dashboard is a set of answers to questions somebody thought of in advance. Reading one as an operator means asking the opposite: **what question is this panel actually answering, and what would it look like if the answer were bad?** Most bad dashboards fail quietly. They look fine because the thing that would have made them look bad is missing.

## Overview panels and per-instance panels

| | Overview | Per instance |
|---|---|---|
| Question | "Is any site in trouble?" | "Which machine, and what is it doing?" |
| Grouping | `by (site)` | `by (site, instance)` |
| Reader | Anyone glancing | The person who already knows something is wrong |
| Failure mode | Averages and sums hide one bad machine | Legends and rows multiply with every host |

The design groups host panels by the pair `(site, instance)` so a host name reused in two sites cannot merge. Every Prometheus panel filters on `{site=~"$site", instance=~"$instance"}`, with a `site` variable (multi-select, with "All") and an `instance` variable that depends on it. The dashboards are provisioned from files, so the same JSON can install into a cloud Grafana, with the datasource name as a variable.

**Scale test.** A legend with one entry per host has `sites x hosts per site` entries. Two sites with two connectors each is 4. Ten sites is 20, and a line chart with twenty lines is unreadable. Past a handful, a panel must aggregate or show only the worst few.

## Three ways a panel hides a problem

1. **It averages.** Two connectors, one at 100 percent CPU and one idle, average 50 percent. The panel says "fine". The same happens to an `up` series: the mean of 1 and 0 is 0.5, which looks like "mostly up" and means "one is down".
2. **It sums.** Total bytes out across all hosts stays flat when one host stops and another doubles.
3. **It shows nothing.** A panel with no series displays "No data". That reads as an absence of bad news. It is the same picture whether nothing is wrong or the thing that measures it is dead.

The third is the dangerous one. A healthy dashboard and a dashboard whose collector died can look the same.

## `up`, `up == 0` and a missing series

Prometheus records a synthetic series called `up` for every target it tries to scrape: 1 if the scrape succeeded, 0 if it failed. That gives three situations, and they are different:

| What happened | What the series looks like | What catches it |
|---|---|---|
| The target answers | `up` is 1 | Nothing, correctly |
| The target is in the inventory but a scrape fails (host down, tunnel down, port closed) | The series **exists** with value 0 | A test for `up == 0` |
| The target is **not in the inventory at all** (the site was never added, or the file was changed) | **No series.** Nothing exists to compare | Only something that knows what *should* exist |

A series that stops being written also disappears from queries after a short window (Prometheus marks it stale). A whole site that vanishes leaves no series to group by.

### Why `absent()` fails here

`absent(up{job="twingate-ztna"})` is true only when **no** series for that job exists anywhere. With two sites, one healthy site keeps the job's series alive, so the expression stays false while the other site is gone. It also cannot say *which* site is missing, because once every series for that site is absent, there is no label left to report. And a site whose scrapes all fail does not disappear at all; its series simply read 0, so `absent()` stays false and only a test for `== 1` catches it.

### The expected-target inventory

The design's fix is to record what should exist and compare. A generator turns the telemetry stack's output (the list of targets it created) into two files for the home side: the scrape target file, and a rule file that records the expected number of targets per site as a metric. Then two alert conditions, evaluated at home so they do not depend on the cloud path:

- **Silent:** a site has an expected count but **no** healthy target. The rule is "expected count, unless a count of healthy targets exists for the same site".
- **Degraded:** a site has fewer healthy targets than expected.

Those two rules are design text, not code in this repository. The point to take away is in the structure: **a count of what is there is compared with a number written down earlier**. No rule in the design uses `absent()` on the job.

Written down as a limitation: the inventory is only as current as the last time it was generated. A site added in the cloud but not in the inventory is never alerted on, and removing a site is a reviewed change to generated data, not an event that fires.

## The fixture, described

`promtool test rules` reads a YAML file of synthetic time series and a list of expected alerts, and checks a rules file against them without a running Prometheus. The design's fixture is **2 sites x 2 hosts**, with these scenarios. The runnable version is in `labs/demo-monitoring/prometheus/tests/` (see the [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md)).

| # | Scenario | Series for `site-a` | Series for `site-b` | Expected |
|---|---|---|---|---|
| 1 | All healthy | both hosts `up` = 1 | both hosts `up` = 1 | No alert |
| 2 | One host down at one site | one host 1, one host 0 | both 1 | Degraded for `site-a` only |
| 3 | A whole site's series missing, the other healthy | none | both 1 | Silent for `site-a` only; nothing for `site-b` |
| 4 | A site removed from the inventory | none | both 1 | No alert (which is why removal is a reviewed change) |
| 5 | Every target of a site down (scrapes fail) | both hosts 0 | both 1 | Silent for `site-a` |

Scenario 5 is the one that surprises people: the series still exist, so the failure is not "absent", and the rule has to test for healthy targets rather than for the presence of any series.

You do not need Prometheus to practise this. Draw the table on paper, write the expected count per site, and for each scenario count the healthy targets per site by hand. If expected minus healthy is zero for a site, nothing fires; if healthy is zero (including "there is no row"), it is silent; otherwise degraded.

## Reading rates and latency

Most metrics from exporters are **counters**: a number that only goes up (bytes sent since boot, requests since start). The raw value is rarely useful. What you want is the **rate**: how fast it is growing.

- A rate is a difference over a window, per second. If a counter for bytes sent went from 100,000,000 to 109,000,000 in 60 seconds, the rate is 9,000,000 / 60 = 150,000 bytes a second, which is 1,200,000 bits a second, 1.2 Mbit/s.
- The window needs at least two samples in it. With a scrape interval of 15 seconds (the design's default for `scrape_interval_seconds`), a window shorter than about two intervals can hold fewer than two samples, and in practice windows are several times the interval so one missed scrape does not blank the graph.
- A counter resets to zero when the process restarts. Rate functions know that and do not show a huge negative spike. The connectors reboot on a schedule (04:00 and 05:00 Eastern, per the [Twingate page](Twingate.md#two-connectors-not-one)), so expect a dip in `up` and a counter reset on those mornings. An alert that waits several minutes before firing (the design's rules wait 5) does not page for a reboot.
- Prometheus convention: node exporter names its counters with a `_total` suffix, for example network bytes received and transmitted. The connector's own metrics (bytes in and out, split into direct and relay, plus uptime) are the ones this project cares about. Twingate's documentation (read 2026-10-16) names them `twingate_inbound_bytes_total` and `twingate_outbound_bytes_total` with a `transport` label, and `twingate_connector_uptime_seconds`.

**Latency** is a distribution, not a number. If 90 requests take 10 ms and 10 take 1,010 ms, the mean is (90 x 10 + 10 x 1,010) / 100 = 110 ms, a figure no request experienced. The median is 10 ms and the 95th percentile is 1,010 ms. Dashboards show percentiles (p50, p95, p99) for that reason; a percentile comes from a **histogram**, a counter per time bucket. Connectors and exporters here do not produce request latency. Black-box checks (an uptime check that probes from outside) would, and the design says an uptime tool is for black-box checks while Grafana is for metrics.

## What a silent site looks like

Put the pieces together. Site B's tunnel is down. What does the operator see?

- **Overview "up versus expected" stat:** if built on the inventory, it reads 0 of 2 for site B and turns red. If built on `count(up == 1)` alone, site B has no series and the panel shows no data for it, or omits it.
- **Host panels:** the `instance` variable for site B may list nothing, because the variable is built from series that stopped. The panel is empty.
- **Averages across sites:** they quietly become averages over fewer sites.
- **Logs:** the agent also depends on a tunnel, so logs from site B stop too. Nothing is wrong in the log view, which just has fewer lines.

The lesson is the one the detection page ends on: the number nobody has is how long it takes for anything to tell you a sensor has gone quiet. A "last seen" age per site is the cheapest way to have that number.

## Predict, then check

1. Three panels: (a) mean CPU across all hosts; (b) a stat showing `count(up == 1)` for the whole job; (c) a table of `up` per instance. Site A has two hosts, one of which is down. Which panel fails to show a problem?
2. Sites go from 1 to 10, two hosts each. What happens to a legend with one entry per host?
3. Using the 2 x 2 table above, what fires in scenario 3, and why could `absent()` on the job not have told you?
4. Every scrape of site A's targets fails from 04:00 to 04:12 because of a tunnel problem. The alert rules wait five minutes before firing. Does anything fire? Separately: one connector reboots on schedule and is unreachable for a while. What decides whether that pages?
5. Which view would still look healthy while the collector for a site is dead?
6. A counter went from 4,200 to 5,100 in 30 seconds. What is the rate?

<details>
<summary>Reference answers</summary>

1. (a) fails: one down host barely moves a mean of CPU readings (a host that is down may not even contribute a reading). (b) shows the count drop by one but does not say which host. (c) names the instance. Only (c) answers "which".
2. It grows from 4 entries to 20. Twenty lines are hard to read. Aggregate by site, or show only the worst few.
3. Silent for `site-a` only. `absent()` on the job is false because `site-b` keeps the job's series alive, and it could not name a site anyway.
4. Yes: both targets read 0 for 12 minutes, longer than the 5-minute wait, so the Silent condition fires for site A. For one scheduled reboot, only one target is down, which is the Degraded condition. It pages only if the reboot keeps the connector unreachable for longer than the wait. How long a reboot actually takes is something to measure, not assume. If it exceeds the wait, lengthen the wait or suppress Degraded in the reboot window; the design specifies neither, so test your choice with the fixture.
5. The log view: fewer lines looks like a quiet system. Any panel built only from the series that still exist (an average over the surviving sites, a legend with fewer entries) behaves the same way.
6. (5,100 - 4,200) / 30 = 30 per second.

</details>

## Try it yourself

- **On paper.** Add a sixth fixture scenario: site B has one healthy target and its other is missing from the inventory. What should fire?
- Open any Grafana dashboard you have access to and, for three panels, write what the panel would show if its data source died.
- Decide which "last seen" age would worry you for a connector, and write the alert in words: threshold, who is told, what they do first.
- When the telemetry step exists in your copy, write the fixture file for the five scenarios and make the rule file pass it. Then delete the rule's `== 1` and watch scenario 5 fail.

- **Run it.** The [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md) runs the repository's Grafana dashboards, both alert rules and the fixtures below on your laptop, with a `silent-site` command that does scenario 5 to a live Grafana.

![The sites overview with site-tor2 silent: a red 0 up and 4 down for site-tor2, a table listing its four endpoints and target-state bars that turned red](images/demo-sites-overview-silent.png)

*A silent site on the lab's synthetic dashboard, a few minutes after `silent-site site-tor2`. Grafana 12.1.0 and Prometheus 3.5.0 from the lab's own containers, captured 2026-10-19. All data is the lab's synthetic generator output; nothing in it is real.*

Next: [Build your own mini SOC](Build-Your-Own-Mini-SOC.md). Back to the [Reading order](Reading-Order.md).
