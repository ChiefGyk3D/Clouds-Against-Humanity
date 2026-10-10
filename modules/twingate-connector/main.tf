resource "twingate_connector" "this" {
  remote_network_id = var.remote_network_id
  name              = "${var.layer}-${var.region}-connector-${var.instance}"
}

resource "twingate_connector_tokens" "this" {
  connector_id = twingate_connector.this.id
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
  })
}
