# Stage 3: Workload host (code written, DISABLED, NOT APPLIED)

> **Unbuilt and unapplied.** `stacks/30-workloads` and `modules/docker-host` are written and tested with mocked providers only. The switch `workload_enabled` defaults to `false`, so the stack plans zero resources. Stage 3 is not approved: the `stage-3` phase in `docs/stages/approved.json` is `planned`, `cost.json` prices nothing and says `workload_approved: false`, and the stack is not registered in `.spacelift/config.yml`. Nothing here has run on a real machine or against any cloud API.

Design: [2026-10-11 stage 3 design](../superpowers/specs/2026-10-11-stage-3-workloads-design.md) (sections 5.1 to 5.3 and 9a). Issue: #111. This page covers the host only. The Spaces bucket, the daemons' compose files and the Functions are later issues.

## 1. What exists

| Piece | Where | Note |
|---|---|---|
| Workload tag `cah-workload-<key>` | `stacks/30-workloads` | The firewall attaches to it |
| Firewall `workload-<key>-host` | `stacks/30-workloads`, built by `modules/firewall` | Inbound: TCP 22 and TCP 9443, each from the **connector tag** only (`inbound_from_other_tags`). Never an address. Outbound: the module's five defaults (TCP 443, 80, 53; UDP 53, 123). The connectors' TCP 30000-31000 and UDP 1-65535 rules are not copied |
| Droplet `workload-<key>-docker` | `modules/docker-host` | `s-1vcpu-2gb`, Ubuntu 24.04, in the core VPC, IPv6 off, backups off, monitoring on, one admin SSH key, tags: baseline and workload |
| Cloud-init | `modules/docker-host/cloud-init.yaml.tftpl` | Update, baseline, harden, then Docker Engine and Portainer CE (section 3) |
| Twingate resources | `stacks/30-workloads` | `cah-<key>-workload-ssh` (TCP 22) and `cah-<key>-workload-portainer` (TCP 9443). Each is one private address, one TCP port, UDP denied, ICMP off, granted to the admins group. No Docker API resource, ever |
| Project attachment | `stacks/30-workloads` | The droplet joins the existing project |

Cost: $0.00 while off. When approved, the droplet is $12.00 a month (`s-1vcpu-2gb`, from `docs/cost-prices.json`) on top of the connectors' $12.00, so $24.00 before the Spaces bucket ($5.00, not part of this issue), $29.00 in all as the design says.

## 2. How the switch is guarded

1. Every resource, data source and module call in `stacks/30-workloads/main.tf` has `count = local.on`, and `on` is `var.workload_enabled ? 1 : 0`. `tests/test_workloads_stack.py` fails if a block lacks it.
2. An output precondition refuses `workload_enabled = true` unless `cost.json` carries `workload_approved = true` and exactly one priced droplet named `workload`. Both change only in the reviewed change that approves the stage.
3. Not registered in `.spacelift/config.yml`, so Spacelift cannot plan or apply it. A test keeps the stanza absent.
4. With the switch off even the SSH key lookup does not run: the plan needs no API call, creates nothing and changes nothing.

## 3. The host

The order is the one every stage guide states: update, baseline, harden, then applications.

- **Update.** Package update and upgrade, unattended upgrades with a reboot window (default 03:30 Eastern, at least 30 minutes from the connectors' 04:00 and 05:00 reboots and their weekly updates at 04:30 and 05:30, and outside the edge slots of 01:00 to 03:00).
- **Baseline.** User `cah-admin`, one public key, no password, root locked. sshd: no root login, no password login, `AllowUsers cah-admin`.
- **Harden.** `sshd -t && systemctl restart ssh` runs before anything is installed.
- **Docker Engine** from Docker's apt repository. The key file must hold exactly one key and its fingerprint must equal the pin (`docker_apt_key_fingerprint`) before the repository is trusted. `daemon.json`: `live-restore`, capped `json-file` logs, default bind address `127.0.0.1`, and **no `hosts` key**, so the Docker API is the local socket and nothing else.
- **Portainer CE**, pinned to an exact tag (`portainer_version`), from a compose file owned by cloud-init. Its one published port is `${PORTAINER_BIND:?}:9443:9443`, where the address is the droplet's private VPC address read from the metadata endpoint. If there is no private address nothing starts: there is no wildcard fallback. Memory limit and `no-new-privileges` are set.
- **No credential in user-data.** User-data is readable from the metadata endpoint and ends up in state. The daemons' credentials stay in Doppler (design section 6).

## 4. Before the switch can be turned on

These are decisions and changes outside this issue. The code refuses to run until the first two are done.

1. **Cost approval (the maintainer's, not this change).** Making `stage-3` the current phase in `docs/stages/approved.json`, and raising the DigitalOcean `approved_monthly_total` from 12.0 to 24.0 (29.0 with the bucket). `scripts/cost_raise.py` prints the diff.
2. **Cost gate allowlist (an approval edit).** `digitalocean_droplet` is a priced type and is allowed only in the files `approved.json` lists. `modules/docker-host/main.tf` must be added under `providers.digitalocean.allowed_sources.digitalocean_droplet`. **Until it is, the cost gate fails on this branch with `modules/docker-host/main.tf: digitalocean_droplet`**; this change deliberately does not edit `approved.json`.
3. **Cost gate support for the module (code).** `scripts/cost_check.py` counts only `twingate-connector` and `edge-host` module calls against the manifest's droplet entries, so a priced `workload` droplet entry in `cost.json` would be reported as a machine with no connector block. The gate needs a `docker-host` module kind with the same rules as edge-host (no `for_each`, `count` only as `local.on`, a plain `size` reference, and manifest entries that are 0 only when the switch is verified). Then `cost.json` gets the priced entry `{ "name": "workload", "kind": "droplet", "size": "s-1vcpu-2gb", "backups": false }` and `workload_approved` becomes `true`.
4. **The connectors' firewall.** DigitalOcean allows outbound traffic only when a rule permits it, and the connector firewall allows TCP 22 only to its own tag. Stack 10 must add `outbound_to_other_tags` for TCP 22 and TCP 9443 to the workload tag (the firewall module already supports it), behind a flag that defaults off, and apply it before the switch. The workload stack outputs `workload_tag` for this.
5. **Two outputs from stack 10.** The access stack does not output the Twingate remote network id or the admins group id yet; `remote_network_id` and `admin_group_id` are variables until it does.
6. **Plan policy and Spacelift.** The Spacelift stanza `cah-30-workloads`, its Doppler names (`DIGITALOCEAN_TOKEN`, `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, `ADMIN_SSH_PUBLIC_KEY`, `ADMIN_SSH_KEY_NAME`), and a read of the plan policy against this stack's plan (it creates a firewall with tag-sourced inbound rules only, so it should not hit the world-open inbound deny). `tests/test_secret_separation.py` names the stacks it accepts and needs the new name.
7. **The plan is read by the maintainer** before any apply.

## 5. After the first apply (verify; none of this has been run)

- `systemctl is-active docker` and `docker ps` show Portainer running; `/var/log/cah-docker-host-install.log` holds the outcome.
- `ss -ltn` shows Portainer on the private VPC address and port 9443 only, and nothing on `0.0.0.0` or `[::]` except sshd on 22 (sshd is reachable only through the cloud firewall's connector rule).
- From a machine with the Twingate client, SSH and the Portainer UI are reachable; from anywhere else, neither is.
- `unattended-upgrade --dry-run -d` lists the Docker origin as allowed (the origin spelling in `52cah-unattended-upgrades` is unverified).
- First Portainer visit: set the admin password within the first minutes (Portainer locks the first-run screen after a timeout), strong and unique, in the password manager.

## 6. Rollback

Set `workload_enabled = false` and apply: the droplet, firewall, tag, project attachment and both Twingate resources are destroyed in one run. The droplet holds nothing that is not in git, Doppler or (later) the bucket. Until the Spaces bucket exists, anything the daemons wrote to the droplet's disk is lost with it.

## 7. Settings and tests

Every variable is typed, validated and listed in [the settings reference](../wiki/Settings-Reference.md). Tests: `tofu test` in `stacks/30-workloads` and `modules/docker-host` (mocked providers: off plans nothing, on plans the expected resources, inputs are validated, the firewall has no inbound but the connector tag, no wildcard bind), and `tests/test_workloads_stack.py` (static guards, each with a negative case). Nothing here calls DigitalOcean, Twingate or Spacelift.
