locals {
  # Names and tags use resource_key when it is set and region otherwise. The
  # region argument of the droplets and modules stays var.region.
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
  connector_b = one([for r in local.cost.resources : r if r.name == "connector-b"])
}

resource "digitalocean_tag" "connector" {
  name = "cah-connector-${local.resource_key}"
}

# One site and one SSH key for every connector, so the connectors are redundant
# members of the same Twingate remote network.
resource "twingate_remote_network" "this" {
  name     = "access-${local.resource_key}"
  location = "OTHER"
}

# The admin key is already registered on the DigitalOcean account, and the API
# refuses a second registration of the same key (422), so look it up by name.
data "digitalocean_ssh_key" "admin" {
  name = var.admin_ssh_key_name
}

module "connector_a" {
  source              = "../../modules/twingate-connector"
  layer               = "access"
  region              = var.region
  resource_key        = var.resource_key
  vpc_id              = var.vpc_id
  tags                = [var.baseline_tag, digitalocean_tag.connector.name]
  size                = local.connector_a.size
  remote_network_id   = twingate_remote_network.this.id
  ssh_key_fingerprint = data.digitalocean_ssh_key.admin.fingerprint
  instance            = "a"
  twingate_network    = var.twingate_network

  admin_ssh_public_key = var.admin_ssh_public_key
  # In var.timezone (Eastern by default), staggered so the two connectors never reboot together
  # (reboot_times is validated to hold two different times).
  reboot_time = var.reboot_times["a"]
  timezone    = var.timezone

  connector_telemetry = contains(var.connector_telemetry_instances, "a") ? var.connector_telemetry : var.connector_telemetry_previous

  metadata_lock = var.metadata_lock && contains(var.metadata_lock_instances, "a")

  # The outbound rules must exist before the droplet boots and starts to install.
  depends_on = [module.connector_firewall]
}

module "connector_b" {
  source              = "../../modules/twingate-connector"
  layer               = "access"
  region              = var.region
  resource_key        = var.resource_key
  vpc_id              = var.vpc_id
  tags                = [var.baseline_tag, digitalocean_tag.connector.name]
  size                = local.connector_b.size
  remote_network_id   = twingate_remote_network.this.id
  ssh_key_fingerprint = data.digitalocean_ssh_key.admin.fingerprint
  instance            = "b"
  twingate_network    = var.twingate_network

  admin_ssh_public_key = var.admin_ssh_public_key
  reboot_time          = var.reboot_times["b"]
  timezone             = var.timezone

  connector_telemetry = contains(var.connector_telemetry_instances, "b") ? var.connector_telemetry : var.connector_telemetry_previous

  metadata_lock = var.metadata_lock && contains(var.metadata_lock_instances, "b")

  depends_on = [module.connector_firewall]
}

# The baseline firewall already denies all inbound traffic. This one adds the
# outbound ports the connector needs and TCP 22 in both directions between
# droplets with the connector tag. Twingate may route a session to either
# connector, so each must reach the other's SSH (all connectors in a remote
# network need identical reach:
# https://www.twingate.com/docs/connector-best-practices). The target needs the
# inbound rule to accept, and the sender needs the outbound rule to open the
# connection: DigitalOcean firewalls are stateful for replies, but a new
# connection is allowed out only if an outbound rule permits it. Both rules name
# the connector tag, never an address. SSH is still only
# reachable from outside through Twingate; there is no public inbound. Twingate's allowlist article
# (https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure)
# requires outbound UDP to any port for peer-to-peer connections, so UDP is
# open outbound only; inbound stays deny-all. Record the check date in the stage guide.
module "connector_firewall" {
  source       = "../../modules/firewall"
  layer        = "access"
  region       = var.region
  resource_key = var.resource_key
  purpose      = "connector"
  tag          = digitalocean_tag.connector.name
  inbound_from_tag_rules = [
    { protocol = "tcp", port_range = "22" },
  ]
  outbound_to_tag_rules = [
    { protocol = "tcp", port_range = "22" },
  ]
  extra_outbound_rules = [
    { protocol = "tcp", port_range = "30000-31000" },
    { protocol = "udp", port_range = "1-65535" },
  ]
}

resource "digitalocean_project_resources" "access" {
  project   = var.project_id
  resources = [module.connector_a.droplet_urn, module.connector_b.droplet_urn]
}

resource "twingate_group" "admins" {
  name     = "cah-${local.resource_key}-admins"
  user_ids = var.admin_user_ids
}

resource "twingate_resource" "connector_a_ssh" {
  name              = "cah-${local.resource_key}-connector-a-ssh"
  address           = module.connector_a.private_ip
  remote_network_id = twingate_remote_network.this.id

  access_group {
    group_id = twingate_group.admins.id
  }

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = ["22"]
    }
    udp = {
      policy = "DENY_ALL"
    }
  }
}

resource "twingate_resource" "connector_b_ssh" {
  name              = "cah-${local.resource_key}-connector-b-ssh"
  address           = module.connector_b.private_ip
  remote_network_id = twingate_remote_network.this.id

  access_group {
    group_id = twingate_group.admins.id
  }

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = ["22"]
    }
    udp = {
      policy = "DENY_ALL"
    }
  }
}
