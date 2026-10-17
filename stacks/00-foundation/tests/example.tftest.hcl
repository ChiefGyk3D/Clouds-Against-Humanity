# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "digitalocean" {}

variables {
  # Example values for stacks/00-foundation. Copy this file to terraform.tfvars
  # (which git ignores) for a local plan. Never put a token, key or password in a
  # value file: those live in Doppler. Every value here is a placeholder or a
  # private/documentation range, not a real one. The real values of a live stack
  # come from the Spacelift stack environment (TF_VAR_*) or Doppler.
  #
  # Sizes are not set here. A droplet size lives in cost.json, so the cost gate
  # stays the one place that prices it (see docs/cost.md).

  # DigitalOcean region slug: three lowercase letters and a digit. Check the sizes
  # your account may use there first (GET /v2/sizes).
  region = "tor1"

  # Private CIDR for the VPC, written as its network address. Prefix length between
  # /16 and /28, and it must not overlap anything in reserved_ranges.
  vpc_ip_range = "10.99.0.0/24"

  # Private CIDRs the VPC range must not overlap: your homelab, other VPCs,
  # anything you connect to. These identify your network, so never commit the real
  # list. Today it arrives as TF_VAR_reserved_ranges in the Spacelift stack
  # environment (a JSON list) or from a private tfvars; Doppler only once a hook
  # line in .spacelift/config.yml requests it.
  reserved_ranges = ["10.50.0.0/16", "10.60.0.0/16"]

  # Name of the DigitalOcean project that groups the resources.
  project_name = "clouds-against-humanity"

  # Used in the NAMES and TAGS of cloud objects. Empty means region, so every name
  # is the same as before this setting existed. IMMUTABLE for the life of a stack:
  # changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data. Set it only on a NEW stack,
  # for example "tor1-b" for a second site in the same region.
  resource_key = ""

  # A label for telemetry only (empty means "site-<region>"). It appears in no
  # resource name, tag or output, and changing it replaces nothing.
  site_name = "site-tor1"
}

run "the_example_values_are_valid" {
  command = plan
}
