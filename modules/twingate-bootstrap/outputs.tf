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

    # Log shipping. Every value except the bootstrap token is plain, validated
    # configuration; the token is the only secret-shaped value and it is rendered
    # only while log_shipping is enabled (so the default user_data is unchanged).
    log_shipping                 = var.log_shipping.enabled
    log_shipping_manager_address = var.log_shipping.enabled ? var.log_shipping.manager_address : ""
    log_shipping_manager_port    = tostring(var.log_shipping.manager_port)
    log_shipping_enroll_port     = tostring(var.log_shipping.enroll_port)
    log_shipping_agent_name      = var.log_shipping.enabled ? var.log_shipping.agent_name : ""
    log_shipping_site            = var.log_shipping.enabled ? trimsuffix(var.log_shipping.agent_name, "-connector-${var.instance}") : ""
    log_shipping_agent_group     = var.log_shipping.enabled ? var.log_shipping.agent_group : ""
    log_shipping_key_fingerprint = var.log_shipping.enabled ? var.log_shipping.apt_key_fingerprint : ""
    log_shipping_agent_package   = var.log_shipping.agent_version == "" ? "wazuh-agent" : "wazuh-agent=${var.log_shipping.agent_version}"
    log_shipping_hostboot_config = "cah-${local.name_key}-hostboot"
    log_shipping_bootstrap_token = var.log_shipping.enabled ? var.log_shipping_bootstrap_token : ""
  })

  precondition {
    condition     = !var.node_exporter.enabled || var.connector_telemetry.metrics_port != var.node_exporter.port
    error_message = "node_exporter.port must differ from connector_telemetry.metrics_port (two listeners cannot share a port)."
  }

  precondition {
    condition     = !var.log_shipping.enabled || var.log_shipping_bootstrap_token != ""
    error_message = "log_shipping.enabled needs log_shipping_bootstrap_token (a short-lived, read-only Doppler token for the hostboot config). Without it the first-boot pull cannot run and the agent would never enroll."
  }

  precondition {
    condition     = !var.log_shipping.enabled || endswith(var.log_shipping.agent_name, "-connector-${var.instance}")
    error_message = "log_shipping.agent_name must end in -connector-<instance> for this machine's instance (for example site-tor1-connector-a for instance a)."
  }
}
