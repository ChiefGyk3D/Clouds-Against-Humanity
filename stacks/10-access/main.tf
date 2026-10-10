locals {
  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
  connector_b = one([for r in local.cost.resources : r if r.name == "connector-b"])
}

resource "digitalocean_tag" "connector" {
  name = "cah-connector-${var.region}"
}

# One site and one SSH key for every connector, so the connectors are redundant
# members of the same Twingate remote network.
resource "twingate_remote_network" "this" {
  name     = "access-${var.region}"
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
  vpc_id              = var.vpc_id
  tags                = [var.baseline_tag, digitalocean_tag.connector.name]
  size                = local.connector_a.size
  remote_network_id   = twingate_remote_network.this.id
  ssh_key_fingerprint = data.digitalocean_ssh_key.admin.fingerprint
  instance            = "a"
  twingate_network    = var.twingate_network

  # The outbound rules must exist before the droplet boots and starts to install.
  depends_on = [module.connector_firewall]
}

module "connector_b" {
  source              = "../../modules/twingate-connector"
  layer               = "access"
  region              = var.region
  vpc_id              = var.vpc_id
  tags                = [var.baseline_tag, digitalocean_tag.connector.name]
  size                = local.connector_b.size
  remote_network_id   = twingate_remote_network.this.id
  ssh_key_fingerprint = data.digitalocean_ssh_key.admin.fingerprint
  instance            = "b"
  twingate_network    = var.twingate_network

  depends_on = [module.connector_firewall]
}

# The baseline firewall already denies all inbound traffic. This one only adds
# the outbound ports the connector needs. Verify the list against Twingate's
# current firewall documentation before apply and record the date in the stage guide.
module "connector_firewall" {
  source  = "../../modules/firewall"
  layer   = "access"
  region  = var.region
  purpose = "connector"
  tag     = digitalocean_tag.connector.name
  extra_outbound_rules = [
    { protocol = "tcp", port_range = "30000-31000" },
    { protocol = "udp", port_range = "19302-19308" },
    { protocol = "udp", port_range = "443" },
  ]
}

resource "digitalocean_project_resources" "access" {
  project   = var.project_id
  resources = [module.connector_a.droplet_urn, module.connector_b.droplet_urn]
}

resource "twingate_group" "admins" {
  name     = "cah-${var.region}-admins"
  user_ids = var.admin_user_ids
}

resource "twingate_resource" "connector_a_ssh" {
  name              = "cah-${var.region}-connector-a-ssh"
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
  name              = "cah-${var.region}-connector-b-ssh"
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
