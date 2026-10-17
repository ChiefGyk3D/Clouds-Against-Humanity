# Troubleshooting index

> Before this page: [Lessons learned](Lessons-Learned.md) tells the stories behind many of these rows, and [Spacelift](Spacelift.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) explain the machinery that prints the messages.

This page is a lookup table: you see something wrong, you find the row that matches, and the last column says where the fix is written down. Every row comes from something documented in this repository, either a failure that happened during the build or one of the [labs](Labs-Break-It-on-Purpose.md) that breaks things on purpose. Nothing here is a general guess about how these tools can fail. If your symptom is not in the table, that is a gap worth an issue.

Two habits that make the table faster to use:

- **Read the exact message.** Several rows differ only by the status code or one word (`403` against `422`, `skip` against `fail`).
- **Find which layer printed it.** A line starting `doppler-env:` or `cost-check:` is this repository's own script. A `422` or `403` is DigitalOcean's API. A `fail` with a red box is `tofu test`. Each layer has its own section below.

Runbook links go to the files in the repository, outside the wiki: [Spacelift and Doppler secrets](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md), [Stage 0](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md) and [Stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md).

## Spacelift runs

| Symptom | Likely cause | Where to look |
|---|---|---|
| A red `spacelift/cah-10-access` check on a pull request that changed only docs | The stack's project root or project globs cover more than the stack, so a docs-only change reaches it. The proposed run has no credentials by design and can only fail. | [Lessons learned, "A red check from a run that could never pass"](Lessons-Learned.md#10-a-red-check-from-a-run-that-could-never-pass); the free-plan table of roots and globs is in [runbook section 9](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#9-the-push-policy) |
| A red Spacelift check on a pull request that does change a stack, and every GitHub Actions job is green | On the free plan the push policy cannot be attached, so a pull request that changes a stack still gets a proposed run that fails at the provider. Branch protection requires only `CI green`, so it does not block the merge. | [Spacelift, "Push policies: paid plan versus free plan"](Spacelift.md#push-policies-paid-plan-versus-free-plan) |
| `push.rego` is in the repository and tests pass, but Spacelift behaves as if it did not exist; or there is no Policies menu | Push policies are a paid Spacelift feature. Spacelift reads policies from its own store, not from the repository, so the file takes effect only once it is created there. | [Lessons learned, "Then a second surprise"](Lessons-Learned.md#10-a-red-check-from-a-run-that-could-never-pass); [Spacelift, push policies](Spacelift.md#push-policies-paid-plan-versus-free-plan) |
| A second run for the same stack sits queued behind another one you did not start | A stack dependency starts its own run when the stack it depends on finishes. Starting one by hand queued a duplicate. | [Lessons learned, section 9, "A stack dependency starts its own run"](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true); check the stack's run list before you trigger anything |
| A tracked run reaches the plan and then just waits | Autodeploy is off on purpose. A human reads the plan and confirms or discards. | [Spacelift, "Why autodeploy is off"](Spacelift.md#why-autodeploy-is-off) |
| The plan phase had its secrets but the apply phase does not | The apply can start in a fresh container where the plan phase's environment is gone. Both `before_init` and `before_apply` must load the same list. | [Spacelift, "Why `before_apply` fetches secrets again"](Spacelift.md#why-before_apply-fetches-secrets-again) |
| The run log lacks the Doppler token or a variable that should be there, on a plan that should have it | The run was not a tracked or destroy run on `main`, so the hook gave it nothing. Check the run type and the branch first. | [Doppler and secrets, "How the hook works"](Doppler-and-Secrets.md#how-the-hook-works) |
| A design that relies on a Spacelift run identity token (OIDC) finds no token in the environment | The run identity token is not issued on this Spacelift plan. It is a plan limit, not a misconfiguration. | [Lessons learned, "The plan said no OIDC"](Lessons-Learned.md#7-the-plan-said-no-oidc); [Spacelift, "No OIDC on this plan"](Spacelift.md#no-oidc-on-this-plan) |

## Doppler and the secrets hook

| Symptom | Likely cause | Where to look |
|---|---|---|
| `run type 'PROPOSED' does not get secrets; skipping` | A pull request plan. Expected: proposed runs get no credentials, and the plan then fails at the provider. | [Runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting); [Spacelift, "Why a pull request plan gets no credentials"](Spacelift.md#why-a-pull-request-plan-gets-no-credentials) |
| `DOPPLER_TOKEN is not set; is the cah-doppler context attached?` (a missing environment variable) | The context did not attach to the stack. Check that the stack has the label `cah` and the context has `autoattach:cah`. | [Runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting); [Spacelift, "Adding a stack"](Spacelift.md#adding-a-stack) |
| `could not read NAME from Doppler` | The service token is expired or revoked, or `NAME` is missing from the `prd` config. An expired token warns nobody; the next run just fails. | [Doppler and secrets, "Rotation, in short"](Doppler-and-Secrets.md#rotation-in-short) and [runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting) |
| `NAME is empty in Doppler` | The secret exists but has no value. | [Runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting) |
| `checksum mismatch ... refusing to run it` | The downloaded Doppler CLI is not the pinned release. Do not bypass the check. | [Doppler and secrets, "How the hook works", step 3](Doppler-and-Secrets.md#how-the-hook-works); [runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting) |
| A secret is in Doppler but OpenTofu behaves as if the variable were never set | Case. OpenTofu reads variable `foo` only from the exact name `TF_VAR_foo`, and Doppler names are uppercase. The hook maps them with `TF_VAR_foo=FOO`. | [Lessons learned, "Doppler names are uppercase, OpenTofu variables are not"](Lessons-Learned.md#6-doppler-names-are-uppercase-opentofu-variables-are-not) |
| The token prefix `dop_v1_` appears in a run log | Masking did not work. Revoke the token at once and change the masking approach. | [Doppler and secrets, "First run checks"](Doppler-and-Secrets.md#first-run-checks); [Lessons learned, section 8](Lessons-Learned.md#8-masked-in-logs-needs-to-be-proven-not-assumed) |
| `401` or `403` from DigitalOcean during the plan | The token expired, or a custom scope is missing. The token cannot be edited after creation, only replaced. A `403` reading SSH keys meant the `ssh_key: read` scope was missing. | [Runbook section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#7-troubleshooting); [Lessons learned, "Token scopes are proven by a run"](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true) |

## tofu test failures

| Symptom | Likely cause | Where to look |
|---|---|---|
| `Invalid function argument ... r.source_tags is null`, then `0 passed, 1 failed, 11 skipped` | An inbound rule written with an address instead of a source tag breaks the module's output code before the real assertion is reached. The test failed for the wrong reason but still protected you. | [Labs: Lab 1](Labs-Break-It-on-Purpose.md#lab-1-open-the-firewall) |
| `Missing expected failure ... was expected to report an error but did not` | A guard was loosened. The test that expects a bad input to be refused did not get a refusal. | [Labs: Lab 2](Labs-Break-It-on-Purpose.md#lab-2-let-a-private-network-be-public) |
| Tests marked `skip` after one failed | A failing test stops the rest of its file. Read `skip` as "not checked", never as "fine". | [Labs: Lab 1](Labs-Break-It-on-Purpose.md#lab-1-open-the-firewall) and [Lab 2, "What to take away"](Labs-Break-It-on-Purpose.md#lab-2-let-a-private-network-be-public) |
| `tofu test` seems to need a cloud account or a token | It should not. Every test file mocks its providers, which return made-up IDs, so the tests need no credential and cost nothing. Run `init -backend=false` first. | [OpenTofu, stacks and modules, "Tests without a cloud account"](OpenTofu-Stacks-and-Modules.md#tests-without-a-cloud-account) |
| After adding a Rego rule about pull requests, an unrelated policy test fails (for example "push to another branch starts nothing") | `null` is neither `false` nor undefined in Rego, and every test input carries `"pull_request": null`, so the new rule fires on every event. | [Labs: Lab 4](Labs-Break-It-on-Purpose.md#lab-4-let-a-pull-request-start-a-run) |
| Three `test_non_main_branch_gets_nothing` cases fail in `tests/test_doppler_env.py` | The branch check in the hook was removed or weakened. The cases include `mainline`, which a sloppy prefix check would accept. | [Labs: Lab 5](Labs-Break-It-on-Purpose.md#lab-5-let-the-secrets-hook-run-on-the-wrong-branch) |

## Cost gate failures

The gate is `scripts/cost_check.py`. Every message starts with `cost-check:`, and a failing run exits 1. The summary line prints even when it fails, so read the lines above it.

| Message | What it means | Where to look |
|---|---|---|
| `resource type not on the free list or outside its allowed file: <file>: digitalocean_<type>` | A paid or unknown `digitalocean_*` resource type, or a droplet outside `modules/twingate-connector/main.tf`. The total can still read the old number, because the gate has no price for it and treats unknown as a failure, not zero. | [Labs: Lab 3](Labs-Break-It-on-Purpose.md#lab-3-sneak-in-something-that-costs-money); [CI, tests and the cost gate, "Key ideas"](CI-Tests-and-Cost-Gate.md#the-cost-gate) |
| `planned $X is above approved $Y` | The priced resources add up to more than `approved_monthly_total` in `docs/stages/approved.json`. Raising it is a reviewed diff, not a quiet edit. | [How money works, "Approve before it exists, not after"](How-Money-Works-in-the-Cloud.md#3-approve-before-it-exists-not-after); [CI, cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) |
| `approved total is above the ceiling` | `approved_monthly_total` was raised past the written ceiling ($30). | [How money works, "A ceiling, written down"](How-Money-Works-in-the-Cloud.md#2-a-ceiling-written-down) |
| `N twingate-connector module block(s) but M droplet entr(ies) in the cost manifests; they must match` | The code and `stacks/*/cost.json` disagree about how many connectors exist. Adding a third `module` block fails this; adding a third manifest entry alone fails it the other way. Neither is "the ceiling". | [Labs: Lab 3, part 2](Labs-Break-It-on-Purpose.md#lab-3-sneak-in-something-that-costs-money) |
| `module '<name>' uses count` or `for_each; the connector is costed as a single instance` | A repeated connector module would be priced once. The gate refuses it. | [CI, cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) (the "Connector module count" decision in the flowchart) |
| `module '<name>' has a non-local source` | The gate reads only local modules. A remote source is something it cannot read, so it is refused. | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) ("Only local module sources"); [CI, cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) |
| `*.tf.json cannot be read by this gate and is refused` | The gate parses `.tf` files with regular expressions and does not read the JSON form. | [CI, "What the gate cannot do"](CI-Tests-and-Cost-Gate.md#what-the-gate-cannot-do) |
| `no price for size '<size>'`, `no price model for kind ...`, or `backups requested but the backup price fraction is unverified` | A droplet size missing from `docs/cost-prices.json`, a resource kind the gate cannot price, or a backup-enabled droplet while backup pricing is marked unverified. | [CI, cost gate, "Key ideas"](CI-Tests-and-Cost-Gate.md#the-cost-gate) |
| `no stacks/*/cost.json manifest found; at least one is required` | The gate has nothing to total, which it treats as a failure rather than a pass. | [CI, cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) |

## Twingate connectors and SSH

| Symptom | Likely cause | Where to look |
|---|---|---|
| A connector shows offline in the Twingate admin console (not online) | The install did not finish, the service is down, or the token was rotated. Try the other connector first, since SSH to a connector goes through Twingate. | [Stage 1, section 6a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#6a-if-a-connector-shows-offline); [Twingate, "Verify it yourself"](Twingate.md#verify-it-yourself) |
| `systemctl status twingate-connector` says "Unit not found" | The installer never finished. | [Stage 1, section 6a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#6a-if-a-connector-shows-offline) (read `/var/log/cah-connector-install.log` and `/var/log/cloud-init-output.log`) |
| The `twingate-connector` package is installed, but there is no `/etc/twingate/connector.conf` and the service never started, yet the log said success | The old install piped a vendor script into `bash`, which can swallow the rest of the script, and the pipeline's exit status hid the failure. Cloud-init now writes the file itself and counts success only if the service is active. | [Lessons learned, section 1](Lessons-Learned.md#1-curl--bash-reported-success-and-installed-nothing-useful) |
| The install fails loudly on the repository key check | The pinned fingerprint no longer matches, which is what the check is for. Confirm the new fingerprint with Twingate before updating the pin. | [Stage 1, section 2b](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#2b-how-the-connector-is-installed-and-updated) |
| Both connectors are down | There is no way in, and there is deliberately no console password. The droplets are stateless, so the recovery is to rebuild the affected one through a Spacelift run and read the plan first. | [Stage 1, section 6a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#6a-if-a-connector-shows-offline); [Twingate, "Two connectors, not one"](Twingate.md#two-connectors-not-one) |
| An apply fails because a Twingate site named `access-<region>` already exists, or you end up with two | A hand-made site with that name collides with the one OpenTofu now creates. Delete or rename the hand-made one before the apply. | [Lessons learned, section 4](Lessons-Learned.md#4-a-hand-made-twingate-site-collides-with-the-code) |
| The stack refuses to plan with an empty admin list | `ADMIN_USER_IDS` is required and may not be empty, so a missing secret cannot create a host nobody can reach. | [Twingate, "Access is a group, and the group is code"](Twingate.md#access-is-a-group-and-the-group-is-code) |
| SSH through Twingate works to connector a's address but times out in the banner exchange to connector b's | The connector firewall needs both an inbound rule and an outbound rule for TCP 22 to the connector tag. A new outbound connection needs an outbound rule even inside the VPC. | [Lessons learned, section 2](Lessons-Learned.md#2-connector-to-connector-ssh-timed-out-twice); [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md#inbound-and-outbound-are-both-needed-even-inside-the-vpc) |
| SSH to a droplet added later times out | The baseline firewall has zero inbound rules, and that applies between droplets in the same VPC. A later droplet needs its own firewall with the connector tag as the source for TCP 22. | [Stage 1, section 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#7-stage-3-note) |
| SSH to the public IP from the internet gets no answer | Expected. Nothing is open to the internet. The scan from outside should report ports 22, 80 and 443 as filtered. | [Twingate, "Verify it yourself"](Twingate.md#verify-it-yourself); [DigitalOcean network and firewalls, "Verify it yourself"](DigitalOcean-Network-and-Firewalls.md#verify-it-yourself) |
| SSH is refused for `root`, or asks for a password, or the key is rejected | The only login is user `cah-admin` with the admin key: root login, passwords and keyboard-interactive are off, and `AllowUsers` names only that user. | [Droplet hardening, "Login"](Droplet-Hardening.md#login) and the sshd drop-in section below it |

## Droplet first boot and the DigitalOcean API

| Symptom | Likely cause | Where to look |
|---|---|---|
| Intermittent package install failures on first boot | Ubuntu's own `apt-daily` and `unattended-upgrades` timers start on first boot too and hold the dpkg lock. The fix is `DPkg::Lock::Timeout "300";`, so apt waits up to five minutes. | [Lessons learned, section 5](Lessons-Learned.md#5-first-boot-races-ubuntu-for-the-dpkg-lock); [Stage 1, section 2a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#2a-droplet-hardening) |
| Apply fails with `422 SSH Key is already in use` | The stack tried to register a key that is already on the account. The stack looks the key up by name with a `data` source and never owns it. | [Lessons learned, section 3](Lessons-Learned.md#3-the-ssh-key-that-already-existed) |
| The plan fails at the SSH key lookup | `ADMIN_SSH_KEY_NAME` does not match the name the key already has on the DigitalOcean account. | [Stage 1, section 5, step 3](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#5-bootstrap) |
| `422 Size is not available in this region` | The cheap droplet size is not offered everywhere. Ask the API (`GET /v2/sizes`, `GET /v2/regions`) before choosing a region. | [Lessons learned, "The cheap droplet size is not offered everywhere"](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true) |
| `403 Can not delete default VPCs`, or `422 This range/size overlaps with another VPC network` | The first VPC in a region becomes its default and cannot be deleted, and ranges may not overlap anywhere in the account, even across regions. | [Lessons learned, "A default VPC cannot be deleted"](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true); [Stage 0, section 3](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md#3-choices-to-confirm-before-apply) |
| A rotated connector token destroys and recreates the droplet in the plan | The token is in the cloud-init user-data, and a user-data change forces a new droplet. That is expected: read the plan, then confirm. | [Twingate, "Rotating a connector token"](Twingate.md#rotating-a-connector-token); [Stage 1, "Accepted residual risk"](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md#3-accepted-residual-risk) |

## Wiki pages and link-checker failures

| Symptom | Likely cause | Where to look |
|---|---|---|
| The `Wiki` check fails on a pull request that touches `docs/wiki/` | That check runs `scripts/gen-wiki.sh` on the pages and fails if generation or the link rewrite breaks. Run the script locally against an empty directory and read its error. | [CI, "The wiki is published by a workflow too"](CI-Tests-and-Cost-Gate.md#the-wiki-is-published-by-a-workflow-too) |
| A link works in the repository but not in the published wiki | Page links are written as `(Page-Name.md#anchor)` and the generator rewrites them to `(Page-Name#anchor)`. A link written any other way, such as an absolute path or a missing `.md`, is not rewritten. | [CI, "The wiki is published by a workflow too"](CI-Tests-and-Cost-Gate.md#the-wiki-is-published-by-a-workflow-too); `tests/test_gen_wiki.py` |
| A link lands on the right page but at the top, not at the section | The anchor does not match a heading. The anchor is the heading in lowercase, with punctuation removed and spaces turned to hyphens. Wording changes to a heading break every link to it. | [Git, GitHub and pull requests, "Sending a correction to this wiki"](Git-GitHub-and-Pull-Requests.md#sending-a-correction-to-this-wiki) |
| A page you edited in the wiki editor disappeared | `docs/wiki/` is the only place a page is written. A page that exists only in the wiki is removed on the next publish. | [CI, "The wiki is published by a workflow too"](CI-Tests-and-Cost-Gate.md#the-wiki-is-published-by-a-workflow-too) |

## Predict, then check

Do this before you need the table.

**Predict.** Pick the row you believe is the most likely to hit you first. Without opening the repository, write down three things: the exact message you would see, which layer prints it (your script, DigitalOcean, `tofu test` or Spacelift), and what you would look at first.

**Check.** Now reproduce one that is safe to cause on your own machine. The cost gate is the easiest, because it needs no account:

1. From the repository root, run `python3 -I scripts/cost_check.py --root .` and note the baseline line (`planned $12.00/mo, approved $12.00, ceiling $30.00`).
2. In `stacks/10-access/cost.json`, copy one of the two droplet entries to make a third, without touching any `.tf` file. Before you run the gate, predict which rows of the cost gate table it will trip and what the planned total will be.
3. Run the gate again and compare. Two rules should object, for two different reasons. Then find the same message in `scripts/cost_check.py` and read the condition that prints it.
4. Restore the file with `git restore stacks/10-access/cost.json` and confirm `git status` is clean.

If your prediction named the wrong rule or the wrong total, write one sentence on what you assumed. The [labs](Labs-Break-It-on-Purpose.md) do the same for the firewall, the VPC range, the push policy and the secrets hook.

Back to [Lessons learned](Lessons-Learned.md) or the [Glossary](Glossary.md).
