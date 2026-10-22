# Clouds Against Humanity: composable hands-on labs with transparent cost

> **Proposal for the maintainer. Nothing is built, nothing is approved, nothing is applied.** This note proposes a lesson contract, a folder layout, a cost-menu script and a guard test. It writes none of them. It changes no stack, no module, no manifest, no price table and no ceiling.

Status: DRAFT for review. Date: 2026-10-22. Based on main `a11dac2`, fetched 2026-10-22.
Tooling: OpenTofu throughout.
Scope: how every build-type lesson lets a learner build one piece, several pieces, or the whole thing, and how every such lesson states its cost the same way before the learner spends anything. It is not an implementation plan and it does not touch the maintainer's own deployment or cost gate.

How this was produced. Read in full from the repository on 2026-10-22: `docs/wiki/How-Money-Works-in-the-Cloud.md`, `docs/cost.md` (headings and the parts quoted), `docs/cost-prices.json`, `docs/cost-prices/aws.json`, `docs/stages/approved.json` (first phases), `scripts/cost_check.py` (the type tables, the walk, the HCL scan and the structure checks; the plan-JSON half was skimmed), the Teardown Checklist (sections 1 to 3), the stack-per-service design (read from `origin/docs/stack-per-service-design`, sections 1 to 4), the Roadmap, and the "Cost and teardown (read first)" sections of the merged virtual-machines lesson. Read in part, by grep and excerpt, from origin refs: the F3, F5, F6 and F10 lessons, honeypot Tracks 2 and 3, I1 to I3 (`OpenTofu-From-Zero`, `Plans-State-Drift-and-Recovery`, `Spacelift-From-Zero`), `Twingate-Service-Accounts-in-CAH` and `Zero-Trust-at-Home-Two-Connectors-and-Failover`, and the foundations gap audit. The W lessons were added after the first draft: PRs #216, #217, #219 and #220 (heads fetched 2026-10-22; their cost and piece-table sections read by grep and excerpt, the pages not read in full). The I-series is PRs #209 to #212. Not read: the full text of I4, the full text of honeypot Track 2 and Track 3 pages beyond their cost lines, and the W pages beyond the excerpts above. Everything marked **est.** below is inferred.

## 1. The principle

The maintainer's words, 2026-10-22:

> "The lessons for all these builds must all be able to have the ability to do it piecemeal to be terraformed or the whole thing as a massive enterprise network launch, so they have the most control over the lessons they can afford. Be mindful of that some of the users may have more disposable income than others so it's not that we have a ceiling per se, it's that we need transparency and realistic expectations set for these users."

What follows from it, in four rules this note keeps returning to:

1. **Every build can be taken in pieces or whole.** The learner chooses the pieces they can afford, in a stated order, and the whole is the same pieces composed, not a different thing.
2. **Transparency, not a ceiling.** The project's own gate (`scripts/cost_check.py`, `docs/stages/approved.json`) is a ceiling on the maintainer's deployment, because that is the maintainer's money. A learner's bill is the learner's. For them the project sets no limit; it sets honest numbers and realistic expectations.
3. **Reading and free exercises are free forever.** The own-account path is optional. The wording for it is "optional own-account path", never "paid".
4. **Nobody is graded by their wallet.** A reader who builds the whole enterprise network and a reader who builds one machine for an hour finish the same lesson.

Standing rulings this builds on: services are separate stacks, one per service (`2026-10-22-stack-per-service.md`, question 1 to 3 ruled); hands-on for learners uses their own accounts and bills; no affiliate lines.

## 2. The lesson contract

A **build-type lesson** is any lesson with an own-account path: one that tells the learner to create something that a cloud provider or a vendor can bill for. Lessons that only touch the learner's own computer are not build-type lessons for this contract, though they may still use the free local variant described in section 2.2.

Every build-type lesson ships three things.

### 2.1 A piece table

One table, near the top of the optional own-account section, with one row per piece. A **piece** is the smallest part that can be created and destroyed alone: one stack in the lab layout, in the sense of the stack-per-service ruling.

| Column | Meaning | Source |
|---|---|---|
| Piece | Short name, matching the stack folder name | the lesson |
| Depends on | Pieces that must exist first (empty for a root piece) | the lesson |
| Cost per hour | From the price table, with the arithmetic shown | `docs/cost-prices.json` or `docs/cost-prices/<provider>.json` |
| Cost per month | The same, at the table's `hours_per_month` where it has one | same |
| Build order | A number; pieces with the same number are independent | the lesson |
| Destroy order | The reverse of the dependencies, as a number | the lesson |
| Teardown proof | The read-only command and the expected empty result | the lesson, following the Teardown Checklist section 3 |

Rules for the table:

- Every figure carries the price table's retrieval date, once, under the table: "Prices from `docs/cost-prices.json`, retrieved 2026-10-21." A figure not read from a vendor page or the price table is marked **est.**
- A free piece (a network, a tag, a firewall, a state file) is a row with $0, because the learner needs it in the build order and the destroy order.
- Money that the price table does not cover (data transfer, snapshots, logging, anything made by hand, a vendor plan) is listed in a final row "Not in this table" with the reason, not left out. The AWS table already says what it does not price: "data transfer, logging, snapshots, anything created outside OpenTofu".
- A DigitalOcean hourly rate is not in `docs/cost-prices.json`; the existing lessons deliberately give none ("I did not read an hourly rate"). Dividing the monthly price by 730 would understate the hourly charge when the provider caps a month at 672 hours (it would give $5.52 for a $6 droplet, below the listed $6), so the table must not do that. Until the real rate is read, the piece table shows the monthly figure as the authority and an hourly figure labeled **est., monthly price divided by 672 (the provider's cap), not a vendor rate**, which rounds up rather than down. Question 3 asks whether to read and record the real hourly rates once, so the **est.** can go. AWS keeps its table's own hourly prices.

### 2.2 Three build modes

Each lesson offers all three, and says which are free.

| Mode | What the learner does | Shows | Cost |
|---|---|---|---|
| A. By hand | The console or `doctl`/`aws` commands, one piece at a time | What each piece is, with no tool between the learner and the provider | The pieces chosen |
| B. One OpenTofu stack per piece | `tofu init/plan/apply` in each piece's folder, in build order | The stack-per-service shape: separate state, separate plan, separate destroy | The pieces chosen |
| C. One composed launch | One composition root that calls every piece's code and applies the lot, with a plan read first | The "massive enterprise network launch": the same pieces at once | The sum of every piece; the cost menu says so before apply |

Modes A and B are the "piecemeal" the maintainer asked for. Mode C is the "whole thing". A learner can mix: build two pieces by hand, one by stack, and compose later; the contract only requires that the lesson makes it possible and the piece table is true for each.

**Free local variant.** Where a lesson's idea can be shown without a cloud account, it ships a local variant next to the cloud one, using providers that touch only the learner's own computer (`local`, `random`, `terraform_data`, as I1 to I3 already do), or containers on the learner's machine. The local variant uses the same piece names, the same dependency order and the same three modes. A learner with no account, or no wish to open one, learns the same shape for $0. The cloud variant is the optional own-account path.

### 2.3 A transparent cost box

A fixed block at the top of the own-account section, replacing today's per-lesson free-form "Cost and teardown (read first)" text (that heading already exists in at least F3, F5, F6, F10 and the working-in-a-company lesson, so the idea is established; this fixes the wording). Proposed fixed wording, with the bracketed values filled per lesson:

> **Cost box. Read this before you create anything.**
>
> **What is estimated.** Every dollar figure here comes from [price table], retrieved [date], for [provider and region]. Prices change; check your provider's page before you build. Anything marked est. is my arithmetic or a guess, not a vendor figure.
>
> **If you forget it.** With every piece in the table built and left running, the bill is about **$[x] a day and $[y] a month**. A machine that is powered off is still billed; only destroying it stops the bill.
>
> **Not covered by this estimate.** [data transfer, snapshots, logging, vendor plans, anything you create outside the code].
>
> **A spend alert is not a spending cap.** It sends an email; it does not stop anything. Set one before you build: [link to the provider's budget page] and see [How money works in the cloud](How-Money-Works-in-the-Cloud.md#1-a-billing-alert-before-anything-else). The project sets no limit for you; the choice of how much to build is yours.
>
> **Teardown first.** Read the teardown steps and the proof commands below before you run anything, and set a reminder for the time you plan to destroy. Destroy in the reverse of the build order.
>
> **You can stop at any piece.** Each piece works and teaches on its own. [Free local version] covers the same ideas for $0.

The wording is fixed by a test (section 6), the way the feedback footer is.

### 2.4 The layout convention for learner-facing example code

Proposal: a top-level `labs/` directory. It already exists with one entry, `labs/demo-monitoring` (a Docker Compose demo with its own structure test, `tests/test_demo_monitoring.py`), so the directory is established and `labs/` is the right home; the new folders sit beside it. Nothing in `labs/` is a stack of the project.

```text
labs/
  demo-monitoring/                  (exists today, unchanged)
  <lesson-id>/                      one folder per lesson, e.g. vm-lab, backups-lab, cowrie-weekend
    README.md                       points at the wiki page; holds nothing the page does not
    pieces.json                     the piece table as data (section 3 reads it)
    cloud/
      <piece-name>/                 one subfolder per piece; a complete OpenTofu root module
        main.tf  variables.tf  outputs.tf  versions.tf
        tests/<piece>.tftest.hcl    mock_provider test, no credentials
      compose/                      the composition root (mode C)
        main.tf                     calls each ../<piece> as a module, wires outputs to inputs
        variables.tf                one enable_<piece> flag per piece, all default false
        tests/compose.tftest.hcl
    local/
      <piece-name>/                 the free variant: same names, local providers or containers
      compose/
    scripts/                        helper scripts, if the lesson has any (set -euo pipefail)
```

Conventions:

- **Flag-off defaults.** Every `enable_<piece>` in the composition root, and every piece's own `enabled`, defaults to `false`. `tofu plan` on a fresh checkout creates nothing. This copies the stack-factory habit (the telemetry stack's `logging_enabled` and `metrics_enabled` default to false).
- **Same code, two entry points.** Mode B applies `cloud/<piece>/` directly. Mode C applies `cloud/compose/`, which calls the same piece folders as local modules, so mode B and mode C cannot disagree about what a piece is. Cross-piece values flow through outputs and inputs, never by a hard-coded name; in mode B the learner passes the previous piece's output as a variable (the lesson shows the exact line).
- **No credential in the repository.** Variables for tokens carry no default and are read from the learner's environment. The tests build any fixture at run time.
- **Nothing the project's Spacelift or stacks ever applies.** No `labs/` path appears in `.spacelift/config.yml`, no stack's `project_root` points there, no `modules/` or `stacks/` code sources from `labs/`, and the plan policy is not attached to anything there. A guard test (section 6) fails if a `labs/` path appears in `.spacelift/`.
- **A pinned provider and a pinned region per piece**, so a lab's price table and its code name the same thing.
- **Reuse of the real modules.** Where a lab piece is the same thing as a real module (a droplet behind a firewall), prefer a lab `module` block pointing at the repository's own `modules/<name>` by relative path, so the lab teaches the real code and cannot drift from it. This is possible only if the gate's module-source rule allows it from `labs/` (see the finding below); otherwise the lab carries a small copy and the drift test in section 7 covers it.

**Finding: the cost gate reads `labs/` today.** `scripts/cost_check.py` walks the whole repository, skipping only `.git`, `.venv` and `.claude` at the top level, and its allowlist check (`uncosted_sources`, over `file_blocks`) reads every `*.tf` and `*.tofu` file it finds, not only those under `stacks/` and `modules/`. Only the stack-manifest rule is limited to `stacks/`. So a `labs/vm-lab/cloud/droplet/main.tf` containing a `digitalocean_droplet` resource would fail the maintainer's gate as an unapproved costed type in an unlisted file. The same would hold for any lab resource of a known cloud that is not on the free list, and for `count`/`for_each` on a costed resource (`block_problems`). I read this from the source; I did not run the gate against a `labs/` tree (**est.**, run it before relying on this).

Ways to resolve it, for the maintainer to choose (question 4):

| Option | How | Cost |
|---|---|---|
| L1. The gate skips `labs/` for the type allowlist and the costed-type rules, but still reads it for HCL syntax | One reviewed change: a `LABS_DIR` constant excluded in `file_blocks`/`uncosted_sources`, with a test that proves a droplet under `labs/` passes the gate and under `stacks/` still fails | Small. The gate stays the maintainer's. Labs are tested by their own jobs (below) |
| L2. A separate repository for the labs | New repo, GYST caller, its own CI | Medium. Cleanest separation, but a lesson and its code live apart, which invites drift |
| L3. Lab code stored as `*.tf.txt` or `*.tf.example`, copied to `*.tf` by the learner | No gate change | Small, but the code is never validated by `tofu validate` unless CI renames it, which is a workaround, not a design |

**Decision: L1 chosen.** The maintainer approved L1 on 2026-10-22 (issue #250). The exemption skips only the type allowlist, the `count`/`for_each` rule and the module-source rules, still reads every `.tf` file under `labs/` for syntax, and applies to the top-level `labs/` directory alone (real path, case-sensitive, no symlink or `..` widening). It is not an approval, Spacelift does not apply it, and it is not counted in project spend. The rules are in `docs/cost.md` ("The labs/ exemption") and pinned by `tests/test_cost_check_labs.py`. The text below is the original recommendation.

I recommend **L1**: the gate is a tool for the maintainer's deployment, labs are explicitly outside it, and a test pins the boundary in both directions (labs skipped; stacks not).

**How labs stay outside the cost gate yet stay tested.** Labs get their own CI job, not the gate:

- `tofu fmt -check` and `tofu validate` in every `labs/**/<piece>/` and `compose/` folder, with providers initialized but no credential.
- `tofu test` with `mock_provider` blocks, the pattern the repository's modules already use (`modules/aws/firewall/tests/firewall.tftest.hcl` begins `mock_provider "aws" {}`). Mock tests assert the flags-off plan creates nothing, and that each flag creates exactly the expected resource types. This runs in the existing GYST `tofu-ci` workflow by adding the lab folders to its `directories` input, which is a one-line change per folder (**est.**: I read the input in `ci.yml`, not the reusable workflow's code).
- The piece table's data (`pieces.json`) is checked against the price table by a Python test: every size named exists in the table, and the figures the lesson prints equal the figures the table gives (section 7).

No lab job holds a cloud credential. A pull request may not have one.

## 3. The cost-menu tool

Proposed, not written: `scripts/cost_menu.py`. It answers one question for a learner before they build: "I picked these pieces; what do they cost?"

### 3.1 Behavior

```text
python3 -I scripts/cost_menu.py --lesson vm-lab --pieces network,droplet
python3 -I scripts/cost_menu.py --lesson vm-lab --all
python3 -I scripts/cost_menu.py --pieces-file my-pieces.json
python3 -I scripts/cost_menu.py --lesson vm-lab --all --json
```

It reads `docs/cost-prices.json` (or `docs/cost-prices/<provider>.json` by the piece's provider, the same lookup as the gate's `price_table_path`), reads the lesson's `labs/<lesson>/pieces.json`, adds the chosen pieces with their dependencies (it warns and adds a missing dependency rather than silently pricing a piece that cannot exist alone), and prints:

```text
Lesson: vm-lab   Prices: digitalocean, retrieved 2026-10-21   (check the provider's page)
Piece           Hourly (est.)   Monthly   (DigitalOcean: monthly / 672, est.)
network         $0.0000         $0.00
droplet         $0.0090         $6.00
-----------------------------------------
Total           $0.0090/h       $6.00/month
Per day, if left running:   $0.20 (est.)
Forgotten for a month:       $6.00, plus anything in "Not in this estimate"
Not in this estimate: data transfer, snapshots, anything created by hand.
A spend alert is not a spending cap. Teardown first: see the lesson's cost box.
```

(Figures in the sample are arithmetic from the DigitalOcean $6 size: $6 / 672 = $0.0089, shown rounded up as $0.0090; $6 x 12 / 365 = $0.20; the hourly is **est.** for the reason in section 2.1, and it is not a vendor rate.)

Rules:

- **Same schema where possible.** The piece list reuses the cost gate's manifest shape: `{ "resources": [ { "name": ..., "kind": "droplet", "size": ..., "backups": false } ] }` for DigitalOcean, and `{ "kind": "instance", "type": ..., "root_gb": ..., "public_ip": ... }` for AWS, priced by the gate's own functions (`resource_cost`, `droplet_cost`, `aws_instance_cost`), imported rather than copied, so the menu and the gate cannot disagree about a price. `pieces.json` adds only what the gate has no use for: `piece`, `depends_on`, `build_order`, `destroy_order`, `proof_command`, `unpriced` and `local_variant`.
- **Unknown is refused, not zero.** A size not in the table, a kind the gate has no price model for (a Spaces bucket, a snapshot, a vendor plan), or a table with no retrieval date makes the tool print "not priced" and exit non-zero for that piece. The gate's own stance ("no price for size", "a missing plan is refused") carries over: a missing price must not read as free.
- **Backups.** Priced only as the gate prices them: the weekly plan at `backups_fraction`, and only while `backups_fraction_verified` is true. Anything else is refused.
- **Retrieval date printed, always**, with a stale-date warning past a threshold (section 7).
- **No network, no credential, no write.** It reads two local files and prints. It never calls a provider's API.
- **`--json`** prints the same numbers as data, for the wiki generator and the tests.
- **Not the gate.** It has no ceiling, no `approved.json`, no pass or fail on a total. It reports. It reads `docs/cost-prices*.json` and never `docs/stages/approved.json`, so the learner's menu cannot be confused with the maintainer's approval.

Why a script and not a table alone: a table in a lesson goes stale silently; a script reading the same file the gate reads goes stale only when the price table does, and the section 7 test catches the lesson's printed figures drifting from it.

### 3.2 How the wiki shows "pick what you can afford" menus

Each build-type lesson gets a short **tiers** table after the piece table. Tiers are described by **capability**, not by price judgments. The cost column is a fact in the same row, from the script's output, and the tier names say what you can do:

| Tier | What you can do with it | Pieces | Cost while it exists |
|---|---|---|---|
| Read and local | Follow every idea, run the free exercises | none in a cloud | $0 |
| One machine | Do the hands-on exercise end to end on one real host | network, one machine | $[x] a month if left running |
| A small network | Add a second machine and a firewall rule between them | the above plus a second machine | $[y] |
| The whole thing | Compose every piece the lesson describes | every row of the piece table | $[z] |

Rules for these tables: no "cheap", "budget", "basic", "starter" or "premium" as tier names; no tier is marked "recommended" by price; the same exercises, the same checkpoints and the same completion are available at every tier that can run them, and a lesson says plainly which exercises need which tier. Where the whole thing exceeds what the provider's free allowances or the project's own reference environment cost, the page says what that is (for example the `learner-soc` row in the Roadmap, which already lists a worked $35 to $53 range) instead of hiding it.

## 4. Tone rules

For every lesson, box and menu:

1. **No ceiling per se.** The page never says "you should keep this under $X" for the learner. It may describe what the maintainer's own deployment is held to, as a fact about that deployment, and it labels it so.
2. **Honest numbers.** Every figure has a source and a date or the word est. Round up only where the source does; never round down to look gentler.
3. **Realistic expectations.** State what the whole build costs per day and per month if forgotten, what is not in the estimate, and how long the exercise really takes. Say when the full build is a lot, and say it once.
4. **Nobody is graded by their wallet.** The lesson's checkpoint, completion and credit never depend on the tier built. A reader with more to spend gets no extra praise and no extra content gated behind spending; a reader who builds nothing in the cloud has finished the lesson.
5. **No upsell.** No "upgrade to", no "for the best experience build the whole thing", no affiliate or referral line, no pushing a provider. Provider choice is described by what differs (capability, region, how teardown works), not by which to buy.
6. **No budget shaming.** Never "if you can afford it", "only $6", "just", "a small price", "pennies". A number is a number. Do not use "paid" to describe the own-account path; say "optional own-account path". Do not call a cheap path the "poor man's" anything.
7. **Teardown is part of the lesson, not an afterthought.** It comes before the build, it is ordered, and it ends in a proof.
8. American English, plain words, a definition for each unfamiliar term at first use, as elsewhere in the wiki.

## 5. Retrofit table

Existing and in-flight build-type lessons, what each needs, size and a proposed sprint using the Roadmap's S1 to S8 (S1 2026-10-20 to 2026-11-02, then two-week sprints to S8 ending 2027-02-08). Sizes use the planning page's conversion (S = 2 h, M = 5 h, L = 12 h, XL = 30 h) for the retrofit work only, not for writing a lesson from scratch. "Merged" means on main at `a11dac2`; "in flight" means on an origin branch only.

| Lesson | State | Own-account path today | Pieces and stacks it needs | Size | Sprint |
|---|---|---|---|---|---|
| F3 How a web request works | merged | Two droplets, one private network, up to $12 a month (est., gap audit) | `network` (free), `web-server` (no public inbound), `client` (SSH from the learner's own /32). Three stacks; compose = all three | M | S3 |
| F5 Subnets, routing, NAT, firewall by hand | merged | Same two-droplet shape, up to $12 a month (est.) | `network`, `target`, `scanner`, `firewall-rule` (the deliberate wrong rule is a piece so it can be added and removed alone). Four stacks | M | S3 |
| F6 VMs, containers, cloud service models | merged | One `s-1vcpu-1gb` droplet at $6 a month (lesson, retrieved 2026-10-21); audit said $0, the lesson added the optional VM | `network`, `vm`. Two stacks. Local variant: a container on the learner's machine (already the lesson's main path) | S | S3 |
| F10 Backups, recovery and patching | merged | One droplet; up to about $7.20 with weekly backups (6 + 20 percent, est.) | `network`, `vm`, `backup-plan` (the backup setting as its own piece, since it is the costly add-on). Three stacks. Local variant: the lesson's tar-and-verify lab | M | S4 |
| Honeypot Track 2 (cloud Cowrie weekend) | in flight (`docs/honeypot-track2-cloud-cowrie`) | One `s-1vcpu-1gb` droplet, $6 a month (lesson line, read) | `network`, `sensor-host`, `cowrie`, `log-shipping`. Four stacks; the sensor is the stack that must stay in a separate account by design (honeypot design, section 3), so its stack folder documents that it is never composed into a core account | L | S4 |
| Honeypot Track 3 (T-Pot at home) | in flight (`docs/honeypot-track3-tpot`) | Own hardware; an optional small cloud relay at $6 a month (lesson, read) | `relay-host` (cloud, optional), `tunnel`, `home-honeynet` (the learner's own hardware, local variant only). Two cloud stacks plus a local one | M | S5 |
| I1 OpenTofu from zero | in flight (`docs/iac-1-opentofu-from-zero`) | Free path only; optional own-account path is a small cloud resource (page read in part) | Already local-provider based. Needs a piece table with `scratch-folder` and an optional `cloud-resource`. One cloud stack | S | S4 |
| I2 Plans, state, drift, recovery | in flight (`docs/iac-2-plans-state-drift`) | Optional: move scratch state to a bucket in the learner's own account | `scratch-state` (local), `state-bucket` (cloud, flat monthly fee for object storage: $5 for the provider's flat plan per `How-Money-Works`, est. for the lab's use). Two stacks | S | S4 |
| I3 Spacelift from zero | in flight (`docs/iac-3-spacelift-from-zero`) | Free plan, no cloud; scratch stacks use `terraform_data` only | `scratch-stack` only; a plan-limit row for any step needing a higher Spacelift plan (read: policies are a higher-plan feature). One stack | S | S5 |
| I4 Stack per service | in flight (`docs/iac-4-stack-per-service`) | Not read (est.): likely the lesson that teaches this note's own shape | It should become the lesson that introduces piece tables and the composition root; the layout in section 2.4 should be taught here first. Cost depends on its exercises | M | S5 |
| W lessons, PR #216 `LAMP-and-LEMP-From-Zero` | in review (PR head read in part) | Free local lab; optional droplet `s-1vcpu-1gb` $6 or `s-1vcpu-2gb` $12 a month (page, retrieved 2026-10-21) | Already has a six-row piece table (network and firewall, database, PHP, web server, WordPress, TLS), build and destroy orders, the three modes, and `modules/db`, `modules/web`, `stacks/` local-provider examples. Needs: hourly and teardown-proof columns, the fixed cost box, `pieces.json`, move examples under `labs/` | S | S4 |
| W lesson, PR #217 `DNS-Cloudflare-and-Hosting-Your-Own-Website` | in review | Free local DNS lab; Cloudflare Free $0; one `s-1vcpu-1gb` droplet $6 a month; a forgotten droplet "about $0.20 a day and $6 a month (est.)" in the page; domain fee and Route 53 $0.50 per zone listed | Already has a piece table (domain, DNS zone, origin server, origin firewall, TLS, Cloudflare proxy and WAF) with cost, build order and destroy order, and a forgotten-resource line. Needs: teardown-proof column, fixed cost-box wording, `pieces.json`, lab code | S | S4 |
| W lesson, PR #219 `WordPress-and-PHP-Security-WAF-and-Static-Sites` | in review | Exercises run locally (PHP, `curl`, optionally Docker or Podman); no cloud resource found by grep (est.) | No piece table found; probably none needed. Confirm it is not a build-type lesson under section 2; if it links to a build, point at the piece tables in PR #216 and #220 | S | S4 |
| W lesson, PR #220 `WordPress-at-Scale-CDN-WAF-and-CI` plus `labs/wordpress-at-scale/` | in review | Free local lab (compose, a local pipeline); the cloud tiers in a 12-row piece table: origin node $12, managed database from $15, load balancer $12 per node, Spaces $5, CDN Free $0 or Pro $25; a five-level menu (just the origin $12; origin plus CDN $12 or $37, and more) | Closest to this contract today: piece table, tiers by build level, three build modes. Needs: the fixed cost box and `pieces.json`; its lab is a compose lab (`lab.sh`, `compose.yaml`), the first learner lab under `labs/`, so it sets the layout precedent. Section 2.4's `cloud/` and `local/` subfolders must either adopt its flat shape or it must be regrouped (question 12) | M | S5 |
| Twingate service accounts in CAH | in flight (`docs/twingate-service-accounts`) | Read: service accounts are not on the free Starter plan; a vendor plan is the cost, not a cloud resource | `twingate-network` (free tier), `service-account` (needs a higher vendor plan). The piece table's cost row is "see the vendor's pricing page, retrieved 2026-10-22" with no number written down, since the vendor price was not recorded in the repository | S | S5 |
| Zero trust at home (two connectors and failover) | in flight (`docs/zero-trust-at-home`) | Own hardware (two Raspberry Pis or two VMs) or two small cloud instances, "at the provider's price" | `remote-network`, `connector-a`, `connector-b`, `failover-test`. Same two-connector shape as stage 1 (two `s-1vcpu-1gb`, $12 a month in the reference); local variant: two containers, which the lesson already has (exercise 2) | M | S5 |
| Build your own mini SOC (existing, merged) | merged | The Roadmap's `learner-soc` examples, $35, $41, $47, $53 | The N0, N1, S1 stages are already pieces; give them the contract's table and the cost box. Four to five stacks | M | S6 |

Total retrofit, by the sizes above: 8 S, 8 M and 1 L is roughly 16 + 40 + 12 = 68 hours (**est.**); fits S3 to S7 with the tool and the guard test (section 6) as the first items. Order of work: the tool, the layout and the gate boundary (L1) first, in S3, because every retrofit depends on them; then F3/F5/F6/F10, then the in-flight lessons as they merge, so each merges with its table and box instead of being retrofitted after.

## 6. Proposed guard test

Describe only, not written: `tests/test_lab_contract.py` (**est.** name), run in the existing pytest job, with no network.

1. **Find the build-type lessons.** A wiki page is build-type when it contains a heading matching `Cost and teardown` or `Optional own-account path`, or links to `docs/cost-prices.json`, or contains a cloud CLI or `tofu apply` command in a fenced block under such a heading. The match rules are in one table at the top of the test so a new lesson shape is a one-line addition.
2. **Require the piece table.** For each such page, the test requires a table whose header row has the seven columns of section 2.1 (named exactly), at least one row, and a retrieval date next to it in the form `retrieved YYYY-MM-DD`.
3. **Require the cost box.** The page must contain the fixed cost-box block of section 2.3, matched on its six bold lead phrases in order (**What is estimated**, **If you forget it**, **Not covered by this estimate**, **A spend alert is not a spending cap**, **Teardown first**, **You can stop at any piece**) and must not contain any wording the tone rules ban (`paid`, `cheap`, `just $`, `only $`, `affordable`, `budget` as a judgment; a short banned-phrase list in the test).
4. **Require the labs folder.** For each such page whose piece table names `<lesson-id>`, `labs/<lesson-id>/pieces.json` must exist and match the schema (every piece named in the table, `depends_on` acyclic, build order consistent with dependencies, destroy order its reverse), and `labs/<lesson-id>/cloud/<piece>/` and `local/<piece>/` must exist for each piece (a piece with no local variant is listed in `pieces.json` as `"local_variant": null` with a one-line reason).
5. **Flags off.** For each composition root, every `enable_` variable has `default = false`; the test parses variables with a small HCL reader (the gate's own scanner is reusable) or greps a strict pattern.
6. **Boundary.** No path under `labs/` appears in `.spacelift/` or in `stacks/`; no `stacks/` or `modules/` file has a `source` pointing into `labs/`.
7. **Wording.** The cost box's per-day and per-month figures in the page equal the script's output for the full piece list (section 7).
8. **An allowlist for pages not yet retrofitted**, in the test, with a removal date per page, so the test can be merged first and the allowlist shrinks as lessons are retrofitted. A page on the allowlist past its date fails the test.

The test fails with the page name and the missing item, so the author fixes one thing at a time.

## 7. Risks

| Risk | What goes wrong | Mitigation |
|---|---|---|
| Labs drift from the real stacks | The lab teaches a droplet module that no longer matches `modules/`; a learner follows a lab that the project no longer builds that way | Prefer real `modules/` by relative path from labs where the gate allows (L1); a CI job runs `tofu validate` and mock `tofu test` on every lab folder on every pull request; the lab's folder README names the module version or commit it mirrors; a Python test compares the resource types a lab piece declares with the type its piece-table row prices |
| Price staleness | The table says $6 and the provider says $8; the cost box misleads | Every figure carries the table's retrieval date; the script prints the date and warns past 90 days (threshold **est.**); a test fails when the lesson's printed totals differ from the table; the re-read of the table is already a maintainer step (`docs/cost.md` records the last live read); the box tells the learner to check the provider's page before building |
| Provider API changes | A pinned provider version breaks, or a resource is renamed, so a lab fails for a learner on day one | Pin the provider per piece; mock tests exercise the resource schemas; `tofu validate` with a locked version in CI; the lesson states the version it was written against and the date, as the stage guides do. Real-provider behavior is not tested by CI (no credential), so each lesson says which steps were run and which were not, as the existing lessons already mark |
| Unpriced pieces read as free | A bucket, snapshot or vendor plan the table has no model for looks like $0 | The script refuses unknown kinds; the piece table's "Not in this table" row is required by the guard test; section 2.1 forbids dropping it |
| The cost box becomes boilerplate nobody reads | Fixed wording trained out of attention | Keep it six lines; put it at the top of the section, once; the numbers in it are different per lesson, which is the part to read |
| A composition root applies more than the learner meant | Mode C creates the whole set | Flags default to false; the lesson's mode C step runs the cost menu first and shows `tofu plan`; the cost box says so |
| Lab code reaches the maintainer's apply path | A path under `labs/` is picked up by Spacelift or the cost gate's manifests | Section 6 test 6 pins the boundary; no stack `project_root` may point at `labs/` |
| The gate change (L1) weakens the gate | Skipping `labs/` becomes a hole | The change skips only the type allowlist, not the HCL syntax read; a test proves a costed type in `labs/` passes and the same type under `stacks/` or `modules/` still fails |
| Learner-side security | A lab leaves a learner's machine exposed (an open SSH rule, a honeypot in the wrong account) | Existing lesson rules carry over: SSH only from the learner's own /32, removed at teardown; the sensor lab never in a core account; teardown proof ends each lesson |

## 8. Questions for the maintainer

1. **Which W number is which PR?** The LAMP page (#216) calls the DNS lesson "W3", while #217 is the DNS page. I listed them by PR and page title in section 5 and did not guess numbers. Please confirm.
2. **Is `labs/` the right top-level name?** It already holds `labs/demo-monitoring` and its test, so it fits, but that lab is a Docker Compose demo for the maintainer's stack, not a learner build. Do you want learner labs mixed in, or a subfolder such as `labs/learn/`?
3. **Should the real hourly rates be read and recorded?** The price table has monthly figures only; the lessons give no per-hour figure for DigitalOcean on purpose. The cost box needs a "per hour" figure; the maintainer asked for it in the piece table. Option A: read DigitalOcean's hourly rates once and add an `hourly` field to the price table with its own retrieval date. Option B: keep the est. division by 672 (the cap), labeled as such, never by 730. I recommend A, because the box says "honest numbers".
4. **Which gate boundary: L1 (skip `labs/` for the type allowlist), L2 (separate repository) or L3 (`.example` files)?** I recommend L1. This is a change to the maintainer's own gate, so it needs your approval before it is written.
5. **Do lab pieces call the real `modules/` or carry copies?** Calling the real modules prevents drift but ties the lesson to module changes; copies are stable for learners but drift. I lean to calling the real modules where the gate allows it.
6. **Does the cost-menu script live in this repository or in git-your-ship-together?** Your standing rule says anything two repositories would both need belongs in GYST. This script reads this repository's price tables and manifest shape, so it is project-specific today; the generic part (sum a piece list against a price table) could be a GYST input later. Your call, but the first version is here.
7. **Learner pieces for providers other than DigitalOcean.** AWS has a table (`docs/cost-prices/aws.json`, retrieved 2026-10-16); Azure and GCP have none. Should labs be DigitalOcean-first, with AWS where the price table exists, and Azure/GCP lab variants held until their tables exist?
8. **Do you want the cost box in the shape above (six fixed lines), or shorter?** And: should it name the project's own reference spend ($12 to $29 a month, per the Roadmap) as context, or is that confusing next to a learner's own bill?
9. **Vendor plans (Twingate, Spacelift, others).** The price table has only cloud resources. For a vendor plan the box can only say "see the vendor's pricing page, retrieved on date". Is that acceptable, or do you want vendor plan prices recorded in a second table with retrieval dates?
10. **Retrofit order.** I propose the tool, layout and gate boundary in S3, then F3, F5, F6, then the rest as they merge. The honeypot and I-series lessons are already in review. Do you prefer to hold them until the contract exists, or merge them and retrofit after?
11. **Whose job is the guard test's allowlist date?** Pages not yet retrofitted need a removal date; I proposed putting them in the test. Do you want the dates set to the sprints in section 5?
12. **Which shape for lab folders?** PR #220 puts `labs/wordpress-at-scale/` flat (`lab.sh`, `compose.yaml`, `site/`, `ci/`), with no `cloud/` or `local/` split, and the W1 lesson (PR #216) uses `modules/` and `stacks/` folders for its local-provider examples. Do you want section 2.4's `cloud/<piece>/` and `local/<piece>/` layout applied to them (regroup) or relaxed to "one folder per lesson with a `pieces.json`"?
