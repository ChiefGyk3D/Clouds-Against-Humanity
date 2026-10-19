# Stage 1: Access

## 1. What this stage builds

- One Twingate remote network (site), created by OpenTofu and named `access-tor1`, and an existing DigitalOcean SSH key that the stack looks up by name (it does not register one). Both connectors share them.
- Two `s-1vcpu-1gb` droplets, `access-tor1-connector-a` and `access-tor1-connector-b`, each running a Twingate connector inside the VPC. Twingate recommends at least two active connectors, so one can be down without losing access. Each is created with `ubuntu-24-04-x64`, monitoring on, backups off and IPv6 off.
- A connector firewall, attached by the connector tag, with one inbound rule (TCP 22, only from droplets that carry the connector tag) and seven outbound rules: the firewall module's five defaults (tcp 443, 80 and 53; udp 53 and 123) plus tcp 30000-31000 and outbound UDP on every port (1-65535). Twingate's [outbound allowlist article](https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure) requires outbound UDP to any port for peer-to-peer connections. Nothing outside the connector tag can reach the droplet inbound. The baseline firewall also applies to the droplet through its own tag.
- A Twingate admin group, `cah-tor1-admins`.
- Two per-host Twingate resources, one for each connector's private address, each limited to TCP port 22.

Cost: $12.00/month, approved DigitalOcean total $12.00 in `docs/stages/approved.json` (see [cost](../cost.md)). Phase id `stage-1`, the current phase, ceiling $30.

What the tests prove (`tofu test`, no cloud account needed):

- The connector firewall has exactly one inbound rule, TCP 22 sourced from the connector tag and never from an address. The stage 0 baseline firewall still has zero inbound rules. The firewall module rejects an inbound rule whose protocol is not tcp or udp or whose port range is empty.
- Both droplets are named per instance, carry the baseline and connector tags at creation, and are listed in the project.
- The site is created once, in the stack, and shared by both connectors. The SSH key is looked up by name and never registered. The module's `instance` input accepts one lowercase letter or digit and nothing else.
- Each SSH resource allows only TCP 22, denies UDP and has ICMP off.
- Connector tokens never appear in module outputs. The output test pins the declared output names, so adding an output means editing that list on purpose.

## 2. Why there is no public SSH

DigitalOcean droplets always have a public address. You cannot remove it. So the control is a firewall that is attached by tag at creation and allows no inbound traffic from outside. The one exception, TCP 22 between the connectors themselves, is described in section 2c. The droplet is created with the baseline tag, so there is no moment when it is open. You reach the host by its private IP through Twingate: the connector on the droplet dials out to Twingate, and your client reaches it through that outbound connection.

## 2a. Droplet hardening

Each connector's cloud-init (`modules/twingate-bootstrap/cloud-init.yaml.tftpl`) sets up:

- One login user, `cah-admin`, with the admin public key and passwordless sudo. No password exists (`lock_passwd`), root is disabled (`disable_root`) and the default `ubuntu` user is not created.
- An sshd drop-in, `/etc/ssh/sshd_config.d/99-cah-hardening.conf`: no root login, no passwords, no keyboard-interactive, public keys only, no X11 forwarding, `AllowUsers cah-admin`, `MaxAuthTries 3`, `LoginGraceTime 20`.
- The droplet clock is the `timezone` setting (default `America/New_York`), so every time below is Eastern unless you change it.
- `unattended-upgrades` for security updates, with automatic reboot (also when someone is logged in) at `reboot_time` and removal of unused dependencies. Updates and the install of the connector wait for the dpkg lock for up to 300 seconds (`/etc/apt/apt.conf.d/99cah-lock-wait`), so first boot does not fail while Ubuntu's own apt jobs run.
- `chrony` for time sync (UDP 123 outbound is already allowed).
- A sysctl drop-in: loose reverse-path filtering, no ICMP redirects, no source routing, SYN cookies, martian logging. It does not touch `ip_forward`.
- A weekly connector update, half an hour after each connector's reboot time on Sundays (see the install route below), so the sibling is idle while one restarts.

Update schedule (droplet local time, Eastern by default):

- Security updates install daily.
- A droplet reboots only when an update requires it, at 04:00 (connector a) or 05:00 (connector b).
- The connector package updates on Sundays at 04:30 (a) and 05:30 (b).

### Metadata endpoint lock (built, off by default)

Any process on a connector droplet can read the cloud-init user-data from `169.254.169.254`, and that includes the connector tokens. The `metadata_lock` setting (default `false`) closes that: a small nftables table (`inet cah_metadata`, its own table, so no other rule is touched) rejects outbound traffic to `169.254.169.254` unless the process runs as root (uid 0) or as the `do-agent` user. DigitalOcean's monitoring agent runs as `do-agent` and uses that address as its metric proxy, and the droplet module sets `monitoring = true`, so without that exemption droplet monitoring would silently stop. On AWS there is no `do-agent` user and the script allows root only. A systemd unit (`cah-metadata-lock.service`, ordered after `cloud-final.service` so the `do-agent` user already exists on first boot) applies the table at every boot.

It has **not been tested on a real droplet yet**. Turning it on changes `user_data`, so the plan shows the droplet of every connector in `metadata_lock_instances` REPLACED. Stage it, one connector at a time:

1. Set `metadata_lock = true` and `metadata_lock_instances = ["a"]`. Plan, apply.
2. Verify connector a (below). Check SSH through Twingate to it.
3. Set `metadata_lock_instances = ["a", "b"]`. Plan, apply, verify connector b.

Verify, as `cah-admin` over Twingate (replace `host` with the connector's private address):

```
ssh -t cah-admin@host 'curl -s -m 3 http://169.254.169.254/metadata/v1/id; echo "exit=$?"'
ssh -t cah-admin@host 'sudo curl -s -m 3 http://169.254.169.254/metadata/v1/id; echo "exit=$?"'
ssh -t cah-admin@host 'systemctl is-active do-agent cah-metadata-lock.service'
```

The first line must fail (the request is rejected), the second must print the droplet id, and `do-agent` must stay `active`.

Rollback: set `metadata_lock = false` (this replaces the droplet again), or on one box, without waiting for a rebuild (this lasts until the next boot, so also set the setting to false):

```
ssh -t cah-admin@host 'sudo nft delete table inet cah_metadata'
```

The metadata lock unit also follows `nftables.service`, so a restart of it re-applies the lock (see "Surviving `nftables.service`" under the host firewall below; untested on a real machine).

### Host firewall (built, off by default)

The DigitalOcean cloud firewall is the only inbound layer today. If a tag is ever set wrong, nothing else stands in the way. The `host_firewall` setting (default `false`) adds a second layer on each connector: an nftables table of its own (`inet cah_host`, input chain only, policy drop; the `inet cah_metadata` table and the output and forward chains are never touched, and the ruleset is never flushed). It lets in only loopback, replies to traffic the machine started, the few ICMP types and ICMPv6 neighbour discovery the network card needs, DHCPv4 replies so leases renew, TCP 22 from `host_firewall_ssh_sources` (default the three private blocks `10.0.0.0/8`, `172.16.0.0/12` and `192.168.0.0/16`; the cloud firewall already limits SSH to the connector tag, so this only narrows it to private space, because the module does not know the VPC range) and, when `connector_telemetry.metrics_port` is set, that one port from the same sources. The same template serves DigitalOcean and AWS. A systemd unit (`cah-host-firewall.service`, after `cloud-final.service`, enabled with `--no-block` so it cannot deadlock cloud-init) runs `/usr/local/sbin/cah-host-firewall` at every boot.

The script is built not to lock you out: it checks the ruleset first (`nft -c`, and refuses to apply one that does not parse), applies it, then verifies that sshd is still listening on port 22 and that the ssh accept is in the loaded table, and deletes the table if either check fails. There is no timer that removes the firewall later, because that would be a hole.

It has **not been tested on a real droplet yet**. A wrong ruleset can lock you out of SSH, and turning it on changes `user_data`, so the plan shows the droplet of every connector in `host_firewall_instances` REPLACED. Stage it, one connector at a time:

1. Set `host_firewall = true` and `host_firewall_instances = ["a"]`. Plan, apply.
2. Check SSH through Twingate to the new connector a (below) **before** touching b.
3. Only then set `host_firewall_instances = ["a", "b"]`. Plan, apply, verify connector b.

Verify, as `cah-admin` over Twingate (replace `HOST` with the connector's private address):

```
ssh -t cah-admin@HOST 'sudo nft list table inet cah_host'
ssh -t cah-admin@HOST 'systemctl is-active cah-host-firewall.service twingate-connector'
ssh -t cah-admin@HOST 'sudo journalctl -u cah-host-firewall.service --no-pager -n 20'
```

The first line must print the table with `policy drop` and a `tcp dport 22` rule, and both units in the second must be `active`.

If you lose SSH: the Droplet Console in the DigitalOcean panel is believed to be an out-of-band path that does not go through the host firewall, but that is **not tested**; do not rely on it. The documented fallback is to replace the droplet through OpenTofu: set `host_firewall = false` and apply, which is a replace (a new droplet, so the lost one is destroyed). If the console does work, run the rollback below from it.

Rollback: set `host_firewall = false` (this replaces the droplet again), or on one box, without waiting for a rebuild (this lasts until the next boot, so also set the setting to false):

```
ssh -t cah-admin@HOST 'sudo nft delete table inet cah_host'
```

Surviving `nftables.service` (applies to both the host firewall and the metadata lock above): Ubuntu's `nftables.service` is a oneshot that loads `/etc/nftables.conf`, which begins with `flush ruleset`, on start, restart and reload, and its package upgrade runs `try-restart` on it. Left alone, that would silently delete the `inet cah_host` and `inet cah_metadata` tables (the rules would fail open and nothing would notice). So `cah-host-firewall.service` and `cah-metadata-lock.service` are both `After=nftables.service` and `PartOf=nftables.service`, with `ReloadPropagatedFrom=nftables.service` and an `ExecReload` that re-runs the script: a restart or reload of `nftables.service` restarts or reloads our unit, which loads its table again. The relationship is soft on purpose (no `Requires=`, `Wants=` or `Requisite=`), so when `nftables.service` is inactive, as on first boot, our unit still starts and does not fail. A plain `systemctl stop nftables` still flushes the ruleset and our unit is not restarted by it; do not stop it. This is reasoning from the unit semantics and the unpacked Ubuntu 24.04 package, **not tested on a real machine**. To see it work, run `ssh -t cah-admin@HOST 'sudo systemctl restart nftables.service && sudo nft list tables'` on a staged connector and check that the table is listed again (this also reloads the firewall, so do it only with the Twingate session you already have open).

Not covered yet: when the node exporter is installed on the connectors (stage 2), its port needs its own rule; today nothing on the connectors listens on it.

Follow-ups, not done yet:


- Audit logging (auditd, or shipping auth logs off the droplet).
- Moving the Twingate install to a pinned package source once Twingate documents one (below).

## 2b. How the connector is installed and updated

What Twingate's documentation says, read 2026-10-10:

- The Linux connector page ([connectors-on-linux](https://www.twingate.com/docs/connectors-on-linux)) says the systemd install "can be performed in a single command with the necessary environment variables set" and gives that command only in the Admin Console. It documents `/etc/twingate/connector.conf` with three required settings (`TWINGATE_NETWORK`, `TWINGATE_ACCESS_TOKEN`, `TWINGATE_REFRESH_TOKEN`), the service name `twingate-connector`, and `systemctl` start, stop, restart and enable. It does not document an apt repository, a GPG key or a checksum for the connector.
- The update guide ([systemd-service](https://twingate.com/docs/systemd-service)) upgrades with `apt update`, `apt install -yq twingate-connector` and `systemctl restart twingate-connector`. There is no built-in self-updater. Twingate's documented mechanism is a weekly cron job running those commands, scheduled off-peak, with two or more connectors per remote network so one can update without downtime.

The install does not use Twingate's `setup.sh`. The first real build used it as `curl ... | bash` and both connectors came up with the package installed but no `/etc/twingate/connector.conf` and the service never started, while the log still said "succeeded" because the pipe exited 0. A script that is piped into `bash` is read as it arrives, and anything in it that reads stdin (apt's package configuration is one) can swallow the rest of it. I did not prove that is exactly what happened here, so treat it as the leading explanation, not a fact. The fix does not depend on it: this repository now does what Twingate's own AWS Terraform does ([terraform-aws](https://www.twingate.com/docs/terraform-aws)). Cloud-init writes `/etc/twingate/connector.conf` itself (`TWINGATE_URL=https://<network>.twingate.com`, the access token and the refresh token; mode 0600, owned by root), installs the `twingate-connector` package from Twingate's apt repository, and runs `systemctl enable --now twingate-connector`.

The repository is `https://packages.twingate.com/apt/`, signed with the key at `https://packages.twingate.com/apt/gpg.key`. The install step downloads that key, checks its fingerprint against the one pinned in the template (`EC952DEE4701A407A82B0C505C363F09A9174A9E`, read on 2026-10-10; the key expires in April 2027) and only then trusts it with `signed-by`. When Twingate rotates the key, the check fails loudly; update the pin after confirming the new fingerprint with Twingate. The step retries up to 10 times, 30 seconds apart, and an attempt only counts as a success when the service is active after `systemctl enable --now`. After the retries, a second step writes the service state, the last 50 journal lines and the last 50 lines of the cloud-init output to `/var/log/cah-connector-install.log` (root, mode 0640; no token is read or printed).

The `TWINGATE_LABEL_DEPLOYED_BY` label is no longer set; Twingate's own Terraform guide does not use it.

The weekly update is the documented cron job, as `/etc/cron.d/twingate-connector-update`, because `cron.weekly` would run both connectors at the same moment.

## 2c. Why the connectors may reach each other's SSH

Both connectors sit in one Twingate remote network, and each has a Twingate SSH resource at its own private address. Twingate chooses which connector carries a session, so a session to connector b's address can be routed through connector a. Connector a then has to open TCP 22 to connector b inside the VPC, and DigitalOcean cloud firewalls filter VPC-internal traffic too. With zero inbound rules that connection timed out during the SSH banner exchange, while the connector's own address kept working. Twingate's [connector best practices](https://www.twingate.com/docs/connector-best-practices) say every connector in a remote network needs identical network reach, so every connector must be able to reach every connector-address resource.

The fix needs both directions, because the two connectors play different roles in one session. The target must accept the connection (inbound) and the sender must be allowed to open it (outbound). DigitalOcean allows outbound traffic only when an outbound rule permits it; the connector firewall's other outbound rules (tcp 443, 80, 53 and 30000-31000, udp) do not include TCP 22, so the first fix, inbound alone, still timed out. Replies to an admitted connection are stateful and need no rule.

- Receive, on the target: the firewall module's `inbound_from_tag_rules`, which the connector firewall sets to TCP 22. Each rule uses `source_tags` equal to the firewall's own tag, so only droplets carrying the connector tag can connect.
- Send, from the source: the module's `outbound_to_tag_rules`, also TCP 22. Each rule uses `destination_tags` equal to the firewall's own tag, so a connector can open SSH only to droplets carrying the connector tag.

Neither rule has an address and neither uses `0.0.0.0/0`. The baseline firewall has neither variable set, so it still has zero inbound rules and only its five address-based outbound rules.

Access from outside is unchanged: there is still no public inbound, and SSH is reachable only through Twingate. After the apply, verify:

- From connector a (over Twingate SSH), check the peer's private address directly: `timeout 5 bash -c '</dev/tcp/<connector b private ip>/22' && echo open || echo blocked`. It should print `open`; do the same from b to a. Before the outbound rule it printed `blocked`.
- From a host outside the VPC, `nmap -Pn -p 22 <droplet public address>` should still report the port filtered.
- The SSH resources should work from the Twingate client for both connector addresses.

## 3. Accepted residual risk

The connector token appears in OpenTofu state and in the droplet's cloud-init user-data. It is marked sensitive, and the token is revocable and belongs to a single connector, so each of the two connectors has its own. Two things for you to do and check: keep the state in Spacelift, and in Spacelift restrict who can read the stack's state and outputs to the people who need it.

To rotate the token, replace `module.connector_a.module.bootstrap.twingate_connector_tokens.this` (or `module.connector_b.module.bootstrap...` for the other one; the tokens moved into the shared bootstrap module, and the old address no longer exists once a run has applied that change). Rotate one connector at a time so the other keeps serving. Because the state lives in Spacelift, this is not a local `tofu apply` from a laptop. Do it as a Spacelift run with the replace option for that address (or taint the resource through Spacelift's run options), then read the plan before confirming.

To rotate the admin SSH key: put the new public key in `ADMIN_SSH_PUBLIC_KEY`, register it on the DigitalOcean account, and set `ADMIN_SSH_KEY_NAME` to its name. The key is in `user_data`, so this rebuilds both droplets; do it with the same one-at-a-time care (target one module per run). To change the reboot windows, edit `reboot_time` in the stack; that also rebuilds the droplet.

Rotation is not free. The new token changes the rendered cloud-init `user_data`, and per the DigitalOcean provider's behavior a `user_data` change forces a new droplet; confirm in the plan output before approving the run. If so, rotation destroys and recreates that connector's droplet: expect a short outage of that connector and probably a new private IP, and its SSH Twingate resource follows the new address. The other connector keeps Twingate access up meanwhile.

## 4. Vendor facts to record when verified

Record each date here when you check it.

Verified so far:

- Twingate provider 3.8.0, verified 2026-10-10: the provider reads `TWINGATE_API_TOKEN` and `TWINGATE_NETWORK`. The DigitalOcean provider reads `DIGITALOCEAN_TOKEN`.
- In provider 3.8.0 the `protocols` setting on `twingate_resource` is an attribute object, not a block. The SSH resources in `stacks/10-access/main.tf` are written that way.
- `twingate_network` must be the bare subdomain (lowercase letters, digits, hyphens), not a URL. It is validated in the connector module and again in the stack.
- The cloud-init install (see 2b) runs under `bash -o pipefail` with `curl -fsSL --proto '=https' --tlsv1.2 --retry 5`, checks the repository key fingerprint, and only reports success when `twingate-connector` is active, so a failed download or a service that did not start shows up as a failed step instead of a silent half-install.

Verify before apply (not confirmed yet):

- [ ] The connector firewall's outbound ports (tcp 30000-31000 and udp 1-65535 in `stacks/10-access/main.tf`) against Twingate's [outbound allowlist article](https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure).
  Verified on:
  Verified on:
- [ ] Whether the install page expects the bare subdomain or a full URL for `TWINGATE_NETWORK`.
  Verified on:
- [ ] The Twingate install page title and date. It was read on 2026-10-10 through a summarizing fetch (page title: "Minecraft Server with Twingate (Linux)"), not directly, so read the page itself.
  Verified on:

Known note (corrected 2026-10-17): the `access_group` block on `twingate_resource` is not deprecated in any provider release, and nothing replaces it. Only two attributes nested inside it (`approval_mode` and `usage_based_autolock_duration_days`) are deprecated, and this repository sets neither. The "deprecated source" warnings `tofu test` prints come from the test assertions that read the whole block, not from `main.tf`; `tofu validate` on the stack is clean. The provider is pinned to 3.x (3.8.0, the last 3.x release); moving to 4.x or 5.x is a separate, optional upgrade (issue #93) with its own plan to read.

## 5. Bootstrap

1. Create the Spacelift stack `cah-10-access` rooted at `stacks/10-access`.
2. Add a stack dependency on `cah-00-foundation` and map its outputs to this stack's variables:

   | Foundation output | Environment variable |
   |---|---|
   | `vpc_id` | `TF_VAR_vpc_id` |
   | `project_id` | `TF_VAR_project_id` |
   | `baseline_tag` | `TF_VAR_baseline_tag` |
   | `region` | `TF_VAR_region` |

3. Add to Doppler: `DIGITALOCEAN_TOKEN`, `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, `ADMIN_SSH_PUBLIC_KEY`, `ADMIN_SSH_KEY_NAME` and `ADMIN_USER_IDS`. Doppler only allows uppercase names, so the hook (`.spacelift/config.yml`) maps them to the lowercase environment variables OpenTofu reads: `TF_VAR_twingate_network` (from `TWINGATE_NETWORK`), `TF_VAR_admin_ssh_public_key`, `TF_VAR_admin_ssh_key_name` and `TF_VAR_admin_user_ids`. `ADMIN_USER_IDS` is required (the stack has no default and rejects an empty list, so a missing value cannot create an unreachable host); it is a JSON list of Twingate user ids, for example `["<user id>"]`. Strip the comment field from the SSH public key before storing it (keep only `<type> <key>`): comments often hold a user and machine name, and the key goes into the droplet's cloud-init and into state. `ADMIN_SSH_KEY_NAME` is the name of that same key as it is already registered on the DigitalOcean account. The key must already be there: the stack looks it up by name and does not register it, because DigitalOcean refuses a second registration of the same key with a 422 "SSH Key is already in use". If the name is wrong, the plan fails at the lookup. The two network values are the bare subdomain.
4. Check that no Twingate site named `access-<region>` (for example `access-tor1`) exists in the admin console. OpenTofu now creates the site itself; a hand-made site with that name makes the apply fail or leaves a duplicate, so rename or delete the hand-made one first.
5. Trigger a tracked run on `main`; it stops after the plan because autodeploy is off. Proposed runs get no credentials by design. Read the plan, then confirm.

## 6. Verify

1. Both connectors show online in the Twingate admin console, under the one site `access-<region>`.
2. From a Twingate client: `ssh <user>@<connector private IP>` works for each connector's private IP (`connector_private_ips` output, keys `a` and `b`).
3. From outside Twingate: `nmap -Pn -p 22,80,443 <connector public IP>` shows the ports filtered on both droplets. Scanning your own droplet is authorized.
4. `python3 -I scripts/cost_check.py --root .` still reports `digitalocean: planned $12.00/mo, approved $12.00`.
5. **IPv6 stays closed.** The automated test `tests/test_ipv6_closed.py` (part of `pytest tests`, so part of CI) fails if any droplet lacks an explicit `ipv6 = false`, if any inbound firewall or security group rule has an IPv6 source, if IPv6 settings or resources appear on the AWS VPC, subnet or instance side, or if a .tf file cannot be read or parsed. It checks the declared configuration only. To check a real connector by hand, over Twingate (replace `host` with the connector's private address), the second line should print nothing:

   ```
   ssh -t cah-admin@host 'ip -6 addr show scope global'
   ssh -t cah-admin@host 'ip -6 route show default'
   ```

   Then open the droplet in the DigitalOcean panel: the Networking tab should show no IPv6 address and the "Enable IPv6" option should be off. Not yet run: this hand check has not been run against a real droplet.

## 6b. External zero-open-ports check (run by hand)

The firewall rules, the host firewall and the plan policy say from the inside that the connectors have no public inbound path. `scripts/zero_ports_check.py` says it from the outside: from a machine that is not in the VPC, every TCP port (1 to 65535) on every connector's public address gives no answer at all. It is not run in CI, because it needs live addresses and a credential. It was designed (see `docs/superpowers/specs/2026-10-17-zero-open-ports-check-design.md`) and its logic is tested against fakes and loopback only. It has not been run against real infrastructure yet.

**When to run it.** After any change to a cloud firewall, the host firewall, or a droplet (create, replace, resize, a reserved IP), and once as the proof that stage 1 is closed.

**The command**, from a checkout, on the machine you scan from:

```
doppler run -- python3 -I scripts/zero_ports_check.py --expect-connectors 2
```

Optional: `--region tor1` (the default; it builds the baseline tag `cah-baseline-<region>`), `--resource-key KEY` and `--out PATH` (see below). If the foundation stack sets `resource_key` (for example `tor1-b`), the stack's baseline tag is `cah-baseline-tor1-b`, not `cah-baseline-tor1`: pass the same value with `--resource-key tor1-b` (the check then looks up that tag; leave the option out when `resource_key` is empty). The value is checked against the stack's own format (2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens) and anything else stops the run before any request. This names a tag, never an address: every address still comes from the API, and every droplet the API returns must itself carry that exact tag. There is no argument, file or environment variable that supplies an address, on purpose: a port scanner that takes an address is a tool that can be pointed at anyone. The script finds its own targets from the DigitalOcean API, read-only, and a droplet is a target only if it carries the baseline tag **and** belongs to the project `clouds-against-humanity`, and the number found equals `--expect-connectors`. Anything else (a count mismatch, a project droplet without the tag, a public IPv6 address on a droplet, an address that is not a public IPv4 address) stops the run before any port is touched. Reserved IPs assigned to a connector are scanned too.

**The token (the maintainer's step).** The check uses its own read-only DigitalOcean token in its own Doppler config, not the Spacelift token. Create it in the DigitalOcean control panel with these scopes: `droplet:read`, `tag:read`, `project:read` and `reserved_ip:read`. Per DigitalOcean's API reference (https://docs.digitalocean.com/reference/api/reference/reserved-ips/ and https://docs.digitalocean.com/reference/api/reference/reserved-ipv6/, read 2026-10-19), listing reserved IPv4 and reserved IPv6 addresses both need the single scope `reserved_ip:read`; there is no separate IPv6 scope. The API reference lists `project:read` for listing projects and `droplet:read` for listing droplets (the page for the project resources listing did not state its scope when read, so `project:read` there is expected, not confirmed), and the droplet reference says the `tags` field of a droplet requires `tag:read`. Scope names can change, so confirm them in the token form when you create the token. If a listing is refused for scope, the run ends as "cannot tell" (exit 2) and no port is touched. The script reads it from `DIGITALOCEAN_TOKEN` only, never prints it, never writes it to a file, and never passes it to a child process (it starts none).

**Run it from a network you trust to be neutral.** A middlebox that swallows SYN packets would make an exposed port look silent. So a clean result is claimed only after a **second network** run (a phone hotspot is enough): run the same command from there too, and treat the change as verified only when both runs exit 0. The output prints "observed from this network only" as a reminder.

**Time and budget.** Defaults: 512 attempts in flight, a 2.0 second timeout that starts when each attempt begins, at most 1,500 attempts per second. An all-silent connector takes roughly 4.3 minutes, so about 10 minutes for two connectors, plus a little for re-reading the inventory after every batch of 4,096 attempts. The script checks the open-file limit first and says "cannot tell" instead of failing halfway.

**Do not destroy, replace or reassign a connector while the check runs.** DigitalOcean returns a destroyed droplet's address to its pool. The script re-reads the inventory between batches and at the end, and any change in the droplet ids or addresses discards the results (exit 2). That narrows the race; it cannot remove it without coordinating with the lifecycle, so do not start a change during a scan.

**Exit codes.**

- exit 0: every expected address and every port was attempted exactly once, and every attempt timed out (no answer).
- exit 1: something answered. An open port is an answer. A refusal is an answer too: a reset, or a port-unreachable error reported by the host stack as connection refused (ECONNREFUSED, ECONNRESET, ECONNABORTED). On DigitalOcean a blocked packet is expected to get no reply, so a refusal means something answered. It may be the droplet or a device on the path, so the output says "an answer was received", not "the droplet replied". Network or host unreachable errors (ENETUNREACH, EHOSTUNREACH, ENETDOWN, EHOSTDOWN) are NOT an answer from a port: they are "cannot tell" (exit 2). If a run has both an answer and an error it exits 1 and lists both.
- exit 2: cannot tell. Discovery problems, a local error (too many open files, no local addresses, no buffer space, a worker failure), network or host unreachable, a failed positive control, an inventory change, an interruption, or a report that could not be written when the verdict would have been a pass. An error is never counted as a timeout, and a run never exits 0 with any attempt unaccounted for.

**Positive control.** Before the sweep the script makes one TCP connection to the DigitalOcean API on port 443. If that fails, the local path is not trustworthy and the run is "cannot tell". The control's round-trip time is printed so a slow path that could turn answers into timeouts is visible.

**Output and report.** The console prints connector labels (`connector-1`), never an address; counts of attempts, timeouts, answers and errors; the numbers of any answering ports (a port number is not an identifier); the timeout and concurrency used; and the verdict. `--out PATH` also writes that text to a file with mode 0600. It refuses to overwrite an existing file, refuses a path inside the repository or any directory on the way to it that is a symlink (the path is walked one component at a time without following links, so a home directory reached through a link is refused too; the parent is then opened once and checked by its real location, so a swap after the check cannot redirect the write), and a failed write is reported (exit 2 when the verdict would have been a pass).

**Where the report goes, and the threat model.** The report directory is chosen by the operator, on the operator's own machine. The script defends against mistakes (a path inside the repository, a symlinked parent) and against a casual swap: it opens the directory once, checks its real location, checks again just before creating the file and again after writing, and removes the file and exits 2 if the directory has been moved into the repository in between. It does not defend against another local process with rename rights acting during the run (a descriptor pins a directory object, not its place in the tree), and a bind mount of a repository subdirectory elsewhere is not detected. The report holds connector labels, counts and port numbers only, never an address or the token, so the consequence of a mis-placed report is a file of counts in an untracked or ignored location, not a secret leak.

**If a socket cannot be closed after an answer** the answer still counts (exit 1) and the output adds a line `cleanup problems: N`; after a timeout a failed close is a local error (exit 2). **Interrupting** the run (Ctrl-C) discards the results and exits 2, but shutdown waits for workers that are still running or sleeping for the rate limit, so it can take a few seconds to return.

**What it does not prove.**

- **UDP.** TCP only. For UDP the absence of a reply means "open or filtered". A manual extra: `nmap -Pn -sU -p 53,123,500,4500,51820 <connector public IP>` against a few ports you care about, from the second network too.
- **One vantage point and one moment.** It is an observation from your network at one time. The standing guards are the plan policy, the host firewall and the tests; this is the occasional proof.
- **A lying API.** Targets come from the DigitalOcean API, so a compromised or lying API response defeats the ownership check. An attacker who can add tags and project membership in this account is already inside the trust boundary, and anyone who edits the script can point it elsewhere. The rails make the intended use the only easy one; they are not a guarantee against misuse.

## 6a. If a connector shows offline

SSH to a connector goes through Twingate, so it is impossible while that connector is the only path in. Try the other connector first: if `access-tor1-connector-b` is online, SSH to connector a's private IP through it as `cah-admin`, then:

- `sudo systemctl status twingate-connector` shows whether the service exists and runs. "Unit not found" means the installer never finished.
- `sudo cat /var/log/cah-connector-install.log` holds the service state, the last 50 journal lines and the cloud-init output tail, written at the end of first boot. `sudo tail -n 100 /var/log/cloud-init-output.log` shows the full install attempts (`cah: connector install attempt N of 10 failed`).

If both connectors are down there is no way in, and the DigitalOcean recovery options are limited. The account has no console password by design, so the Droplet web console is not an option, and password reset is deliberately not wired up. The droplets are stateless (nothing on them is kept), so the cheap, honest recovery is to rebuild: in a Spacelift run, replace the affected `module.connector_a.digitalocean_droplet.connector` (and the connector token resource, so the new droplet gets a fresh token), read the plan, then confirm. Expect a few minutes of outage for that connector.

## 7. Stage 3 note

Later droplets will need an inbound rule allowing TCP 22 from the connector tag, because DigitalOcean firewalls also filter VPC-internal traffic. The baseline firewall's zero inbound rules apply between droplets in the same VPC too. The connectors already have this rule between themselves (section 2c); a later droplet gets its own firewall with the connector tag as the source.

## 8. Rollback

Destroy `cah-10-access` first, then `cah-00-foundation` if you want stage 0 gone too: stage 0's VPC, project and tag are in use by stage 1, so the order matters. The connector tokens die with the connectors, and the site goes with the stack. The SSH key was never created by the stack, so it stays on the account.
