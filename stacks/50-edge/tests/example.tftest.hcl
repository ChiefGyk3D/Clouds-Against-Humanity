# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.

mock_provider "digitalocean" {
  mock_resource "digitalocean_droplet" {
    defaults = {
      id = "12345678"
    }
  }
  mock_resource "digitalocean_reserved_ip" {
    defaults = {
      ip_address = "203.0.113.10"
    }
  }
}

variables {
  # Example values for stacks/50-edge, the public edge (DMZ). UNAPPLIED: the stage
  # is not approved and the switch below is off. Copy this file to terraform.tfvars
  # (which git ignores) for a local plan. Never put a token, key or password in a
  # value file: those live in Doppler. Every value here is a placeholder or a
  # documentation/private range, not a real one.
  #
  # The droplet size is not priced here. It lives in cost.json, so the cost gate
  # stays the one place that prices it (see docs/cost.md).

  # Master switch. false creates nothing. Turning it on also needs a priced
  # cost.json and the cost gate's reserved IP support (docs/stages/05-edge.md).
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

  # Droplet size slug. Enabling the edge requires cost.json to price this size.
  droplet_size = "s-1vcpu-1gb"

  # Public TCP port of the Reticulum TCPServerInterface.
  reticulum_port = 4242

  # The pinned inbound i2pd port (TCP and UDP). The default is null, which opens
  # nothing; the design names no number, so this one is only an example.
  i2pd_port = 24680

  # IPv4 ranges allowed to reach iperf3 (TCP 5201). Empty keeps it closed. The real
  # value is the owner's address and comes from Doppler; this is a documentation range.
  iperf3_allowed_sources = ["203.0.113.10/32"]

  # HH:MM (UTC) when unattended-upgrades may reboot the host. Keep it clear of the
  # connectors' reboot times.
  reboot_time = "05:00"
}

run "the_example_values_are_valid" {
  command = plan
}
