output "connector_private_ips" {
  value = {
    a = module.connector_a.private_ip
    b = module.connector_b.private_ip
  }
}

output "connector_security_group_id" {
  value = module.connector_firewall.id

  # The metrics source must be a DIFFERENT group. Naming the connector group
  # itself would admit connector-to-connector metrics, which this stack does not
  # offer. (The firewall module refuses it too; this states it at the stack.)
  precondition {
    condition     = var.metrics_source_security_group_id != module.connector_firewall.id
    error_message = "metrics_source_security_group_id (${var.metrics_source_security_group_id}) is the connector security group itself. Name the scraping machines' group instead."
  }
}
