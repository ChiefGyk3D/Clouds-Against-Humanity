locals {
  # Names and tags use resource_key when it is set and region otherwise. The
  # region argument of the droplets and modules stays var.region.
  resource_key = var.resource_key != "" ? var.resource_key : var.region

  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
  connector_b = one([for r in local.cost.resources : r if r.name == "connector-b"])

  # Metrics ports the connector firewall admits, each from var.metrics_source_tag
  # only. The node exporter port (when enabled) and the connector metrics port
  # (this rollout's value and the previous one, so a connector that still runs
  # the old port stays reachable during a one-at-a-time rollout). distinct()
  # keeps a repeated port to one rule.
  metrics_ports = distinct(concat(
    var.node_exporter.enabled ? [var.node_exporter.port] : [],
    var.connector_telemetry.metrics_port == null ? [] : [var.connector_telemetry.metrics_port],
    var.connector_telemetry_previous.metrics_port == null ? [] : [var.connector_telemetry_previous.metrics_port],
  ))

  # Empty unless metrics_source_tag is set AND a metrics source is on, so with
  # the defaults the firewall renders exactly what it did before. Tag-sourced
  # only: the firewall module has no input that can admit an address.
  metrics_inbound_rules = var.metrics_source_tag == "" ? [] : [
    for p in local.metrics_ports : {
      protocol   = "tcp"
      port_range = tostring(p)
      tag        = var.metrics_source_tag
    }
  ]

  # Log shipping, per connector: the agent is named <prefix>-connector-<a or b>
  # and is on only for the instances listed. With the default ({}) every field is
  # empty or false, so the bootstrap module renders exactly the user_data it did
  # before (golden hashes in its tests). The bootstrap token is passed on as it
  # is and is rendered only while the feature is on.
  log_shipping_a = {
    enabled             = var.log_shipping.enabled && contains(var.log_shipping_instances, "a")
    manager_address     = var.log_shipping.manager_address
    manager_port        = var.log_shipping.manager_port
    enroll_port         = var.log_shipping.enroll_port
    agent_name          = var.log_shipping.enabled ? "${var.log_shipping.agent_name_prefix}-connector-a" : ""
    agent_group         = var.log_shipping.agent_group
    apt_key_fingerprint = var.log_shipping.apt_key_fingerprint
    agent_version       = var.log_shipping.agent_version
  }
  log_shipping_b = merge(local.log_shipping_a, {
    enabled    = var.log_shipping.enabled && contains(var.log_shipping_instances, "b")
    agent_name = var.log_shipping.enabled ? "${var.log_shipping.agent_name_prefix}-connector-b" : ""
  })
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

# user_data comes from modules/twingate-bootstrap: a change to its cloud-init replaces the droplet. A push that changes only modules/ starts no run here until the stack has additional_project_globs (#326), so a stack-root change like this one is how the run starts.
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

  node_exporter = { enabled = var.node_exporter.enabled && contains(var.node_exporter_instances, "a"), port = var.node_exporter.port }

  log_shipping                 = local.log_shipping_a
  log_shipping_bootstrap_token = var.log_shipping_bootstrap_token

  host_firewall             = var.host_firewall && contains(var.host_firewall_instances, "a")
  host_firewall_ssh_sources = var.host_firewall_ssh_sources

  # The outbound rules must exist before the droplet boots and starts to install.
  depends_on = [module.connector_firewall]
}

# user_data comes from modules/twingate-bootstrap: a change to its cloud-init replaces the droplet. A push that changes only modules/ starts no run here until the stack has additional_project_globs (#326), so a stack-root change like this one is how the run starts.
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

  node_exporter = { enabled = var.node_exporter.enabled && contains(var.node_exporter_instances, "b"), port = var.node_exporter.port }

  log_shipping                 = local.log_shipping_b
  log_shipping_bootstrap_token = var.log_shipping_bootstrap_token

  host_firewall             = var.host_firewall && contains(var.host_firewall_instances, "b")
  host_firewall_ssh_sources = var.host_firewall_ssh_sources

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
  # The metrics ports (issue #99): the node exporter and the connector's own
  # metrics endpoint, admitted from the telemetry tag only, never an address.
  # Empty by default.
  inbound_from_other_tags = local.metrics_inbound_rules
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
