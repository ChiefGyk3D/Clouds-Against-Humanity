# Cost

Working ceiling: $30 per month for stages 0 to 4. Each stage must be costed and approved before it runs.

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Twingate connector droplet (`s-1vcpu-1gb`, list price $6) | $6 | $6 |

Source of prices: `docs/cost-prices.json`, retrieved 2026-10-10 from the DigitalOcean sizes API.

## How the gate works

`scripts/cost_check.py` reads each stack's `cost.json` (the planned droplets, their sizes and whether backups are on), looks each size up in the price table and adds them up. It fails if:

- the total is above the approved total in `docs/stages/approved.json` (currently stage 1, $6.00, ceiling $30.00);
- a size is missing from the price table;
- backups are requested while the backup price is unverified (see below);
- the approved total is itself above the ceiling;
- a droplet is declared in a source file that is not listed under `allowed_sources`, so a droplet cannot be added without being costed.

To add a paid resource, add it to a `cost.json`, raise the approved total on purpose in `approved.json`, and have the new total approved before the change merges.

## Not yet verified

These are not priced, or not confirmed against the vendor's current page. Check them before relying on them:

- Droplet backups. The table assumes a fraction of the droplet price (`backups_fraction`), and `backups_fraction_verified` is `false`, so the gate refuses any backup-enabled droplet until someone verifies it.
- Bandwidth overage.
- Snapshots.
- Free-tier limits of Spacelift, Doppler and Twingate.
