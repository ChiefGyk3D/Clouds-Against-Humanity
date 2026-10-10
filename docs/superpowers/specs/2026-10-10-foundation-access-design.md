# Clouds Against Humanity: Foundation and Access (Stages 0-1)

Status: DRAFT for review. Date: 2026-10-10.
Amended 2026-10-10 after implementation: outbound includes tcp 80 and tcp 53; no droplet-baseline module.
Scope: stages 0 and 1 only. Later stages get their own spec, plan and cost approval.

## 1. Purpose

A cloud extension of the homelab, managed entirely as code, that is also a
teaching repo for the community. It is the jumping-off point for more cloud
projects and, eventually, some Penguin Overlord components.

Success looks like:
- A new DigitalOcean account that is hardened before anything is created in it.
- OpenTofu (DigitalOcean provider) applied by Spacelift, with secrets only in Doppler.
- One Twingate connector droplet, so the first workload host is never reachable
  from the public internet.
- Every stage costed, approved and documented before it runs.
- A repo that can be fully public: no secrets, tenant IDs, hostnames, serials,
  callsign, or employer name anywhere in it.

Non-goals for this spec: Wazuh/log shipping (stage 2), workloads (stage 3),
Grafana (stage 4, runs on-prem), Kubernetes, multi-region, load balancing.

## 2. Constraints

- Sole-operator budget. Working ceiling is $30/month for stages 0-4. Each stage
  is approved separately before it costs anything.
- OpenTofu, not Terraform (licensing).
- CI is GYST callers only. Anything reusable goes into git-your-ship-together
  first and is called from here. Gate job is named `CI green`. Callers pinned
  by commit with a `# vX.Y.Z` comment.
- Secrets come from Doppler. No user-scoped PAT anywhere; GitHub access for CI
  is a scoped GitHub App installation token.
- Public-by-default repo. A private repo is created only for something that
  cannot meet the no-secrets rule.

## 3. Architecture

```
Clouds-Against-Humanity/
  stacks/
    00-foundation/     DO project, per-region VPC, tag-based firewall
    10-access/         Twingate connector droplet, groups, resources
  modules/             vpc, twingate-connector
  docs/
    stages/            one guide per stage: decisions, cost, verify, runbook
    cost.md            price table from the DO sizes API + stage totals
  scripts/             cost check (reads planned sizes, totals the stage)
  .github/workflows/   GYST callers only
```

- One Spacelift stack per `stacks/` directory. Dependency order 00 -> 10, with
  outputs passed through Spacelift stack dependency references.
- Every stack and module takes `region` as a variable. Names follow
  `<layer>-<region>-<role>`. VPCs are per region. Adding a region means
  instantiating the same modules again.
- Environment separation (tfvars layer per environment) is a later addition and
  is not blocked by this layout.

## 4. Stage 0: foundation

### 4.1 Account hardening (before any apply)
Checklist, each item verified and recorded in `docs/stages/00-foundation.md`:
- Two-factor authentication on the account, with recovery codes stored in the
  password manager.
- Billing alert set below the working ceiling.
- Separate API tokens by purpose:
  - Spacelift: write scope, held only in Doppler.
  - Read-only token for interactive tooling.
  - Scope of the token behind the existing droplet MCP server is checked and
    replaced with the read-only one if broader.
- Token expiry set and a rotation date recorded.
- Resources grouped in a dedicated DO project.

### 4.2 Resources
- DO project.
- VPC per region (private range chosen to avoid overlap with homelab ranges).
- Cloud Firewall attached by tag: no inbound at all, no public SSH, outbound
  limited to what the connector and package updates need (443, 80 for
  package mirrors, DNS on 53 tcp and udp, NTP on 123 udp).
- Common tag convention applied at droplet creation, so the firewall is in
  force from the first boot.

### 4.3 State and secrets
- State held by Spacelift. Secrets supplied to stacks from Doppler.
- Bootstrap order (account hardening, Doppler config, Spacelift stack, first
  plan) is written out step by step in the stage guide.

## 5. Stage 1: access

- Twingate remote network per region.
- One connector droplet, `s-1vcpu-1gb` class, inside the VPC, tagged so the
  firewall covers it. Outbound connections only.
- Twingate groups by role. Resources defined per host or per narrow CIDR and
  port, never a whole VPC "allow all".
- SSH to any droplet is over its private IP through Twingate only.
- Cloud-to-home access (headless client plus service account) is designed in
  stage 2; this stage only reserves the group names and naming.

### Accepted residual risk
The connector token lands in OpenTofu state and cloud-init user-data. Mitigation:
marked sensitive, state in Spacelift with restricted access, token is
single-connector and revocable, rotation procedure documented. Revisit if a
fetch-at-boot design proves cleaner.

## 6. Cost

| Stage | Adds | Monthly | Running |
|---|---|---|---|
| 0 | Hardening, repo, CI, Spacelift/Doppler wiring | $0 | $0 |
| 1 | Twingate connector droplet (`s-1vcpu-1gb`, list price $6) | $6 | $6 |

Not yet priced and to be checked against current vendor pages before apply:
droplet backups, snapshots, bandwidth overage, and the free-tier limits of
Spacelift, Doppler, Twingate. The cost script fails CI if a PR raises the
planned total above the approved stage total.

## 7. Documentation and logging

- Every stage guide records what was decided, why, the cost, how it was
  verified and how to roll back. Written for community learners.
- Nothing in the repo contains hostnames, machine serials, asset tags,
  callsign or grid, employer name, or raw corpus data. Gitleaks runs through
  the GYST security workflow; an identifier-denylist check is proposed as a
  GYST addition, not a local script.
- Operational logs (connector and access logs) go to the on-prem log server in
  stage 2; no new log service is created in DO.

## 8. AI tiering for this project

1. Local model (`llm-local`) first: drafts of docs, plan and log digests, PR
   summaries. Counting and cost math are done in code.
2. Sonnet: implementation and coordination.
3. ChatGPT/Codex: security review and second opinion at each stage gate.
4. Opus or Mythos: only with explicit approval, for a final whole-repo review.

## 9. Testing and verification

- `tofu fmt -check`, `tofu validate`, `tofu plan` in CI through the GYST
  `tofu-ci` caller.
- Cost script run on every PR.
- Stage 0 verified by: firewall present with zero inbound rules, no droplets,
  billing alert present.
- Stage 1 verified by: connector shows online in Twingate, SSH to the private
  IP works through Twingate, the droplet's public IP refuses all inbound
  connections from outside.

## 10. Open items (decide before the plan is written)

1. Home-side Twingate connector VLAN: it must be on a VLAN allowed to reach the
   local AI server (one VLAN is allowed, one is blocked).
2. Private range for the VPC that does not overlap homelab ranges.
3. Which DO region to start in (cost class and latency).
4. Spacelift, Doppler and Twingate free-tier limits as of today.
5. Whether the existing droplet MCP token needs replacing (see 4.1).
6. Repo creation under the personal account is pending approval.
