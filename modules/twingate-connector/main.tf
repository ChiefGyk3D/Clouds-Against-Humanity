resource "twingate_connector" "this" {
  remote_network_id = var.remote_network_id
  name              = "${var.layer}-${var.region}-connector-${var.instance}"
}

resource "twingate_connector_tokens" "this" {
  connector_id = twingate_connector.this.id
}

locals {
  # The weekly connector update runs half an hour after the nightly reboot
  # window opens, so each connector updates only while its sibling is idle.
  reboot_hour   = tonumber(substr(var.reboot_time, 0, 2))
  reboot_minute = tonumber(substr(var.reboot_time, 3, 2))
  update_minute = (local.reboot_minute + 30) % 60
  update_hour   = (local.reboot_hour + floor((local.reboot_minute + 30) / 60)) % 24
}

resource "digitalocean_droplet" "connector" {
  name       = "${var.layer}-${var.region}-connector-${var.instance}"
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
    access_token  = twingate_connector_tokens.this.access_token
    refresh_token = twingate_connector_tokens.this.refresh_token
    network       = var.twingate_network

    admin_ssh_public_key = var.admin_ssh_public_key
    reboot_time          = var.reboot_time
    update_hour          = local.update_hour
    update_minute        = local.update_minute
  })
}
