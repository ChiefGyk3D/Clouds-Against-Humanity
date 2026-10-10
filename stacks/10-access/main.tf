locals {
  cost      = jsondecode(file("${path.module}/cost.json"))
  connector = one([for r in local.cost.resources : r if r.name == "connector"])
}

resource "digitalocean_tag" "connector" {
  name = "cah-connector-${var.region}"
}

module "connector" {
  source           = "../../modules/twingate-connector"
  layer            = "access"
  region           = var.region
  vpc_id           = var.vpc_id
  tags             = [var.baseline_tag, digitalocean_tag.connector.name]
  size             = local.connector.size
  ssh_public_key   = var.admin_ssh_public_key
  twingate_network = var.twingate_network
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
  resources = [module.connector.droplet_urn]
}

resource "twingate_group" "admins" {
  name     = "cah-${var.region}-admins"
  user_ids = var.admin_user_ids
}

resource "twingate_resource" "connector_ssh" {
  name              = "cah-${var.region}-connector-ssh"
  address           = module.connector.private_ip
  remote_network_id = module.connector.remote_network_id

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
