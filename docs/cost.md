# Cost

Working ceiling: $30 per month for stages 0 to 4. Each stage must be costed and approved before it runs.

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Two Twingate connector droplets (`s-1vcpu-1gb`, list price $6 each) | $12 | $12 |

Source of prices: `docs/cost-prices.json`, retrieved 2026-10-10 from the DigitalOcean sizes API.

## Stage 3 estimate (not approved)

Stage 3 adds one Docker host running Portainer CE, five small daemons and, depending on where the Matrix homeserver is, a Discord-to-Matrix bridge. Stages 2 and 4 are planned to add $0 to the cloud bill (logs and Grafana run on-prem), so this is the only remaining paid stage. The design draft is [2026-10-11 stage 3 workloads](superpowers/specs/2026-10-11-stage-3-workloads-design.md); the three sizes it prices:

| Option | Size | Adds | Running | Headroom under $30 |
|---|---|---|---|---|
| A | `s-1vcpu-2gb` | $12 | $24 | $6 |
| B (recommended) | `s-2vcpu-2gb` | $18 | $30 | $0 |
| C | `s-2vcpu-4gb` | $24 | $36 | needs the ceiling raised to $40 |

None of these is in `approved.json` yet. Backups are off in all three (weekly backups on option B would be $3.60 and break the ceiling); block storage is not needed. Approving the stage means picking one row, raising `approved_monthly_total` to its running total on purpose, and adding the new module to `allowed_sources`.

## How the gate works

`scripts/cost_check.py` reads each stack's `cost.json` (the planned droplets, their sizes and whether backups are on), looks each size up in the price table and adds them up. It fails if:

- the total is above the approved total in `docs/stages/approved.json` (currently stage 1, $12.00, ceiling $30.00);
- a size is missing from the price table;
- backups are requested while the backup price is unverified (see below);
- the approved total is itself above the ceiling;
- a `digitalocean_*` resource type that is not on the free list appears in any `.tf` file. The gate is an allowlist: `digitalocean_project`, `digitalocean_project_resources`, `digitalocean_tag`, `digitalocean_vpc`, `digitalocean_firewall` and `digitalocean_ssh_key` are free, and the droplet is allowed only in the file listed under `allowed_sources` (the connector module). Anything else, such as a NAT gateway, app, container registry, Kubernetes node pool or CDN, is refused by name and file;
- no `stacks/*/cost.json` manifest exists, or the number of `twingate-connector` module blocks differs from the number of `droplet` entries in the manifests, or a connector module block uses `count` or `for_each` (each connector is costed as its own instance, so the gate wants one module block per manifest entry);
- a module source is not local (`./` or `../`), or a `*.tf.json` file exists, because the gate cannot read either.

The gate parses HCL with regular expressions and does not execute it, so it is a guardrail, not a proof: it will not see a resource type built dynamically or a paid resource created outside this repo.

To add a paid resource, add it to a `cost.json`, raise the approved total on purpose in `approved.json`, and have the new total approved before the change merges.

## Not yet verified

These are not priced, or not confirmed against the vendor's current page. Check them before relying on them:

- Droplet backups. The table assumes a fraction of the droplet price (`backups_fraction`), and `backups_fraction_verified` is `false`, so the gate refuses any backup-enabled droplet until someone verifies it. DigitalOcean's backups pricing page, read 2026-10-11, states 20 percent of the droplet price for weekly and 30 percent for daily backups, so the flag can be flipped in the pull request that first turns backups on.
- Bandwidth overage.
- Snapshots.
- Free-tier limits of Spacelift, Doppler and Twingate.
