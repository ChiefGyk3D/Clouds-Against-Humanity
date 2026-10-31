# Environments and promotion: local dev, staging and production

> **Status: written from reading the repository; staging is planned and not built.** Every project fact below comes from a file in this repository, named where it is used and listed in the [claims register](#claims-register), read on **2026-10-30**. Two steps of the exercise were run by the author on that date: `tofu test` in `stacks/10-access` (136 passed, 0 failed) and a changed connector size in `stacks/10-access/cost.json` that made `scripts/cost_check.py` print `planned $18.00 is above approved $12.00` (the file was restored afterwards). The rest was not run. **Production** exists in the sense that the stage 0 and stage 1 stacks have been built; **staging** does not exist: no stack, no cloud project, no Doppler config and no cost entry (issue #310). **A separate dev stack** is an option, not a plan. Where this page says what staging "will" do, that is the design in issue #310, not something built. Where something is general knowledge and not a repository fact, the text says **est.**

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md), [Spacelift](Spacelift.md), [Doppler and secrets](Doppler-and-Secrets.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md). The exercise needs a copy of the repository, Python and OpenTofu on your own computer. It is free and touches no cloud.

Most people meet the word "environment" as a rule: "never test in production." This page explains the reasons behind the rule, then shows honestly which parts of it this project has, which it plans, and which it does without.

## What you will be able to do

- Say what local dev, staging and production are each for.
- Say why each environment gets its own stack, state, secrets, cloud project and cost ceiling.
- Describe how a change travels from your computer to production here, and which step a human owns.
- Say what a mocked test can prove and what only a real apply can.
- Say why this repository uses one trunk and not a branch per environment, and what a `dev`, `staging`, `main` flow would cost in a public repository.
- Say what each environment would need for alerts and logs, and what exists today.

## What each environment is for

| Environment | Purpose | Cloud cost | In this project today |
|---|---|---|---|
| **Local dev** | Write and break things fast. Your computer, your editor, tests with mocked providers. | $0 | Exists. `tofu test` with mocked providers, the Python tests and the [labs](Labs-Break-It-on-Purpose.md) run on a laptop (`docs/stages/approved.json` holds no entry for it because it costs nothing). |
| **Staging** | A real, small copy of the production shape in a separate cloud project, to try a change against the real cloud API before production. | Its own ceiling: $20 per month, by decision | **Planned, not built.** Issue #310. Nothing is built until the maintainer signs in and sets up the accounts. |
| **Production** | The environment that is the point of the project. | The current phase's ceiling: $30 per month in `stage-2` | Exists. The stacks `cah-00-foundation` and `cah-10-access` are built, and `cah-20-telemetry` is written and locked, not applied. |

The names are a convention, not a law. Some teams have four or five environments. What matters is the question each one answers: "does it work?" (local), "does it work against the real cloud?" (staging) and "is it running for real?" (production).

**Dev is optional here.** The decision in issue #310 is that a separate dev stack is added only when a second person works in the repository or staging is busy. Until then staging doubles as dev under the same $20 ceiling. That is a cost-saving choice for a one-maintainer project. A team with several people changing things at once would not make it.

## Why separate stacks and separate cloud projects

An environment is only an environment if a mistake in one cannot reach another. Four things have to be separate, and "a variable that says which environment" does not separate any of them. The same warning already sits in [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) ("Keep development, staging and production apart with separate state and separate accounts or projects, not only a variable that says which").

1. **State.** State is OpenTofu's record of what it built. One stack, one state, held by Spacelift ([Spacelift](Spacelift.md)). If staging shared production's state, a staging `destroy` would plan against production's resources.
2. **Secrets.** Today every run reads from one Doppler config, `prd`, through one read-only token in the Spacelift context `cah-doppler` (`docs/spacelift-secrets.md`, sections 1 and 2). That token can read the whole config, not only the names a stack asks for. If staging ran with it, a staging mistake or leak would hold production's DigitalOcean token. Staging gets its own Doppler config, per issue #310. The same rule is written for other clouds: "One Doppler config and one Spacelift context per cloud" (`docs/spacelift-secrets.md`, section 8a, a convention proposed there and not set up).
3. **Cloud project.** A DigitalOcean project groups resources, and the token that can touch one project's resources is a separate thing from the project itself. Issue #310 asks for "its own small DigitalOcean project", so a mistaken `destroy` or a runaway bill in staging is visible and bounded. Whether the staging token would be a separate DigitalOcean token or the same account's token with the project as the only boundary is not decided in the repository. The weaker version (same account and token, different project) separates the bill and the listing, not the permissions: **est.**, to settle when staging is built.
4. **Cost ceiling.** See [cost ceilings per environment](#cost-ceilings-per-environment).

The result you want: you can destroy staging in full, at any hour, and production does not notice. That is the reason issue #310 plans for staging to be "confirmed by hand, destroyed after each test".

## Promotion: how a change reaches production

Promotion means moving the same change from a safer place to a more important one, with a check at each step. In this repository the path is:

1. **Local.** You change code on a branch, run the tests on your computer (see [Tests: mocked providers and real applies](#tests-mocked-providers-and-real-applies)).
2. **Pull request.** Opening one runs the checks in GitHub Actions. The single required check is `CI green`, and `main` requires a pull request ([Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md#branch-protection-and-one-writer)). The push policy makes Spacelift ignore the pull request: no proposed run, so no pull request code runs in Spacelift next to the Doppler context (`docs/spacelift-secrets.md`, section 9).
3. **Merge to `main`.** If the merge changes a stack's project root, `modules/`, `scripts/spacelift/` or `.spacelift/`, the push policy starts a **tracked run** on that stack. A merge that changes only docs starts nothing (section 9).
4. **Plan, then a human.** The run plans and stops. The plan policy `cah-plan` can deny it before anyone confirms (`docs/spacelift-secrets.md`, section 9a). Autodeploy is off, so a human reads the plan and presses Confirm ([Spacelift](Spacelift.md#why-autodeploy-is-off)).
5. **Apply.** The apply phase reloads the secrets, because it can start in a fresh container (`docs/spacelift-secrets.md`, section 3).

Today there is one environment at the end of that path. **Once staging is built**, the design in issue #310 is that its stack tracks `main` too. A merge would plan in staging and in production. The human decides in which order to confirm, and the staging run is confirmed by hand and torn down after the test. A chain that forces staging to pass before production starts is **not designed** in the repository; today the order is the maintainer's habit, not a gate. Adding such a gate would be new work.

This is also where a fix goes in an emergency: through the same path. The repository has no separate hot-fix route ([Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md#what-is-missing-compared-with-an-enterprise) describes the same absence).

## One trunk, not a branch per environment

A common pattern is a long-lived branch for each environment: merge to `dev`, then to `staging`, then to `main`. This repository does not do that, and issue #310 gives the reason: staging is "a separate stack that tracks `main`, not a staging branch."

The reason is the secrets. A tracked run loads secrets from Doppler, and this repository is public. What is safe to run with those secrets is decided by two things: who can change the code that the run reads, and which branch the run is allowed to read it from. Both are tied to `main`:

- The Doppler hook fetches secrets only for a tracked or destroy run **on `main`**. It checks the branch: any other branch gets "is not main; skipping" (`scripts/spacelift/doppler-env.sh`, around line 126).
- `main` is branch-protected: a pull request and `CI green` are required (`docs/spacelift-secrets.md`, section 8).
- The push policy starts a tracked run only on the stack's tracked branch, and ignores every other branch, every tag and every pull request (`.spacelift/policies/push.rego`; `docs/spacelift-secrets.md`, section 9, issue #306).

Now suppose a `staging` branch existed, tracked by a staging stack. A push to it would start a run that reads code from that branch and, if the hook allowed it, loads staging's secrets. Anyone who could push to the branch could change the hook script or `.spacelift/config.yml` and read the token (this is the trust-boundary point in `docs/spacelift-secrets.md`, section 8). So the branch would need everything `main` has: the same protection, the same required `CI green` check, and no direct pushes. And `dev` would need it too if it also ran tracked. That is three protected branches to keep honest, and a `dev` to `staging` to `main` merge flow that adds ceremony and a merge conflict risk without adding a reader. For a one-maintainer project, issue #310 sets `main` plus short-lived feature branches. The `dev`, `staging`, `main` flow is described there as "only for the lesson".

Branch-per-environment is not wrong. It suits a team that deploys different versions to different environments on purpose, for example a release branch that lags production. It trades simplicity for control, and in a public repository it also multiplies the places where secrets can be reached. **est.**: how large that cost is depends on the team; the repository has only the one-maintainer case.

**One trunk, several stacks** gives each environment the same code at the same commit, and moves the difference into configuration: which Doppler config, which cloud project, which ceiling. That difference is what the next sections describe.

## Secrets per environment

The rule: an environment's secrets can be read only by that environment's runs.

| Item | Production (today) | Staging (planned) |
|---|---|---|
| Doppler config | `prd` in project `clouds-against-humanity` (`docs/spacelift-secrets.md`, section 4) | Its own config; no production secrets or state shared (issue #310) |
| Spacelift context | `cah-doppler`, auto-attached to stacks labeled `cah` | Not designed. A separate context per config follows the pattern in section 8a, so a staging stack does not also get production's token |
| What runs may read | Tracked and destroy runs on `main`; proposed and task runs get nothing | Same hook, same rule |
| Threat-model note | [Threat model](Threat-Model.md) | A note for the staging config "lands with it" (issue #310) |

Two traps the existing documents already name, and that a second environment would make easier to hit:

- **Two tokens on one stack.** Section 8a warns that the auto-attach on the label `cah` "must not also catch" another environment's stacks, "or one stack would receive two tokens". A staging stack therefore needs a different label from the production stacks, or its context needs a different attach rule. Which one is a decision for the build; the repository does not yet make it.
- **The test only proves the declared request.** `tests/test_secret_separation.py` proves each stack asks for the names it should. It does **not** prove that a token cannot read another config, or that the right context is attached ([Doppler and secrets](Doppler-and-Secrets.md); `docs/spacelift-secrets.md`, section 8a). That is a manual check against the live Doppler and Spacelift, and for a staging stack it would be the first check to run: ask for a production name from a staging run and expect the hook to fail with `could not read ... from Doppler`.

Local dev uses none of these. Your computer needs no Doppler config and no cloud token to run `tofu test`; the providers are mocked. If you ever put a real production token into your local shell to "try something," you have made local dev into production, with fewer controls.

## Cost ceilings per environment

Cost is the fourth separation. The mechanism that exists today is the cost gate, described in [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) and `docs/cost.md`.

What is built:

- A **ceiling per project phase** in `docs/stages/approved.json`. `current_phase` is `stage-2` at $30, with a `hard_max` of $60 above which no phase may go without editing that number in the same reviewed change (`docs/cost.md`, "Ceilings per phase").
- A **cost manifest per stack** (`cost.json`) that lists the planned machines and sizes. The gate adds them up per cloud and fails if the total passes that cloud's approved figure or if the active clouds together pass the phase ceiling. A stack directory without a `cost.json` fails the gate.
- It is checked on every pull request. A change that would raise the bill cannot merge unless the number in `approved.json` is raised in the same pull request, where a reviewer can see it.

What is **not** built: a ceiling per *environment*. The existing ceilings belong to phases of one production project, not to environments. Issue #310 requires the $20 staging ceiling to be written into `docs/stages/approved.json` and `cost.json` "before any resource exists", and `docs/wiki/Roadmap.md` records that it is not yet written. The repository does not yet say how the gate would hold two ceilings at once: today it compares the sum of the active clouds with one phase ceiling, so a $20 staging figure added to production's $12 would be judged against $30. That is a design question for the build, and the page does not answer it. **Not designed.**

The cost gate cannot see what is actually running (`docs/cost.md` says it cannot), so the other protections still matter: a billing alert at the provider (the project set two in stage 0, at $10 and $25; [How money works in the cloud](How-Money-Works-in-the-Cloud.md)), and destroying staging after each test so the ceiling is a cap on a bill that is mostly zero. Issue #310 sets a test to finish with the staging cost "under the ceiling" as part of its definition of done.

## Tests: mocked providers and real applies

| Question | Mocked tests | A real apply |
|---|---|---|
| Where | Your computer and GitHub Actions (`tofu test` with `mock_provider`, pytest, `opa test`) | Spacelift, after a human confirms |
| Cloud account | None | Yes, with the environment's token |
| Cost | $0 | Whatever the plan creates, until destroyed |
| What it proves | The code's own logic: sizes read from `cost.json`, connector names, firewall rules the module emits, policies behave on fixtures | That the cloud accepts the request |
| What it cannot prove | Anything the provider decides: scopes, regions, quotas, existing names, timing | The code is right for all inputs; it proves one run |

The repository has real examples where only the real API found the problem:

- A new account got `422 Size is not available in this region` for the $6 droplet in `nyc3`, and the region became `tor1` (`docs/cost.md`).
- An apply failed with `422 SSH Key is already in use` because the key already existed on the account, so the stack now looks it up by name ([Lessons learned](Lessons-Learned.md#3-the-ssh-key-that-already-existed)).
- The token needs the `ssh_key: read` scope; without it the plan fails with a `403`. This was "proven by the 2026-10-11 redeploy" (`docs/spacelift-secrets.md`, section 4a).

A mock will happily say yes to all three. That is not a flaw of mocking; it is what a mock is for. Staging is the planned place to find the next such surprise on a $20 budget, before it happens in production.

A related limit, from issue #310: **staging cannot test the Twingate and home-network side.** The home connector, the VLAN, the pfSense allow-list and the Twingate resources that cross into a home network exist at home, not in a cloud project. So a successful staging run does not show that a change works across that path. It shows the cloud-side half works. Stage 2 is the stage that crosses that boundary, and it is written and mock-tested but **not applied** ([Roadmap](Roadmap.md); [Stage 2: the home side runbook](Stage-2-Home-Side-Runbook.md)).

## Alerting and logging per environment

Be careful with this section. Most of it is plan, not product.

| Topic | Local dev | Staging | Production |
|---|---|---|---|
| **Logs** | Terminal output and test results. The synthetic [monitoring lab](Lab-Demo-Monitoring-Stack.md) generates fake telemetry on your computer. | **Not designed.** Issue #310 does not say what, if anything, it ships. | Stage 2 design: connector and access logs go to the existing on-prem SIEM, "no new log service in the cloud" (`docs/wiki/Roadmap.md`). **Written, not applied.** |
| **Alerts** | None needed. | Not designed. | A billing alert at the provider at $10 and $25 (`docs/wiki/How-Money-Works-in-the-Cloud.md`). Detection alerts belong to stage 2 and 4, which are not applied. |
| **Record of changes** | git history | git history, and Spacelift's run history | git history, Spacelift's run history, and the plan policy's denials |

Three design points hold regardless of what is built:

- **Do not page anyone for staging.** Staging is torn down after each test and is allowed to break. If staging pages a person as production does, people stop trusting pages. **est.**
- **Keep the logs apart.** Staging's logs should not be mixed with production's in the same index, or an investigator cannot tell a test from an incident. If staging ever ships to the on-prem SIEM, give it its own index or tag. **est.**; not designed.
- **Staging has its own secrets, so it needs its own leak check.** A token that appears in a staging run log is a smaller incident than production's only if the staging token really is separate. This is why the Doppler masking check in `docs/spacelift-secrets.md`, section 8, would be repeated for the staging config.

## What is built, what is planned, what is not planned

| Piece | Status | Where it is written |
|---|---|---|
| Local tests with mocked providers | Built | `stacks/*/tests/`, [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) |
| Production stacks 00 and 10 | Built; stage 1 connectors redeployed 2026-10-11 | `docs/spacelift-secrets.md` (section 4a), [Roadmap](Roadmap.md) |
| Stack 20 (telemetry) | Written, locked, not applied | `docs/spacelift-secrets.md` (section 6) |
| Push policy and plan policy | Built and live | `docs/spacelift-secrets.md` (sections 9 and 9a) |
| Cost gate with a ceiling per phase | Built | `docs/cost.md` |
| Staging stack | **Planned, not built** | Issue #310 |
| $20 staging ceiling in `approved.json` and `cost.json` | **Planned, not written** | Issue #310; `docs/wiki/Roadmap.md` |
| Staging Doppler config, context and cloud project | **Planned, not built** | Issue #310 |
| Staging threat-model note | **Planned** | Issue #310 |
| A separate dev stack | Option only | Issue #310 |
| A chain that forces staging before production | Not designed | none |
| `dev`, `staging` and `main` branches | Not planned; lesson only | Issue #310 |
| Staging logs and alerts | Not designed | none |

## Predict, then check

1. A teammate says "staging is just production with a smaller droplet, so a variable called `environment` is enough." Name two things that stay shared.
2. You add a `staging` branch, set the staging stack to track it, and leave `scripts/spacelift/doppler-env.sh` alone. What happens to the secrets on a push to that branch, and why would changing the script be a bad idea without more controls?
3. A pull request passes `tofu test` and `CI green`. Name one failure it could still produce on the real apply.
4. The $20 staging figure is added to `approved.json`. Production costs $12. Which single number does the cost gate compare the sum against today?
5. A staging run log contains the staging Doppler token. Is that better or worse than the same thing in production, and what decides it?

<details>
<summary>Answers</summary>

1. State (one state would let a staging destroy plan against production) and secrets (one config means the staging run holds production's token). Also the cost ceiling and the cloud project's resource list.
2. The hook skips any branch that is not `main`, so the run gets no secrets and fails at the provider. Changing the script to allow `staging` would make secrets reachable from whoever can push that branch, so that branch would need `main`'s protection and `CI green` first.
3. Any provider-side surprise: a missing token scope (`403`), a size unavailable in the region (`422`), a name that already exists. The three real ones are in the section on tests.
4. The current phase's ceiling, $30 in `stage-2`. How the gate would hold a separate $20 for staging is not designed.
5. Better only if the staging token is a different token that can reach only staging's config and project. If it is the same token or the same permissions, it is the same incident.

</details>

## Try it yourself

Free; nothing leaves your computer. This is written from reading plus the two runs named in the banner.

1. In a copy of the repository, run the mocked tests for the access stack, the way the CI does (`tofu -chdir=stacks/10-access init -backend=false -input=false`, then `tofu -chdir=stacks/10-access test`). Read one `mock_provider` block in `stacks/10-access/tests/access.tftest.hcl`. Which cloud account did that test need? None.
2. Run `python3 -I scripts/cost_check.py --root .` and read the last three lines. Then change the first `size` in `stacks/10-access/cost.json` to `s-1vcpu-2gb`, run it again, and read the failure. Restore the file with `git checkout stacks/10-access/cost.json`. Which environment would have paid $6 more per month, if this had reached an apply?
3. Run `opa test .spacelift/policies -v` if you have OPA. Read one test in `push_test.rego` that names a non-`main` branch. What does the policy do with it?
4. On paper, design staging's Spacelift setup in six lines: stack name, tracked branch, Doppler config, context, label, cost ceiling. Check each line against [Secrets per environment](#secrets-per-environment) for a place where it would share something with production.
5. Write the one-paragraph threat-model note for the staging Doppler config. What does an attacker with its token reach? What can they not reach? Compare with the [Threat model](Threat-Model.md).

## Claims register

All entries are repository files read on **2026-10-30**. No vendor page was read for this lesson.

| Claim | Source | Status |
|---|---|---|
| Staging is a separate stack tracking `main` (not a branch), with a $20 per month ceiling in `approved.json` and `cost.json` before any resource exists, its own Doppler config, project and state, confirmed by hand and destroyed after each test, covered by `cah-plan` and the push policy, with a threat-model note; cannot test Twingate and the home network; a separate dev stack is an option; `main` plus short-lived feature branches; `dev`, `staging`, `main` only for the lesson | GitHub issue #310 (read 2026-10-30) | Read. Planned, not built |
| The staging ceiling is not yet written into `approved.json`; stage 2 and the S7 and S8 sprint items | `docs/wiki/Roadmap.md`; `docs/stages/approved.json` has no staging phase | Read |
| Phases, ceilings, `hard_max` $60, `current_phase` `stage-2` at $30, the cost gate's rules, the `nyc3` region `422` | `docs/stages/approved.json`; `docs/cost.md` | Read; `scripts/cost_check.py` run on 2026-10-30 |
| One Doppler config `prd`, one context `cah-doppler`, hook rules, the token reads the whole config, per-cloud contexts convention (proposed, not set up), two tokens on one stack warning, what the secret-separation test does not prove | `docs/spacelift-secrets.md` sections 1 to 4, 8, 8a; `.spacelift/config.yml` | Read |
| The hook fetches only on a tracked or destroy run on `main` | `scripts/spacelift/doppler-env.sh` lines 24 and 117 to 127 | Read |
| Push policy: a tracked run only for a push to the stack's tracked branch that changes the stack; nothing for pull requests, tags, other branches or forks | `.spacelift/policies/push.rego`; `docs/spacelift-secrets.md` section 9 | Read |
| Plan policy `cah-plan`, autodeploy guard, destroy guard | `docs/spacelift-secrets.md` section 9a; [Spacelift](Spacelift.md) | Read |
| `main` requires a pull request and `CI green` | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) (Branch protection) | Read |
| `ssh_key: read` scope proven by the 2026-10-11 redeploy | `docs/spacelift-secrets.md` section 4a | Read |
| The SSH key `422` | [Lessons learned](Lessons-Learned.md) | Read |
| Billing alerts at $10 and $25 | [How money works in the cloud](How-Money-Works-in-the-Cloud.md) | Read; not checked against the provider |
| Stage 2 logs go to the on-prem SIEM, written and not applied | `docs/wiki/Roadmap.md` | Read |
| `tofu test` in `stacks/10-access` passed with providers mocked | `stacks/10-access/tests/access.tftest.hcl` | Run, 2026-10-30: 136 passed, 0 failed |
| Raising a connector size in `cost.json` fails the gate | `stacks/10-access/cost.json`; `scripts/cost_check.py` | Run, 2026-10-30: `planned $18.00 is above approved $12.00`; file restored |
| Why a staging branch would need `main`'s protection | Reasoning from the three rows above and issue #310 | **est.**, not tested |
| A separate DigitalOcean token for staging; how the gate holds two ceilings; the staging label or context; a staging-before-production gate; staging logs and alerts | Nothing | **Not designed** |
| Live Spacelift, Doppler and DigitalOcean settings | Not checked in this lesson | Not verified |

Next: [Roadmap](Roadmap.md). Back to the [Reading order](Reading-Order.md).
