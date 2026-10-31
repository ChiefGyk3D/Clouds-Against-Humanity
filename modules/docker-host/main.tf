# SPDX-License-Identifier: Apache-2.0
# One hardened Docker host (stage 3, design docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md
# section 5.3): a droplet in the VPC running Docker Engine and Portainer CE,
# set up by cloud-init. There is no Twingate connector in it; the stack gives the
# host its firewall and its Twingate resources. UNAPPLIED: only stacks/30-workloads
# calls this module, behind a switch that defaults to off.

locals {
  # Names use resource_key when it is set and region otherwise.
  name_key = var.resource_key != "" ? var.resource_key : var.region

  # What the cloud-init gets for the admin key: "<algorithm> <key>" only. A
  # trailing comment is accepted by the variable's validation and dropped here.
  admin_key_parts = split(" ", var.admin_ssh_public_key)
  admin_key       = "${local.admin_key_parts[0]} ${local.admin_key_parts[1]}"
}

resource "digitalocean_droplet" "workload" {
  name       = "${var.layer}-${local.name_key}-docker"
  region     = var.region
  size       = var.size
  image      = "ubuntu-24-04-x64"
  vpc_uuid   = var.vpc_id
  tags       = var.tags
  ssh_keys   = [var.ssh_key_fingerprint]
  ipv6       = false
  backups    = false
  monitoring = true

  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    timezone               = var.timezone
    reboot_time            = var.reboot_time
    admin_ssh_public_key   = local.admin_key
    docker_key_fingerprint = var.docker_apt_key_fingerprint
    portainer_version      = var.portainer_version
    portainer_port         = var.portainer_port
  })
}
