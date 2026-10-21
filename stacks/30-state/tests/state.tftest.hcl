# SPDX-License-Identifier: Apache-2.0
mock_provider "digitalocean" {}

run "flag_off_by_default_creates_nothing" {
  command = plan
  assert {
    condition     = length(module.state_bucket) == 0
    error_message = "With the flag at its default the stack must plan no bucket."
  }
  assert {
    condition     = output.bucket_name == null && output.bucket_region == null && output.bucket_endpoint == null && output.bucket_acl == null && output.bucket_versioning_enabled == null
    error_message = "Every output must be null while the flag is off."
  }
}

run "flag_explicitly_false_creates_nothing" {
  command = plan
  variables {
    state_bucket_enabled = false
  }
  assert {
    condition     = length(module.state_bucket) == 0
    error_message = "state_bucket_enabled = false must plan no bucket."
  }
}

run "flag_on_creates_exactly_one_private_versioned_bucket" {
  command = plan
  variables {
    state_bucket_enabled = true
  }
  assert {
    condition     = length(module.state_bucket) == 1
    error_message = "The flag must create exactly one bucket module instance."
  }
  assert {
    condition     = output.bucket_name == "cah-tor1-state" && output.bucket_region == "tor1"
    error_message = "The default bucket is cah-tor1-state in tor1."
  }
  assert {
    condition     = output.bucket_versioning_enabled == true
    error_message = "Versioning must be on."
  }
  assert {
    condition     = output.bucket_acl == "private"
    error_message = "The ACL must be private."
  }
  assert {
    condition     = output.bucket_endpoint == "https://tor1.digitaloceanspaces.com"
    error_message = "The endpoint must be the regional S3 endpoint."
  }
}

run "resource_key_names_the_bucket_and_region_stays_the_region" {
  command = plan
  variables {
    state_bucket_enabled = true
    resource_key         = "tor1-b"
  }
  assert {
    condition     = output.bucket_name == "cah-tor1-b-state" && output.bucket_region == "tor1"
    error_message = "A resource_key must replace the region in the name only."
  }
}

run "region_flows_into_the_bucket" {
  command = plan
  variables {
    state_bucket_enabled = true
    region               = "fra1"
  }
  assert {
    condition     = output.bucket_name == "cah-fra1-state" && output.bucket_region == "fra1"
    error_message = "Changing region must change the name and the region."
  }
}

run "an_invalid_region_is_rejected" {
  command = plan
  variables {
    state_bucket_enabled = true
    region               = "toronto"
  }
  expect_failures = [var.region]
}

run "an_invalid_region_is_rejected_even_with_the_flag_off" {
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

run "the_restore_window_is_rejected_below_one_day" {
  command = plan
  variables {
    noncurrent_version_days = 0
  }
  expect_failures = [var.noncurrent_version_days]
}

run "the_restore_window_reaches_the_module" {
  command = plan
  variables {
    state_bucket_enabled    = true
    noncurrent_version_days = 30
  }
  assert {
    condition     = length(module.state_bucket) == 1
    error_message = "A changed restore window must still plan the bucket."
  }
}

run "the_stack_declares_no_costed_resource_of_its_own" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "resource \"")
    error_message = "The stack must hold only the module call; the bucket is the module's."
  }
}
