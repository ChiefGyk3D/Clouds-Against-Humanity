# Stage 0: Foundation

## 1. What this stage builds

- A DigitalOcean project to group the resources.
- One VPC (private network) in `nyc3`, default range `10.77.0.0/24`.
- A baseline tag, `cah-baseline-nyc3`.
- A baseline firewall attached to that tag with zero inbound rules. DigitalOcean denies any inbound traffic that no rule allows, so every droplet that carries the tag is closed to the internet from the moment it exists.

Cost: $0. Nothing in this stage is billed.

## 2. Account hardening checklist

Do these by hand in the DigitalOcean console and the password manager before the first apply. When an item is done, fill in its `Verified on:` line.

- [ ] Two-factor authentication on the account; recovery codes in the password manager.
  Verified on:
- [ ] Billing alerts set at $10 and $25 (below the $30 ceiling).
  Verified on:
- [ ] Token A: write scope, 90-day expiry, stored only in Doppler, used only by Spacelift.
  Verified on:
- [ ] Token B: read scope, 90-day expiry, for interactive tooling.
  Verified on:
- [ ] The token currently behind the `do-droplets` MCP server is identified; if it is write-scoped, it is replaced with Token B.
  Verified on:
- [ ] Rotation date for both tokens recorded in the password manager (not in this repo).
  Verified on:

## 3. Choices to confirm before apply

- Region: `nyc3` is the default. It is the region that carries the `$6` price for `s-1vcpu-1gb` in the price table; a different region needs its price checked first.
- VPC CIDR: confirm that `10.77.0.0/24` does not overlap any home or lab range you connect to. Compare against your router's routing table. Record only "no overlap confirmed" in this repo, never the ranges themselves. If it overlaps, set `vpc_ip_range` to another private range.
- License of this repository: choose it before the repository goes public.

## 4. Bootstrap order

1. Create the Doppler project `clouds-against-humanity` with a `prd` config holding `DIGITALOCEAN_TOKEN` (Token A).
2. Create the Spacelift stack `cah-00-foundation` rooted at `stacks/00-foundation`, with the OpenTofu binary and autodeploy off.
3. Feed the Doppler secrets into the stack's environment by whichever mechanism the free plans support. Verify this at setup time: either Doppler's native Spacelift sync, or a Spacelift context filled once by hand.
4. Run a proposed run, read the plan, then confirm it. The plan should show a project, a tag, a VPC and a firewall, and nothing else.

## 5. Verify

- The DigitalOcean project exists.
- The firewall lists no inbound rules.
- `doctl compute droplet list` (or the MCP droplet list) is empty.
- The billing alerts are visible in the account settings.

## 6. Rollback

Before confirming, discard the Spacelift run and nothing changes. After apply, run `destroy` on the stack. Nothing here costs money, so leaving it in place is also safe.
