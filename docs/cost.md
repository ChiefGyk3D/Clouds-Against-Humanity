# Cost

Working ceiling: $30 per month for stages 0 to 4. Each stage must be costed and approved before it runs.

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Two Twingate connector droplets (`s-1vcpu-1gb`, list price $6 each) | $12 | $12 |

The region is `tor1` (Toronto), chosen on 2026-10-11 after a new account got `422 Size is not available in this region` for the $6 `s-1vcpu-1gb` in nyc3. Check `GET /v2/sizes` and `GET /v2/regions` for your own account before picking a region: availability of the cheap legacy sizes differs by region and by account, and the newer US sites (Atlanta, Richmond, Kansas City, Memphis) start at about $18 for 1 GB.

Source of prices: `docs/cost-prices.json`, retrieved 2026-10-10 from the DigitalOcean sizes API.

## Stage 3 estimate (not approved)

Stage 3 adds one Docker host running Portainer CE, five small daemons, an S3-compatible bucket for their state and a self-hosted Discord-to-Matrix bridge on the same droplet (the Matrix homeserver itself is hosted by etke.cc). The jobs that already run on a timer move to DigitalOcean Functions. In the reference environment stages 2 and 4 are planned to add $0 to the cloud bill (logs and the Grafana run on-prem), so this is the only remaining paid stage there. A learner who builds their own cloud Grafana (option N1) or Wazuh manager (S1) pays $6 to $24 or more for one more droplet, which with stage 3 option A ($29) does not fit under $30; see the [settings and mini SOC design](superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) section 1.3 and the wiki page [Build your own mini SOC](wiki/Build-Your-Own-Mini-SOC.md). The design draft is [2026-10-11 stage 3 workloads](superpowers/specs/2026-10-11-stage-3-workloads-design.md); what it prices:

| Option | Droplet | Spaces bucket | Functions | Running | Fits $30? |
|---|---|---|---|---|---|
| A + bucket (recommended) | `s-1vcpu-2gb`, $12 | $5 flat | $0 within the free allowance | $29 | Yes |
| B, state on the host | `s-2vcpu-2gb`, $18 | none | $0 | $30 | Yes, with nothing left |
| B + bucket | $18 | $5 | $0 | $35 | Needs a $40 ceiling |
| C + bucket | `s-2vcpu-4gb`, $24 | $5 | $0 | $41 | Needs a $45 ceiling |

Prices read 2026-10-11: Spaces is $5 per month for 250 GiB stored and 1 TiB outbound transfer per account, then $0.02 per GiB stored and $0.01 per GiB out. Functions have a free allowance of 90,000 GiB-seconds per month per team, then $0.0000185 per GiB-second; the stage's expected use is near the allowance and an overage month would cost cents. Functions are deployed with `doctl`, not OpenTofu, so the gate cannot see them: their spend is a line someone checks on the usage page.

None of this is in `approved.json` yet. Droplet backups are off in every row; the bucket's versioning and a nightly copy off the account are the backups. Block storage is not needed. Approving the stage means picking one row, raising `approved_monthly_total` to its running total on purpose, adding the new module and the bucket's file to `allowed_sources`, and teaching the gate to price a `spaces` manifest entry as a flat amount.

## How the gate works

`scripts/cost_check.py` reads each stack's `cost.json` (found anywhere under `stacks/`; the planned machines, their sizes and whether backups are on), looks each up in that cloud's price table and adds them up per cloud. The DigitalOcean table is `docs/cost-prices.json`; other clouds have `docs/cost-prices/<cloud>.json`. A stack under `stacks/aws/` belongs to AWS; any other stack belongs to DigitalOcean. It fails if:

- a cloud's total is above that cloud's `approved_monthly_total` in `docs/stages/approved.json` (currently DigitalOcean $12.00 of a shared $30.00 ceiling);
- the approved figures of the clouds marked `active` add up to more than the shared ceiling. A cloud that is not applied right now is marked inactive, which is how a second cloud fits under one budget: you apply it while the other is torn down;
- a stack directory has OpenTofu files but no `cost.json`;
- a size is missing from the price table;
- backups are requested while the backup price is unverified (see below);
- the approved total is itself above the ceiling;
- a `digitalocean_*` resource type that is not on the free list appears in any `.tf` or `.tofu` file. The gate is an allowlist: `digitalocean_project`, `digitalocean_project_resources`, `digitalocean_tag`, `digitalocean_vpc`, `digitalocean_firewall` and `digitalocean_ssh_key` are free, and the droplet is allowed only in the file listed under `allowed_sources` (the connector module). Anything else, such as a NAT gateway, app, container registry, Kubernetes node pool or CDN, is refused by name and file;
- no `stacks/**/cost.json` manifest exists, or, in any one stack, the number of `twingate-connector` module blocks differs from the number of machine entries (`droplet` or `instance`) in that stack's manifest, or a connector module block uses `count` or `for_each` (each connector is costed as its own instance, so the gate wants one module block per manifest entry);
- a module source is not local (`./` or `../`), goes through a dot-directory, or leaves the repository, or a `*.tf.json` or `*.tofu.json` file exists, because the gate cannot read them. `*.tf` and `*.tofu` files are both read, override files included;
- a dot-directory exists anywhere under `stacks/` or `modules/` (only `.terraform` is ignored there, and `.git`, `.venv` and `.claude` at the repository top level), or a directory under `stacks/` is not named `NN-name` or exactly `aws`, `azure` or `gcp`, because the gate would not scan or classify it;
- a resource type's provider prefix is neither a known cloud nor one of the non-cloud prefixes in `SAFE_PREFIXES` (`twingate_`, `terraform_`, `null_`, `random_`, `time_`, `tls_`, `local_`). A new provider has to be added there deliberately;
- a resource of a costed type (`digitalocean_droplet`, `aws_instance`, `aws_eip`, `aws_ebs_volume`) uses `count` or `for_each`, because the manifest cannot be reconciled with it without a plan;
- a label of a `resource` or `module` block contains a backslash (the gate does not decode escapes), or a block header is not understood;
- a `twingate-connector` module block does not set `size` (or `instance_type`) to a plain `local.<name>.size` (or `local.<name>.type`) reference. The machine size is the one number a typo could change without touching `cost.json`, so the source must read it from the manifest locals. The gate checks the shape of that reference; the stack's own test ties the local to `cost.json` (see `stacks/10-access/tests/access.tftest.hcl`), and the plan check in the trusted run is what proves the size that will actually be created.

The gate scans HCL with a small scanner that understands comments, quoted strings and heredocs, and does not execute it, so it is a guardrail, not a proof. The trusted-run plan check below, not the source scan, is the guarantee: it will not see a resource type built dynamically or a paid resource created outside this repo.

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

With a map present: every instance's `resource_key` must be in it; each site's planned total must be within its own figure; the sites' figures must add up to no more than the provider figure; and the base stacks (everything not under `stacks/sites`) must fit in the provider figure minus the sites' figures. So the provider figure is the base stack plus its sites. The shared-ceiling check still sums the provider figures of the `active` providers, never the sites (they are already inside it). Site, base and sum comparisons are made at cent precision (full precision is kept while adding up), as the provider total already is. With no map, behaviour is unchanged.

`--plan` accepts an instance path (`--stack stacks/sites/east/aws/10-access`): the provider comes from `instance_of` and the plan is compared with that instance's manifest.

## Not yet verified

These are not priced, or not confirmed against the vendor's current page. Check them before relying on them:

- Droplet backups. The table assumes a fraction of the droplet price (`backups_fraction`), and `backups_fraction_verified` is `false`, so the gate refuses any backup-enabled droplet until someone verifies it. DigitalOcean's backups pricing page, read 2026-10-11, states 20 percent of the droplet price for weekly and 30 percent for daily backups, so the flag can be flipped in the pull request that first turns backups on.
- Bandwidth overage.
- Snapshots.
- Free-tier limits of Spacelift, Doppler and Twingate.

### What `active` means

`active` in `approved.json` is the maintainer's statement that a cloud is applied right now. The gate adds up the active figures against the shared ceiling, but it cannot see what is actually running: a cloud marked inactive can still have a manifest in the repository (the code exists, it is just not applied), and nothing checks that its stacks are destroyed. Marking a cloud inactive is a promise to tear it down first, backed by the billing alert, not by the gate.

### Other limits of the source scan

Comments are removed and braces inside quoted strings are ignored, but heredocs, dynamic module sources and resource types built from strings are not understood. A type the gate has no price model for fails even when `approved.json` names a file for it: approval can place a priced type in a file, not invent a price.

## AWS in `approved.json`

`aws` is listed with `approved_monthly_total` 21.0 (the two-connector stack is $20.84) and `active: false`: the shared $30 ceiling cannot hold DigitalOcean stage 1 ($12) and AWS ($21) together, so the AWS stack is applied only while DigitalOcean stage 1 is torn down, and `active` is flipped on purpose at that point. `modules/aws/twingate-connector/main.tf` is the only file allowed to declare an `aws_instance`. `aws_default_security_group` is a free type. On a plan, a T-family instance (`t2`, `t3`, `t3a`, `t4g`) must state `credit_specification.cpu_credits = "standard"`: the omitted default is unlimited, whose surplus credits are billed outside the fixed figure, so the gate fails closed when the block is missing.
