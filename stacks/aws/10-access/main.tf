locals {
  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
  connector_b = one([for r in local.cost.resources : r if r.name == "connector-b"])
}

# One site for every connector, so the connectors are redundant members of the
# same Twingate remote network.
resource "twingate_remote_network" "this" {
  name     = "access-${var.region}"
  location = "OTHER"
}

# Only this security group is attached to a connector (an instance wears
# exactly one group). It has no inbound rule from any address. Its member
# rules name the group itself as source and destination: Twingate may route a
# session to either connector, so each must reach the other's SSH (all
# connectors in a remote network need identical reach:
# https://www.twingate.com/docs/connector-best-practices). The target needs the
# inbound rule to accept, and the sender needs the outbound rule to open the
# connection. Twingate's allowlist article
# (https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure)
# requires outbound UDP to any port for peer-to-peer connections, so UDP is
# open outbound only; inbound stays deny-all. Record the check date in the
# stage guide.
module "connector_firewall" {
  source  = "../../../modules/aws/firewall"
  layer   = "access"
  region  = var.region
  purpose = "connector"
  vpc_id  = var.vpc_id
  inbound_from_member_rules = [
    { protocol = "tcp", port_range = "22" },
  ]
  outbound_to_member_rules = [
    { protocol = "tcp", port_range = "22" },
  ]
  extra_outbound_rules = [
    { protocol = "tcp", port_range = "30000-31000" },
    { protocol = "udp", port_range = "1-65535" },
  ]
}

module "connector_a" {
  source               = "../../../modules/aws/twingate-connector"
  layer                = "access"
  region               = var.region
  subnet_id            = var.subnet_id
  security_group_id    = one(module.connector_firewall.rule_targets)
  instance_type        = local.connector_a.type
  root_volume_size     = local.connector_a.root_gb
  remote_network_id    = twingate_remote_network.this.id
  instance             = "a"
  twingate_network     = var.twingate_network
  admin_ssh_public_key = var.admin_ssh_public_key
  # In var.timezone (Eastern by default), staggered so the two connectors never reboot together.
  reboot_time = "04:00"
  timezone    = var.timezone

  connector_telemetry = contains(var.connector_telemetry_instances, "a") ? var.connector_telemetry : var.connector_telemetry_previous

  metadata_lock = var.metadata_lock && contains(var.metadata_lock_instances, "a")

  # The outbound rules must exist before the instance boots and starts to install.
  depends_on = [module.connector_firewall]
}

module "connector_b" {
  source               = "../../../modules/aws/twingate-connector"
  layer                = "access"
  region               = var.region
  subnet_id            = var.subnet_id
  security_group_id    = one(module.connector_firewall.rule_targets)
  instance_type        = local.connector_b.type
  root_volume_size     = local.connector_b.root_gb
  remote_network_id    = twingate_remote_network.this.id
  instance             = "b"
  twingate_network     = var.twingate_network
  admin_ssh_public_key = var.admin_ssh_public_key
  reboot_time          = "05:00"
  timezone             = var.timezone

  connector_telemetry = contains(var.connector_telemetry_instances, "b") ? var.connector_telemetry : var.connector_telemetry_previous

  metadata_lock = var.metadata_lock && contains(var.metadata_lock_instances, "b")

  depends_on = [module.connector_firewall]
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
