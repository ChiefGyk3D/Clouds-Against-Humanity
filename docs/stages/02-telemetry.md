# Stage 2: Telemetry (skeleton, everything off)

Design: [2026-10-16 settings layer, multi-site telemetry and the mini cloud SOC](../superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md), step 4 of section 7.

## 1. What this stage builds

`stacks/20-telemetry` is one stack per site. It creates only Twingate objects, in two groups that are each switched on by their own flag. **Both flags default to false, so a fresh stack plans zero resources.** Nothing here has been applied, and nothing is applied until you decide to.

| Flag | Creates when true | Where |
|---|---|---|
| `logging_enabled` | One Twingate service, `telemetry-<resource_key>-logging`, and one Twingate resource per `logging_servers` element, named `logging-<resource_key>-<name>`, each limited to its one port and protocol | Resources live in the home remote network (`home_remote_network_id`) |
| `metrics_enabled` | One Twingate service, `telemetry-<resource_key>-scrape`, and one resource per `scrape_allowlist` entry per connector, named `scrape-<resource_key>-<entry>-<a or b>` | Resources live in the site's cloud remote network (`cloud_remote_network_id`) |

Cost: $0.00. `cost.json` lists no resources, and the cost gate requires the file to exist anyway.

What it does **not** do yet: it creates no firewall rule, no droplet, no agent, no exporter and no service key. Service keys are issued out of band, one per host, so no key is ever in state (design section 2.8). Metrics need an exporter on the connectors (step 5 of the design) and logs need an agent (step 7), so enabling a flag today only creates the Twingate side.

Outputs: `scrape_targets` (sensitive; empty unless metrics are on) and `site_identity` (site label, region, provider, agent group, labels). The scrape targets carry private connector addresses, so the output is hidden in plan and run logs. The home logging addresses are in no output, name or tag.

## 2. Settings

Every variable is typed, validated and listed in [the settings reference](../wiki/Settings-Reference.md) (generated from `docs/settings.json`). `terraform.tfvars.example` shows the shape with documentation-range values and both flags false.

- `resource_key` builds names and is **immutable** for the life of the stack: changing it replaces every object. Use the same value as the site's stacks 00 and 10. Empty means the region.
- `site_name` is a telemetry label only (the `site` field of the outputs). It is in no resource name or tag, and changing it replaces nothing.
- `logging_servers` is private: the real list comes from the site's Doppler config as JSON (`TF_VAR_logging_servers`) or the Spacelift stack environment, never from a committed file. The address may be an RFC 1918 address, a documentation-range address (accepted so the example is valid; it is not routable, so a real deployment that leaves one in place fails at the connector) or a host name. A public IPv4 literal is refused.
- `metrics_port_connector` has **no default**. The connector's metrics bind port and address are not verified, so test them on one connector before enabling metrics. When `metrics_enabled` is true the plan fails until the port is set.
- **The connector side is stack 10, not this stack.** Twingate exposes metrics only when `TWINGATE_METRICS_PORT` is in each connector's `connector.conf` (connector v1.80.0 or later; plain HTTP at `/metrics`; the listen address is not documented). That is the stack 10 variable `connector_telemetry.metrics_port`, and it should equal `metrics_port_connector` here. Setting it changes `user_data`, so the access stack plan shows each connector REPLACED. Roll it out one connector at a time with `connector_telemetry_instances` (`["a"]`, apply, SSH through Twingate to the new connector, then `["a", "b"]`), and only then enable `metrics_enabled` here. Neither stack opens a firewall port for it: the connector firewall also needs tag-sourced rules for the metrics port. Details and sources: the [connector telemetry findings](../superpowers/specs/2026-10-17-twingate-connector-telemetry-findings.md).
- `connector_private_ips` is the access stack's `connector_private_ips` output (keys `a` and `b`). Passing a map through a Spacelift stack dependency is not verified: supply it as a JSON value in the stack environment if it does not work.
- `cloud_remote_network_id` is not an output of stack 10 today. Copy it from the Twingate console (the remote network `access-<resource_key>`) until a later step adds the output.

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
