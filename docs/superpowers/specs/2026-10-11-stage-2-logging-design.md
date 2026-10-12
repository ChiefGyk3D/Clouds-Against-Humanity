# Clouds Against Humanity: Stage 2 Logging, Metrics and the Link Home

Status: DRAFT for review. Date: 2026-10-11.
Tooling: OpenTofu throughout; where this document or a conversation says "Terraform", read OpenTofu.
Scope: stage 2 only. It builds on stages 0 and 1 (built) and is a prerequisite for stage 3 (the workload host feeds the same pipeline). Nothing here is applied. The cloud cost is $0 (section 8), so the cost gate needs no new line, but every other change goes through the usual plan, review and confirm.

## 1. Purpose

Everything in the cloud should be visible from the SIEM that already watches the homelab. Today the two Twingate connector droplets are a blind spot: nobody sees their logs or their throughput. Stage 2 gives the SIEM two things from every cloud host:

- **Metrics**: Prometheus on the home side scrapes the cloud connectors, the same way it scrapes the on-prem Twingate connectors now (job `twingate-ztna`).
- **Logs**: the cloud hosts ship their logs to the home SIEM (Wazuh and OpenSearch), the same destination the on-prem connectors use.

No new log or metrics service is built in the cloud. The SIEM stays at home; the cloud only gets agents and narrow paths.

Success looks like:

- The cloud connectors appear on the existing Grafana Twingate dashboards next to the on-prem ones, with a `site` label to tell them apart.
- Wazuh has an agent per cloud host, and connector log events produce alerts through rules written for the journald log shape.
- Each path between cloud and home is its own Twingate resource, one port each, and a compromised droplet can reach exactly the SIEM ports it needs and nothing else.
- Stage 3's workload host joins by changing a variable, not by redesign.

Non-goals: a cloud-side Prometheus or log store, shipping to a SaaS, packet capture, and the stage 4 Grafana (that is a different stage; the dashboards here are the existing on-prem ones).

## 2. What exists at home (read from siem-docker-stack, 2026-10-11)

| Piece | How it works today |
|---|---|
| Connectors | Docker containers on Raspberry Pis |
| Metrics | `node_exporter` on port 9100 on each Pi; Prometheus scrapes it through a `file_sd` target file (gitignored, an example is committed) under job `twingate-ztna` |
| Logs | A Wazuh agent on each Pi reads the Docker JSON logs (`source=twingate-docker`) and sends to the manager on TCP 1514 (enrollment 1515 or 55000 depending on setup) |
| Detection | Wazuh rules 120700 to 120750 in `twingate_rules.xml`, written for the Docker log format |
| Dashboards | `twingate_ztna.json` and `siem_ztna_overview.json` in Grafana |
| Syslog path | syslog-ng on 514, then Logstash on 5045 into OpenSearch, and a copy to Wazuh on UDP 514 |

## 3. What the cloud connectors are

Per Twingate's documentation (connector monitoring and SIEM guide), read 2026-10-11:

- The cloud connectors install from apt and run under **systemd**, not Docker. Their logs go to **journald**.
- Log level is `TWINGATE_LOG_LEVEL` in `/etc/twingate/connector.conf` (default 3). `TWINGATE_LOG_ANALYTICS=v2` adds connection logs; the documentation does not confirm it for systemd installs, so section 9 lists it as to-verify.
- Metrics are enabled by `TWINGATE_METRICS_PORT` in the same file and served at `/metrics`: bytes in and out split into direct and relay, and uptime. The documentation says nothing about the bind address or authentication, so section 9 treats the endpoint as unauthenticated.

The differences from the on-prem setup are therefore the log source (journald, not Docker JSON) and the transport (the cloud and the home have no route to each other yet).

## 4. The link: Twingate in both directions

Stage 1 gave an operator laptop a way into the cloud (laptop client, cloud connectors). The SIEM needs two more directions, and Twingate expresses each as a resource behind a connector:

```
 METRICS  (home pulls from cloud)
   SIEM Prometheus host                         cloud connector droplets
   headless client, service account   ---->     resource: <private IP>:9100 and :<metrics port>
   (cloud remote network's connectors)

 LOGS     (cloud pushes home)
   cloud droplet                                home-logging connector (one per VLAN, section 4.0a)
   headless client, one service           ---->  resource: SIEM manager :1514 and :1515
   account per host (or per role)
```

Both need pieces that do not exist yet:

- **One home remote network per VLAN to be reached**, each with its own connector in that VLAN. A Twingate resource belongs to exactly one remote network, and its traffic leaves from a connector there, so this is also how the homelab's segmentation is carried to the cloud. The apps are segmented in the cloud the way they are at home.
- **Headless clients** (Twingate service accounts with keys) on the SIEM Prometheus host and on each cloud host. Each service account belongs to groups that see only the resources it needs.

### 4.0 Where each kind of segmentation is enforced

Everything between the cloud and home travels over Twingate; there is no other path. pfSense therefore sees only the home connector's IP as the source. A droplet, the workload host and the bridge all look identical to it, so pfSense cannot tell cloud hosts apart.

| Layer | Question it answers | Enforced by |
|---|---|---|
| Twingate groups and resource ACLs | *Who* (which cloud identity) may reach *which* host and port | Service account, group, resource. This is the identity-level RBAC. |
| pfSense on the connector's VLAN | *What can this connector reach at all*, if Twingate is misconfigured or the connector is compromised | Rules on the connector's source IP allowing only the listed host:ports, default deny |

Per-host separation inside a VLAN is Twingate's job alone. pfSense is a coarse backstop that caps the damage at one VLAN's allowed targets, which is the only reason for one connector per VLAN.

### 4.0a Home remote networks

| Remote network | Connector sits in | pfSense allows the connector to reach | Resources |
|---|---|---|---|
| `home-logging` | the logging/SIEM VLAN | SIEM manager 1514 and 1515 (and syslog 514 if the fallback in section 6.1 is used) | one resource per port |
| `home-ai` | the AI VLAN | the Ollama host on its API port (stage 3 uses it; default 11434) | one resource |

Two connectors per remote network if redundancy is wanted, with identical reachability. The VLAN IDs, the Ollama host and port and the SIEM addresses are the operator's to fill in (section 9, item 6); this repository does not record them.

### 4.0b Cloud service accounts

| Service account | Group | Resources | Used by |
|---|---|---|---|
| `cah-logging` | `cloud-logging` | SIEM 1514 and 1515 | the Wazuh agent on every cloud host |
| `cah-ai` | `cloud-ai` | Ollama API | the stage 3 workload host only |
| `prometheus-scrape` | `prometheus-scrape` | cloud connector metrics ports | the SIEM Prometheus host |

A headless client sees the union of its service account's groups, so a host that needs both logging and AI gets both groups and a compromise of that host reaches both. The connector droplets get `cah-logging` only; nothing in the access plane gets AI access. A future segment is a new remote network, group and service account, not a change to these.

### 4.1 Why pull for metrics and push for logs

- Prometheus pulls by design. Keeping that means no push gateway and no change to the existing dashboards and alert rules.
- Wazuh agents push to the manager by design. The agent connects out to 1514, which is the same direction the Pis use.
- The two directions are different resources and different service accounts, so losing or rotating one does not touch the other.

### 4.2 The cost of a headless client on the connector droplets

A droplet carrying a Twingate client as well as a connector is two Twingate roles on one host. The risk is one of blast radius: if the connector droplet is compromised, the attacker holds the client service key and can reach the SIEM's 1514 and 1515 and nothing else. That is equivalent to the Pis today (they also hold a path to 1514). Mitigations:

- The service account's group is bound to exactly two resources (ports 1514 and 1515 on the manager) and nothing else, enforced by Twingate; the home-logging connector's pfSense rules repeat the same two ports as a second layer.
- The key is shown once by Twingate, is held in Doppler and is rotated on the same cadence as the connector tokens.
- Wazuh agent keys are per host, so one agent being compromised does not expose another's enrollment.
- When stage 3's workload host exists, section 7 moves the client off the connectors onto one collector, so the access plane carries no client at all.

## 5. Metrics design

### 5.1 On the cloud hosts

- **Connector metrics**: add `TWINGATE_METRICS_PORT=<port>` to the connector config template (cloud-init). The port is a variable; the documented default is not assumed. To-verify (section 9): which address the listener binds to. If it binds to all interfaces, the DigitalOcean firewall already denies it from outside and the Twingate resource is the only way in; if the documentation or a test shows a bind option, bind to the private IP.
- **Host metrics**: install `prometheus-node-exporter` from the Debian or Ubuntu archive (as the on-prem Pis serve `:9100`) and bind it to the private IP with `--web.listen-address`. Nothing is exposed on the public interface; the connector firewall already denies public inbound.
- **Firewall**: the connector firewall has zero inbound rules from the Internet today. The metrics ports are reached from Twingate (outbound-initiated tunnel through the connector), so no inbound firewall hole is needed for them, the same reason SSH works through Twingate without opening port 22 publicly. The only firewall change in this section is none. To-verify: confirm in the plan that no `inbound_rule` is added.

### 5.2 Twingate resources (metrics)

Per droplet, two resources, each one address and one port, `tcp` only, UDP denied and ICMP off, following the same rule as the SSH resources:

| Resource | Address | Port | Group |
|---|---|---|---|
| `cah-tor1-connector-a-node-metrics` | connector a private IP | 9100 | `prometheus-scrape` |
| `cah-tor1-connector-a-twingate-metrics` | connector a private IP | the metrics port | `prometheus-scrape` |
| (same pair for connector b) | | | |

The `prometheus-scrape` group contains only the service account of the SIEM Prometheus host. Operators do not get these resources by default.

### 5.3 On the SIEM side

- A headless Twingate client runs on the host where Prometheus runs (or on a small sidecar container in the SIEM compose stack).
- A second `file_sd` file, `twingate-ztna-cloud.json`, lists the four targets with labels `site="cloud-tor1"`, `role="connector"`, and the existing `job: twingate-ztna`. The existing alert rules and dashboards select on the job label already.
- The `siem-docker-stack` change is a docs-and-example change in that repository (a new example target file, the `site` variable in the dashboard, and three panels for the Twingate-specific metrics). That is a separate pull request in that repository and this design only specifies it.
- Alert: absence of a cloud target for five minutes (the connector or its tunnel is down). A connector being down is also visible to Twingate; the metrics alert is the second opinion.

## 6. Log design

### 6.1 Choosing the transport

| Option | How | Pros | Cons |
|---|---|---|---|
| **Wazuh agent reading journald** | Install the Wazuh agent; `<localfile>` with `log_format` journald, query for the `twingate-connector` unit | Same agent, same manager, same rule engine as the Pis. Also gives FIM, SCA and rootcheck on the droplets for free, which serves "audit logging on the droplets" from the roadmap | Journald support depends on the agent version (to-verify, section 9) |
| journald `ForwardToSyslog` to syslog-ng | Forward to a remote syslog over TCP | Uses the syslog path that exists | Needs a syslog resource at home; loses Wazuh's host-level checks; plain syslog over a Twingate tunnel is fine but gives no per-host identity beyond the sender address |
| Vector | Reads journald, ships to OpenSearch or syslog | Very flexible; Twingate documents it | A new agent and a new pipeline to maintain; duplicates what Wazuh does |
| Twingate's S3 or Datadog export | Controller-side export | Zero host work | Twingate-controller events only (not connector logs), and sends data to a third party |

**Recommendation: the Wazuh agent.** It matches the on-prem pattern, covers more than the connector logs, and needs no new component at home. If the agent cannot read journald on the supported version, the fallback is `ForwardToSyslog` over a Twingate resource to syslog-ng on TCP 514, which lands in the same Logstash and Wazuh path.

### 6.2 What the agent collects

- journald: the `twingate-connector` unit; `sshd`; `sudo`; the cloud-init and unattended-upgrades units.
- Files: `/var/log/auth.log`, `/var/log/cloud-init-output.log`.
- Host checks from the agent defaults: file integrity on `/etc/twingate`, `/etc/ssh`, `/etc/sudoers.d`; SCA benchmark for the base OS.
- `TWINGATE_LOG_LEVEL` raised from 3 to 4 only if the extra volume is worth it; the default is kept unless a test shows connection logs are missing without it.

### 6.3 Detection

The existing rules 120700 to 120750 match the Docker JSON shape (`source=twingate-docker`). They do not match journald lines. Stage 2 adds a second rule file, `twingate_journald_rules.xml`, in a separate id range (120760 onward) so the two shapes cannot clash. The new rules cover the same events as the old ones where the connector emits the same message text:

- connector start, stop, restart, or crash loop;
- authentication failure to the controller (an expired or revoked token);
- relay fallback (direct connection failed, traffic going through a relay);
- new SSH login and `sudo` use on a connector (which should be rare; the user is the only admin).

This is a change in `siem-docker-stack`, tested there with `wazuh-logtest` using lines captured from the real droplets. Capturing real lines is a prerequisite, so no rule is written before the droplets have run for a few days.

### 6.4 Agent enrollment and secrets

- The manager address and the enrollment secret come from Doppler into cloud-init, never into the repository, matching how the connector tokens are handled (the user-data-contains-secrets caveat from stage 1 applies, and a better path is in section 9).
- The agent name is `cah-<region>-connector-<a|b>` so it is stable across rebuilds. A rebuilt droplet re-enrolls; the old agent entry is removed by the operator or by Wazuh's inactive-agent cleanup.

## 7. Droplet audit logging and the stage 3 host

- Stage 1 left "audit logging on the droplets" for this stage. The Wazuh agent plus `auditd` with a short rule set (identity and sudo changes, writes to `/etc/twingate`, and `execve` is not enabled because of its volume) covers it.
- When stage 3's workload host arrives, it takes the same cloud-init fragment (agent, node exporter, client) through a shared module input. The connectors' headless clients then move to one collector, so the access plane no longer carries a client. This design keeps the log-and-metrics fragment as one reusable cloud-init template so that move is a variable, not a rewrite.

## 8. Cost

| Item | Monthly |
|---|---|
| Wazuh agent, node exporter, headless client on the existing droplets | $0 |
| Twingate service accounts and resources | $0 if the plan allows them (to-verify, section 9) |
| Home connector on a VLAN | $0 cloud (runs on existing hardware) |
| Bandwidth | Negligible; logs and metrics are kilobytes per second, inside the droplet transfer allowance |

The approved stage 1 total stays $12 against the $30 ceiling. `docs/stages/approved.json` is unchanged, and the cost gate must still pass. Memory impact on the 1 GB connector droplets is the one real risk: the Wazuh agent (roughly 50 to 100 MB resident, est.) plus node exporter (about 20 MB, est.) plus the Twingate client could leave little headroom on `s-1vcpu-1gb`. This must be measured on one connector before the second is touched (section 10), and the fallback is a size bump, which would show in the cost gate as a deliberate approval.

## 9. Open questions and things to verify

Each of these changes the build, so each is a checked item rather than a guess.

1. **Metrics bind address and authentication.** The documentation is silent. Test on a connector: `ss -ltnp` for the listener and a curl from inside and outside the VPC.
2. **`TWINGATE_LOG_ANALYTICS=v2` on systemd installs.** Check that connection logs appear in journald after setting it.
3. **Wazuh agent journald support** in the version the manager runs. If it is absent, use the `ForwardToSyslog` fallback.
4. **Twingate plan limits** on service accounts, resources and remote networks. The free plan has limits; confirm before designing around several service accounts.
5. **Where the headless client key and the Wazuh enrollment secret live at boot.** Passing them in user-data is the accepted-risk path stage 1 already took for connector tokens (Terraform state and the DigitalOcean metadata endpoint both hold them). Better: cloud-init fetches them from Doppler at boot using a narrowly scoped, read-only service token. That needs the metadata-endpoint restriction on the roadmap, so it is an option rather than a requirement.
6. **Home side:** a connector per VLAN (logging now, AI for stage 3), the pfSense rules that let each reach only its listed host:ports, and the VLAN IDs, Ollama host and port. That is the operator's change, not this repository's.
7. **Rule shape:** collect real journald lines for a few days before writing rules.

## 10. Build order

Each step is its own pull request and is reversible. The first two are in this repository; the SIEM-side steps are in `siem-docker-stack` and are specified here, not built here.

1. **Docs only:** this design merged. (This PR.)
2. **Metrics on the cloud side:** cloud-init gains `TWINGATE_METRICS_PORT` and `prometheus-node-exporter` bound to the private IP, and the Twingate metrics resources and group are added in stack 20. Measure memory on connector a first; replace connector b only after a is healthy. Test: `tofu test` with mocked providers asserting the config lines, the resources, the group, and that no firewall inbound rule appears.
3. **Home side (operator):** home remote network, connector, VLAN and rules; Prometheus host headless client; the `file_sd` target file. Verify the four targets are up in Prometheus.
4. **Logs on the cloud side:** the Wazuh agent and `auditd` fragment, the headless client and its service account with the two-port resource. Test as in step 2. Verify an agent shows as active on the manager.
5. **Rules and dashboards in `siem-docker-stack`:** journald rules from captured lines, `site` variable and three panels, the absence alert.
6. **Lessons and wiki:** Twingate and Architecture pages updated, the roadmap stage 2 marked done, and a lesson per surprise.

Estimated effort at the operator's pace: about a week, in two weekend-sized pieces (metrics, then logs). Steps 3 and 6 need the operator's hands.

## 11. Known risks and decisions

| Risk | Decision |
|---|---|
| A compromised connector has a path to the SIEM | Two ports only, one service account per role, key held in Doppler, rotated with the connector tokens. Same exposure as the Pis. |
| Memory pressure on 1 GB droplets | Measure first on one droplet; size bump is an explicit cost-gate approval |
| Metrics endpoint is unauthenticated | Private IP bind where possible, no public inbound, reached only through a narrow Twingate resource for one service account |
| Rules written without real log lines | Capture first, write second; keep the Docker rules untouched |
| Twingate plan limits | Verified before step 2; the fallback is one service account for logs and one for metrics, which is already the minimum |
| Home connectors are new attack surface at home | One connector per VLAN, each reaching only its listed host:ports; Twingate groups carry the identity-level rules and pfSense keys on the connector as a backstop; the operator owns the pfSense change |

## 12. Changes this stage makes to the repository

New: `docs/stages/02-logging.md`, a reusable cloud-init fragment for the agent and exporter, the cross-site Twingate objects (home remote networks, resources, groups, service accounts) in a new stack 20, so the access stack stays small (recommended; the operator confirms), tests, wiki updates (Twingate, Architecture-Overview, Droplet-Hardening, Roadmap, Terraform-Reference), and a Lessons-Learned entry. Unchanged: `approved.json`, the cost gate, and the firewall inbound rules.
