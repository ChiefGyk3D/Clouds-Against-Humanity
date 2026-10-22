# Build and destroy a bunch: one stack per service

Side page to [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) (core step 15), and the fourth lesson of a four-lesson infrastructure-as-code track: [OpenTofu from zero](OpenTofu-From-Zero.md), then [plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md), then [Spacelift from zero](Spacelift-From-Zero.md), then this page. It teaches how to split an environment into one stack per service, how to wire the stacks together, and how to build and destroy the whole set without leaving a bill behind.

Next: [Teardown checklist](Teardown-Checklist.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free lab was run on Linux; the cloud lab was only validated, never applied; PowerShell was not run.** On **2026-10-22** the author ran the whole free lab on Linux with OpenTofu 1.12.6 (the version CI pins) and the `hashicorp/local` provider 2.9.1: five full build-and-destroy cycles, each ending with a checker that found every state empty, plus the wrong-order and forgotten-resource exercises below; the output shown is from that run, trimmed. The cloud lab's five stacks were checked with `tofu init` and `tofu validate` against the `digitalocean/digitalocean` provider 2.106.0 (a schema check: no token, no API call, nothing created), so their argument names are right, but **nothing in them was ever applied**. Expect to fix something. The PowerShell scripts were written from Microsoft's and OpenTofu's documentation and **were not run** (there was no Windows machine): treat every PowerShell line as **est.** Vendor facts come from the pages listed in the [claims register](#claims-register), read on **2026-10-22**. Nothing here was run against this project's own stacks, which are locked.

> **Prerequisites.** The three earlier lessons of the track, which are planned lessons being written at the same time as this one: [OpenTofu from zero](OpenTofu-From-Zero.md) (init, plan, apply, destroy), [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) and [Spacelift from zero](Spacelift-From-Zero.md). Those links work once the lessons are merged; until then, [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) and [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) cover the minimum (provider, resource, plan, apply, state, stack). Also useful: [The terminal and your first script](Terminal-and-Your-First-Script.md) and [Teardown checklist](Teardown-Checklist.md). The free lab needs OpenTofu 1.8 or newer, a terminal and a few megabytes of disk; no account, no money. About 60 minutes of reading and 90 minutes for the free lab (est.); the optional cloud lab adds about an hour (est.) and uses your own account.

## What you will be able to do

- Say why a bigger environment is split into one stack per service, and name the costs of splitting just as plainly as the benefits.
- Lay out a repository so each stack has its own folder, its own state and its own cost line.
- Pass a value from one stack to another (an output read through remote state, a Spacelift stack dependency, or a lookup by tag), and say why a secret is not one of those values.
- Work out a build order from the dependencies and destroy in exactly the reverse order, and read the error you get when you do not.
- Tag every resource so that a forgotten one can be found, and say what a tag audit cannot find.
- Build and destroy five stacks in a loop, and prove with a checker, not with a feeling, that nothing remains.
- Compute a hard cost budget for a cloud run from the repository's price file before you create anything.
- Describe how this project does it (numbered stack directories, a cost gate, golden-address tests, a destroy guard) without running anything against locked stacks.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Stack, module, layered stacks | [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) gives five reasons for layers and says outputs flow from 00 to 10 through Spacelift dependencies. | It describes this project's three stacks. It does not teach the general rule, the costs of splitting, or what to do with fifteen stacks. |
| Destroy order and leftovers | [Teardown checklist](Teardown-Checklist.md) gives the order and the proof commands for this project. | It is a checklist for one environment. The reasons, the hazards and a practice loop are here. |
| Cost per stack | [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) explain the gate. | Nothing teaches a learner to compute a budget for their own run. |
| Running stacks | [Spacelift](Spacelift.md) shows the run lifecycle for this project. | It does not show building and destroying a whole set again and again. |

## Why one stack per service

First the words. A **stack** is a folder of OpenTofu code that you plan and apply as one unit, with **its own state** (the file or record of what that code created). A **service** here means anything one person or team can own, change and switch off on its own: the network, a firewall baseline, one web application, a logging server. One stack per service means one folder, one state, one plan, one apply and one destroy for each.

| Reason | What it buys | A small example |
|---|---|---|
| **Blast radius** | A mistake can only touch what is in that stack's state. | A bad edit to the web app's stack cannot plan a change to the network, because the network is not in that state. |
| **State isolation** | One state file, one lock, one thing to corrupt or lose. State often holds sensitive values, so fewer secrets per file is a smaller loss. | Two people can apply two services at the same time; only two applies to the same stack have to wait for each other. |
| **Trust boundary** | Each stack runs with its own credentials and identity, so what one stack's credentials can reach is limited to what that stack needs. The maintainer's ruling for this project is that stack boundaries are trust boundaries: for example, the lxmd service and Reticulum get separate stacks and separate identities, so a mistake or a compromise in one does not carry into the other. | The token for the logging stack cannot touch the network. |
| **Ownership** | A folder can have an owner, a reviewer and a set of permissions. | The team that runs the web app can change the web app, and is not able to change the network by accident. |
| **Independent destroy** | You can switch one service off, or rebuild it, without touching the others. | Rebuild a test server nightly while the network stays up. |
| **Cost gating per stack** | Each stack declares its own spend, so a price change shows up in the right place. | This project keeps one `cost.json` per stack; see [the cost gate](#cost-counters-a-number-per-stack-and-one-for-the-whole). |
| **Faster, readable plans** | A short plan gets read; a 300-line plan gets skimmed. Fewer resources also means a quicker refresh. | The human who confirms an apply can actually read it. |

### What splitting costs

Splitting is a trade, not a free win. The costs are real, and they are why you should not split everything.

| Cost | What it looks like | What softens it |
|---|---|---|
| **Cross-stack wiring** | A value one stack creates (a network ID) is needed by another, so you must publish it and read it. | Few, boring outputs (IDs and names), pinned by a test. See [Passing values between stacks](#passing-values-between-stacks). |
| **Ordering** | Stacks must be built in dependency order and destroyed in the reverse. Get it wrong and a run fails, sometimes half way. | A written order, a script, or the platform's dependency feature. See [Build order and destroy order](#build-order-and-reverse-destroy-order). |
| **More runs and more approvals** | Ten stacks are ten plans to read. A change that touches three of them is three pull requests or three runs. | Keep the number of stacks to what ownership and change rate justify; use a factory (below) to create stacks the same way each time. |
| **Duplicated setup** | Each stack repeats the provider block, the backend and the variables. | Put the reusable parts in modules; keep the per-stack code to wiring. |
| **Harder refactors** | Moving a resource from one stack's state to another's is a careful, manual step. | Decide boundaries early; move with `tofu state` commands or `moved` and `import` blocks, never by hand-editing state. |
| **Partial failure** | With one stack, a run either worked or it did not. With five, you can end up with three built and two not. | Make every stack safe to run again, and keep a "what is built right now" check (the lab below has one). |

Rule of thumb: split along **ownership**, **change rate** and **blast radius**. Things that always change together, and are owned by the same person, can stay in one stack. A single-person throwaway lab in one folder is fine. An environment where the network changes yearly and an application changes daily is not.

## What the layout looks like

The free lab you will build has this shape. Each box is a folder with its own state; an arrow means "reads an output of".

```text
  00-tag  <---------- 10-firewall <------- 20-network <--+---- 30-server-a
    ^                      ^                    ^        |
    |                      |                    |        +---- 40-server-b
    +----------------------+--------------------+  (every stack also reads 00-tag)
```

Build order: `00-tag`, `10-firewall`, `20-network`, `30-server-a`, `40-server-b`. Destroy order: exactly backwards. In the cloud lab the same five boxes are a tag, a firewall that is attached by that tag, a private network, and two small servers.

### Layout conventions worth copying

- **One folder per stack, one state per folder.** `stacks/<NN>-<name>/` with its own `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` and tests. This project's stacks are `00-foundation`, `10-access` and `20-telemetry`.
- **Numbers with gaps.** `00`, `10`, `20` leave room to slot a layer in later without renaming. The number is the build order; the name says what it is.
- **Names carry meaning.** This project names resources `<layer>-<region>-<role>`. The lab's names carry a prefix (`cah-lab-`) so a script can find everything the lab made.
- **A committed example, an ignored real file.** `terraform.tfvars.example` is committed and `*.tfvars` is ignored, so values with an account in them never reach Git. (The lab's `terraform.tfvars` files live in your scratch folder and hold no secrets.) See [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md).
- **Validation at the edge.** Variables reject bad input before a plan touches an API. The lab's consumer stack refuses to plan unless `00-tag` is in its `needs` list.
- **Look up, do not re-create, what exists.** A data source finds something that is already there.
- **Only a short, pinned list of outputs.** This project has a test that pins the exact list, so adding an output (and perhaps leaking something through it) has to be done on purpose.
- **Provider lock files are committed**, so every run uses the same provider build.
- **A cost manifest per stack** (`cost.json` here), read by the cost gate.
- **Tests that need no account.** Each stack has `tests/*.tftest.hcl` files with mocked providers, so CI proves the shape for free.

## Passing values between stacks

Once the network lives in one stack and the server in another, the server needs the network's ID. There are four ways, and each has a catch.

| Way | How it works | Catch |
|---|---|---|
| **Remote state data source** | The consumer reads the producer's **root module outputs** with `data "terraform_remote_state"`. The free lab does this. | OpenTofu's documentation warns that the reader needs access to the **entire** state snapshot, which often includes sensitive information, and that the data source does not respect the sensitivity of the source state. |
| **Spacelift stack dependency with an output reference** | A downstream stack lists an upstream stack's output and maps it to an environment variable, `TF_VAR_<name>` for OpenTofu. This project does this, so stack 10 never has read access to stack 00's whole state, only the values it consumes. | It only respects **tracked runs**, uses the outputs of a **successful** run that included an apply, and (per Spacelift's documentation) does not manage creating or deleting stacks. See [Spacelift](Spacelift.md) and the third lesson of the track. |
| **Lookup by tag or name** | The consumer uses a provider data source to find the resource that exists, by its tag or name. | The thing must already exist and the name must be stable. There is no recorded link, so destroy order is not enforced by anything. |
| **Publish somewhere on purpose** | One stack writes the shared value to a named place (a parameter store, a DNS record); others read it there. OpenTofu's documentation recommends this when you can, because it lets you set different access for shared data and for state. | One more moving part to run. |

**Never pass a secret this way.** An output lands in the state, state sits somewhere (a plain-text JSON file when it is local, per OpenTofu's documentation), and a stack dependency copies it into another stack's environment and logs. Pass **identifiers**: IDs, names, CIDR ranges, tag names. Pass secrets by giving each stack its own read of the secret store (this project uses [Doppler](Doppler-and-Secrets.md) with a per-stack list of the names a stack may load), and mark sensitive outputs `sensitive = true` knowing that this hides them in the terminal, not in the state file.

A quick test for a candidate output: "if this value appeared in a bug report, would I mind?" If you would mind, it is not an output.

## Build order and reverse destroy order

Every arrow in the picture above is a **dependency**: the consumer cannot plan until the producer's outputs exist. A build order is any ordering where each stack comes after everything it reads. (Computer science calls that a topological order; for a handful of stacks you can just read it off the picture.) Two rules follow.

1. **Build** with the dependencies first.
2. **Destroy** in exactly the reverse: the consumers first, the producers last.

Why the reverse? Because a consumer holds things that sit inside the producer's things. In the cloud, a network cannot be deleted while a server is still attached to it, and the provider refuses with an error (the exact wording varies by provider; est.). In the free lab the failure is different but just as real: the consumer reads the producer's outputs on **every** plan, including the plan that destroys it. If the producer is gone, the consumer can no longer even plan its own destruction, and you are stuck with resources nothing can remove. You will make this happen on purpose in [Exercise 5](#exercise-5-destroy-in-the-wrong-order-on-purpose).

## Tag everything, so teardown can be proven

A destroy that reports success is a claim. The evidence is a list that comes back empty. To make that list possible, every resource must carry something a script can search for:

- A **tag** or **label** (a short text attached to a resource) naming the environment and the stack, and a **name prefix** as a second handle. Use both, because not every resource type takes tags. DigitalOcean's documentation says tags apply to droplets "and other DigitalOcean resources", but I did not check which types, so confirm each type you use (est.).
- A tag is applied at creation, in the same code that creates the resource. A tag added later by hand is a tag somebody has to remember.
- Put the tag in the **first** stack, as this project does (a baseline tag in `00-foundation`) and as the lab does (`00-tag`). Later stacks read it instead of inventing their own spelling.
- A tag is not a proof by itself. It lets a script ask "show me everything with this tag", and the answer proves something only if nothing is untagged. [Exercise 6](#exercise-6-a-forgotten-resource-and-an-untagged-one) shows the gap.

## Cost counters: a number per stack, and one for the whole

Cost has to be visible per stack, or nobody sees which stack is the expensive one.

- **A manifest per stack.** This project's `cost.json` lists the machines a stack plans, and `scripts/cost_check.py` prices each from `docs/cost-prices.json`, adds them up per cloud and fails if the sum goes over the approved figure, if a stack directory has no manifest, if an unpriced billable resource type appears, or if a size is missing from the price table. The gate reads source code; it does not see what is actually running. See [Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).
- **A budget before the run.** For your own runs, write the arithmetic down first. The cloud lab below ships a small script that reads only the price file.
- **A time counter.** Hourly billing means cost is size times time. The cheapest habit is to put a calendar reminder at the time you plan to have destroyed everything.
- **A spend alert.** DigitalOcean's documentation says a spend alert budget "is not a spending cap and does not limit how much you can use". An alert tells you after the money is spent; the destroy is what stops it.

## How this project does it

This section is a tour. Nothing here is run: the project's stacks are locked, and every Spacelift change needs the maintainer's confirmation.

- **Stage directories.** `stacks/00-foundation` (project, baseline tag, VPC, baseline firewall), `stacks/10-access` (the connector droplets and the Twingate objects) and `stacks/20-telemetry` (the logging and metrics paths), plus `stacks/aws/` for the AWS twin. The numbers match the build stages in the [Roadmap](Roadmap.md); the roadmap names `50-edge` for a planned public edge, so the numbers `30` and `40` are free for the workload and dashboard stages that have no directory yet. Only 00 and 10 have ever been applied for real.
- **One Spacelift stack per directory,** one explicit stanza per stack in `.spacelift/config.yml` listing only the secrets that stack may load, and tests that fail closed on that file. See [Spacelift](Spacelift.md).
- **Outputs flow by stack dependency,** not remote state; see above.
- **The cost gate** reads one `cost.json` per stack and refuses a stack directory without one.
- **Golden-address tests.** `docs/golden-addresses/00-foundation.json`, `10-access.json` and `20-telemetry.json` list every resource address each stack plans, with the attributes that would force a replacement. `scripts/plan_noop_check.py` takes a saved plan and fails if anything in it is not a no-op, or an address appears that is not in the golden file, or one is missing. That is the check for "I edited a live stack's code, and the default plan must change nothing". The checker is proven in CI against mocked plan JSON; the real gate is a human reading the real plan in Spacelift.
- **A destroy guard.** The plan policy `.spacelift/policies/plan.rego` denies any plan that deletes or replaces a protected resource (a VPC, project, firewall, Twingate remote network, or anything tagged `protected`), so a full teardown needs the exact addresses added to an allowlist in a reviewed pull request and removed again afterwards. [Teardown checklist](Teardown-Checklist.md) walks through it.
- **Reverse destroy order, written down.** `20-telemetry`, then `10-access`, then `00-foundation`, then the Spacelift stacks themselves.

## If you are terraforming an entire infrastructure

Everything above scales up, with a few more decisions to make early because they are painful to change later.

- **Environments.** Keep development, staging and production apart with **separate state and separate accounts or projects**, not only a variable that says which. A shared account means a shared blast radius and a shared bill. The same code, called with different inputs, builds each environment.
- **Naming.** Pick one scheme and use it everywhere, such as `<org>-<env>-<region>-<service>`. Short, lowercase, no personal names, no account numbers. A script that tears down or audits an environment depends on being able to match names.
- **Accounts and projects.** Use the provider's boundary (a project, a team, an account, an organization) as an access boundary, and put resources in the right one at creation. This project puts everything in one DigitalOcean project created by stack 00.
- **A shared network stack.** Networks, shared DNS, logging and identity change rarely and many things depend on them. Give them their own stacks, early in the order, owned by the people who can answer for them, and publish only identifiers.
- **Per-service stacks on top.** Each service reads the shared outputs it needs and nothing else. Add services without touching the layers below.
- **A stack factory.** When the stack count grows, creating each stack by hand in a console does not scale and invites mistakes. This project's design is one explicit stanza per stack, created from code by a factory repository, with tests that fail closed. The status of that work is in `docs/superpowers/specs/2026-10-22-stack-factory-status.md`; it is a gap analysis, not a finished system.
- **Who may destroy what.** Separate three powers and give them to different roles: **plan** (read-only, anyone on the team), **apply** (a reviewer or an approval step), **destroy** (fewest people, with a second pair of eyes for anything shared or production). Turn on the platform's **deletion protection** where it exists, mark long-lived resources so a policy can refuse to delete them, and keep destroy-capable credentials out of the places that run on every pull request.
- **Tag policy and cost reports.** Require tags at creation where the platform can enforce it (some cloud providers have organization-wide tag policies; check yours, est.), and read a cost report grouped by tag or by project at least monthly. Both are in the [defend step](#build-break-detect-evade-defend) below.
- **Moving from one big stack to many.** Do it in small steps, one service at a time, with a no-op plan as the acceptance test. This project's golden-address file is exactly that test.

## Lessons-learned: what makes a destroy fail or leave a bill

1. **A dependency blocks the destroy.** A network with a server still attached, a firewall still referenced, a stack whose producer is already gone. Fix: destroy in reverse build order, and read the plan.
2. **A protected resource refuses.** Deletion protection, `prevent_destroy` in the code, a plan policy, or the provider itself. This project's policy denies deleting a VPC, project or firewall until the address is on a reviewed allowlist. Fix: remove the protection on purpose, in a reviewed change, then put it back.
3. **A default resource cannot be deleted.** DigitalOcean refuses to delete a VPC that is a region's default (`403 Can not delete default VPCs`; see [Lessons learned 9](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true)). Fix: make another network the default, or forget the resource from state and leave it, and write down that you did.
4. **Volumes, snapshots, reserved addresses and backups outlive the machine.** DigitalOcean's documentation says destroying a droplet does not destroy its automated backups (they expire after four weeks) and that associated snapshots and volumes are only destroyed if you ask. Fix: list them after every destroy.
5. **State is left behind.** A destroyed stack leaves a state file that is empty but present. Anything that reads that state, as the lab's consumers do, now sees outputs that are not there. Fix: destroy consumers first, and delete the state storage only after proving the stack is empty.
6. **Things made by hand are in no state.** No destroy touches them and no cost gate saw them. Fix: a tag audit, an inventory of the whole account, and the discipline of not creating things in a console.
7. **A powered-off machine still bills.** DigitalOcean's documentation says bundled-plan droplets that are powered off are still billed, because the compute resources stay reserved; billing ends when you destroy. Fix: destroy, do not stop.
8. **Billing outlives the resource on the page.** Usage data lags, the invoice comes at month end, and a minimum charge applies even to a droplet destroyed within a minute. Fix: look again the next day.
9. **The credential was revoked too early.** Revoking the token before the destroy leaves a run with nothing to authenticate with. Fix: destroy, prove zero, then revoke (the order in [Teardown checklist](Teardown-Checklist.md#4-revoke-and-rotate)).
10. **Destroying in the wrong account.** The same code run with the wrong token tears down the wrong thing. Fix: before a destroy, check which account the token belongs to, and use a separate account or project for experiments.

## Free path: five stacks in a scratch folder

### Cost and teardown (read first)

- **Cost.** Nothing. The lab uses the `local` provider, which writes small text files in a folder you choose. No account, no network except downloading the provider once from the OpenTofu registry.
- **Teardown.** If you have never built anything, there is nothing to tear down. Once you have built, this is the whole teardown, and you can run it any time:

```bash
cd ~/iac4-lab && ./lab.sh destroy && ./lab.sh check
cd ~ && rm -rf ~/iac4-lab ~/.cache/iac4-plugins
```

```powershell
Set-Location $HOME\iac4-lab; .\lab.ps1 destroy; .\lab.ps1 check
Set-Location $HOME; Remove-Item -Recurse -Force $HOME\iac4-lab, $HOME\.cache\iac4-plugins
```

- **Safety.** The lab writes only below the folder you give it. Nothing is exposed to a network. Use a scratch folder, never a folder with data you care about.

### What the lab is

Five stacks, one folder each, built in order and destroyed in reverse. Each stack manages one thing: a text file. The files stand in for cloud resources: a tag, a firewall, a network and two servers. Every file starts with `tag=cah-lab`, and every stack except the first reads its upstream stacks' outputs and writes what it saw into its file, so you can see the values travel. The state is local, one `terraform.tfstate` per stack folder. `lab.sh` builds all, destroys all, and proves emptiness two ways: every state is empty, **and** a second, independent look (`proof.sh`) finds no files. The cloud lab swaps in a different second look and keeps the rest.

### Step 0: write the lab

Save this as `setup.sh` and run `bash setup.sh`. It writes everything into `~/iac4-lab` (give a folder as an argument to use another) and runs no OpenTofu.

```bash
#!/usr/bin/env bash
# setup.sh: write the five-stack practice lab into a scratch folder. Usage: bash setup.sh [FOLDER]
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
LAB="${1:-$HOME/iac4-lab}"
mkdir -p "$LAB/stacks" "$LAB/world"
LAB="$(cd "$LAB" && pwd)"

# Stack 00 makes the tag every other stack will read.
mkdir -p "$LAB/stacks/00-tag"
cat > "$LAB/stacks/00-tag/main.tf" <<'EOF'
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "name" { type = string }
variable "world" { type = string }

locals {
  tag = "cah-lab"
}

resource "local_file" "this" {
  filename = "${var.world}/${var.name}.txt"
  content  = "tag=${local.tag}\nstack=${var.name}\n"
}

output "tag" {
  value = local.tag
}
EOF

# Stacks 10 to 40 share one shape: read the stacks they need, write one file.
mkdir -p "$LAB/stacks/_consumer"
cat > "$LAB/stacks/_consumer/main.tf" <<'EOF'
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "name" { type = string }
variable "world" { type = string }
variable "root" { type = string }

variable "needs" {
  type = list(string)
  validation {
    condition     = contains(var.needs, "00-tag")
    error_message = "Every stack needs 00-tag: it owns the tag."
  }
}

# Read-only look at the OUTPUTS of the stacks this one depends on.
data "terraform_remote_state" "up" {
  for_each = toset(var.needs)
  backend  = "local"
  config = {
    path = "${var.root}/stacks/${each.key}/terraform.tfstate"
  }
}

locals {
  tag = data.terraform_remote_state.up["00-tag"].outputs.tag
  seen = [for k in sort(var.needs) : "${k}=${try(data.terraform_remote_state.up[k].outputs.id, data.terraform_remote_state.up[k].outputs.tag)}"]
}

resource "local_file" "this" {
  filename = "${var.world}/${var.name}.txt"
  content  = "tag=${local.tag}\nstack=${var.name}\n${join("\n", local.seen)}\n"
}

output "id" {
  value = local_file.this.id
}
EOF

mk() { # mk NAME NEEDS...   (NEEDS are other stack names)
  local name="$1"; shift
  mkdir -p "$LAB/stacks/$name"
  [ "$name" = "00-tag" ] || cp "$LAB/stacks/_consumer/main.tf" "$LAB/stacks/$name/main.tf"
  {
    printf 'name  = "%s"\nworld = "%s"\n' "$name" "$LAB/world"
    if [ "$name" != "00-tag" ]; then
      printf 'root  = "%s"\nneeds = [' "$LAB"
      local first=1 n
      for n in "$@"; do [ $first = 1 ] || printf ', '; printf '"%s"' "$n"; first=0; done
      printf ']\n'
    fi
  } > "$LAB/stacks/$name/terraform.tfvars"
}
mk 00-tag
mk 10-firewall 00-tag
mk 20-network 00-tag 10-firewall
mk 30-server-a 00-tag 10-firewall 20-network
mk 40-server-b 00-tag 10-firewall 20-network
rm -r "$LAB/stacks/_consumer"

printf '%s\n' 00-tag 10-firewall 20-network 30-server-a 40-server-b > "$LAB/order.txt"

# proof.sh: the second, independent look. Here: is anything left in the world folder?
cat > "$LAB/proof.sh" <<'EOF'
#!/usr/bin/env bash
LAB="$(cd "$(dirname "$0")" && pwd)"
files=$(find "$LAB/world" -type f | wc -l)
printf '%-14s %s file(s) left\n' "world/" "$files"
[ "$files" = 0 ]
EOF

# audit.sh: list everything left, tagged or not.
cat > "$LAB/audit.sh" <<'EOF'
#!/usr/bin/env bash
LAB="$(cd "$(dirname "$0")" && pwd)"
left=0
while IFS= read -r f; do
  left=1
  if grep -q '^tag=cah-lab$' "$f"; then echo "TAGGED    $(basename "$f")"; else echo "UNTAGGED  $(basename "$f")"; fi
done < <(find "$LAB/world" -type f | sort)
[ $left = 0 ] && echo "audit: world is empty"
exit $left
EOF

cat > "$LAB/lab.sh" <<'EOF'
#!/usr/bin/env bash
# lab.sh: build all stacks in order.txt, destroy them in reverse, prove nothing remains.
# SPDX-License-Identifier: Apache-2.0
# Usage: ./lab.sh build | destroy | check | cycle N
set -uo pipefail
LAB="$(cd "$(dirname "$0")" && pwd)"
mapfile -t ORDER < "$LAB/order.txt"
export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-$HOME/.cache/iac4-plugins}" TF_IN_AUTOMATION=1
mkdir -p "$TF_PLUGIN_CACHE_DIR"

tf() { local s="$1"; shift; tofu -chdir="$LAB/stacks/$s" "$@" -no-color; }

build() {
  local s out rc
  for s in "${ORDER[@]}"; do
    echo "== build $s"
    tf "$s" init -input=false >/dev/null || return 1
    out=$(tf "$s" apply -auto-approve -input=false 2>&1); rc=$?
    echo "$out" | grep -E "^(Apply complete|Error)" || true
    [ $rc = 0 ] || { echo "build failed at $s"; return 1; }
  done
}

destroy() {
  local i r out rc=0
  for ((i=${#ORDER[@]}-1; i>=0; i--)); do
    echo "== destroy ${ORDER[i]}"
    tf "${ORDER[i]}" init -input=false >/dev/null || rc=1
    out=$(tf "${ORDER[i]}" destroy -auto-approve -input=false 2>&1); r=$?
    echo "$out" | grep -E "^(Destroy complete|Error)" || true
    [ $r = 0 ] || { echo "destroy failed at ${ORDER[i]}"; rc=1; }
  done
  return $rc
}

# statecount STACK [managed]: items in one stack's state. No state file means nothing was ever applied: 0.
# A state file that exists but cannot be read is an error (return 1), never a zero.
statecount() {
  local s="$1" out
  [ -f "$LAB/stacks/$s/terraform.tfstate" ] || { echo 0; return 0; }
  out=$(tf "$s" state list 2>&1) || return 1
  if [ "${2:-}" = managed ]; then out=$(printf '%s\n' "$out" | grep -v '^data\.'); fi
  printf '%s\n' "$out" | grep -c . || true
}

count() { # managed resources recorded in all states (data sources do not count)
  local s total=0 n
  for s in "${ORDER[@]}"; do
    n=$(statecount "$s" managed) || { echo "state of $s is unreadable" >&2; return 1; }
    total=$((total + n))
  done
  echo "$total"
}

check() { # every state empty, AND the second look (proof.sh) finds nothing
  local s n bad=0
  for s in "${ORDER[@]}"; do
    if n=$(statecount "$s"); then
      printf '%-14s %s item(s) in state\n' "$s" "$n"
      [ "$n" = 0 ] || bad=1
    else
      printf '%-14s state UNREADABLE (this proves nothing)\n' "$s"; bad=1
    fi
  done
  bash "$LAB/proof.sh" || bad=1
  if [ $bad = 0 ]; then echo "CHECK PASSED: nothing remains"; else echo "CHECK FAILED: something remains"; fi
  return $bad
}

cycle() {
  local i n="${1:-5}"
  for ((i=1; i<=n; i++)); do
    echo "######## cycle $i of $n"
    build || { echo "cycle $i: build failed"; return 1; }
    echo "cycle $i: $(count) resources in state after build"
    destroy || { echo "cycle $i: destroy failed"; return 1; }
    check || { echo "cycle $i: NOT EMPTY"; return 1; }
  done
  echo "ALL $n CYCLES CLEAN"
}

case "${1:-}" in
  build) build ;; destroy) destroy ;; check) check ;; cycle) cycle "${2:-5}" ;;
  *) echo "usage: $0 build|destroy|check|cycle N"; exit 2 ;;
esac
EOF
chmod +x "$LAB/lab.sh" "$LAB/proof.sh" "$LAB/audit.sh"
echo "lab written to $LAB"
```

The PowerShell version writes the same files (est.: not run). Save it as `setup.ps1` and run it with `.\setup.ps1`. If PowerShell refuses to run a script, see your execution policy in Microsoft's documentation, and run it for one session only.

```powershell
# setup.ps1: write the five-stack practice lab into a scratch folder. Usage: .\setup.ps1 [-Lab FOLDER]
# SPDX-License-Identifier: Apache-2.0
param([string]$Lab = "$HOME\iac4-lab")
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force "$Lab\stacks", "$Lab\world" | Out-Null
$Lab = (Resolve-Path $Lab).Path
$Fwd = $Lab -replace '\\', '/'   # OpenTofu is happy with forward slashes on Windows

# Stack 00 makes the tag every other stack will read.
$TagTf = @'
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "name" { type = string }
variable "world" { type = string }

locals {
  tag = "cah-lab"
}

resource "local_file" "this" {
  filename = "${var.world}/${var.name}.txt"
  content  = "tag=${local.tag}\nstack=${var.name}\n"
}

output "tag" {
  value = local.tag
}
'@

# Stacks 10 to 40 share one shape: read the stacks they need, write one file.
$ConsumerTf = @'
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "name" { type = string }
variable "world" { type = string }
variable "root" { type = string }

variable "needs" {
  type = list(string)
  validation {
    condition     = contains(var.needs, "00-tag")
    error_message = "Every stack needs 00-tag: it owns the tag."
  }
}

# Read-only look at the OUTPUTS of the stacks this one depends on.
data "terraform_remote_state" "up" {
  for_each = toset(var.needs)
  backend  = "local"
  config = {
    path = "${var.root}/stacks/${each.key}/terraform.tfstate"
  }
}

locals {
  tag = data.terraform_remote_state.up["00-tag"].outputs.tag
  seen = [for k in sort(var.needs) : "${k}=${try(data.terraform_remote_state.up[k].outputs.id, data.terraform_remote_state.up[k].outputs.tag)}"]
}

resource "local_file" "this" {
  filename = "${var.world}/${var.name}.txt"
  content  = "tag=${local.tag}\nstack=${var.name}\n${join("\n", local.seen)}\n"
}

output "id" {
  value = local_file.this.id
}
'@

function New-Stack([string]$Name, [string[]]$Needs) {
    New-Item -ItemType Directory -Force "$Lab\stacks\$Name" | Out-Null
    $tf = if ($Name -eq '00-tag') { $TagTf } else { $ConsumerTf }
    Set-Content -Path "$Lab\stacks\$Name\main.tf" -Value $tf -Encoding ascii
    $vars = @("name  = `"$Name`"", "world = `"$Fwd/world`"")
    if ($Name -ne '00-tag') {
        $list = ($Needs | ForEach-Object { "`"$_`"" }) -join ', '
        $vars += "root  = `"$Fwd`""
        $vars += "needs = [$list]"
    }
    Set-Content -Path "$Lab\stacks\$Name\terraform.tfvars" -Value $vars -Encoding ascii
}
New-Stack '00-tag' @()
New-Stack '10-firewall' @('00-tag')
New-Stack '20-network' @('00-tag', '10-firewall')
New-Stack '30-server-a' @('00-tag', '10-firewall', '20-network')
New-Stack '40-server-b' @('00-tag', '10-firewall', '20-network')

Set-Content "$Lab\order.txt" @('00-tag', '10-firewall', '20-network', '30-server-a', '40-server-b') -Encoding ascii

# proof.ps1: the second, independent look. Here: is anything left in the world folder?
Set-Content "$Lab\proof.ps1" -Encoding ascii -Value @'
$files = @(Get-ChildItem "$PSScriptRoot\world" -Recurse -File).Count
"{0,-14} {1} file(s) left" -f 'world/', $files
exit ([int]($files -ne 0))
'@

# audit.ps1: list everything left, tagged or not.
Set-Content "$Lab\audit.ps1" -Encoding ascii -Value @'
$left = 0
Get-ChildItem "$PSScriptRoot\world" -Recurse -File | Sort-Object Name | ForEach-Object {
    $left = 1
    if (Select-String -Path $_.FullName -Pattern '^tag=cah-lab$' -Quiet) { "TAGGED    $($_.Name)" } else { "UNTAGGED  $($_.Name)" }
}
if ($left -eq 0) { 'audit: world is empty' }
exit $left
'@

Set-Content "$Lab\lab.ps1" -Encoding ascii -Value @'
# lab.ps1: build all stacks in order.txt, destroy them in reverse, prove nothing remains.
# Usage: .\lab.ps1 build | destroy | check | cycle [N]
param([Parameter(Position = 0)][string]$Action = '', [Parameter(Position = 1)][int]$N = 5)
$Lab = $PSScriptRoot
$Order = @(Get-Content "$Lab\order.txt" | Where-Object { $_ })
if (-not $env:TF_PLUGIN_CACHE_DIR) { $env:TF_PLUGIN_CACHE_DIR = "$HOME\.cache\iac4-plugins" }
New-Item -ItemType Directory -Force $env:TF_PLUGIN_CACHE_DIR | Out-Null
$env:TF_IN_AUTOMATION = '1'

function Tf([string]$Stack, [string[]]$More) { & tofu "-chdir=$Lab/stacks/$Stack" @More '-no-color' }

function Build {
    foreach ($s in $Order) {
        "== build $s"
        Tf $s @('init', '-input=false') | Out-Null
        if ($LASTEXITCODE -ne 0) { "build failed at $s"; return $false }
        $out = Tf $s @('apply', '-auto-approve', '-input=false') 2>&1
        $out | Select-String '^(Apply complete|Error)' | Out-Host
        if ($LASTEXITCODE -ne 0) { "build failed at $s"; return $false }
    }
    return $true
}

function Destroy {
    $ok = $true
    for ($i = $Order.Count - 1; $i -ge 0; $i--) {
        $s = $Order[$i]
        "== destroy $s"
        Tf $s @('init', '-input=false') | Out-Null
        $out = Tf $s @('destroy', '-auto-approve', '-input=false') 2>&1
        $out | Select-String '^(Destroy complete|Error)' | Out-Host
        if ($LASTEXITCODE -ne 0) { "destroy failed at $s"; $ok = $false }
    }
    return $ok
}

# State-Count STACK: items in one state. No state file means nothing was applied: 0.
# A state file that exists but cannot be read returns -1 (an error), never 0.
function State-Count([string]$Stack, [bool]$ManagedOnly = $false) {
    if (-not (Test-Path "$Lab\stacks\$Stack\terraform.tfstate")) { return 0 }
    $out = Tf $Stack @('state', 'list') 2>&1
    if ($LASTEXITCODE -ne 0) { return -1 }
    $items = @($out | Where-Object { $_ })
    if ($ManagedOnly) { $items = @($items | Where-Object { $_ -notmatch '^data\.' }) }
    return $items.Count
}

function Count-Managed { # managed resources in all states (data sources do not count)
    $total = 0
    foreach ($s in $Order) { $total += [Math]::Max(0, (State-Count $s $true)) }
    return $total
}

function Check { # every state empty, AND the second look (proof.ps1) finds nothing
    $bad = $false
    foreach ($s in $Order) {
        $n = State-Count $s
        if ($n -lt 0) { "{0,-14} state UNREADABLE (this proves nothing)" -f $s; $bad = $true; continue }
        "{0,-14} {1} item(s) in state" -f $s, $n
        if ($n -ne 0) { $bad = $true }
    }
    & "$Lab\proof.ps1"
    if ($LASTEXITCODE -ne 0) { $bad = $true }
    if ($bad) { 'CHECK FAILED: something remains' } else { 'CHECK PASSED: nothing remains' }
    return (-not $bad)
}

switch ($Action) {
    'build'   { if (Build) { exit 0 } else { exit 1 } }
    'destroy' { if (Destroy) { exit 0 } else { exit 1 } }
    'check'   { if (Check) { exit 0 } else { exit 1 } }
    'cycle'   {
        for ($i = 1; $i -le $N; $i++) {
            "######## cycle $i of $N"
            if (-not (Build)) { "cycle $i`: build failed"; exit 1 }
            "cycle $i`: $(Count-Managed) resources in state after build"
            if (-not (Destroy)) { "cycle $i`: destroy failed"; exit 1 }
            if (-not (Check)) { "cycle $i`: NOT EMPTY"; exit 1 }
        }
        "ALL $N CYCLES CLEAN"
    }
    default   { 'usage: .\lab.ps1 build|destroy|check|cycle [N]'; exit 2 }
}
'@
Write-Output "lab written to $Lab"
```

Look at what you got. The producer stack is short, and the other four are one file copied four times with different `terraform.tfvars`:

```bash
cd ~/iac4-lab
cat stacks/30-server-a/terraform.tfvars
```

```powershell
Set-Location $HOME\iac4-lab
Get-Content .\stacks\30-server-a\terraform.tfvars
```

You will see the stack's name, the `world` folder, the `root` folder and `needs = ["00-tag", "10-firewall", "20-network"]`. The `needs` list is the dependency list from the picture, in data.

### Exercise 1: predict before you build

**Predict.** Without running anything, write down: (a) how many resources the five states will hold after a full build; (b) which stack's file will contain the line `10-firewall=` and what comes after the equals sign; (c) what `./lab.sh check` will say right now, before any build.

**Do.**

```bash
cd ~/iac4-lab
./lab.sh check; echo "exit=$?"
```

```powershell
Set-Location $HOME\iac4-lab
.\lab.ps1 check; "exit=$LASTEXITCODE"
```

**Check.** Before any build there are no states yet, so each stack shows `0 item(s) in state`, the world folder shows `0 file(s) left`, and the check prints `CHECK PASSED: nothing remains` and exits 0. That is the baseline: a checker you have only ever seen pass proves nothing, so you will see it fail in Exercise 3 and Exercise 6. (a) is 5, one local file per stack; the remote-state lookups are data sources and are not counted. (b) The files for `20-network`, `30-server-a` and `40-server-b`, each followed by the firewall file's ID (a long hexadecimal string; yours will differ).

**Undo.** Nothing was created.

### Exercise 2: build all five, in order

**Predict.** Which stack must be built first, and what happens if you try to plan `30-server-a` before `00-tag` exists?

**Do.**

```bash
cd ~/iac4-lab
./lab.sh build
cat world/40-server-b.txt
```

```powershell
Set-Location $HOME\iac4-lab
.\lab.ps1 build
Get-Content .\world\40-server-b.txt
```

**Check.** Five lines of the form `== build <stack>` each followed by `Apply complete! Resources: 1 added, 0 changed, 0 destroyed.` (the first run also downloads the provider and takes longer). The file looks like this; the two IDs will differ:

```text
tag=cah-lab
stack=40-server-b
00-tag=cah-lab
10-firewall=1d71d8f7a40d90e5f49f14de224b2b0133266fbd
20-network=c1e113a77d9a86f4de352c5581aa9745f28c0ac1
```

Those last three lines are the cross-stack values. `00-tag=cah-lab` is the producer's output; the other two are IDs from the stacks it read. Run `./lab.sh build` a second time: every stack says `0 added`, because nothing changed. A second run that changes nothing is a property worth wanting from every stack. For the answer to the predict question: if you try to plan `30-server-a` first, its `terraform_remote_state` looks for state files that are not there and the plan fails with `Error: Unable to find remote state` (what OpenTofu 1.12.6 printed on 2026-10-22).

**Undo.** The next exercise destroys it.

### Exercise 3: destroy all five, in reverse, and prove it

**Predict.** In what order will the stacks be destroyed? After the destroy, will the folders `stacks/*/terraform.tfstate` still exist?

**Do.**

```bash
./lab.sh destroy
./lab.sh check; echo "exit=$?"
ls stacks/00-tag
```

```powershell
.\lab.ps1 destroy
.\lab.ps1 check; "exit=$LASTEXITCODE"
Get-ChildItem .\stacks\00-tag
```

**Check.** The destroy goes `40-server-b`, `30-server-a`, `20-network`, `10-firewall`, `00-tag`, each reporting `Destroy complete! Resources: 1 destroyed.` Then the check prints:

```text
00-tag         0 item(s) in state
10-firewall    0 item(s) in state
20-network     0 item(s) in state
30-server-a    0 item(s) in state
40-server-b    0 item(s) in state
world/         0 file(s) left
CHECK PASSED: nothing remains
```

and exits 0. The state files still exist (`terraform.tfstate` and a `.backup`): they are empty, which is the hazard in lessons-learned item 5. An empty state is not the same as no state; that is why the checker asks for resources, not for the absence of a file.

**Undo.** Nothing to undo; this was the undo. Build again when you need to.

### Exercise 4: five full cycles

A loop is where this becomes a habit. One cycle is: build all, count what is in state, destroy all, run the checker. Any red stops the loop.

**Predict.** How many resources will the count show after each build, and will the fifth cycle be any different from the first?

**Do.**

```bash
cd ~/iac4-lab
./lab.sh cycle 5
```

```powershell
Set-Location $HOME\iac4-lab
.\lab.ps1 cycle 5
```

**Check.** For each of the five cycles you see `cycle N: 5 resources in state after build`, then the destroy, then `CHECK PASSED: nothing remains`, and the last line is `ALL 5 CYCLES CLEAN`. On the author's machine the five cycles took about 13 seconds in all once the provider was cached. If a cycle fails, the script stops there and tells you which one; do not start another until you can explain it.

**Undo.** The loop ends with everything destroyed. Run `./lab.sh check` to see it for yourself.

### Exercise 5: destroy in the wrong order, on purpose

**Predict.** If you destroy `00-tag` first while the other four exist, what do you expect when you then run the normal destroy? Which stacks will fail, and which will not?

**Do.**

```bash
cd ~/iac4-lab
./lab.sh build > /dev/null
tofu -chdir=stacks/00-tag destroy -auto-approve -no-color | tail -1
./lab.sh destroy
./lab.sh check; echo "exit=$?"
```

```powershell
Set-Location $HOME\iac4-lab
.\lab.ps1 build | Out-Null
tofu -chdir=stacks/00-tag destroy -auto-approve -no-color | Select-Object -Last 1
.\lab.ps1 destroy
.\lab.ps1 check; "exit=$LASTEXITCODE"
```

**Check.** The first command succeeds (`Destroy complete! Resources: 1 destroyed.`). Then the normal destroy fails for the four consumers, one after another:

```text
== destroy 40-server-b
Error: Unsupported attribute
Error: Error in function call
destroy failed at 40-server-b
...
== destroy 00-tag
Destroy complete! Resources: 0 destroyed.
```

and the check ends `CHECK FAILED: something remains` with exit 1, showing 2, 3, 4 and 4 items still in the four consumer states and 4 files left. The error, in full, is that `data.terraform_remote_state.up["00-tag"].outputs is object with no attributes`: the producer no longer publishes the tag, and the consumers cannot plan anything, including their own destruction. In a real cloud, the failure would usually come earlier and from the provider, and the cure is the same.

**Undo (recovery).** Put the producer back, then destroy properly. The build is safe to repeat; it recreates `00-tag` and leaves the rest as they are:

```bash
./lab.sh build > /dev/null
./lab.sh destroy
./lab.sh check; echo "exit=$?"
```

```powershell
.\lab.ps1 build | Out-Null
.\lab.ps1 destroy
.\lab.ps1 check; "exit=$LASTEXITCODE"
```

The check passes again. Note what you did: you rebuilt in order so you could destroy in order. That is the standard recovery.

### Exercise 6: a forgotten resource and an untagged one

**Predict.** Suppose a destroy stops early and leaves `40-server-b` built, and somebody also creates one file by hand with no tag. Which of the two does a tag-based search find? Which does the whole-folder listing find?

**Do.**

```bash
cd ~/iac4-lab
./lab.sh build > /dev/null
tofu -chdir=stacks/30-server-a destroy -auto-approve -no-color | tail -1   # 30 only; 40 is "forgotten"
printf 'owner=someone\n' > world/handmade.txt                               # a resource nobody tagged
echo "--- tag search:"; grep -l '^tag=cah-lab$' world/*
echo "--- whole-folder audit:"; ./audit.sh; echo "audit exit=$?"
./lab.sh check | tail -3
```

```powershell
Set-Location $HOME\iac4-lab
.\lab.ps1 build | Out-Null
tofu -chdir=stacks/30-server-a destroy -auto-approve -no-color | Select-Object -Last 1
Set-Content .\world\handmade.txt 'owner=someone'
"--- tag search:"; Select-String -Path .\world\* -Pattern '^tag=cah-lab$' -List | ForEach-Object Path
"--- whole-folder audit:"; .\audit.ps1; "audit exit=$LASTEXITCODE"
.\lab.ps1 check | Select-Object -Last 3
```

**Check.** The tag search lists the four tagged files and **not** `handmade.txt`. The audit lists all five, and marks the last as `UNTAGGED  handmade.txt`; it exits 1 because anything left at all is a failure. `check` fails too. The lesson: a tag search proves "everything I tagged is gone" and nothing more. The untagged file was invisible to it.

**Undo.**

```bash
rm world/handmade.txt
./lab.sh destroy && ./lab.sh check
```

```powershell
Remove-Item .\world\handmade.txt
.\lab.ps1 destroy; .\lab.ps1 check
```

### Exercise 7: read how this project pins its addresses (read-only)

You need a clone of the repository for this one. It reads files and changes nothing.

**Predict.** If a pull request added one new resource to `stacks/00-foundation` and forgot to touch `docs/golden-addresses/00-foundation.json`, what would `scripts/plan_noop_check.py` say about a plan from that code?

**Do.** From the root of a clone:

```bash
python3 -I -c "import json; g=json.load(open('docs/golden-addresses/00-foundation.json')); print(len(g['addresses']), 'addresses'); print(*sorted(g['addresses']), sep='\n')"
python3 -I scripts/plan_noop_check.py --help | head -20
```

```powershell
python -I -c "import json; g=json.load(open('docs/golden-addresses/00-foundation.json')); print(len(g['addresses']), 'addresses'); print(*sorted(g['addresses']), sep='\n')"
python -I scripts/plan_noop_check.py --help | Select-Object -First 20
```

**Check.** You get the list of resource addresses stack 00 plans. The checker's header says it fails on any change that is not a no-op, on an address missing from the golden list, and on a golden address missing from the plan. So the answer to the predict question is: it would name the new address as not in the golden file. The pull request has to add it on purpose, and a reviewer sees that edit.

**Undo.** Nothing changed.

## Optional: the same shape on your own cloud account

> **Status of this path: the files validate against the provider's schema; nothing here was ever applied.** Run it expecting to fix something.

This path builds the same five boxes on DigitalOcean: a tag, a firewall attached by that tag, a private network, and two of the smallest droplets. It uses your own account and your own bill. It is optional, and the free path above teaches the same lesson.

### Cost and teardown (read first)

**Teardown first, in this order.** Write these down before you build anything.

```bash
cd ~/iac4-cloud && ./lab.sh destroy && ./lab.sh check        # the normal route
# If the stacks' state is lost and the check shows leftovers, use the tag (flags from the doctl reference):
doctl compute droplet delete --tag-name cah-lab-iac4 --force
doctl compute firewall list --format ID,Name                 # note the cah-lab-iac4 ID, then:
doctl compute firewall delete FIREWALL_ID --force
doctl vpcs list --format ID,Name                             # note the cah-lab-iac4-net ID, then:
doctl vpcs delete VPC_ID --force
doctl compute tag delete cah-lab-iac4 --force
```

```powershell
# est.: the cloud lab is Bash-first. On Windows, run lab.sh from WSL or Git Bash; these doctl lines are the same in PowerShell.
doctl compute droplet delete --tag-name cah-lab-iac4 --force
doctl compute firewall list --format ID,Name
doctl compute firewall delete FIREWALL_ID --force
doctl vpcs list --format ID,Name
doctl vpcs delete VPC_ID --force
doctl compute tag delete cah-lab-iac4 --force
```

(`FIREWALL_ID` and `VPC_ID` are placeholders for the IDs you read. Whether `--force` is accepted by the `firewall delete`, `vpcs delete` and `tag delete` commands should be confirmed with `--help` on your doctl version; est.)

**Prove nothing remains.** Use a read-only token. The `proof.sh` the setup script writes lists droplets, firewalls, VPCs and tags whose names start with `cah-lab-`, and also lists your volumes, snapshots and reserved addresses, which do not carry the lab's name; use a dedicated account or project, because any item in those three lists fails the proof until you explain or delete it. It **fails closed**: if `doctl` is missing or the token is rejected, it says the listing failed and exits 1, instead of printing zero. An API alternative, read-only: `GET https://api.digitalocean.com/v2/droplets?tag_name=cah-lab-iac4`, which per DigitalOcean's published API description needs the `tag:read` scope.

**Cost.** Computed from `docs/cost-prices.json` only (retrieved 2026-10-21 from DigitalOcean's sizes API) and DigitalOcean's pricing page (read 2026-10-22):

| Fact | Value | Where it comes from |
|---|---|---|
| Smallest droplet size in the file | `s-1vcpu-512mb-10gb`, $4 a month | `docs/cost-prices.json` |
| Next size | `s-1vcpu-1gb`, $6 a month, verified available in `tor1` on 2026-10-21 | `docs/cost-prices.json`, `docs/cost.md` |
| Billing unit | per second, minimum charge of 60 seconds or $0.01, whichever is higher | DigitalOcean pricing page |
| Monthly cap | usage capped at 672 hours (28 days) a month | DigitalOcean pricing page |
| Powered off | still billed; destroy to stop billing | DigitalOcean pricing page |
| Hourly rate | about monthly price divided by 672, so $4 gives about $0.006 an hour (**est.**: the hourly rate itself was not read) | derived |
| Firewall, tag, VPC | no line in `docs/cost.md` or the gate's price list; DigitalOcean's firewall page calls cloud firewalls "at no additional cost" | repository and DigitalOcean docs |

Region and size availability differ by account: the file lists `s-1vcpu-512mb-10gb`, but `docs/cost.md` only re-read five other sizes for `tor1`, so check yours first with `doctl compute size list` (read-only) and fall back to `s-1vcpu-1gb` if it is missing.

**Hard budget: $1.00 for the whole path.** The planned run is 2 droplets x 3 cycles x 30 minutes. Each droplet-run is billed at least the $0.01 minimum. The budget covers that run **and one forgotten day** (about $0.29, est.). A forgotten month would be $8.00 at $4 each, which is eight times the budget: the script prints it but does not count it as covered, because only the destroy, your calendar reminder and a spend alert cover that. Do not trust my arithmetic: this script recomputes it from the file in your clone, and refuses to say OK if the covered number is over budget or the size is not in the file.

```python
# budget.py: worst-case cost of the cloud lab, from the repository's own price file only.
# SPDX-License-Identifier: Apache-2.0
# Usage: python3 -I budget.py PRICES_JSON SIZE DROPLETS HOURS_EACH CYCLES BUDGET_USD
import json
import sys

path, size = sys.argv[1], sys.argv[2]
droplets, hours, cycles, budget = int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])
with open(path, encoding="utf-8") as fh:
    prices = json.load(fh)["droplets"]
if size not in prices:
    sys.exit(f"STOP: {size} is not in {path}; no price read, no run")
monthly = float(prices[size])
hourly = monthly / 672  # est.: DigitalOcean caps bundled droplets at 672 hours; the hourly rate itself was not read
one_run = max(hours * hourly, 0.01)  # DigitalOcean's minimum charge is 60 seconds or $0.01, whichever is higher
planned = droplets * cycles * one_run
forgotten_day = droplets * 24 * hourly
forgotten_month = droplets * monthly
# The guard covers the planned run and one forgotten day. A forgotten month is shown, not allowed.
print(f"size {size}: ${monthly:.2f} a month (file), about ${hourly:.5f} an hour (est.)")
print(f"planned: {droplets} droplet(s) x {cycles} cycle(s) x {hours:g} h each: about ${planned:.3f} (est.)")
print(f"if you forget them for a day: about ${forgotten_day:.3f} (est.)")
print(f"if you forget them for a month: ${forgotten_month:.2f} (NOT covered by the budget: only destroying covers that)")
ok = max(planned, forgotten_day) <= budget
print(f"budget ${budget:.2f}:", "OK" if ok else "OVER, do not run")
sys.exit(0 if ok else 1)
```

```bash
python3 -I budget.py path/to/Clouds-Against-Humanity/docs/cost-prices.json s-1vcpu-512mb-10gb 2 0.5 3 1.00
```

```powershell
python -I budget.py path\to\Clouds-Against-Humanity\docs\cost-prices.json s-1vcpu-512mb-10gb 2 0.5 3 1.00
```

The output the author got on 2026-10-22:

```text
size s-1vcpu-512mb-10gb: $4.00 a month (file), about $0.00595 an hour (est.)
planned: 2 droplet(s) x 3 cycle(s) x 0.5 h each: about $0.060 (est.)
if you forget them for a day: about $0.286 (est.)
if you forget them for a month: $8.00 (NOT covered by the budget: only destroying covers that)
budget $1.00: OK
```

**Set a spend alert, and know what it is.** In the billing area, create a spend alert for a small monthly budget (say $5) with thresholds. DigitalOcean's page is explicit that this is not a cap. It emails you; it does not stop anything. The reminder to destroy is the control.

**Data and credentials.** No real data goes on these machines. Keep the API token in your shell session or password manager, not in a file in the folder; the provider reads `DIGITALOCEAN_TOKEN` from the environment. Use a separate account or project for experiments, and revoke the token when you finish. This lab never logs in to the droplets.

### The files

The setup script copies `lab.sh` from your free lab, writes the five cloud stacks, and replaces `order.txt` and `proof.sh`. It calls no API. Save it as `setup-cloud.sh`. Run it only after the budget script said OK, passing the size the budget approved.

```bash
#!/usr/bin/env bash
# setup-cloud.sh: write the same five-stack shape for DigitalOcean. It writes files only; it calls no API.
# SPDX-License-Identifier: Apache-2.0
# Usage: SIZE=<slug from budget.py> bash setup-cloud.sh [FOLDER]   (needs ~/iac4-lab/lab.sh from the free tier)
set -euo pipefail
: "${SIZE:?set SIZE to a droplet size slug that budget.py approved}"
REGION="${REGION:-tor1}"
LAB="${1:-$HOME/iac4-cloud}"
mkdir -p "$LAB/stacks"
LAB="$(cd "$LAB" && pwd)"
cp "${FREE_LAB:-$HOME/iac4-lab}/lab.sh" "$LAB/lab.sh"

hdr() { cat <<'EOF'
terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}
# The token comes from the environment (DIGITALOCEAN_TOKEN), never from a file.
provider "digitalocean" {}
EOF
}
up() { cat <<'EOF'
variable "root" { type = string }
data "terraform_remote_state" "tag" {
  backend = "local"
  config  = { path = "${var.root}/stacks/00-tag/terraform.tfstate" }
}
locals { tag = data.terraform_remote_state.tag.outputs.tag }
EOF
}

mkdir -p "$LAB/stacks/00-tag"
{ hdr; cat <<'EOF'
variable "tag" { type = string }
resource "digitalocean_tag" "this" { name = var.tag }
output "tag" { value = digitalocean_tag.this.name }
EOF
} > "$LAB/stacks/00-tag/main.tf"
printf 'tag = "cah-lab-iac4"\n' > "$LAB/stacks/00-tag/terraform.tfvars"

mkdir -p "$LAB/stacks/10-firewall"
{ hdr; up; cat <<'EOF'
# No inbound and no outbound rules: DigitalOcean's cloud firewalls block what no rule permits.
resource "digitalocean_firewall" "this" {
  name = "cah-lab-iac4-baseline"
  tags = [local.tag]
}
output "id" { value = digitalocean_firewall.this.id }
EOF
} > "$LAB/stacks/10-firewall/main.tf"
printf 'root = "%s"\n' "$LAB" > "$LAB/stacks/10-firewall/terraform.tfvars"

mkdir -p "$LAB/stacks/20-network"
{ hdr; up; cat <<'EOF'
variable "region" { type = string }
data "terraform_remote_state" "fw" {
  backend = "local"
  config  = { path = "${var.root}/stacks/10-firewall/terraform.tfstate" }
}
resource "digitalocean_vpc" "this" {
  name     = "cah-lab-iac4-net"
  region   = var.region
  ip_range = "10.99.0.0/24"
  # Reading the firewall's id makes the order real: the network cannot even be planned without it.
  lifecycle {
    precondition {
      condition     = data.terraform_remote_state.fw.outputs.id != ""
      error_message = "Build 10-firewall first."
    }
  }
}
output "id" { value = digitalocean_vpc.this.id }
EOF
} > "$LAB/stacks/20-network/main.tf"
printf 'root = "%s"\nregion = "%s"\n' "$LAB" "$REGION" > "$LAB/stacks/20-network/terraform.tfvars"

for d in 30-server-a 40-server-b; do
  mkdir -p "$LAB/stacks/$d"
  { hdr; up; cat <<'EOF'
variable "name" { type = string }
variable "region" { type = string }
variable "size" { type = string }
data "terraform_remote_state" "fw" {
  backend = "local"
  config  = { path = "${var.root}/stacks/10-firewall/terraform.tfstate" }
}
data "terraform_remote_state" "net" {
  backend = "local"
  config  = { path = "${var.root}/stacks/20-network/terraform.tfstate" }
}
resource "digitalocean_droplet" "this" {
  name       = var.name
  image      = "ubuntu-24-04-x64"
  region     = var.region
  size       = var.size
  vpc_uuid   = data.terraform_remote_state.net.outputs.id
  tags       = [local.tag]
  backups    = false
  monitoring = false
  ipv6       = false
  # The firewall stack ran first. Reading its id here makes the order explicit.
  lifecycle {
    precondition {
      condition     = data.terraform_remote_state.fw.outputs.id != ""
      error_message = "Build 10-firewall first: a droplet must never exist without it."
    }
  }
}
output "id" { value = digitalocean_droplet.this.id }
EOF
  } > "$LAB/stacks/$d/main.tf"
  printf 'root = "%s"\nname = "cah-lab-%s"\nregion = "%s"\nsize = "%s"\n' "$LAB" "$d" "$REGION" "$SIZE" > "$LAB/stacks/$d/terraform.tfvars"
done

printf '%s\n' 00-tag 10-firewall 20-network 30-server-a 40-server-b > "$LAB/order.txt"

# proof.sh: the second look, from DigitalOcean's side. Read-only doctl listings.
cat > "$LAB/proof.sh" <<'EOF'
#!/usr/bin/env bash
# Needs doctl logged in with a READ-ONLY token. Lists only; changes nothing.
bad=0
show() { # show LABEL COMMAND...  : count lines whose name starts with cah-lab-
  local label="$1" out n; shift
  out=$("$@" 2>&1) || { echo "$label: the listing FAILED, so this proves nothing: $out"; bad=1; return; }
  n=$(printf '%s\n' "$out" | grep -c '^cah-lab-' || true)
  printf '%-10s %s left named cah-lab-*\n' "$label" "$n"
  [ "$n" = 0 ] || bad=1
}
show droplets  doctl compute droplet list --no-header --format Name
show firewalls doctl compute firewall list --no-header --format Name
show vpcs      doctl vpcs list --no-header --format Name
show tags      doctl compute tag list --no-header --format Name
for kind in "volume list" "snapshot list" "reserved-ip list"; do
  out=$(doctl compute $kind --no-header 2>&1) || { echo "$kind: the listing FAILED: $out"; bad=1; continue; }
  n=$(printf '%s\n' "$out" | grep -c . || true)
  printf '%-16s %s item(s)\n' "$kind" "$n"
  # These do not carry the lab's name, so use a dedicated account or project: any item fails the proof.
  [ "$n" = 0 ] || { echo "  ^ not empty: explain it or delete it, then run the proof again"; bad=1; }
done
exit $bad
EOF
chmod +x "$LAB/lab.sh" "$LAB/proof.sh"
echo "cloud lab written to $LAB (no API was called)"
```

```bash
cd ~
SIZE=s-1vcpu-512mb-10gb bash setup-cloud.sh
```

```powershell
# est.: the generator is a Bash script. On Windows run it from WSL or Git Bash; the files it writes are identical.
wsl bash -c 'cd ~ && SIZE=s-1vcpu-512mb-10gb bash setup-cloud.sh'
```

Read before you run. Open each stack and answer: what does it read, what does it create, what does it output? Notice that the firewall has **no rules**: DigitalOcean's documentation says cloud firewalls block all traffic that is not expressly permitted, so the droplets are closed from the first second, which is why the firewall stack is built before the servers. Whether the tag-attached firewall is in effect before a new droplet finishes booting is **est.**

### Exercise 8: build and destroy the cloud set

**Predict.** How many billable resources will exist after the build, and what is the worst case if you walk away right now?

**Do.**

```bash
read -rsp 'token: ' DIGITALOCEAN_TOKEN; export DIGITALOCEAN_TOKEN; echo   # typed at the prompt; not echoed, not saved
cd ~/iac4-cloud
tofu -chdir=stacks/00-tag init -input=false -no-color > /dev/null
tofu -chdir=stacks/00-tag plan -no-color | tail -5     # read it; it should show 1 to add
./lab.sh build
bash proof.sh; echo "exit=$?"                          # EXPECTED to fail: things exist
./lab.sh destroy
bash proof.sh; echo "exit=$?"                          # now 0
```

```powershell
# est.: not run. The cloud lab's scripts are Bash, so on Windows run the Bash lines above inside WSL or Git Bash.
# The only PowerShell-specific part is setting and clearing the token for a session that calls doctl or tofu directly:
$sec = Read-Host -AsSecureString 'token'
$env:DIGITALOCEAN_TOKEN = [System.Net.NetworkCredential]::new('', $sec).Password
# ... work ...
Remove-Item Env:DIGITALOCEAN_TOKEN
```

**Check.** After the build, `proof.sh` reports droplets and firewalls and VPCs and a tag with a count above zero, and exits 1: the proof can fail, which is what makes it a proof. After the destroy all four show `0 left named cah-lab-*` and the script exits 0. Look at the billing page the next day: usage for the hours you ran, and nothing continuing. Then run `unset DIGITALOCEAN_TOKEN` (PowerShell: `Remove-Item Env:DIGITALOCEAN_TOKEN`), revoke the token, and delete the folder.

**Undo.** The destroy is the undo. If anything is left, use the tag-based teardown at the top of this section.

## Optional: run the same stacks through Spacelift

The same five stacks, with the dependencies as Spacelift stack dependencies and the outputs mapped to `TF_VAR_` variables, run through Spacelift's plan, approve and apply steps instead of from your terminal. That is the third lesson of the track: [Spacelift from zero](Spacelift-From-Zero.md) (a planned lesson; the link works once it merges). Read it for the setup. Do not point this project's own Spacelift stacks at any of it: those stacks are locked and only the maintainer changes them.

## Build, break, detect, evade, defend

The same loop as the [labs](Labs-Break-It-on-Purpose.md), applied to a resource nobody remembers. Everything is in the free lab or on paper; you need no account.

**Build.** The five-stack lab: every file tagged `cah-lab`, every stack destroyable, a checker that proves emptiness two ways.

**Break.** A forgotten resource: a destroy that stops early, leaving `40-server-b` built. In a cloud this is a droplet nobody is looking at, billing every hour. You did it in Exercise 6.

**Detect.** A tag audit. `grep -l '^tag=cah-lab$' world/*` in the lab; `doctl compute droplet list --tag-name <tag>` in the cloud. It finds the forgotten stack and the tagged files, and a scheduled run of it, with a person who gets the result, turns "I should check" into a habit. Detection also has a second source: the billing page and cost analysis, which show spend by product whether or not you remembered the resource. That is why the teardown checklist insists on looking again the next day.

**Evade.** A resource that does not carry the tag: `handmade.txt`. In a cloud it is a droplet made in the console, a resource whose provider does not support tags, a resource a script created with a typo in the tag, or a resource somebody deliberately left untagged. The tag audit does not find it. This is not an attack technique in any sense that needs a target; it is the ordinary way a clean-looking account is not clean, and an attacker who creates infrastructure in an account they have taken over has the same preference for not carrying your tags. Nothing here shows how to do that to anyone else's account.

**Defend.** Three layers, none sufficient alone.

- **Make untagged creation hard.** Where the platform has an organization-wide tag policy or a policy-as-code check, require the tag at creation (check whether your provider offers one; I did not verify DigitalOcean here, est.). In this project the equivalent is CI: the cost gate refuses a stack with no manifest and an unpriced billable resource type, and the plan policy refuses to delete a protected resource.
- **Inventory the whole account, not only the tag.** List everything and explain each line. The lab's `audit.sh` does this for the folder. For a cloud account, the read-only listings in [Teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources).
- **A cost report and a spend alert,** read by a person. The report shows spend by product and by day; the alert tells you when you cross a line. Neither is a cap.
- **Separate accounts for experiments,** so there is a small, known set of things that can be wrong.

### Flip the board

Now be the person who has to run an account for a team, not the person who made one mistake.

1. You inherit an account with 60 resources and no stack for 20 of them. What is the first read-only thing you do, and what do you not do until you have it?
2. A teammate says "just tag it by hand afterwards." What is the argument against, and what is the argument for?
3. Production's network stack and a service's stack are both yours. Which one may a new hire destroy, and which approvals does the other need?
4. A cost report shows $40 for a product nobody on the team uses. Walk through finding the resource without clicking around: which listing, which filter, and which token scope?
5. Your destroy script reported success. Name three independent places you would look before you believed it.

Write your answers down. Question 5 has the answer in [lessons-learned item 8](#lessons-learned-what-makes-a-destroy-fail-or-leave-a-bill): resource listings, the provider's console, and tomorrow's billing page.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `Unsupported attribute` or `Error in function call` on a destroy of a consumer | The producer was destroyed first | Rebuild the producer, then destroy consumers first (Exercise 5). |
| `No such file` or an empty output on the first plan of a consumer | The producer was never applied | Build in order. |
| `Error: Failed to load plugin schemas` or provider download fails | No network to the registry, or a stale cache | Run `tofu init` again; set `TF_PLUGIN_CACHE_DIR` to a folder you own. |
| The checker passes but the cloud still bills | The checker listed the wrong account, region or tag | Check the token's account, list without filters, look at the billing page tomorrow. |
| `proof.sh` says "the listing FAILED" | `doctl` not installed, not logged in, or a token without read scope | Fix the credential; do not read a failed listing as zero. |
| The loop stops at cycle 3 | A real failure, not noise | Read the first `Error` line; fix it; start the loop again from cycle 1. |

## Claims register

All reads were read-only requests on **2026-10-22** unless a different date is shown.

| Claim | Source | Status |
|---|---|---|
| Bundled-plan CPU droplets are billed per second, minimum 60 seconds or $0.01 (whichever is higher), usage capped at 672 hours (28 days) a month; billing starts at create and ends at destroy; powered-off bundled droplets are still billed because compute stays reserved | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) (page marked "Last verified 25 Aug 2026") | Read |
| The hourly rate of `s-1vcpu-512mb-10gb` | Not read from any vendor page. The script divides the monthly price by 672 | **est.** |
| `s-1vcpu-512mb-10gb` is $4 and `s-1vcpu-1gb` is $6 a month | `docs/cost-prices.json`, retrieved 2026-10-21 | Read in this repository. Availability of the $4 size is not recorded for `tor1` in `docs/cost.md` |
| A spend alert budget "is not a spending cap" | [Spend alerts](https://docs.digitalocean.com/products/billing/billing-alerts/) ("Last verified 19 Oct 2026") | Read |
| Destroying a droplet does not destroy its automated backups (they stay four weeks); snapshots, volumes and volume snapshots are only destroyed if selected | [Destroy a Droplet](https://docs.digitalocean.com/products/droplets/how-to/destroy/) ("Last verified 13 Jul 2026") | Read |
| Tags are custom labels for droplets and other resources; cloud firewalls are free and block all traffic not expressly permitted | [Tag Droplets](https://docs.digitalocean.com/products/droplets/how-to/tag/) and [Create a firewall](https://docs.digitalocean.com/products/networking/firewalls/how-to/create/) | Read. Which resource types take tags: not checked, **est.** |
| `doctl` flags used: `compute droplet list --tag-name --format --no-header`, `compute droplet delete --tag-name --force`, `compute tag list/delete`, `compute firewall list/delete`, `vpcs list/delete`, `compute volume list`, `compute snapshot list`, `compute reserved-ip list`, `compute size list`, `account get` | [doctl reference](https://docs.digitalocean.com/reference/doctl/reference/) pages for each (generated 15 Oct 2026, doctl v2.0.0) | Flag names read; never run (no `doctl` on the author's machine). `--force` on firewall, vpcs and tag delete not confirmed, **est.** |
| `GET /v2/droplets?tag_name=` filters by tag and needs the `tag:read` scope | [DigitalOcean OpenAPI source](https://github.com/digitalocean/openapi/blob/main/specification/resources/droplets/droplets_list.yml) | Read; not called |
| `terraform_remote_state` reads root module outputs, needs access to the entire state snapshot, and does not respect the sensitivity of the source state; publishing explicitly to a separate location is recommended | [OpenTofu: terraform_remote_state](https://opentofu.org/docs/language/state/remote-state-data/) | Read |
| Local state is plain-text JSON; state may contain sensitive values | [OpenTofu: sensitive data in state](https://opentofu.org/docs/language/state/sensitive-data/) | Read |
| Spacelift stack dependencies respect tracked runs only; output references use outputs of a successful run that included an apply and map to environment variables (`TF_VAR_` for OpenTofu); sensitive-output transfer must be enabled; dependencies do not manage creating or deleting stacks | [Spacelift stack dependencies](https://docs.spacelift.io/concepts/stack/stack-dependencies) | Read. Whether a destroy run is ordered by a dependency was **not tested** |
| The lab behaves as shown (five cycles clean; the wrong-order error; the tag search missing an untagged file) | Run on Linux, OpenTofu 1.12.6, `hashicorp/local` 2.9.1, 2026-10-22 | Run |
| The cloud stacks are valid for the provider's schema | `tofu validate` with `digitalocean/digitalocean` 2.106.0, 2026-10-22 | Validated; never planned or applied |
| This project's stack layout, cost gate, golden addresses, destroy guard and stack-factory status | Files in this repository at the commit this page was written against | Read |
| Everything PowerShell; WSL as a way to run the generator; tag policies on other providers | Written from documentation or general knowledge | **est.**, not verified |

Not verified, plainly: the whole PowerShell track; the cloud path from start to finish (including whether a new droplet is covered by a tag-attached firewall from its first second, and whether the $4 size is offered to your account and region); `--force` on three `doctl` delete commands; which DigitalOcean resource types accept tags; whether an organization-wide tag policy exists on DigitalOcean; whether a Spacelift destroy run is ordered by stack dependencies.

Next: [Teardown checklist](Teardown-Checklist.md), the project's own version of the destroy order and the proof, with the destroy guard in front of it.
