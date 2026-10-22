# SPDX-License-Identifier: Apache-2.0
# The public edge host (DMZ). One immutable droplet with no SSH, no Twingate
# connector and no admin path, a reserved IP that survives a rebuild, and a
# cloud-init that hardens the machine. Every change is a pull request, a plan
# and a rebuild. Design: docs/superpowers/specs/2026-10-19-edge-dmz-design.md.
# Unapplied: the stack that calls this module ships disabled.

locals {
  # Names use resource_key when it is set and region otherwise.
  name_key = var.resource_key != "" ? var.resource_key : var.region

  # One nftables accept per public port, and one per restricted port that has at
  # least one source. A restricted port with no source renders nothing, so it is
  # closed here exactly as it is in the Cloud Firewall.
  public_rules = [for r in var.public_ports : "${r.protocol} dport ${r.port_range} accept"]
  restricted_rules = [
    for r in var.restricted_ports :
    "${r.protocol} dport ${r.port_range} ip saddr { ${join(", ", r.sources)} } accept"
    if length(r.sources) > 0
  ]

  # Already indented for the cloud-init block scalar, each line ending in a newline.
  host_rules = join("", [for l in concat(local.public_rules, local.restricted_rules) : "          ${l}\n"])

  host_rule_descriptors = sort(concat(
    [for r in var.public_ports : "${r.protocol}/${r.port_range}/any"],
    [for r in var.restricted_ports : "${r.protocol}/${r.port_range}/restricted" if length(r.sources) > 0],
  ))
}

# The reserved IP is its own resource, assigned by a second one, so a rebuilt
# droplet keeps the address people and firewall rules know. Unassigned it costs
# money (design section 5.1); the cost gate treats it as a priced type.
resource "digitalocean_reserved_ip" "edge" {
  region = var.region
}

resource "digitalocean_reserved_ip_assignment" "edge" {
  ip_address = digitalocean_reserved_ip.edge.ip_address
  droplet_id = digitalocean_droplet.edge.id
}

# No ssh_keys on purpose: there is no admin path. The cloud-init locks the root
# password and stops sshd; the Droplet Console is not part of this design.
resource "digitalocean_droplet" "edge" {
  name       = "${var.layer}-${local.name_key}-transport"
  region     = var.region
  size       = var.size
  image      = "ubuntu-24-04-x64"
  vpc_uuid   = var.vpc_id
  tags       = var.tags
  ipv6       = false
  backups    = false
  monitoring = true

  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    timezone         = var.timezone
    reboot_time      = var.reboot_time
    host_rules       = local.host_rules
    service_packages = var.service_packages
  })
}
