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

- **Only tracked and destroy runs, only on `main`.** A pull request produces a proposed run, and planning executes code from the pull request. This repository is public, so the script fetches no secret for a proposed run. That is not the same as the run holding no credential: the `cah-doppler` context is attached to every run type, so `DOPPLER_TOKEN` is present, and branch-controlled hook code could read it (section 8). The cost is that a pull request plan cannot talk to DigitalOcean; CI covers it with `tofu test` and mocked providers, and the real plan happens on `main` before you confirm. Once the push policy in section 9 is attached, Spacelift does not start a proposed run at all, so this rule becomes the second line of defence rather than the only one.
- **Task runs get nothing.** A task runs an arbitrary command. If you need a task to hold a credential, add that deliberately and write it down here.
- **Named secrets only.** Each stack lists the exact names it needs in `.spacelift/config.yml`. A name must be a plain identifier.
- **Verified download.** The Doppler CLI is fetched from the official release over HTTPS and checked against the SHA-256 pinned in the script. A mismatch deletes the file and stops the run.
- **Masking.** Each fetched value is passed to Spacelift's `::add-mask` command so it is redacted in the logs.
- **Fetch again before apply.** After a run waits for your confirmation, the apply phase can start in a fresh container where the earlier work is gone. `before_apply` repeats the load.

## 4. One-time setup (already done for this repository)

1. Doppler project `clouds-against-humanity`, config `prd`, holding `DIGITALOCEAN_TOKEN` (Token A).
2. A read-only Doppler service token for that project and config, expiring in 90 days.
3. Spacelift context `cah-doppler` in the root space with the label `autoattach:cah`. Variables: `DOPPLER_TOKEN` (write-only secret), `DOPPLER_PROJECT=clouds-against-humanity`, `DOPPLER_CONFIG=prd`. <!-- identifier-check: ignore (a Doppler project name, not a GCP project id) -->
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

1. Create the stack in Spacelift with the label `cah`, so the context attaches, and so does the push policy if it carries `autoattach:cah` (section 9).
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
| `run type 'PROPOSED' does not get secrets; skipping` | A pull request plan. Expected without the push policy. | Attach the push policy (section 9) and proposed runs stop happening. Without it, the plan fails at the provider, by design. |
| `DOPPLER_TOKEN is not set; is the cah-doppler context attached?` | The context did not attach. | Check the stack has the label `cah` and the context has `autoattach:cah`. |
| `could not read NAME from Doppler` | The service token is expired or revoked, or `NAME` is missing in `prd`. | Rotate the service token (section 5) or add the secret. |
| `NAME is empty in Doppler` | The secret exists but has no value. | Set the value. |
| `checksum mismatch ... refusing to run it` | The download is not the pinned release. | Check your network path and the pinned hash. Do not bypass the check. |
| `401` or `403` from DigitalOcean during the plan | The token expired, or a custom scope is missing. | Rotate Token A, or add the scope the error names. |

## 8. Known limits and open checks

- **No OIDC on this plan.** Spacelift's run identity token is not issued to this account (checked with a task: the variable was absent). If the plan changes, the token fetch can switch to Doppler OIDC, so no long-lived token sits in Spacelift. Only the login step in `doppler-env.sh` would change.
- **The real trust boundary is Spacelift, not the script.** The script and `.spacelift/config.yml` are read from the branch being run, and the `cah-doppler` context is attached to every run type. Anyone who can push a branch or open a pull request can change either file to read `$DOPPLER_TOKEN` directly, so the script's run-type and branch checks only guard honest code. Today the repository owner is the only writer, which keeps the risk low. Keep it that way by doing all of the following:
  - **The push policy** in section 9, attached to every stack. It never proposes a run, so no pull request's code runs in Spacelift next to the context, from a fork or from a branch of this repository. Until it is attached, do not let anyone else open pull requests.
  - **Branch protection** on `main` stays on (a pull request and `CI green` are required). Add a required review before giving anyone else write access.
  - **Keep the Doppler token read-only** and scoped to this one config, so a leak reaches only these secrets.
- **Masking must be confirmed on the first tracked run.** The script masks each value with Spacelift's documented `echo "::add-mask <value>"` command, which the runner is meant to consume without showing it. The documentation does not say the mask line itself is hidden from the log. After the first tracked run, search that run's log for the token prefix (`dop_v1_`) and confirm it never appears. If it does, revoke the token at once, then remove the `echo "::add-mask"` line and replace it with a different masking approach.
- **Unverified until the first tracked run:** that hooks run with `/mnt/workspace/source/` as the checkout path, and that the Alpine runner image has `curl`, `tar` and `sha256sum`. If either is wrong the run fails closed with a clear message; fix the path or the install step.

## 8a. More than one cloud

Everything above describes one cloud (DigitalOcean) and one Doppler token. When AWS, Azure or GCP stacks join (issue #22, design section 4 point 4), do not add their credentials to the existing config. Nothing here changes the live stacks or the `cah-doppler` context.

### The rule

One Doppler config and one Spacelift context **per cloud**, each with its own read-only service token, attached only to that cloud's stacks.

The names below are a **convention proposed here, not something already set up or verified**:

| Cloud | Doppler project / config | Spacelift context | Stack names | Attached to |
|---|---|---|---|---|
| DigitalOcean | the existing `prd` setup, left as is | `cah-doppler` (existing, not renamed) | `cah-00-...`, `cah-10-...` | label `cah` today |
| AWS | project `cah`, config `dev_aws` | `cah-doppler-aws` | `cah-aws-...` | a cloud label such as `cah-aws`, not the DigitalOcean one |
| Azure, GCP | same pattern: `dev_azure`, `dev_gcp` | `cah-doppler-azure`, `cah-doppler-gcp` | `cah-azure-...`, `cah-gcp-...` | their own labels |

Each context holds the same three variables as today (`DOPPLER_TOKEN`, write-only; `DOPPLER_PROJECT`; `DOPPLER_CONFIG`), with values for that cloud only. The hook script is unchanged: it reads those three from the environment, so which config a run can read is decided entirely by which context is attached. The existing auto-attach on the `cah` label must not also catch the new clouds' stacks, or one stack would receive two tokens; give them a different label.

**Attach the push policy first.** Section 9 attaches the push policy to the `cah` label (`autoattach:cah`), so changing the label also drops that auto-attachment. Before attaching any secret context to a new cloud's stacks, attach the policy to them manually or extend its autoattach labels to the new label. A stack that has a secret context without the policy would let a pull request's run sit next to the token.

### Prefer a native integration for the cloud login

Where Spacelift offers it, a native cloud integration beats any stored key, because the credential is short-lived and nothing is kept in Doppler. For AWS that means Spacelift assuming an IAM role in your account, with a per-stack external id in the role's trust policy, so one stack's role cannot be used by another. Doppler would then hold only non-credential settings for that cloud.

**Unverified:** whether the maintainer's Spacelift plan includes cloud integrations. The DigitalOcean setup used Doppler because the plan issued no run-level identity token, which is a separate feature. The answer is an open check in issue #22 (phase 0). This is a gate, not a preference (design section 10, decision 6): AWS stack creation waits for that check, so no long-lived AWS key is needed. If the integration is not available, return to the maintainer; falling back to a static key in a separate Doppler config is a new decision, not the default.

### Why separate contexts

The Doppler token in a context can read the **whole config**, not just the names a stack asks for (the hook only fetches named secrets, but code on a tracked run can use the token directly; see section 8). If the AWS keys sat in the DigitalOcean config, a compromised DigitalOcean run would reach AWS too. Per-cloud configs and contexts keep a compromise inside one cloud's control plane.

### What the test proves, and what it does not

`tests/test_secret_separation.py` parses `.spacelift/config.yml` with PyYAML (a pinned CI test dependency) and fails closed: any shape it does not understand is a failure, not a skip. It fails if:

- a stack name is not one of the known DigitalOcean stacks or a `cah-aws-*`, `cah-azure-*` or `cah-gcp-*` name (a typo cannot inherit DigitalOcean's permissions);
- a hook is not exactly the source line followed by one plain `cah_doppler_env NAME ...` call (extra calls, shell operators, quoting, variables, YAML anchors and aliases, duplicate keys and non-string entries are all refused);
- a stack requests a name with another cloud's prefix (`AWS_` on a DigitalOcean stack, `DIGITALOCEAN_` on `cah-aws-*`, and so on; the prefix table is in the test), or any name outside its own cloud's prefixes and the exact shared names (`TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, `ADMIN_SSH_PUBLIC_KEY`, `ADMIN_SSH_KEY_NAME`, `ADMIN_USER_IDS`);
- `before_init` and `before_apply` differ (the apply phase can run in a fresh container, so both must load the same names);
- the hook script assigns `DOPPLER_PROJECT`, `DOPPLER_CONFIG` or `DOPPLER_TOKEN`, or hard-codes a config name.

It proves the **declared requests** are separated. It does **not** prove that a Doppler token cannot read another config, that a context is attached to the right stacks, or that the secret names sit in the right Doppler config. Those are Doppler and Spacelift settings. The design asks for "request another cloud's secret from one stack and show the secret store refuses it"; that needs live Doppler and Spacelift, so it is a manual check to run and record when the first second cloud is wired up: from an AWS stack run, ask for `DIGITALOCEAN_TOKEN` through the AWS context and expect the hook to fail with `could not read DIGITALOCEAN_TOKEN from Doppler`.

## 9. The push policy

`.spacelift/policies/push.rego` decides which Git events start a Spacelift run. Spacelift does not read it from the repository; it is a policy object in Spacelift with this file as its body. The tests next to it (`push_test.rego`) run on every pull request through the `policy (OPA)` job of git-your-ship-together's `tofu-ci.yml`.

What it decides:

| Event | Outcome |
|---|---|
| Push or merge to `main` that changes the stack's project root, `modules/`, `scripts/spacelift/` or `.spacelift/` | Tracked run. It stops after the plan for you to confirm, as before. |
| Push or merge to `main` that changes only other files (docs, the wiki, the README, another stack) | Nothing. |
| Any pull request, whatever it changes | Nothing. No proposed run, so no red check from a plan that could only fail without credentials. |
| A tag, or a push to any other branch | Nothing. |
| A pull request from a fork | Nothing. Spacelift runs a fork's pull request only when a push policy defines `allow_fork`, and this one never does. |

**Plan check first.** Spacelift's documentation (read 2026-10-12) says the Git push policy type is available only to paid Spacelift accounts, and that policies live under **Enforce Guardrails > Policies**, visible to Spacelift admins. On the free plan there is no Policies entry to find. The free-plan route is below; the policy file stays in the repository, tested, for the day the plan changes.

Why it exists: on 2026-10-12 a pull request that changed only `docs/wiki/` and the README got a red `spacelift/cah-10-access` check. The proposed run had no credentials by design, so it could only fail. Pull requests are already covered by `tofu test` with mocked providers in GitHub Actions, so a proposed run adds a failure and nothing else. Never proposing also closes the gap described in section 8: no pull request's code ever runs in Spacelift next to the Doppler context.

### Free plan: narrow each stack's project root and globs

Without a push policy, Spacelift's built-in behaviour starts a stack's runs only when a push or pull request changes a file inside the stack's **project root** or matching one of its **project globs**. A docs-only pull request reaching `cah-10-access` means that stack's root or globs cover more than the stack. For each stack, open it, then **Settings**, and set:

| Stack | Project root | Project globs |
|---|---|---|
| `cah-00-foundation` | `stacks/00-foundation` | `modules/**`, `scripts/spacelift/**`, `.spacelift/**` |
| `cah-10-access` | `stacks/10-access` | `modules/**`, `scripts/spacelift/**`, `.spacelift/**` |

Remove any other glob, such as `**`, `*` or one that covers `docs/`. Then a docs-only pull request or merge starts nothing. What this cannot do is the other half of the policy: a pull request that does change a stack still gets a proposed run, which still fails at the provider without credentials. On the free plan that red check is expected on those pull requests only; branch protection requires only `CI green`, so it does not block a merge, and `tofu test` in CI is the real test. The exposure in section 8 also remains: that proposed run executes the pull request's code with the Doppler context attached, so keep this repository single-writer.

### Paid plan: attach the policy (once)

1. In Spacelift, open **Enforce Guardrails > Policies**, choose **Create policy**, name it `cah-push`, and pick the type **Git push**.
2. Paste the contents of `.spacelift/policies/push.rego` as the body. Do not paste `push_test.rego`; it is only for CI.
3. Add the label `autoattach:cah`, so it attaches to every stack labelled `cah`, the same way the Doppler context does. Or attach it by hand to `cah-00-foundation` and `cah-10-access`.
4. Detach any other Git push policy from those stacks. With more than one attached, the outcome is a combination of both and is no longer what the tests describe.
5. When the policy changes in a pull request, paste the new body into the same policy after the merge. The file in the repository is the reviewed copy, not the live one; a check on the next tracked run is the only proof they match.

### Verify it

- Open a pull request that changes only a Markdown file. No `spacelift/...` check should appear on it.
- Merge a change under `stacks/10-access/`. `cah-10-access` should start a tracked run that stops for confirmation.
- The policy sets `sample := true`, so Spacelift keeps recent inputs in the policy workbench. Open one and confirm that `input.push.branch`, `input.push.affected_files` and `input.stack.project_root` look the way the policy assumes. The input shape was taken from Spacelift's published example policies, not from a real event on this account, so check it once.

### Run the tests locally

```bash
opa test .spacelift/policies -v
opa check --strict .spacelift/policies
opa fmt --list --fail .spacelift/policies
```

Use OPA 1.21.0, the version CI pins (`opa_linux_amd64_static`, SHA-256 `5eef70644868bb04d0556bcc795ee42f2ab379e73f51d1bfa30f83e1305bc9b9`).

## 9a. The plan policy

`.spacelift/policies/plan.rego` decides whether a plan may be applied. Like the push policy, it is a policy object in Spacelift with this file as its body; Spacelift does not read it from the repository. Its tests (`plan_test.rego`) run on every pull request in the same `policy (OPA)` CI job.

Why it exists: a careless pull request could open a port on a connector. The firewall module's tests catch that after the fact, in CI, for the code they exercise. The plan policy checks the plan Spacelift is about to apply, so a tracked run with an open port is denied before anyone can confirm the apply.

It denies a created or updated resource that is:

| Resource | Denied when |
|---|---|
| `digitalocean_firewall` | An inbound rule has any source other than a tag: a source address (and `0.0.0.0/0` or `::/0` is called out as the whole internet), a droplet id, a load balancer or a Kubernetes cluster. The firewall module only ever emits `source_tags`, so a tag-scoped rule passes. |
| `aws_vpc_security_group_ingress_rule`, `aws_security_group_rule` (ingress), `aws_security_group` (inline ingress) | The source is a CIDR range, IPv4 or IPv6. A reference to a security group passes. |
| `digitalocean_droplet` | `ipv6 = true`. |
| `aws_vpc`, `aws_subnet`, `aws_instance` | The plan turns on an IPv6 range or address. |

For those rules, deletes and no-ops are ignored: removing a rule never opens anything. Two more rules, the destroy guard and the autodeploy guard (issue #92), turn "locked and manual" from a convention into a rule:

| Guard | Denied when |
|---|---|
| Destroy | The plan deletes, or replaces (the delete half counts, in either order), a `digitalocean_vpc`, `digitalocean_project`, `digitalocean_firewall`, `twingate_remote_network`, `aws_vpc` or `aws_security_group`, or any resource whose tags contain `protected` (a DigitalOcean tag list, or an AWS tag map with that key; the tags are read from the values being destroyed). Droplets are deliberately not protected: a connector replace is a normal, reviewed event. Creates, updates and no-ops never trigger it. |
| Autodeploy | The stack has autodeploy on. Spacelift's plan policy input documents `input.spacelift.stack.autodeploy` (a required field), so this is a real check on the stack the plan belongs to. It blocks the apply; it cannot stop someone creating a stack with autodeploy on, so the setting is also enforced where stacks are made (the stack factory, issue #96). |

Each message names the resource address (or the stack) and says what a human must do. I have not seen a real plan input in Spacelift yet: the field paths follow the published policy contract, and the fixtures in `plan_test.rego` follow it too. Keep a real plan in the policy workbench (the `sample` rule) and compare the first time the policy is attached.

**Plan check first.** Spacelift's documentation lists policies under **Enforce Guardrails > Policies**, and the push policy type is paid-plan only (section 9). I have not confirmed whether the plan policy type is available on the maintainer's plan; if **Create policy** offers no **Plan** type, the policy stays in the repository, tested, until the plan changes. Until it is attached, the firewall module's own tests in CI are the only check on inbound rules, and they run on the pull request, not on the plan Spacelift applies.

### Attach it (once)

1. In Spacelift, open **Enforce Guardrails > Policies**, choose **Create policy**, name it `cah-plan`, and pick the type **Plan**.
2. Paste the contents of `.spacelift/policies/plan.rego` as the body. Do not paste `plan_test.rego`.
3. Add the label `autoattach:cah`, so it attaches to every stack labelled `cah`, or attach it by hand to each stack.
4. When the policy changes in a pull request, paste the new body into the same policy after the merge. The file in the repository is the reviewed copy, not the live one.

### A deliberate exception

A deliberate inbound rule is allowed only by a reviewed code change. Add the exact resource address, as the plan shows it (for example `module.fw.digitalocean_firewall.this`), to `inbound_allowlist` in `plan.rego`, in a pull request. Every entry needs a threat-model note (`docs/wiki/Threat-Model.md`) naming the port, the source and the reason, and a review. After the merge, paste the new body into Spacelift. There is no stack label, environment variable or plan field that grants an exception, on purpose: a branch must not be able to grant its own. The list is empty today. The IPv6 checks have no exception.

A deliberate destroy works the same way, with its own list: add the exact resource address of the protected resource to `destroy_allowlist` in `plan.rego`, in a pull request that names the address and the reason, and paste the new body into Spacelift after the merge. The denial message says the same. Remove the entry once the change has applied, so the next plan is guarded again. Other addresses stay denied while one is allowlisted. The autodeploy guard has no exception: turn autodeploy off on the stack.

### Reading a denial

A denial names the resource address and the rule, for example:

```text
module.fw.digitalocean_firewall.this: inbound rule tcp/8080 opens the port to the whole internet (address 0.0.0.0/0). Inbound on core tags must come from a tag only.
```

Find that address in the plan, then change the code so the rule uses a tag source (or, for a reviewed exception, see above). Messages carry addresses and rule shapes only, never a secret.

### Verify it

The input shape (`input.terraform.resource_changes`, each with `address`, `type`, and `change.actions` and `change.after`) comes from Spacelift's published plan-policy contract and the Terraform JSON plan format, not from a real run on this account. After attaching it, check those fields against a real run's plan input in the policy workbench (the policy sets `sample := true`, so Spacelift keeps recent inputs). Local tests are the same as section 9: `opa test .spacelift/policies -v`.
