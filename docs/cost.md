# Cost

Working ceiling: $30 per month for stages 0 to 4. Each stage must be costed and approved before it runs.

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Two Twingate connector droplets (`s-1vcpu-1gb`, list price $6 each) | $12 | $12 |

The region is `tor1` (Toronto), chosen on 2026-10-11 after a new account got `422 Size is not available in this region` for the $6 `s-1vcpu-1gb` in nyc3. Check `GET /v2/sizes` and `GET /v2/regions` for your own account before picking a region: availability of the cheap legacy sizes differs by region and by account, and the newer US sites (Atlanta, Richmond, Kansas City, Memphis) start at about $18 for 1 GB.

Source of prices: `docs/cost-prices.json`, retrieved 2026-10-10 from the DigitalOcean sizes API.

## Stage 3 estimate (not approved)

Stage 3 adds one Docker host running Portainer CE, five small daemons, an S3-compatible bucket for their state and a self-hosted Discord-to-Matrix bridge on the same droplet (the Matrix homeserver itself is hosted by etke.cc). The jobs that already run on a timer move to DigitalOcean Functions. Stages 2 and 4 are planned to add $0 to the cloud bill (logs and Grafana run on-prem), so this is the only remaining paid stage. The design draft is [2026-10-11 stage 3 workloads](superpowers/specs/2026-10-11-stage-3-workloads-design.md); what it prices:

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
- a `digitalocean_*` resource type that is not on the free list appears in any `.tf` file. The gate is an allowlist: `digitalocean_project`, `digitalocean_project_resources`, `digitalocean_tag`, `digitalocean_vpc`, `digitalocean_firewall` and `digitalocean_ssh_key` are free, and the droplet is allowed only in the file listed under `allowed_sources` (the connector module). Anything else, such as a NAT gateway, app, container registry, Kubernetes node pool or CDN, is refused by name and file;
- no `stacks/**/cost.json` manifest exists, or, in any one stack, the number of `twingate-connector` module blocks differs from the number of machine entries (`droplet` or `instance`) in that stack's manifest, or a connector module block uses `count` or `for_each` (each connector is costed as its own instance, so the gate wants one module block per manifest entry);
- a module source is not local (`./` or `../`), or a `*.tf.json` file exists, because the gate cannot read either.

The gate parses HCL with regular expressions and does not execute it, so it is a guardrail, not a proof: it will not see a resource type built dynamically or a paid resource created outside this repo.

To add a paid resource, add it to a `cost.json`, raise that cloud's approved total on purpose in `approved.json`, and have the new total approved before the change merges.

### Costing a plan, not just the source

Source code hides the expensive parts: on AWS a public address is an attribute of an instance, a disk size is a setting, and `count` or `for_each` multiply things the file shows once. So for AWS the gate can also read an OpenTofu plan as JSON (`tofu show -json plan`), where those values are resolved:

```bash
python3 -I scripts/cost_check.py --root . --plan plan.json --stack stacks/aws/10-access
```

It prices each planned instance (hourly price times 730, plus a public address unless `associate_public_ip_address` is explicitly `false`, plus the root disk, which must be set explicitly because the image default is not priced), each elastic address and each volume, then requires the result to equal the stack's `cost.json`. Anything it cannot price, such as a load balancer or an unknown instance type, is a failure rather than a zero, and a NAT gateway is rejected outright at this ceiling. Where the plan comes from matters: a plan file checked into a pull request can be edited to say anything, so the check is only a guarantee on a plan produced by the trusted run; on a pull request it is an early warning.

## Not yet verified

These are not priced, or not confirmed against the vendor's current page. Check them before relying on them:

- Droplet backups. The table assumes a fraction of the droplet price (`backups_fraction`), and `backups_fraction_verified` is `false`, so the gate refuses any backup-enabled droplet until someone verifies it. DigitalOcean's backups pricing page, read 2026-10-11, states 20 percent of the droplet price for weekly and 30 percent for daily backups, so the flag can be flipped in the pull request that first turns backups on.
- Bandwidth overage.
- Snapshots.
- Free-tier limits of Spacelift, Doppler and Twingate.
