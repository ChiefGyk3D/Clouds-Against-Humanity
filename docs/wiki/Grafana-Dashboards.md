# Grafana dashboards: the three this repository ships

> **Unverified draft: written from the design, none of these dashboards has been imported into a live Grafana or run against real data.** The queries are checked for shape by `tests/test_dashboards.py` (valid JSON, data sources as variables, no real address, a `site` variable on each) and for nothing else. Metric names for the Twingate connector come from [Twingate's connector metrics page](https://www.twingate.com/docs/connector-metrics) as read on 2026-10-17; node exporter names are the standard ones; Wazuh field names are marked UNVERIFIED panel by panel. Sources: the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) sections 3.2 and 5, and the [connector telemetry findings](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-17-twingate-connector-telemetry-findings.md).

**Prerequisites:** [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) and [Multiple sites and identity](Multiple-Sites-and-Identity.md).

The repository keeps its own dashboards as JSON files in [`dashboards/`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/dashboards). They are modelled on the maintainer's home SIEM dashboards in layout and panel style only; no query, data source or label value was copied from them. Dashboards that are files in git can be reviewed, tested and rebuilt, which is the same reason the infrastructure is code.

## What is in the box

| Dashboard | File | uid | Data source | Answers |
|---|---|---|---|---|
| CAH: Sites overview | `cah_sites_overview.json` | `cah-sites-overview` | Prometheus | Is each site reachable, is collection healthy, and how much connector traffic goes direct versus through a relay? |
| CAH: Droplet health | `cah_droplet_health.json` | `cah-droplet-health` | Prometheus | Is each droplet healthy: CPU, memory, swap, disk, network, uptime? |
| CAH: Wazuh agents | `cah_wazuh_agents.json` | `cah-wazuh-agents` | OpenSearch (the Wazuh alerts index, plus the monitoring index for one panel) | Are the agents connected, and is anyone logging in or changing files they should not? |

Every dashboard is tagged `cah`, has a stable uid and title, and has two variables that work together:

- **`site`**: multi-select, with "All". It lists the `site` label values (the telemetry label `site_name`, for example `site-tor1`). A second site appears in the list by itself; nothing in the dashboard names a site.
- **`instance`**: multi-select, filled from the `instance` label of the chosen sites. In the design `instance` is the one host label every panel uses, so a host reused in two sites cannot merge (design section 3.2).

The Prometheus panels filter on `job="twingate-ztna"`, `site=~"$site"` and `instance=~"$instance"`, the job the home Prometheus uses for the cloud targets ([target file shape](Stage-2-Home-Side-Runbook.md#5-the-target-file-shape)).

Data sources are variables too (`DS_PROMETHEUS`, `DS_OPENSEARCH`, `DS_OPENSEARCH_MONITORING`). The files contain no data source uid, no URL and no address; when you import, Grafana asks you which of your own data sources to use, or you pick it from the dropdown at the top of the dashboard.

## How to import

1. In Grafana, open Dashboards, New, Import, and upload one JSON file from `dashboards/`. Repeat for the others.
2. Choose the folder. The uid is fixed, so importing again replaces the same dashboard instead of making a copy.
3. Open the dashboard. At the top, pick your Prometheus (or OpenSearch) in the data source dropdowns, then choose a site.
4. Or provision from files: point a Grafana dashboard provider at a folder holding these files. Nothing in them needs editing first.

If a dropdown at the top is empty, the data source variable found no data source of that type. Add the data source first (type Prometheus, or the OpenSearch plugin's type).

## Sites overview, panel by panel

- **Targets up per site.** One number per site: how many scrape targets answered the last scrape. A site showing 0 is sending no metrics, so every other panel for it is empty. Compare it with how many targets you expect. *Why it matters:* this is the first thing to look at after a change.
- **Targets down per site.** How many targets answer as down now. Above 0 means a connector, its exporter or the path to it has a problem. A site whose series vanished completely does not show here at all; that case needs the expected-target alerts from [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md#up-up--0-and-a-missing-series), not a panel.
- **Targets that are not up.** A table of every down target with its site and instance. Empty is good.
- **Target state per instance.** A green and red timeline. Red bars show when a target stopped and for how long. The node exporter port and the connector metrics port of one host share an instance name in the design's target file, so a row can hide which of the two failed; read the table above it.
- **Scrape duration.** How long Prometheus took to fetch each target. A slow or growing line means the path or the exporter is struggling.
- **Samples scraped.** How many samples each target returned. A sudden drop means the exporter answers but exports almost nothing, which a plain up check calls healthy.
- **Connector inbound traffic by path** and **outbound traffic by path.** Bytes per second through each connector from `twingate_inbound_bytes_total` and `twingate_outbound_bytes_total`, split by the `transport` label Twingate documents (`direct` or `relay`).
- **Share of traffic through a relay.** Relay bytes divided by all bytes per site. High is not an outage; it usually means a firewall or NAT stops direct connections and latency is higher. It shows no data when no bytes moved.
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
- **Agent status and last keepalive.** Reads a Wazuh monitoring index (`name`, `status`, `lastKeepAlive`). Those names are remembered from the Wazuh 4.x series, not read from this project's manager, and newer Wazuh releases may no longer write that index. It needs its own data source, which is why `DS_OPENSEARCH_MONITORING` exists. If it shows nothing, that is the first suspect.
- **Agents reporting** and **Last alert seen per agent.** Built on `agent.name` and `@timestamp`, which are standard in the alerts index. They count agents that *spoke*, so a connected but quiet agent is missed. The last-alert table is a stand-in for a keepalive, not a replacement.
- **SSH events, Failed logins, Sudo events and the recent-alerts table.** Use the stock rule groups `sshd`, `authentication_failed` and `sudo` (`rule.groups`). Whether the connector's login lines reach those rules depends on the agent reading the journal, which the stage 2 logging design marks UNVERIFIED. On a droplet with no public SSH, failed logins should be near zero.
- **File integrity events under /etc/twingate**, with its recent-events table. Use `rule.groups:syscheck` and `syscheck.path`, `syscheck.event`, the fields the Wazuh file integrity module writes. The design lists `/etc/twingate` among the watched paths; the agent configuration that watches it is not built.

## What is NOT verified

- Nothing was imported into a live Grafana, so the panel layout, colours and units have never been seen rendered. Expect to nudge them.
- No query was run against a Prometheus or OpenSearch. Syntax was reasoned, not executed. `promtool` and a fixture of two sites with two hosts each (design section 3.2) are the right next check and are not written.
- `schemaVersion` is 41, the version Grafana 12.0 is believed to write (not checked against a live install). Grafana migrates older versions on import; whether a later 12.x writes a higher number was not checked.
- The Twingate metric names and the `transport` label values are from Twingate's own page. Whether connector labels reach Prometheus is not documented, which is why `site` and `instance` come from the target file, not from the connector.
- The target file in the runbook gives the node exporter and the connector metrics port of one host the same `instance` label. Two targets of one job with identical labels can produce duplicate series, which has not been tried here. Check it before relying on the up panels, and if it happens, add a distinguishing label such as `role` to the target file.
- The Wazuh points above.
- Dashboards import with the data source you pick, so a Prometheus that scrapes other jobs is fine: every query filters on the job.

## Screenshots

No picture is committed. The [screenshots policy](Screenshots-Policy.md) allows synthetic demo dashboards only, and the synthetic two-site demo lab does not exist yet.

> **Screenshot to take yourself:** the Sites overview dashboard in your own Grafana, with two sites selected.
> Capture: the top of the dashboard with the site and instance dropdowns open and the three status panels in frame, from a demo Prometheus you fed with made-up series.
> Look for: one number per site in the up and down panels, and the red bars in the state timeline lining up with a target you stopped on purpose.
> Redact: the Grafana address and tab strip, your user name and avatar, real site, host and instance names, and any address that is not in a documentation range.

> **Screenshot to take yourself:** the Wazuh agents dashboard in your own Grafana after you set the site label on a test agent.
> Capture: the failed logins panel and the file integrity panel after you caused one failed login and touched a file under the watched path on a test machine.
> Look for: a bar in each panel at the time of your test, labelled with your test agent's name.
> Redact: the Grafana address and tab strip, your user name, real agent names and addresses, and any user name that appears in a recent-alerts table.

## Try it yourself

- Before importing, predict what the "Targets down per site" panel shows for a site with two healthy targets, then for one whose scrapes all fail, then for one that has been removed from the target file.
- Import Sites overview against a Prometheus with a fake `twingate-ztna` job and add a second site by editing the target file only. Did the dashboard need a change?
- Change one panel's data source variable to a name that does not exist and read the error. Then run `python -I -m pytest tests/test_dashboards.py` and find which rule would catch it.

Next: [Roadmap](Roadmap.md). Back to the [Reading order](Reading-Order.md).
