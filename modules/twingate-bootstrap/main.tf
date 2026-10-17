# The part of a Twingate connector that is the same on every cloud: the
# Twingate connector and its tokens, and the cloud-init that hardens the machine
# and installs the connector. Each provider's connector module calls this one,
# so a hardening fix reaches every cloud at once. It creates no cloud resource.

resource "twingate_connector" "this" {
  remote_network_id = var.remote_network_id
  name              = "${var.layer}-${local.name_key}-connector-${var.instance}"

  # Provider-side, not in user_data. Unset it is null, which the provider treats
  # as "not configured": the resource config is then exactly what it was before
  # this setting existed, so the default plan cannot differ. Set to true or
  # false it is sent.
  status_updates_enabled = var.connector_telemetry.status_updates_enabled
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

  # Extra lines for /etc/twingate/connector.conf, already indented for the
  # cloud-init block scalar and each ending in a newline. With the default
  # connector_telemetry every list is empty, so this is "" and user_data is
  # byte-identical to before this setting existed (golden hashes in the tests).
  telemetry_conf_lines = concat(
    var.connector_telemetry.log_level == null ? [] : ["TWINGATE_LOG_LEVEL=${var.connector_telemetry.log_level}"],
    var.connector_telemetry.connection_logs ? ["TWINGATE_LOG_ANALYTICS=v3"] : [],
    var.connector_telemetry.metrics_port == null ? [] : ["TWINGATE_METRICS_PORT=${var.connector_telemetry.metrics_port}"],
    [for k in sort(keys(var.connector_telemetry.labels)) : "TWINGATE_LABEL_${k}=${var.connector_telemetry.labels[k]}"],
  )
  telemetry_conf = join("", [for l in local.telemetry_conf_lines : "      ${l}\n"])
}
