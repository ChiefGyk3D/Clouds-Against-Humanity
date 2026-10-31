# SPDX-License-Identifier: Apache-2.0
# A private, versioned DigitalOcean Spaces bucket for the daemons' state
# (issue #113, stage 3 design section 3b). Unapplied and off. The off switch is
# the caller's: a stack calls this module with `count = local.on`, the same plain
# switch modules/edge-host uses, because the cost gate refuses count on the
# bucket resource itself (a costed type) and prices the bucket from the stack's
# cost.json instead. Called with count 0, nothing here is planned at all.

locals {
  # Keys are a second opt-in on top of the module call itself.
  key_names = var.create_access_keys ? toset(var.access_key_names) : toset([])
}

resource "digitalocean_spaces_bucket" "this" {
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
    bucket     = digitalocean_spaces_bucket.this.name
    permission = "readwrite"
  }
}
