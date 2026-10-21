# SPDX-License-Identifier: Apache-2.0
mock_provider "digitalocean" {}

variables {
  layer  = "state"
  region = "tor1"
}

run "one_private_versioned_bucket" {
  command = plan
  assert {
    condition     = digitalocean_spaces_bucket.this.name == "state-tor1-state"
    error_message = "Bucket name must be <layer>-<region>-<purpose>."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.region == "tor1"
    error_message = "The bucket must be created in the requested region."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.acl == "private"
    error_message = "The bucket ACL must be private."
  }
  assert {
    condition     = length(digitalocean_spaces_bucket.this.versioning) == 1 && digitalocean_spaces_bucket.this.versioning[0].enabled == true
    error_message = "Versioning must be on."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.force_destroy == false
    error_message = "A bucket that holds versions must not be force-destroyable."
  }
  assert {
    condition     = length(digitalocean_spaces_bucket.this.cors_rule) == 0
    error_message = "The bucket must carry no CORS rule."
  }
}

run "noncurrent_versions_expire_after_90_days_by_default" {
  command = plan
  assert {
    condition     = flatten([for r in digitalocean_spaces_bucket.this.lifecycle_rule : [for e in r.noncurrent_version_expiration : e.days] if r.enabled]) == [90]
    error_message = "Exactly one enabled noncurrent-version expiry, of 90 days, must be set."
  }
  assert {
    condition     = alltrue([for r in digitalocean_spaces_bucket.this.lifecycle_rule : length(r.expiration) == 0])
    error_message = "No rule may expire current versions."
  }
}

run "the_expiry_window_can_be_changed" {
  command = plan
  variables {
    noncurrent_version_days = 30
  }
  assert {
    condition     = flatten([for r in digitalocean_spaces_bucket.this.lifecycle_rule : [for e in r.noncurrent_version_expiration : e.days] if r.enabled]) == [30]
    error_message = "noncurrent_version_days must reach the lifecycle rule."
  }
}

run "resource_key_changes_the_name_not_the_region" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.name == "state-tor1-b-state" && digitalocean_spaces_bucket.this.region == "tor1"
    error_message = "A resource_key must replace the region in the name only."
  }
}

run "endpoint_is_the_regional_s3_endpoint" {
  command = plan
  assert {
    condition     = output.endpoint == "https://tor1.digitaloceanspaces.com"
    error_message = "The endpoint output must be the regional S3 endpoint."
  }
}

run "region_rejects_a_city_name" {
  command = plan
  variables {
    region = "toronto"
  }
  expect_failures = [var.region]
}

run "region_rejects_uppercase" {
  command = plan
  variables {
    region = "Tor1"
  }
  expect_failures = [var.region]
}

run "region_rejects_empty" {
  command = plan
  variables {
    region = ""
  }
  expect_failures = [var.region]
}

run "resource_key_rejects_uppercase" {
  command = plan
  variables {
    resource_key = "Tor1"
  }
  expect_failures = [var.resource_key]
}

run "expiry_rejects_zero" {
  command = plan
  variables {
    noncurrent_version_days = 0
  }
  expect_failures = [var.noncurrent_version_days]
}

run "expiry_rejects_a_fraction" {
  command = plan
  variables {
    noncurrent_version_days = 1.5
  }
  expect_failures = [var.noncurrent_version_days]
}

run "abort_days_rejects_zero" {
  command = plan
  variables {
    abort_incomplete_upload_days = 0
  }
  expect_failures = [var.abort_incomplete_upload_days]
}

run "layer_rejects_a_dash" {
  command = plan
  variables {
    layer = "my-state"
  }
  expect_failures = [var.layer]
}
