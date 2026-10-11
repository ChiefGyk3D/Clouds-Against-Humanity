# Stage 0: Foundation

## 1. What this stage builds

- A DigitalOcean project to group the resources.
- One VPC (private network) in `tor1`, default range `10.77.0.0/24`.
- A baseline tag, `cah-baseline-tor1`.
- A baseline firewall attached to that tag with zero inbound rules. DigitalOcean denies any inbound traffic that no rule allows, so every droplet that carries the tag is closed to the internet from the moment it exists.

Cost: $0. Nothing in this stage is billed.

## 2. Account hardening checklist

Do these by hand in the DigitalOcean console and the password manager before the first apply. When an item is done, fill in its `Verified on:` line.

- [ ] Two-factor authentication on the account; recovery codes in the password manager.
  Verified on:
- [ ] Billing alerts set at $10 and $25 (below the $30 ceiling).
  Verified on:
- [ ] Token A: custom write scopes from [the scope table](../spacelift-secrets.md#4a-digitalocean-token-scopes), 90-day expiry, stored only in Doppler, used only by Spacelift.
  Verified on:
- [ ] Token B: custom read-only scopes from the same table, 90-day expiry, for interactive tooling.
  Verified on:
- [ ] The token currently behind the `do-droplets` MCP server is identified; if it is write-scoped, it is replaced with Token B.
  Verified on:
- [ ] Rotation date for both tokens recorded in the password manager (not in this repo).
  Verified on:

## 3. Choices to confirm before apply

- Region: `tor1` is the default. The price table (`docs/cost-prices.json`) is not region-specific; it records list prices retrieved on 2026-10-10 for the listed sizes. Check the availability and price of a size in another region before changing region.
- VPC CIDR: confirm that `10.77.0.0/24` does not overlap any home or lab range you connect to. Compare against your router's routing table. Record only "no overlap confirmed" in this repo, never the ranges themselves. If it overlaps, set `vpc_ip_range` to another private range.
- License of this repository: MIT (see `LICENSE`), matching the author's other repositories.

## 4. Bootstrap order

1. Create the Doppler project `clouds-against-humanity` with a `prd` config holding `DIGITALOCEAN_TOKEN` (Token A).
2. Create the Spacelift stack `cah-00-foundation` rooted at `stacks/00-foundation`, with OpenTofu as the workflow tool (the Terraform vendor setting with `OPEN_TOFU`, because the standalone OpenTofu vendor is not enabled on this account) and autodeploy off.
3. Feed the Doppler secrets into the stack's environment. Doppler has no native Spacelift integration and this Spacelift plan has no OIDC token, so a Spacelift context holds one read-only Doppler service token and a hook fetches the rest. Setup, rotation and troubleshooting are in [Spacelift and Doppler secrets](../spacelift-secrets.md).
4. Trigger a tracked run on `main`. Autodeploy is off, so it stops after the plan and waits for you. A proposed run (a pull request plan) gets no credentials by design, so it cannot be used for this. Read the plan, then confirm it. The plan should show a project, a tag, a VPC and a firewall, and nothing else.

## 5. Verify

- The DigitalOcean project exists.
- The firewall lists no inbound rules.
- `doctl compute droplet list` (or the MCP droplet list) is empty.
- The billing alerts are visible in the account settings.

## 6. Rollback

Before confirming, discard the Spacelift run and nothing changes. After apply, run `destroy` on the stack. Nothing here costs money, so leaving it in place is also safe.
