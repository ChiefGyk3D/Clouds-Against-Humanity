# SPDX-License-Identifier: Apache-2.0
# A private, versioned DigitalOcean Spaces bucket for the daemons' state
# (issue #113, stage 3 design section 3b). Unapplied and off: every resource is
# count 0 unless enabled is true, and the Spaces cost is not approved.

locals {
  on = var.enabled ? 1 : 0

  # Keys are a second opt-in on top of the master switch.
  key_names = var.enabled && var.create_access_keys ? toset(var.access_key_names) : toset([])
}

resource "digitalocean_spaces_bucket" "this" {
  count = local.on

  name   = var.name
  region = var.region

  # Private: no public listing, no public read. The variable only accepts private.
  acl = var.acl

  # A bucket holding state is never deleted with its contents by accident.
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "expire-noncurrent-versions"
    enabled = true
    prefix  = ""

    noncurrent_version_expiration {
      days = var.noncurrent_version_expiration_days
    }

    abort_incomplete_multipart_upload_days = 7
  }
}

# One key per daemon, each scoped to this one bucket. A grant names a bucket,
# so a key can never reach another one; fullaccess is not offered.
resource "digitalocean_spaces_key" "this" {
  for_each = local.key_names

  name = each.key

  grant {
    bucket     = digitalocean_spaces_bucket.this[0].name
    permission = "readwrite"
  }
}
