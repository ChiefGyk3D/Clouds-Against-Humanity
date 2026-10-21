# From commit to pipeline: how DevOps and DevSecOps start in git

> Before this page: [Git from zero](Git-From-Zero.md) for commits, branches and clones, [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) for what a pull request and a CI check are, and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) for the checks themselves. The exercises at the end need your own private copy from [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) and the `gh` command-line tool, signed in. The reading part needs nothing.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

People say "DevOps" as if it were a tool you install. It is a habit: the way a change gets from someone's head to a running system is written down, automated, and checked at every step, so that nobody has to remember. **DevSecOps** is the same habit with security checks built into the chain instead of added at the end.

This page follows one tiny change through this repository's real chain. It names only checks that exist in `.github/workflows/ci.yml` today. Where something is written but not switched on, it says so.

## The idea in three words

| Word | Plain meaning | In this project |
|---|---|---|
| **CI** (continuous integration) | Every proposed change is tested by machines, automatically, before anyone merges it. | The `tofu`, `python` and `security` jobs, gathered under `CI green`. They hold no cloud-provider credential and change nothing in the cloud. |
| **CD** (continuous delivery) | An approved change is carried towards the real system by automation, with a person deciding the last step. | After the merge, Spacelift runs a plan from `main` and waits. A human confirms, and only then does the apply happen. |
| **Shift left** | Find a problem as early in the chain as possible, because a fix costs a minute at the start and an outage at the end. | Secret scanning, the cost gate and the tests run on the pull request, before the merge, long before a droplet exists. |

"Left" is simply the direction time runs on a diagram: commit on the left, running infrastructure on the right.

A note on the second row. Some teams push every green change straight to production with no person in between; that is continuous *deployment*. This project deliberately does not. [Autodeploy is off](Spacelift.md#why-autodeploy-is-off), so it is continuous delivery with a human gate.

## One change, start to finish

![Diagram, From commit to pipeline: 1. Commit on a branch; 2. Push and open a pull request; and more in the source below](images/from-commit-to-pipeline-diagram-1.png)

<details>
<summary>Diagram source (Mermaid)</summary>

```mermaid
flowchart LR
    subgraph left["Shift left: cheap to fix"]
        commit["1. Commit<br/>on a branch"]:::you
        push["2. Push and open<br/>a pull request"]:::you
        ci["3. CI checks<br/>tofu, python + cost gate,<br/>security. No cloud credentials"]:::ctrl
    end
    subgraph gate["The merge gate"]
        green{"4. CI green?<br/>required by<br/>branch protection"}:::warn
        review["5. A human<br/>reads the diff"]:::you
        merge["6. Merge to main"]:::you
    end
    subgraph delivery["CD: carry it to the cloud"]
        plan["7. Spacelift plan<br/>from main"]:::ctrl
        confirm["8. Human reads the plan<br/>and confirms"]:::warn
        apply["9. Apply<br/>real infrastructure"]:::cloud
    end

    commit --> push --> ci --> green
    green -- "no: fix and push again" --> commit
    green -- "yes" --> review --> merge --> plan --> confirm --> apply

    classDef you fill:#132a1f,stroke:#4ade80,color:#dcfce7
    classDef ctrl fill:#1e1b3a,stroke:#a78bfa,color:#ede9fe
    classDef warn fill:#3a2a0f,stroke:#fbbf24,color:#fef3c7
    classDef cloud fill:#0f2a3d,stroke:#38bdf8,color:#e0f2fe
```

</details>

Imagine a one-line change to a stack, say to one rule in `stacks/10-access/main.tf`. [Trace one change end to end](Trace-One-Change-End-to-End.md) follows a real one (pull request #8) with its real files; here the same journey is told in order, one box at a time.

### 1. Commit

You edit the file on a **branch**, never on `main`, and make a **commit** with a message that says *why*. Nothing is live. Nothing has left your computer. This is the cheapest place in the whole chain to be wrong: you can undo it with a keystroke. If git itself is new, [Git from zero](Git-From-Zero.md) walks the buttons and the commands.

### 2. Push and open a pull request

**Pushing** copies your branch to GitHub. Opening a **pull request** says "please look at this and merge it". The description is part of the chain: this project's pull requests carry four headings, *Why*, *Change*, *Testing* and *Not verified*. The last one is a gate made of words. It tells the reviewer what green does not prove.

### 3. The checks

The moment the pull request exists, GitHub starts the workflow in `.github/workflows/ci.yml`. It has three jobs, each a call to a shared workflow from the author's [git-your-ship-together](https://github.com/ChiefGyk3D/git-your-ship-together) library, pinned to an exact commit:

| Job | What it runs | The mistake it catches |
|---|---|---|
| **`tofu`** | `fmt -check`, `validate`, tflint and Trivy; then `tofu test` in each stack and module directory with every provider mocked; then `opa fmt`, `opa check` and `opa test` over `.spacelift/policies` | Badly formatted or broken code. A firewall that gained an inbound rule. A policy file that no longer parses or whose own tests fail. |
| **`python`** | In order: the cost gate (`scripts/ci_cost_gate.sh`), the settings page check, `pytest`, the identifier check and the Threat Dragon layout check, on Python 3.12 and 3.13; then `ruff` | A bill that rose past the approved figure. A stale reference page. A cloud account id written into a public file. |
| **`security`** | Code scanning (CodeQL), secret scanning (Gitleaks) and the other scanners the shared security workflow runs | A token or key committed by accident. A risky pattern in a workflow. |

Two more facts matter. The jobs hold no cloud credential, because every provider in the tests is a mock, so a compromised check can *block* you but cannot *destroy* anything. And if your pull request touches `docs/wiki/`, a separate **Wiki** workflow also runs, to prove the pages still generate.

Notice what these have in common: each one answers a question a machine can answer every time without getting bored. That is the whole of CI.

### 4. The merge gate: `CI green`

A fourth job, `ci-green`, is the only one defined in this repository itself. It lists the three jobs as `needs`, runs even if one failed (`if: always()`), and fails unless every needed job finished as `success`. A skipped or cancelled job counts as a failure, so a check cannot quietly not run.

**Branch protection** then makes that job *required*: GitHub refuses to enable the merge button until `CI green` passes. This is a **required status check**. The point of having one name is that you can add or rename a job without touching the protection settings.

Two honest limits, both from [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md#branch-protection-and-one-writer). Branch protection is a repository setting, not a file, so a copy of the repository starts without it. And the checks guard against honest mistakes; someone who can push a branch can change the checks. The real boundary is who can push.

### 5. Review

A human reads what a machine cannot judge: is this a good idea? Do the files in the diff match what the description claims? If the same pull request changes a rule *and* the test that guards the rule, read it slowly. When you are the only person on the project, the pause and the pull request description are a review of yourself, and they are still worth it.

### 6. Merge

The merge puts the change on `main`. A change to a stack, a module or the Spacelift setup now matters to Spacelift. A change to documentation only does not start a run. (The [push policy](Spacelift.md#push-policies-paid-plan-versus-free-plan) that narrows this exists in the repository but only takes effect once attached in Spacelift, and it needs a paid plan; on the free plan the narrow project roots do the docs-only half.)

### 7. Plan in Spacelift

For each affected stack, Spacelift starts a **tracked run** on `main`. Its hook fetches the secrets that stack needs from Doppler (only for a tracked run on `main`, so a pull request never receives them) and runs `tofu plan`. The plan is a description of exactly what *would* change in the real world. Nothing has changed yet.

### 8. The human gate

Autodeploy is off, so the run stops and waits. You read three things: the verb (`update in-place`, not `replace` or `destroy`), the count (one resource, not two) and whether the diff matches the story in the pull request. Confirm only when it does. Discard when it does not; discarding changes nothing.

This is also where [policy as code](#policy-as-code-rules-a-machine-can-enforce-on-every-plan) can say no before you even look.

### 9. Apply

Only now does `tofu apply` run, against the real cloud. Everything before this box was cheap and reversible. This one is not, which is why every earlier box exists.

## Policy as code: rules a machine can enforce on every plan

A **policy** is a rule such as "no firewall may accept the whole internet". **Policy as code** means the rule is written in a file, in the repository, with tests, and a machine applies it every time, instead of a person remembering. This project has three kinds, and they sit at different points on the chain:

| Policy | Where it lives | What it enforces | Runs |
|---|---|---|---|
| The **cost gate** | `scripts/cost_check.py` | The planned monthly cost may not exceed the approved total, and a paid resource type nobody priced is refused by name | In CI, on the pull request |
| The **tests** | `tofu test` files next to each module and stack | Security properties written as assertions, for example that the connector firewall has exactly one inbound rule and it names a tag, never an address | In CI, on the pull request |
| The **plan policy** | `.spacelift/policies/plan.rego` | Denies a plan that would open a port to the whole internet, turn on IPv6, delete or replace a protected network piece, or run with autodeploy on | In Spacelift, on the plan, before an apply |

The plan policy is written in Rego, the language of Open Policy Agent. CI checks its formatting and runs its own tests (`plan_test.rego`) on every pull request, so the rule itself is tested. But the repository's [Spacelift page](Spacelift.md#the-plan-policy-no-open-ports-in-a-plan) says plainly that it is **written and tested but not yet attached** in Spacelift, and whether the plan policy type is available on the maintainer's plan is unconfirmed. A policy file that is not attached protects nothing in the cloud. It protects the repository (CI proves it still works) and it is ready to attach.

## Shift left, in plain language

Cost of fixing a mistake rises as it moves right:

- A typo you notice while committing costs a few seconds.
- A secret caught by Gitleaks on the pull request costs a force-pushed branch and a rotated token, because the secret was already on GitHub's servers when the scan ran. A secret that reached a live system costs far more.
- A firewall rule caught by `tofu test` costs a failed check. The same rule caught at the plan costs a discarded run. Caught after the apply, it costs an incident.

Shifting left means putting the questions where the answers are cheapest. It does not mean the later gates are redundant. Each gate catches something the others cannot: CI cannot see the real cloud, the plan cannot judge whether the idea was good, and neither can tell you the change fixed the bug. That last check is yours, from outside the pipeline, as the [trace page](Trace-One-Change-End-to-End.md#how-you-would-verify) shows.

Security is "shifted left" in this chain in four places:

1. **Secrets never enter a file** ([Doppler](Doppler-and-Secrets.md)), and Gitleaks checks the diff anyway.
2. **CI holds no cloud-provider credentials**, so the checks cannot be turned against your cloud account. They do run with a GitHub token, and that token is boxed in too: the workflow starts with `permissions: {}`, and each job is granted only what it asks for. In `ci.yml` the three jobs get `contents: read` and `id-token: write` (to request a short-lived identity token); the `security` job also gets `security-events: write` (to post code-scanning results) and `pull-requests: write` (to comment on the pull request). None of those can create a droplet, but a token that can comment or write scan results is still something to keep narrow, which is why each grant is listed per job.
3. **Rules are tests and policies**, so a change that weakens a control fails a check instead of relying on a reviewer's memory.
4. **A human confirms the plan**, so a mistake that every automated check agreed with still has one last reader.

## Exercises on your own private copy

You need the private repository from [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) with Actions enabled. Do these there, never in the public repository.

**Safety first.**

- Work on a throwaway branch for each exercise, and open the pull request against **your own private repository's** `main`. When `gh pr create` asks where to send it, choose your own repository, never `upstream`. If you have used `gh` here before, `gh repo set-default <you>/<your-private-repo>` makes this automatic.
- Before you start, open the Actions tab of an untouched `main` and confirm `CI green` is green. If it is not, stop. Reading why is the skill in exercise 1, and nothing below makes sense until your baseline is clean. Do not remove a job to make it pass.
- Each exercise ends with an undo. Do the undo, so the next exercise starts from a clean `main`.
- Do not paste anything into a file that looks like a token or an account id. None of these exercises needs one.

> **Screenshot to take yourself:** the checks list at the bottom of a pull request on your private repository, once with every check passing and once with `CI green` failing.
> Capture: the merge box of a pull request, with the list of checks, the name `CI green` and its status, and the merge button or the message beside it in view.
> Look for: which checks passed and which failed, and the text that says a required check has not passed.
> Redact: your username, the repository name, the address bar, and the avatars and names of any reviewers.

### Exercise 1: read a failing check

**What it teaches:** a red check is a message, and the log says exactly what to fix.

**Predict.** `tofu fmt -check` fails when a file is not formatted the way `tofu fmt` would write it. Which job will fail? Which others will stay green?

**Do.**

```bash
git switch -c exercise-read-a-check
```

Open `stacks/00-foundation/main.tf`. Find the `module "vpc"` block, where the `=` signs line up in a column. On the `region` line, add a few extra spaces before the `=`, so it no longer lines up. Save the file, then:

```bash
tofu fmt -check -recursive stacks/00-foundation
echo "exit=$?"
```

You should see the file named and a non-zero exit. That is the check, run on your own computer for free. Now send it up:

```bash
git add stacks/00-foundation/main.tf
git commit -m "exercise: break formatting on purpose"
git push -u origin exercise-read-a-check
gh pr create --fill
gh pr checks
```

**Check.** Wait for the checks to finish, then open the failed one (`gh run view --log-failed`, or the Details link). Find three things: which job failed, which file it names, and the line that says why. Confirm `CI green` is red because a needed job was not a success, even though the other jobs passed.

**Undo.** Fix it the way the log tells you (`tofu fmt stacks/00-foundation`), commit, push, and watch the check turn green. Then close the pull request without merging and delete the branch.

**Take away:** you did not need to guess. The log named the file.

### Exercise 2: make the cost gate fail on purpose, then fix it

**What it teaches:** the bill is a number someone has to approve in a reviewed change.

**Predict.** The two connectors are `s-1vcpu-1gb`, $6 each, $12 in all, and `docs/stages/approved.json` approves $12.00 for DigitalOcean. If you change one connector to a bigger size in `cost.json` and touch nothing else, which job fails, and what does the message say?

**Do.**

```bash
git switch main && git pull origin main
git switch -c exercise-cost-gate
```

In `stacks/10-access/cost.json`, change the `size` of `connector-a` from `s-1vcpu-1gb` to `s-1vcpu-2gb`. Run the gate on your own computer first:

```bash
python3 -I scripts/cost_check.py --root .
echo "exit=$?"
```

You should see a line saying the planned figure is above the approved one (`planned $18.00 is above approved $12.00` when this page was written) and a non-zero exit. Open the pull request as in exercise 1 and find the same sentence in the `python` job's log.

**Check.** There are two ways to make it pass, and they mean different things. You can put the size back, which says "I did not mean to spend that". Or you can raise `approved_monthly_total` in `docs/stages/approved.json` to match, which says "I decided to spend that", and which must also still fit under the current phase's ceiling. Read [the cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate) and say which of the two a reviewer should be able to see in the diff, and why raising the approved figure is deliberately a separate, visible edit.

**Undo.** Put the size back, push, and confirm green. Close the pull request without merging and delete the branch.

**Take away:** the gate does not stop you spending money. It stops you spending it *by accident*.

### Exercise 3: break a test and watch the merge button block

**What it teaches:** a required check turns "CI says no" into "the merge button says no".

**Predict.** If you change what a test expects so that it is wrong, which job fails, and what happens to the merge button? What would happen if branch protection were not switched on?

**Do.** Make sure your private repository has branch protection on `main` that requires `CI green` (the setup is in step 3 of [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md#step-3-what-has-to-be-re-pointed-in-your-copy); a free personal account may not be able to enforce it on a private repository, so check your plan). Then:

```bash
git switch main && git pull origin main
git switch -c exercise-break-a-test
```

In `stacks/10-access/tests/access.tftest.hcl`, find the first assertion whose message begins "The only inbound rule must be tcp 22" (around line 146) and, in its condition, change `tcp/22/cah-connector-tor1` to `tcp/2222/cah-connector-tor1`. You have just made the test expect something false. Run it on your own computer first:

```bash
cd stacks/10-access
tofu init -backend=false -input=false
tofu test
cd ../..
```

You should see one failure and the message from the assertion. Commit, push and open the pull request.

**Check.** Wait for the checks. `CI green` should fail, because the `tofu` job did. Look at the merge box: with branch protection on, the merge button is disabled and GitHub tells you a required check has not passed. Now ask the question this exercise is for: *what stopped the merge*, you, or the pipeline? And what would have stopped it if you were not looking?

If your plan cannot enforce branch protection, the merge button stays available even though a check is red. That is the gate you are missing, as the page on [your plan](Fork-Private-Stacks-and-the-Pipeline.md#what-your-github-plan-allows) warned. Write down what replaces it. Do **not** press merge.

**Undo.** Close the pull request without merging, and delete the branch. Check `main` is untouched.

**Take away:** a test is only a gate when merging depends on it.

## Where this shows up in the repo

| Idea | Where |
|---|---|
| The checks and the `CI green` gate | `.github/workflows/ci.yml` |
| The wiki workflow | `.github/workflows/wiki.yml` |
| The cost gate and the approved figures | `scripts/cost_check.py`, `docs/stages/approved.json` |
| Policy as code | `.spacelift/policies/plan.rego` and `plan_test.rego` (also `push.rego`) |
| Tests that are security properties | `tofu test` files under `modules/*/tests/` and `stacks/*/tests/` |
| The human gate | [Spacelift](Spacelift.md#why-autodeploy-is-off) |

## Try it yourself

- Take the nine boxes in the diagram and, for each, write one sentence on the mistake only that box can catch. A box with no answer is either a good gate that rarely fires or decoration; decide which.
- Pick one check from the table in step 3 and say what it could not have caught. Then read [Trace one change end to end](Trace-One-Change-End-to-End.md#what-would-have-stopped-it-three-bad-variants) and see whether you found the same limit.
- Look at the `permissions:` lines in `ci.yml`. For each job, ask what the worst thing is it could do if the code it runs were malicious. That is the reason the checks hold no cloud-provider credential and only a narrow GitHub token.

Next: [Trace one change end to end](Trace-One-Change-End-to-End.md), then back to the [Reading order](Reading-Order.md).
