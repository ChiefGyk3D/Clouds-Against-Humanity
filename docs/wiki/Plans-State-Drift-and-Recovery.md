# OpenTofu plans, state, drift and recovery

Side page to the infrastructure-as-code pages, and lesson 2 of 4 in the infrastructure-as-code track. Read it after [OpenTofu from zero: init, plan, apply, destroy](OpenTofu-From-Zero.md) (lesson 1) and [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) (core step 5), and before [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) (core step 15) if reading a plan, the state file or the word "drift" still feels like guessing.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from OpenTofu's documentation; every free exercise's Bash commands were run on 2026-10-22, and the PowerShell versions were not.** The behavior claims are cited to [opentofu.org/docs](https://opentofu.org/docs/) in the claims register at the end, with the date each page was read. The documentation site showed version 1.13 as current that day; the commands were run with OpenTofu **1.12.6** (the version this repository's CI pins) on Linux, with `hashicorp/local` 2.9.1 and `hashicorp/random` 3.9.1 (the newest releases on [registry.opentofu.org](https://registry.opentofu.org/) that day; the exercises ask for `~> 2.5` and `~> 3.6`). Output shown is trimmed and the generated names and ids will differ on your machine. The PowerShell commands are **est.** (estimates): there was no PowerShell on the machine that ran the exercises, so I wrote them to mirror the Bash ones and did not run them. Nothing on this page is applied to this repository's real stacks, and none of it asks you to run `tofu` against them.

> **Prerequisites.** [OpenTofu from zero: init, plan, apply, destroy](OpenTofu-From-Zero.md) (installing `tofu`, the init, plan, apply, destroy cycle and what a provider is), or the same ideas from [What is infrastructure as code](What-Is-Infrastructure-as-Code.md); a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)); and, for the exercises, OpenTofu on your own computer (written for 1.8 or newer, est.; the exercises were run on 1.12.6). `jq` is used in the Bash exercises that read JSON (PowerShell users need nothing extra). About 3 hours for all the free exercises (est.); the reading alone is about 45 minutes (est.). The lesson-1 file may not be merged yet when you read this; the link will resolve once it is.

## What you will be able to do

- Read a plan the way a reviewer does: tell create, update in place, replace and destroy apart, say why a change "forces replacement", and recognize a plan that changes nothing.
- Apply the decision rule for discarding a run, and say who may approve what in this project and in a company.
- Say what state is, where it lives, why a team puts it somewhere shared, how locking protects it, and why it holds secrets.
- Create drift on purpose, see it in a plan, and choose between accepting it and reverting it.
- Use `import`, `moved` and `removed` blocks and `state list`, `state show` and `state rm`, and say why `-target` is a last resort.
- Use `prevent_destroy` and `create_before_destroy`, and say what each does not do.
- Reproduce four classic disasters (an index shift, a rename, lost state, a stale plan) safely with local files, and recover from each.
- Say why CI saves a plan and applies that exact file.

## Where this project already touches these ideas (and the gaps)

I searched the wiki before writing this page. What exists, and what was missing:

| Idea | Where it is covered today | The gap this page fills |
|---|---|---|
| Plan, apply, state, drift | [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) defines each in a paragraph. | No exercise that makes you read a plan line by line, cause drift, or lose state and recover. |
| Plan as the human review | [Spacelift](Spacelift.md) shows the run lifecycle and why autodeploy is off. [How this project is planned](How-This-Project-Is-Planned.md) says a plan that replaces a droplet is discarded unless that was the point. | The rule is stated, not taught: nothing says how to decide. |
| Stop-and-read on create, replace or destroy | [Stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) and [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md#known-follow-up) say any create, replace or destroy on the Twingate objects in the first tracked plan is a stop-and-read. | What each of those words looks like in a plan, and why replacing is not a small change. |
| Destroy order and the destroy guard | [Teardown checklist](Teardown-Checklist.md). | Why a plan can destroy something you did not touch (a rename, an index shift). |
| `moved` blocks | Used in `modules/twingate-connector/main.tf`, and the plan no-op check pins them. | What a `moved` block is for, and what the plan looks like without one. |
| Locking, remote state, secrets in state | Three bullets in [What is infrastructure as code](What-Is-Infrastructure-as-Code.md#state); Spacelift holds this project's state. | What locking looks like when it fires, and what "state contains secrets" means in a file you can open. |

## Two paths through this page

**Free path (reading only).** Read the sections below in order. Every behavior is cited, and every output you need to follow is shown in the page. You can skip the exercises and still finish the checkpoint, but you will have read about a plan instead of reading one.

**Free path (hands-on, local).** The exercises use two providers and one built-in resource, all of which touch only your own computer. The providers are [`hashicorp/local`](https://registry.opentofu.org/providers/hashicorp/local/latest) (writes files), [`hashicorp/random`](https://registry.opentofu.org/providers/hashicorp/random/latest) (makes names and ids). The built-in resource is `terraform_data`: it is not a provider and needs no download. Names read from the registry on 2026-10-22. Everything happens in a scratch folder under your home directory. No account, no API token and no money: the reading and the exercises are free and always will be. The one network use is `tofu init` downloading the two providers from the public registry.

**Optional own-account path (remote state).** After the local exercises you can move a scratch state to a bucket in your own cloud account. Read the cost and teardown notes first, in [Optional: put the scratch state in a bucket of your own](#optional-put-the-scratch-state-in-a-bucket-of-your-own).

## Reading a plan like a reviewer

A **plan** is OpenTofu's list of what it would do, computed by comparing three things: your configuration (the `.tf` files), the **state** (its record of what it built) and the real world (which it refreshes first). It changes nothing by itself ([plan command](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). An **apply** carries a plan out.

### The five outcomes and the symbols

Every resource in a plan lands in one of these. The symbols are from a real plan (OpenTofu 1.12.6); the JSON names are from [the JSON output format](https://opentofu.org/docs/internals/json-format/), retrieved 2026-10-22.

| Symbol and words | JSON `actions` | What happens | The reviewer's question |
|---|---|---|---|
| `+` will be created | `["create"]` | A new object is made. | Is this on the list of things the change was meant to add? |
| `~` will be updated in-place | `["update"]` | The same object keeps its identity and one or more settings change. | Does the changed setting matter (a firewall rule, a permission)? |
| `-/+` must be replaced (destroy and then create replacement) | `["delete","create"]` | The old object is destroyed, then a new one is made. | Is anything depending on the old one? Is losing it acceptable? |
| `+/-` must be replaced (create replacement and then destroy) | `["create","delete"]` | The new one is made first, then the old one goes. | Can the two exist at once (names, quotas, addresses)? |
| `-` will be destroyed | `["delete"]` | The object is removed. | Did I mean to? Is it recorded anywhere I can restore from? |
| (nothing listed) No changes | `["no-op"]` | Reality already matches. | None. This is what a healthy repeat plan looks like. |

Two more verbs you will meet later on this page: "has moved" (a `moved` block renamed the record, nothing in the real world changes) and "will be removed from the OpenTofu state but will not be destroyed" (a `removed` block told it to forget). The JSON format lists a `"forget"` action for the second.

### "Forces replacement": the part beginners miss

Some settings of some objects cannot be changed once the object exists. Change one of those and the only way to apply your edit is to destroy the old object and build a new one. The plan marks the setting that caused it with `# forces replacement`. Which settings behave like this depends on the provider and the resource, so the plan, not a guess, is the source of truth. The documentation puts it this way: when an argument cannot be updated in place "due to remote API limitations", OpenTofu destroys the existing object and creates a new one ([resource behavior, `create_before_destroy`](https://opentofu.org/docs/language/resources/behavior/), retrieved 2026-10-22).

Replacement is also contagious. If object B uses a value from object A and A is replaced, B may change too. You will see this in Exercise 2: changing one number on a name generator replaces the file that contains the name, even though you did not touch the file's configuration.

A small edit that replaces a live server is the plan a reviewer exists to catch. In this project's words: a plan that replaces a droplet "is discarded unless that was the point" ([How this project is planned](How-This-Project-Is-Planned.md)).

### What a no-op looks like

After a successful apply, planning again without changing anything ends with this (Exercise 1 shows it for real):

```text
No changes. Your infrastructure matches the configuration.
```

With `-detailed-exitcode`, `tofu plan` exits with 0 for "no changes", 1 for an error and 2 for "changes present" ([plan command](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). That exit code is how a scheduled job can detect drift without a person reading text. This repository's `scripts/plan_noop_check.py` applies the same idea to a saved plan of its own stacks: with default values the plan must change nothing. CI proves that checker against mocked plan JSON only; the real plan is read on Spacelift ([Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md)).

### The discard decision rule

On Spacelift (and in any pipeline that stops before the apply) someone sees a finished plan and a Confirm button next to a Discard button. **Discard** throws the plan away; nothing changes; a new run can plan again. Discarding costs one re-run. A wrong apply of a destroy can cost a rebuild, so when you are unsure, discard (est.: this is a judgment, not an OpenTofu rule). A way to decide, in order:

1. **Does the plan match the pull request that was merged?** Compare the list of resource addresses in the plan with the files the change touched. An address you cannot connect to the change is a reason to discard.
2. **Count the deletes.** Anything marked `-`, `-/+` or `+/-` needs a named reason in the pull request. Unnamed means discard.
3. **Is it a protected or identity piece?** In this project, a create, replace or destroy on a Twingate object in the first tracked plan after a provider change is a stop-and-read, not an apply ([stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md); [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md#known-follow-up)). A network, firewall or access object deserves the same pause in any environment.
4. **Is the plan still fresh?** The documentation warns that other changes made to the target system in the meantime can make the final effect different from an earlier plan, so re-check the final plan before applying ([plan command](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). If the plan is old, or someone applied something since, discard and re-plan.
5. **Does something say "(known after apply)" where you need to know?** Unknown values cannot be judged. Ask whether the change can be split so the risky part is visible.

If a step fails, discard, say why in the pull request or ticket, and fix the cause.

### Who may approve what

| Where | Who reads the plan and presses Confirm | Why |
|---|---|---|
| This project | The maintainer. Agents (including the AI ones that help write it) open pull requests and do not decide what ships; a change that touches live infrastructure shows its plan and the maintainer reads it ([How this project is planned](How-This-Project-Is-Planned.md)). Autodeploy is off, so every apply waits for a person ([Spacelift](Spacelift.md#why-autodeploy-is-off)). | One writer, one approver, and no apply from a laptop. |
| A company (est.) | Usually someone other than the author, for anything touching production, with the pipeline (not a person) holding the apply credential. The change record says who approved what. | Separation of duties: the person who wrote the change is not the only one who checks it. See [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md). |
| A learner's scratch folder | You. `-auto-approve` is fine here because nothing in the folder matters. | Nothing to protect. |

Least privilege applies to the approving side too: the person who may press Confirm does not need the cloud token, and the pipeline that holds the token does not need to be able to log in as a person. A request for broader access than the job needs is worth challenging, including your own.

## State: the record, the map and the secret

### What state is

**State** is a file OpenTofu writes after an apply: for each resource in your configuration it records which real object it created and what that object looked like. The primary purpose is to store bindings between objects in a remote system and the resource instances declared in your configuration ([state](https://opentofu.org/docs/language/state/); [purpose of state](https://opentofu.org/docs/language/state/purpose/), retrieved 2026-10-22). Without that map, OpenTofu cannot tell "the droplet I made" from "some other droplet".

Before most operations OpenTofu **refreshes**: it asks the provider about each recorded object and updates the state with what is really there ([state](https://opentofu.org/docs/language/state/), retrieved 2026-10-22). That is how a plan notices changes made by hand.

### Where it lives

By default the state is a local file named `terraform.tfstate` in the folder you ran `tofu` from ([state](https://opentofu.org/docs/language/state/), retrieved 2026-10-22). It is plain JSON, but the documentation discourages editing it directly and offers `tofu state` commands instead. When a command changes the state it writes a backup file next to it; on 1.12.6 I saw `terraform.tfstate.backup` after an apply and `terraform.tfstate.<number>.backup` after `state rm`. The backup is the state from just before the latest write, so it can be one change behind what you want ([state commands, backups](https://opentofu.org/docs/cli/commands/state/); [local backend, `-backup`](https://opentofu.org/docs/language/settings/backends/local/), retrieved 2026-10-22).

### Why teams use remote state

With a local file, each person must have the latest copy before running anything and make sure nobody else runs at the same time. With **remote state** the file lives in a shared store (a bucket, a database, or a service that runs OpenTofu for you) that the whole team uses ([remote state](https://opentofu.org/docs/language/state/remote/), retrieved 2026-10-22). This project's state lives in Spacelift, which also queues runs one at a time ([Spacelift](Spacelift.md)). The other reasons are in the table.

| Reason | What it buys |
|---|---|
| One shared copy | Everyone and every pipeline plans against the same record. |
| Locking | Two runs cannot write at once. |
| Versioning and backups | A bad write can be rolled back. The S3 backend's documentation recommends turning on bucket versioning "to allow for state recovery in the case of accidental deletions and human error" ([S3 backend](https://opentofu.org/docs/language/settings/backends/s3/), retrieved 2026-10-22). |
| Access control | Who may read or write state is a permission, not a file you emailed. |
| No state on a laptop | Fewer copies of a file that holds secrets. |

### Locking

If the backend supports it, OpenTofu locks the state for every operation that could write it, so others cannot acquire the lock and corrupt it. If acquiring the lock fails, OpenTofu does not continue. You can turn locking off for most commands with `-lock=false`, but the documentation says that is not recommended ([state locking](https://opentofu.org/docs/language/state/locking/), retrieved 2026-10-22). `tofu force-unlock` removes a stuck lock; the documentation says to use it only to unlock your own lock after an automatic unlock failed, because unlocking someone else's active lock could allow multiple writers ([state locking](https://opentofu.org/docs/language/state/locking/); [`force-unlock`](https://opentofu.org/docs/cli/commands/force-unlock/), retrieved 2026-10-22). Not every backend supports locking.

### Why state holds secrets

State contains the resource IDs and all resource attributes. For a database that can include its initial password ([sensitive data in state](https://opentofu.org/docs/language/state/sensitive-data/), retrieved 2026-10-22). Marking a value `sensitive` hides it in terminal output; it does not remove it from the file. Exercise 4 shows a generated password sitting in `terraform.tfstate` as ordinary text while `tofu state show` prints `(sensitive value)`. Local state is plain text. Remote state is held only in memory while OpenTofu uses it and some backends encrypt it at rest, but that depends on the backend ([sensitive data in state](https://opentofu.org/docs/language/state/sensitive-data/), retrieved 2026-10-22). OpenTofu can also encrypt state and plan files itself; the documentation notes that encryption protects against reading, not against data loss or replay of an older file ([state encryption](https://opentofu.org/docs/language/state/encryption/), retrieved 2026-10-22). Treat state as a secret and keep it out of Git. This project's other secret rules are in [Doppler and secrets](Doppler-and-Secrets.md).

## Drift

**Drift** is reality no longer matching the code, because someone changed an object by hand (or another tool did). The next plan shows it, because refresh compares the record with the real object.

Two commands deal with it:

- **`tofu plan -refresh-only`** (and `tofu apply -refresh-only`) creates a plan whose goal is only to update the state and outputs to match changes made outside OpenTofu. The documentation describes it as useful when you changed objects on purpose, for example while responding to an incident, and now need to reconcile the record ([plan command](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). Applying it changes the **record**, not the real world.
- **A normal `tofu apply`** makes the real world match the code. Drift gets reverted.

So when a plan shows drift you have two choices. This table is a way to think, not an OpenTofu rule (est.).

| Choice | When | What you do |
|---|---|---|
| **Revert** (make reality match the code) | The hand change was a mistake, or an attacker's, or nobody can explain it. | Apply. Then find out who changed it and how, and close that door. |
| **Accept** (make the code match reality) | The hand change was right, for example a fix during an incident. | Edit the code to say what reality now says, in a pull request, so the next plan is a no-op. A refresh-only apply can bring the record up to date, but the code still has to agree. |
| **Neither yet** | You do not know who or why. | Do not apply. Capture the plan, ask, and discard the run. |

Detecting drift on a schedule is a pipeline job: run `tofu plan -detailed-exitcode` on a timer and alert when it exits 2. The exit code 2 exists only because of that flag; a plain plan, including `-refresh-only`, would not return it, so a job that omits the flag treats drift as success. To look at drift only, add `-refresh-only` to the same command (est.: I ran `-detailed-exitcode` alone, not combined with `-refresh-only`). Some hosted services offer this as a feature; that is out of scope for the local exercises and not something this project has switched on (est.).

## Changing the map without changing the world

Sometimes the code or the real world was reorganized and OpenTofu's record needs to follow. Four tools, from safest to sharpest.

| Tool | Use it when | What it changes |
|---|---|---|
| `moved` block | You renamed a resource, moved it into a module, or switched between `count` and `for_each`, and want the same real object kept. | The record's address only, shown in the plan as "has moved". It is a configuration block, so it is reviewed and repeatable ([refactoring](https://opentofu.org/docs/language/modules/develop/refactoring/), retrieved 2026-10-22). |
| `import` block | A real object exists that OpenTofu does not track. | Adds a binding to state. The block says it imported the object and did not create it, and a plan previews the import before anything is written ([import](https://opentofu.org/docs/language/import/), retrieved 2026-10-22). Not every resource type supports import. |
| `removed` block | You want OpenTofu to stop managing an object without destroying it. | With `lifecycle { destroy = false }` the plan says the object will be removed from state but not destroyed ([resource syntax, removing resources](https://opentofu.org/docs/language/resources/syntax/), retrieved 2026-10-22). Without that, it behaves like deleting the resource block. |
| `tofu state mv` and `tofu state rm` | An immediate, hand-run fix to the state. `mv` re-tracks an object under another address. `rm` makes OpenTofu forget an object while it keeps existing. | The state directly, with a backup file. After `rm`, the next plan includes a create for each forgotten object ([`state rm`](https://opentofu.org/docs/cli/commands/state/rm/); [`state mv`](https://opentofu.org/docs/cli/commands/state/mv/), retrieved 2026-10-22). |

Prefer the blocks to the commands where you can: a block is in a pull request, a command is in someone's shell history. The read-only commands are safe to learn first: `tofu state list` lists the addresses in the state and `tofu state show ADDRESS` prints one resource's attributes ([`state list`](https://opentofu.org/docs/cli/commands/state/list/); [`state show`](https://opentofu.org/docs/cli/commands/state/show/), retrieved 2026-10-22).

OpenTofu expects a one-to-one mapping between configured resource instances and remote objects. If you add or remove bindings by hand (import, `state rm`) you are responsible for keeping that rule true ([state](https://opentofu.org/docs/language/state/), retrieved 2026-10-22).

### `-target`: a last resort

`-target=ADDRESS` (and `-exclude`) makes a plan or apply look at only part of the configuration. OpenTofu prints a warning every time you use it. The documentation says the options are for exceptional circumstances, such as recovering from mistakes or working around OpenTofu limitations, and that routine use "can lead to undetected configuration drift and confusion about how the true state of resources relates to configuration". It suggests splitting large configurations into smaller ones that are applied independently ([plan command, resource targeting](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). This is part of why this project has one stack per layer. The documentation also advises using whole-resource addresses rather than individual instance addresses with these options. Exercise 10 shows the leftover change a targeted apply hides.

### Lifecycle settings that act as seat belts

A `lifecycle` block inside a resource customizes its plan and apply behavior ([resource behavior](https://opentofu.org/docs/language/resources/behavior/), retrieved 2026-10-22). Two matter here.

- **`prevent_destroy = true`** makes OpenTofu reject, with an error, any plan that would destroy the object while the argument stays in the configuration. The documentation says to use it sparingly because it also blocks `tofu destroy` and some legitimate changes. It does **not** protect the object if you delete the whole resource block, because the setting goes with it. It is a guard against accidents, not against a determined person.
- **`create_before_destroy = true`** reverses a replacement: the new object is built first and the old one removed after. It is opt-in because many remote objects have unique names or other limits that stop two from existing together. The documentation also notes that OpenTofu propagates the setting to the resources the protected one depends on.

Neither setting changes what you should decide at the Confirm button.

## Four classic disasters (concept level)

Each of these happens in real teams. Each is reproduced with local files in the exercises, and each has a recovery.

| Disaster | What goes wrong | Why | Recovery |
|---|---|---|---|
| **Index shift** | You remove the first item of a list that a `count` loop reads, and the plan replaces objects you did not touch. | With `count`, each instance is named by its position (`item[0]`, `item[1]`). Remove the first and everything slides down one place, so the item that was `[1]` is now compared with the configuration for `[0]` ([`count`](https://opentofu.org/docs/language/meta-arguments/count/), retrieved 2026-10-22). | Key instances by a stable name with `for_each`, and write `moved` blocks to carry over the existing objects. Exercise 7. |
| **Rename** | You rename a resource block and the plan wants to destroy the old object and create a new one. | The address is the identity. A new address is a new resource to OpenTofu. | Add a `moved` block from the old address to the new one. Exercise 8. |
| **Lost state** | The state file is deleted, overwritten or never shared. The plan wants to create everything that already exists. | The map is gone. | Restore the last good copy (a versioned bucket, a snapshot you took, or the `.backup` file if it is current enough). Import only works for resource types that support it. Exercises 8 and 11. |
| **Stale plan** | A saved plan is applied after the state changed. | The plan was computed against a state that no longer exists. | OpenTofu refuses ("Saved plan is stale"). Discard it and plan again. Exercise 3. |

## Saved plans, and why CI applies the file

`tofu plan -out=FILE` writes the plan to a file. `tofu apply FILE` carries out exactly that plan without prompting, because passing the plan file counts as the approval. The documentation says this two-step workflow is primarily intended for automation, and that `tofu show` inspects a saved plan before applying ([apply command](https://opentofu.org/docs/cli/commands/apply/); [plan command](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). Why a pipeline wants it:

- **What was reviewed is what runs.** A fresh `apply` would plan again, possibly against newer state, and could do something different from what a person approved.
- **It can be machine-checked.** `tofu show -json FILE` gives a structured plan that a script can test (Exercise 3 counts the deletes; this repository's `plan_noop_check.py` does a stricter version for its own stacks).
- **Stale protection.** If the state moved on, the apply is refused.

A saved plan holds your whole configuration and all planned values, and sensitive values may be saved in clear text unless plan encryption is on ([plan command, `-out`](https://opentofu.org/docs/cli/commands/plan/), retrieved 2026-10-22). Treat the plan file like the state: do not commit it, and delete it when done.

## Hands-on: free exercises

Every exercise follows four steps: **predict** (write down what you expect before you run anything), **do**, **check**, **undo**.

You need `tofu` (written for 1.8 or newer, est.; run on 1.12.6), `jq` for the Bash JSON steps, and about 100 MB of disk for the provider downloads (est.). Windows users: the PowerShell blocks need PowerShell 7 (`pwsh`), because they write files with `-Encoding utf8NoBOM` so that no byte-order mark confuses the parser (est.). Everything below happens under `~/tofu-scratch/plans` (Bash) or `$HOME\tofu-scratch\plans` (PowerShell), which you can delete at the end. **Never run these commands inside this repository or against its stacks.** The point of a scratch folder is that nothing in it matters.

> **Screenshot to take yourself:** your terminal after Exercise 2.
> Capture: the plan output with the `-/+` replacement block, the `# forces replacement` marker and the `Plan:` summary line in frame.
> Look for: the `must be replaced` line on a resource you did not edit, and the summary counting adds and destroys together.
> Redact: your username and the prompt path if they identify you. The generated pet names are random and safe to show.

### Exercise 1: read a create plan, and a no-op

**Predict.** The configuration below declares three resources. How many will the first plan say it will add? After applying, what will an identical second plan say, and what exit code will `-detailed-exitcode` return?

**Do.** Make the folder, write the configuration, and run the cycle.

```bash
mkdir -p ~/tofu-scratch/plans/read && cd ~/tofu-scratch/plans/read
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "pet_length" {
  type    = number
  default = 2
}

variable "label" {
  type    = string
  default = "v1"
}

resource "random_pet" "mascot" {
  length = var.pet_length
}

resource "local_file" "note" {
  filename             = "${path.module}/out/note.txt"
  content              = "hello ${random_pet.mascot.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}

resource "terraform_data" "label" {
  input = var.label
}
EOF
tofu init
tofu plan
tofu apply -auto-approve
tofu plan -detailed-exitcode; echo "exit=$?"
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\read" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\read"
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "pet_length" {
  type    = number
  default = 2
}

variable "label" {
  type    = string
  default = "v1"
}

resource "random_pet" "mascot" {
  length = var.pet_length
}

resource "local_file" "note" {
  filename             = "${path.module}/out/note.txt"
  content              = "hello ${random_pet.mascot.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}

resource "terraform_data" "label" {
  input = var.label
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu plan
tofu apply -auto-approve
tofu plan -detailed-exitcode; "exit=$LASTEXITCODE"
```

**Check.** The first plan lists three `+` blocks and ends `Plan: 3 to add, 0 to change, 0 to destroy.` Notice `(known after apply)` on values that do not exist yet: the file's checksums and its `content` (which needs the pet's name) and the pet's id. After the apply, the second plan prints `No changes. Your infrastructure matches the configuration.` and the exit code is `0`. Also open `out/note.txt` to see the file the plan described.

**Undo.** Nothing yet; the next exercises build on this folder. To start over completely, delete the folder.

### Exercise 2: update in place versus replace

**Predict.** If you change `label` from `v1` to `v2`, will the plan update in place or replace? If you instead change `pet_length` from 2 to 3, how many resources will it touch, and will the file be one of them even though you did not edit the file's block?

**Do.** In the same folder. These only plan; nothing is applied.

```bash
cd ~/tofu-scratch/plans/read
tofu plan -var label=v2
tofu plan -var pet_length=3
tofu plan -replace=terraform_data.label
tofu plan -destroy
```

```powershell
Set-Location "$HOME\tofu-scratch\plans\read"
tofu plan -var label=v2
tofu plan -var pet_length=3
tofu plan -replace=terraform_data.label
tofu plan -destroy
```

**Check.** First plan: `terraform_data.label will be updated in-place`, with `~ input = "v1" -> "v2"` and the summary `0 to add, 1 to change, 0 to destroy`. Second plan, trimmed from the real output:

```text
  # local_file.note must be replaced
-/+ resource "local_file" "note" {
      ~ content              = <<-EOT # forces replacement
            hello gorgeous-ox
        EOT -> (known after apply) # forces replacement
  # random_pet.mascot must be replaced
-/+ resource "random_pet" "mascot" {
      ~ length    = 2 -> 3 # forces replacement
Plan: 2 to add, 0 to change, 2 to destroy.
```

You touched one number and two resources are replaced: the pet because `length` forces replacement, and the file because its content uses the pet's name. Third plan: `terraform_data.label will be replaced, as requested` (`-replace` forces a replacement that would otherwise be nothing). Fourth plan: `Plan: 0 to add, 0 to change, 3 to destroy.` That is what a destroy looks like before you do it; reading it is how you check that you are about to destroy what you think.

**Undo.** None of these changed anything.

### Exercise 3: a saved plan, a reviewer script and a stale plan

**Predict.** Will `tofu show -json` list the file's action as one word or two? And what do you expect when you apply a saved plan after something else has changed the state?

**Do.** Part A saves a plan, summarizes it with a script, and applies the file. This time the replacement is intended, so you apply it. Create a variable file so later exercises keep using `pet_length = 3`.

```bash
cd ~/tofu-scratch/plans/read
printf 'pet_length = 3\n' > terraform.tfvars
tofu plan -out=review.tfplan
tofu show -json review.tfplan | jq -r '[.resource_changes[].change.actions] | map(join("+")) | group_by(.) | map("\(.[0])=\(length)") | join(" ")'
tofu show -json review.tfplan | jq -e '[.resource_changes[] | select(.change.actions | index("delete"))] | length == 0' > /dev/null && echo "no deletes" || echo "DELETES: read them before applying"
tofu apply review.tfplan
```

```powershell
Set-Location "$HOME\tofu-scratch\plans\read"
'pet_length = 3' | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan -out=review.tfplan
$plan = tofu show -json review.tfplan | ConvertFrom-Json
$plan.resource_changes | Group-Object { $_.change.actions -join '+' } | ForEach-Object { "$($_.Name)=$($_.Count)" }
$deletes = @($plan.resource_changes | Where-Object { $_.change.actions -contains 'delete' })
if ($deletes.Count -eq 0) { 'no deletes' } else { 'DELETES: read them before applying' }
tofu apply review.tfplan
```

Part B makes a plan stale on purpose.

```bash
printf 'pet_length = 3\nlabel = "v2"\n' > terraform.tfvars
tofu plan -out=old.tfplan > /dev/null
printf 'pet_length = 3\nlabel = "v3"\n' > terraform.tfvars
tofu apply -auto-approve
tofu apply old.tfplan; echo "exit=$?"
```

```powershell
"pet_length = 3`nlabel = `"v2`"" | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan -out=old.tfplan | Out-Null
"pet_length = 3`nlabel = `"v3`"" | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu apply -auto-approve
tofu apply old.tfplan; "exit=$LASTEXITCODE"
```

**Check.** Part A: the summary prints `delete+create=2 no-op=1` (a replacement is two words in one list, `delete` and `create`, which is why scanning for `delete` finds every case that removes an object; the JSON format page says so). The delete check prints the warning line, you read the plan, and the apply finishes with `2 added, 0 changed, 2 destroyed`. Part B: the last command fails with `Error: Saved plan is stale` and exit `1`. The state changed after the plan was made, and OpenTofu refused to apply it. That refusal is the safe outcome.

**Undo.** `rm review.tfplan old.tfplan` (PowerShell: `Remove-Item review.tfplan, old.tfplan`). Saved plans can hold sensitive values, so do not leave them around.

### Exercise 4: look at the state, and find the secret in it

**Predict.** If a resource makes a password and marks it sensitive, will `tofu state show` print it? Will the file `terraform.tfstate` contain it?

**Do.** A new folder, so the first one stays tidy.

```bash
mkdir -p ~/tofu-scratch/plans/state && cd ~/tofu-scratch/plans/state
cat > main.tf <<'EOF'
terraform {
  required_providers {
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_password" "demo" {
  length = 16
}

resource "terraform_data" "note" {
  input = "hello"
}
EOF
tofu init
tofu apply -auto-approve
tofu state list
tofu state show random_password.demo
ls -l terraform.tfstate
jq '.resources[] | select(.type=="random_password") | .instances[0].attributes.result | length' terraform.tfstate
tofu state pull | jq '{version, serial, lineage}'
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\state" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\state"
@'
terraform {
  required_providers {
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_password" "demo" {
  length = 16
}

resource "terraform_data" "note" {
  input = "hello"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu apply -auto-approve
tofu state list
tofu state show random_password.demo
Get-Item terraform.tfstate | Select-Object Name, Length
$s = Get-Content terraform.tfstate -Raw | ConvertFrom-Json
($s.resources | Where-Object type -eq random_password).instances[0].attributes.result.Length
tofu state pull | ConvertFrom-Json | Select-Object version, serial, lineage
```

**Check.** `state list` prints `random_password.demo` and `terraform_data.note`. `state show` prints the attributes with `result = (sensitive value)`. Yet the `jq` line prints `16`: the real 16-character password is in the file, as plain text. (The commands print only its length, so no secret appears on screen or in your history.) `state pull` shows the file's `serial` (a counter that went up with each change I made) and `lineage` (an id for this particular state's history; est. from the field names, I did not test what OpenTofu does when two lineages meet). The takeaway: anyone who can read the state can read the password.

**Undo.** Keep the folder for Exercise 11's lesson on copies, or delete it. The password is random and unused.

### Exercise 5: locking, from two terminals

**Predict.** If one terminal is in the middle of an apply, what happens to a plan started in a second terminal on the same folder?

**Do.** The `local-exec` provisioner below runs a command on your computer and is used here only to make an apply last about 20 seconds; the documentation says provisioners are a last resort for real work ([provisioners](https://opentofu.org/docs/language/resources/provisioners/syntax/), retrieved 2026-10-22). Open **two** terminal windows.

```bash
mkdir -p ~/tofu-scratch/plans/lock && cd ~/tofu-scratch/plans/lock
cat > main.tf <<'EOF'
resource "terraform_data" "slow" {
  provisioner "local-exec" {
    command = "sleep 20"
  }
}
EOF
tofu init
```

In terminal 1, start the slow apply, then switch to terminal 2 within a few seconds:

```bash
tofu apply -auto-approve
```

In terminal 2, in the same folder, while terminal 1 is still working:

```bash
cd ~/tofu-scratch/plans/lock
tofu plan -lock-timeout=2s; echo "exit=$?"
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\lock" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\lock"
@'
resource "terraform_data" "slow" {
  provisioner "local-exec" {
    interpreter = ["pwsh", "-Command"]
    command     = "Start-Sleep -Seconds 20"
  }
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
```

In terminal 1, start the slow apply, then switch to terminal 2 within a few seconds:

```powershell
tofu apply -auto-approve
```

In terminal 2, in the same folder, while terminal 1 is still working:

```powershell
Set-Location "$HOME\tofu-scratch\plans\lock"
tofu plan -lock-timeout=2s; "exit=$LASTEXITCODE"
```

**Check.** Terminal 2 prints `Error: Error acquiring the state lock` and a `Lock Info` block (trimmed; the `Who` field names the user and computer that hold the lock, which is how a team finds the owner):

```text
Error message: resource temporarily unavailable
Lock Info:
  ID:        <a uuid>
  Path:      terraform.tfstate
  Operation: OperationTypeApply
  Who:       <user>@<computer>
  Created:   <time>
```

The exit code is `1`. When terminal 1 finishes, run the plan again in terminal 2; it works. A lock held by a crashed run is what `tofu force-unlock LOCK_ID` is for, and the documentation says to use it only for your own stuck lock (do not practice it on someone else's folder). A local state file lives on one computer, so this protects against a second process there (est.); a shared remote backend that supports locking extends the same protection to other people and machines.

**Undo.** `tofu destroy -auto-approve` in that folder, then delete it.

### Exercise 6: create drift, see it, then revert and accept

**Predict.** If you edit `out/note.txt` by hand, will the next plan stay quiet? What do you expect when you delete the file instead?

**Do.** Back in the first folder (after Exercise 3 its state matches `pet_length = 3` and `label = "v3"`; if you changed the variable file since, set it back to those two values first).

```bash
cd ~/tofu-scratch/plans/read
printf 'pet_length = 3\nlabel = "v3"\n' > terraform.tfvars
tofu plan -detailed-exitcode > /dev/null; echo "baseline exit=$?"
echo "edited by hand" > out/note.txt
tofu plan -detailed-exitcode; echo "exit=$?"
tofu apply -auto-approve
cat out/note.txt
rm out/note.txt
tofu plan -refresh-only
tofu apply -refresh-only -auto-approve
tofu state list
tofu plan
tofu apply -auto-approve
```

```powershell
Set-Location "$HOME\tofu-scratch\plans\read"
"pet_length = 3`nlabel = `"v3`"" | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan -detailed-exitcode | Out-Null; "baseline exit=$LASTEXITCODE"
'edited by hand' | Set-Content out\note.txt
tofu plan -detailed-exitcode; "exit=$LASTEXITCODE"
tofu apply -auto-approve
Get-Content out\note.txt
Remove-Item out\note.txt
tofu plan -refresh-only
tofu apply -refresh-only -auto-approve
tofu state list
tofu plan
tofu apply -auto-approve
```

**Check.** The baseline exit is `0`. After the hand edit the plan exits `2` and wants to create `local_file.note`: for this provider, a file whose content no longer matches what it recorded is treated as gone, so the drift shows up as a create rather than an update (other providers usually show an in-place `~` change; I did not test any other). The apply is the **revert**: `cat` shows `hello <your pet name>` again. Then you delete the file. `plan -refresh-only` reports `local_file.note has been deleted` and says it is a refresh-only plan, so it "will not take any actions to undo these". Applying that **accepts** the fact into the record: `state list` no longer shows `local_file.note`. A normal plan then still wants to create the file, because the code still declares it. That is the point: accepting a drift in the record does not change the code. To truly accept a change you also edit the code; to revert it you apply. The final apply restores the file.

**Undo.** The last apply already restored everything.

### Exercise 7: the index shift

**Predict.** A `count` loop makes three files from a list of names. If you remove the first name, how many files do you expect the plan to touch? One?

**Do.**

```bash
mkdir -p ~/tofu-scratch/plans/count && cd ~/tofu-scratch/plans/count
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "local_file" "item" {
  count                = length(var.names)
  filename             = "${path.module}/out/${var.names[count.index]}.txt"
  content              = "I am ${var.names[count.index]}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
EOF
tofu init
tofu apply -auto-approve
tofu state list
printf 'names = ["bravo", "charlie"]\n' > terraform.tfvars
tofu plan
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\count" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\count"
@'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "local_file" "item" {
  count                = length(var.names)
  filename             = "${path.module}/out/${var.names[count.index]}.txt"
  content              = "I am ${var.names[count.index]}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu apply -auto-approve
tofu state list
'names = ["bravo", "charlie"]' | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan
```

**Check.** You removed one name and the plan says `Plan: 2 to add, 0 to change, 3 to destroy.` Trimmed:

```text
  # local_file.item[0] must be replaced
      ~ filename = "./out/alpha.txt" -> "./out/bravo.txt" # forces replacement
  # local_file.item[1] must be replaced
      ~ filename = "./out/bravo.txt" -> "./out/charlie.txt" # forces replacement
  # local_file.item[2] will be destroyed
  # (because index [2] is out of range for count)
```

Every instance after the removed one shifted down a position, so `bravo` and `charlie`, which you did not touch, are destroyed and rebuilt. With files that is churn; with servers it is an outage. **Do not apply.** Now the recovery. Remove the variable file so the list is back to three, then switch to `for_each` and write `moved` blocks that carry each old index to its stable key:

```bash
rm terraform.tfvars
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "local_file" "item" {
  for_each             = toset(var.names)
  filename             = "${path.module}/out/${each.key}.txt"
  content              = "I am ${each.key}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}

moved {
  from = local_file.item[0]
  to   = local_file.item["alpha"]
}

moved {
  from = local_file.item[1]
  to   = local_file.item["bravo"]
}

moved {
  from = local_file.item[2]
  to   = local_file.item["charlie"]
}
EOF
tofu plan
tofu apply -auto-approve
tofu state list
printf 'names = ["bravo", "charlie"]\n' > terraform.tfvars
tofu plan
```

```powershell
Remove-Item terraform.tfvars
@'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "local_file" "item" {
  for_each             = toset(var.names)
  filename             = "${path.module}/out/${each.key}.txt"
  content              = "I am ${each.key}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}

moved {
  from = local_file.item[0]
  to   = local_file.item["alpha"]
}

moved {
  from = local_file.item[1]
  to   = local_file.item["bravo"]
}

moved {
  from = local_file.item[2]
  to   = local_file.item["charlie"]
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu plan
tofu apply -auto-approve
tofu state list
'names = ["bravo", "charlie"]' | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan
```

**Check.** The first plan lists three lines like `local_file.item[0] has moved to local_file.item["alpha"]` and ends `Plan: 0 to add, 0 to change, 0 to destroy.` (no real change, only the record). After the apply, `state list` shows `item["alpha"]`, `item["bravo"]`, `item["charlie"]`. The last plan, with `alpha` removed, says `local_file.item["alpha"] will be destroyed` and `Plan: 0 to add, 0 to change, 1 to destroy.` Exactly the thing you removed, and nothing else. That is why many teams prefer `for_each` keyed by a stable name when the items are not interchangeable (est.: a convention, not a rule; `count` is fine for "N identical things").

**Undo.** `tofu destroy -auto-approve`, then delete the folder.

### Exercise 8: rename, and lost state

**Predict.** If you only rename a resource block (same settings, new label), will the plan be a no-op? And if you delete `terraform.tfstate` while the files it describes still exist, what will the next plan say?

**Do.** Start with a name generator and a file that uses it.

```bash
mkdir -p ~/tofu-scratch/plans/rename && cd ~/tofu-scratch/plans/rename
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "server" {
  length = 2
}

resource "local_file" "greeting" {
  filename             = "${path.module}/out/greeting.txt"
  content              = "server is ${random_pet.server.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
EOF
tofu init
tofu apply -auto-approve
cat out/greeting.txt
```

Now the rename: change `server` to `web` in both places.

```bash
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "web" {
  length = 2
}

resource "local_file" "greeting" {
  filename             = "${path.module}/out/greeting.txt"
  content              = "server is ${random_pet.web.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
EOF
tofu plan
```

Then the fix: add a `moved` block, plan, and apply.

```bash
cat >> main.tf <<'EOF'

moved {
  from = random_pet.server
  to   = random_pet.web
}
EOF
tofu plan
tofu apply -auto-approve
```

Now lose the state. Keep a copy first (the habit), delete the state, and look at the plan.

```bash
cp terraform.tfstate ../rename-known-good.tfstate
rm -f terraform.tfstate terraform.tfstate.backup
tofu plan
cat out/greeting.txt
```

Recover by putting the copy back:

```bash
cp ../rename-known-good.tfstate terraform.tfstate
tofu plan
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\rename" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\rename"
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "server" {
  length = 2
}

resource "local_file" "greeting" {
  filename             = "${path.module}/out/greeting.txt"
  content              = "server is ${random_pet.server.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu apply -auto-approve
Get-Content out\greeting.txt

# The rename: server -> web, in both places.
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "web" {
  length = 2
}

resource "local_file" "greeting" {
  filename             = "${path.module}/out/greeting.txt"
  content              = "server is ${random_pet.web.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu plan

# The fix: a moved block.
@'

moved {
  from = random_pet.server
  to   = random_pet.web
}
'@ | Add-Content -Encoding utf8NoBOM main.tf
tofu plan
tofu apply -auto-approve

# Lose the state, with a copy kept first.
Copy-Item terraform.tfstate ..\rename-known-good.tfstate
Remove-Item terraform.tfstate, terraform.tfstate.backup -ErrorAction SilentlyContinue
tofu plan
Get-Content out\greeting.txt

# Recover.
Copy-Item ..\rename-known-good.tfstate terraform.tfstate
tofu plan
```

**Check.** The rename plan is not a no-op: `random_pet.server will be destroyed (because random_pet.server is not in configuration)`, `random_pet.web will be created`, and `local_file.greeting must be replaced` because the new pet has a different name. `Plan: 2 to add, 0 to change, 2 to destroy.` For a server that would be a destroy and rebuild caused by a tidy-up. With the `moved` block the plan reads `random_pet.server has moved to random_pet.web` and `Plan: 0 to add, 0 to change, 0 to destroy.` After you delete the state the plan says `local_file.greeting will be created` and `random_pet.web will be created`, `Plan: 2 to add`, although both already exist: with the map gone, OpenTofu believes nothing exists, and an apply would write a new pet name over the file. Restoring the copy makes the next plan report no changes again. Importing is not an option here: I tried `tofu import` on both resource types and both answered `Resource Import Not Implemented`; whether a type supports import is up to its provider. The `.backup` file written by an apply is the state from before that apply, so after a single apply it can be missing or one change behind; a copy you took on purpose is better.

**Undo.** `tofu destroy -auto-approve` removes the files; then delete the folder and `rename-known-good.tfstate`.

### Exercise 9: import, `state rm` and `removed`

**Predict.** If you tell OpenTofu to forget a resource with `state rm`, what will the next plan want to do? Which command previews an import before it changes anything?

**Do.** `random_id` is one of the few local resource types that supports import, so it can stand in for a real object you want to adopt. The files are split so you can add and remove pieces by file.

```bash
mkdir -p ~/tofu-scratch/plans/import && cd ~/tofu-scratch/plans/import
cat > main.tf <<'EOF'
terraform {
  required_providers {
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "terraform_data" "anchor" {
  input = "x"
}
EOF
cat > ticket.tf <<'EOF'
resource "random_id" "ticket" {
  byte_length = 4
}
EOF
tofu init
tofu apply -auto-approve
ID=$(tofu state show -no-color random_id.ticket | awk '/b64_url/ {gsub(/"/,"",$3); print $3}')
echo "the object's id is: $ID"
```

The id is what a real adoption needs (for a cloud object, its id from the console or the provider's documentation). Now make OpenTofu forget the object and see what a plan thinks:

```bash
tofu state rm random_id.ticket
ls
tofu plan
```

Now adopt it again with an `import` block:

```bash
cat > import.tf <<EOF
import {
  to = random_id.ticket
  id = "$ID"
}
EOF
cat import.tf
tofu plan
tofu apply -auto-approve
tofu plan -detailed-exitcode; echo "exit=$?"
```

Last, stop managing it without destroying it, using a `removed` block:

```bash
rm import.tf ticket.tf
cat > removed.tf <<'EOF'
removed {
  from = random_id.ticket

  lifecycle {
    destroy = false
  }
}
EOF
tofu plan
tofu apply -auto-approve
tofu state list
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\import" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\import"
@'
terraform {
  required_providers {
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "terraform_data" "anchor" {
  input = "x"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
@'
resource "random_id" "ticket" {
  byte_length = 4
}
'@ | Set-Content -Encoding utf8NoBOM ticket.tf
tofu init
tofu apply -auto-approve
$id = (tofu state show -no-color random_id.ticket | Select-String 'b64_url\s+=\s+"([^"]+)"').Matches[0].Groups[1].Value
"the object's id is: $id"
tofu state rm random_id.ticket
Get-ChildItem
tofu plan
@"
import {
  to = random_id.ticket
  id = "$id"
}
"@ | Set-Content -Encoding utf8NoBOM import.tf
tofu plan
tofu apply -auto-approve
tofu plan -detailed-exitcode; "exit=$LASTEXITCODE"
Remove-Item import.tf, ticket.tf
@'
removed {
  from = random_id.ticket

  lifecycle {
    destroy = false
  }
}
'@ | Set-Content -Encoding utf8NoBOM removed.tf
tofu plan
tofu apply -auto-approve
tofu state list
```

**Check.** `state rm` prints `Removed random_id.ticket` and writes a timestamped backup file next to the state (the `ls` shows it). The plan now says `random_id.ticket will be created`: the object still "exists" (random ids exist only as values) but OpenTofu forgot it, so it wants to make another, different one. With the import block the plan says `random_id.ticket will be imported`, shows the attributes, and ends `Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.` After the apply, `Apply complete! Resources: 1 imported` and the next plan exits `0`. With the `removed` block the plan says the resource "will be removed from the OpenTofu state but will not be destroyed", and the apply says `1 forgotten`; `state list` shows only `terraform_data.anchor`. In a real cloud account the forgotten object keeps running and billing, and nothing tracks it any more, so a `removed` block with `destroy = false` is a deliberate hand-off, not a clean-up.

**Undo.** `tofu destroy -auto-approve`, then delete the folder.

### Exercise 10: lifecycle seat belts, and `-target`

**Predict.** What will OpenTofu do with a plan that would destroy a resource marked `prevent_destroy`? And after an apply restricted with `-target`, will a normal plan afterward be a no-op?

**Do.**

```bash
mkdir -p ~/tofu-scratch/plans/life && cd ~/tofu-scratch/plans/life
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "precious_text" {
  type    = string
  default = "do not lose me"
}

variable "release" {
  type    = string
  default = "r1"
}

variable "other_input" {
  type    = string
  default = "unrelated"
}

resource "local_file" "precious" {
  filename             = "${path.module}/out/precious.txt"
  content              = "${var.precious_text}\n"
  file_permission      = "0644"
  directory_permission = "0755"

  lifecycle {
    prevent_destroy = true
  }
}

resource "terraform_data" "svc" {
  triggers_replace = [var.release]

  lifecycle {
    create_before_destroy = true
  }
}

resource "terraform_data" "other" {
  input = var.other_input
}
EOF
tofu init
tofu apply -auto-approve
printf 'precious_text = "changed"\n' > terraform.tfvars
tofu plan; echo "exit=$?"
printf 'release = "r2"\n' > terraform.tfvars
tofu plan
tofu apply -auto-approve
printf 'release = "r3"\nother_input = "edited"\n' > terraform.tfvars
tofu plan -target=terraform_data.other
tofu apply -target=terraform_data.other -auto-approve
tofu plan
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\life" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\life"
@'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "precious_text" {
  type    = string
  default = "do not lose me"
}

variable "release" {
  type    = string
  default = "r1"
}

variable "other_input" {
  type    = string
  default = "unrelated"
}

resource "local_file" "precious" {
  filename             = "${path.module}/out/precious.txt"
  content              = "${var.precious_text}\n"
  file_permission      = "0644"
  directory_permission = "0755"

  lifecycle {
    prevent_destroy = true
  }
}

resource "terraform_data" "svc" {
  triggers_replace = [var.release]

  lifecycle {
    create_before_destroy = true
  }
}

resource "terraform_data" "other" {
  input = var.other_input
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu apply -auto-approve
'precious_text = "changed"' | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan; "exit=$LASTEXITCODE"
'release = "r2"' | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan
tofu apply -auto-approve
"release = `"r3`"`nother_input = `"edited`"" | Set-Content -Encoding utf8NoBOM terraform.tfvars
tofu plan '-target=terraform_data.other'
tofu apply '-target=terraform_data.other' -auto-approve
tofu plan
```

**Check.** First plan: a replacement is needed for `local_file.precious` (the file's content forces it), and the plan ends with `Error: Resource instance cannot be destroyed`, naming `prevent_destroy`; exit `1`. The error is the guard working. Second plan (`release = "r2"`): the replacement symbol is `+/-` and the legend says `create replacement and then destroy`; the apply log shows `terraform_data.svc: Creating...` and `Creation complete` *before* `terraform_data.svc (deposed object ...): Destroying...`. The old object is called "deposed" while it waits to be removed. Third: with `-target`, OpenTofu prints `Warning: Resource targeting is in effect` and says the options "are not for routine use". After the targeted apply, the plain `tofu plan` is **not** empty: it still wants to replace `terraform_data.svc` (the `r3` change that the targeted apply skipped). That unapplied change was easy to miss, which is the documented risk of routine targeting.

**Undo.** Remove the guard so the folder can be destroyed: edit `main.tf`, delete the `lifecycle { prevent_destroy = true }` block from `local_file.precious`, then `tofu destroy -auto-approve`. (With the guard in place the destroy fails, which is the point of it.) Delete the folder.

### Exercise 11: the drill (break it on purpose, recover from a state copy)

This one is a small version of an incident. A script damages a practice lab in three ways at once; you recover using only the safety copy of the state that the script leaves in a `backups` folder. Read the whole script before you run it: it deletes and overwrites files, but only inside the lab folder, and it refuses to run if the lab marker file is missing.

**Predict.** After the damage, the plan will say what? How many things will it want to create, and will the files it creates have the same pet name as before, if you apply without restoring the state?

**Do.** Set up the lab and the break script.

```bash
mkdir -p ~/tofu-scratch/plans/drillroot/drill && cd ~/tofu-scratch/plans/drillroot/drill
touch .tofu-lab
cat > main.tf <<'EOF'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "owner" {
  length = 2
}

resource "local_file" "page" {
  for_each             = toset(["a", "b", "c"])
  filename             = "${path.module}/out/${each.key}.txt"
  content              = "page ${each.key} owned by ${random_pet.owner.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
EOF
tofu init
tofu apply -auto-approve
cat out/*.txt
cd ..
cat > break-it.sh <<'EOF'
#!/usr/bin/env bash
# break-it.sh: deliberately damages the practice lab in ./drill. Nothing else.
set -eu
cd "$(dirname "$0")/drill"
[ -f .tofu-lab ] || { echo "refusing: this is not the practice lab"; exit 1; }
mkdir -p backups
cp terraform.tfstate backups/state-known-good.json   # the safety copy you recover from
rm -f terraform.tfstate terraform.tfstate.backup     # damage 1: the state is gone
echo "tampered by hand" > out/b.txt                   # damage 2: drift
rm -f out/c.txt                                       # damage 3: a managed file vanishes
echo "Damage done. Recover using only the copy in drill/backups."
EOF
chmod +x break-it.sh
./break-it.sh
```

Now recover. Work out the order yourself before you read the next block: look at the plan first, restore the state before you apply, then check the plan again.

```bash
cd drill
tofu plan
cp backups/state-known-good.json terraform.tfstate
tofu plan
tofu apply -auto-approve
cat out/*.txt
tofu plan -detailed-exitcode; echo "exit=$?"
```

```powershell
New-Item -ItemType Directory -Force "$HOME\tofu-scratch\plans\drillroot\drill" | Out-Null
Set-Location "$HOME\tofu-scratch\plans\drillroot\drill"
New-Item -ItemType File .tofu-lab -Force | Out-Null
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_pet" "owner" {
  length = 2
}

resource "local_file" "page" {
  for_each             = toset(["a", "b", "c"])
  filename             = "${path.module}/out/${each.key}.txt"
  content              = "page ${each.key} owned by ${random_pet.owner.id}\n"
  file_permission      = "0644"
  directory_permission = "0755"
}
'@ | Set-Content -Encoding utf8NoBOM main.tf
tofu init
tofu apply -auto-approve
Get-Content out\*.txt
Set-Location ..
@'
# break-it.ps1: deliberately damages the practice lab in .\drill. Nothing else.
Set-Location (Join-Path $PSScriptRoot 'drill')
if (-not (Test-Path .tofu-lab)) { Write-Error 'refusing: this is not the practice lab'; exit 1 }
New-Item -ItemType Directory -Force backups | Out-Null
Copy-Item terraform.tfstate backups\state-known-good.json
Remove-Item terraform.tfstate, terraform.tfstate.backup -ErrorAction SilentlyContinue
'tampered by hand' | Set-Content out\b.txt
Remove-Item out\c.txt -ErrorAction SilentlyContinue
'Damage done. Recover using only the copy in drill\backups.'
'@ | Set-Content -Encoding utf8NoBOM break-it.ps1
.\break-it.ps1

# Recover.
Set-Location drill
tofu plan
Copy-Item backups\state-known-good.json terraform.tfstate
tofu plan
tofu apply -auto-approve
Get-Content out\*.txt
tofu plan -detailed-exitcode; "exit=$LASTEXITCODE"
```

**Check.** Before restoring, the plan says `Plan: 4 to add, 0 to change, 0 to destroy.` (the pet and all three files) even though `a.txt` exists and `b.txt` holds the hand-written line: the state is gone, so OpenTofu thinks nothing exists. Applying then would have written a **new** pet name into every file. After the restore the plan shrinks to `Plan: 2 to add` (`page["b"]` and `page["c"]`: one edited by hand, one deleted), which is the real remaining damage. The apply repairs both, all three files show the original pet name, and the last plan exits `0`. The order is the lesson: restore the map first, read what is actually wrong, then apply. If you had applied before restoring, the original name would be gone for good.

**Undo.** `tofu destroy -auto-approve` inside `drill`, then delete `~/tofu-scratch/plans` (PowerShell: `Remove-Item -Recurse -Force $HOME\tofu-scratch\plans`).

## Optional: put the scratch state in a bucket of your own

This is the one part of the page that uses your own cloud account. It is **optional** and I did not run it, so every detail here is **est.** and taken from the [S3 backend page](https://opentofu.org/docs/language/settings/backends/s3/) and the [`init` command page](https://opentofu.org/docs/cli/commands/init/) (retrieved 2026-10-22).

**Cost, first.** A bucket for a few kilobytes of state costs what your provider charges you for storage and requests, on your own bill. I give no figure: I did not read your provider's current price page, so check it, and set a billing alert before you start. This repository's [cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) page covers only the figures it approved for its own stages, not yours. Read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first if "billing alert" is new.

**Teardown, first.** Know how you will finish before you begin: (1) in the scratch folder run `tofu destroy`; (2) delete every object and every version in the bucket, then the bucket; (3) delete or deactivate the access key you made for this; (4) confirm in your provider's billing view that nothing is left. [Teardown checklist](Teardown-Checklist.md) has the same proof-it-is-zero habit for this project's stacks.

**Steps (est.).**

1. Make a private bucket with versioning turned on, using your provider's console or command line, in a throwaway account or a throwaway project of your own. Create a credential that can only read and write that bucket, and give it to OpenTofu through the standard environment variables of your provider, never in the `.tf` file.
2. In the `lock` folder from Exercise 5, add a backend block (placeholders shown: use your own bucket name and region):

```hcl
terraform {
  backend "s3" {
    bucket       = "example-your-bucket-name"
    key          = "plans-lesson/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}
```

3. Run `tofu init -migrate-state`. The documentation says `-migrate-state` is required to update the backend configuration and copies the existing state to the new backend.
4. Repeat Exercise 5 from two terminals. The lock now lives in the bucket, so two computers would be blocked too.
5. Tear down as above.

An S3-compatible service from another provider may need extra settings; check its documentation (est.).

## Build it, break it, detect it, evade it, defend it

The same loop the [labs](Labs-Break-It-on-Purpose.md) use, applied to drift. The cloud steps are described, not run; the local version is Exercise 6.

- **Build.** A firewall is declared in code with zero inbound rules, applied, and the next plan is a no-op. That is the state you want to be able to prove.
- **Break.** Someone with console access opens a port on that firewall by hand, "just for a minute" (or an attacker who stole a console login does). Reality now differs from the code. Exercise 6 is the same event on a file.
- **Detect.** The next plan shows the extra rule as a change to revert. A plan run on a schedule with `-detailed-exitcode` exits 2 and can raise an alert without a person reading text. The cloud's own audit log shows who made the change. This project's plan policy also denies a plan that would open a port ([Spacelift](Spacelift.md#the-plan-policy-no-open-ports-in-a-plan); written and tested, not yet attached).
- **Evade.** A plan only compares what the code declares and what the state records. A change the code does not own does not show up: a rule added on an object that was never imported, a brand-new resource created by hand and never added to state, a setting hidden by an `ignore_changes` entry, or a change made and undone between two scheduled checks. Detection by plan is blind to all four. Each is a reason not to treat a clean plan as proof of a clean account.
- **Defend.** Run the drift check on a schedule and alert on it. Keep write credentials in the pipeline and give people read-only console roles, so a hand change is hard to make and easy to attribute. Keep `ignore_changes` narrow and written down (this repository ignores one attribute on one AWS resource and says why). Add an inventory that compares what exists with what is declared, so unmanaged objects surface. Turn on the cloud's audit log and watch it.

**Flip the board.** Look at the state backend as an attacker would. It holds a map of everything, often secrets, and whoever can write it can make OpenTofu forget a resource (`state rm` does exactly that in Exercise 9) so a later plan no longer shows it. Whoever can only read it gets passwords and keys (Exercise 4). The defender's version of the same fact: the state bucket and the pipeline's credentials are as sensitive as the infrastructure itself. Version the bucket, restrict who reads and writes it, log access, encrypt it, and treat a change to the state or to the plan policy as a security event. If you were the person defending this project, which single permission on the state would you remove first, and what would break?

## Checkpoint

You are done when you can say, without looking:

- The five outcomes of a plan, which two words make a replacement, and what `# forces replacement` points at.
- Why changing one setting can replace a resource you did not touch.
- The first three questions you ask before pressing Confirm, and when you press Discard instead.
- What the state is, why it can hold a password even when the screen says `(sensitive value)`, and what locking prevents.
- The difference between reverting drift and accepting it, and why a refresh-only apply alone does not finish the job.
- What a `moved` block fixes and why `count` can turn a small edit into many replacements.
- Why `-target` leaves unfinished work behind, and what `prevent_destroy` does not protect.
- Why CI saves a plan and applies the file, and what "stale" means.
- In the drill: which single step must come before the apply.

## Claims register

Each behavior claim above rests on one of these sources or on a run. Retrieved means the page was read with a read-only `curl` on that date.

| Claim | Source | Retrieved or run |
|---|---|---|
| `tofu plan` changes nothing; `-out` saves a plan; `-detailed-exitcode` gives 0, 1 or 2; `-refresh-only`, `-replace`, `-target`, `-exclude`, `-lock-timeout`; targeting is for exceptional circumstances; re-check a speculative plan before applying; saved plans can hold sensitive values | [Plan command](https://opentofu.org/docs/cli/commands/plan/) | 2026-10-22 |
| Applying a saved plan runs without a prompt; `-auto-approve`; `tofu show` inspects a plan | [Apply command](https://opentofu.org/docs/cli/commands/apply/) | 2026-10-22 |
| The `actions` values (`no-op`, `create`, `update`, `delete`+`create`, `create`+`delete`, `delete`, `forget`) | [JSON output format](https://opentofu.org/docs/internals/json-format/) | 2026-10-22 |
| State maps configuration to real objects; default local file `terraform.tfstate`; refresh before operations; hand-editing discouraged; one-to-one mapping | [State](https://opentofu.org/docs/language/state/) and [Purpose of state](https://opentofu.org/docs/language/state/purpose/) | 2026-10-22 |
| Locking on write operations; `-lock=false` not recommended; `force-unlock` only for your own stuck lock; not all backends lock | [State locking](https://opentofu.org/docs/language/state/locking/) and [`force-unlock`](https://opentofu.org/docs/cli/commands/force-unlock/) | 2026-10-22 |
| Remote state shares state across a team and supports locking where the backend does | [Remote state](https://opentofu.org/docs/language/state/remote/) | 2026-10-22 |
| State holds all attributes including secrets; local state is plain text; remote state may be encrypted at rest depending on the backend | [Sensitive data in state](https://opentofu.org/docs/language/state/sensitive-data/) | 2026-10-22 |
| Encryption protects at rest, not against data loss or replay | [State encryption](https://opentofu.org/docs/language/state/encryption/) | 2026-10-22 |
| `tofu state` subcommands that modify state write backups; `-backup` option | [State commands](https://opentofu.org/docs/cli/commands/state/) and [Local backend](https://opentofu.org/docs/language/settings/backends/local/) | 2026-10-22 |
| `state list`, `state show`, `state rm` (forgets an object, the next plan creates a new one), `state mv` | [`state list`](https://opentofu.org/docs/cli/commands/state/list/), [`state show`](https://opentofu.org/docs/cli/commands/state/show/), [`state rm`](https://opentofu.org/docs/cli/commands/state/rm/), [`state mv`](https://opentofu.org/docs/cli/commands/state/mv/) | 2026-10-22 |
| `moved` blocks (rename, `count` to `for_each`) | [Refactoring](https://opentofu.org/docs/language/modules/develop/refactoring/) | 2026-10-22 |
| `import` blocks preview an import and record that it was imported, not created | [Import](https://opentofu.org/docs/language/import/) | 2026-10-22 |
| `removed` block with `lifecycle { destroy = false }` | [Resource syntax](https://opentofu.org/docs/language/resources/syntax/) | 2026-10-22 |
| `create_before_destroy`, `prevent_destroy` and what each does and does not do | [Resource behavior](https://opentofu.org/docs/language/resources/behavior/) | 2026-10-22 |
| `count` instances are identified by an index starting at 0 | [`count`](https://opentofu.org/docs/language/meta-arguments/count/) | 2026-10-22 |
| `terraform_data` is built in and needs no provider | [`terraform_data`](https://opentofu.org/docs/language/resources/tf-data/) | 2026-10-22 |
| S3 backend: `use_lockfile`, versioning recommended; `init -migrate-state` | [S3 backend](https://opentofu.org/docs/language/settings/backends/s3/) and [`init`](https://opentofu.org/docs/cli/commands/init/) | 2026-10-22 |
| `local-exec` provisioners are a last resort | [Provisioners](https://opentofu.org/docs/language/resources/provisioners/syntax/) | 2026-10-22 |
| Provider names and newest versions (`hashicorp/local` 2.9.1, `hashicorp/random` 3.9.1) | [registry.opentofu.org](https://registry.opentofu.org/) | 2026-10-22 |
| All plan outputs, error messages, exit codes and file names quoted in the exercises | Observed: OpenTofu 1.12.6, Linux, Bash. The Windows and PowerShell versions were not run (est.). | 2026-10-22 |
| `local_file` reports a hand-edited file as gone; `import` is not implemented for `random_pet` and `local_file`; `random_id` supports import by its `b64_url` value | Observed in the same run; provider behavior can change between versions. | 2026-10-22 |
| The project's stop-and-read, discard and approval rules, destroy guard, and `moved` blocks | This repository: [stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md), [Spacelift](Spacelift.md), [How this project is planned](How-This-Project-Is-Planned.md), [Teardown checklist](Teardown-Checklist.md) | Read in the repository, 2026-10-22 |

Not verified: the PowerShell commands; macOS and Windows behavior (the `sed`-free Bash commands should work on macOS, est.); any OpenTofu 1.13 difference from 1.12.6; the optional remote-state path; how drift detection is offered on any hosted service.

## Where to next

Next: [Spacelift](Spacelift.md), step 16 of the core path on the [Reading order](Reading-Order.md) page, where this project runs plans and holds its state.

Planned lessons in this infrastructure-as-code track, which may not be merged yet when you read this (the links work once they are): lesson 3, [Spacelift from zero](Spacelift-From-Zero.md), and lesson 4, [Build and destroy a stack per service](Build-and-Destroy-Stack-Per-Service.md).
