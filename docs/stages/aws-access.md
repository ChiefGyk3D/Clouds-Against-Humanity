# AWS stages 0 and 1: foundation and access

> **Status: written, tested with mocked providers, never applied.** No AWS account, no credential and no Spacelift stack exists for this code. **Do not create the Spacelift stacks `cah-aws-00-foundation` or `cah-aws-10-access` until the maintainer's check of Spacelift's native AWS integration on the current plan has passed** ([design](../superpowers/specs/2026-10-16-multicloud-design.md), section 10, decision 6). If that check fails, return to the maintainer before any fallback to a static key. `.spacelift/config.yml` has no AWS entry for the same reason.

This is the AWS twin of [stage 0](00-foundation.md) and [stage 1](01-access.md). The shape is the same: a foundation layer, then an access layer that builds two Twingate connectors with no public inbound. The objects underneath differ; the [provider pages](../wiki/Provider-AWS-The-Same-Four-Pieces.md) explain how.

## 1. What this builds

Stack `stacks/aws/00-foundation` (cost: nothing):

- One VPC with one public subnet, an internet gateway and an explicit route table (`modules/aws/vpc`), default range `10.78.0.0/24`. The VPC's default security group is emptied.
- A baseline security group with no inbound rule and the five default outbound ports (`modules/aws/firewall`). No stage 1 machine wears it (an instance carries exactly one group); it is the deny-all starting point for later stages.
- The AWS provider is configured with a region variable (default `us-east-1`, the region the price table was recorded for) and a `Project` default tag. It names no account id, profile, key or role. Credentials come from the environment at run time.
- Outputs: `vpc_id`, `vpc_ip_range`, `subnet_id`, `baseline_security_group_id`, `region`.

Stack `stacks/aws/10-access` (cost: $20.84 a month):

- One Twingate remote network `access-<region>`, the group `cah-<region>-admins`, and one restricted SSH resource per connector (TCP 22 only, UDP denied, no ICMP), the same as the DigitalOcean stack.
- Two `t4g.micro` instances, `access-<region>-connector-a` and `-b`, each running a Twingate connector (the shared `modules/twingate-bootstrap`). Each has a public IPv4 address, an 8 GiB encrypted gp3 root volume, standard CPU credits, IMDSv2 required, no key pair and no instance profile.
- A connector security group (the only group attached to either instance) with no inbound rule from any address. It has one inbound rule whose source is the group itself (TCP 22), mirrored by one outbound rule to the group itself, so each connector can reach the other's SSH as Twingate may route a session through either one (see [section 2c of stage 1](01-access.md)). Outbound to any address: tcp 443, 80, 53; udp 53, 123; tcp 30000-31000 and udp 1-65535 for Twingate peer-to-peer.
- The connectors reboot at 04:00 and 05:00 Eastern, so they never reboot together.
- Outputs: `connector_private_ips` (keys `a` and `b`), `connector_security_group_id`.

Values pass between the stacks the way they do on DigitalOcean: Spacelift stack dependencies mapped to `TF_VAR_*` variables, no remote state.

What the tests prove (`tofu test`, mocked providers, no account needed): names and wiring; instance type and root size read from `cost.json`; two connectors with distinct reboot times; the connector group has exactly the member-only SSH rule and no inbound from an address anywhere; the baseline has zero inbound; outputs; and that no stack file names an account id, profile, key or role. What they cannot prove is in section 7.

## 2. Prerequisites

1. The throwaway AWS account from [AWS account preparation](../wiki/Provider-AWS-Account-Preparation.md): root protected, a billing alert set, nothing else in the account.
2. The Spacelift AWS integration check passed (the warning at the top). Until then there is no way to run this stack without a long-lived key, which this project does not want.
3. The Spacelift role needs `ssm:GetParameter` on Canonical's public path `/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id`, plus the EC2 permissions to create the objects above. Scope it to the one region.
4. Doppler config `prd` holds `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, `ADMIN_SSH_PUBLIC_KEY` and `ADMIN_USER_IDS`, as for stage 1 (the key pair name `ADMIN_SSH_KEY_NAME` is not used on AWS: there is no key pair). **No AWS secret goes in Doppler** if the native integration is available.
5. Confirm `10.78.0.0/24` overlaps no homelab range, or set `vpc_ip_range`.
6. Record the check date of Twingate's [outbound allowlist article](https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure) here, as stage 1 does: not yet checked for this stack.

## 3. Cost

Planned $20.84 a month (two `t4g.micro` at $0.0084 an hour, two public IPv4 addresses at $0.005 an hour, two 8 GiB gp3 volumes at $0.08 per GiB-month), against an approved $21.00 for AWS. `approved.json` lists AWS as **inactive**: the shared ceiling is $30, and DigitalOcean stage 1 ($12) plus AWS ($21) would be $33. So **apply this only while the DigitalOcean access stage is torn down**, and flip `active` to true in `docs/stages/approved.json` at that moment (a deliberate edit, reviewed). Data transfer and anything created outside OpenTofu are not priced; a billing alert only notifies. See [cost](../cost.md) and the [AWS cost lesson](../wiki/Provider-AWS-Cost-Lesson.md).

`python3 -I scripts/cost_check.py --root .` reports `aws: planned $20.84/mo, approved $21.00, inactive`. Once a trusted run produces a real plan, run the gate with `--plan plan.json --stack stacks/aws/10-access` before the first apply; it prices what the plan resolves, which source code can hide.

## 4. Bootstrap (when the check has passed)

1. Create `cah-aws-00-foundation` rooted at `stacks/aws/00-foundation`, with the AWS integration attached and `TF_VAR_region` set.
2. Create `cah-aws-10-access` rooted at `stacks/aws/10-access`, depending on the foundation stack, with this mapping:

   | Foundation output | Environment variable |
   |---|---|
   | `vpc_id` | `TF_VAR_vpc_id` |
   | `subnet_id` | `TF_VAR_subnet_id` |
   | `region` | `TF_VAR_region` |

   The Doppler hook must export `TF_VAR_twingate_network`, `TF_VAR_admin_ssh_public_key` and `TF_VAR_admin_user_ids` for this stack, as it does for the DigitalOcean one.
3. Check that no Twingate site named `access-<region>` exists in the console (a hand-made one makes the apply fail or leaves a duplicate).
4. Add the two stacks to `.spacelift/config.yml` and the CI trigger paths in that same change, then run tracked. Autodeploy stays off; read the plan, then confirm.

## 5. Verify

1. Both connectors show online in the Twingate console, under `access-<region>`.
2. From a Twingate client: `ssh cah-admin@<private ip>` works for each address in `connector_private_ips`.
3. From outside Twingate, `nmap -Pn -p 22,80,443 <connector public ip>` shows the ports filtered (scanning your own instance is authorized).
4. The phase 4 acceptance checks in section 7, recorded with their command output.
5. `python3 -I scripts/cost_check.py --root .` still reports the planned AWS figure, and the AWS bill for the first day matches two instances, two public addresses and two 8 GiB volumes.

## 6. Rollback and teardown

Destroy `cah-aws-10-access` first, then `cah-aws-00-foundation`; the VPC is in use by the access stack until then. The connector tokens die with the instances and the Twingate site goes with the stack. Afterwards confirm in the console that no instance, volume or public address remains (an address left allocated keeps billing), then flip `active` back to false in `approved.json` if DigitalOcean stage 1 is returning. To rotate a token or the admin key, replace one connector at a time as in [stage 1 section 3](01-access.md); a changed cloud-init replaces the instance (`user_data_replace_on_change`) and probably changes its private address.

If a connector is offline, use the other one for SSH, then `sudo systemctl status twingate-connector` and `sudo cat /var/log/cah-connector-install.log`, as in stage 1 section 6a. There is no AWS key pair and no console password path by design, so a total loss of both connectors is recovered by replacing them in a run.

## 7. Phase 4 acceptance checklist (the first real apply must record all of these)

Mocked tests show the shape of the code, not AWS's behaviour. Keep the command output with the apply notes. Everything below is **UNVERIFIED** until then.

From the `vpc` module:

- [ ] The VPC's default security group has no rules (`describe-security-group-rules` filtered to it).
- [ ] The subnet's route table is the explicit one, with `0.0.0.0/0` to the internet gateway; the subnet does not use the main table.
- [ ] The default network ACL is still allow-all, as documented.

From the `firewall` module:

- [ ] `aws ec2 describe-security-group-rules` for the connector group: the seven outbound rules to `0.0.0.0/0`, the member rules (TCP 22 in and out, source and destination the group itself), no every-protocol (`-1`) egress rule, no inbound rule from `0.0.0.0/0` or `::/0`. The baseline group: five outbound rules, no inbound. Repeat after any manual console change (drift in a rule added outside the code is not detected).
- [ ] The egress rules exist before the instances boot (the declared ordering is UNVERIFIED).

From the `twingate-connector` module:

- [ ] Both network interfaces carry exactly the one connector group, not the default group or any other.
- [ ] `aws ec2 describe-instances`: `HttpTokens=required`, hop limit 1, no IAM instance profile, no key name, `CpuCredits=standard`.
- [ ] The root volumes are encrypted gp3, 8 GiB, 3000 IOPS, 125 MiB/s.
- [ ] The Canonical SSM parameter resolves to an available Ubuntu 24.04 arm64 image in the region and zone, matching `t4g.micro`.
- [ ] Both public IPv4 addresses are assigned and the route works (the connector reaches Twingate).
- [ ] `cloud-init status --wait` (through Twingate) completed and the connector is healthy in the console.
- [ ] The bill model matches the manifest: two instances, two public IPv4 addresses, two 8 GiB gp3 roots, standard credits, nothing else.

From these stacks:

- [ ] A peer-to-peer session through connector a to connector b's SSH resource works (the member rules do their job), and the reverse.
- [ ] Twingate's outbound allowlist check date recorded (section 2, item 6).
- [ ] `tofu plan` shows no `Project` tag drift on any resource (default tags interacting with module resources is untested against AWS).
