# Stage 2 home-side runbook: what you set up at home before the cloud sends anything

> **Status: design merged, cloud side in progress, nothing applied.** This page is an operator runbook written from the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) (sections 3.5, 4 and 4.1) and the [stage 2 logging design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-11-stage-2-logging-design.md) (section 4). Everything here happens on **your** network, in **your** firewall and in **your** Prometheus. Nothing in this repository can check it for you, so the page asks you to write the evidence down. Every address below is from a documentation range (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`); replace them with yours and keep your real values out of the repository, issues and pull requests.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Twingate](Twingate.md), [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) and [Networking basics for this project](Networking-Basics-for-This-Project.md).

The cloud half is the [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md). It builds Twingate objects only, behind two flags that default to off. The home half is this page. The order is fixed: **the firewall and its recorded negative tests come first.** No logging resource is applied until the record in section 3 exists (design section 4.1).

## Why two layers

Everything between the cloud and home travels over Twingate, so your firewall sees one source address: the home connector. A droplet, a later workload host and a compromised machine all look the same to it.

| Layer | Question it answers | Enforced by |
|---|---|---|
| Twingate resources and groups | Which cloud identity may reach which host and port | One resource per host and port, one service per role |
| Your firewall on the connector's VLAN | What the connector can reach at all, if Twingate is misconfigured or the connector is compromised | Rules on the connector's source address, only the listed host and ports, default deny |

Per-host separation inside a VLAN is Twingate's job alone. The firewall only caps the damage at one VLAN's allowed targets.

## 1. A dedicated connector VLAN

- Create one VLAN (or the equivalent isolated segment) per home remote network, and put that remote network's connector in it. One connector per VLAN: the connector sits in the segment of the things it reaches. For logging, that is the segment of the log manager.
- Give the connector a fixed address (a static lease or a static configuration). The firewall rules key on it, so a changing address silently moves the connector out from under its own rules.
- A second connector in the same VLAN is fine for redundancy, with an identical rule set.
- Record the VLAN id, the connector address and the manager address in your **private** notes. This repository does not store them.

## 2. The firewall allow-list: default deny

Rules are keyed to the connector's source address, allow **only** the listed host and ports, and end in a logged deny. The shape, with placeholders (the worked example uses the connector at `192.0.2.50`, the log manager at `192.0.2.10`, a management subnet `198.51.100.0/24` and a user subnet `203.0.113.0/24`):

| Order | Source | Destination | Port | Action |
|---|---|---|---|---|
| 1 | connector address (`192.0.2.50`) | log manager (`192.0.2.10`) | tcp 1514 | allow |
| 2 | connector address | log manager | tcp 1515 | allow |
| 3 | connector address | whatever the connector needs to reach Twingate, outbound | per Twingate's current documentation | allow |
| 4 | connector address | any | any | **deny, log** |

Notes:

- Row 3 must sit above the deny, or the connector goes offline. The exact outbound destinations and ports come from Twingate's own documentation at the time you build it, not from this page. If you use the syslog fallback (journald forwarded instead of an agent, only if the agent cannot read journald, which is UNVERIFIED), the manager also needs tcp 514 in the list; nothing else is added silently.
- Add a row only for a host and port you can name. A new row is a reviewed change, and it repeats the negative tests in section 3.
- The connector is not allowed to reach your management or user subnets at all. That is the point of the VLAN.

## 3. The recorded negative reachability tests

A rule you have not tested to fail is a rule you hope works. From the connector's address (or from a test host placed in the connector's VLAN with the same rules), try each connection below. **Every "must fail" row is expected to time out or be refused.** Run the set again after any rule change, and keep the filled table with your private notes; do not paste real addresses into the repository.

| # | From | To | Port | Expected | Result | Date | Tester | Rule set version |
|---|---|---|---|---|---|---|---|---|
| 1 | connector | `198.51.100.10` (management host) | tcp 22 | must fail | not run yet | | | |
| 2 | connector | `198.51.100.10` | tcp 443 | must fail | not run yet | | | |
| 3 | connector | `203.0.113.20` (user host) | tcp 445 | must fail | not run yet | | | |
| 4 | connector | `192.0.2.10` (log manager) | tcp 9200 (any port but 1514 and 1515) | must fail | not run yet | | | |
| 5 | connector | `192.0.2.10` | tcp 1514 | must work | not run yet | | | |
| 6 | connector | `192.0.2.10` | tcp 1515 | must work | not run yet | | | |
| 7 | connector | Twingate, outbound | as in row 3 above | must work | not run yet | | | |

A copy-paste form for each probe (a plain TCP connect with a short timeout, run on the connector or test host):

```
timeout 5 bash -c '</dev/tcp/198.51.100.10/22' && echo "OPEN" || echo "no connection"
```

Change the address and port for each row. `OPEN` on a must-fail row is a failed test: fix the rule, record the failure, and run the whole table again. Also read the firewall's deny log once: the failed attempts should appear there, which proves the deny rule is the one stopping them.

## 4. The headless client on the Prometheus host

Metrics are **pulled**: your Prometheus scrapes the cloud connectors through Twingate. That needs a Twingate headless client (a service account with a key, no interactive login) on the host that runs Prometheus, or on a sidecar in the same compose stack.

- The client belongs to the **scrape** service that stack 20 creates when `metrics_enabled` is on (`telemetry-<resource_key>-scrape`). That service sees only the scrape resources, one per `scrape_allowlist` entry per connector. It must not be the service used for logs.
- The key is issued in the Twingate console, once per host, and shown once. It is **never in the repository, in a tfvars file or in OpenTofu state**. Keep it in your secrets manager and rotate it on the same cadence as the connector tokens.
- Whether your Twingate plan allows the number of services this design needs (two per site, one per role) is **UNVERIFIED**: check it before creating anything (stage 2 guide, section 3, step 1).
- The connector's metrics bind address and the metrics endpoint's lack of authentication are **UNVERIFIED**. Test one connector first, and read the unauthenticated endpoint as open to anything that can reach the resource.
- Check from the Prometheus host that the client can fetch a sample from a connector (the first check in the stage 2 guide's verification section) before writing any target file.

## 5. The target file shape

Prometheus reads the cloud targets from a `file_sd` JSON file, kept next to your existing target files and listed under the scrape job named `twingate-ztna`, the job the on-prem Twingate targets use (the file carries no `job` label: Prometheus sets it from the job name). One entry per scrape endpoint. The label set is the same on every entry except `endpoint`, and `instance` is the one host label every panel and alert uses (design section 3.2). **`endpoint` is required**: the node exporter and the connector metrics of one host share `job`, `site` and `instance`, so without a label that tells them apart their `up` and `scrape_*` series would be identical and collide. Use exactly `node-exporter` or `connector-metrics`; the dashboards in this repository filter and group on it (`role` is taken: it names the host):

```json
[
  {
    "targets": ["192.0.2.21:9100"],
    "labels": {
      "site": "site-tor1",
      "region": "tor1",
      "provider": "digitalocean",
      "role": "connector",
      "instance": "site-tor1-connector-a",
      "endpoint": "node-exporter"
    }
  },
  {
    "targets": ["192.0.2.21:9101"],
    "labels": {
      "site": "site-tor1",
      "region": "tor1",
      "provider": "digitalocean",
      "role": "connector",
      "instance": "site-tor1-connector-a",
      "endpoint": "connector-metrics"
    }
  }
]
```

Repeat both entries for connector b (`192.0.2.22`). That is four entries, so four expected endpoints per site (the inventory in section 6 counts endpoints, not hosts). Notes:

- The address and port come from the stack 20 `scrape_targets` output (sensitive; read it with `tofu output -json scrape_targets`). The port `9101` here is only an example: your connector metrics port is the value you set for `metrics_port_connector`, which has no default and is never `9100` (node exporter keeps that).
- Port, label and `site` values are placeholders. `site` is the telemetry label `site_name` (default `site-<region>`), not the `resource_key` that names cloud objects.
- A generator that turns the output into this file is specified in the design and is **not built**. For a first site, write the file by hand and keep the real one out of git.
- Set `scrape_interval_seconds` to what you want (the design's default is 15). If your existing config labels hosts with another name such as `instance_name`, the relabel that maps it to `instance` should be tested with `promtool`, not copied from memory.

## 6. The expected-target inventory and its two alerts

`absent(up{job="twingate-ztna"})` is true only when **no** series exists for the job, so it cannot tell you a whole site went quiet while another site stays healthy. The design replaces it with an inventory of how many targets each site should have, recorded as a metric, and two alerts compared against it. The shape (design section 3.5; the numbers come from the stack 20 output):

```yaml
- record: cah_expected_targets
  expr: vector(4)
  labels: { site: "site-tor1", job: "twingate-ztna" }
```

```yaml
# a site with no healthy target at all
- alert: CloudSiteSilent
  expr: cah_expected_targets unless on(site) count by (site) (up{job="twingate-ztna"} == 1)
  for: 5m
# a site with fewer healthy targets than expected
- alert: CloudSiteDegraded
  expr: cah_expected_targets > on(site) count by (site) (up{job="twingate-ztna"} == 1)
  for: 5m
```

Here `vector(4)` is two connectors times two endpoints each; your number follows your target file. These expressions are **proposed, not yet tested**: the design requires `promtool test rules` fixtures of 2 sites by 2 hosts (all healthy; one host down; a whole site's series missing; a site removed from the inventory; every target `up == 0`) before they are trusted, and those fixtures belong in the home repository's change. Two limits to write into your own notes: the inventory is only as current as its last generation, so a site added in the cloud but not here is never alerted on; and removing a site is a reviewed change to this data, because a removed site raises no alert.

## 7. Done means evidence

You are finished with the home side when you hold, privately:

1. The filled table in section 3, all rows passing, with date, tester and rule set version.
2. The target file loaded, and the cloud targets listed as up in Prometheus once the cloud side is applied.
3. The inventory and both alerts loaded, with their `promtool` fixtures passing.

The cloud-side checks that prove the whole path (targets up, agent active, a test alert, zero open ports from outside, no-op plans for stacks 00 and 10) are in the [stage 2 guide's verification section](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md#7-verification-after-an-apply-every-item-is-not-run-yet), and each is marked `not run yet` until you run it.

Rollback: remove the cloud entries from the target file and reload Prometheus, delete the headless client's key in the Twingate console, and restore the previous firewall rules.

## What this page does not claim

- It does not claim any of this is built or applied. The cloud side is a skeleton that creates Twingate objects only, and the home side is yours.
- It does not claim your firewall is configured as shown; only the recorded tests in section 3 can say so.
- It does not describe the home SIEM repository's own changes (dashboards, journald rules, notes). Those are written only after the cloud side is applied and confirmed working.
- It does not record your VLAN ids, addresses, host names or tenant names. Every value above is a placeholder.

Next: [Grafana dashboards](Grafana-Dashboards.md), the importable dashboards for what you just set up. Then the [Roadmap](Roadmap.md), where stage 2 is tracked.
