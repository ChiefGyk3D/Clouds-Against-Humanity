# Spacelift and Doppler: how secrets reach a run

This page explains how the Spacelift stacks get the credentials they need, who holds each one, and how to rotate or change any of it. Read it before you touch a token, add a stack, or upgrade the Doppler CLI.

## 1. The idea in one paragraph

Spacelift runs `tofu plan` and `tofu apply`. The secrets that those runs need (the DigitalOcean token, the Twingate values) live in Doppler. Spacelift itself holds exactly one secret: a read-only Doppler service token. A hook script uses that token to fetch the other secrets at run time, puts them in the environment of the run, and hides them in the logs. Nothing secret is in this repository, and nothing applies from CI.

```
Doppler (clouds-against-humanity / prd)      holds every real secret
   ^  read-only service token
   |
Spacelift context cah-doppler                holds only that one token
   |  auto-attached to stacks labelled cah
   v
hook: scripts/spacelift/doppler-env.sh       fetches named secrets, masks them
   |
   v
tofu plan / apply                            sees them as environment variables
```

## 2. Who holds what

Values are never written here. This table is the inventory to check when a token expires.

| Secret | Lives in | Used by | Scope | Lifetime |
|---|---|---|---|---|
| `DIGITALOCEAN_TOKEN` | Doppler `prd` | stacks 00 and 10 (OpenTofu provider) | custom scopes, see [section 4a](#4a-digitalocean-token-scopes) | 90 days |
| Doppler service token `spacelift` | Spacelift context `cah-doppler`, variable `DOPPLER_TOKEN` (write-only) | the hook script | read-only, config `prd` only | 90 days |
| `TWINGATE_API_TOKEN` | Doppler `prd` | stack 10 | Twingate "Read, Write & Provision" key | 90 days |
| `TWINGATE_NETWORK` | Doppler `prd` | stack 10 (also exported as `TF_VAR_twingate_network`) | not a credential; the tenant name | none |
| `ADMIN_SSH_PUBLIC_KEY`, `ADMIN_SSH_KEY_NAME`, `ADMIN_USER_IDS` | Doppler `prd` | stack 10 (exported as `TF_VAR_admin_ssh_public_key`, `TF_VAR_admin_ssh_key_name` and `TF_VAR_admin_user_ids`) | not credentials, but account-specific | none |

The context also holds two plain variables, `DOPPLER_PROJECT` and `DOPPLER_CONFIG`.

Record the real expiry dates in your password manager, not in this repository. An expired token does not warn anyone; the next run just fails (see section 7).

## 3. Rules the script enforces

`scripts/spacelift/doppler-env.sh` is the only code that sees the token. It fails closed and does this:

- **Only tracked and destroy runs, only on `main`.** A pull request produces a proposed run, and planning executes code from the pull request. This repository is public, so a proposed run never gets a credential. The cost is that a pull request plan cannot talk to DigitalOcean; CI covers it with `tofu test` and mocked providers, and the real plan happens on `main` before you confirm.
- **Task runs get nothing.** A task runs an arbitrary command. If you need a task to hold a credential, add that deliberately and write it down here.
- **Named secrets only.** Each stack lists the exact names it needs in `.spacelift/config.yml`. A name must be a plain identifier.
- **Verified download.** The Doppler CLI is fetched from the official release over HTTPS and checked against the SHA-256 pinned in the script. A mismatch deletes the file and stops the run.
- **Masking.** Each fetched value is passed to Spacelift's `::add-mask` command so it is redacted in the logs.
- **Fetch again before apply.** After a run waits for your confirmation, the apply phase can start in a fresh container where the earlier work is gone. `before_apply` repeats the load.

## 4. One-time setup (already done for this repository)

1. Doppler project `clouds-against-humanity`, config `prd`, holding `DIGITALOCEAN_TOKEN` (Token A).
2. A read-only Doppler service token for that project and config, expiring in 90 days.
3. Spacelift context `cah-doppler` in the root space with the label `autoattach:cah`. Variables: `DOPPLER_TOKEN` (write-only secret), `DOPPLER_PROJECT=clouds-against-humanity`, `DOPPLER_CONFIG=prd`.
4. Spacelift stacks carry the label `cah`, so the context attaches itself.
5. This repository's `.spacelift/config.yml` and `scripts/spacelift/doppler-env.sh`.

## 4a. DigitalOcean token scopes

Create both tokens under DigitalOcean console, API, Tokens, Generate New Token, **Custom scopes** (never "Full access"). Pick exactly these.

**Token A** (write; Doppler `DIGITALOCEAN_TOKEN`, used only by Spacelift). One row per OpenTofu resource the stacks manage:

| Scope group | Actions to tick | Why |
|---|---|---|
| project | create, read, update, delete | `digitalocean_project` and `digitalocean_project_resources` |
| vpc | create, read, update, delete | `digitalocean_vpc`; droplet creation also reads it |
| firewall | create, read, update, delete | `digitalocean_firewall` |
| tag | create, read, delete | `digitalocean_tag` (tags have no update) |
| droplet | create, read, update, delete | `digitalocean_droplet` |
| ssh_key | **read** | the stack looks the admin key up by name (`data.digitalocean_ssh_key`) and never registers it, so create and delete are not needed |
| image, region, size | read | resolved when a droplet is created |
| actions | read | the provider polls droplet actions while it builds |

**Token B** (read only; interactive tooling and the `do-droplets` MCP server): `read` on the same groups, nothing else. It cannot change anything, so a leak costs you visibility, not infrastructure.

Derived from the resources in `modules/` and the stack roots (`data "digitalocean_ssh_key"`, `digitalocean_droplet`, `digitalocean_firewall`, `digitalocean_project`, `digitalocean_project_resources`, `digitalocean_tag`, `digitalocean_vpc`). Proven by the 2026-10-11 redeploy, which ran with exactly this token: `ssh_key: read` is enough for the lookup (without it the plan fails with `403`). If a plan fails with `401` or `403`, the error names the missing scope: add that one and update this table.

## 5. Rotation

Do these in order and never paste a token into a chat, an issue, a commit or a log.

### DigitalOcean token (Token A), every 90 days

1. DigitalOcean console, API, Tokens: generate a new token with the scopes in [section 4a](#4a-digitalocean-token-scopes) and a 90-day expiry.
2. Store it: `doppler secrets set DIGITALOCEAN_TOKEN -p clouds-against-humanity -c prd` (it prompts for the value, so it stays out of your shell history).
3. Trigger a run on stack 00 and read the plan. It should show no changes.
4. Revoke the old token in the console.

### Doppler service token, every 90 days

1. Doppler dashboard, project `clouds-against-humanity`, config `prd`, Access, Service Tokens: generate a new read-only token with a 90-day expiry.
2. Spacelift console, context `cah-doppler`: replace the value of `DOPPLER_TOKEN` (keep it write-only).
3. Trigger a run on stack 00. In the log, look for `doppler-env: loaded DIGITALOCEAN_TOKEN`.
4. Delete the old service token in Doppler.

### Twingate

Replace the value in Doppler. The next tracked run picks it up. Rotating the connector token recreates the connector droplet (see the stage 1 guide).

## 6. Changing things

### Add a secret to a stack

1. Add it to Doppler (`doppler secrets set NAME -p clouds-against-humanity -c prd`). Doppler only allows uppercase letters, digits and underscores in names.
2. If OpenTofu reads it as a variable, the environment variable must be exactly `TF_VAR_<variable name>`, which is lowercase. Write the argument as `TF_VAR_my_var=MY_VAR` and the hook fetches `MY_VAR` and exports it as `TF_VAR_my_var`. Plain `NAME` fetches and exports under the same name.
3. Add the argument to both the `before_init` and `before_apply` lines for that stack in `.spacelift/config.yml`. A test checks that the two lists match.
4. Open a pull request; merge once CI is green.

### Add a stack

1. Create the stack in Spacelift with the label `cah`, so the context attaches.
2. Add its entry to `.spacelift/config.yml`, keyed by the stack id.
3. Open a pull request.

### Upgrade the pinned Doppler CLI

1. Pick the release at <https://github.com/DopplerHQ/cli/releases>.
2. Download `checksums.txt` and its `.sig` from that release, verify the signature against Doppler's published key, and copy the `linux_amd64` and `linux_arm64` tarball hashes.
3. Update `CAH_DOPPLER_VERSION` and both `CAH_DOPPLER_SHA256_*` values in `scripts/spacelift/doppler-env.sh`.
4. Run the tests (`python3 -I -m pytest tests -q`) and open a pull request. The first tracked run after the merge proves the new binary on the real runner.

### Run the tests

```bash
python3 -I -m pytest tests -q
```

The script tests run it under plain `sh` with stubbed `doppler` and `curl`, and check that proposed runs, non-main branches, task runs and bad checksums all get nothing.

## 7. Troubleshooting

| What you see in the run log | What it means | Fix |
|---|---|---|
| `run type 'PROPOSED' does not get secrets; skipping` | A pull request plan. Expected. | Nothing. The plan then fails at the provider, by design. |
| `DOPPLER_TOKEN is not set; is the cah-doppler context attached?` | The context did not attach. | Check the stack has the label `cah` and the context has `autoattach:cah`. |
| `could not read NAME from Doppler` | The service token is expired or revoked, or `NAME` is missing in `prd`. | Rotate the service token (section 5) or add the secret. |
| `NAME is empty in Doppler` | The secret exists but has no value. | Set the value. |
| `checksum mismatch ... refusing to run it` | The download is not the pinned release. | Check your network path and the pinned hash. Do not bypass the check. |
| `401` or `403` from DigitalOcean during the plan | The token expired, or a custom scope is missing. | Rotate Token A, or add the scope the error names. |

## 8. Known limits and open checks

- **No OIDC on this plan.** Spacelift's run identity token is not issued to this account (checked with a task: the variable was absent). If the plan changes, the token fetch can switch to Doppler OIDC, so no long-lived token sits in Spacelift. Only the login step in `doppler-env.sh` would change.
- **The real trust boundary is Spacelift, not the script.** The script and `.spacelift/config.yml` are read from the branch being run, and the `cah-doppler` context is attached to every run type. Anyone who can push a branch or open a pull request can change either file to read `$DOPPLER_TOKEN` directly, so the script's run-type and branch checks only guard honest code. Today the repository owner is the only writer, which keeps the risk low. Keep it that way by doing all of the following:
  - **A push policy** on these stacks that ignores pull request events from forks, and ignores pull requests that do not come from a branch of this repository. Until it exists, do not let anyone else open pull requests that trigger runs.
  - **Branch protection** on `main` stays on (a pull request and `CI green` are required). Add a required review before giving anyone else write access.
  - **Keep the Doppler token read-only** and scoped to this one config, so a leak reaches only these secrets.
- **Masking must be confirmed on the first tracked run.** The script masks each value with Spacelift's documented `echo "::add-mask <value>"` command, which the runner is meant to consume without showing it. The documentation does not say the mask line itself is hidden from the log. After the first tracked run, search that run's log for the token prefix (`dop_v1_`) and confirm it never appears. If it does, revoke the token at once, then remove the `echo "::add-mask"` line and replace it with a different masking approach.
- **Unverified until the first tracked run:** that hooks run with `/mnt/workspace/source/` as the checkout path, and that the Alpine runner image has `curl`, `tar` and `sha256sum`. If either is wrong the run fails closed with a clear message; fix the path or the install step.
