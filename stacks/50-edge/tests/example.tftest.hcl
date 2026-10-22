# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "digitalocean" {}

variables {
  # Example values for stacks/50-edge, the shared edge network (VPC, tags and Cloud
  # Firewall; no droplet, every edge service is its own stack later). UNAPPLIED: the
  # stage is not approved and the switch below is off. Copy this file to terraform.tfvars
  # (which git ignores) for a local plan. Never put a token, key or password in a
  # value file: those live in Doppler. Every value here is a placeholder or a
  # documentation/private range, not a real one.
  #
  # Droplet sizes are not set here. Each service stack prices its droplet in its
  # own cost.json, so the cost gate stays the one place that prices it.

  # Master switch. false creates nothing. Turning it on also needs
  # edge_network_approved = true in this stack's cost.json (docs/stages/05-edge.md).
  edge_enabled = false

  # DigitalOcean region slug, the same as core. Check the sizes your account may
  # use there first (GET /v2/sizes).
  region = "tor1"

  # Used in the NAMES of the firewall and droplet. Empty means region. IMMUTABLE for
  # the life of a stack. The VPC and the tags keep their fixed design names.
  resource_key = ""

  # Private CIDR of the edge VPC, written as its network address. It must not
  # overlap the core range below or anything in reserved_ranges.
  vpc_ip_range = "10.30.0.0/24"

  # The core VPC's range (stack 00-foundation), used only to refuse an overlap.
  core_vpc_ip_range = "10.78.0.0/24"

  # Private CIDRs the edge range must not overlap: your homelab, other VPCs. These
  # identify your network, so never commit the real list.
  reserved_ranges = ["10.50.0.0/16", "10.60.0.0/16"]

  # Public TCP port of the Reticulum TCPServerInterface. i2pd and iperf3 have no
  # variable here: they stay closed until their own stacks exist.
  reticulum_port = 4242
}

run "the_example_values_are_valid" {
  command = plan
}
