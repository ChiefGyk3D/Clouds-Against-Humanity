# Stage 2: Telemetry (skeleton, everything off)

Design: [2026-10-16 settings layer, multi-site telemetry and the mini cloud SOC](../superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md), step 4 of section 7.

## 1. What this stage builds

`stacks/20-telemetry` is one stack per site. It creates only Twingate objects, in two groups that are each switched on by their own flag. **Both flags default to false, so a fresh stack plans zero resources.** Nothing here has been applied, and nothing is applied until you decide to.

| Flag | Creates when true | Where |
|---|---|---|
| `logging_enabled` | One Twingate service, `telemetry-<resource_key>-logging`, and one Twingate resource per `logging_servers` element, named `logging-<resource_key>-<name>`, each limited to its one port and protocol | Resources live in the home remote network (`home_remote_network_id`) |
| `metrics_enabled` | One Twingate service, `telemetry-<resource_key>-scrape`, and one resource per `scrape_allowlist` entry per connector, named `scrape-<resource_key>-<entry>-<a or b>` | Resources live in the site's cloud remote network (`cloud_remote_network_id`) |

Cost: $0.00. `cost.json` lists no resources, and the cost gate requires the file to exist anyway. Phase id `stage-2`, planned, proposed ceiling $30 (the reference environment adds $0; see [cost](../cost.md#ceilings-per-phase)).

What it does **not** do yet: it creates no firewall rule, no droplet, no agent, no exporter and no service key. Service keys are issued out of band, one per host, so no key is ever in state (design section 2.8). Metrics need an exporter on the connectors (step 5 of the design) and logs need an agent (step 7), so enabling a flag today only creates the Twingate side.

Outputs: `scrape_targets` (sensitive; empty unless metrics are on) and `site_identity` (site label, region, provider, agent group, labels). The scrape targets carry private connector addresses, so the output is hidden in plan and run logs. The home logging addresses are in no output, name or tag.

## 2. Settings

Every variable is typed, validated and listed in [the settings reference](../wiki/Settings-Reference.md) (generated from `docs/settings.json`). `terraform.tfvars.example` shows the shape with documentation-range values and both flags false.

- `resource_key` builds names and is **immutable** for the life of the stack: changing it replaces every object. Use the same value as the site's stacks 00 and 10. Empty means the region.
- `site_name` is a telemetry label only (the `site` field of the outputs). It is in no resource name or tag, and changing it replaces nothing.
- `logging_servers` is private: the real list comes from the site's Doppler config as JSON (`TF_VAR_logging_servers`) or the Spacelift stack environment, never from a committed file. The address may be an RFC 1918 address, a documentation-range address (accepted so the example is valid; it is not routable, so a real deployment that leaves one in place fails at the connector) or a host name. A public IPv4 literal is refused.
- `metrics_port_connector` has **no default**. The connector's metrics bind port and address are not verified, so test them on one connector before enabling metrics. When `metrics_enabled` is true the plan fails until the port is set.
- **The connector side is stack 10, not this stack.** Twingate exposes metrics only when `TWINGATE_METRICS_PORT` is in each connector's `connector.conf` (connector v1.80.0 or later; plain HTTP at `/metrics`; the listen address is not documented). That is the stack 10 variable `connector_telemetry.metrics_port`, and it should equal `metrics_port_connector` here. Setting it changes `user_data`, so the access stack plan shows each connector REPLACED. Roll it out one connector at a time with `connector_telemetry_instances` (`["a"]`, apply, SSH through Twingate to the new connector, then `["a", "b"]`), and only then enable `metrics_enabled` here. Details and sources: the [connector telemetry findings](../superpowers/specs/2026-10-17-twingate-connector-telemetry-findings.md).
- `node_exporter_port` should equal `node_exporter.port` in stack 10, and `metrics_port_connector` should equal `connector_telemetry.metrics_port` there. The two stacks are separate, so nothing links the values; keep them in step by hand. Stack 20 refuses `9100` as `metrics_port_connector` (kept for the node exporter), the same rule stack 10 applies, so the two stacks cannot disagree about it.

### 2.1 Metrics on the connectors (stage 2 step 5, issue #99)

**Status: written and mock-tested only. Nothing here is applied, and none of it has run on a real machine.**

Three opt-in settings in stack 10 (`stacks/10-access`) switch on the cloud side of metrics. All three default to off, and with the defaults the plan is a no-op (the golden `user_data` hashes in the bootstrap tests prove the cloud-init is byte-identical):

| Setting | What it does | Replaces droplets? |
|---|---|---|
| `node_exporter = { enabled = true, port = 9100 }` | Installs `prometheus-node-exporter` from the Ubuntu archive. A systemd drop-in replaces the package's `ExecStart=` with a wrapper (`/usr/local/sbin/cah-node-exporter-run`) that, at every start, picks the first RFC 1918 address and `exec`s the exporter with `--web.listen-address=<private IPv4>:<port>`; it exits non-zero when there is none, so the exporter then does not start. Nothing depends on the order systemd reads files in. It never falls back to a wildcard address. With `host_firewall` on, the port is allowed from `host_firewall_ssh_sources` | **Yes**: `user_data` changes, so each connector in `node_exporter_instances` is REPLACED. Roll out `["a"]`, check SSH through Twingate and the memory headroom of the 1 GB droplet, then `["a", "b"]` |
| `node_exporter_instances` | Which connectors get it (default both) | n/a |
| `metrics_source_tag = "<tag>"` | The connector firewall gains one inbound rule per enabled metrics port (the node exporter port and `connector_telemetry.metrics_port`, including the previous value during a rollout), `source_tags = [<tag>]`, through the firewall module's `inbound_from_other_tags`. No address-sourced rule, no public source. Empty (default) adds no rule | No, a firewall change only |

What the tests prove (`tofu test` with mocked providers, plus `tests/test_metrics_firewall.py`, `tests/test_node_exporter_script.py`): the inbound rules equal the expected list of `(protocol, port, source tag)` triples (a new inbound rule is a visible diff), no inbound rule can name an address, a tag with nothing enabled opens nothing, metrics enabled with no tag opens nothing, and the bind script fails closed on a machine with no private address.

What is **not** known or **not** done:

- **The Twingate connector's metrics bind address is UNVERIFIED.** Twingate documents the port (`TWINGATE_METRICS_PORT`) and no bind setting. The firewall rule above is the boundary either way. Test `ss -ltnp` on one connector before relying on anything else.
- The node exporter has no authentication. Its only protection is the cloud firewall tag rule and, if on, the host firewall.
- The telemetry tag is **not created by this repository**: the stack that creates the scraping droplets owns it, and the tag must exist before the rule can apply. Until then leave `metrics_source_tag` empty.
- Design section 4.2 also lists tag-to-tag rules for the connector tag itself (a Twingate session can be routed through either connector, so connector a may open the connection to connector b's metrics port). This change does **not** add them: it admits the telemetry tag only, as the issue asks. If the scrape path turns out to be connector to connector, that is a follow-up (own-tag inbound and outbound rules for the two metrics ports) and must be reviewed on its own.
- The AWS stack (`stacks/aws/10-access`) uses security groups, not this firewall module, so issue #99 is not done there. The bootstrap module already supports the node exporter (it is cloud-neutral), but the AWS connector module and stack do not pass it through yet.
- The `awk` and `ip` based address pick, the systemd drop-in (`ExecStart=` reset to the wrapper) and the order of package install against `write_files` are reasoned from the documentation and the unit file of the Ubuntu package, and tested only as text and with a fake `ip`. They need a first boot on one connector.
- `connector_private_ips` is the access stack's `connector_private_ips` output (keys `a` and `b`). Passing a map through a Spacelift stack dependency is not verified: supply it as a JSON value in the stack environment if it does not work.
- `cloud_remote_network_id` is not an output of stack 10 today. Copy it from the Twingate console (the remote network `access-<resource_key>`) until a later step adds the output.

### 2.2 Dashboards

The repository ships three importable Grafana dashboards in [`dashboards/`](../../dashboards/): a sites overview, droplet health and Wazuh agents, all with `site` and `instance` variables and data sources as variables. They expect an `endpoint` label on every scrape target and a `cah_expected_targets` inventory (see the runbook sections 5 and 6). They are checked for shape by `tests/test_dashboards.py` and are **not** imported into a live Grafana or run against real data. What each panel shows and what is unverified: [Grafana dashboards](../wiki/Grafana-Dashboards.md).

## 3. Your manual steps (nothing here is automatic)

1. **Verify the Twingate plan limits for services before enabling anything. UNVERIFIED.** The design needs one service per site per role (two per site) and the Twingate services page documents no plan limit either way. Check your plan in the Twingate console or with Twingate support, and record the date here: `Verified on:`. If the plan cannot hold the count, stop and choose between upgrading, fewer sites or a written downgrade (design section 3.4). Do not share one service between sites to get around it.
2. **Create the Spacelift stack locked, with the `cah` label.** Name it `cah-20-telemetry`, root `stacks/20-telemetry`, OpenTofu, autodeploy off, label `cah`, then lock it. The label attaches the existing `cah-doppler` context (and the push policy, if it carries `autoattach:cah`); without the label or an explicit attachment the first tracked run fails in `before_init` because `DOPPLER_TOKEN`, `DOPPLER_PROJECT` and `DOPPLER_CONFIG` are missing, even with both flags false. Attaching the credentials does not by itself protect them from branch-controlled hooks: attach the push policy as well, following [the push policy instructions](../spacelift-secrets.md#9-the-push-policy) (section 8 there explains why). The entry in `.spacelift/config.yml` asks for `TWINGATE_API_TOKEN` and `TWINGATE_NETWORK` only. For a second site the stack id becomes `cah-20-telemetry-<resource_key>` with its own `stacks/sites/` manifest (design section 3.3).
3. **Set the per-site inputs as explicit Spacelift environment variables.** The hooks export only the two Twingate names, and `cah_doppler_env` exports only its explicit arguments, so values placed in Doppler alone are not delivered. Until Doppler mappings exist, set these on the stack as `TF_VAR_*` environment variables (mark the private ones secret/write-only): `TF_VAR_region`, `TF_VAR_logging_servers` (a JSON list), `TF_VAR_home_remote_network_id`, `TF_VAR_cloud_remote_network_id`, `TF_VAR_connector_private_ips` (a JSON map), and the flags. If you prefer Doppler, add the secrets there and extend the hook line in `.spacelift/config.yml` (both `before_init` and `before_apply`, identical) using the mapping syntax from [the secrets guide](../spacelift-secrets.md), for example `TF_VAR_logging_servers=LOGGING_SERVERS`; the secret-separation test then needs the new names added to its explicit shared-name list (`SHARED_NAMES` in `tests/test_secret_separation.py`) and `docs/settings.json` needs matching `secrets` entries. A per-site Doppler config (design section 2.7) is the target.
4. **Map the access stack's outputs.** Add a dependency on `cah-10-access` for `connector_private_ips` if a map works, otherwise set it by hand. `region` comes from stack 00 as for stack 10.
5. **First run.** Unlock, trigger a tracked run, and read the plan. With both flags false it must show no changes. Only then, one flag at a time, set it in the stack environment, read the plan, and confirm. A value that is private must render as `(sensitive value)`.

## 4. Verify

1. `tofu plan` with both flags false shows `No changes`.
2. With a flag on, the plan creates exactly the objects in the table above and nothing else.
3. The plan shows no home address in any resource name.
4. `python3 -I scripts/cost_check.py --root .` still reports the same total.

## 5. Rollback

Set the flags back to false and apply: the Twingate objects are destroyed and nothing else is touched. To remove the stack, destroy `cah-20-telemetry` (only this site's telemetry paths go; stacks 00 and 10 are untouched), then delete the Spacelift stack. Revoke any service key issued for these services in the Twingate console.

## 6. What the tests prove

- Both flags false (and the defaults) plan zero resources, even with every other input set.
- With a flag true the plan holds exactly the expected Twingate objects, named from `resource_key` and never from `site_name`.
- No resource name or output holds the private logging address; the connector addresses appear only in the sensitive `scrape_targets`.
- Each validation rejects its bad input (duplicate or address-shaped names, public addresses, bad ports, protocols and purposes, unknown label keys, and so on), and each precondition stops a flag that is missing its inputs.
- A source test pins the resource list, so a new resource without a flag gate fails.

## 7. Verification after an apply (every item is "not run yet")

Nothing in stage 2 is applied, so **every check below is marked `not run yet`**. Change a mark to a dated result only when you have run the command and read the output. All checks are read-only: none changes a stack, a firewall, an agent or a rule. Addresses and names are placeholders from the documentation ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and `example.com`; replace them with your own, and keep your real values out of this file, issues and pull requests.

Three facts are **UNVERIFIED** and change what a pass looks like, so settle them first. The connector's metrics bind address is not documented: test it on one connector before relying on the metrics checks. Whether the Wazuh agent can read journald on the version your manager runs is not known: if it cannot, the log checks pass only for file sources such as `/var/log/auth.log`. The Twingate plan limit for services is not documented either (section 3, step 1).

Order matters. The home side must be in place first: [the home-side runbook](../wiki/Stage-2-Home-Side-Runbook.md) holds the firewall prerequisite, and the log checks do not start until its negative reachability record exists (design section 4.1).

### 7.1 Metrics

| # | Check | Status |
|---|---|---|
| M1 | Prometheus lists every expected target as up | not run yet |
| M2 | The up count per site equals the expected-target inventory | not run yet |
| M3 | A node exporter and a connector metrics sample are readable through Twingate | not run yet |

**M1. Prometheus lists the targets up.** Run from any machine that can reach the home Prometheus:

```
curl -fsS 'http://prometheus.example.com:9090/api/v1/targets?state=active' | jq -r '.data.activeTargets[] | select(.labels.site == "site-tor1") | [.labels.site, .labels.instance, .labels.endpoint, .scrapeUrl, .health] | @tsv'
```

Pass: one line per expected target, each ending in `up`. For one site with two connectors and two exporters per connector (node exporter and connector metrics) that is **four lines**, told apart by the `endpoint` label (`node-exporter` or `connector-metrics`), which every scrape target must carry because the two endpoints of one host otherwise produce identical series (see [the target file shape](../wiki/Stage-2-Home-Side-Runbook.md#5-the-target-file-shape)). A `down` line with a timeout in `lastError` points at the firewall pair (design section 4.2), the Twingate resource or the home headless client, in that order. Fewer lines than expected means the target file is missing an entry.

**M2. The count matches the inventory.** The inventory is a recorded metric (`cah_expected_targets`), so one query compares both sides:

```
curl -fsS --get 'http://prometheus.example.com:9090/api/v1/query' --data-urlencode 'query=cah_expected_targets{site="site-tor1"} - on(site) count by (site) (up{site="site-tor1"} == 1)' | jq -r '.data.result[] | [.metric.site, .value[1]] | @tsv'
```

Pass: the value is `0` for each site. A positive number is how many targets are missing; no row at all means the inventory has no entry for that site, or no target is up (the inventory is only as current as its last generation, design section 3.5).

**M3. Samples are readable.** From a machine with a Twingate client that holds the scrape resources (the home Prometheus host's headless client, or an operator allowed to see them):

```
curl -fsS http://192.0.2.21:9100/metrics | head -n 5
```

Pass: lines beginning `# HELP` from the node exporter. Repeat with the connector metrics port you set in `metrics_port_connector` (plain HTTP at `/metrics`), for both connectors. The endpoints are unauthenticated (UNVERIFIED), so the exposure is bounded only by the resource list: a port that is not in `scrape_allowlist` must not answer.

### 7.2 Logs

| # | Check | Status |
|---|---|---|
| L1 | The agent service is active on the host | not run yet |
| L2 | The manager lists the agent as Active | not run yet |
| L3 | A test event produces an alert, recorded with identifiers removed | not run yet |

**L1. The agent is active on the host.** Through Twingate, using the SSH resource:

```
ssh operator@192.0.2.21 'systemctl is-active wazuh-agent'
```

Pass: the single word `active`.

**L2. The manager lists it.** On the manager (the docker form is shown; use your own container name, or run the binary directly on a package install):

```
docker exec wazuh-manager /var/ossec/bin/agent_control -l
```

Pass: one line per cloud host with status `Active`, named `<site_name>-<role>-<a or b>` (for example `site-tor1-connector-a`). Run it again a minute later: a status that flips to `Disconnected` is not a pass. The agent group is the primary grouping; whether labels are searchable in the indexer is UNVERIFIED.

**L3. A test event and its alert.** Create one harmless authentication failure on a connector from the operator machine (an invalid user over SSH, through Twingate):

```
ssh -o BatchMode=yes -o ConnectTimeout=10 no-such-user@192.0.2.21 true
```

Then read the newest alert for that agent on the manager:

```
docker exec wazuh-manager sh -c "grep 'site-tor1-connector-a' /var/ossec/logs/alerts/alerts.json | tail -n 1" | jq '{rule: .rule.id, level: .rule.level, description: .rule.description, agent: .agent.name}'
```

Pass: an alert exists with a timestamp after the test, from the agent you tested. Record **the alert's text with identifiers removed**: replace addresses, user names, host names and the agent name with placeholders before pasting it anywhere. If no alert arrives, check the source first: the invalid-user line is in `/var/log/auth.log` and in journald, and the agent reads journald only if it supports it (UNVERIFIED). The rule ids are the manager's stock rules until the journald rule file exists in the home repository.

### 7.3 From outside, and for the live stacks

| # | Check | Status |
|---|---|---|
| X1 | No inbound rule has an address source | not run yet |
| X2 | Zero open ports on each connector's public address, from outside | not run yet |
| X3 | The plan is a no-op for stacks 00 and 10 | not run yet |
| X4 | The plan for stack 20 matches its flags | not run yet |

**X1. No inbound rule has an address source.** Read-only, with `doctl` authenticated by a read-only token:

```
doctl compute firewall list --output json | jq '[.[].inbound_rules[]? | select((.sources.addresses // []) | length > 0)] | length'
```

Pass: `0`. After the metrics step the firewalls do carry inbound rules, sourced only from tags (design section 4.2); an address source of any kind, including `0.0.0.0/0` or `::/0`, fails. The field names are written from the shape of `doctl`'s JSON and are not checked against any installed version.

**X2. Zero open ports from outside.** From a machine that is not in the VPC, scan **only a connector you own**, at the public address `doctl` shows for it. Do not point a scanner at anything else. Until the read-only check in the [zero-open-ports design](../superpowers/specs/2026-10-17-zero-open-ports-check-design.md) is built (issue 91), this is the manual form:

```
nmap -Pn -p- --max-retries 1 --host-timeout 30m 203.0.113.10
```

Pass: every port is `filtered` (no answer), none `open` and none `closed`. A `closed` port means something answered with a reset, which that design counts as a failure of the silence criterion. A scan from a network that drops outbound probes proves nothing, so repeat it from a second network.

**X3. The plan is a no-op for stacks 00 and 10.** Stage 2 adds no resource to either stack, so a saved plan of each must change nothing. The plan reads live state, so use the credentials the tracked run uses. In `stacks/00-foundation`:

```
tofu plan -out=plan.tfplan && tofu show -json plan.tfplan > plan.json && python3 -I ../../scripts/plan_noop_check.py --plan plan.json --golden ../../docs/golden-addresses/00-foundation.json
```

And in `stacks/10-access`:

```
tofu plan -out=plan.tfplan && tofu show -json plan.tfplan > plan.json && python3 -I ../../scripts/plan_noop_check.py --plan plan.json --golden ../../docs/golden-addresses/10-access.json
```

Pass: the checker exits 0 and `tofu plan` reported no changes. Delete `plan.json` afterwards, because it holds `user_data` with connector tokens (`*.tfplan` and `plan.json` are git-ignored). In Spacelift the same check is the tracked-run plan: anything but "no changes" for these stacks is discarded.

**X4. Stack 20 matches its flags.** In `stacks/20-telemetry`:

```
tofu plan -detailed-exitcode
```

Pass with both flags false: exit code `0` (nothing to do). With one flag on and not yet applied: exit code `2`, and the plan lists exactly the objects in the table in section 1. After that flag is applied, a second plan returns `0`.
