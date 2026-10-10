# Stage 1: Access

## 1. What this stage builds

- One Twingate remote network (site), created by OpenTofu and named `access-nyc3`, and an existing DigitalOcean SSH key that the stack looks up by name (it does not register one). Both connectors share them.
- Two `s-1vcpu-1gb` droplets, `access-nyc3-connector-a` and `access-nyc3-connector-b`, each running a Twingate connector inside the VPC. Twingate recommends at least two active connectors, so one can be down without losing access. Each is created with `ubuntu-24-04-x64`, monitoring on, backups off and IPv6 off.
- A connector firewall, attached by the connector tag, with no inbound rules and eight outbound rules: the firewall module's five defaults (tcp 443, 80 and 53; udp 53 and 123) plus three Twingate ports (tcp 30000-31000, udp 19302-19308, udp 443). The baseline firewall also applies to the droplet through its own tag.
- A Twingate admin group, `cah-nyc3-admins`.
- Two per-host Twingate resources, one for each connector's private address, each limited to TCP port 22.

Cost: $12.00/month, approved total $12.00 (see [cost](../cost.md)).

What the tests prove (`tofu test`, no cloud account needed):

- There are zero inbound rules.
- Both droplets are named per instance, carry the baseline and connector tags at creation, and are listed in the project.
- The site is created once, in the stack, and shared by both connectors. The SSH key is looked up by name and never registered. The module's `instance` input accepts one lowercase letter or digit and nothing else.
- Each SSH resource allows only TCP 22, denies UDP and has ICMP off.
- Connector tokens never appear in module outputs. The output test pins the declared output names, so adding an output means editing that list on purpose.

## 2. Why there is no public SSH

DigitalOcean droplets always have a public address. You cannot remove it. So the control is a firewall that is attached by tag at creation and allows no inbound traffic at all. The droplet is created with the baseline tag, so there is no moment when it is open. You reach the host by its private IP through Twingate: the connector on the droplet dials out to Twingate, and your client reaches it through that outbound connection.

## 3. Accepted residual risk

The connector token appears in OpenTofu state and in the droplet's cloud-init user-data. It is marked sensitive, and the token is revocable and belongs to a single connector, so each of the two connectors has its own. Two things for you to do and check: keep the state in Spacelift, and in Spacelift restrict who can read the stack's state and outputs to the people who need it.

To rotate the token, replace `module.connector_a.twingate_connector_tokens.this` (or `module.connector_b...` for the other one). Rotate one connector at a time so the other keeps serving. Because the state lives in Spacelift, this is not a local `tofu apply` from a laptop. Do it as a Spacelift run with the replace option for that address (or taint the resource through Spacelift's run options), then read the plan before confirming.

Rotation is not free. The new token changes the rendered cloud-init `user_data`, and per the DigitalOcean provider's behavior a `user_data` change forces a new droplet; confirm in the plan output before approving the run. If so, rotation destroys and recreates that connector's droplet: expect a short outage of that connector and probably a new private IP, and its SSH Twingate resource follows the new address. The other connector keeps Twingate access up meanwhile.

## 4. Vendor facts to record when verified

Record each date here when you check it.

Verified so far:

- Twingate provider 3.8.0, verified 2026-10-10: the provider reads `TWINGATE_API_TOKEN` and `TWINGATE_NETWORK`. The DigitalOcean provider reads `DIGITALOCEAN_TOKEN`.
- In provider 3.8.0 the `protocols` setting on `twingate_resource` is an attribute object, not a block. The SSH resources in `stacks/10-access/main.tf` are written that way.
- `twingate_network` must be the bare subdomain (lowercase letters, digits, hyphens), not a URL. It is validated in the connector module and again in the stack.
- The cloud-init install runs under `bash -o pipefail` with `curl -fsSL --proto '=https' --tlsv1.2 --retry 5`, so a failed download shows up as a failed cloud-init run instead of a silent half-install.

Verify before apply (not confirmed yet):

- [ ] The connector firewall's outbound ports (tcp 30000-31000, udp 19302-19308, udp 443 in `stacks/10-access/main.tf`) against Twingate's current firewall requirements page.
  Verified on:
- [ ] `TWINGATE_LABEL_DEPLOYED_BY` in the install command in `modules/twingate-connector/cloud-init.yaml.tftpl` is still a supported setting.
  Verified on:
- [ ] Whether the install page expects the bare subdomain or a full URL for `TWINGATE_NETWORK`.
  Verified on:
- [ ] The Twingate install page title and date. It was read on 2026-10-10 through a summarizing fetch (page title: "Minecraft Server with Twingate (Linux)"), not directly, so read the page itself.
  Verified on:

Known follow-up: the provider emits a deprecation warning when `access_group` is read on `twingate_resource`. Replace it with the provider's current access setting before a provider upgrade removes it.

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
4. Check that no Twingate site named `access-<region>` (for example `access-nyc3`) exists in the admin console. OpenTofu now creates the site itself; a hand-made site with that name makes the apply fail or leaves a duplicate, so rename or delete the hand-made one first.
5. Trigger a tracked run on `main`; it stops after the plan because autodeploy is off. Proposed runs get no credentials by design. Read the plan, then confirm.

## 6. Verify

1. Both connectors show online in the Twingate admin console, under the one site `access-<region>`.
2. From a Twingate client: `ssh <user>@<connector private IP>` works for each connector's private IP (`connector_private_ips` output, keys `a` and `b`).
3. From outside Twingate: `nmap -Pn -p 22,80,443 <connector public IP>` shows the ports filtered on both droplets. Scanning your own droplet is authorized.
4. `python3 -I scripts/cost_check.py --root .` still reports `$12.00`.

## 7. Stage 3 note

Later droplets will need an inbound rule allowing TCP 22 from the connector tag, because DigitalOcean firewalls also filter VPC-internal traffic. The baseline firewall's zero inbound rules apply between droplets in the same VPC too.

## 8. Rollback

Destroy `cah-10-access` first, then `cah-00-foundation` if you want stage 0 gone too: stage 0's VPC, project and tag are in use by stage 1, so the order matters. The connector tokens die with the connectors, and the site goes with the stack. The SSH key was never created by the stack, so it stays on the account.
