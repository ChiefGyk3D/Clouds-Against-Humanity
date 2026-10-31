# Cost

Working ceiling: $30 per month in the current phase (`stage-3`). The ceiling is a decision per phase, kept in `docs/stages/approved.json` (see "Ceilings per phase" below), and a later phase may raise it on purpose. Each stage must be costed and approved before it runs.

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Two Twingate connector droplets (`s-1vcpu-1gb`, list price $6 each) | $12 | $12 |

The region is `tor1` (Toronto), chosen on 2026-10-11 after a new account got `422 Size is not available in this region` for the $6 `s-1vcpu-1gb` in nyc3. Check `GET /v2/sizes` and `GET /v2/regions` for your own account before picking a region: availability of the cheap legacy sizes differs by region and by account, and the newer US sites (Atlanta, Richmond, Kansas City, Memphis) start at about $18 for 1 GB.

Source of prices: `docs/cost-prices.json`, retrieved 2026-10-21 from the DigitalOcean sizes API (five sizes re-read live for tor1, table below; the file's prices were first read 2026-10-10 and none changed).

## Stage 3 estimate (not approved)

Stage 3 adds one Docker host running Portainer CE, five small daemons, an S3-compatible bucket for their state. The Discord-to-Matrix bridge is not part of it: etke.cc hosts the Matrix server and the bridge (ruled 2026-10-22, #254), so no bridge, no bridge database and no firewall rule are costed here. Recomputed from `docs/cost-prices.json` without the bridge, the figure is unchanged, because the bridge never had its own priced line and the droplet size rests on the daemons and Portainer. The jobs that already run on a timer move to DigitalOcean Functions. In the reference environment stages 2 and 4 are planned to add $0 to the cloud bill (logs and the Grafana run on-prem), so this is the only remaining paid stage there. A learner who builds their own cloud Grafana (option N1) or Wazuh manager (S1) pays $6 to $24 or more for one more droplet, which with stage 3 option A ($29) does not fit under $30; see the [settings and mini SOC design](superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) section 1.3 and the wiki page [Build your own mini SOC](wiki/Build-Your-Own-Mini-SOC.md). The design draft is [2026-10-11 stage 3 workloads](superpowers/specs/2026-10-11-stage-3-workloads-design.md); what it prices:

| Option | Droplet | Spaces bucket | Functions | Running | Fits $30? |
|---|---|---|---|---|---|
| A + bucket (recommended) | `s-1vcpu-2gb`, $12 | $5 flat | $0 within the free allowance | $29 | Yes |
| B, state on the host | `s-2vcpu-2gb`, $18 | none | $0 | $30 | Yes, with nothing left |
| B + bucket | $18 | $5 | $0 | $35 | Needs a $40 ceiling |
| C + bucket | `s-2vcpu-4gb`, $24 | $5 | $0 | $41 | Needs a $45 ceiling |

Prices read 2026-10-11: Spaces is $5 per month for 250 GiB stored and 1 TiB outbound transfer per account, then $0.02 per GiB stored and $0.01 per GiB out. Functions have a free allowance of 90,000 GiB-seconds per month per team, then $0.0000185 per GiB-second; the stage's expected use is near the allowance and an overage month would cost cents. Functions are deployed with `doctl`, not OpenTofu, so the gate cannot see them: their spend is a line someone checks on the usage page.

Droplet sizes verified available in tor1 on 2026-10-21 (read live from the DigitalOcean sizes API, regular `s-` family) and matching `docs/cost-prices.json`:

| Size | Memory | Disk | Transfer | Per month |
|---|---|---|---|---|
| `s-1vcpu-1gb` | 1 GiB | 25 GB | 1 TB | $6 |
| `s-1vcpu-2gb` | 2 GiB | 50 GB | 2 TB | $12 |
| `s-2vcpu-2gb` | 2 GiB | 60 GB | 3 TB | $18 |
| `s-2vcpu-4gb` | 4 GiB | 80 GB | 4 TB | $24 |
| `s-4vcpu-8gb` | 8 GiB | 160 GB | 5 TB | $48 |

The stage 3 pick, `s-1vcpu-2gb` at $12, is verified available in tor1 on 2026-10-21 and stays valid.

Status on 2026-10-31: the maintainer approved the full stage 3 scope ("Yes, full stage 3 scope"), so `stage-3` is the current phase at its planned $30 ceiling, the gate prices a `spaces` manifest entry as a flat $5.00 read from `docs/cost-prices.json` (source page and retrieval date are in that entry), and `approved.json` allows `modules/spaces-bucket/main.tf` for `digitalocean_spaces_bucket`. Nothing is built: the DigitalOcean `approved_monthly_total` stays $12.00 because no `cost.json` prices a Spaces entry yet and the module is switched off, so the bucket adds $0. The pull request that switches the bucket on adds the `spaces` entry to the stack's `cost.json` and raises `approved_monthly_total` to cover it ($17.00 with the bucket alone, $29.00 with the workload droplet, never above $29.00). Droplet backups are off in every row; the bucket's versioning and a nightly copy off the account are the backups. Block storage is not needed. The workload droplet's module is not allowed yet.

## Edge (DMZ) estimate (not approved)

The shared edge network (VPC, tags, Cloud Firewall) is written as `stacks/50-edge`, disabled, unapplied and free. Edge services are one droplet each, built later from `modules/edge-host` in their own stacks ([stage page](stages/05-edge.md)). Design option A ([edge DMZ design](superpowers/specs/2026-10-19-edge-dmz-design.md), section 5.1) priced one droplet:

| Line | Basis | Monthly |
|---|---|---|
| Edge droplet `s-1vcpu-1gb` | `docs/cost-prices.json`, retrieved 2026-10-21 | $6.00 each |
| Reserved IP, assigned | DigitalOcean pricing page as read in the design, 2026-10-19: free when assigned | $0.00 |
| `rns-dmz` VPC, Cloud Firewall | free types in the gate | $0.00 |

With one droplet per service the cost is $6.00 per approved service. The `edge` ceiling stays at its existing placeholder and is raised one approved service at a time; nothing is approved yet. A reserved IP that is not assigned costs $5.00 a month ($0.01 an hour, same page), so a failed apply that leaves the IP behind costs money until someone notices. The DigitalOcean total stays $12, and no `cost.json` prices a droplet: the gate has no `reserved_ip` manifest kind yet, so no service stack can be switched on. Outbound transfer is not priced and is not seen by the gate; check the usage page once an edge service runs (design section 5.7), the same way as Functions.

## Ceilings per phase

The ceiling is not one hard-coded number. `docs/stages/approved.json` holds an ordered map `phases`, one entry per phase of the project, and `current_phase` names the one the gate enforces:

```json
"current_phase": "stage-3",
"phases": {
  "stage-3": { "ceiling": 30.0, "reason": "why this number", "decided": "2026-10-31", "status": "current" },
  "stage-4": { "ceiling": 30.0, "reason": "...", "decided": "2026-10-16", "status": "planned" }
}
```

| Phase id | Ceiling | Status | What it covers |
|---|---|---|---|
| `stage-0` | $30 | done | Foundation, $0 |
| `stage-1` | $30 | done | Two connectors, $12 |
| `stage-2` | $30 | done | Logs and the link home, $0 in the reference environment |
| `stage-3` | $30 | current | Workload host, bucket, Functions, $29 |
| `stage-4` | $30 | planned | Grafana on-prem, $0 |
| `aws-twin` | $30 | planned | The AWS twin of stage 1, $20.84, applied only while the DigitalOcean connectors are down |
| `edge` | $35 | planned | Public edge (DMZ); design option A is stage 3 plus one $6 droplet, written but disabled and not approved |
| `second-site` | $41 | planned | A second DigitalOcean site on top of stage 3: $29 + $12 |
| `learner-soc` | $53 | planned | A learner's own cloud mini SOC on top of stage 3: $29 + $24 for the largest single-droplet option |

The planned rows are proposals taken from the stage designs; none of them is approved until it becomes `current`. The [Roadmap](wiki/Roadmap.md) shows the arithmetic.

The gate enforces, for the current phase:

- `current_phase` is a key of `phases`, and exactly one phase has `status: "current"`, which is `current_phase`;
- every phase has a finite, non-negative `ceiling`, a non-empty `reason`, a `decided` date (`YYYY-MM-DD`) and a `status` of `planned`, `current` or `done`;
- over the declared order a ceiling may stay equal or rise. A **decrease** must be explicit: the phase carries `"lowers": true` (and a reason), so a limit is never weakened quietly. `lowers: true` on a phase that does not go lower also fails;
- a top-level `hard_max` (with a `hard_max_reason`) is required whenever `phases` exists. It is the absolute limit: any phase ceiling above it fails, so a ceiling can only go past it by editing `hard_max` in the same reviewed diff (today $60);
- ceilings, `hard_max` and every `approved_monthly_total` must be JSON numbers (a string such as `"1e6"` fails) with at most two decimal places, so the number the gate enforces is the one a reviewer reads;
- phases run `planned -> current -> done`, in declared order: every `done` phase comes before the current one and every `planned` phase after it. `lowers: true` on the first phase fails (nothing comes before it). A `done` phase may not have a ceiling above the current phase's: one file cannot prove that a finished phase is real, so finished phases are a ratchet and a large ceiling planted in one cannot be switched on later. The price is that a ceiling lower than any finished phase is not supported; to go lower you start a new approved file in a reviewed change;
- a JSON file with a repeated key (`current_phase` twice, say) fails, because Python would keep the last one silently. This covers `approved.json`, every `cost.json` and the price tables;
- the per-provider approvals and the sum of the `active` providers are checked against the current phase's ceiling (everything else in the next section is unchanged);
- a top-level `ceiling` is read only when `phases` is absent (an older file); with both present, the file fails.

The summary line names the phase: `cost-check: phase stage-3 ceiling $30.00 (reason: ...)`.

One file cannot show history, so the lifecycle between versions is checked when the gate is given the base branch's copy: `python3 -I scripts/cost_check.py --root . --base-approved <base approved.json>`. CI does this on every pull request through `scripts/ci_cost_gate.sh`, which fetches the base branch tip (shallow, from the same host the checkout uses) and **fails** if it cannot get it; on a push to main it prints that there is no base and runs the plain gate. The gate then also fails when a phase of any status is removed, when a `done` phase changes or becomes current again (a large ceiling planted in a finished phase could otherwise be switched on without looking like a raise), when a status moves any way but planned, current, done, or when a new phase starts as `done`, and it prints `EFFECTIVE CEILING CHANGED: phase A $X -> phase B $Y` whenever the enforced number moves. `scripts/cost_raise.py` always runs the same check on its own edit.

### To raise the ceiling

Add or edit the phase entry (`ceiling`, `reason`, `decided`), set `current_phase` (and move `status: "current"` to match), and raise the provider approval separately. The diff is the review: a reviewer sees the new number, why, and when it was decided, in one pull request. `scripts/cost_raise.py` prints that diff for you:

```bash
python3 -I scripts/cost_raise.py --phase stage-3 --ceiling 36 --reason 'bigger droplet for the daemons' --make-current --cascade
python3 -I scripts/cost_raise.py --phase stage-3 --ceiling 36 --reason 'bigger droplet for the daemons' --make-current --cascade --write
```

The first line is a dry run: it starts with `EFFECTIVE CEILING: phase stage-1 $30.00 -> phase stage-3 $36.00` (the number the gate will enforce, before and after), then shows the proposed `approved.json` diff and any problem the gate finds. It runs every check `cost_check.py` runs (allowlist, structure, approvals, phases and the lifecycle), not only the totals. The second edits the file, only if those pass: it takes an exclusive lock on the directory, re-reads the file and refuses if it changed since the first read, then writes a temporary file in the same directory, syncs it and renames it over the original. A phase that is `done` cannot be edited or made current again, and `--make-current` moves one phase forward at a time. `--cascade` also raises later phases whose ceiling would otherwise be a quiet decrease (each keeps its reason with a note and gets the new date). A later deliberate `lowers` decrease is kept while it is still a decrease; its flag is dropped only when it no longer goes below its predecessor. Without `--cascade` such a raise fails the no-quiet-decrease rule. `--lowers` marks a deliberate decrease, `--after PHASE` places a new phase, `--decided DATE` overrides today. The helper never changes a provider's `approved_monthly_total`: raise that yourself, in the same pull request, together with the `cost.json` and the allowed file.

## How the gate works

`scripts/cost_check.py` reads each stack's `cost.json` (found anywhere under `stacks/`; the planned machines, their sizes and whether backups are on), looks each up in that cloud's price table and adds them up per cloud. The DigitalOcean table is `docs/cost-prices.json`; other clouds have `docs/cost-prices/<cloud>.json`. A stack under `stacks/aws/` belongs to AWS; any other stack belongs to DigitalOcean. It fails if:

- a cloud's total is above that cloud's `approved_monthly_total` in `docs/stages/approved.json` (currently DigitalOcean $12.00 of the current phase's $30.00 ceiling);
- the approved figures of the clouds marked `active` add up to more than the current phase's ceiling. A cloud that is not applied right now is marked inactive, which is how a second cloud fits under one budget: you apply it while the other is torn down;
- a stack directory has OpenTofu files but no `cost.json`;
- a size is missing from the price table;
- backups are requested while `backups_fraction_verified` is false (it is true in the committed table; see Verified below);
- a droplet's backups are on in any way but the basic weekly plan. A manifest entry with `backups: true` must also say `"backup_plan": "weekly"`; a missing or unknown plan, `daily`, any other `backup*` key (usage-based shapes, hours, a policy object) and a `backups` value that is not a real boolean are refused, because DigitalOcean defaults to the daily plan when none is stated. In `.tf` source a droplet may set `backups` only to the literal `false`, and may not carry a `backup_policy` block;
- a cloud's approved total is itself above the current phase's ceiling;
- the per-phase ceilings are malformed, a ceiling is lower than the phase before it without `lowers`, or a ceiling is above `hard_max` (see "Ceilings per phase");
- a `digitalocean_*` resource type that is not on the free list appears in any `.tf` or `.tofu` file. The gate is an allowlist: `digitalocean_project`, `digitalocean_project_resources`, `digitalocean_tag`, `digitalocean_vpc`, `digitalocean_firewall`, `digitalocean_ssh_key`, `digitalocean_reserved_ip_assignment` and `digitalocean_spaces_key` are free, and the droplet, the reserved IP and the Spaces bucket are allowed only in the files listed under `allowed_sources` (the connector module for the droplet; the edge host module for the droplet and the reserved IP; `modules/spaces-bucket` for the bucket). Each `digitalocean_reserved_ip` needs exactly one assignment in its file, because an unassigned reserved IP costs $5.00 a month, and the manifest cannot cost one yet. Anything else, such as a NAT gateway, app, container registry, Kubernetes node pool or CDN, is refused by name and file;
- no `stacks/**/cost.json` manifest exists, or, in any one stack, the number of `twingate-connector` module blocks differs from the number of machine entries (`droplet` or `instance`) in that stack's manifest, or a connector module block uses `count` or `for_each` (each connector is costed as its own instance, so the gate wants one module block per manifest entry);
- a module source is not local (`./` or `../`), goes through a dot-directory, or leaves the repository, or a `*.tf.json` or `*.tofu.json` file exists, because the gate cannot read them. `*.tf` and `*.tofu` files are both read, override files included;
- a dot-directory exists anywhere under `stacks/` or `modules/` (only `.terraform` is ignored there, and `.git`, `.venv` and `.claude` at the repository top level), or a directory under `stacks/` is not named `NN-name` or exactly `aws`, `azure` or `gcp`, because the gate would not scan or classify it;
- a resource type's provider prefix is neither a known cloud nor one of the non-cloud prefixes in `SAFE_PREFIXES` (`twingate_`, `terraform_`, `null_`, `random_`, `time_`, `tls_`, `local_`). A new provider has to be added there deliberately;
- a Spaces bucket is a flat monthly subscription, priced from a `spaces` manifest entry (`{"name": ..., "kind": "spaces"}`; the amount is read only from the `spaces` entry of `docs/cost-prices.json`, never from the manifest). The bucket resource may not use `count` (it is a costed type), so, like the edge host, a stack switches `modules/spaces-bucket` with a module-call `count = local.on` and nothing else (no `for_each`, no other count). In any one stack the number of `spaces` manifest entries must equal the number of module calls, or be 0 only when every call is `count = local.on` and the stack defines `on = var.<flag> ? 1 : 0` and an output precondition that refuses the flag unless `local.cost.resources` prices the bucket. A switched-off module therefore adds $0;
- a resource of a costed type (`digitalocean_droplet`, `digitalocean_spaces_bucket`, `aws_instance`, `aws_eip`, `aws_ebs_volume`) uses `count` or `for_each`, because the manifest cannot be reconciled with it without a plan;
- a label of a `resource` or `module` block contains a backslash (the gate does not decode escapes), or a block header is not understood;
- a `twingate-connector` module block does not set `size` (or `instance_type`) to a plain `local.<name>.size` (or `local.<name>.type`) reference. The machine size is the one number a typo could change without touching `cost.json`, so the source must read it from the manifest locals. The gate checks the shape of that reference; the stack's own test ties the local to `cost.json` (see `stacks/10-access/tests/access.tftest.hcl`), and the plan check in the trusted run is what proves the size that will actually be created.

The gate scans HCL with a small scanner that understands comments, quoted strings and heredocs, and does not execute it, so it is a guardrail, not a proof. The trusted-run plan check below, not the source scan, is the guarantee: it will not see a resource type built dynamically or a paid resource created outside this repo.

### The labs/ exemption (option L1)

The top-level `labs/` directory holds learner labs, which may create cloud resources the project's own deployment never would. The maintainer approved option L1 of the composable-labs design on 2026-10-22. Under `labs/` the gate:

- still reads every `*.tf` and `*.tofu` file for syntax, and still refuses `*.tf.json`, `*.tofu.json`, symlinked files and symlinked directories;
- skips the resource-type allowlist, the `count`/`for_each` rule on costed resources and the module-source rules.

Everything else is unchanged: `stacks/` and `modules/` get exactly the rules above. The exemption applies only to a path whose first component is exactly `labs` (so not `Labs`, `labs2`, `stacks/labs` or `docs/labs`), with no `..`, whose real path resolves inside the real `labs/` directory of the repository root. A symlink from `labs/` into `stacks/` is not exempt, and a symlinked `labs/` is refused.

A module block outside `labs/` may not take a source that points into `labs/` (by `..`, or through a symlink, checked with the resolved path), because lab files are not costed and the lab's resources would reach a stack unseen. A lab may call `modules/` by relative path: `modules/` is scanned in full wherever it is called from, so nothing is hidden.

What the exemption is not:

- It is not an approval. Nothing under `labs/` is priced, listed in `approved.json` `allowed_sources`, or counted in the project's spend or in any ceiling.
- It is not applied by Spacelift. No `labs/` path may appear in `.spacelift/` or back a registered stack; `tests/test_cost_check_labs.py` fails if one does.
- It does not make a lab safe to run. A learner's bill is the learner's, which is why each lab states its cost before the learner builds it.

To add a paid resource, add it to a `cost.json`, raise that cloud's approved total on purpose in `approved.json`, and have the new total approved before the change merges.

### Costing a plan, not just the source

Source code hides the expensive parts: on AWS a public address is an attribute of an instance, a disk size is a setting, and `count` or `for_each` multiply things the file shows once. So for AWS the gate can also read an OpenTofu plan as JSON (`tofu show -json plan`), where those values are resolved:

```bash
python3 -I scripts/cost_check.py --root . --plan plan.json --stack stacks/aws/10-access
```

For an `aws_instance` it also fails on an `unpriced attribute`: a `tenancy` other than `default`, `unlimited` CPU credits, `instance_market_options`, a placement group or host, detailed `monitoring`, extra `network_interface` blocks, a `launch_template` or a `license_specification`. The list is the constant `AWS_INSTANCE_UNPRICED_ATTRS` in the script. The same attributes (plus `tenancy` and `credit_specification`, nested values included) also fail when the plan cannot value them: the gate reads the plan's `configuration` block, where a resource's `expressions` list only the attributes the configuration sets, and refuses an attribute that is unknown in the plan and set there (for example from a `terraform_data` output). An unknown attribute the configuration does not set is a provider default computed at apply, which every normal plan shows, so it passes; and if the plan carries no `configuration` for the instance the gate cannot tell the two apart and fails. What is not caught: another provider default that is priced differently, and anything set outside the configuration. (CPU credits left unset on a T-family type are caught: see "AWS in approved.json" below.) It prices each planned instance (hourly price times 730, plus a public address unless `associate_public_ip_address` is explicitly `false`, plus the root disk, which must be set explicitly because the image default is not priced), each elastic address and each volume, then requires the result to equal the stack's `cost.json`. Anything it cannot price, such as a load balancer or an unknown instance type, is a failure rather than a zero, and a NAT gateway is rejected outright at this ceiling. The required CI check does not run it today: CI has no AWS plan to give it (the AWS stacks exist as `stacks/aws/00-foundation` and `stacks/aws/10-access` but have never been applied). It belongs in the trusted run that produces the real plan, which is part of the AWS code phase. Where the plan comes from matters: a plan file checked into a pull request can be edited to say anything, so the check is only a guarantee on a plan produced by the trusted run; on a pull request it is an early warning.

## Stack instances: more than one site of the same code

A second site runs the same stack code (one Spacelift project root) with different settings, so the source holds one manifest and the gate would count it once. A **stack instance manifest** makes the second deployment visible. It is data only:

```
stacks/sites/<resource_key>/<stack path>/cost.json      e.g. stacks/sites/tor2/10-access/cost.json
{ "instance_of": "stacks/10-access", "resources": [ ...that site's machines... ] }
```

The gate prices an instance like any manifest. The provider is the one of the stack named in `instance_of`, not the path. It fails if:

- `instance_of` is missing, is not a plain normalized stack path, points into `stacks/sites`, or names a stack directory that has no `cost.json` of its own; or the manifest is not at `stacks/sites/<resource_key>/` plus the `instance_of` path without its `stacks/` prefix; or `instance_of` is set on a manifest outside `stacks/sites/`;
- the `resource_key` directory is not lowercase letters, digits and dashes;
- any `.tf` or `.tofu` file exists under `stacks/sites/` (instances carry no code);
- the instance's resource list differs from the base stack's manifest: the shared code reads sizes from the base stack's own `cost.json` and creates every resource in it again, so the names and every entry (machines, volumes, addresses, sizes, backups) must be equal. A site-specific size needs the stack to read the instance manifest, which is a later change;
- the number of machine entries in the instance manifest differs from the number of `twingate-connector` module blocks in the stack named by `instance_of` (the same reconciliation as a base stack, against that stack's code);
- two manifests answer to one stack id (below).

### Stack ids and `.spacelift/config.yml`

Each manifest answers to one Spacelift stack id:

| Manifest directory | Stack id |
|---|---|
| `stacks/10-access` | `cah-10-access` |
| `stacks/aws/10-access` | `cah-aws-10-access` |
| `stacks/sites/tor2/10-access` (`instance_of: stacks/10-access`) | `cah-10-access-tor2` |

The rule is `cah-` plus the stack path after `stacks/` joined with dashes, plus `-<resource_key>` for an instance. The gate itself requires every stack id in `.spacelift/config.yml` (read with PyYAML, installed in CI before the gate; a missing file is skipped, an unreadable one fails) to have exactly one manifest: an entry with no manifest fails, and it fails when two manifests share an id (`tests/test_cost_check_instances.py` covers both). A stack with no entry in `config.yml` never loads its secrets and cannot apply, and an entry cannot be added without a manifest, so a second site cannot reach an apply without being costed. The gate cannot see a Spacelift stack that is created and never listed.

### Approving sites

By default the provider's `approved_monthly_total` covers everything of that provider, instances included. A provider entry may also carry an optional `sites` map:

```json
"digitalocean": { "approved_monthly_total": 24.0, "active": true,
  "sites": { "tor2": { "approved_monthly_total": 12.0 } } }
```

With a map present: every instance's `resource_key` must be in it; each site's planned total must be within its own figure; the sites' figures must add up to no more than the provider figure; and the base stacks (everything not under `stacks/sites`) must fit in the provider figure minus the sites' figures. So the provider figure is the base stack plus its sites. The shared-ceiling check still sums the provider figures of the `active` providers, never the sites (they are already inside it). Site, base and sum comparisons are made at cent precision (full precision is kept while adding up), as the provider total already is. With no map, behavior is unchanged.

`--plan` accepts an instance path (`--stack stacks/sites/east/aws/10-access`): the provider comes from `instance_of` and the plan is compared with that instance's manifest.

## Verified

- Droplet backups are verified (issue 117) for the basic weekly plan only: `backups_fraction` is 0.2 and `backups_fraction_verified` is `true`. DigitalOcean's backups pricing page (https://docs.digitalocean.com/products/backups/details/pricing/), read 2026-10-19, lists basic plans at 20.0 percent (weekly) and 30.0 percent (daily) of the Droplet's cost per month. The table prices only that weekly fraction. The gate refuses daily backups and the per-GiB usage-based plans (public preview, weekly, daily, 12, 6 or 4 hour) on the same page, and any backup shape it does not recognize, until someone prices and verifies them.

## Not yet verified

These are not priced, or not confirmed against the vendor's current page. Check them before relying on them:

- Bandwidth overage.
- Block storage.
- Droplet backups other than the basic weekly plan (daily and usage-based plans). The gate refuses them rather than guessing a price.
- Snapshots.
- Free-tier limits of Spacelift, Doppler and Twingate.

### What `active` means

`active` in `approved.json` is the maintainer's statement that a cloud is applied right now. The gate adds up the active figures against the current phase's ceiling, but it cannot see what is actually running: a cloud marked inactive can still have a manifest in the repository (the code exists, it is just not applied), and nothing checks that its stacks are destroyed. Marking a cloud inactive is a promise to tear it down first, backed by the billing alert, not by the gate.

### Other limits of the source scan

Comments are removed and braces inside quoted strings are ignored, but heredocs, dynamic module sources and resource types built from strings are not understood. A type the gate has no price model for fails even when `approved.json` names a file for it: approval can place a priced type in a file, not invent a price.

## AWS in `approved.json`

`aws` is listed with `approved_monthly_total` 21.0 (the two-connector stack is $20.84) and `active: false`: the current phase's $30 ceiling cannot hold DigitalOcean stage 1 ($12) and AWS ($21) together, so the AWS stack is applied only while DigitalOcean stage 1 is torn down, and `active` is flipped on purpose at that point. `modules/aws/twingate-connector/main.tf` is the only file allowed to declare an `aws_instance`. `aws_default_security_group` is a free type. On a plan, a T-family instance (`t2`, `t3`, `t3a`, `t4g`) must state `credit_specification.cpu_credits = "standard"`: the omitted default is unlimited, whose surplus credits are billed outside the fixed figure, so the gate fails closed when the block is missing.
