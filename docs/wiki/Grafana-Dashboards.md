# Grafana dashboards: the three this repository ships

> **Partly verified against a synthetic lab only: the two Prometheus dashboards have been loaded into a Grafana with invented data, and none of the three has been imported into a real home Grafana or run against real data.** `tests/test_dashboards.py` checks structure (valid JSON, allowed panel types, a grid position, a ref id and a query on every panel, data sources as variables, no real address or host name, a `site` variable on each). The [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md) adds two sites with two connectors each, and `tests/test_demo_monitoring.py` asserts that every Prometheus panel query uses only metrics the lab's generator exports. The Wazuh dashboard is not in the lab and stays unverified. Metric names for the Twingate connector come from [Twingate's connector metrics page](https://www.twingate.com/docs/connector-metrics) as read on 2026-10-17; node exporter names are the standard ones; Wazuh field names are marked UNVERIFIED panel by panel. Sources: the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) sections 3.2 and 5, and the [connector telemetry findings](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-17-twingate-connector-telemetry-findings.md).

**Prerequisites:** [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) and [Multiple sites and identity](Multiple-Sites-and-Identity.md).

The repository keeps its own dashboards as JSON files in [`dashboards/`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/dashboards). They are modelled on the maintainer's home SIEM dashboards in layout and panel style only; no query, data source or label value was copied from them. Dashboards that are files in git can be reviewed, tested and rebuilt, which is the same reason the infrastructure is code.

## What is in the box

| Dashboard | File | uid | Data source | Answers |
|---|---|---|---|---|
| CAH: Sites overview | `cah_sites_overview.json` | `cah-sites-overview` | Prometheus | Is each site reachable, is collection healthy, and how much connector traffic goes direct versus through a relay? |
| CAH: Droplet health | `cah_droplet_health.json` | `cah-droplet-health` | Prometheus | Is each droplet healthy: CPU, memory, swap, disk, network, uptime? |
| CAH: Wazuh agents | `cah_wazuh_agents.json` | `cah-wazuh-agents` | OpenSearch (the Wazuh alerts index, plus the monitoring index for one panel) | Are the agents connected, and is anyone logging in or changing files they should not? |

Every dashboard is tagged `cah`, has a stable uid and title, and has two variables that work together (plus one extra on the Wazuh dashboard, below):

- **`site`**: multi-select, with "All". It lists the `site` label values (the telemetry label `site_name`, for example `site-tor1`). A second site appears in the list by itself; nothing in the dashboard names a site.
- **`instance`**: multi-select, filled from the `instance` label of the chosen sites. In the design `instance` is the one host label every panel uses, so a host reused in two sites cannot merge (design section 3.2).

The Prometheus panels filter on `job="twingate-ztna"`, `site=~"$site"` and `instance=~"$instance"`, the job the home Prometheus uses for the cloud targets. They also **require an `endpoint` label on every scrape target**, `node-exporter` or `connector-metrics`: the two endpoints of one host share job, site and instance, so without it their `up` and `scrape_*` series would collide. Panels group and label by `(site, instance, endpoint)`, and the droplet panels read only `endpoint="node-exporter"`, the connector panels only `endpoint="connector-metrics"`. The sites overview also reads the expected-target inventory `cah_expected_targets` (one series per site, counting endpoints). Both are specified in the [target file shape and inventory](Stage-2-Home-Side-Runbook.md#5-the-target-file-shape) and neither is built in this repository.

Data sources are variables too (`DS_PROMETHEUS`, `DS_OPENSEARCH`, `DS_OPENSEARCH_MONITORING`). The files contain no data source uid, no URL and no address; the files have no `__inputs` section, so the import screen does **not** ask you to map them. After import you pick your own data sources from the dropdowns at the top of the dashboard.

## How to import

1. In Grafana, open Dashboards, New, Import, and upload one JSON file from `dashboards/`. Repeat for the others.
2. Choose the folder. The uid is fixed, so importing again replaces the same dashboard instead of making a copy.
3. Open the dashboard. Import does not ask which data source to use: at the top of the dashboard, pick your Prometheus (or OpenSearch) in the data source dropdowns, then choose a site. Until you do, panels show no data.
4. Or provision from files: point a Grafana dashboard provider at a folder holding these files. Nothing in them needs editing first.

If a dropdown at the top is empty, the data source variable found no data source of that type. Add the data source first (type Prometheus, or the OpenSearch plugin's type).

## Sites overview, panel by panel

- **Targets up per site.** One number per site: how many scrape endpoints answered the last scrape. The query starts from the expected-target inventory, so a site whose targets are all down or gone still shows, as 0, instead of disappearing. Without the inventory a fully silent site cannot be listed, because nothing is left to name it. *Why it matters:* this is the first thing to look at after a change.
- **Targets down per site.** Expected endpoints minus endpoints that are up, so an endpoint that vanished counts as down, not only one that reads 0. Above 0 means a connector, an exporter or the path to it has a problem. Without the inventory the panel falls back to counting series that read 0, which cannot see a vanished site; the alerts in [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md#up-up--0-and-a-missing-series) remain the thing that pages you.
- **Targets that are not up.** A table of every down target with its site and instance. Empty is good.
- **Target state per instance.** A green and red timeline, one row per site, instance and endpoint. Red bars show when a target stopped and for how long; the endpoint in the row name says whether the node exporter or the connector metrics failed.
- **Scrape duration.** How long Prometheus took to fetch each target. A slow or growing line means the path or the exporter is struggling.
- **Samples scraped.** How many samples each target returned. A sudden drop means the exporter answers but exports almost nothing, which a plain up check calls healthy.
- **Connector inbound traffic by path** and **outbound traffic by path.** Bytes per second through each connector from `twingate_inbound_bytes_total` and `twingate_outbound_bytes_total`, split by the `transport` label Twingate documents (`direct` or `relay`).
- **Share of traffic through a relay.** Relay bytes divided by all bytes per site. Each direction is summed per site first and a missing direction counts as 0, so one absent series cannot silently drop a site. High is not an outage; it usually means a firewall or NAT stops direct connections and latency is higher. It shows no data when no bytes moved.
- **Connector uptime.** `twingate_connector_uptime_seconds`. A drop to zero is a connector restart, not a droplet reboot.

## Droplet health, panel by panel

All from the standard node exporter metrics (the opt-in exporter from stack 10, bound to the droplet's private address).

- **Uptime since boot**, **Memory used now** and **Fullest disk now.** Three quick gauges. The connector droplets are small, so memory and disk are the ones to watch before adding anything to one.
- **CPU busy.** One minus the idle share of CPU time, averaged over cores. Short spikes during updates are normal.
- **Memory used.** Percent in use (total minus available). A climb that never falls back suggests a leak.
- **Swap used.** Normally 0 or no data on these droplets. A rising line means memory is short.
- **Disk used by filesystem.** Percent used per mount point, with tmpfs, overlay and similar left out. The slope tells you how many days remain.
- **Network traffic.** Bytes per second received and sent, loopback and container interfaces left out.
- **Network errors and drops.** Should sit at 0. A steady line points at the network, not the application.

## Wazuh agents, panel by panel

Every panel here says UNVERIFIED in its description, and this section says what is unverified.

- **The site filter.** Wazuh alerts do not carry a Prometheus-style `site` label. These panels filter on `agent.labels.site`, which exists only if the agent configuration sets a label named `site`. No agent configuration in this repository does yet (the agent is a later stage 2 step). The `instance` variable is the agent name; the design names agents `<site_name>-connector-<a|b>` so the name itself also identifies the site. If your agents carry no label, edit the queries to filter on the agent name instead.
- **Agent status and last keepalive.** Reads a Wazuh monitoring index (`name`, `status`, `lastKeepAlive`). It does not use the `site` and `instance` variables, because those are built from alerts and so list only agents that have already raised one; a quiet or never-reporting agent could not be picked. It has its own `monitored_agent` variable, built from the monitoring index. Those names are remembered from the Wazuh 4.x series, not read from this project's manager, and newer Wazuh releases may no longer write that index. It needs its own data source, which is why `DS_OPENSEARCH_MONITORING` exists. If it shows nothing, that is the first suspect.
- **Agents reporting** and **Last alert seen per agent.** Built on `agent.name` and `@timestamp`, which are standard in the alerts index. They count agents that *spoke*, so a connected but quiet agent is missed. The last-alert table is a stand-in for a keepalive, not a replacement.
- **SSH events, Failed logins, Sudo events and the recent-alerts table.** Use the stock rule groups `sshd`, `authentication_failed` and `sudo` (`rule.groups`). Whether the connector's login lines reach those rules depends on the agent reading the journal, which the stage 2 logging design marks UNVERIFIED. On a droplet with no public SSH, failed logins should be near zero.
- **File integrity events under /etc/twingate**, with its recent-events table. Use `rule.groups:syscheck` and `syscheck.path`, `syscheck.event`, the fields the Wazuh file integrity module writes. The design lists `/etc/twingate` among the watched paths; the agent configuration that watches it is not built.

## What is NOT verified

- **Nothing was imported into a real home Grafana.** The Sites overview and Droplet health dashboards are mounted into the [lab's](Lab-Demo-Monitoring-Stack.md) Grafana 12.1.0 and the lab page carries screenshots of them rendered with invented data, so the layout has been seen there. Colours, units and behaviour against your own Prometheus and data are unchecked; expect to nudge them.
- **Queries have run only in the lab.** The lab's tests check that each Prometheus panel query names only metrics the generator exports; the committed `promtool` fixtures (2 sites x 2 hosts x 2 endpoints, `labs/demo-monitoring/prometheus/tests/`) test the two alert rules and the inventory, not the dashboard panels. That the panel PromQL returns correct numbers was judged from the lab's screenshots, not asserted by a test, and no query was run against a real Prometheus. No OpenSearch query of any kind was run, and the Wazuh dashboard is not in the lab.
- `schemaVersion` is 41, believed to be what Grafana 12.0 writes (not checked against a live install). The test treats 41 only as a structural floor, not as proof that a file imports; Grafana migrates older versions on import, and whether a later 12.x writes a higher number was not checked.
- The offline test checks panel types against an allowlist, grid positions, ref ids, and that every query uses a variable. It does not parse PromQL or Lucene.
- The Twingate metric names and the `transport` label values are from Twingate's own page. Whether connector labels reach Prometheus is not documented, which is why `site` and `instance` come from the target file, not from the connector.
- The `endpoint` label is a requirement these dashboards add to the target file shape. Without it the two endpoints of one host would produce identical series. That collision was reasoned, not reproduced in a Prometheus, and the dashboards were not run with the label in place either.
- `cah_expected_targets` is specified by the design and not built. The inventory must count scrape endpoints (four for a default two-connector site), the same unit as the `up` series; the design's earlier example value of 2 counted hosts.
- The Wazuh points above.
- Dashboards import with the data source you pick, so a Prometheus that scrapes other jobs is fine: every query filters on the job.

## Screenshots

Pictures of the Sites overview dashboard (healthy, and with one site silenced) are on the [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md) page and in [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md); they come from the lab's invented data, as the [screenshots policy](Screenshots-Policy.md) requires. No picture of the Wazuh dashboard is committed.

> **Screenshot to take yourself:** the Wazuh agents dashboard in your own Grafana after you set the site label on a test agent.
> Capture: the failed logins panel and the file integrity panel after you caused one failed login and touched a file under the watched path on a test machine.
> Look for: a bar in each panel at the time of your test, labelled with your test agent's name.
> Redact: the Grafana address and tab strip, your user name, real agent names and addresses, and any user name that appears in a recent-alerts table.

## Try it yourself

- Before importing, predict what the "Targets down per site" panel shows for a site with two healthy targets, then for one whose scrapes all fail, then for one that has been removed from the target file.
- Run the [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md), add a third site to `labs/demo-monitoring/prometheus/targets.json` and the inventory rules only, and reload. Did the dashboard need a change?
- Change one panel's data source variable to a name that does not exist and read the error. Then run `python -I -m pytest tests/test_dashboards.py` and find which rule would catch it.

Next: [Roadmap](Roadmap.md). Back to the [Reading order](Reading-Order.md).
