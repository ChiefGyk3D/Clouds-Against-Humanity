# OpenTofu from zero: init, plan, apply, destroy

Side page to the start-from-zero pages, and lesson I1 of a four-lesson infrastructure-as-code track. Read it after [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) and before [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), or at any point you want to type the commands yourself instead of reading about them. Next: [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash half was run, the PowerShell half was not.** On **2026-10-22** I ran every Bash exercise on this page on Linux with OpenTofu 1.12.6 (the version this repository's CI pins) and pasted the output, trimmed to the lines that matter; the "build and destroy a bunch" script ran ten cycles plus the changing-input run and finished with an empty state every time. I did **not** run any PowerShell command: it is written from the same commands and marked **est.** (estimate) until someone runs it. I did not test macOS or Windows. Providers, versions and install steps were read from [opentofu.org](https://opentofu.org/docs/intro/install/) and [registry.opentofu.org](https://registry.opentofu.org/) on 2026-10-22; the claims register at the bottom lists each one. Versions move; your output may differ in ids, random names and small wording.

> **Prerequisites.** A computer with a terminal and internet access (to download OpenTofu and three small providers once). No cloud account, no money, no programming. If you have never opened a terminal, do the terminal part of [Git from zero](Git-From-Zero.md) or [The terminal and your first script](Terminal-and-Your-First-Script.md) first. About three hours for everything (est.); the centerpiece exercise alone is about 30 minutes (est.).

## What you will be able to do

- Say what infrastructure as code is and why a team wants it, in two sentences.
- Install OpenTofu and check which version you have.
- Read a small configuration: provider, resource, data source, variable, local value and output.
- Run the whole lifecycle by hand: `init`, `fmt`, `validate`, `plan`, `apply`, `destroy`.
- Read a plan, symbol by symbol (`+`, `-`, `~`, `-/+`), and tell an in-place update from a replacement before you apply anything.
- Say what the state file is, why it stays out of git and why it can hold secrets.
- Use `count` and `for_each`, and explain why the second is safer when a list changes.
- Split code into a module and test it with `tofu test` and a mock provider, with nothing created.
- Build and destroy a set of resources ten times in a loop, previewing every destroy and proving the state is empty each time.
- State the OpenTofu and Terraform relationship in neutral terms.

Everything in this lesson is free. Every exercise uses providers that cost nothing and touch nothing except one scratch folder on your own computer. The reading and the exercises are free and always will be; the only optional part that uses your own cloud account is a pointer at the end, and its cost is explained in the lesson that does it, not here.

## The free path and the optional own-account path

| Path | What it uses | Cost | Where |
|---|---|---|---|
| **Free (this page)** | OpenTofu and three providers (`local`, `random` and the built-in `terraform_data`) that only write files and make random names in one folder | $0 | Exercises 1 to 7 |
| **Optional own-account** | A real cloud provider in your own account, one stack per service | Your own provider bill; the figures and the teardown steps live in the I4 lesson, [Build and destroy: a stack per service](Build-and-Destroy-Stack-Per-Service.md), and in [docs/cost.md](../cost.md) for this project's own ceiling | Not on this page |

Do the free path first. You lose nothing by stopping there: the lifecycle, the plan symbols, the state file and the destroy habit are the same for a file on your disk and for a server in a data center. Only the bill differs.

## What infrastructure as code is, and why

**Infrastructure** is the things your software runs on: servers, networks, firewalls, storage, user accounts. **Infrastructure as code (IaC)** means you write those things down in text files, and a tool reads the files and makes the real thing match. The alternative, building it by clicking in a web console, is nicknamed **ClickOps** (see [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) for the long version).

Why a team wants the text files:

- **Repeatable.** Run it twice, get the same result. A new environment is the same files with different inputs.
- **Reviewable.** A change is a diff in a pull request that a colleague reads before anything happens, which a click cannot offer.
- **Recoverable.** If a server is lost, the description of it is not.
- **Removable.** The tool knows what it built, so it can remove exactly that, which is the thing this lesson practices the most. Forgotten, still-running machines are where surprise bills come from (see [How money works in the cloud](How-Money-Works-in-the-Cloud.md)).

The honest limit: text files do not make a design good. IaC faithfully builds a bad firewall rule every time. It makes mistakes repeatable and reviewable, and that is a win only if someone reviews.

## Install OpenTofu

**OpenTofu** is the tool; its command is `tofu`. The documentation lists many install methods; these are the ones that need the fewest steps. Read the page for your system before you copy anything: [Installing OpenTofu](https://opentofu.org/docs/intro/install/) (read 2026-10-22).

| System | Command from opentofu.org (read 2026-10-22) |
|---|---|
| macOS, or Linux with Homebrew | `brew update` then `brew install opentofu` |
| Windows, with winget | `winget install --exact --id=OpenTofu.Tofu` (open a new terminal afterwards so `PATH` updates) |
| Windows, with Scoop | `scoop bucket add main` then `scoop install main/opentofu` |
| Debian or Ubuntu | A package repository you add with a signing key; the page has the exact steps, so follow them there rather than from a copy here |
| Any Linux, macOS or Windows | A standalone installer script. The page tells you to download it, **inspect it**, then run it; do that |

The page also covers Fedora, RHEL-family, Alpine, Snap, FreeBSD and a container image. Whatever you pick, the check is the same:

```bash
tofu version
```

On 2026-10-22 the OpenTofu website's banner announced **1.13.0**, while this repository pins **1.12.6** in CI and the output in this lesson comes from 1.12.6. Everything here should work on both; if your version is older than 1.8, upgrade (the repository's tests need 1.8 or newer, see [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md)).

## The parts of a configuration

OpenTofu reads every file ending in `.tf` in a folder as one configuration, written in **HCL** (a small configuration language, see [Data formats and config files](Data-Formats-JSON-YAML-HCL.md)). Six kinds of block cover most of what you will read.

| Block | In plain words | Example from this lesson |
|---|---|---|
| **`terraform` / `required_providers`** | Which plugins this code needs, and which versions are acceptable | `local = { source = "hashicorp/local", version = "~> 2.5" }` |
| **Provider** | A plugin that knows how to talk to one service. Here the service is your own disk or a random-number generator | `hashicorp/local`, `hashicorp/random` |
| **Resource** | One thing to create and keep track of | `resource "local_file" "note" { ... }` |
| **Data source** | One thing that already exists, which you look up instead of creating | `data "local_file" "readback" { ... }` |
| **Variable** | An input. Callers can change it without editing the code | `variable "greeting" { ... }` |
| **Local value** | A named value used inside the code, like a variable nobody can set from outside | `locals { prefix = "lab" }` |
| **Output** | A value printed at the end and available to other code | `output "pet" { ... }` |

A **provider** is downloaded from a **registry** (a public catalog) when you run `init`. The registry OpenTofu uses is [registry.opentofu.org](https://registry.opentofu.org/). On 2026-10-22 its API listed `hashicorp/local` (newest 2.9.1), `hashicorp/random` (newest 3.9.1) and `hashicorp/null` (newest 3.3.2). The built-in `terraform_data` resource needs no download at all; `init` prints "terraform.io/builtin/terraform is built in to OpenTofu".

Resource names have two parts: `local_file.note` is the type (`local_file`, set by the provider) and your name for it (`note`). That pair is the resource's **address**, and you will see addresses in every plan and in the state.

## The lifecycle: init, fmt, validate, plan, apply, destroy

| Command | What it does | Changes anything real? |
|---|---|---|
| `tofu init` | Downloads the providers and modules the code names, writes the lock file | Only your folder (a `.terraform` directory and a `.terraform.lock.hcl` file) |
| `tofu fmt` | Rewrites your files to the standard layout (spacing, alignment) | Only your source files' whitespace |
| `tofu validate` | Checks the code is well-formed and consistent. Does not read real infrastructure | No |
| `tofu plan` | Compares the code, the state and reality, and prints what it would do | No |
| `tofu apply` | Shows a plan, asks you to type `yes`, then does it | **Yes** |
| `tofu destroy` | Removes everything the state says this configuration created | **Yes** |

Two details worth knowing now:

- `plan` changes nothing, so run it as often as you like. `plan -destroy` shows what `destroy` would remove without removing anything. The [plan command page](https://opentofu.org/docs/cli/commands/plan/) (read 2026-10-22) describes both.
- `.terraform.lock.hcl` records the exact provider versions and checksums `init` chose, so a colleague (or a CI job) gets the same ones. Commit it. This repository does too.

`apply` and `destroy` ask for a typed `yes` unless you pass `-auto-approve`. In your scratch folder `-auto-approve` is fine, and the scripts below use it. On anything real, a human reads the plan and approves; that is the point of [Spacelift](Spacelift.md) waiting for confirmation on every run.

## How to read a plan

A plan lists each resource with a symbol at the left. Learn these five and you can read most plans.

| Symbol | Word in the plan | Meaning | Danger |
|---|---|---|---|
| `+` | will be created | A new thing appears | Low, but check cost |
| `-` | will be destroyed | A thing is deleted | High if it holds data |
| `~` | will be updated in-place | The thing stays; one setting changes | Usually low |
| `-/+` | must be replaced | **Destroy the old, create a new one.** The ids change and anything stored in it is gone | High: this is a delete wearing a small coat |
| `<=` | will be read during apply | A data source is looked up when the plan cannot know the answer yet | None |

The summary line at the bottom, `Plan: 3 to add, 1 to change, 2 to destroy.`, counts a replacement as one add **and** one destroy. A line that says `0 to change` and `2 to destroy` can still be hiding a replacement of something important, so read the addresses and the `forces replacement` comments, not only the totals. (A variant `+/-`, which creates the replacement before destroying the old one, appears when the code asks for that order; est., not exercised here.)

Some changes are in-place for one setting and a replacement for another: renaming a server's label may be a `~`, while changing its image may be a `-/+`. The plan tells you which, and it marks the setting responsible with `# forces replacement`. Exercise 3 makes you cause each of them on purpose.

## The state file in plain words

When `apply` creates something, OpenTofu writes down what it made and the real id the provider returned. That record is the **state**, by default a JSON file named `terraform.tfstate` in the folder (the file name keeps the old tool's name). Next time, `plan` compares three things: your code (what you want), the state (what OpenTofu believes it made) and reality (what is really there, refreshed from the provider). Without the state, the tool would not know that the server named `web` in your code is the machine with a particular id.

Three rules follow, and each has a reason:

1. **Never edit it by hand.** The [state page](https://opentofu.org/docs/language/state/) (read 2026-10-22) says direct editing is discouraged and points to the `tofu state` commands, which keep the file consistent.
2. **Never commit it to git.** It is working data, not source, and it changes on every apply. This repository's `.gitignore` lists `*.tfstate` and `*.tfstate.*`. Git also keeps history forever, which leads to rule 3.
3. **Treat it as secret.** The [sensitive data page](https://opentofu.org/docs/language/state/sensitive-data/) (read 2026-10-22) says the state contains resource ids and **all resource attributes**, and that for some resources that includes initial passwords. Marking a value `sensitive` hides it from the screen, not from the file. Exercise 4 shows it.

For real work the state does not stay on one laptop; a team keeps it in a shared **backend** (remote storage with locking and, where offered, encryption) so two people cannot apply at once. Spacelift is that place for this project, and lesson I2 goes deeper ([Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md)).

## Many copies: count and for_each

Both make several copies of one resource block.

- **`count = 3`** numbers the copies `0, 1, 2`. Addresses look like `local_file.by_count[1]`.
- **`for_each = toset(["alpha", "bravo"])`** (or a map) names the copies by key. Addresses look like `local_file.by_key["alpha"]`.

The difference bites when the list changes. With `count`, the copies are tied to their position, so removing the first item makes everything after it shift down one place, and the plan wants to change or replace things you did not touch. With `for_each`, each copy is tied to its key, so removing `alpha` removes only `alpha`. Exercise 5 shows the plan for both side by side. A good default is `for_each` for anything you might later add to or remove from in the middle, and `count` for "zero or one of these" switches.

## Modules at beginner level

A **module** is a folder of `.tf` files that you call like a function: it takes inputs (variables), builds resources, and gives back outputs. Your main folder is itself a module (the "root" module); it can call others with a `module` block and a `source` path. Why bother: the same module can build two similar things without copying code. This repository's `firewall` module builds both the baseline firewall and the connector firewall with different inputs ([OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md)). Exercise 6 builds a tiny one and calls it twice.

## Tests without building anything: tofu test and mock providers

`tofu test` runs files ending in `.tftest.hcl` (also `.tofutest.hcl` and the `.json` variants) from the current folder or a `tests` folder; each `run` block makes a plan or an apply and checks **assertions** you wrote ([test command page](https://opentofu.org/docs/cli/commands/test/), read 2026-10-22). A **mock provider** (`mock_provider "local" {}`) replaces the real plugin with a fake one that returns made-up values, so a test with `command = plan` and a mock builds nothing, needs no credentials and costs nothing. This is how every module and stack in this repository is tested in CI. `expect_failures` turns the test around: it passes only if the named validation rejects the input, which proves your guard rails fire.

## OpenTofu and Terraform

**Terraform** was created by HashiCorp. HashiCorp moved Terraform from an open-source license to the Business Source License (BUSL). **OpenTofu** is a fork of Terraform created in response, now hosted by the Linux Foundation; its [FAQ](https://opentofu.org/faq/) (read 2026-10-22) says it was started "as an initiative of Gruntwork, Spacelift, Harness, Env0, Scalr, and others". The two tools share a language and a lot of history, and they are developed separately now, so features can differ and the project's own FAQ says OpenTofu's aim is feature parity "for future releases", which is a goal and not a promise about any particular version.

What the FAQ says that matters to a beginner:

- Providers: "OpenTofu will not have its own providers"; it works with the existing Terraform providers but "uses a separate registry".
- State files: OpenTofu "will work with existing state files up to those created with Terraform versions 1.5.x". Mixing the two tools on one state is a decision to make deliberately, not by accident.
- The FAQ's own advice for personal use is that either tool works at the start, because the BUSL has no restriction for non-commercial use.

This is the maintainer's choice, not a verdict: this project uses OpenTofu so a public teaching repository sits on a tool with an open-source license a vendor cannot change; you can learn it and carry the skills to Terraform jobs, because the commands and the language are close. Read the license terms yourself before using either tool in a company; this page is not legal advice. Where the project's files say "Terraform" (the lock file name, Spacelift's workflow setting), that is the ecosystem's naming, as [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) explains.

## Hands-on: free exercises

All exercises use one scratch folder, `cah-tofu-lab`, in your home directory, and nothing outside it. Nothing here connects to a cloud account, reads a credential or opens a port. The only network traffic is the one-time provider download in `init`. The files the exercises make are tiny text files.

Every exercise has four parts: **Predict** (write your guess before running anything; guessing first is what makes the output teach you), **Do**, **Check** and **Undo**. The PowerShell versions are **est.**: they are the same steps in PowerShell 7 syntax and were not run. Use PowerShell 7 (`pwsh`); older Windows PowerShell 5.1 can write a byte-order mark into files, which HCL tools may not like (est.).

### Exercise 1: check the install

**Predict.** What will `tofu version` print besides the number?

**Do.**

```bash
tofu version
mkdir -p "$HOME/cah-tofu-lab" && cd "$HOME/cah-tofu-lab" && pwd
```

PowerShell (est.):

```powershell
tofu version
New-Item -ItemType Directory -Force -Path "$HOME\cah-tofu-lab" | Out-Null
Set-Location "$HOME\cah-tofu-lab"; (Get-Location).Path
```

**Check.** A line like `OpenTofu v1.12.6` and `on linux_amd64` (your version and platform will differ), then the full path of the scratch folder. If `tofu` is "not found", the install did not reach your `PATH`; open a new terminal and try again.

**Undo.** Nothing to undo; the folder is empty and is removed at the end of the lesson.

### Exercise 2: your first init, fmt, validate, plan, apply, destroy

**Predict.** The code below describes four resources and one data source. How many will the plan say it will add? Will the data source be counted?

**Do.** Create a folder for this exercise and write the configuration. The `locals` block is deliberately crammed onto one line so `fmt` has something to fix.

```bash
mkdir -p "$HOME/cah-tofu-lab/first" && cd "$HOME/cah-tofu-lab/first"
cat > main.tf <<'HCL'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "greeting" {
  type    = string
  default = "hello"
  validation {
    condition     = length(var.greeting) > 0
    error_message = "greeting must not be empty."
  }
}

variable "label" {
  type    = string
  default = "a"
}

variable "release" {
  type    = number
  default = 1
}

variable "copies" {
  type    = number
  default = 2
}

locals { prefix="lab" }

resource "random_pet" "name" {
  length = 2
}

resource "local_file" "note" {
  count    = var.copies
  filename = "${path.module}/out/${local.prefix}-${count.index}.txt"
  content  = "${var.greeting} from ${random_pet.name.id}\n"
}

resource "terraform_data" "tag" {
  input            = var.label
  triggers_replace = [var.release]
}

data "local_file" "readback" {
  filename = local_file.note[0].filename
}

output "first_note" {
  value = data.local_file.readback.content
}

output "pet" {
  value = random_pet.name.id
}
HCL

tofu init
tofu fmt
tofu validate
tofu plan
tofu apply          # type yes when asked
tofu plan           # again, straight after
```

PowerShell (est.):

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\cah-tofu-lab\first" | Out-Null
Set-Location "$HOME\cah-tofu-lab\first"
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "greeting" {
  type    = string
  default = "hello"
  validation {
    condition     = length(var.greeting) > 0
    error_message = "greeting must not be empty."
  }
}

variable "label" {
  type    = string
  default = "a"
}

variable "release" {
  type    = number
  default = 1
}

variable "copies" {
  type    = number
  default = 2
}

locals { prefix="lab" }

resource "random_pet" "name" {
  length = 2
}

resource "local_file" "note" {
  count    = var.copies
  filename = "${path.module}/out/${local.prefix}-${count.index}.txt"
  content  = "${var.greeting} from ${random_pet.name.id}\n"
}

resource "terraform_data" "tag" {
  input            = var.label
  triggers_replace = [var.release]
}

data "local_file" "readback" {
  filename = local_file.note[0].filename
}

output "first_note" {
  value = data.local_file.readback.content
}

output "pet" {
  value = random_pet.name.id
}
'@ | Set-Content -Path main.tf -Encoding utf8NoBOM

tofu init
tofu fmt
tofu validate
tofu plan
tofu apply          # type yes when asked
tofu plan           # again, straight after
```

**Check.**

- `init` prints "Installing hashicorp/local" and "hashicorp/random" with a version each, then "OpenTofu has been successfully initialized!". The folder now has `.terraform` and `.terraform.lock.hcl`.
- `fmt` prints `main.tf`, the name of the file it rewrote. Open it: the `locals` block is now three lines.
- `validate` prints `Success! The configuration is valid.`
- The first `plan` ends `Plan: 4 to add, 0 to change, 0 to destroy.` The data source is not counted: it adds nothing, and the plan marks it `<=`. The outputs show `(known after apply)` because the random name does not exist yet.
- `apply` shows the plan again and asks for `yes`; it ends `Apply complete! Resources: 4 added, 0 changed, 0 destroyed.` and prints `pet = "..."` with two random words.
- The second `plan` should say `No changes. Your infrastructure matches the configuration.` That is **idempotence**: running the same code again changes nothing.
- Look at what exists: `ls out` (or `Get-ChildItem out`) lists `lab-0.txt` and `lab-1.txt`.

**Undo.** Preview, then destroy:

```bash
tofu plan -destroy
tofu destroy        # type yes when asked
tofu state list | wc -l
```

PowerShell (est.):

```powershell
tofu plan -destroy
tofu destroy        # type yes when asked
@(tofu state list).Count
```

The preview ends `Plan: 0 to add, 0 to change, 4 to destroy.`, the destroy ends `Destroy complete! Resources: 4 destroyed.` and the count is `0`. Keep this folder for the next exercises.

### Exercise 3: read the plan symbols

**Predict.** For each of the following, write down the symbol you expect and the summary line before you run it: (a) change `label` from `a` to `b`; (b) change `greeting` to `bye`; (c) change `release` from 1 to 2; (d) set `copies` to 1.

**Do.** The `first` folder is empty of resources after Exercise 2, so build it again, then plan each change one at a time. `plan` never changes anything, so you can try them all.

```bash
cd "$HOME/cah-tofu-lab/first"
tofu apply -auto-approve > /dev/null
tofu plan -no-color -var label=b       | grep -E '^(Plan:|  # )'
tofu plan -no-color -var greeting=bye  | grep -E '^(Plan:|  # )'
tofu plan -no-color -var release=2     | grep -E '^(Plan:|  # )'
tofu plan -no-color -var copies=1      | grep -E '^(Plan:|  # )'
tofu plan -no-color -var greeting=bye  | grep -B2 -A6 'forces replacement'
```

PowerShell (est.):

```powershell
Set-Location "$HOME\cah-tofu-lab\first"
tofu apply -auto-approve | Out-Null
foreach ($v in 'label=b','greeting=bye','release=2','copies=1') {
  "--- $v"
  tofu plan -no-color -var $v | Select-String '^(Plan:|  # )'
}
tofu plan -no-color -var greeting=bye | Select-String -Context 2,6 'forces replacement'
```

(`-auto-approve` is acceptable here because it is your scratch folder and the plan is the one you just read in Exercise 2. `-no-color` stops the tool from adding color codes that would break the `grep`; use it whenever you filter OpenTofu's output.)

**Check.** What I got on 2026-10-22, trimmed:

```text
(a)  # terraform_data.tag will be updated in-place
     Plan: 0 to add, 1 to change, 0 to destroy.
(b)  # data.local_file.readback will be read during apply
     # (depends on a resource or a module with changes pending)
     # local_file.note[0] must be replaced
     # local_file.note[1] must be replaced
     Plan: 2 to add, 0 to change, 2 to destroy.
(c)  # terraform_data.tag must be replaced
     Plan: 1 to add, 0 to change, 1 to destroy.
(d)  # data.local_file.readback will be read during apply
     # (depends on a resource or a module with changes pending)
     # local_file.note[1] will be destroyed
     # (because index [1] is out of range for count)
     Plan: 0 to add, 0 to change, 1 to destroy.
```

The `data.local_file.readback` lines are the `<=` row of the symbol table: the data source is read again at apply time because the files it reads are changing. It is not counted in the `Plan:` line.

(a) is a `~`: changing `input` on `terraform_data` updates it where it stands. (b) is `-/+` twice: the `content` argument of `local_file` cannot change in place, and the plan prints `# forces replacement` beside it; "2 to add, 2 to destroy" is two replacements. (c) is `-/+` because `triggers_replace` exists to force a replacement when its value changes. (d) is a plain `-`.

Notice the summary lines in (a) and (b): the word "change" is in-place only. A replacement hides inside "add" and "destroy" counts that both went up by the same amount, which is the clue.

**Undo.**

```bash
tofu destroy -auto-approve -no-color | tail -1
tofu state list | wc -l
```

PowerShell (est.): `tofu destroy -auto-approve -no-color | Select-Object -Last 1; @(tofu state list).Count`

Expect `Destroy complete! Resources: 4 destroyed.` and `0`. Leave the folder for Exercise 4.

### Exercise 4: the state file, and why it can hold secrets

**Predict.** If I mark a password `sensitive`, will it be missing from the state file?

**Do.** Add a second file to the same folder, build, and look in three places: the screen, `tofu state show`, and the file itself. The password is a random string made on your computer; it protects nothing.

```bash
cd "$HOME/cah-tofu-lab/first"
cat > secret.tf <<'HCL'
resource "random_password" "demo" {
  length = 16
}

output "demo_password" {
  value     = random_password.demo.result
  sensitive = true
}
HCL
tofu apply -no-color -auto-approve | grep -E 'demo|Apply'
tofu state list
tofu state show random_password.demo | head -6
ls -l terraform.tfstate
grep -m1 '"result"' terraform.tfstate | sed 's/: "[^"]*"/: "<hidden here, visible in the file>"/'
```

PowerShell (est.):

```powershell
Set-Location "$HOME\cah-tofu-lab\first"
@'
resource "random_password" "demo" {
  length = 16
}

output "demo_password" {
  value     = random_password.demo.result
  sensitive = true
}
'@ | Set-Content -Path secret.tf -Encoding utf8NoBOM
tofu apply -no-color -auto-approve | Select-String 'demo|Apply'
tofu state list
tofu state show random_password.demo | Select-Object -First 6
Get-Item terraform.tfstate | Select-Object Name, Length
(Select-String -Path terraform.tfstate -Pattern '"result"' | Select-Object -First 1).Line -replace ': "[^"]*"', ': "<hidden here, visible in the file>"'
```

**Check.**

- The apply output shows `demo_password = <sensitive>` (and in the plan, `(sensitive value)`): OpenTofu hides it **on screen**.
- `tofu state list` shows six addresses: the five resources, including `random_password.demo`, and the data source. `state show` prints `bcrypt_hash = (sensitive value)`: the command also hides it.
- `terraform.tfstate` is a few kilobytes and, searched directly, has a line `"result": "..."` holding the 16 characters in plain text. The `sed` and `-replace` above print the line with the value blanked on purpose, so you see the shape without copying the secret into your terminal history. Open the file in an editor if you want to see it; it is yours and random.
- Also `"sensitive_attributes"` entries in the file mark which values the tool hides on screen. That list is a display hint, not encryption.

So the answer to Predict is no: `sensitive = true` controls what is printed, not what is stored. That is exactly why the state is kept out of git (this repository's `.gitignore` excludes it) and kept in a store with access control and logging when real passwords are in it.

**Undo.**

```bash
tofu destroy -no-color -auto-approve | tail -1
rm secret.tf
```

PowerShell (est.): `tofu destroy -no-color -auto-approve | Select-Object -Last 1; Remove-Item secret.tf`

Expect `Destroy complete! Resources: 5 destroyed.` The `.tfstate` file now lists no resources, but old values may linger in `terraform.tfstate.backup`; the scratch folder is deleted at the end, which removes those too.

### Exercise 5: count against for_each

**Predict.** A list holds `alpha`, `bravo`, `charlie`. You remove `alpha`. How many copies will the `count` version touch? How many will the `for_each` version touch?

**Do.**

```bash
mkdir -p "$HOME/cah-tofu-lab/copies" && cd "$HOME/cah-tofu-lab/copies"
cat > main.tf <<'HCL'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

# count: copies are numbered 0, 1, 2 in list order
resource "local_file" "by_count" {
  count    = length(var.names)
  filename = "${path.module}/out/count-${var.names[count.index]}.txt"
  content  = "${var.names[count.index]}\n"
}

# for_each: copies are named by their key
resource "local_file" "by_key" {
  for_each = toset(var.names)
  filename = "${path.module}/out/key-${each.key}.txt"
  content  = "${each.key}\n"
}
HCL
tofu init > /dev/null
tofu apply -no-color -auto-approve | tail -1
tofu state list
tofu plan -no-color -var 'names=["bravo","charlie"]' | grep -E '^(Plan:|  # )'
```

PowerShell (est.): create `main.tf` with a here-string as in Exercise 2 (the same HCL), then:

```powershell
tofu init | Out-Null
tofu apply -no-color -auto-approve | Select-Object -Last 1
tofu state list
tofu plan -no-color -var 'names=["bravo","charlie"]' | Select-String '^(Plan:|  # )'
```

If PowerShell mangles the quotes in the `-var` value, put the list in a file named `drop.tfvars` containing `names = ["bravo", "charlie"]` and use `-var-file=drop.tfvars` instead (est.).

**Check.** On 2026-10-22 the state listed `by_count[0..2]` and `by_key["alpha"|"bravo"|"charlie"]`, and the plan said:

```text
  # local_file.by_count[0] must be replaced
  # local_file.by_count[1] must be replaced
  # local_file.by_count[2] will be destroyed
  # local_file.by_key["alpha"] will be destroyed
Plan: 2 to add, 0 to change, 4 to destroy.
```

Removing `alpha` made `count` replace two copies it did not need to touch (position 0 was `alpha`, now it is `bravo`, and so on) and destroy the last one. `for_each` removed exactly `alpha`. In a real stack, "replace" can mean a server rebuilt and its data lost; this is the practical reason to prefer `for_each` for lists that change.

**Undo.** `tofu destroy -no-color -auto-approve | tail -1` (PowerShell: `... | Select-Object -Last 1`). Expect `Destroy complete! Resources: 6 destroyed.`

### Exercise 6: a module, and a test with a mock provider

**Predict.** If `tofu test` plans a module with a mock provider, will a file appear in `out`?

**Do.** Write a module with one resource, call it twice, then test it.

```bash
mkdir -p "$HOME/cah-tofu-lab/modlab/modules/note" "$HOME/cah-tofu-lab/modlab/tests"
cd "$HOME/cah-tofu-lab/modlab"
cat > modules/note/main.tf <<'HCL'
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.5" }
  }
}

variable "name" {
  type = string
}

resource "local_file" "this" {
  filename = "${path.root}/out/${var.name}.txt"
  content  = "note: ${var.name}\n"
}

output "path" {
  value = local_file.this.filename
}
HCL
cat > main.tf <<'HCL'
variable "second_name" {
  type    = string
  default = "second"
  validation {
    condition     = can(regex("^[a-z]+$", var.second_name))
    error_message = "second_name must be lower-case letters only."
  }
}

module "first" {
  source = "./modules/note"
  name   = "first"
}

module "second" {
  source = "./modules/note"
  name   = var.second_name
}

output "paths" {
  value = [module.first.path, module.second.path]
}
HCL
cat > tests/note.tftest.hcl <<'HCL'
mock_provider "local" {}

run "paths_are_named_after_the_module_inputs" {
  command = plan
  assert {
    condition     = module.first.path == "./out/first.txt"
    error_message = "first note should land in out/first.txt"
  }
  assert {
    condition     = module.second.path == "./out/second.txt"
    error_message = "second note should land in out/second.txt"
  }
}

run "an_upper_case_name_is_rejected" {
  command = plan
  variables {
    second_name = "LOUD"
  }
  expect_failures = [var.second_name]
}
HCL
tofu init > /dev/null
tofu test
ls out 2>&1
tofu apply -no-color -auto-approve | tail -6
```

PowerShell (est.): create the three files with here-strings exactly as in Exercise 2 (same HCL, paths `modules\note\main.tf`, `main.tf`, `tests\note.tftest.hcl`; create the folders with `New-Item -ItemType Directory -Force`), then:

```powershell
tofu init | Out-Null
tofu test
Get-ChildItem out -ErrorAction SilentlyContinue
tofu apply -no-color -auto-approve | Select-Object -Last 6
```

**Check.** `tofu test` prints each run as `pass` and ends `Success! 2 passed, 0 failed.` Then `ls out` reports that `out` does not exist: the mock provider replaced `local`, so the test made no file. The `apply` afterward is the real thing: `Apply complete! Resources: 2 added`, and it prints the two paths (`./out/first.txt` and `./out/second.txt`). The second test run passes **because** the bad input fails: change `expect_failures` to something else and it would fail with "Missing expected failure".

Two lessons here. The module is the unit you test; and the test checks the plan's promises (names, counts, guard rails) without any real resource, which is why this repository's CI can test every stack with no cloud credentials.

**Undo.** `tofu destroy -no-color -auto-approve | tail -1` (PowerShell: `| Select-Object -Last 1`). Expect `Destroy complete! Resources: 2 destroyed.`

### Exercise 7 (centerpiece): build and destroy a bunch

This is the habit that makes IaC safe to use: build, look, preview the destroy, destroy, **prove** nothing is left. You will do it ten times, then do a run where the inputs change between applies.

**Predict.** After each destroy, how many resources should `tofu state list` show? What will the destroy preview say for a four-resource build? In the changing-input run, which of these three changes will be a `~`: a different `label`, a different `greeting`, a different `release`?

**Do.** Save the script, read it (it is short, and you should read any script before running it), then run it. It makes one fresh folder per cycle under the lab folder, keeps one shared download cache so providers are fetched once, and stops with an error the moment a state is not empty.

```bash
cat > "$HOME/cah-tofu-lab/bunch.sh" <<'SH'
#!/usr/bin/env bash
# Build and destroy a bunch: N full cycles in scratch folders, state counted after each.
set -euo pipefail

LAB="${1:?usage: bunch.sh LAB_DIR [CYCLES]}"
CYCLES="${2:-10}"
export TF_PLUGIN_CACHE_DIR="$LAB/plugin-cache"   # download each provider once, reuse it
export TF_IN_AUTOMATION=1                        # quieter, script-friendly output
mkdir -p "$TF_PLUGIN_CACHE_DIR"

write_config() {
  cat > main.tf <<'HCL'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "greeting" {
  type    = string
  default = "hello"
}

variable "label" {
  type    = string
  default = "a"
}

variable "release" {
  type    = number
  default = 1
}

resource "random_pet" "name" {
  length = 2
}

resource "local_file" "note" {
  count    = 2
  filename = "${path.module}/out/note-${count.index}.txt"
  content  = "${var.greeting} from ${random_pet.name.id}\n"
}

resource "terraform_data" "tag" {
  input            = var.label
  triggers_replace = [var.release]
}
HCL
}

# Count what the state file tracks. An empty state prints nothing, so wc gives 0.
count_state() { tofu state list 2>/dev/null | wc -l | tr -d ' '; }

pass=0
for i in $(seq 1 "$CYCLES"); do
  dir="$LAB/cycle-$i"; mkdir -p "$dir"; cd "$dir"; write_config
  tofu init -input=false -no-color > init.log
  tofu apply -auto-approve -input=false -no-color -var "greeting=run-$i" > apply.log
  built=$(count_state)
  # Preview before every destroy: this is the habit. Read it, then destroy.
  preview=$(tofu plan -destroy -input=false -no-color | grep '^Plan:')
  tofu destroy -auto-approve -input=false -no-color > destroy.log
  left=$(count_state)
  echo "cycle $i: built=$built | preview: $preview | left after destroy=$left"
  if [ "$left" -ne 0 ]; then echo "STATE NOT EMPTY in $dir" >&2; exit 1; fi
  pass=$((pass + 1))
done
echo "OK: $pass of $CYCLES cycles ended with an empty state."

# The changing-input run: one change at a time, read each plan, apply, repeat.
dir="$LAB/change-run"; mkdir -p "$dir"; cd "$dir"; write_config
tofu init -input=false -no-color > init.log
tofu apply -auto-approve -input=false -no-color > apply.log
VARS=()    # each change is kept, so each plan differs from the last by exactly one thing
for change in "label=b" "greeting=bye" "release=2"; do
  VARS+=(-var "$change")
  echo "--- change: $change"
  tofu plan -input=false -no-color "${VARS[@]}" | grep -E '^(Plan:|  # )' || true
  tofu apply -auto-approve -input=false -no-color "${VARS[@]}" > /dev/null
done
tofu plan -destroy -input=false -no-color "${VARS[@]}" | grep '^Plan:'
tofu destroy -auto-approve -input=false -no-color "${VARS[@]}" > destroy.log
echo "change-run: state left after destroy=$(count_state)"
SH
chmod +x "$HOME/cah-tofu-lab/bunch.sh"
"$HOME/cah-tofu-lab/bunch.sh" "$HOME/cah-tofu-lab/bunch" 10
```

PowerShell (est.), same loop in PowerShell 7. Two steps: save the configuration as a template file, then save and run the script (a here-string cannot contain another one, so the script copies the template).

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\cah-tofu-lab" | Out-Null
@'
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "~> 2.5" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

variable "greeting" {
  type    = string
  default = "hello"
}

variable "label" {
  type    = string
  default = "a"
}

variable "release" {
  type    = number
  default = 1
}

resource "random_pet" "name" {
  length = 2
}

resource "local_file" "note" {
  count    = 2
  filename = "${path.module}/out/note-${count.index}.txt"
  content  = "${var.greeting} from ${random_pet.name.id}\n"
}

resource "terraform_data" "tag" {
  input            = var.label
  triggers_replace = [var.release]
}

'@ | Set-Content -Path "$HOME\cah-tofu-lab\template.tf" -Encoding utf8NoBOM

@'
# Build and destroy a bunch: N full cycles in scratch folders, state counted after each.
param(
  [Parameter(Mandatory)][string]$Lab,
  [int]$Cycles = 10
)
$ErrorActionPreference = 'Stop'

$env:TF_PLUGIN_CACHE_DIR = Join-Path $Lab 'plugin-cache'   # download each provider once
$env:TF_IN_AUTOMATION = '1'                                # quieter, script-friendly output
New-Item -ItemType Directory -Force -Path $env:TF_PLUGIN_CACHE_DIR | Out-Null
$template = Join-Path (Split-Path $Lab -Parent) 'template.tf'

# Run tofu and stop the script if it exits non-zero (PowerShell does not do this by itself).
function Tofu {
  & tofu @args
  if ($LASTEXITCODE -ne 0) { throw "tofu $($args -join ' ') failed with exit code $LASTEXITCODE" }
}

# Count what the state file tracks. An empty state prints nothing, so the count is 0.
function Count-State { @(& tofu state list 2>$null).Count }

$pass = 0
foreach ($i in 1..$Cycles) {
  $dir = Join-Path $Lab "cycle-$i"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Set-Location $dir
  Copy-Item $template main.tf
  Tofu init -input=false -no-color | Out-File init.log
  Tofu apply -auto-approve -input=false -no-color -var "greeting=run-$i" | Out-File apply.log
  $built = Count-State
  # Preview before every destroy: this is the habit. Read it, then destroy.
  $preview = (Tofu plan -destroy -input=false -no-color | Select-String '^Plan:').Line
  Tofu destroy -auto-approve -input=false -no-color | Out-File destroy.log
  $left = Count-State
  Write-Host "cycle ${i}: built=$built | preview: $preview | left after destroy=$left"
  if ($left -ne 0) { throw "STATE NOT EMPTY in $dir" }
  $pass++
}
Write-Host "OK: $pass of $Cycles cycles ended with an empty state."

# The changing-input run: one change at a time, read each plan, apply, repeat.
$dir = Join-Path $Lab 'change-run'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Set-Location $dir
Copy-Item $template main.tf
Tofu init -input=false -no-color | Out-File init.log
Tofu apply -auto-approve -input=false -no-color | Out-File apply.log
$vars = @()   # each change is kept, so each plan differs from the last by exactly one thing
foreach ($change in 'label=b', 'greeting=bye', 'release=2') {
  $vars += '-var', $change
  Write-Host "--- change: $change"
  Tofu plan -input=false -no-color @vars | Select-String '^(Plan:|  # )' | ForEach-Object { $_.Line }
  Tofu apply -auto-approve -input=false -no-color @vars | Out-Null
}
Tofu plan -destroy -input=false -no-color @vars | Select-String '^Plan:' | ForEach-Object { $_.Line }
Tofu destroy -auto-approve -input=false -no-color @vars | Out-File destroy.log
Write-Host "change-run: state left after destroy=$(Count-State)"
'@ | Set-Content -Path "$HOME\cah-tofu-lab\bunch.ps1" -Encoding utf8NoBOM

& "$HOME\cah-tofu-lab\bunch.ps1" -Lab "$HOME\cah-tofu-lab\bunch" -Cycles 10
```

**Check.** The whole run, including the one-time provider download, took about 30 seconds on 2026-10-22. Output, trimmed to cycles 1, 10 and the end:

```text
cycle 1: built=4 | preview: Plan: 0 to add, 0 to change, 4 to destroy. | left after destroy=0
...
cycle 10: built=4 | preview: Plan: 0 to add, 0 to change, 4 to destroy. | left after destroy=0
OK: 10 of 10 cycles ended with an empty state.
--- change: label=b
  # terraform_data.tag will be updated in-place
Plan: 0 to add, 1 to change, 0 to destroy.
--- change: greeting=bye
  # local_file.note[0] must be replaced
  # local_file.note[1] must be replaced
Plan: 2 to add, 0 to change, 2 to destroy.
--- change: release=2
  # terraform_data.tag must be replaced
Plan: 1 to add, 0 to change, 1 to destroy.
Plan: 0 to add, 0 to change, 4 to destroy.
change-run: state left after destroy=0
```

What each part proves:

- Ten init, apply, destroy cycles, each in its own folder, each ending with the counter at `0` and the script stopping if it were not. "It said `Destroy complete`" is a claim; a count of zero from the state is evidence.
- The preview (`plan -destroy`) matched the build every time: four things built, four to destroy. If a preview ever lists something you did not expect, you stop. That habit is what saves you on a real stack.
- The changing-input run answers Predict: `label` is the `~` (in place), `greeting` is a double replacement, and `release` is a replacement because that is what `triggers_replace` is for.

Look in a cycle folder to see what the script left: `ls "$HOME/cah-tofu-lab/bunch/cycle-1"` (PowerShell: `Get-ChildItem`) shows `apply.log`, `destroy.log`, `init.log`, `main.tf`, the state files and an empty `out`. Open `destroy.log` and find the lines "Destroying..." and "Destruction complete".

What the counter cannot catch: a resource the state has **forgotten** is not in the count, so a destroy can report success while the real thing keeps running. With local files that is harmless; with servers it is a bill. Lesson I2 covers how that happens and how to recover.

**Undo.** The script already destroyed everything it built, and it counted to prove it. Delete its cycle folders:

```bash
cd "$HOME" && rm -rf "$HOME/cah-tofu-lab/bunch"
```

PowerShell (est.): `Set-Location $HOME; Remove-Item -Recurse -Force "$HOME\cah-tofu-lab\bunch"`

The rest of the lab is removed at the end of the next section. If you want to stop here, run the last command of that section now.

## Optional: your own account

This lesson stops short of a real cloud on purpose, because the first bill is the one you remember. When you are ready, lesson I4, [Build and destroy: a stack per service](Build-and-Destroy-Stack-Per-Service.md), repeats Exercise 7 against your own account with small, costed resources, one stack per service, and the cost and teardown steps come first on that page. The Spacelift side is lesson I3, [Spacelift from zero](Spacelift-From-Zero.md). Neither is needed to finish this page, and nothing here uses a Spacelift account.

> I2, I3 and I4 are written alongside this page. Until they are merged, the three links in this section may not resolve yet.

## Build it, break it, detect it, defend it

The same loop the [labs](Labs-Break-It-on-Purpose.md) use, applied to infrastructure code. Use the `first` folder from Exercise 2.

- **Build.** The configuration and the ten-cycle script: a reviewable description, an empty-state proof, and a destroy you previewed. Rebuild the `first` folder so there is something to protect:

  ```bash
  cd "$HOME/cah-tofu-lab/first" && tofu apply -auto-approve -no-color | grep 'Apply complete'
  ```

  PowerShell (est.): `Set-Location "$HOME\cah-tofu-lab\first"; tofu apply -auto-approve -no-color | Select-String 'Apply complete'`
- **Break.** Make a mistake that a person could make in a pull request. A typo in an argument name:

  ```bash
  cd "$HOME/cah-tofu-lab/first"
  cp main.tf main.bak
  sed -i 's/content  = /contents = /' main.tf
  ```

  PowerShell (est.): `Copy-Item main.tf main.bak; (Get-Content main.tf) -replace 'content  = ', 'contents = ' | Set-Content main.tf -Encoding utf8NoBOM`

  Then a second, quieter break: a change that looks small and is not (Exercise 3, case (b): `-var greeting=bye` replaces files).
- **Detect.** Run the checks. `validate` catches the typo before anything is read from the world:

  ```bash
  tofu validate -no-color
  cp main.bak main.tf
  tofu plan -no-color -detailed-exitcode > /dev/null; echo "no change: exit $?"
  tofu plan -no-color -detailed-exitcode -var label=z > /dev/null; echo "one change: exit $?"
  ```

  PowerShell (est.): `tofu validate -no-color; Copy-Item main.bak main.tf; tofu plan -no-color -detailed-exitcode | Out-Null; $LASTEXITCODE; tofu plan -no-color -detailed-exitcode -var label=z | Out-Null; $LASTEXITCODE`

  The first command ends `Error: Unsupported argument` and `An argument named "contents" is not expected here. Did you mean "content"?` (observed 2026-10-22). After the file is restored, `-detailed-exitcode` turns "would anything change?" into a number a script or CI job can test: `0` for no changes, `2` for changes, and `1` for an error (observed on 1.12.6, 2026-10-22). The quiet break, `-var greeting=bye`, is caught by reading the plan: `-/+` and `# forces replacement`, as in Exercise 3.
- **Evade.** The way a careless run hides a change is `-target`. Plan only the tag while two files are also pending:

  ```bash
  tofu plan -no-color -var release=2 -var greeting=bye -target=terraform_data.tag | grep -E '^(Plan:|  # |Warning)'
  ```

  You see `Plan: 1 to add, 0 to change, 1 to destroy.`, one replacement, and a `Warning: Resource targeting is in effect`. The two `local_file` replacements the full plan would show are simply not there. A plan that looks small because it was narrowed is not a clean bill of health. The [plan command page](https://opentofu.org/docs/cli/commands/plan/) (read 2026-10-22) says to use `-target` "in exceptional circumstances only, such as recovering from mistakes or working around OpenTofu limitations".
- **Defend.** Defenses are layers, and the first two are yours to do now:

  1. Run `fmt`, `validate` and a plan on every change, and read the addresses and the replacement markers, not only the totals.
  2. Keep `-target` for recovery, not for making a plan look smaller, and treat a plan that carries the targeting warning as incomplete.
  3. Put the same checks in CI on every pull request so a person cannot skip them. This repository runs `tofu test` with mock providers (no credentials) and the plan itself runs in Spacelift only after merge, where a human confirms.
  4. Put a cost gate in front of the merge so a plan that adds a costly resource cannot slip through. This repository's gate is `scripts/cost_check.py`, described in [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).

**Clean up the break and the whole lab.** Restore the file, destroy, then delete the scratch folder:

```bash
cd "$HOME/cah-tofu-lab/first" && cp main.bak main.tf
tofu destroy -auto-approve -no-color | tail -1
cd "$HOME" && rm -rf "$HOME/cah-tofu-lab"
ls "$HOME/cah-tofu-lab" 2>&1
```

PowerShell (est.):

```powershell
Set-Location "$HOME\cah-tofu-lab\first"; Copy-Item main.bak main.tf
tofu destroy -auto-approve -no-color | Select-Object -Last 1
Set-Location $HOME; Remove-Item -Recurse -Force "$HOME\cah-tofu-lab"
Test-Path "$HOME\cah-tofu-lab"
```

The last line should report that the folder does not exist (`False` in PowerShell).

### Flip the board

Now read the same pages as the attacker, and as a defender who has to catch one.

- **Where would an attacker look?** In the state file (it holds every attribute, secrets included) and in whatever stores it; in the CI job that runs plan and apply (it holds the cloud credentials); and in a pull request that adds a module from a remote source (code that runs with those credentials). The defender's questions are the mirror: who can read the state, which job holds which credential, and does anything run code from a place nobody reviewed? This repository answers the last one in the cost gate (it refuses remote module sources it cannot read) and the first two by giving a pull-request plan no credentials at all ([Spacelift](Spacelift.md)).
- **What would an attacker like a reviewer to miss?** A small-looking plan. A targeted plan, a `-/+` hidden in the summary counts, a destroy of the one resource that holds data. If you review infrastructure changes, make "list every address and its symbol" your first read.
- **What does a destroy habit buy a defender?** Fast, complete removal: the lab you can tear down in seconds is also the lab an incident responder can rebuild clean. The same habit helps a defender who builds a disposable test lab, attacks it, and throws it away.

## How this repository uses it

Read-only; nothing here asks you to run `tofu` against this repository's stacks. The stacks describe the maintainer's real environment, and applying them is a Spacelift run a human confirms, not something a lesson does.

- **Layout.** `stacks/` holds one folder per layer (`00-foundation`, `10-access`, `20-telemetry`, and an `aws` folder for a second provider); `modules/` holds reusable pieces. Each stack has the same small set of files you made in Exercise 2: `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` (the `required_providers` block), a `terraform.tfvars.example` with the settings a learner fills in, a `tests/` folder and a `cost.json`. Your real `.tfvars` files are git-ignored. Look with `ls stacks/00-foundation` from a checkout.
- **Tests.** Every module and stack has `tests/*.tftest.hcl` files using mock providers, exactly as in Exercise 6. CI runs them on each pull request through the shared reusable workflow described in [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).
- **Golden-address tests.** `docs/golden-addresses/` holds one JSON file per stack listing every resource address the stack has today and the settings that force a replacement. `scripts/plan_noop_check.py` reads a saved plan and fails if a change that should be a no-op touches anything: an update counts as a failure, as do a create, a delete, a replacement and a moved address. It is the Exercise 3 skill (spot the `~` and `-/+` in a plan) turned into a rule. CI cannot run it, because a real plan needs the live state; CI tests the checker against fake plans, and the real gate is the plan a human reads in Spacelift.
- **The cost gate.** `scripts/cost_check.py` reads each stack's `cost.json`, prices what is declared from the repository's price table, and fails the build when a total exceeds the phase ceiling in [docs/cost.md](../cost.md). That is the "defend" layer 4 above, applied to money.
- **No state in the repo.** `.gitignore` excludes `*.tfstate`, `*.tfstate.*`, `*.tfvars` and saved plans. The state lives in Spacelift.

## Checkpoint

You are done when you can say, without looking:

- What `init`, `plan`, `apply` and `destroy` each do, and which of them change anything real.
- What `+`, `-`, `~` and `-/+` mean, and why "2 to add, 2 to destroy" can be two replacements.
- Why the state file is kept out of git and why `sensitive = true` does not remove a value from it.
- Why `for_each` is safer than `count` when a list changes.
- What a mock provider is for, and why a passing `tofu test` created no files.
- How you proved, ten times, that a destroy left nothing behind.
- How OpenTofu and Terraform are related, without taking a side you cannot back with the FAQ.

## Claims register

What on this page came from outside, read on **2026-10-22** unless noted. Everything marked "observed" was run by me on OpenTofu 1.12.6.

| Claim | Source | Status |
|---|---|---|
| Install commands for Homebrew (`brew update`, `brew install opentofu`), winget (`winget install --exact --id=OpenTofu.Tofu`), Scoop (`scoop bucket add main`, `scoop install main/opentofu`); the standalone installer must be inspected before running; Debian repository steps live on the page | [Install overview](https://opentofu.org/docs/intro/install/), [Homebrew](https://opentofu.org/docs/intro/install/homebrew/), [Windows](https://opentofu.org/docs/intro/install/windows/), [Standalone](https://opentofu.org/docs/intro/install/standalone/), [Debian](https://opentofu.org/docs/intro/install/deb/) | Read; not run on macOS or Windows |
| The site banner announced OpenTofu 1.13.0; docs offered v1.13.x and v1.12.x | Banner on opentofu.org pages | Read; this lesson run on 1.12.6, the repository CI pin |
| Registry has `hashicorp/local` 2.9.1, `hashicorp/random` 3.9.1, `hashicorp/null` 3.3.2 as newest | `https://registry.opentofu.org/v1/providers/hashicorp/<name>/versions` | Read |
| `terraform_data` is built in | Output of `tofu init` ("terraform.io/builtin/terraform is built in") | Observed |
| State holds resource ids and all attributes; may contain passwords; treat as sensitive | [Sensitive data in state](https://opentofu.org/docs/language/state/sensitive-data/) | Read |
| Hand-editing state is discouraged; `tofu state` commands exist | [State](https://opentofu.org/docs/language/state/) | Read |
| `-target` is for exceptional circumstances; `-destroy` plans a destroy; `-out` saves a plan | [plan command](https://opentofu.org/docs/cli/commands/plan/) | Read |
| `tofu test` file extensions, `tests` folder, mock providers | [test command](https://opentofu.org/docs/cli/commands/test/) | Read; mock behavior observed |
| OpenTofu is a Terraform fork started in response to the BUSL; compatibility statements; separate registry; state compatibility to 1.5.x | [OpenTofu FAQ](https://opentofu.org/faq/) | Read; quoted as written, not endorsed |
| `plan -detailed-exitcode` exits 0 with no changes, 2 with changes | Ran it | Observed (docs page not read for this flag) |
| `+/-` create-before-destroy marker | General knowledge | **est.**, not exercised |
| PowerShell commands, PowerShell 5.1 byte-order-mark behavior | Written from the Bash steps | **est.**, not run |

## Where to next

[OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) shows how this project lays out stacks and why. The rest of the track:

- I2, [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md): what happens when the state and the world disagree, and how to recover.
- I3, [Spacelift from zero](Spacelift-From-Zero.md): the hosted place where plan and apply run.
- I4, [Build and destroy: a stack per service](Build-and-Destroy-Stack-Per-Service.md): the build-and-destroy habit, against your own account.

For the line-by-line lookup of this repository's variables and resources, see the [Terraform reference](Terraform-Reference.md).
