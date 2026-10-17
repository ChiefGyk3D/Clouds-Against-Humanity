# Variables, tfvars and secrets: where does this value belong?

> Before this page: [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) explains plan and apply, and [Doppler and secrets](Doppler-and-Secrets.md) explains how a secret reaches a run. This page is the decision table that sits between them.

The stage 2 settings work started with one question: where does `region` live, and where does the VPC range that must not collide with a homelab live? Every value in this repository has exactly one correct home. Put it in the wrong one and the cost is either a leaked identifier in a public repository or a plan that quietly renames live machines.

## The decision table

Ask the questions in order and stop at the first yes.

| Question | Home | Example here |
|---|---|---|
| Is it a credential, or would it let someone act as you? | **Doppler**, delivered as an environment variable for one run. Never a variable default, never a value file. | `DIGITALOCEAN_TOKEN`, `TWINGATE_API_TOKEN` |
| Does it identify your accounts or your network, without being a credential? | **Doppler** for the Twingate and SSH values (the hook requests them by name), and for `reserved_ranges` only once a hook line requests it; today it arrives as a Spacelift stack environment variable (`TF_VAR_reserved_ranges`, a JSON list) or a private value file. The variable is `sensitive = true` where it carries your network. | `twingate_network`, `admin_user_ids`, `reserved_ranges` |
| Is it the size or count of a billed machine? | **`cost.json`**, edited together with `approved.json`. The cost gate reads it, so nothing else may. | `connector-a` size |
| Is it a non-secret setting that differs per site and is safe to read in a plan? | **`terraform.tfvars`** for a local plan, or **`TF_VAR_*` in the Spacelift stack environment** for a run. | `region`, `vpc_ip_range`, `reboot_times`, `resource_key` |
| Is it the shape of a setting (its name, type, validation, safe default)? | **`variables.tf`**, committed, public. | every `variable` block |
| Is it a fact of the design that nobody should change per site? | **Hard-coded** in the `.tf` file, and listed in `docs/settings.json` under `hardcoded` so it is visible. | the outbound firewall ports Twingate needs |

The full inventory, generated from one machine-readable file, is the [Settings reference](Settings-Reference.md).

## Why tfvars never holds a secret

A value file is a file. It is copied to laptops, pasted into chats, and sits in shell history after a `-var-file` command. It has no read control and no audit trail. Plan files and state repeat every variable that reaches a resource, so a secret that enters through a variable ends up in state as well. A secrets manager gives you the two things a file cannot: who can read it, and a record of who did.

So the repository's `.gitignore` ignores `*.tfvars`, `*.auto.tfvars`, `*.tfvars.json`, `*.auto.tfvars.json` and `*.tfplan`. That rule is a backstop against a mistake, not the protection. The protection is that secrets are never in a value file to begin with.

## Why `*.tfvars` is ignored and `*.example` is committed

`terraform.tfvars.example` does not end in `.tfvars`, so the ignore rule does not match it, and OpenTofu never loads it by itself (it loads only `terraform.tfvars` and `*.auto.tfvars`). That is the point: the example is documentation. It lists every variable of the stack with a comment, using placeholders and documentation ranges (`192.0.2.0/24` and friends) or obviously private ranges. Three tests keep it honest:

- every variable of the stack must have an entry, and nothing may be listed that is not a variable;
- the example is planned with mocked providers by a generated test, so every validation runs against it;
- nothing in it may look like a token, an account id, a public address or a real host name.

To use it, copy it to `terraform.tfvars` (git ignores the copy) and change the values. In a private copy of the repository you may choose to commit your own `*.auto.tfvars`; the [capstone](Fork-Private-Stacks-and-the-Pipeline.md) explains that pattern.

## What the new settings do

| Setting | What it is | Rule |
|---|---|---|
| `region` | The cloud region, passed to the provider. | Must look like a DigitalOcean slug (`tor1`). |
| `vpc_ip_range` | The VPC's private range. | A private network address with a prefix between /16 and /28. |
| `reserved_ranges` | Ranges the VPC must not overlap (your homelab). Optional. | The plan fails if the VPC range overlaps any entry. It only knows what you list. |
| `reboot_times` | When each connector may reboot: `{ a = "04:00", b = "05:00" }`. | `HH:MM`, at least 60 minutes apart around the clock (so 23:30 and 00:30 pass, 04:00 and 04:59 fail), which keeps each connector's weekly update, 30 minutes after its reboot, clear of the other's reboot. |
| `admin_ssh_public_key` | The key for the admin user. | A normal key with one trailing comment is accepted. The comment is removed before it reaches the machine. |
| `resource_key` | The word used in **names and tags** (`access-tor1`). Empty means the region. | Immutable on a live stack. |
| `site_name` | A **telemetry label** for a later stage. Empty means `site-<region>`. | Appears in no name, tag or output. |

### `resource_key` and `site_name`: one is immutable, and why

Every name here is built from the region today: the Twingate network `access-tor1`, the tag `cah-connector-tor1`, the droplet `access-tor1-connector-a`. If a friendlier label such as `site-tor1` replaced the region in those names, the next plan would rename a Twingate network, a group and two tags, and several of those force a new machine. The connectors would be rebuilt and access would drop.

So there are two settings and they never mix. `resource_key` goes into names and defaults to the region, so with the defaults every name is byte-identical to what is deployed. It cannot be changed on a live stack, because changed names cause widespread plan changes and can replace resources, through the name itself, through tags, or through user_data. `site_name` only labels telemetry. You can change it freely, because nothing in the cloud is named after it. A test reads every `.tf` file and fails if `site_name` appears in anything but its declaration.

## How to run a second site with a new tfvars (conceptually)

Second sites are **not built**. This is how the design says it would go, so you can see why the settings above exist. The [stage 2 design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) (section 3.3) has the full version.

1. Write a new set of values: a different `region` or a new `resource_key` (for example `tor1-b`), a `vpc_ip_range` that does not overlap the first site (list the first site's range in `reserved_ranges`), and a `site_name`.
2. Create separate stacks for the new site, each with its own state, environment and Doppler config. A new stack starts from nothing, so its names can use the new key.
3. The cost gate has to see the second site's machines. The rules for that (an instance manifest per site) are written down in section 3.3 of the design, and [how the gate works](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) explains why it counts connector module blocks per stack directory today.
4. A second site costs money, so it needs its own cost approval first.

Never edit the live stack's `resource_key` to "become" the second site.

## The no-op plan check

A change to the settings layer edits code that two live stacks run. The acceptance test is a plan that changes nothing. `scripts/plan_noop_check.py` reads the JSON of a saved plan (`tofu plan -out=plan.tfplan`, then `tofu show -json plan.tfplan`) and a golden list of every resource address in `docs/golden-addresses/`. It fails on any action other than `no-op` (an `update` counts), on an address missing from either side, and on any identity attribute that differs: names, tags, region, size, image. It never prints an attribute value, because `user_data` holds connector tokens.

CI cannot run a real plan, because a real plan needs the live state and credentials. CI proves the checker against mocked plan JSON: a no-op plan passes, and a plan that renames `access-tor1` to `access-site-tor1` fails. **The real gate is the plan you read in Spacelift before you confirm.** The tracked run shows the plan; if it lists anything but "no changes" for these stacks, discard it.

## Exercises

Try each answer before you read it.

1. You want to change the reboot hour of connector b. Which file, and what happens to the machine?
2. Your homelab uses `10.78.0.0/16` and you set `vpc_ip_range = "10.78.4.0/24"`. What happens, and where?
3. A friend gives you their public key as `ssh-ed25519 AAAA... alice@laptop`. Does it go through, and what does the machine receive?
4. You set `site_name = "site-tor1"` on the live stack. What does the plan show?
5. You set `resource_key = "tor1-main"` on the live access stack. What does the plan show, and what do you do?
6. Which of these may go in `terraform.tfvars`: the Twingate API token, the VPC range, the SSH key name?
7. You want a bigger droplet. Where does the size live?

<details>
<summary>Reference answers</summary>

1. `reboot_times` in a value file or the Spacelift environment (or its default in `variables.tf` for everyone). Two things follow: the two times must stay at least 60 minutes apart, and the change alters the cloud-init text, so the droplet is replaced. That is a deliberate rebuild, not a no-op.
2. The plan fails before anything is created. `reserved_ranges` must contain `10.78.0.0/16`, and then the overlap check on the foundation project stops the plan with a message. If you forgot to list the range, nothing stops you, because the check only knows what you list.
3. It goes through; the comment is allowed. The machine receives `ssh-ed25519 AAAA...` with no comment, so the rendered cloud-init is the same as for the bare key.
4. Nothing. No resource, tag or output uses it, so the plan is a no-op.
5. Replacements: the Twingate network, group, resources, tag, firewall and both droplets are renamed, and several force a new machine. Discard the run and put the value back. The key is only for a brand new stack.
6. The VPC range (private, non-secret). The SSH key name is account-specific and comes from Doppler in this repository; the API token is a credential and belongs only in Doppler.
7. `cost.json`, edited together with `docs/stages/approved.json`. The cost gate checks the price, so the size is not a variable.

</details>

Related: [Settings reference](Settings-Reference.md), [Doppler and secrets](Doppler-and-Secrets.md), [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).
