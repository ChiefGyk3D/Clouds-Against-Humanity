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
    metadata_lock        = var.metadata_lock

    host_firewall              = var.host_firewall
    host_firewall_ssh_sources  = join(", ", var.host_firewall_ssh_sources)
    host_firewall_metrics_port = var.connector_telemetry.metrics_port == null ? "" : tostring(var.connector_telemetry.metrics_port)

    node_exporter               = var.node_exporter.enabled
    node_exporter_port          = var.node_exporter.port
    host_firewall_node_exporter = var.node_exporter.enabled ? tostring(var.node_exporter.port) : ""
  })

  precondition {
    condition     = !var.node_exporter.enabled || var.connector_telemetry.metrics_port != var.node_exporter.port
    error_message = "node_exporter.port must differ from connector_telemetry.metrics_port (two listeners cannot share a port)."
  }
}
