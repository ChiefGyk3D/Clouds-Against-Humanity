# SPDX-License-Identifier: Apache-2.0
locals {
  # Names use resource_key when it is set and region otherwise; the region
  # argument below always takes the real region.
  name_key = var.resource_key != "" ? var.resource_key : var.region
}

# One private, versioned bucket for the daemons' state. UNBUILT and never
# applied: the stack that calls this module keeps it behind a flag that is off.
#
# What this module deliberately does not contain:
#   - no digitalocean_spaces_bucket_policy, so no bucket policy of any kind
#     and nothing can make the bucket or an object public through one;
#   - no CORS rule (a browser never talks to this bucket);
#   - no access key (digitalocean_spaces_key): keys are made by hand and kept
#     in Doppler, so they never land in state (docs/stages/03-state-bucket.md).
resource "digitalocean_spaces_bucket" "this" {
  name   = "${var.layer}-${local.name_key}-${var.purpose}"
  region = var.region
  acl    = "private"

  # Deleting a bucket that still holds objects or versions must fail, not
  # empty it. Emptying a versioned bucket on purpose is a manual act.
  force_destroy = false

  versioning {
    enabled = true
  }

  # Old versions are the backup, so they are kept for a fixed time and then
  # expire. The current version of an object never expires: this rule only
  # reaches versions that a newer write or a delete has replaced.
  lifecycle_rule {
    id      = "expire-noncurrent-versions"
    enabled = true

    noncurrent_version_expiration {
      days = var.noncurrent_version_days
    }
  }

  # Half-finished uploads cost storage and are never read.
  lifecycle_rule {
    id                                     = "abort-incomplete-uploads"
    enabled                                = true
    abort_incomplete_multipart_upload_days = var.abort_incomplete_upload_days
  }
}
