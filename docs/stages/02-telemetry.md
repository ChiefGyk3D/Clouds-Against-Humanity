# Stage 2: Telemetry (skeleton, everything off)

Design: [2026-10-16 settings layer, multi-site telemetry and the mini cloud SOC](../superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md), step 4 of section 7.

## 1. What this stage builds

`stacks/20-telemetry` is one stack per site. It creates only Twingate objects, in two groups that are each switched on by their own flag. **Both flags default to false, so a fresh stack plans zero resources.** Nothing here has been applied, and nothing is applied until you decide to.

| Flag | Creates when true | Where |
|---|---|---|
| `logging_enabled` | One Twingate service, `telemetry-<resource_key>-logging`, and one Twingate resource per `logging_servers` element, named `logging-<resource_key>-<name>`, each limited to its one port and protocol | Resources live in the home remote network (`home_remote_network_id`) |
| `metrics_enabled` | One Twingate service, `telemetry-<resource_key>-scrape`, and one resource per `scrape_allowlist` entry per connector, named `scrape-<resource_key>-<entry>-<a or b>` | Resources live in the site's cloud remote network (`cloud_remote_network_id`) |

Cost: $0.00. `cost.json` lists no resources, and the cost gate requires the file to exist anyway. Phase id `stage-2`, planned, proposed ceiling $30 (the reference environment adds $0; see [cost](../cost.md#ceilings-per-phase)).

What it does **not** do yet: it creates no firewall rule, no droplet, no agent, no exporter and no service key. Service keys are issued out of band, one per host, so no key is ever in state (design section 2.8). Metrics need an exporter on the connectors (step 5 of the design) and logs need an agent (step 7, section 2.4: written but not applied, and without the Twingate headless client), so enabling a flag in this stack only creates the Twingate side.

Outputs: `scrape_targets` (sensitive; empty unless metrics are on), `site_identity` and `extra_site_identities` (the `sites` map, section 2.5) (site label, region, provider, agent group, labels). The scrape targets carry private connector addresses, so the output is hidden in plan and run logs. The home logging addresses are in no output, name or tag.

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
- The AWS half of issue #99 is described in section 2.3 below. Everything in this section is the DigitalOcean stack.
- The `awk` and `ip` based address pick, the systemd drop-in (`ExecStart=` reset to the wrapper) and the order of package install against `write_files` are reasoned from the documentation and the unit file of the Ubuntu package, and tested only as text and with a fake `ip`. They need a first boot on one connector.
- `connector_private_ips` is the access stack's `connector_private_ips` output (keys `a` and `b`). Passing a map through a Spacelift stack dependency is not verified: supply it as a JSON value in the stack environment if it does not work.
- `cloud_remote_network_id` is not an output of stack 10 today. Copy it from the Twingate console (the remote network `access-<resource_key>`) until a later step adds the output.

### 2.2 Dashboards

The repository ships three importable Grafana dashboards in [`dashboards/`](../../dashboards/): a sites overview, droplet health and Wazuh agents, all with `site` and `instance` variables and data sources as variables. They expect an `endpoint` label on every scrape target and a `cah_expected_targets` inventory (see the runbook sections 5 and 6). They are checked for shape by `tests/test_dashboards.py` and are **not** imported into a live Grafana or run against real data. What each panel shows and what is unverified: [Grafana dashboards](../wiki/Grafana-Dashboards.md).

### 2.3 Metrics on the AWS connectors (stage 2 step 5, issue #99, AWS half)

**Status: written and mock-tested only. Nothing is applied, no AWS account or Spacelift stack exists for this code, and the maintainer's check of Spacelift's native AWS integration is still open ([AWS stages 0 and 1](aws-access.md)). Do not assume it works.**

The same three opt-in settings exist in `stacks/aws/10-access`, with one difference: the source of the metrics rule is a security group, not a tag. All three default to off and the plan is then a no-op (golden `user_data` hashes in the AWS connector module tests, connector a and connector b).

| Setting | What it does | Replaces instances? |
|---|---|---|
| `node_exporter = { enabled = true, port = 9100 }` | Passed through `modules/aws/twingate-connector` to the shared bootstrap, which installs the exporter and binds it to the private IPv4 address only (section 2.1 describes the script). | **Yes**: `user_data` changes and the instance has `user_data_replace_on_change`, so each connector in `node_exporter_instances` is REPLACED, with its public address (there is no Elastic IP). Roll out `["a"]`, check SSH through Twingate, then `["a", "b"]` |
| `node_exporter_instances` | Which connectors get it (default both) | n/a |
| `metrics_source_security_group_id = "sg-..."` | The connector security group gains one inbound rule per enabled metrics port (the node exporter port and `connector_telemetry.metrics_port`, including the previous value during a rollout) whose source is that security group (`referenced_security_group_id`), through the AWS firewall module's `inbound_from_other_groups`. Never an address, an IPv6 range or a prefix list. Empty (default) adds no rule | No, a security group change only |

What the tests prove (`tofu test` with mocked providers, plus `tests/test_metrics_firewall_aws.py`): the exact ingress list at the defaults (only SSH from the group itself) and with the exporter on; a source group with nothing enabled opens nothing; metrics enabled with no source group opens nothing; the variable refuses an address, a CIDR and an empty-looking value; and a source scan that no ingress rule in the AWS firewall module can take `cidr_blocks`, `ipv6_cidr_blocks`, `cidr_ipv4`, `cidr_ipv6` or a prefix list (with a negative case proving the scan bites).

Not known or not done:

- The source security group is **supplied by the operator** and is not created here. It must exist before the rule applies, and a security group reference only works inside the same VPC or a peered one. Until a scraper exists, leave it empty.
- The source group must be **different from the connector group**: naming the connector group itself is refused (a precondition in the firewall module, and one on the stack output), since it would admit connector-to-connector metrics. The module check runs at plan once the group exists, and at apply on a first creation (the new group's id is unknown until then).
- **Changing the source group takes two applies.** A different group is a different rule key, so one plan removes the old rules and adds the new ones, and AWS may briefly hold both, or reject the add as a duplicate if it runs first. Set `metrics_source_security_group_id = ""` and apply, then set the new group and apply. Scraping is down between the two, as intended.
- The node exporter has no authentication. Its only protection is the security group rule and, if on, the host firewall.
- The connector's own metrics bind address stays UNVERIFIED, as in section 2.1.
- Connector-to-connector scraping is not added (only the one source group), as in section 2.1.
- Log shipping is **not** added on AWS. That is a later follow-up, after the DigitalOcean change lands.
- The AWS `connector_private_ips` handoff to stack 20 is as unverified as in section 2.1; and stack 20 itself has no AWS variant.

### 2.4 Log shipping on the connectors (stage 2 step 7)

**Status: written and mock-tested only. Nothing here is applied, nothing has run on a real machine, and the agent cannot reach a manager yet (see "Not built" below).**

An opt-in Wazuh agent and a short auditd rule set on each connector, in stack 10 (`stacks/10-access`) through the shared bootstrap module. With the defaults (`log_shipping = {}`) the plan is a no-op: the golden `user_data` hashes in the bootstrap tests (connectors a and b, `host_firewall` false and true, node exporter off) prove the cloud-init is byte-identical. That no-op claim rests on those hashes alone: the stack 10 test only shows that the default plans with the agent off and no token.

**Enabling it REPLACES the droplet.** `user_data` changes, and a DigitalOcean droplet is replaced when it does. Each connector in `log_shipping_instances` is rebuilt. Roll out one at a time: `log_shipping_instances = ["a"]`, apply, check SSH through Twingate and the memory headroom, then `["a", "b"]`.

The agent also carries a `site` label (a `<labels>` block in `ossec.conf`, the site part of `agent_name_prefix`), which is what the Grafana Wazuh dashboard's site filter reads (`agent.labels.site`). It is part of the same opt-in `user_data`: nothing changes while `log_shipping` is off, and a stack that already enabled `log_shipping` before this label existed will see its droplets replaced on the next apply for it, so treat it like any other change to that block.

| Setting (stack 10) | What it does |
|---|---|
| `log_shipping = { enabled = true, manager_address, agent_name_prefix, apt_key_fingerprint, ... }` | Installs `auditd` from the distro archive and the `wazuh-agent` package from Wazuh's apt repository. The repository key is checked against `apt_key_fingerprint` before it is trusted (the same pattern as the Twingate repository in the template). The fingerprint is a **required input with no default**: this repository does not carry one, because a wrong value written from memory would be worse than none. Read the 40 hex digits from Wazuh's documentation and compare them yourself |
| `agent_name_prefix` | Each agent is named `<prefix>-connector-<a or b>`, for example `site-tor1-connector-a`. Use the same value as `site_name`. It is a separate input on purpose: it lands in `user_data`, so changing it replaces the droplet, while `site_name` replaces nothing |
| `agent_group` | Optional. The group must already exist on the manager, or enrollment fails (and the agent stays off) |
| `agent_version` | Optional package pin such as `4.9.2-1`. Match the manager: Wazuh does not support an agent newer than its manager |
| `manager_port` / `enroll_port` | 1514 and 1515. They must match the `wazuh-agent` and `wazuh-enroll` ports in stack 20's `logging_servers`; `tests/test_log_shipping_ports.py` fails when they disagree |
| `log_shipping_instances` | Which connectors get it (default both) |
| `log_shipping_bootstrap_token` | The one secret-shaped value (below). Sensitive. Required when enabled |

What the agent collects (`<localfile>` blocks that `/usr/local/sbin/cah-ossec-insert` puts inside the existing `<ossec_config>` element of its `ossec.conf`, before the last closing tag. The file is rewritten through a same-directory temporary file that is fsynced, keeps the mode and owner, and replaces the original by rename, so a full disk or a kill leaves the original intact; a result that is not well-formed XML, or that would add a top-level element, is never installed, and a config with no root fails closed): journald for the `twingate-connector`, `ssh`/`sshd` and `sudo` (by syslog identifier), `/var/log/auth.log`, and `/var/log/audit/audit.log`. Because `sshd` events are in both journald and `auth.log`, expect duplicate events for them until you drop one source. The auditd rules (`/etc/audit/rules.d/60-cah.rules`) are watches only: writes to `/etc/passwd`, `group`, `shadow`, `gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` and `/etc/twingate/`. There are no syscall rules and no `execve` auditing, because the volume is too high for a 1 GB droplet (logging design, section 7).

#### Secrets: one mechanism (design section 2.8)

`user_data` and the state hold **one** secret-shaped value, the bootstrap token, and nothing else:

1. The maintainer creates, out of band (not in OpenTofu, so it is not a resource in state), a read-only Doppler service token for the config `cah-<resource_key>-hostboot`, which holds only that site's host secrets (here `WAZUH_ENROLLMENT_PASSWORD`). It is handed to the stack as the sensitive `TF_VAR_log_shipping_bootstrap_token`.
2. cloud-init writes it to `/etc/cah/hostboot.token` (root, 0600). The first-boot script (`/usr/local/sbin/cah-log-shipping-firstboot`, run from `runcmd` after the agent package is installed) reads it, **deletes the file**, and sends it to `api.doppler.com` over TLS on curl's standard input (never in a command line).
3. It extracts only `WAZUH_ENROLLMENT_PASSWORD` from the answer, deletes the rest of the pulled config, writes the password to the agent's `authd.pass` (root, 0600), runs `agent-auth` against the manager, and **removes the password file after enrollment, on success or failure**. The per-host agent key that enrollment yields stays on the host.
4. Only then does it enable and start the agent.

**Fail closed.** If the token file is missing or empty, the agent is not installed, the pull fails (an expired token looks like this), the secret is missing or unusable, the enrollment fails, or `augenrules --load` fails, the script logs why to the cloud-init output, stops, disables and masks the agent, removes the token and password files, and exits non-zero. It never falls back to a literal and never starts an unenrolled agent. A failed first boot is recovered by rebuilding with a fresh token; the token file is deleted even on failure, so there is nothing to re-run by hand.

**The agent cannot start before it is enrolled.** The Wazuh package may start its service when it is installed. So before the install, `/usr/local/sbin/cah-agent-guard deny` masks the unit and installs a `/usr/sbin/policy-rc.d` that answers 101 (denied) for `wazuh-agent` only; if the guard fails nothing is installed. A `policy-rc.d` that already existed is moved to `/usr/sbin/policy-rc.d.cah-orig`, not replaced: the new one delegates every other request to it, and `cah-agent-guard allow` puts the original back byte for byte after enrollment (or removes ours when there was none). The first-boot script lifts both guards only after a successful enrollment, just before it enables the agent. Every failure leaves both in place, and a failure after they were lifted (for example the agent not starting) puts both back. The policy file's effect on the package scripts is UNVERIFIED on a real machine.

**How the guard stays safe.** The guard does not guess that a policy file is its own from a marker in the text: `deny` records the sha256 of exactly what it installed in `/var/lib/cah/agent-guard.state`, and a policy counts as ours only while that file exists and the hash still matches, so an unrelated policy that merely mentions the marker is moved aside and put back, never overwritten or deleted. It refuses a symlinked `policy-rc.d` (nothing is written through it) and installs the policy from a temporary file in the same directory by rename. `deny` masks the unit first, whatever else happens, and exits non-zero with a message when it cannot restore the denial (for example an unmanaged `policy-rc.d` and a saved original both exist: both are left untouched). On any failure the first-boot script stops and disables the agent, masks it directly, then runs `deny`; if `deny` cannot restore the denial it logs `CRITICAL` (as it does if the mask itself fails) and exits non-zero, so the unit stays masked and the problem is on the record. The one case that remains is a mask that fails together with a policy the guard cannot take over: that is reported, not fixed, and needs a person to look at `/usr/sbin/policy-rc.d` and `systemctl status wazuh-agent`.

**Leftovers after a hard kill.** The cleanup is an exit trap, which SIGKILL, a reboot or a power loss skips. So: the first-boot script removes any leftover password file and pulled config before it does anything else; a `cah-log-shipping-sweep.service` unit (enabled for the next boot, never started on the first, because the first-boot script still needs the token) removes the token and password files at every later boot before the agent starts; and a `wazuh-agent` drop-in removes a stale password file with `ExecStartPre=-` before every agent start. The honest remaining window: the token file exists from cloud-init's `write_files` until the script reads it (seconds to minutes, longer if the first boot stalls), the password file exists from the pull until enrollment ends, and after a SIGKILL they stay on disk until the next boot's sweep. The token file is not swept at the start of the script, because it is the script's input. That window is root-readable only (0600).

**The Wazuh key is accepted only when it is exactly the pinned key.** `/usr/local/sbin/cah-wazuh-key-check` lists the downloaded file with `gpg --show-keys --with-colons` and refuses it unless it holds exactly one public key (no secret key, no second `pub` record), whose primary fingerprint equals the pin. A subkey's own fingerprint record is accepted only directly after its `sub` record, so a bundle of the pinned key plus an attacker key is refused (tests with fake gpg output cover two keys in either order, an extra fingerprint record and a wrong primary).

Where the token (and so the credential) lives, written down. Copies: the Terraform state; the DigitalOcean API (the droplet's user_data); the droplet's metadata endpoint (unless `metadata_lock` is on); and cloud-init's own retained copy of `user_data` under `/var/lib/cloud` on the machine, which the first-boot script does not delete. All of them hold it until the token expires or you revoke it, so the token must be short-lived and revoked right after the first boot. Whether Doppler can issue a token that expires within hours, or a single-use one, is **UNVERIFIED**; the design needs "expires on its own within a day", and if the minimum is longer you revoke it after the first boot. The enrollment password, any Twingate service key and any Doppler secret value are never in `user_data`: `tofu test` renders `user_data` with fixture values for all three and fails if any appears, and the bootstrap module declares no variable that could carry one.

#### Not built, and UNVERIFIED

- **The Twingate headless client is NOT included.** The design (section 4) has each cloud host reach the manager's 1514 and 1515 through a Twingate headless client with its own service key (pulled from the same hostboot config). That is a second package, a service-key pull, a client start and a connection check, on a host that already runs a connector, and it needs the `logging_servers` resources from stack 20 applied first. It is a separate follow-up. Until it exists, `manager_address` must be something the droplet can already reach, and an enabled agent otherwise **cannot connect**: enrollment will fail and, by design, the agent stays off.
- **Memory on the 1 GB droplets is UNMEASURED.** The design estimates the agent at roughly 50 to 100 MB resident, with the node exporter about 20 MB more; these are estimates. Measure on connector a before touching b. The fallback is a size bump, which the cost gate shows as a deliberate approval.
- **journald inside the Wazuh agent is UNVERIFIED.** The `journald` log format and the filter field names (`_SYSTEMD_UNIT`, `SYSLOG_IDENTIFIER`) are written from Wazuh's documentation, not run against your agent version. **The syslog fallback is documented, not built:** if the agent rejects the journald blocks, set journald `ForwardToSyslog=yes` on the connectors and ship it over a Twingate resource to a syslog listener on the manager side (TCP 514), which lands in the same pipeline (design 2026-10-11, section 6.1). Nothing in this repository builds that path.
- The agent-side details are reasoned from the documentation and tested only as text and with fake binaries: that the deb package does not start the agent before enrollment, that `agent-auth` reads `authd.pass` when no `-P` is given, that the first `<address>` and `<port>` in the stock `ossec.conf` are the server's (the script edits those two), and that `augenrules --load` picks up the rule file. They need a first boot on one connector.
- The AWS connector module does not pass `log_shipping` through yet (the bootstrap module is cloud-neutral and supports it), the same state as the node exporter.
- No rule is written for the journald line shapes: capture real lines first (design 2026-10-11, section 6.3).

What the tests prove: `tofu test` for the golden hashes, the secret-absence rule, every validation, and the wiring in the stack; `tests/test_log_shipping_script.py` renders the script from the template and runs it with fake `curl`, `systemctl` and `agent-auth` for success, a failed pull, a missing secret, a failed enrollment, a missing agent and a missing token (agent never started, token file and password file gone every time, no secret on stdout or stderr); `tests/test_log_shipping_ports.py` for the 1514 and 1515 agreement with stack 20.

### 2.5 Per-site accounts: the `sites` map (issue #104)

**Status: written and mock-tested only (`tofu test` with a mocked Twingate provider). Nothing here is applied.**

The `sites` variable adds sites to this stack without touching the first one. It is empty by default, and the planned addresses of the single-site stack are byte-identical with it empty: the new objects are separate `site_*` resources, so no `moved` block is needed or used. `docs/golden-addresses/20-telemetry.json` pins the single-site addresses and `tests/test_golden_telemetry.py` ties them to the sources (the default plan has no objects at all while both flags are false; the golden file describes the flags-on shape).

| Per `sites` entry (key = the site's `resource_key`) | Created when | Name |
|---|---|---|
| A logging service (`twingate_service_account.site_logging`) | `logging_enabled` | `telemetry-<key>-logging` |
| A scrape service (`twingate_service_account.site_scrape`) | `metrics_enabled` | `telemetry-<key>-scrape` |
| A logging resource per `logging_servers` element (`site_logging`), granted to that site's logging service only | `logging_enabled` | `logging-<key>-<server>` |
| A scrape resource per `scrape_allowlist` entry per connector (`site_scrape`), in that site's own `cloud_remote_network_id`, granted to that site's scrape service only | `metrics_enabled` | `scrape-<key>-<entry>-<a or b>` |

- One service per site per role, never shared: a stolen key reaches only its own site's resources. The home logging servers (`logging_servers`, `home_remote_network_id`) and the allowlist and ports are shared inputs; the cloud network id and connector addresses are per site.
- The **`site_name` label** (`site_name`, empty meaning `site-<key>`) goes into the `site` and `instance` fields of the sensitive `scrape_targets` output and into the new `extra_site_identities` output. It is in no name. The services themselves carry no label (Twingate service accounts have none that this stack sets); the label lives in the outputs the home Prometheus generator reads.
- **Service keys are NOT created here.** The existing design (section 2.8) and `tests/test_telemetry_stack.py::test_no_service_key_is_created` keep keys out of state: they are issued out of band, one per host, for each site's service. Per site that is one key for the logging service on each cloud host and one for the scrape service on the home Prometheus host.
- Cost: $0.00. A site in this map is not a new Spacelift stack, so no `instance_of` manifest is needed and `cost.json` stays empty. A site that gets its **own** stack (separate state) uses the stack id rule and an instance manifest as in [the cost document](../cost.md).
- **UNVERIFIED:** whether Twingate accepts several resources with the same address in the same remote network (the logging resources of every site point at the same home servers), and whether the plan allows this many service accounts (step 1 of section 3). If duplicate addresses are refused, the fallback is one shared logging resource granted to every site's logging service, which widens what a stolen key reaches back to the same home endpoints and is a design decision for the maintainer.
- **Isolation and collision checks (preconditions, mock-tested).** Every scrape endpoint, a (`cloud_remote_network_id`, connector address) pair, must be unique across the default site and every `sites` entry, so no two sites' scrape services can reach the same endpoint; the same address in different remote networks is allowed. The generated resource names must be unique (a hyphen in a key or entry name can make distinct pairs render alike, for example `ab-c` with `de` and `ab` with `c-de`); and the resolved site labels must be distinct, including the default site's (`site_name` or `site-<region>`) and each entry's (`site_name` or `site-<key>`). Only `connector`-role allowlist entries are multiplied across connector addresses (the variable validation already refuses any other `host_role`). The logging resources of different sites deliberately point at the same shared home servers (each service is granted only its own site's resources), so the endpoint-uniqueness rule applies to scrape only. `extra_site_identities` reports the labels of listed sites even with the flags off (labels only, no objects).
- A `sites` key may not equal this stack's own `resource_key` (a precondition refuses it). Keys are immutable once applied, like every name.

### 2.6 TLS decision record: Prometheus scrape and Wazuh agent traffic over Twingate

**Status: a decision record, not a build. Nothing in it was applied or measured. Every statement about a vendor's behaviour below is UNVERIFIED: this change was written without fetching any vendor page, so no page was read for it, and each claim is from the maintainer-side design documents or from memory. Check each against the cited vendor page before relying on it.** Pages to read: Twingate security and encryption documentation (twingate.com/docs), Prometheus configuration (`tls_config`, `--web.config.file`) at prometheus.io/docs, and the Wazuh manual sections on agent enrollment and agent-manager communication at documentation.wazuh.com.

**Decision to make:** where, if anywhere, TLS is terminated for (a) the home Prometheus scraping the connectors' node exporter and connector metrics (plain HTTP today, design section 4.2 and open question 7) and (b) Wazuh agents reaching the manager on 1514 and 1515, both across a Twingate resource.

| Hop | What already protects it (UNVERIFIED) | What remains |
|---|---|---|
| Scrape: client to Twingate | Twingate's client-to-connector tunnel is encrypted (believed TLS-based or equivalent, possibly end-to-end through the relay; the cipher and who can read the traffic at the relay are not verified) | Nothing between the Twingate client and connector, if that holds |
| Scrape: connector to the exporter | Plain HTTP inside the VPC, bound to the private address (stack 10), firewall admits only the telemetry tag | An on-VPC hop with no TLS and no authentication on the exporter |
| Wazuh agent to manager | Wazuh encrypts agent-manager event traffic with its own key from enrollment, and enrollment on 1515 uses TLS (believed, not verified for the version in use) | Whether the manager certificate is validated by the agent (the default may not verify it) |
| Wazuh across Twingate | Twingate's tunnel is a second layer around the above | Two layers, so TLS termination at a proxy is not needed for confidentiality |

Options:

1. **No extra TLS: rely on Twingate (scrape) and Wazuh's own channel (agents).** Cost $0, no certificates to rotate. Leaves the VPC hop to the exporter in clear and the exporter unauthenticated. Matches the design's first-build stance (open question 7).
2. **TLS on the exporter** (`--web.config.file` with a certificate, Prometheus `tls_config` with a private CA). Protects the VPC hop and lets Prometheus check which exporter it reached. Costs a CA, certificate distribution (a secret on each droplet, so a new secret path) and rotation. The node exporter and connector metrics endpoint support for this is UNVERIFIED (the connector's metrics endpoint is documented as plain HTTP at `/metrics`, per the connector telemetry findings).
3. **A TLS-terminating proxy on each connector in front of the exporters.** Adds a process on a 1 GB droplet (memory UNMEASURED) and a second listener to firewall. Only worth it if option 2 is impossible for the connector's own endpoint.
4. **Enable certificate verification and manager authentication for Wazuh agents** (a private CA for the manager, `agent-auth` options to be checked in the manual, an enrollment password, which stack 10 already pulls from the host config). Cheap relative to its value because it stops an agent enrolling with a wrong server.

**Recommendation:** option 1 for scrape in the first build, as the design already records, with the exposure written down: the VPC hop is plain HTTP and is protected by the private bind address and the tag-sourced firewall rule only. Do option 4 for Wazuh (verify the manager certificate and use the enrollment password) before the first live enrollment, since it costs little. Revisit option 2 when a second operator or a second site's hosts share a network with the connectors. Do not build option 3. Reconsider all of this after verifying the three vendor claims above; a different answer on any row changes the recommendation.

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

**X2. Zero open ports from outside.** From a machine that is not in the VPC, scan **only a connector you own**, at the public address `doctl` shows for it. Do not point a scanner at anything else. The read-only check in the [zero-open-ports design](../superpowers/specs/2026-10-17-zero-open-ports-check-design.md) is built (`scripts/zero_ports_check.py`, issue 91, [stage 1 guide section 6b](01-access.md)) and has not run against real infrastructure. This is the manual form:

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
