output "name" {
  description = "Name shared by the Twingate connector and the machine: <layer>-<resource_key or region>-connector-<instance>."
  value       = twingate_connector.this.name
}

# This is the only output that carries the connector tokens, so it is
# sensitive. A provider module passes it straight to the machine's boot data
# and never re-exports it.
output "user_data" {
  description = "Rendered cloud-init for the machine. Contains the connector tokens."
  sensitive   = true
  value = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    access_token  = twingate_connector_tokens.this.access_token
    refresh_token = twingate_connector_tokens.this.refresh_token
    network       = var.twingate_network

    admin_ssh_public_key = local.admin_key
    reboot_time          = var.reboot_time
    timezone             = var.timezone
    update_hour          = local.update_hour
    update_minute        = local.update_minute
    telemetry_conf       = local.telemetry_conf
  })
}
