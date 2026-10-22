# Spacelift from zero: your first stack, run and teardown

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Lesson I3 of the four-lesson infrastructure-as-code track. The track: I1 [OpenTofu from zero: init, plan, apply, destroy](OpenTofu-From-Zero.md), I2 [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md), **I3 this page**, I4 [Build and destroy a stack per service](Build-and-Destroy-Stack-Per-Service.md). A foundations side page to [Spacelift](Spacelift.md); no step of the core path is renumbered.

> **Status: written from vendor documentation; the free local exercises were run once, the Spacelift console exercises were not.** On **2026-10-22** the author read the Spacelift pricing and documentation pages listed in the [claims register](#claims-register) with read-only `curl`, and ran the free local exercises (Exercises 1 and 2) on Linux with OpenTofu 1.12.6, pasting trimmed output from that run. The own-account path (Exercises 3 to 11) uses menu names as the documentation gave them that day; **nobody has run it against a real Spacelift account for this page**, so every console step, every message it shows and every statement about what the free plan lets you do is marked **est.** unless the claims register says it was read. Vendor pages change; if your screen disagrees, trust your screen and the vendor's current page, and tell the project (see [Give feedback and open an issue](Give-Feedback-and-Open-an-Issue.md)). Windows PowerShell commands are **est.** (not run; no PowerShell was available when this was written).

> **Prerequisites.** [OpenTofu from zero](OpenTofu-From-Zero.md) (I1) and [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) (I2), or the same ideas from [What is infrastructure as code](What-Is-Infrastructure-as-Code.md): plan, apply, state. [Git from zero](Git-From-Zero.md) for branches, commits and pushes, and [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) for pull requests. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). The free theory path needs no account. The own-account path needs a GitHub account and a Spacelift account, both yours. About 90 minutes for reading and the free local exercises (est.); the own-account path adds about three hours (est.), most of it waiting for runs and clicking.

> **I1, I2 and I4 are written at the same time as this page by other authors.** If one of those links is dead when you read this, the lesson has not merged yet. This page does not depend on their text; it repeats the three words it needs (plan, apply, state) where it uses them.

## Read this first: what this lesson touches, and what it never touches

- **It never touches the maintainer's Spacelift account or this repository's stacks.** This project runs `cah-00-foundation`, `cah-10-access` and `cah-20-telemetry` in the maintainer's own Spacelift account. They are **locked and manual on purpose**: deletion protection on, autodeploy off, a human confirms every apply. You do not need access to them for anything here, you cannot get it from this page, and you should never ask for it. Everything below happens in a Spacelift account **you** create, against a scratch GitHub repository **you** create.
- **No cloud, no cloud bill.** The scratch stacks use only OpenTofu's built-in `terraform_data` resource, which records a value in state and creates nothing anywhere. There is no provider to download and no credential to hold. (The `random` and `local` providers are also free and need no cloud account, but they are downloaded from a public registry, so this page keeps to `terraform_data`.)
- **Nothing here uses this project's tokens.** The project's secrets live in Doppler and reach its stacks through a hook ([Doppler and secrets](Doppler-and-Secrets.md)). Your scratch stacks need no secret of that kind. The one secret-shaped thing you will make is a throwaway value in a Spacelift environment variable, and you will build it at run time.
- **This page names Spacelift because the project uses it.** It states no affiliation with Spacelift or any other vendor named here, and none is known. It is not an endorsement or a comparison test: other tools can do this job (next section).

## What you will be able to do

- Say in plain words what a hosted infrastructure-as-code runner is, what Spacelift adds to `tofu plan` and `tofu apply`, and name the other kinds of tool that do a similar job.
- State the plan limits that matter to a learner (what the free plan is said to include, what needs a higher plan, what needs a private worker) and say where you read them and when.
- Connect a GitHub repository to Spacelift with the least access that works (one repository, not all of them).
- Create a stack, point it at a project root, choose OpenTofu and a version, and explain what each setting does.
- Tell a **proposed run** (a preview, triggered by a branch or pull request) from a **tracked run** (a deployment, triggered by a push to the tracked branch), walk through the phases of a run, and **confirm** or **discard** one.
- Set an environment variable and a secret variable on a stack, explain what a context is, and say why this project keeps secrets in Doppler and not in Spacelift variables.
- Read a plan policy and a push policy written in Rego, and say what each can and cannot stop.
- Chain two stacks with a dependency and an output, and know why drift detection and scheduled runs sit behind a higher plan.
- **Destroy before you delete, in the right order**, and prove nothing is left; then tear down the integration itself.
- Run a build-and-destroy loop over several scratch stacks with a checklist that proves the account and the repository are empty at the end.

## What a hosted runner is, and the alternatives

You already know the loop from I1: `tofu plan` shows what would change, `tofu apply` makes it so, and **state** is the file where OpenTofu remembers what it built. On your laptop all three live on one machine, under one person's credentials, and nobody else sees a plan before it applies.

A **hosted runner** (Spacelift is one) moves that loop onto a service. You push code to Git; the service checks out the code on a **worker** (a container the service starts for the run), runs `tofu plan`, **holds the state** for you, shows the plan, **waits for a person to approve**, then applies. It also gives you history (who ran what, when), permissions, and a place to attach rules written as code.

What that buys, in order of how much it matters to a beginner:

1. **A plan that someone reads before it applies.** The service stops after planning and shows the difference.
2. **Credentials in one place.** The cloud token is on the service, not on every laptop and in every CI job.
3. **State that is not on your laptop.** Lose the laptop, keep the state.
4. **A record.** Every run is listed, with its commit and who confirmed it.

What it costs: a dependency on another company's service, a second place where access must be managed, and a new set of words. [Spacelift](Spacelift.md) explains why this project chose one; this page teaches you to use one.

**Alternatives, named without a ranking.** None was tested for this page, and no price or limit for them was read. Other hosted services that run OpenTofu or Terraform include HCP Terraform (HashiCorp), env0 and Scalr. Self-managed options include Atlantis, which runs on a server you operate and comments on pull requests, and a plain CI system (GitHub Actions, GitLab CI) running `tofu` with a state bucket you provide. [Why I picked these tools](Why-I-Picked-These-Tools.md) is the project's reasoning; check each vendor's current terms yourself before you decide, because terms change.

## Plans, workers and limits, as read on 2026-10-22

Read from [spacelift.io/pricing](https://spacelift.io/pricing) with `curl` on **2026-10-22**:

| What | What the page says | What it does not say |
|---|---|---|
| Free plan | "Always free for small teams. No credit card, no time limit." It includes 2 users and 1 public worker. | How many stacks, runs or run minutes it allows. Which features of the comparison table the free plan has: the table has no column for it. |
| Higher plans | Starter+, Business, Enterprise and Enterprise+, by quote ("Request a quote"), no prices listed. | Any dollar figure. This page therefore states none. |
| Public worker | Spacelift runs it in a shared pool; each run is its own isolated container. | |
| Private worker | A worker you host in your own cloud; Starter+ and above. | |
| Drift detection | Listed as included from Starter+ on the pricing page. | |

Read from the documentation (`docs.spacelift.io`) on the same day:

| Feature | Documentation says | Consequence for you |
|---|---|---|
| Policies (Rego) | "This feature is only available to paid Spacelift accounts." ([policy page](https://docs.spacelift.io/concepts/policy/)) | On the free plan you can read policies and test them on your own computer, but this page expects you cannot attach them. Confirm in the console. |
| Drift detection | "Only available on the Starter+ plan and above." "Drift detection only works on private workers." ([drift page](https://docs.spacelift.io/concepts/stack/drift-detection)) | Read-only for you. |
| Scheduling (tasks, runs, scheduled stack deletion) | "Only available on the Business plan and above." Schedules on public workers do not trigger. ([scheduling page](https://docs.spacelift.io/concepts/stack/scheduling)) | Read-only for you. |
| Targeted replan | "Only available to Business plan and above." | Not used. |
| Stack dependencies, contexts | Documented with no plan note on their pages. The pricing comparison lists them but shows no Free column. | **Unconfirmed for the free plan.** Exercises 7 and 8 say what to do if your account lacks them. |
| Audit trail | Listed under Enterprise on the pricing page. | Not available to you; the run list is your record. |

Two honesty notes. First, the documentation's signup instruction says to click **Free trial** at the top right of the home page, and the pricing page's free-plan banner links to the same address, while the pricing page text calls the free plan "no time limit". Whether you get a time-limited trial of a higher plan or the free plan after signing up is **something to read on your own screen** (Exercise 3); if you are offered a card form, stop and read before you enter anything. Second, the product the documentation calls "Spacelift Deploy" is the same thing this project calls Spacelift; the documentation says the name changed when "Spacelift Flows" was added. This page uses "Spacelift".

**Cost.** Per [docs/cost.md](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md), the project's own Spacelift wiring is a $0 line (stage 0). For your scratch account, the figure to hold is: **$0 if you stay on the free plan and enter no payment card; you control the card, so you control the bill.** A GitHub account and a scratch repository are free. No cloud resource exists, so no cloud bill can.

## The pieces, in the order you meet them

Each paragraph names a Spacelift word, says what it is, and says what to look for.

**Source control integration.** Spacelift needs to read your repository and report back on commits and pull requests. For GitHub that is a **GitHub App**: a small program GitHub lets you install on your account, with a list of permissions you can read before you accept. The documentation lists the permissions of the custom-app route: repository Checks, Commit statuses, Deployments, Pull requests and Webhooks at read and write; Contents and Metadata read-only; organization Members read-only. The point for you is the choice at install time: **all repositories or only selected ones.** Choose selected, and select the scratch repository only. That is least privilege: if the app, or Spacelift, is ever compromised, the damage stops at one disposable repository.

**Stack.** The documentation defines it as source code, the current state of the managed infrastructure, and configuration (environment variables and mounted files), "an isolated, independent entity". One stack, one state. This project has one stack per directory under `stacks/`. A stack with no runs shows the state "None".

**Project root.** The folder in the repository where the stack's code lives. It matters twice: it tells the worker where to run `tofu`, and it tells Spacelift which pushes affect this stack (per this project's [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md), which read Spacelift's documentation on 2026-10-12, a push that changes only files outside the project root and outside the **project globs** you add does not start a run for it). Wrong project root is the most common first failure ("no configuration files").

**Vendor and version.** You choose OpenTofu (a dedicated vendor in the documentation) or Terraform (FOSS), and a version or a range such as `~> 1.10`. The documentation says the version is required and "latest" is rejected. The same page says that when you create a stack and choose **Manage State**, Spacelift holds the state, and that creation is the only time you can ask Spacelift to be the state backend ("This is the only time you can ask Spacelift to be the state backend for a given OpenTofu stack"). Leave it on for this lesson. This project's stacks use the Terraform vendor with the OpenTofu workflow tool; see [Spacelift](Spacelift.md#opentofu-inside-spacelift) for why.

**Tracked branch.** The branch a stack deploys from, normally `main`. A push to it starts a **tracked run**; a push to any other branch starts a **proposed run**, by default.

**Proposed run.** A preview. The documentation: "previews of changes that would be applied", triggered by Git push events to branches other than the tracked branch, for each affected stack. It runs the planning phase and stops. It reports in the pull request as a commit status and a comment. It never applies.

**Tracked run.** A deployment: it plans, and if there are changes it can apply. Triggered by a person, by a push to the tracked branch, or by a trigger policy. If the plan shows no change, the run is a **no-op** and finishes without an approval step.

**The phases.** In the order you will see them in the run view (the full list is on the [run page](https://docs.spacelift.io/concepts/run/)):

| Phase | What happens | Passive? |
|---|---|---|
| Queued | Waiting for a worker or for another run to release the stack's lock. Only one run changes a stack's state at a time. | yes |
| Preparing | Spacelift hands the job to a worker. | |
| Initializing | The worker runs before-init hooks, then `tofu init`. | |
| Planning | The worker runs `tofu plan`; plan policies (if any) are evaluated. | |
| Unconfirmed | The plan is done and shows a change; nothing happens until a person acts. | yes |
| Confirmed | A person accepted the plan; waiting for a worker. | yes |
| Applying | The worker runs `tofu apply`. | |
| Finished | Done. Also the end of a proposed run or a no-op. | terminal |
| Discarded | A person rejected the plan, or an unconfirmed run waited too long. | terminal |
| Failed | Something broke: bad code, a hook, a policy `deny`, an apply error. | terminal |

"Passive" is the documentation's word for a state where "no operations are performed". Timeouts worth knowing: an unconfirmed run with no change for 7 days becomes discarded, and any run not finished in 30 days is closed by Spacelift (read from the run page, 2026-10-22).

**Confirm and discard.** In the Unconfirmed state the run page shows the plan and two buttons. Confirm means "apply exactly this". Discard means "stop, change nothing". Autodeploy, when on, skips this step if there are no plan-policy warnings; that is why this project leaves it off ([Why autodeploy is off](Spacelift.md#why-autodeploy-is-off)).

**Environment variables.** Set per stack, on its Environment tab. A variable named `TF_VAR_x` becomes the OpenTofu input variable `x`. You can mark a variable **secret**: its value is then hidden in the console and the API, and you cannot read it back, only replace it.

**Contexts.** A context is a bundle of environment variables, mounted files and hooks, kept apart from any stack and attached to as many stacks as you like. The `autoattach:<label>` label on a context attaches it to every stack that has the matching label. This project's `cah-doppler` context works exactly this way ([Spacelift and Doppler runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md)).

**Secrets, and why Doppler is separate here.** A secret variable in Spacelift is simple and, for a throwaway value, fine. This project does not put its real secrets there. [Doppler and secrets](Doppler-and-Secrets.md) gives the reasons: one place to rotate (change the value in Doppler and the next run picks it up, with no hunting through CI settings and stack variables); Spacelift holds exactly one secret, a read-only service token scoped to one config, so a leak reaches only those values; and the same pattern is used across the author's other repositories. A hook script then fetches only the names each stack lists in a reviewed file (`.spacelift/config.yml`), so what a stack may read is a change someone reviews, not a click in a console. The trade-off is one more moving part. For your scratch stacks, a plain secret variable is the lesson; for anything real, read the Doppler page first.

**Policies.** Rules written in **Rego**, the language of Open Policy Agent. Spacelift runs a policy at a decision point and acts on what it returns. The ones this page uses: a **plan policy** reads the plan and can `deny` (fail the run) or `warn` (flag for a human); a **push policy** reads a Git event and decides `track`, `propose` or `ignore`; an **approval policy** decides who may approve a run and how many approvals it needs. Others exist (login, notification, trigger). Policies are created in the Spacelift console, not read from your repository: the repository file is only the reviewed copy. For the full contract of every input and rule, see the [policy documentation](https://docs.spacelift.io/concepts/policy/) and the policy-writing skill's references.

**Stack dependencies and outputs.** A stack can depend on another so it runs after it. A stack can also **reference an output** of the stack it depends on and receive it as an environment variable (use the `TF_VAR_` prefix for OpenTofu). The documentation notes: dependencies only respect tracked runs; the referenced output must already exist from a successful tracked run that applied; and **a stack that has downstream dependents cannot be deleted until those are deleted** ("First child, then parent").

**Drift detection and scheduled runs.** Drift is the difference between what the code says and what exists, usually because someone changed something by hand. Spacelift's drift detection runs proposed runs on a schedule and can start a tracked run to fix what it finds. It needs a higher plan and a private worker, so on the free plan it is a thing to understand, not to run. Detecting drift with your own commands is I2's subject.

**Spacectl.** Spacelift's command-line client. The documentation describes it as wrapping the GraphQL API for "limited functionality for creating or editing resources"; creating stacks is done in the console or with the Spacelift Terraform provider (that is I4's subject). Commands the documentation shows: `spacectl profile login`, `spacectl stack list`, `spacectl stack deploy --id <stack>` and `spacectl stack local-preview --id <stack>`. Others exist (`spacectl --help` lists them); this page uses only the ones it read.

## Why this project's proposed-run check is red by design

If you open a pull request in this repository that changes a stack's files, you may see a red `spacelift/...` check next to the green `CI green`. That is **expected, and it does not block the merge**, and the reason is a chain of three deliberate choices:

1. This repository is **public**. A proposed run executes code from the pull request (provider configuration and data sources can run lookups). So the project's hook script ([Doppler and secrets](Doppler-and-Secrets.md)) refuses to fetch any secret unless the run is a tracked or destroy run on `main`.
2. With no secret fetched, a proposed run cannot talk to DigitalOcean. It starts, reaches the provider, and fails.
3. The tool that would stop Spacelift starting that run at all is a **push policy**, and policies need a higher plan than the free one. Where it is not attached, the narrowest the project can do is set each stack's project root and globs so a docs-only pull request starts nothing; a pull request that changes a stack still gets a proposed run that fails. Branch protection on `main` requires only `CI green`, so the red check informs and does not stop a merge. The same trade-off is written in full at [Push policies: paid plan versus free plan](Spacelift.md#push-policies-paid-plan-versus-free-plan), and the story of the first such red check is in [Lessons learned](Lessons-Learned.md).

Notice the contrast with your own scratch repository below. Your stacks need no credential, so a proposed run for a pull request in your scratch repository **succeeds and shows a plan**. Red here, green there, same Spacelift feature: the difference is whether the run needs a secret it is not allowed to have. Whether the maintainer's account currently has a push policy attached cannot be told from this repository; the page does not claim either way.

## Free theory path: build and run the scratch stacks on your own computer

Before any account, build the exact code the stacks will use and run it locally with OpenTofu. If you have not installed OpenTofu, I1 shows how; check with `tofu version`. These exercises touch no network and no account.

### Exercise 1: build three scratch stacks and run one by hand

**Predict.** A stack that contains one `terraform_data` resource and an output: when you apply it, how many resources does OpenTofu say it created, and what does the output print? After a destroy, what does it say?

**Do.** Save the generator, run it, and run the first stack.

Bash (run on Linux, 2026-10-22):

```bash
mkdir -p ~/iac-scratch-tools && cat > ~/iac-scratch-tools/make-scratch.sh <<'EOF'
#!/usr/bin/env bash
# Usage: bash make-scratch.sh DIRECTORY [STACK_NAME ...]
# Builds one tiny OpenTofu stack per name, using only the built-in
# terraform_data resource: no provider download, no cloud, no account.
set -euo pipefail
root="${1:?usage: make-scratch.sh DIRECTORY [STACK_NAME ...]}"
shift || true
names=("$@")
[ "${#names[@]}" -gt 0 ] || names=(a-base b-app c-extra)

mkdir -p "$root"
cd "$root"
printf '%s\n' '.terraform/' '*.tfstate' '*.tfstate.*' 'crash.log' '*.tfvars' > .gitignore

for name in "${names[@]}"; do
  case "$name" in
    *[!a-z0-9-]*|'') echo "bad stack name: $name (use a-z, 0-9 and -)" >&2; exit 2 ;;
  esac
  mkdir -p "stacks/$name"
  cat > "stacks/$name/main.tf" <<HCL
terraform {
  required_version = ">= 1.6.0"
}

variable "greeting" {
  type    = string
  default = "hello from $name"
}

resource "terraform_data" "note" {
  input = var.greeting
}

output "greeting" {
  value = terraform_data.note.output
}
HCL
done
echo "built ${#names[@]} stacks in $root"
EOF
bash ~/iac-scratch-tools/make-scratch.sh ~/cah-scratch
cd ~/cah-scratch/stacks/a-base
tofu init -input=false
tofu apply -auto-approve -input=false
tofu output greeting
tofu state list
tofu destroy -auto-approve -input=false
```

PowerShell (est., not run). First save this as `make-scratch.ps1` in a folder named `iac-scratch-tools` in your home folder (use any editor; the file is the whole block):

```powershell
param([Parameter(Mandatory)][string]$Root, [string[]]$Names = @('a-base','b-app','c-extra'))
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Set-Location $Root
Set-Content -Path .gitignore -Value @('.terraform/','*.tfstate','*.tfstate.*','crash.log','*.tfvars')
$template = @'
terraform {
  required_version = ">= 1.6.0"
}

variable "greeting" {
  type    = string
  default = "hello from NAME"
}

resource "terraform_data" "note" {
  input = var.greeting
}

output "greeting" {
  value = terraform_data.note.output
}
'@
foreach ($n in $Names) {
  if ($n -notmatch '^[a-z0-9-]+$') { throw "bad stack name: $n" }
  New-Item -ItemType Directory -Force -Path "stacks/$n" | Out-Null
  Set-Content -Path "stacks/$n/main.tf" -Value $template.Replace('NAME', $n)
}
"built $($Names.Count) stacks in $Root"
```

Then run it and the stack:

```powershell
& "$HOME/iac-scratch-tools/make-scratch.ps1" -Root "$HOME/cah-scratch"
Set-Location "$HOME/cah-scratch/stacks/a-base"
tofu init -input=false
tofu apply -auto-approve -input=false
tofu output greeting
tofu state list
tofu destroy -auto-approve -input=false
```

**Check.** Bash output, trimmed, from the 2026-10-22 run: the generator prints `built 3 stacks in ...`. `tofu init` succeeds with no provider downloaded (the resource is built in). The apply finishes with `Outputs:` and `greeting = "hello from a-base"`. `tofu output greeting` prints `"hello from a-base"`, `tofu state list` prints `terraform_data.note`, and the destroy ends `Destroy complete! Resources: 1 destroyed.` (Colors and spacing vary by terminal.)

**Undo.** The destroy already ran. Remove the local files if you like: `rm -rf ~/cah-scratch` (PowerShell: `Remove-Item -Recurse -Force "$HOME/cah-scratch"`). The tools folder `~/iac-scratch-tools` is reused later. In the PowerShell version, the script is saved in `iac-scratch-tools` in your home folder.

### Exercise 2: read the rules before any account exists

You have two real policies to read in this repository: the push policy [`.spacelift/policies/push.rego`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/.spacelift/policies/push.rego) and the plan policy [`.spacelift/policies/plan.rego`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/.spacelift/policies/plan.rego). Each has a test file next to it.

**Predict.** In the push policy, which three rule names does the file define or mention, and which one does it deliberately never define? What does that mean for a pull request?

**Do.** Read `push.rego` from the top. Find the rule names `track` and `ignore`, and the comment that starts "Deliberately absent".

**Check.** `track` holds when the push is to the stack's tracked branch, is not a tag, and touches a file under the stack's project root or under `modules/`, `scripts/spacelift/` or `.spacelift/`. `ignore` is defined as "not track". `propose` and `allow_fork` are deliberately absent, so **no event ever proposes a run**: that is the "no red check on pull requests" design, and it also means no pull request's code runs in Spacelift next to the secrets context. (This is what the project's wiki says about the file; reading it yourself is the exercise.)

**Optional, if you have OPA installed** (the project's CI uses OPA 1.21.0; this page's author did not have it, so this is **est.**):

```bash
opa test .spacelift/policies -v
```

**Undo.** Nothing to undo; reading changes nothing.

Now a **teaching plan policy** you will use in Exercise 9. It denies any plan that would delete a resource. It is written against the input shape the documentation shows (`input.terraform.resource_changes[].change.actions`) and the Rego-v1 form with `import rego.v1`; it is **est.** until you run it, because OPA was not available to test it:

```rego
package spacelift

import rego.v1

# Deny a plan that deletes anything. For a scratch account this teaches the
# shape of a plan policy; it would be far too blunt for a real stack.
deny contains msg if {
	some change in input.terraform.resource_changes
	"delete" in change.change.actions
	msg := sprintf("blocked: %s would be deleted", [change.address])
}
```

## Optional: your own Spacelift account and scratch repository

> **Status of this path: written from the documentation, never run.** Console menu names are as the documentation gave them on 2026-10-22 and may have moved. Use your own accounts only. If anything is unclear, stop at the end of the step you are on and read the vendor page again; nothing here is urgent.

### Cost and teardown (read first)

- **Cost.** $0 on the free plan with no payment card entered (pricing page, retrieved 2026-10-22). If you are offered a trial of a higher plan, a card form or a quote, stop: that is not this lesson.
- **Teardown, in this order** (each step is repeated at the end with proof):
  1. In Spacelift, for every scratch stack: run a destroy, check the resources are gone, turn off deletion protection, delete the stack.
  2. Delete your contexts, API keys and any other Spacelift objects you made.
  3. In GitHub, uninstall the Spacelift app from your account (or remove the scratch repository from its selection), then delete the scratch repository.
  4. Spacelift account closing: the documentation pages read for this lesson say nothing about deleting an account. With the free plan and no card, an empty account costs nothing; if you want it closed, ask Spacelift support (est.).
- **Never leave stacks with resources in them.** Here the resources are only state entries, but the habit is the point: the same order protects a real bill.

### Exercise 3: sign up and read your plan

**Predict.** After signup, will the console tell you which plan you are on, and will it ask for a card?

**Do.**

1. Open `https://spacelift.io/pricing`, find the free-plan banner, and follow its link (the documentation names the button **Free trial**; the page text says free, no card, no time limit).
2. Choose the data region the form offers (the documentation lists Europe or United States). Pick the closer; it is a hosting choice, not a security one.
3. Sign in with a GitHub, GitLab, Google or Microsoft account you own. The documentation notes that if you sign in with GitHub, the GitHub organization or account name becomes your Spacelift account name, so use a **personal** account you are happy to see in a URL, not an employer's.
4. You land on the LaunchPad, which has Learn missions, a knowledge base, videos and an FAQ. Find where the console shows your plan or usage (the documentation says usage lives under Organization Settings, then Other, then Usage).

**Check.** You can state, in one sentence, which plan you are on and whether a card is on file. If a trial of a higher plan is shown with an end date, write the date down and remember the teardown must finish before it.

**Undo.** Nothing yet. If you do not want to continue, close the tab; no resource exists.

> **Screenshot to take yourself:** the console page that shows your plan or usage.
> Capture: the plan name and any limit shown, with no card details.
> Look for: a plan name, a number of users and workers, an end date if it is a trial.
> Redact: your account name in the header and address bar, your email, any billing information.

### Exercise 4: create the scratch repository and connect it, with the least access

**Predict.** If you install the Spacelift GitHub App on "all repositories", what can it read? If you select one repository, what can it read?

**Do.**

1. Create a **new private repository** in your own GitHub account named for what it is, for example `iac-scratch`. Private, because stacks and run logs reference it; empty is fine. (`gh repo create iac-scratch --private --clone` does the same from a terminal, est.)
2. Build the three stacks into a clone and push to `main`:

```bash
git clone https://github.com/YOUR_USER/iac-scratch.git ~/iac-scratch
bash ~/iac-scratch-tools/make-scratch.sh ~/iac-scratch
cd ~/iac-scratch
git add -A
git commit -m "scratch stacks a-base b-app c-extra"
git push origin HEAD:main
```

```powershell
git clone https://github.com/YOUR_USER/iac-scratch.git "$HOME/iac-scratch"
& "$HOME/iac-scratch-tools/make-scratch.ps1" -Root "$HOME/iac-scratch"
Set-Location "$HOME/iac-scratch"
git add -A
git commit -m "scratch stacks a-base b-app c-extra"
git push origin HEAD:main
```

(`git add -A` is safe here: this folder holds only what the generator wrote. Replace `YOUR_USER` with your GitHub name. If your default branch is not `main`, use its name.)

3. In Spacelift, add the GitHub integration. The documentation says: if you created the account with GitHub, install the Spacelift GitHub App from the GitHub Marketplace and **select the repository or repositories to manage**; if you used another sign-in, create a custom GitHub app through the wizard (Integrate Services, then View on the GitHub card, then Set up GitHub, then Set up via wizard). In the install step, choose **Only select repositories** and tick `iac-scratch` and nothing else.
4. In GitHub, open the app's installation settings and confirm the repository list shows only the scratch repository.

**Check.** GitHub's installed-apps page lists the Spacelift app with exactly one repository. A GitHub App with access to all repositories could read every private repository you own; this one can read one you were about to throw away.

**Undo.** In GitHub, Settings, Applications, Installed GitHub Apps, then Configure or Uninstall on the Spacelift app ([GitHub's page on reviewing and modifying installed apps](https://docs.github.com/en/apps/using-github-apps/reviewing-and-modifying-installed-github-apps), read 2026-10-22). Uninstalling removes the app's access to that account's resources.

> **Screenshot to take yourself:** GitHub's page for the installed app.
> Capture: the repository access section showing "Only select repositories" and the one repository.
> Look for: exactly one repository listed.
> Redact: your username and any other repository names.

### Exercise 5: create the first stack, run it, confirm it

**Predict.** With the stack set to autodeploy off, a push to `main` that changes a stack's folder will run through which phases, and where will it stop? How many resources will the plan say it adds?

**Do.**

1. In Spacelift, Ship Infra, Stacks, **Create stack** (the documentation's path; the LaunchPad has a Create first stack button). Fill in:
   - Name: `scratch-a-base`. Space: the default. Labels: `scratch` (so you can find and clean them all later).
   - Source: your integration, repository `iac-scratch`, branch `main`, **project root `stacks/a-base`**. Leave project globs empty.
   - Vendor: **OpenTofu**, a current version or a range such as `~> 1.10` (the documentation's example), **Manage State on**.
   - Behavior: worker pool default (the public workers), **Autodeploy off**, **Protect from deletion on** (you will have to turn it off in Exercise 10; that is the lesson), local preview off.
   - Skip roles, hooks, cloud integrations, policies and contexts for now.
2. Open the stack and press **Trigger**. This makes a tracked run.
3. Watch the run view move through Preparing, Initializing, Planning, and stop at **Unconfirmed** with a plan summary.
4. Read the plan summary, then press **Confirm**. Watch Confirmed, Applying, Finished.

**Check.** The plan summary shows 1 resource to add (and an output, est.). After finishing, the stack's state label reads Finished. Open the stack's resources view and find `terraform_data.note` (the name of that tab is est.). Find the output `greeting` with the value `hello from a-base` on the stack (where outputs are shown is est.).

**Undo.** Leave it; Exercise 10 destroys it properly. If you want to practice the other branch of the decision, trigger another run after changing the greeting (Exercise 6) and press **Discard** instead of Confirm: the run goes to Discarded and nothing changes.

> **Screenshot to take yourself:** the run view at the Unconfirmed step.
> Capture: the plan summary and the Confirm and Discard buttons.
> Look for: "1 to add" and the two buttons.
> Redact: your account and stack names if you share it, the commit author and email.

### Exercise 6: proposed run versus tracked run, with a real pull request

**Predict.** You push a branch and open a pull request that changes the greeting in `stacks/a-base/main.tf`. Does Spacelift start a run? What kind? Will it apply? Will the check be green or red, given what the "red by design" section said?

**Do.**

```bash
cd ~/iac-scratch
git switch -c change-greeting
sed -i 's/hello from a-base/hello again from a-base/' stacks/a-base/main.tf
git commit -am "change the greeting"
git push -u origin change-greeting
```

```powershell
Set-Location "$HOME/iac-scratch"
git switch -c change-greeting
(Get-Content stacks/a-base/main.tf) -replace 'hello from a-base','hello again from a-base' | Set-Content stacks/a-base/main.tf
git commit -am "change the greeting"
git push -u origin change-greeting
```

(`sed -i` as written is GNU sed; on macOS use `sed -i ''`.) Open the pull request on GitHub. Then look at the pull request's checks and at the stack's run list in Spacelift.

**Check.** Expect a **proposed run** on `scratch-a-base` (the documentation: a push to a branch other than the tracked one starts one by default), a status check named for the stack or `spacelift/proposed` (the documentation names `spacelift/tracked`, `spacelift/proposed` and `spacelift/modules` as grouped check names for the aggregate option; the exact name you see depends on your integration's settings), a comment with the plan, and a **green** result: your stack needs no credential, so planning succeeds. The run stops after planning and never offers Apply. Now merge the pull request. A **tracked run** starts on `main`, stops at Unconfirmed, and this time the plan says 1 change. Confirm it. (Whether the proposed run starts at all on the free plan is **est.**; the documentation describes the default behavior without a plan note.)

**Undo.** Delete the branch on GitHub after merging, and locally: `git switch main && git pull && git branch -d change-greeting`.

### Exercise 7: environment variables, secrets and a context

**Predict.** If you mark a variable secret and then open the Environment tab, can you read its value? If you set `TF_VAR_greeting` on the stack, what does the next plan do?

**Do.**

1. Build a throwaway value at run time, not one you invent and type into a file. Bash: `openssl rand -hex 8`. PowerShell (est.): `-join ((1..8) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })`. Do not paste the value into chat, a screenshot or a commit.
2. On `scratch-a-base`, open **Environment**, **Add variable**: name `TF_VAR_greeting`, value `set from the environment`, not secret. Trigger a run. The plan should show the greeting changing.
3. Add a second variable: name `SCRATCH_SECRET`, the random value, **Mark as secret** on. Open the Environment tab again.
4. Create a **context**: Share code and config, Contexts, **Create context**, name `scratch-context`, label `autoattach:scratch`, add a variable `SCRATCH_SHARED` = `shared` (not secret). The stack has the label `scratch`, so the context should attach itself. Open the stack's Contexts tab to confirm.

**Check.** The secret's value is not shown (the documentation: secret values "will not be visible in the Spacelift UI or via the API"), and you can only replace it. The plain variable is shown. The context appears on the stack's Contexts tab with its priority. The synthetic Environment view lists what the run will "see" (the documentation's phrase).

**Undo.** Delete the variables: three dots next to each, Delete. Delete the context from the Contexts list. Detach is not needed if you delete it.

> **Screenshot to take yourself:** the Environment tab with one plain and one secret variable.
> Capture: both rows, with the secret row showing no value.
> Look for: the plain value visible and the secret value hidden.
> Redact: nothing secret appears; crop your account name if you share it.

### Exercise 8: a second stack, a dependency and an output

**Predict.** `b-app` has an input variable `greeting`. If `b-app` depends on `a-base` and takes the output `greeting` as `TF_VAR_greeting`, which stack must have applied first, and what happens if `a-base` has not?

**Do.**

1. Create stack `scratch-b-app` the same way as Exercise 5, project root `stacks/b-app`, label `scratch`, autodeploy off.
2. Open `scratch-b-app`, the **Dependencies** tab, add `scratch-a-base` as a dependency, and add a reference: output `greeting` of `scratch-a-base` into input name `TF_VAR_greeting` (the documentation: choose an existing output or one that will exist, and name the environment variable that receives it).
3. Trigger `scratch-a-base`. When its tracked run finishes with a change, `scratch-b-app` should queue a tracked run of its own. Confirm it.

**Check.** After the second stack applies, its output `greeting` equals the first stack's. If the free plan lacks dependencies (**unconfirmed**), the Dependencies tab will be missing or will refuse; in that case set `TF_VAR_greeting` by hand on `scratch-b-app` and note in your own words what you could not do. Either way, now try the failure the documentation warns about: on a new stack that references an output that has never been produced, the run fails with a "inputs are missing" message (the documentation's wording); do not create a stack just for that, read the page.

**Undo.** Leave both stacks for Exercises 9 and 10.

### Exercise 9: policies you can read, and perhaps attach

**Predict.** On the free plan, can you create a policy? If you can, what will the teaching plan policy do to a plan that only creates things?

**Do.**

1. In the console, look for **Enforce Guardrails**, then **Policies** (the documentation's path), and try **Create policy** with type **Plan**, body from Exercise 2. Attach it to `scratch-b-app`.
2. If the console refuses because of your plan, that is the answer to the predict step: the policy page is written for "paid Spacelift accounts". Say so in your notes and continue; there is nothing to fix.
3. If it attaches: change `b-app` so a resource is removed (for example, delete the `terraform_data` block and the output in a branch), open a pull request, and read the proposed run.

**Check.** With the policy attached, the proposed run **fails in the planning phase** with the message `blocked: terraform_data.note would be deleted` (est.: the phase and wording follow the documentation's description that `deny` fails the run). Creates and updates pass.

**Undo.** Detach and delete the policy. Close the pull request without merging and delete its branch.

### Exercise 10: destroy, then delete, in that order

This is the exercise that matters most for your bill later. The rule, from the documentation: **destroy the resources first, then delete the stack.** If you delete a stack and choose to keep the resources, the stack and its state are gone and the resources are still there, now managed by nothing, still billing if they cost money. Those are **orphans**.

**Predict.** `scratch-b-app` depends on `scratch-a-base`. Which can you delete first? What will Spacelift say if you try the other order? What does turning on "Protect from deletion" do to your attempt?

**Do.** For each stack, **child first** (`scratch-b-app`, then `scratch-a-base`):

1. Destroy the resources. Two routes from the documentation: run a **task** on the stack with the command for OpenTofu, `tofu destroy -auto-approve`; or, when you delete the stack, choose to **delete the stack's resources**, which runs a destroy run and then deletes the stack when that succeeds (stated on the scheduling page for scheduled deletion; for the manual path the delete dialog offers "delete or keep the stack's resources"). The task route lets you read the result before deleting anything.
2. Check the destroy: open the stack's resources view (no resources) and the run's log (`Destroy complete! Resources: 1 destroyed.`, est.).
3. If you want the final state file, the documentation says you can retrieve it with a task before deleting.
4. Turn off **Protect from deletion** in the stack's settings (est.: the setting's exact location is not in the pages read).
5. Delete the stack: on the Stacks tab, the three dots next to the stack, **Settings**, **Stack deletion**, choose **keep** (the resources are already gone) or **delete**, type `delete` in the box, and confirm.

Optional: do the same with the command line (est.; `spacectl` lists the stacks, and you must authenticate first with `spacectl profile login my-account`, following the documentation's option 3, the browser flow):

```bash
spacectl stack list
```

**Check.** The Stacks tab no longer lists the stack. Try to delete `scratch-a-base` **before** `scratch-b-app` once, if you still have both: the documentation says a stack with downstream dependencies cannot be deleted, and the console should refuse and name the dependent.

**Undo.** There is no undo for a deleted stack; that is the reason for the order and the typed confirmation. Recreate it from the repository if you need it again.

> **Screenshot to take yourself:** the stack deletion dialog.
> Capture: the choice between deleting and keeping the stack's resources, before you confirm.
> Look for: the two options and the box where you type `delete`.
> Redact: your account name and stack name if you share it.

### Exercise 11: tear down the integration

**Predict.** After every stack is deleted, what is still connected between GitHub and Spacelift?

**Do.**

1. Delete any context, policy, API key or other object you created (Spacelift: Share code and config, Contexts; Enforce Guardrails, Policies; any keys under your profile or organization settings).
2. In GitHub: Settings, Applications, Installed GitHub Apps, uninstall the Spacelift app from your account. Check that it no longer appears.
3. Delete the scratch repository (Settings, Danger Zone, Delete this repository).
4. Delete the local clone and tools: `rm -rf ~/iac-scratch ~/iac-scratch-tools` (PowerShell: `Remove-Item -Recurse -Force "$HOME/iac-scratch","$HOME/iac-scratch-tools"`). If you logged in with spacectl: `spacectl profile logout my-account`.

**Check.** Spacelift's stack list is empty; GitHub's installed-app list has no Spacelift entry; the repository 404s when you open its address; `spacectl profile list` shows no profile for it (est.).

**Undo.** None needed. If you want to use Spacelift again, start at Exercise 3.

## Build and destroy a bunch

Now repeat the loop until it is a habit. This is where the speed comes from: five stacks, built and destroyed in a defined order, with a checklist that proves nothing is left. It is the free-plan version of the habit I4 uses for stack-per-service work.

**Plan.** Five scratch stacks, one dependency chain, all with the label `scratch`.

| Stack | Project root | Depends on | Built | Destroyed |
|---|---|---|---|---|
| `scratch-a-base` | `stacks/a-base` | none | 1st | 5th (last) |
| `scratch-b-app` | `stacks/b-app` | `scratch-a-base` | 2nd | 4th |
| `scratch-c-extra` | `stacks/c-extra` | none | 3rd | 3rd |
| `scratch-d-extra` | `stacks/d-extra` | none | 4th | 2nd |
| `scratch-e-extra` | `stacks/e-extra` | `scratch-c-extra` | 5th | 1st |

Build order: parents before children, so each referenced output exists. Destroy order: **children before parents**, the reverse. Two stacks are standalone and can go in any order among themselves.

**Do.**

1. Rebuild the code with five names (regenerates the repository content; you recreate the scratch repository and reinstall the app per Exercise 4 if you tore it down):

```bash
bash ~/iac-scratch-tools/make-scratch.sh ~/iac-scratch a-base b-app c-extra d-extra e-extra
```

```powershell
& "$HOME/iac-scratch-tools/make-scratch.ps1" -Root "$HOME/iac-scratch" -Names a-base,b-app,c-extra,d-extra,e-extra
```

2. Create the five stacks as in Exercise 5, one at a time, labelled `scratch`, autodeploy off. Add the two dependencies as in Exercise 8 (where dependencies exist on your plan).
3. Trigger and confirm each, parents first. Write down the order and how long each took.
4. Destroy in the reverse order. For each stack: task `tofu destroy -auto-approve`, check the resources view, then turn off deletion protection and delete the stack.
5. Run the checklist.

**Checklist, tick each box after looking, not remembering.**

- [ ] The Stacks tab, filtered by label `scratch`, lists no stack.
- [ ] No context named for the scratch work remains (Share code and config, Contexts).
- [ ] No policy named for the scratch work remains (Enforce Guardrails, Policies), if your plan has the page.
- [ ] No API key or machine user you made remains.
- [ ] GitHub's installed-apps list does not show the Spacelift app, or shows it with no repository you care about.
- [ ] The scratch repository is deleted, or contains only code and no secret.
- [ ] No local state file or `.terraform` folder remains: `find ~ -name terraform.tfstate -o -name .terraform` finds nothing from this lesson (PowerShell: `Get-ChildItem -Recurse -Force $HOME -Include terraform.tfstate,.terraform -ErrorAction SilentlyContinue`).
- [ ] The billing or usage page still shows $0 and no card (or the trial end date you wrote down).

If a box fails, do not add resources to fix it: find what is left and remove it, and write down how you got there. That note is the most useful thing in the exercise.

## Build, break, detect, evade, defend

The loop the [labs](Labs-Break-It-on-Purpose.md) use, applied to the one decision this page is about: **does a human read the plan before it applies?**

- **Build.** The stack from Exercise 5: autodeploy off, a tracked branch, a human at the Unconfirmed step, and (on a higher plan) a plan policy and an approval policy attached.
- **Break.** Turn **autodeploy on** and push a change to `main`. The run goes straight from Planning to Applying with nobody reading the plan. In a scratch account this applies a `terraform_data` change; in a real account the same sequence applies a destroy. Reason it through on paper for a real stack. Do this on a scratch stack only.
- **Detect.** What shows it? In the run list, a run that applied with no Unconfirmed step and no person named as the confirmer. In GitHub, a deployment recorded without a review. A plan policy can catch it before the apply: this project's `plan.rego` has an autodeploy guard that denies a plan when the stack has autodeploy on (the plan input carries the setting). On a plan without policies, detection is you reading the run list. An audit trail is an Enterprise feature on the pricing page, so do not assume you have one.
- **Evade.** An attacker, or a hurried teammate, with write access can skip the pull request: push straight to the tracked branch, so no proposed run and no review ever sees the change; or edit the stack's settings in the console to turn autodeploy on. The policy that checks autodeploy only runs inside a plan, so it blocks the apply it would have made but does not stop the stack being created or edited that way (the same limit is written into this project's `plan.rego` header). A policy lives in the console, so someone with console admin can detach it.
- **Defend.** Layers, none sufficient alone: **branch protection on the tracked branch** (GitHub lists "Require pull request reviews before merging" and "Require status checks before merging" among the protection settings; [GitHub's page, read 2026-10-22](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)) so a direct push is refused; **autodeploy off and deletion protection on** for every stack that matters; an **approval policy** requiring a reviewer who is not the author (higher plans); a plan policy with the autodeploy and destroy guards; and **few people with console admin**. [Enterprise engineering habits](Enterprise-Engineering-Habits.md#separation-of-duties-the-thing-that-checks-is-not-the-thing-that-changes) is the principle underneath: the thing that checks is not the thing that changes.

### Flip the board

Now play the other side. Read this project's [trust boundary section](Spacelift.md#the-trust-boundary-is-spacelift-not-the-script): the hook script and `.spacelift/config.yml` are read from the branch being run, so anyone who can push a branch that triggers a run could change them. You are now the person defending a Spacelift account that runs code from Git. List, on paper, every person and every program that can (1) push to a branch your stacks track, (2) edit a stack's settings in the console, (3) change a context or a policy. For each, name the control that limits them and the evidence you would look at to see if it failed. Then, as the attacker with only one of those three powers, say which one gets you furthest. The answer in this project is the first, and the defenses against it are one writer, branch protection and the push policy that never proposes a run; that is why those are written down as the boundary and not as a property of a script.

## Common mistakes

- **Installing the GitHub App on all repositories** because it is the default-looking choice. Select the one scratch repository.
- **Wrong project root**, so the run says there is no configuration. It is the folder holding `main.tf`, relative to the repository root, with no leading slash.
- **Deleting a stack before destroying its resources**, then wondering where the resources went. Destroy, check, then delete.
- **Deleting a parent before its child** when a dependency exists; the console refuses, and the order to follow is child first.
- **Leaving autodeploy on "just for the scratch stack"**, then copying the stack's settings to a real one.
- **Treating a green proposed run as proof the apply will work.** A proposed run for a pull request reads the plan; the apply can still fail, for example on a permission the plan never needed.
- **Pasting a secret into a variable's value without marking it secret**, or into a screenshot. Mark it secret, and remember the value is not shown again.
- **Assuming a feature exists on your plan** because a page documents it. Policies, drift detection and scheduling sit behind higher plans; contexts and dependencies are unconfirmed for the free plan. Read the console before you build around one.
- **Trusting the dates on this page.** It was written on 2026-10-22. Re-read the pricing page before you rely on a limit.

## Checkpoint

You are done when you can say, without looking:

- What the difference is between a proposed run and a tracked run, and which one can apply.
- The phases of a tracked run in order, and which one waits for a human.
- Why you destroy a stack's resources before deleting the stack, and which order two dependent stacks go in.
- Why this project's proposed-run check is red by design, and why yours in the scratch repository is green.
- What a context is, why a secret variable is hidden, and why the project's secrets live in Doppler.
- Which of policies, drift detection and scheduled runs are behind a higher plan, per the pages you read.
- What you removed, in order, to leave no integration behind.

## Claims register

Read-only requests with `curl`; all retrieved **2026-10-22** unless stated. "Read" means the page text said it. Nothing was called with an API key.

| Claim | Source | Status |
|---|---|---|
| Free plan: "Always free for small teams", "No credit card, no time limit"; includes 2 users and 1 public worker; higher plans by quote with no prices; Starter+ includes drift detection, a policy engine, 1 private worker; Business adds advanced scheduling and targeted replans; Enterprise lists an audit trail | [spacelift.io/pricing](https://spacelift.io/pricing) | read |
| The pricing comparison table has no Free column, so the free plan's per-feature contents (contexts, dependencies) are not stated there | [spacelift.io/pricing](https://spacelift.io/pricing) | read; consequence marked unconfirmed |
| Signup: click Free trial on the home page, choose Europe or United States, sign in with GitHub, GitLab, Google or Microsoft; with GitHub the organization or account name becomes the Spacelift account name; LaunchPad has Learn, Knowledge base, Videos, FAQ | [docs.spacelift.io](https://docs.spacelift.io/) | read |
| The documentation calls the product "Spacelift Deploy" after the introduction of "Spacelift Flows" | [docs.spacelift.io](https://docs.spacelift.io/) | read |
| GitHub integration: install the GitHub App and select the repository or repositories to manage; custom GitHub app via wizard for other sign-ins; custom-app permissions listed; install "all repositories or only specific ones" | [Integrate GitHub](https://docs.spacelift.io/getting-started/integrate-source-code/GitHub) | read |
| Stack creation steps and fields (name, space, labels; integration, repository, branch, project root, project globs; OpenTofu vendor, version, Manage State; worker pool, autodeploy, protect from deletion) | [Create a stack](https://docs.spacelift.io/concepts/stack/creating-a-stack) | read |
| "This is the only time you can ask Spacelift to be the state backend" for an OpenTofu stack | [Create a stack](https://docs.spacelift.io/concepts/stack/creating-a-stack) | read |
| Delete a stack: three dots, Settings, Stack deletion, choose delete or keep the stack's resources, type "delete"; resources can be destroyed first with a task, `tofu destroy -auto-approve` for OpenTofu; state can be retrieved with a task before deleting | [Create, delete, and lock stacks](https://docs.spacelift.io/concepts/stack/creating-a-stack) | read |
| That turning off "Protect from deletion" is the step needed before a delete, and where that setting lives | not in the pages read | est. |
| Scheduled deletion with resources: a destruction run triggers, then the stack is deleted when it succeeds | [Scheduling](https://docs.spacelift.io/concepts/stack/scheduling) | read |
| Scheduling needs Business and above; schedules on public workers do not trigger | [Scheduling](https://docs.spacelift.io/concepts/stack/scheduling) | read |
| Drift detection needs Starter+ and above and private workers | [Drift detection](https://docs.spacelift.io/concepts/stack/drift-detection) | read |
| Policies: "only available to paid Spacelift accounts"; policy types and rules; Rego v1 `deny contains ... if` form; plan input `input.terraform.resource_changes[].change.actions` | [Policy](https://docs.spacelift.io/concepts/policy/), [Plan policy](https://docs.spacelift.io/concepts/policy/terraform-plan-policy) | read |
| That the teaching policy in this page runs as written | not run: OPA was not available | est. |
| Proposed run: default is a push to any non-tracked branch; reports in VCS as commit status and comment; never applies | [Proposed run](https://docs.spacelift.io/concepts/run/proposed) | read |
| Tracked run triggers (manual, push to tracked branch, trigger policy); no-op finishes without approval; Unconfirmed, Confirmed, Discarded, Applying, Finished meanings; autodeploy conditions | [Tracked run](https://docs.spacelift.io/concepts/run/tracked) | read |
| Run states, locking, 30-day and 7-day terminations, `DESTROY` run type, worker model | [Run](https://docs.spacelift.io/concepts/run/) | read |
| Environment: `TF_VAR_` variables become OpenTofu inputs; secret variables hidden in UI and API | [Environment](https://docs.spacelift.io/concepts/configuration/environment), [Context](https://docs.spacelift.io/concepts/configuration/context) | read |
| Context creation, attach, `autoattach:<label>` | [Context](https://docs.spacelift.io/concepts/configuration/context) | read |
| Stack dependencies: tracked runs only; output reference needs a successful applied run; a stack with downstream dependents cannot be deleted | [Stack dependencies](https://docs.spacelift.io/concepts/stack/stack-dependencies) | read |
| `spacectl`: wraps the GraphQL API with limited create/edit; `profile login` (option 3 browser), `stack list`, `stack deploy --id`, `stack local-preview --id` | [spacectl](https://docs.spacelift.io/concepts/spacectl) | read |
| Account deletion procedure | no page found among those read | not found; est. |
| Uninstalling a GitHub App removes its access to that account's resources | [GitHub: reviewing and modifying installed apps](https://docs.github.com/en/apps/using-github-apps/reviewing-and-modifying-installed-github-apps) | read |
| Protected-branch settings include required pull request reviews and required status checks | [GitHub: about protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) | read |
| The scratch stacks apply and destroy with OpenTofu 1.12.6 with no provider download and no network | author's local run, Exercise 1 | run once |
| Everything in the Spacelift console exercises (3 to 11), and every PowerShell command | not run | est. |
| This project's push and plan policies, hook, and why its proposed run is red | repository files cited above | read |

## Where to next

[Build and destroy a stack per service](Build-and-Destroy-Stack-Per-Service.md) (I4) takes the same loop and makes it repeatable. Meanwhile, [Spacelift](Spacelift.md) shows the real run lifecycle this project uses, and [Teardown checklist](Teardown-Checklist.md) shows the same destroy-before-delete order applied to the project's own stacks.

Next: lesson I4, Build and destroy a stack per service (planned; its page name is `Build-and-Destroy-Stack-Per-Service`, linked above once it merges).
