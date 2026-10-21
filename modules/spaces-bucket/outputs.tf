# SPDX-License-Identifier: Apache-2.0
output "name" {
  value = digitalocean_spaces_bucket.this.name
}

output "region" {
  value = digitalocean_spaces_bucket.this.region
}

output "urn" {
  value = digitalocean_spaces_bucket.this.urn
}

# The S3-compatible endpoint (https://<region>.digitaloceanspaces.com), not the
# bucket's own domain: the daemons set it as their STATE_S3_ENDPOINT.
output "endpoint" {
  value = "https://${digitalocean_spaces_bucket.this.region}.digitaloceanspaces.com"
}

# Read back from the resource, not repeated as a literal, so a stack's tests
# can assert what the bucket really is configured to be.
output "acl" {
  value = digitalocean_spaces_bucket.this.acl
}

output "versioning_enabled" {
  value = one(digitalocean_spaces_bucket.this.versioning).enabled
}
