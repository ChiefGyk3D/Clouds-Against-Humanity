# The cloud-neutral part (Twingate connector, tokens, cloud-init) lives in the
# bootstrap module so every provider shares one copy of the hardening.
module "bootstrap" {
  source = "../twingate-bootstrap"

  layer                = var.layer
  region               = var.region
  resource_key         = var.resource_key
  instance             = var.instance
  remote_network_id    = var.remote_network_id
  twingate_network     = var.twingate_network
  admin_ssh_public_key = var.admin_ssh_public_key
  reboot_time          = var.reboot_time
  timezone             = var.timezone
  connector_telemetry  = var.connector_telemetry
  metadata_lock        = var.metadata_lock
  node_exporter        = var.node_exporter

  host_firewall             = var.host_firewall
  host_firewall_ssh_sources = var.host_firewall_ssh_sources
}

# These resources used to live directly in this module. Moving them into the
# bootstrap module changes their addresses, and without these blocks the next
# plan would destroy and recreate the connector tokens. With them, state is
# renamed in place and the plan shows no change.
moved {
  from = twingate_connector.this
  to   = module.bootstrap.twingate_connector.this
}

moved {
  from = twingate_connector_tokens.this
  to   = module.bootstrap.twingate_connector_tokens.this
}

resource "digitalocean_droplet" "connector" {
  name       = module.bootstrap.name
  region     = var.region
  size       = var.size
  image      = "ubuntu-24-04-x64"
  vpc_uuid   = var.vpc_id
  tags       = var.tags
  ssh_keys   = [var.ssh_key_fingerprint]
  ipv6       = false
  backups    = false
  monitoring = true

  user_data = module.bootstrap.user_data
}
