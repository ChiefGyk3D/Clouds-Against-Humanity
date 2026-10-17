# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "digitalocean" {
  mock_data "digitalocean_ssh_key" {
    defaults = {
      fingerprint = "aa:bb:cc:dd:ee:ff"
    }
  }
}
mock_provider "twingate" {}

variables {
  # Example values for stacks/10-access. Copy this file to terraform.tfvars
  # (which git ignores) for a local plan. Never put a token, key or password in a
  # value file: those live in Doppler. Every value here is a placeholder, not a
  # real one. In the live stack the first five arrive as TF_VAR_* from the
  # foundation stack's outputs and the Spacelift environment, and the rest from
  # Doppler through the Spacelift hook.
  #
  # Droplet sizes are not set here. They live in cost.json, so the cost gate stays
  # the one place that prices them (see docs/cost.md).

  # DigitalOcean region slug, from the foundation stack's region output.
  region = "tor1"

  # Id of the VPC the connectors join, from the foundation stack's vpc_id output.
  vpc_id = "vpc-example-0000"

  # Id of the DigitalOcean project, from the foundation stack's project_id output.
  project_id = "project-example-0000"

  # Baseline firewall tag, from the foundation stack's baseline_tag output. It must
  # start with "cah-baseline-" so the baseline firewall covers the connectors.
  baseline_tag = "cah-baseline-tor1"

  # Bare Twingate network subdomain (only the part before the Twingate domain). Private: it
  # identifies your tenant, so the real one comes from Doppler.
  twingate_network = "example-tenant"

  # Public SSH key for the cah-admin user: "<algorithm> <key>" with an optional
  # one-word comment. The comment is dropped before the key reaches the droplet.
  # This placeholder is deliberately not a real key. The real one comes from Doppler.
  admin_ssh_public_key = "ssh-ed25519 AAAAEXAMPLEONLYNOTAREALKEY example-key"

  # Name of an SSH key already registered on the DigitalOcean account (it is looked
  # up, never registered). The real name comes from Doppler.
  admin_ssh_key_name = "example-admin-key"

  # Twingate user ids placed in the admin group (at least one). The real ids come
  # from Doppler.
  admin_user_ids = ["example-user-id"]

  # When each connector may reboot, HH:MM in America/New_York (the droplet's local
  # time). Keys a and b. The two times must be at least 60 minutes apart around the
  # clock (across midnight too), so the connectors never reboot together and the
  # weekly update, 30 minutes after each reboot, stays clear of the other reboot.
  # These are the times the live connectors use.
  reboot_times = { a = "04:00", b = "05:00" }

  # IANA time zone of the droplets (UTC or Area/Location). reboot_times above and
  # the weekly connector update are read in this zone. The default is the zone the
  # live connectors use. Changing it changes the rendered cloud-init (user_data),
  # which is force-new: both droplets are REPLACED, so read the plan first.
  timezone = "America/New_York"

  # Used in the NAMES and TAGS of cloud and Twingate objects (access-<key>,
  # cah-connector-<key>, droplet names). Empty means region, so every name is the
  # same as before this setting existed. IMMUTABLE for the life of a stack:
  # changing it changes names, causes widespread plan changes and may replace resources, including through tags or user_data including the connectors.
  # Set it only on a NEW stack, and use the same value as the foundation stack.
  resource_key = ""

  # Twingate connector telemetry (both connectors). The default, {}, changes nothing.
  # Setting any of log_level, connection_logs, metrics_port or labels adds lines to
  # /etc/twingate/connector.conf, which changes user_data: the plan then shows BOTH
  # droplets REPLACED. Roll out one connector at a time with
  # connector_telemetry_instances (["a"] first, then ["a", "b"]) and an
  # SSH-through-Twingate check between (docs/wiki/Trace-One-Change-End-to-End.md,
  # variant C). It opens no firewall port. Uncomment to try it; the values are
  # placeholders.
  # connector_telemetry = {
  #   status_updates_enabled = true         # provider setting, not sent while unset, never replaces anything
  #   log_level              = 5            # 3, 4, 5 or 7 (Twingate's default is 3)
  #   connection_logs        = true         # TWINGATE_LOG_ANALYTICS=v3 (user emails and client IPs in the journal)
  #   metrics_port           = 9999         # TWINGATE_METRICS_PORT, 1024 to 65535, not 9100
  #   labels                 = { DEPLOYED_BY = "opentofu" }  # shown in the Admin Console: no secrets
  # }
  connector_telemetry = {}

  # Which connectors get connector_telemetry (a, b or both). Default both.
  connector_telemetry_instances = ["a", "b"]

  # What the connectors NOT listed above keep (their current telemetry). {} for the
  # first activation. For a later change, put the old value here and list ["a"]
  # first, so b keeps its config while a changes.
  connector_telemetry_previous = {}

  # Lock the droplet metadata endpoint (169.254.169.254, which serves each
  # connector's user-data and so its Twingate tokens) to root and to the do-agent
  # user that DigitalOcean's monitoring agent runs as. Default false changes
  # nothing. true REPLACES the droplet of every connector in
  # metadata_lock_instances (user_data changes). Roll out one at a time:
  # metadata_lock = true with ["a"], apply, check SSH through Twingate, then
  # ["a", "b"]. Not yet tested on a real droplet.
  metadata_lock = false

  # Which connectors get metadata_lock (a, b or both). Default both.
  metadata_lock_instances = ["a", "b"]

  # A label for telemetry only (empty means "site-<region>"). It appears in no
  # resource name, tag or output, and changing it replaces nothing.
  site_name = "site-tor1"
}

run "the_example_values_are_valid" {
  command = plan
}
