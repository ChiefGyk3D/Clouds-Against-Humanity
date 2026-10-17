# The part of a Twingate connector that is the same on every cloud: the
# Twingate connector and its tokens, and the cloud-init that hardens the machine
# and installs the connector. Each provider's connector module calls this one,
# so a hardening fix reaches every cloud at once. It creates no cloud resource.

resource "twingate_connector" "this" {
  remote_network_id = var.remote_network_id
  name              = "${var.layer}-${local.name_key}-connector-${var.instance}"
}

resource "twingate_connector_tokens" "this" {
  connector_id = twingate_connector.this.id
}

locals {
  # Names use resource_key when it is set and region otherwise.
  name_key = var.resource_key != "" ? var.resource_key : var.region

  # What the cloud-init gets for the admin key: "<algorithm> <key>" only. A
  # trailing comment is accepted by the variable's validation and dropped here,
  # so user_data is the same whether or not the key carries one.
  admin_key_parts = split(" ", var.admin_ssh_public_key)
  admin_key       = "${local.admin_key_parts[0]} ${local.admin_key_parts[1]}"

  # The weekly connector update runs half an hour after the nightly reboot
  # window opens, so each connector updates only while its sibling is idle.
  reboot_hour   = tonumber(substr(var.reboot_time, 0, 2))
  reboot_minute = tonumber(substr(var.reboot_time, 3, 2))
  update_minute = (local.reboot_minute + 30) % 60
  update_hour   = (local.reboot_hour + floor((local.reboot_minute + 30) / 60)) % 24
}
