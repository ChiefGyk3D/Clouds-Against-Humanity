# SPDX-License-Identifier: Apache-2.0
mock_provider "digitalocean" {}

variables {
  name   = "cah-state-tor1"
  region = "tor1"
}

run "plans_a_private_versioned_bucket" {
  command = plan
  assert {
    condition     = output.bucket_name == "cah-state-tor1" && output.region == "tor1"
    error_message = "A call to the module plans exactly one bucket (the switch is the caller's count)."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.versioning[0].enabled == true
    error_message = "Versioning must be on."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.acl == "private"
    error_message = "The bucket ACL must be private."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.name == "cah-state-tor1" && digitalocean_spaces_bucket.this.region == "tor1"
    error_message = "Name and region must come from the variables."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.force_destroy == false
    error_message = "The bucket must not be force-destroyable."
  }
  assert {
    condition     = length(digitalocean_spaces_key.this) == 0
    error_message = "Keys are a separate opt-in and must not appear by default."
  }
}

run "lifecycle_expires_old_versions_after_90_days_by_default" {
  command = plan
  assert {
    condition     = length(digitalocean_spaces_bucket.this.lifecycle_rule) == 1
    error_message = "Exactly one lifecycle rule is expected."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.lifecycle_rule[0].enabled == true
    error_message = "The lifecycle rule must be enabled."
  }
  assert {
    condition     = one([for n in digitalocean_spaces_bucket.this.lifecycle_rule[0].noncurrent_version_expiration : n.days]) == 90
    error_message = "Noncurrent versions must expire after 90 days by default."
  }
  assert {
    condition     = digitalocean_spaces_bucket.this.lifecycle_rule[0].prefix == ""
    error_message = "The rule must cover the whole bucket."
  }
}

run "lifecycle_days_are_configurable" {
  command = plan
  variables {
    noncurrent_version_expiration_days = 30
  }
  assert {
    condition     = one([for n in digitalocean_spaces_bucket.this.lifecycle_rule[0].noncurrent_version_expiration : n.days]) == 30
    error_message = "noncurrent_version_expiration_days must reach the rule."
  }
}

run "rejects_zero_lifecycle_days" {
  command = plan
  variables {
    noncurrent_version_expiration_days = 0
  }
  expect_failures = [var.noncurrent_version_expiration_days]
}

run "rejects_public_read_acl" {
  command = plan
  variables {
    acl     = "public-read"
  }
  expect_failures = [var.acl]
}

run "rejects_public_read_write_acl" {
  command = plan
  variables {
    acl = "public-read-write"
  }
  expect_failures = [var.acl]
}

run "rejects_authenticated_read_acl" {
  command = plan
  variables {
    acl = "authenticated-read"
  }
  expect_failures = [var.acl]
}

run "rejects_an_uppercase_name" {
  command = plan
  variables {
    name = "CAH-State"
  }
  expect_failures = [var.name]
}

run "rejects_a_name_with_an_underscore" {
  command = plan
  variables {
    name = "cah_state"
  }
  expect_failures = [var.name]
}

run "rejects_a_name_that_is_too_short" {
  command = plan
  variables {
    name = "ab"
  }
  expect_failures = [var.name]
}

run "rejects_a_name_that_is_too_long" {
  command = plan
  variables {
    name = "a1234567890123456789012345678901234567890123456789012345678901234"
  }
  expect_failures = [var.name]
}

run "rejects_a_name_that_ends_with_a_hyphen" {
  command = plan
  variables {
    name = "cah-state-"
  }
  expect_failures = [var.name]
}

run "rejects_a_bad_region" {
  command = plan
  variables {
    region = "Toronto"
  }
  expect_failures = [var.region]
}

run "keys_are_scoped_to_the_one_bucket" {
  command = plan
  variables {
    create_access_keys = true
    access_key_names   = ["penguin-overlord", "star-daemon"]
  }
  assert {
    condition     = length(digitalocean_spaces_key.this) == 2
    error_message = "One key per requested name."
  }
  assert {
    condition = alltrue([
      for k in digitalocean_spaces_key.this :
      length(k.grant) == 1 && one(k.grant).bucket == "cah-state-tor1" && one(k.grant).permission == "readwrite"
    ])
    error_message = "Every key must carry exactly one grant: readwrite on this bucket, never fullaccess and never all buckets."
  }
}

run "keys_cannot_be_fullaccess_or_empty_grant" {
  command = plan
  variables {
    create_access_keys = true
    access_key_names   = ["penguin-overlord"]
  }
  assert {
    condition     = alltrue([for k in digitalocean_spaces_key.this : one(k.grant).bucket != "" && one(k.grant).permission != "fullaccess"])
    error_message = "A key with an empty bucket or fullaccess is not scoped."
  }
}

run "secret_outputs_are_sensitive" {
  command = plan
  variables {
    create_access_keys = true
    access_key_names   = ["penguin-overlord"]
  }
  assert {
    condition     = issensitive(output.secret_keys)
    error_message = "secret_keys must be marked sensitive."
  }
  assert {
    condition     = issensitive(output.access_keys)
    error_message = "access_keys must be marked sensitive."
  }
}

run "rejects_duplicate_key_names" {
  command = plan
  variables {
    access_key_names = ["a-daemon", "a-daemon"]
  }
  expect_failures = [var.access_key_names]
}

run "rejects_a_bad_key_name" {
  command = plan
  variables {
    access_key_names = ["Bad Name"]
  }
  expect_failures = [var.access_key_names]
}
