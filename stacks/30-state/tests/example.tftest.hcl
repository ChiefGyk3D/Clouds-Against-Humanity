# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "digitalocean" {}

variables {
  # Example values for stacks/30-state. Copy this file to terraform.tfvars (which
  # git ignores) for a local plan. Never put a token or an access key in a value
  # file: those live in Doppler. Every value here is a placeholder.

  # Create the private, versioned Spaces bucket. Leave false until the maintainer
  # has approved stage 3 and the cost gate prices the bucket (docs/stages/03-state-bucket.md).
  state_bucket_enabled = false

  # DigitalOcean region slug: three lowercase letters and a digit.
  region = "tor1"

  # Used in the bucket NAME (cah-<key>-state). Empty means region. IMMUTABLE for the life
  # of the bucket: a different name is a different, empty bucket. Set one only if the
  # default name is already taken in the region.
  resource_key = ""

  # Days a replaced or deleted version is kept before it expires (the restore window).
  noncurrent_version_days = 90

  # Days after which an unfinished multipart upload is aborted.
  abort_incomplete_upload_days = 7
}

run "the_example_values_are_valid" {
  command = plan
}
