# Clouds Against Humanity

This repository builds a small, cheap, locked-down DigitalOcean environment with OpenTofu, one stage at a time. It is written for people who are learning cloud infrastructure and want to see every decision explained. Each stage is costed and approved before it runs, and the working ceiling is $30 per month across stages 0 to 4. A cost gate in CI fails any change that raises the planned total above the approved total.

This first release covers two stages: stage 0 (foundation) and stage 1 (access).

## Layers

```
Clouds-Against-Humanity/
  scripts/cost_check.py                    cost gate
  tests/test_cost_check.py                 pytest for the gate
  scripts/spacelift/doppler-env.sh         hook that loads Doppler secrets into a run
  tests/test_doppler_env.py                pytest for the hook and its config
  .spacelift/config.yml                    which secrets each stack loads
  docs/cost-prices.json                    price table from the DO sizes API
  docs/cost.md                             cost gate explained
  docs/stages/approved.json                approved totals + allowed sources
  docs/spacelift-secrets.md                how secrets reach a run, rotation, upgrades
  modules/vpc/                             per-region VPC
  modules/firewall/                        tag-based deny-inbound firewall
  modules/twingate-connector/              remote network, connector, droplet
  stacks/00-foundation/                    project, tag, VPC, baseline firewall
  stacks/10-access/                        connector, connector firewall, group, SSH resource
  .github/workflows/ci.yml                 GYST callers + tofu-test + CI green
  docs/stages/00-foundation.md, 01-access.md   stage guides
```

Modules are reusable building blocks. Stacks are the things you actually apply, one Spacelift stack each. Each module and stack has its tests in `<module or stack>/tests/*.tftest.hcl`.

## Run the checks

Install OpenTofu 1.8 or newer and Python 3, then:

```bash
# cost gate: totals the planned resources and compares with docs/stages/approved.json
python3 -I scripts/cost_check.py --root .

# tests for the cost gate (needs a virtualenv with pytest installed)
python3 -I -m pytest tests -q

# tests for one module or stack (no cloud account needed, providers are mocked)
tofu -chdir=modules/firewall init -backend=false
tofu -chdir=modules/firewall test
```

Run the second pair for each of `modules/vpc`, `modules/firewall`, `modules/twingate-connector`, `stacks/00-foundation` and `stacks/10-access`. CI does the same and also runs the cost gate.

## Stage guides

- [Stage 0: foundation](docs/stages/00-foundation.md)
- [Stage 1: access](docs/stages/01-access.md)
- [Cost](docs/cost.md)
- [Spacelift and Doppler secrets](docs/spacelift-secrets.md)

## Public by design

This repository is public from its first commit, so the GitHub code-scanning and dependency-review checks run in CI. Everything that varies per person or per account (tokens, tenant names, user ids, address ranges you do not want shared) is a Doppler variable, not a file. If a piece ever cannot meet that rule, it moves to a separate private repository and this one calls it.

## Secrets

Secrets live in Doppler; nothing in this repository is a credential. Spacelift holds one read-only Doppler token and fetches the rest at run time; see [Spacelift and Doppler secrets](docs/spacelift-secrets.md) for how that works and how to rotate it.
