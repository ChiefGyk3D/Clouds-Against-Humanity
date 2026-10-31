# spaces-bucket

A private, versioned DigitalOcean Spaces bucket for the daemons' state
([stage 3 design](../../docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md)
sections 3b and 7, issue #113). Moving state off the host makes the droplet
disposable; versioning makes the bucket the first backup.

**Off by default.** A stack switches the whole module with `count = local.on`
(the edge host's pattern); with the count at 0 nothing is planned, so merging a
call changes nothing. The module has no switch of its own, because the cost gate
refuses `count` on the bucket resource. The $5 a month Spaces cost is approved
in the full stage 3 scope (2026-10-31) but nothing is built.

## What it makes (when called)

| Resource | Setting |
|---|---|
| `digitalocean_spaces_bucket` | ACL `private`, versioning on, `force_destroy` off |
| lifecycle rule | Noncurrent versions expire after `noncurrent_version_expiration_days` (default 90); incomplete multipart uploads are aborted after 7 days |
| `digitalocean_spaces_key` (optional) | One per name in `access_key_names`, each with a single `readwrite` grant on this bucket |

`acl` only accepts `private`. A public value fails validation instead of being
ignored. There is no public listing and no public read.

Keys are a second switch, `create_access_keys` (default false). A key's secret
is stored in OpenTofu state; the design leans on creating keys by hand and
keeping them in Doppler until Spacelift state access is restricted. A Spaces
grant names a bucket and a permission, not a prefix, so a key reaches the whole
bucket. The prefix per daemon is a convention, not a boundary.

## Inputs

| Name | Default | Meaning |
|---|---|---|
| `name` | required | Bucket name, 3 to 63 characters, lowercase letters, digits, hyphens |
| `region` | required | Spaces region slug, such as `tor1` |
| `acl` | `"private"` | Only `private` is accepted |
| `noncurrent_version_expiration_days` | `90` | 1 to 3650 |
| `create_access_keys` | `false` | Create the keys below |
| `access_key_names` | `[]` | Key names, unique |

## Outputs

`bucket_name`, `region`, `endpoint`, `bucket_domain_name` and `urn` are plain
strings (the module has no off state: switch it with `count` on the call). `access_keys` and `secret_keys` are maps by key name
and are marked sensitive. Do not print them; put them in Doppler.

## Restore

Overwritten and deleted objects stay as noncurrent versions for the lifecycle
window. To restore, list versions of the object (`aws s3api list-object-versions`
with the Spaces endpoint), then copy the wanted version over the current one
(`aws s3api copy-object --copy-source "bucket/key?versionId=ID"`). After the
window the old version is gone; the nightly copy off the account (design
section 7, layer 3) is the backstop. The commands are from the S3 API that
Spaces implements; they have not been run against a live bucket yet.

## Cost and approval

The maintainer approved the full stage 3 scope on 2026-10-31. The cost gate
prices a `{"kind": "spaces"}` entry in a stack's `cost.json` at the flat amount
in `docs/cost-prices.json` ($5.00 a month, source page and date in that entry),
allows `digitalocean_spaces_bucket` only in this module's `main.tf`, and treats
`digitalocean_spaces_key` as free. A stack that calls this module must use
`count = local.on`, define `on = var.<flag> ? 1 : 0`, and refuse the flag with an
output precondition unless its `cost.json` prices the bucket (see `docs/cost.md`).
Switching it on means adding the `spaces` entry to that `cost.json` and raising
the DigitalOcean `approved_monthly_total` to cover it, in the same reviewed
change. `cost.json` here is the reference copy of the entry.

## Provider extensions

None. This module is DigitalOcean-specific and not part of the provider
contract.
