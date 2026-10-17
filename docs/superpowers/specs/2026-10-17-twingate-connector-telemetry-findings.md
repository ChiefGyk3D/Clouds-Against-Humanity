# Twingate connector telemetry: findings and what the code does

Date of the research: 2026-10-16 (pages fetched with curl and read as text the same day). Requested by the maintainer as "the CAH 10 Access layer needs to have twingate enable the logging telemetry". This note records what Twingate's own documentation says, what the Twingate Terraform provider offers, which assumptions of the [stage 2 design](2026-10-16-stage2-settings-and-mini-soc-design.md) are now verified or wrong, and what the code in this change does.

How to read it: **VERIFIED** means the quoted page says it, on the retrieval date. **UNVERIFIED** means no page read says it, or it is inferred. Nothing here was tested on a live connector: no connector was touched. Quotes are short and exact; everything else is paraphrase.

## Pages read

| Page | URL | Page footer says |
|---|---|---|
| Advanced Connector Management | https://www.twingate.com/docs/advanced-connector-management | updated 6 months ago |
| Connector Logging (real-time logs) | https://www.twingate.com/docs/connector-real-time-logs | updated 1 month ago |
| Connector Metadata | https://www.twingate.com/docs/connector-metadata | updated 5 months ago |
| Connector Health Checks | https://www.twingate.com/docs/connector-health-checks | updated 5 months ago |
| Connector Metrics Overview | https://www.twingate.com/docs/connector-metrics | updated 6 months ago |
| Deployment Automation | https://www.twingate.com/docs/deployment-semi-automation | updated 5 months ago |
| Complete metrics setup guide (linked from the metrics page) | https://www.twingate.com/docs/connector-monitoring | not shown |
| Connector Details | https://www.twingate.com/docs/connector-details | updated 6 months ago |
| Linux Deployment | https://www.twingate.com/docs/connectors-on-linux | updated 4 months ago |

The last three were not on the maintainer's list; the metrics page points at the monitoring guide for the setup, and the Linux page is the one for the package install this repository uses.

## Verified facts, by feature

### Service log level

- Env var `TWINGATE_LOG_LEVEL`. Levels: "Level 3 (default) - Basic connectivity and ERROR messaging", level 4 WARN, level 5 INFO, level 7 DEBUG. Each level includes the lower ones. No level 6 is documented.
- "The logging level is changed by updating `/etc/twingate/connector.conf` or changing the Docker configuration to include an environment variable". For systemd this is the config file. Restart is how the unit reloads it: "Restart the Connector service (eg. for configuration file reload)" (Linux page).
- Level 7 is "very verbose"; Twingate does not recommend it for long if the host has little log storage.
- No log format setting exists on these pages. Service logs go through the journal (`journalctl -u twingate-connector`). The repository's design assumed a "log format" knob would exist; it does not.

### Real-time connection logs (the "logging telemetry")

- Env var `TWINGATE_LOG_ANALYTICS`, value `v3`: "If the environment variable `TWINGATE_LOG_ANALYTICS` is set to `v3`, the Connector will output network connection logs".
- systemd: "you can add the line `TWINGATE_LOG_ANALYTICS=v3` to the file `/etc/twingate/connector.conf`".
- Transport: "local connection logs will be output to `stdout` in single-line JSON format", mixed with service logs; "you will need to filter for lines starting with `ANALYTICS`". For systemd they are read with `journalctl -u twingate-connector -n 100 -f`. Twingate's SIEM example is a Vector `journald` source with `include_units = ["twingate-connector"]`.
- Schema v3 fields in the example line: `connection` (id, client_ip, resource_ip, resource_port, protocol, rx, tx, duration, tunnel_path, tunnel_proto), `connector` (id, name), `device.id`, `event_type` (`established_connection`, `closed_connection`), `location` (geoip city, country, lat, lon), `relays`, `remote_network`, `resource` (address, id, applied_rule), `timestamp`, `user` (email, id).
- **Privacy consequence (derived from the schema, not stated by Twingate as a warning):** every line carries the user's email, client IP and a city-level location. Anything that ships the journal off the host (the Wazuh agent in the design) ships those.
- What must be enabled where: **nothing in the Admin Console and nothing in the provider.** The Linux page, step 3 of the generated install command, is "enable optional real-time logging", which only adds the variable to the command. It is purely a connector-side setting. (Inference from the page: no server-side toggle is described anywhere read.)
- Not documented: whether the Ubuntu journal is persistent on a cloud image. The design's "journald" source reads it; persistence is UNVERIFIED and is not changed by this work.

### Metrics

- Env var `TWINGATE_METRICS_PORT`. "Enable metrics on your Twingate Connectors by setting `TWINGATE_METRICS_PORT=9999`" (metrics page). Monitoring guide: "Any unused port can be used."
- Requires "Twingate Connectors (v1.80.0 or later)".
- systemd: "Edit the Connector configuration: `sudo nano /etc/twingate/connector.conf`; add metrics configuration: `TWINGATE_METRICS_PORT=9999`; restart the Connector service: `sudo systemctl restart twingate-connector`".
- Endpoint: the guide's check is `curl http://<connector-ip>:9999/metrics`, and Prometheus is configured with `metrics_path: /metrics`. Plain HTTP, no credential in the example, no authentication setting documented. So the endpoint is **unauthenticated plain HTTP on the connector's IP** as documented.
- Format: Prometheus text. Metric names shown: `twingate_inbound_bytes_total{transport="direct"}`, `twingate_outbound_bytes_total{transport="relay"}`, `twingate_connector_uptime_seconds`. The overview also lists "Resource counts" (no metric name given) and says more are coming.
- The guide's Docker example publishes the port (`ports: "9999:9999"`) and says "Ensure firewall allows access to port 9999 on Connectors".
- **Bind address: not documented.** No setting, no statement. The guide scrapes `<connector-ip>:9999`, which shows the port is reachable on a non-loopback address, but not which interfaces. UNVERIFIED.
- Dashboard: https://github.com/Twingate-Community/dashboards, `grafana/insights.json` (Grafana 12.2.1+). Not read.

### Health checks

- There is **no health-check port or endpoint and no setting.** It is a command. systemd: "Run `twingate-connectorctl health` to run a health check." Result: "will return `OK` and exit with status code 0 if completed successfully. Any other response or error with a nonzero exit code means the health check failed." Docker: built into the image (`docker ps`, `docker inspect`). Other containers: `connectorctl health` inside the container.
- "Health checks only return unhealthy if the Connector service is not running correctly. They do not check if network connectivity has been established to Twingate's infrastructure." So `systemctl is-active` is close to it, and neither proves the connector is online. The Admin Console (and the provider's `state` attribute, see below) says whether the controller sees it.

### Metadata and labels

- "Twingate supports adding custom metadata as key-value pairs to Connectors when deploying them." Env vars prefixed `TWINGATE_LABEL_`: `TWINGATE_LABEL_DEV_ENVIRONMENT=dev1` shows in the Admin Console as `Dev Environment: dev1`.
- The scripts Twingate generates preset `TWINGATE_LABEL_HOSTNAME` and `TWINGATE_LABEL_DEPLOYED_BY`. The two worked examples on the page are Docker and ECS Fargate (environment variables).
- **UNVERIFIED for systemd:** the page does not show `TWINGATE_LABEL_*` in `/etc/twingate/connector.conf` for the package install. The Linux page shows the file with three variables only. It is very likely the same mechanism (the unit reads the file as an environment file), but it was not confirmed. The change therefore renders the labels but the first live apply must check the connector page for them.
- Connector Details page: Twingate reports hostname, public IP, private IPs, uptime and downtime, time offset (tolerance "+/- 5 seconds") and STUN discovery to the Admin Console automatically; no setting.

### Deployment (apt package, tokens)

- Linux page: systemd service supported on Ubuntu 22.04 and 24.04 LTS (the repository uses 24.04). "You can find the Connector configuration file in `/etc/twingate/connector.conf`. The three environment variables ... must be set in the configuration file in order for the Connector service to start". Its example writes `TWINGATE_NETWORK=https://autoco.twingate.com`; this repository writes `TWINGATE_URL=https://<network>.twingate.com`, following Twingate's Terraform guide (see the template comment), and the live connectors work. The pages disagree with each other here; the repository's line is left alone.
- Deployment Automation page: tokens "are unique to that specific Connector, and these tokens cannot be reused for multiple Connectors"; "`TWINGATE_ACCESS_TOKEN` ... should be treated as a secret and never checked into source control." Consistent with the repository (tokens only in the 0600 `connector.conf`).
- No telemetry-related variable is Admin-Console-only. The Admin Console shows the result (labels, details, the connector's state) and its install-script generator adds the variables to the command.

## The Twingate provider (twingate/twingate 3.8.0, read with `tofu providers schema -json`)

- `twingate_connector` attributes: `name`, `remote_network_id`, **`status_updates_enabled`** (bool, optional and computed: "Determines whether status notifications are enabled for the Connector. Default is `true`."), and computed `hostname`, `id`, `private_ips`, `public_ip`, `state` (`ALIVE`, `DEAD_NO_HEARTBEAT`, `DEAD_HEARTBEAT_TOO_OLD`, `DEAD_NO_RELAYS`), `version`.
- `twingate_connector_tokens`: `connector_id`, `keepers`, computed `access_token`, `refresh_token`.
- `twingate_remote_network`: `name`, `location`, `type` only. No settings for logs, metrics or labels.
- Resources in 3.8.0: connector, connector_tokens, dns_filtering_profile, group, remote_network, resource, service_account, service_account_key, user. **No resource or attribute for connector logs, metrics, labels or health, and no notification-settings resource.** Those are configured only by connector environment variables.
- `status_updates_enabled` default is `true` in the provider, so the live connectors (which never set it) already have it on. The code therefore does **not send it while it is unset** (`optional(bool)`, null): the resource config stays exactly what it was, so the default plan cannot differ on this account. Only an explicit `true` or `false` is sent. Caveat: an optional and computed attribute that goes from set back to unset keeps its last value, so to undo a `false`, set it to `true` explicitly. What the notification does beyond the attribute's one-line description is not documented in what was read; the Notifications admin page was not fetched.
- `state` and `version` are readable data (also as data sources `twingate_connector` and `twingate_connectors`). Useful as a pre-flight (metrics need v1.80.0 or later; the weekly cron keeps the package current), not used by this change.

## Reconciliation with the stage 2 design

| Design statement | Where | Now |
|---|---|---|
| "Metrics port and bind address are still UNVERIFIED" | section 8, item 6 | **Port: verified** as `TWINGATE_METRICS_PORT` in `connector.conf`, any unused port, 9999 in Twingate's examples, path `/metrics`, connector v1.80.0 or later. **Bind address: still UNVERIFIED**, and there is no setting to choose it, so it is a thing to test, not to configure. |
| `metrics_port_connector` has "no default until the metrics port question is answered" | settings table | The mechanism is known, the value is still the operator's choice. The code makes it the operator's choice (`connector_telemetry.metrics_port`, unset by default). The planned `metrics_enabled`, `metrics_port_connector` entries of stack 10 in `docs/settings.json` overlap this setting; stack 20 should read `connector_telemetry.metrics_port` rather than add a second one. |
| Connector metrics are bytes in and out split direct versus relay, plus uptime | metrics sections, Reading a dashboard | **Verified**, with the metric names above. |
| Connector metrics endpoints are unauthenticated | trust-boundary table (UNVERIFIED) | **Effectively verified**: the documented check is an unauthenticated `curl` and no auth setting exists. |
| "The endpoints bind to the private address and are reachable only through the scrape service's resources" | Telemetry-Crosses-the-Trust-Boundary, answer 4 | **Not supported by the docs.** Twingate offers no bind setting. Treat the endpoint as listening wherever the connector listens, and make the cloud firewall (deny-all inbound, plus tag-sourced rules) the boundary. Corrected in that page. |
| A health check "port or endpoint" | request text | **Wrong.** It is the command `twingate-connectorctl health`, there is no port. Nothing is rendered for it. |
| A log "format" setting | request text | **No such setting.** Only `TWINGATE_LOG_LEVEL` (service) and `TWINGATE_LOG_ANALYTICS=v3` (connection logs, always single-line JSON). |
| Logs come from journald | design (Wazuh agent) | **Consistent**: connection logs and service logs both go to stdout and so to the `twingate-connector` journal unit, lines starting `ANALYTICS `. Add: they hold user emails and client IPs. |
| Twingate reaches the metrics ports so no inbound firewall change is needed | design section 5.1 draft | Already marked wrong in the design; unchanged. Metrics scraping across connectors needs tag-sourced rules (below). |
| Labels searchable and `site` label | design | Connector labels are shown in the Admin Console; whether they appear in any exported data is UNVERIFIED. |

## What the code does

One variable, `connector_telemetry`, in `modules/twingate-bootstrap`, passed through `modules/twingate-connector`, `modules/aws/twingate-connector`, `stacks/10-access` and `stacks/aws/10-access`. Default `{}`. All fields optional:

| Field | Default | Effect | Changes user_data |
|---|---|---|---|
| `status_updates_enabled` | unset (not sent) | `twingate_connector.status_updates_enabled` (provider) | No |
| `log_level` | unset | `TWINGATE_LOG_LEVEL=<3,4,5,7>` | Yes |
| `connection_logs` | `false` | `TWINGATE_LOG_ANALYTICS=v3` | Yes |
| `metrics_port` | unset | `TWINGATE_METRICS_PORT=<1024..65535, not 9100>` | Yes |
| `labels` | `{}` | `TWINGATE_LABEL_<KEY>=<value>`, sorted, at most 10 | Yes |

The two stacks add `connector_telemetry_instances` (list of `a` and `b`, default both) so the rollout can be one connector per plan; a connector not listed gets `connector_telemetry_previous` (default `{}`, nothing). For a later change to settings already on (say log level 5 to 7), put the old value in `connector_telemetry_previous`, the new one in `connector_telemetry`, and list `["a"]` first; otherwise the unlisted connector would lose its telemetry and be replaced in the same plan.

Validation: log level in {3, 4, 5, 7}; port a whole number from 1024 to 65535 and not 9100 (kept for the node exporter in the design); label keys `^[A-Z][A-Z0-9_]{0,31}$`; values `^[A-Za-z0-9._-]{1,64}$` (no spaces, quotes or line breaks, because they are written into a config file inside a YAML block). The health check has no input, as it has no setting. Because there is only one port, the "distinct ports" rule applies only against 9100.

The lines are rendered by one `${telemetry_conf}` placeholder directly after the three original lines of `connector.conf`. Disabled, it renders the empty string, so `user_data` is byte-identical: the golden hashes `3689d9b9...` (connector a, 04:00) and `de2de628...` (connector b, 05:00) are unchanged and pass in the module tests (a template hash proves the rendered text only, not a live plan), and the tests prove that taking the telemetry lines out of an enabled render gives the golden hash back. Tokens still appear only in the 0600 `connector.conf`.

No firewall or security-group rule is added. To scrape the metrics port later:

- Another host (a SOC droplet) needs the firewall module's `inbound_from_other_tags` on the connector firewall for the metrics port, plus `outbound_to_other_tags` on the scraper's firewall.
- The other connector (Twingate routes a session to either) needs the connector tag's own `inbound_from_tag_rules` and `outbound_to_tag_rules` for the metrics port, the same way port 22 is handled in `stacks/10-access/main.tf`.
- A Twingate resource in stack 20 (one address and one port per endpoint, as for SSH) is what makes the endpoint reachable from home.

## Plan impact when enabled

- Setting `log_level`, `connection_logs`, `metrics_port` or `labels` changes `user_data`. In `stacks/10-access` that replaces **both** `digitalocean_droplet.connector` (force-new `user_data`); in `stacks/aws/10-access` it replaces **both** `aws_instance.connector` (`user_data_replace_on_change = true`). The `twingate_connector` and `twingate_connector_tokens` are not replaced, so the connector identity and tokens stay. The droplet gets a new private IP, so the two `twingate_resource` SSH addresses update in place.
- Apply one connector at a time, with an SSH-through-Twingate health check between (`docs/wiki/Trace-One-Change-End-to-End.md`, variant C). Confirmation approves a whole saved plan, so the sequencing has to be in the plans themselves: the stacks have a second variable, `connector_telemetry_instances` (default `["a", "b"]`). Set `connector_telemetry` with `["a"]`, apply (one replace), check SSH to the new connector a, then set `["a", "b"]` and apply (one more replace). The other connector keeps the site up meanwhile.
- `status_updates_enabled` alone replaces nothing.
- Default in code is `{}`. Expected result of merging: a plan with no difference, because the rendered user_data text is identical and the resource config is unchanged. That is an expectation, not a proof: a template hash cannot show what the provider does against live state. Confirm with the saved plan in Spacelift before applying anything; any difference there is a bug to report, not apply.

## Not verified, to test on one connector first

1. The listening address of the metrics port (loopback, private or all interfaces).
2. That the package install reads `TWINGATE_LABEL_*` from `connector.conf`.
3. The live connectors' version is at least 1.80.0.
4. That the default plan is empty against live state (expected; confirm with the saved plan in Spacelift), and that an explicit `status_updates_enabled = true` is also a no-op.
5. Whether the Ubuntu journal is persistent, and how large connection logs grow at level 5 or 7.
6. What the `status_updates_enabled` notification actually sends and to whom.
