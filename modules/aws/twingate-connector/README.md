# twingate-connector (AWS)

The AWS machine that runs a Twingate connector. The Twingate resources and the
hardened cloud-init are not here: they come from
[`../../twingate-bootstrap`](../../twingate-bootstrap), which every provider's
connector module calls, and `main.tf` passes its `user_data` straight to the
instance. Mocked-provider tests only: this module has never been applied to a
real AWS account.

| Role | DigitalOcean object | AWS object |
|---|---|---|
| The machine | `digitalocean_droplet` | `aws_instance` |
| Its identity | `instance_id`, `instance_name` | The instance id and its `Name` tag. |
| Its private address | `private_ip` | The primary interface's private address. |
| Its size | `size` | `instance_type`. |
| Boot data | `user_data` | `user_data`, unmodified from the bootstrap. |

Contract outputs: `instance_id`, `instance_name`, `private_ip`, `size`.

## Provider extensions

- **Placement and filtering.** `subnet_id` (from the vpc module) and
  `security_group_ids` (from the firewall module's `rule_targets`) are attached
  at launch, so there is no unprotected moment.
- **Public address, no way in.** `associate_public_ip_address = true`. The
  address is how the connector reaches Twingate and package mirrors without a NAT
  gateway; the group has no inbound rule from the internet. The address is a
  priced item.
- **IMDSv2.** The metadata service requires a session token, hop limit 1. This
  does not hide the boot data from a process already on the instance (threat T5).
- **No key pair, no instance profile.** cloud-init installs `admin_ssh_public_key`
  for the `cah-admin` user and SSH is reachable only through Twingate, so no AWS
  key pair is created. The connector never calls AWS, so it has no IAM identity.
- **Image.** Ubuntu 24.04 from Canonical's public SSM parameter, `architecture`
  `arm64` (default, Graviton types such as `t4g`) or `amd64` (such as `t3`). It
  must match `instance_type`. The image is chosen at creation and not replaced
  when Canonical publishes a newer one (`ignore_changes = [ami]`); updates come from
  unattended-upgrades.
- **Disk.** An explicit gp3 root volume, `root_volume_size` GiB (default 8, the
  smallest the image accepts), encrypted, baseline iops and throughput written
  out. The size is an input to the cost gate: the image's own default is not priced.
- **Replacement.** A changed cloud-init replaces the instance
  (`user_data_replace_on_change`), because cloud-init runs only on first boot.
