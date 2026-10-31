# SPDX-License-Identifier: Apache-2.0
# Stage 3, the workload host: one hardened droplet in the core VPC running
# Docker Engine and Portainer CE, reachable only through Twingate, with inbound
# traffic admitted only from the connectors' tag. Design:
# docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md; operator
# guide: docs/stages/03-workloads.md.
# UNAPPLIED and DISABLED: every resource and module call below is count 0
# unless workload_enabled is true, and the stage is not approved. Turning the
# switch on is refused until cost.json says the stage is approved and prices
# the droplet.

locals {
  # Names and tags use resource_key when it is set and region otherwise.
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  on = var.workload_enabled ? 1 : 0

  cost = jsondecode(file("${path.module}/cost.json"))

  # The droplet size is read from the cost manifest so the cost gate stays the
  # one place that prices it. Once the stage is approved the priced "workload"
  # droplet entry is the source; until then the manifest prices nothing and
  # carries the planned size under "planned".
  priced_workload = [for r in local.cost.resources : r if r.name == "workload" && r.kind == "droplet"]
  workload_size   = length(local.priced_workload) == 1 ? local.priced_workload[0].size : local.cost.planned.workload.size

  # The two ports this host exposes through Twingate, each as its own resource.
  # The Docker API is never one of them: Portainer talks to Docker over the
  # local socket.
  ssh_port       = "22"
  portainer_port = 9443
}

resource "digitalocean_tag" "workload" {
  count = local.on

  name = "cah-workload-${local.resource_key}"
}

# The admin key is already registered on the DigitalOcean account, and the API
# refuses a second registration of the same key (422), so look it up by name.
data "digitalocean_ssh_key" "admin" {
  count = local.on

  name = var.admin_ssh_key_name
}

# Inbound is deny-all except the connectors: each rule admits the connector tag
# only (never an address), for SSH and for Portainer. Outbound stays the
# firewall module's five defaults (tcp 443, 80, 53; udp 53, 123); the
# connectors' wide outbound ranges are not copied here. The connectors' own
# firewall still has to allow tcp 22 and the Portainer port outbound to this
# tag before the switch is turned on (docs/stages/03-workloads.md, section 4).
module "workload_firewall" {
  count = local.on

  source       = "../../modules/firewall"
  layer        = "workload"
  region       = var.region
  resource_key = var.resource_key
  purpose      = "host"
  tag          = digitalocean_tag.workload[0].name
  inbound_from_other_tags = [
    { protocol = "tcp", port_range = local.ssh_port, tag = var.connector_tag },
    { protocol = "tcp", port_range = tostring(local.portainer_port), tag = var.connector_tag },
  ]
}

# user_data comes from the module's cloud-init: a change to it replaces the droplet.
module "workload" {
  count = local.on

  source = "../../modules/docker-host"

  layer                = "workload"
  region               = var.region
  resource_key         = var.resource_key
  vpc_id               = var.vpc_id
  tags                 = [var.baseline_tag, digitalocean_tag.workload[0].name]
  size                 = local.workload_size
  ssh_key_fingerprint  = data.digitalocean_ssh_key.admin[0].fingerprint
  admin_ssh_public_key = var.admin_ssh_public_key
  reboot_time          = var.reboot_time
  timezone             = var.timezone
  portainer_version    = var.portainer_version
  portainer_port       = local.portainer_port
}

resource "digitalocean_project_resources" "workload" {
  count = local.on

  project   = var.project_id
  resources = [module.workload[0].droplet_urn]
}

# One narrow Twingate resource per port: one private address, one TCP port,
# granted to the admins group. No ICMP, no UDP.
resource "twingate_resource" "ssh" {
  count = local.on

  name              = "cah-${local.resource_key}-workload-ssh"
  address           = module.workload[0].private_ip
  remote_network_id = var.remote_network_id

  access_group {
    group_id = var.admin_group_id
  }

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = [local.ssh_port]
    }
    udp = {
      policy = "DENY_ALL"
    }
  }
}

resource "twingate_resource" "portainer" {
  count = local.on

  name              = "cah-${local.resource_key}-workload-portainer"
  address           = module.workload[0].private_ip
  remote_network_id = var.remote_network_id

  access_group {
    group_id = var.admin_group_id
  }

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = [tostring(local.portainer_port)]
    }
    udp = {
      policy = "DENY_ALL"
    }
  }
}
