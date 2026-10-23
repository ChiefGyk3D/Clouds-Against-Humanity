# Teardown checklist

> Prerequisites: [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md), whose step 11 is the short version of this page, and [How money works in the cloud](How-Money-Works-in-the-Cloud.md).

> **Status.** The DigitalOcean order and the leftovers in sections 1 and 2 come from stages 0 and 1, which were built, applied and torn down by the author. Stage 2 (`cah-20-telemetry`) is built but never applied, so its line in the order is from the stage guide, not from a real destroy. The AWS, Azure and GCP notes are pointers to those pages' unverified drafts. The read-only commands in section 3 were not run against a live account for this page: check each against your own tool's `--help` before relying on it.

Teardown is the step people skip, and it is the one that stops the bill. This page expands step 11 of the build page into a checklist you can tick through. It adds nothing that changes how the stacks work; it puts the order, the leftovers, the proof and the clean-up of credentials in one place.

**Why it matters, in one line.** Billing stops when a resource is gone, not when you stop looking at it. At the prices the repository recorded on 2026-10-10, the two stage 1 droplets are about $12 a month (see [cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)); everything else in stages 0 and 1 is $0 on DigitalOcean. A forgotten droplet is the expensive mistake, and an empty network is not.

## 1. The order of destruction

A stack cannot be destroyed while another stack still uses its objects. Destroy in the reverse order you built, which is the same as the dependency order read backwards.

| Order | Stack | Why it goes here | What goes with it |
|---|---|---|---|
| 1 | `cah-20-telemetry` (only if you applied it) | It sits on top of stack 10. Its flags default to false, so an unapplied stack has nothing to destroy. | Only the Twingate objects for telemetry paths. Stacks 00 and 10 are untouched. |
| 2 | `cah-10-access` | It uses stage 0's network, project and tag. | The two connector droplets, their tokens (they die with the connectors) and the Twingate site. This is the step that stops the bill. Needs the destroy allowlist (below). |
| 3 | `cah-00-foundation` | Nothing depends on it once stack 10 is gone. | The private network, the project, the baseline firewall and the tag. Needs the destroy allowlist (below). |
| 4 | The Spacelift stacks themselves | Deletion protection is on by design, so this is a deliberate act, last. | The stack definitions and their run history. |

For another cloud, the same rule applies: its access stack first, then its foundation. The cloud-specific pages say it in their own words: [AWS](Provider-AWS-Cost-Lesson.md#prove-it-is-zero), [Azure](Provider-Azure-Cost-Lesson.md) and [GCP](Provider-GCP-Cost-Lesson.md), all unverified drafts.

### The destroy guard will object, on purpose

If the Spacelift plan policy from the secrets runbook is attached (`.spacelift/policies/plan.rego`, policy `cah-plan`), it denies any plan that deletes or replaces a protected resource. The protected types are `digitalocean_vpc`, `digitalocean_project`, `digitalocean_firewall`, `twingate_remote_network`, `aws_vpc` and `aws_security_group`, plus anything tagged `protected`. Only droplets are deliberately left unprotected. So **a full teardown is refused at both stacks** until the exact resource addresses are on the policy's `destroy_allowlist`. These are the addresses the destroy plans show:

| Stack | Addresses to allow |
|---|---|
| `cah-10-access` | `twingate_remote_network.this` and `module.connector_firewall.digitalocean_firewall.this` |
| `cah-00-foundation` | `module.vpc.digitalocean_vpc.this`, `digitalocean_project.this` and `module.baseline_firewall.digitalocean_firewall.this` |

Stack 20 deletes only `twingate_resource` and `twingate_service_account` objects, which are not protected. Droplets, tags and the project-membership object (`digitalocean_project_resources`) are not protected either. Read the real denial message in your destroy plan and treat it as the authority, because I have not seen a real plan input yet: if it names an address not in this table, add that one.

What you do, in order:

1. In a pull request, add the addresses for the stack you are about to destroy to `destroy_allowlist` in `.spacelift/policies/plan.rego` (one string per address). Name each address and the reason in the pull request. You can add all five at once if you are tearing down both stacks.
2. After review and merge, paste the new policy body into the `cah-plan` policy in Spacelift (the file in the repository is the reviewed copy, not the live one).
3. Run the destroy for `cah-10-access`, read the plan, confirm. Then the same for `cah-00-foundation`.
4. In a second pull request, **empty the allowlist again** and paste the body into Spacelift, so the next plan is guarded.

The allowlist applies to every stack the policy is attached to, so keep it as short as the teardown needs. There is no stack setting or label that grants an exception, on purpose. If the policy is not attached to your stacks, none of this applies and the confirmation click is your only check: read the plan first. The details are in the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md).

## 2. What survives a destroy

Some things were never in the stacks, or are kept on purpose. Destroying everything will not remove them, and some are the reason a "clean" account is not empty.

| Left behind | Why | Costs money? | What to do |
|---|---|---|---|
| The SSH key on your DigitalOcean account | The stack looks the key up by name and never created it. | No | Delete it by hand if you no longer want it. |
| An orphaned VPC (a virtual private network) | If the stack's network became the region's default, DigitalOcean refuses to delete it (`403 Can not delete default VPCs`). The fix is to make another network the default, or to forget it from state and leave it. | No, an empty network is free | Either make another VPC the default first and destroy again, or remove it from state and note that it stays. See [Lessons learned 9](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true). |
| Twingate objects made by hand, or by a flag you left on | The stacks destroy only what they created. A hand-made site, a service key or a resource you added in the console stays. | The free tier changes; check the vendor's page | Look in the Twingate admin console and delete what the code did not make. |
| The Twingate account and its identity provider link | You made the account, not the stack. | See the vendor's pricing page | Keep it or close it; this is an account decision. |
| The Doppler project and its secrets | Outside OpenTofu entirely. | See the vendor's pricing page | Delete the secrets you no longer need, or the project. |
| The Spacelift stacks, contexts and policies | Deletion protection is on, and contexts and policies are not stacks. | See the vendor's pricing page | Delete in the Spacelift console once the cloud side is gone. |
| A droplet's automated backups, if you turned them on | Destroying a droplet does not destroy them; they expire on their own schedule (four weeks for weekly backups, per DigitalOcean's pages). The [backups lesson](Backups-Recovery-and-Patching.md#cost-and-teardown-read-first) shows where this was read. | Possibly; check the billing page after a destroy | Look at the image list and the billing page; do not assume. |
| Anything you made by hand in the cloud console | It is not in the repository, so no destroy touches it and the cost gate never saw it. | Yes, possibly | Find it with the checks in section 3. |

## 3. Prove zero billable resources

A destroy that reports success is a claim. These checks are the evidence. They are all read-only: they list, they do not change anything. Use a read-only API token for them if you made one (the secrets runbook's "Token B"), not the write token. Token B's table in the runbook originally covered only what the stacks use; it now also lists `read` on reserved IPs, block storage volumes and snapshots, which the stacks never touch but these checks do. A Token B made before that change needs replacing (tokens cannot be edited), or those three commands fail with `403`. The exact scope names in DigitalOcean's token form may differ from the runbook's wording; the `403` message names the missing one.

Cross-checking two different views is the point: the provider's console, a command-line listing, and the billing page. Billing data lags, so the last check is tomorrow.

With the DigitalOcean command-line tool (`doctl`), logged in with the read-only token:

```bash
doctl compute droplet list
doctl compute firewall list
doctl compute vpc list
doctl compute reserved-ip list
doctl compute volume list
doctl compute snapshot list
doctl projects list
```

What you expect to see:

- `droplet list`, `reserved-ip list`, `volume list` and `snapshot list`: empty. These are the ones that bill.
- `firewall list` and `vpc list`: empty, or only the leftovers you chose in section 2. Empty networks and firewalls cost nothing, but you should be able to name each one.
- `projects list`: only your default project, unless you kept one on purpose.

Then:

1. In the cloud console, open the billing page and check the current month's usage by service. Every line should be one you can name.
2. Open the Twingate admin console and confirm no connector is listed and no site remains under the name the stack used.
3. In the repository, `python3 -I scripts/cost_check.py` still adds up the *approved* figures in `approved.json`. That is a statement about what the repository declares. It cannot see what is actually running, so it is not proof the account is empty.
4. **Look again tomorrow.** A resource you forgot shows up on the second look. This is the check people skip.

## 4. Revoke and rotate

Destroying the machines does not remove the credentials that could build them again. Every token below should be revoked or left to expire on purpose, not forgotten.

| Credential | Where it lives | What to do |
|---|---|---|
| DigitalOcean write token ("Token A") | Doppler `prd`, used only by Spacelift | Revoke it in the DigitalOcean console under API, Tokens. Tokens cannot be edited, only replaced, so revoke rather than shrink. Delete the secret from Doppler. |
| DigitalOcean read-only token ("Token B") | Wherever you keep it for tooling | Revoke it too, unless you will use it for the next build. |
| Doppler service token | Spacelift context `cah-doppler`, variable `DOPPLER_TOKEN` | Delete the token in Doppler, then clear the variable in the Spacelift context. |
| Twingate API key | Doppler `prd` | Revoke it in the Twingate console. Revoke any service key issued for telemetry services as well. |
| Connector tokens | Inside the connectors | Nothing to do: they die with the connectors. Confirm the connectors are gone (section 3). |
| Your own sign-ins | Provider, Spacelift, Doppler, Twingate | If you are closing an account, remove the security keys you registered and delete the account's payment method after the last invoice. |

Do these in an order that does not strand you: destroy first, prove zero, then revoke. Revoking the write token first leaves a destroy run with no credential. If you are keeping the environment for another build, rotate on the normal 90-day schedule in the secrets runbook instead of revoking.

Never paste a token into a chat, an issue, a commit or a log while you do this.

## 5. The "cost stops here" checklist

Tick every line. If you cannot tick one, the cost may not have stopped.

- [ ] I read the plan before I confirmed each destroy.
- [ ] `cah-20-telemetry` is destroyed, or I never applied it.
- [ ] `cah-10-access` is destroyed and the droplet list is empty.
- [ ] `cah-00-foundation` is destroyed, or I know why a network is left (section 2).
- [ ] The destroy allowlist is empty again in `plan.rego` and in the live policy (every stack id's list, and no stale `whole_service_teardown_stacks` entry for a stack that no longer exists).
- [ ] Reserved addresses, volumes and snapshots lists are empty.
- [ ] Nothing I made by hand in the console is still running.
- [ ] The billing page shows no droplet or reserved resource today.
- [ ] I looked at the billing page again the next day and saw no new usage.
- [ ] The write token is revoked and deleted from Doppler.
- [ ] The Doppler service token is deleted and the Spacelift context variable is cleared.
- [ ] The Twingate API key is revoked and no connector remains.
- [ ] The leftovers (SSH key, empty network, accounts) are written in my notes, with a reason for each.
- [ ] I deleted my billing alerts last, not first.

## Try it yourself

- **Predict, then check.** Before you destroy anything, write down what you expect each list in section 3 to show. Which entry would surprise you most if it were not empty?
- Read the destroy guard's table in the secrets runbook, then say why a droplet is not protected and a network is.
- Practice the order on something free first: [Build and destroy a bunch: one stack per service](Build-and-Destroy-Stack-Per-Service.md) builds and destroys five throwaway stacks in a loop and shows what a wrong destroy order looks like.
- Pick one row from section 2 and find where, in the repository, the code that does *not* create it lives.

Back to [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) or the [Reading order](Reading-Order.md).
