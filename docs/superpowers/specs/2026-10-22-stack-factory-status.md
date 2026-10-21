# Clouds Against Humanity: Stack factory status (issue #96)

Status: GAP ANALYSIS for review. Date: 2026-10-22. Issue: #96 (title: "Create the private spacelift-stack-factory repository and adopt cah-00 by import").
Scope: where issue #96 stands against its own "Done when" list, what is left, and who does each step. This is a status document, not an approval. It changes no stack, adds no code and creates nothing in Spacelift.

How this was produced: the public repository was read in full for this topic (`.spacelift/config.yml`, `.spacelift/policies/`, `docs/spacelift-secrets.md`, `docs/wiki/Spacelift.md`, `tests/test_secret_separation.py`, `tests/test_doppler_env.py`, the stack directories). The private repository named in the issue exists and was read once, read-only, through the GitHub API, for a structural summary only. Nothing from it (names, identifiers, values) is copied here. No Spacelift or DigitalOcean API was called, so anything that lives only in the Spacelift console is marked "cannot tell".

## 1. The issue as written

The factory keeps stack definitions, spaces, contexts and policies in a private repository, so the public one holds only code.

Done when:

1. Private repo with GYST callers and gitleaks.
2. cah-00 imported, plan is a no-op.

Gate: the maintainer creates the repository; every Spacelift change needs his confirmation. Size L (about 12 h).

## 2. Verdict

The issue is not fully satisfied and should stay open. Item 1 looks done. Item 2 is partly done: the code to adopt cah-00 exists, but whether the plan is a no-op today can only be seen in the Spacelift console. Two follow-on gaps (section 5) are not in the done-when list and are worth adding to it.

## 3. Done-when items

### Item 1. Private repo with GYST callers and gitleaks

Status: done (structure confirmed by a read-only look; the maintainer should glance at the Actions tab to confirm it is still green).

Evidence in this public repo: only indirect. The README's last paragraph and `docs/wiki/Fork-Private-Stacks-and-the-Pipeline.md` describe the intended split (public modules, private stacks). The proof of item 1 lives in the private repository, so it cannot be linked from here.

Structural summary of the private repository: it exists, is private, is non-empty, and has a short merged history with a green CI on `main`. Its workflow calls the GYST reusable `tofu-ci` and `security` workflows pinned by commit with a version comment, runs a local `tofu test` job (GYST has no OpenTofu test leg yet), and ends in a gate job named `CI green`. gitleaks is switched on with its own config; CodeQL, dependency review and Semgrep are switched off with a stated reason (no GitHub Advanced Security on a private repository). It has a pre-commit config, OpenTofu test files, and a few docs pages (bootstrap, adding a stack, push policy).

Next step:
- Agent in the private repo: none required for this item. Optional: record, in the private README, the date the GYST pin was last checked (the lead's re-pin sweep already covers it).
- Maintainer: confirm on the private repo that branch protection requires `CI green`. The private README says `main` is the security boundary because the factory holds an organization-wide role, and a file cannot prove a repository setting. Cannot tell from here.

### Item 2. cah-00 imported, plan is a no-op

Status: partial. Code present; the live result cannot be told without the console.

What the code does (structural): an import block exists for the `cah-00-foundation` stack, matching the stack that this repo's `docs/stages/00-foundation.md` tells the maintainer to create by hand (project root `stacks/00-foundation`, OpenTofu, autodeploy off). Imports are switched by a variable, so after adoption the blocks are inert. The private bootstrap doc states the expected first plan: imports only, no create, no destroy.

Why this is not simply "done":
- The expected first plan is not strictly a no-op. The private bootstrap doc says it shows one change on the factory's own stack. That is the factory's change, not cah-00's, but the issue's wording ("plan is a no-op") should say "no create, no destroy, no change on cah-00".
- Whether the first run was confirmed, and what the plan looked like on the latest run, is held in Spacelift. A later commit message says a rebuild "is applied", which suggests at least one apply happened, but a commit message is not a plan.
- A drift check after import (a second plan that shows nothing at all) is the real definition of a no-op, and it is only visible in the console.

Evidence in this public repo: `docs/stages/00-foundation.md` (how the live stack is configured), `.spacelift/config.yml` stanza `cah-00-foundation` (its secret names), and `docs/spacelift-secrets.md` section 4 (the one-time setup that must stay true after import).

Next step:
- Maintainer in the Spacelift UI: open the factory stack's latest run and the latest cah-00 run, and report in the issue (a) whether the factory plan showed imports with no create and no destroy, and (b) whether a plan of cah-00 after adoption says "no changes". Take a screenshot yourself; do not paste it publicly. The maintainer must confirm every Spacelift change, so no agent triggers a run.
- Agent in the private repo (after the maintainer's report): if any diff was shown, fix the declared attribute (the usual causes are a description or label differing by a character) and open a pull request there. Do not apply.

## 4. Design questions that remain

### 4.1 One explicit stanza per stack

Decision recorded (the redo of the stack factory): every stack gets its own explicit stanza; nothing is generated from a loop or a pattern that could widen silently. The public repo already does this, and tests hold it:

- `.spacelift/config.yml` has one stanza per stack (`cah-00-foundation`, `cah-10-access`, `cah-20-telemetry`), each with its own `before_init` and `before_apply` hooks that name the exact secrets the stack may load.
- `tests/test_secret_separation.py` validates every stanza fail-closed. A stack name must match exactly one explicit provider pattern; a stack may request only its own cloud's secrets plus a short exact list of shared names; duplicate keys, anchors, aliases and folded scalars are refused; `before_init` and `before_apply` must be identical. The tests also assert that something was actually validated, so an empty config cannot pass.
- `tests/test_doppler_env.py` pins the hook script's inputs.

Open questions:

1. Two lists must agree. The public config lists the stacks that may load secrets; the private factory lists the stacks that exist. Nothing today fails if a stack is created in the factory with no stanza here (it would simply load no secrets) or a stanza here has no stack. Proposal: a check in the private repo's CI that fetches this repo's `.spacelift/config.yml` at a pinned commit and compares stack names, failing on any difference. That check belongs in the private repo and uses a public file, so nothing private leaks.
2. Coverage. The public config has a stanza for each of the three DigitalOcean stage stacks. The factory, by the structural look, does not yet declare all of them. Adoption of the remaining stage stack is the next increment, and the same applies to the AWS, Azure and GCP stack names the secret-separation tests already allow by pattern but that have no stanza yet. Each new stack needs both a stanza here and an entry there, in one pair of pull requests.
3. Where the policy bodies live. This repo holds the push and plan policies with Rego tests that run in CI (`.spacelift/policies/`). The private repo also carries a push policy. Two copies will drift. Decide one source of truth. Proposal: the tested bodies stay public (they contain no identifiers), and the private factory's policy resource reads the same text, or its CI diffs against this repo's file at a pinned commit.
4. The factory's own privilege. The private README states that the factory stack holds an organization-wide admin role and applies automatically. That is a deliberate, documented exception to "every workload stack is manual", but it sits against this repo's plan-policy autodeploy guard and the issue's gate ("every Spacelift change needs his confirmation"). Question for the maintainer: keep the factory auto-applying (merge to `main` is then the confirmation, and branch protection is the control), or make it manual like the others and accept that every account change waits for a click. This document recommends manual until the first month of adoption has passed without surprises, because the role can change every other stack.
5. Which objects the factory should own. Spaces, contexts and policies are named in the issue's first sentence. Context secrets (the Doppler read token) stay out of any repository and stay in the console, as `docs/spacelift-secrets.md` section 2 says. Decide, per object, adopt or leave alone, and write it in the private README.

### 4.2 How the factory is tested with mocked providers

The pattern already exists in this repo: each stack has `tests/*.tftest.hcl` files that use `mock_provider` blocks, so `tofu test` runs with no account, no token and no network, in GitHub Actions on every pull request (`stacks/00-foundation/tests/`, `stacks/10-access/tests/`). The same pattern applies to the factory, with its own provider mocked:

- Plan-mode tests with the Spacelift provider mocked assert the declared shape: every workload stack manual (the factory stack is the open exception), deletion protection on, project roots as expected, labels present, the context auto-attach label present.
- A guard test proves the rule bites: a stack declared with autodeploy on, or with an admin role other than the factory's, must fail the plan (the private repo already carries this kind of negative test).
- A hygiene test scans the configuration text for secret-shaped values and account-specific names, with a negative case.
- Import blocks cannot be proven by a mocked provider (an import needs the live object). Their proof is the first real plan in the console, which is why item 2 stays with the maintainer.
- Rego policy tests (`opa test`) stay where the policy text lives.
- All fixtures are built at run time; no secret-shaped literal is committed (gitleaks scans all branch history).

## 5. Gaps beyond the done-when list

These are not in the issue as written. Suggested additions are in section 7.

1. Cross-repo agreement check (section 4.1 item 1).
2. Single source for policy text (4.1 item 3).
3. Decision on the factory's own autodeploy (4.1 item 4).
4. Remaining stage stack, and the other clouds, adopted by the same route.

## 6. What the public repo must keep

The factory moves definitions out of the public repo. It must not move the controls that make a stack safe:

1. Workload stacks (the stacks this repository defines: cah-00, cah-10, cah-20 and later ones) stay locked and manual. The stack-protection setting is on and autodeploy is off for each of them. The factory's own stack is the open exception, undecided until section 4.1 item 4 is resolved; until then it is not covered by this rule. `docs/stages/00-foundation.md`, `docs/wiki/Spacelift.md` ("Why autodeploy is off") and the guard table in `docs/spacelift-secrets.md` state this and must keep stating it.
2. The plan policy's autodeploy guard and destroy guard (`.spacelift/policies/plan.rego`, with `plan_test.rego`) stay and stay tested. The guard blocks the apply of a stack that has autodeploy on; the factory's own tests block creating one.
3. The push policy that never proposes a run (`push.rego`, with `push_test.rego`) stays, with its reasoning about pull-request code never running next to the Doppler context.
4. `.spacelift/config.yml` and `scripts/spacelift/doppler-env.sh` stay public, with the per-stack stanzas and the fail-closed tests. They are code, not identifiers: secret names are not secrets.
5. The README's rule holds: no tokens, tenant names, hostnames or account identifiers in this repository. The private repo may hold the names; this one holds code and docs.
6. Nothing about adoption authorizes a run. Every Spacelift change still needs the maintainer's confirmation in the console, as the issue's gate says.

## 7. Proposed issue-body update (plain list, for a comment)

- Repository created: yes (private, with GYST `tofu-ci` and `security` callers, gitleaks on, `CI green` gate). Item 1 can be ticked once the maintainer confirms branch protection requires `CI green`.
- Item 2 is partly done: the adoption code and the expected first-plan description exist in the private repo; the live result (imports with no create and no destroy, then a "no changes" plan for cah-00) needs the maintainer to read it in Spacelift and report here.
- Reword item 2 to: "cah-00 imported; the first plan shows imports only, no create, no destroy and no change to cah-00; a second plan shows no changes."
- Add: the remaining stage stack (cah-20-telemetry) is adopted by the same route, one explicit stanza here and one entry in the factory.
- Add: a check in the private CI that compares the factory's stack list with this repo's `.spacelift/config.yml` at a pinned commit.
- Add: one source of truth for the push and plan policy text.
- Add: maintainer decision on whether the factory's own stack stays auto-applying or becomes manual (recommendation: manual at first).
- Keep as non-negotiable: every workload stack locked and manual (the factory stack is the open exception, section 4.1 item 4), plan-policy guards and their tests stay in this repo, no Spacelift change without the maintainer's confirmation.
- Owners: maintainer does the console reads and decisions; an agent in the private repo does the list-comparison check, the policy-source change and the extra stack entry; an agent in this repo does docs and tests only.

## 8. Not verified

- Anything in the Spacelift console: run history, current plan, whether stacks are locked there, whether a plan policy type is available on the plan.
- Whether branch protection is on for the private repository.
- That the private repository's CI is green today (last known state read from its latest runs, 2026-10-22).
- No code was run for this document other than the repository's test gate.
