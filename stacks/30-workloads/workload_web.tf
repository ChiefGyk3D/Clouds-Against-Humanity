# SPDX-License-Identifier: Apache-2.0
# Optional workload web ports (issue #437). Empty by default, so nothing here
# exists. Each listed port gets one Twingate resource on the droplet's private
# address, built like the ssh and Portainer resources in main.tf, and one
# firewall allowance from the connector tag; main.tf adds the rules from
# local.workload_web_firewall_rules. Nothing is applied and the stage is not
# approved: the master switch still gates everything.
locals {
  # Empty unless the master switch is on, so the switch off means no resource.
  workload_web_ports = var.workload_enabled ? { for p in var.workload_web_ports : tostring(p) => p } : {}

  workload_web_firewall_rules = [
    for p in var.workload_web_ports : { protocol = "tcp", port_range = tostring(p), tag = var.connector_tag }
  ]
}

resource "twingate_resource" "workload_web" {
  for_each = local.workload_web_ports

  name              = "cah-${local.resource_key}-workload-web-${each.key}"
  address           = module.workload[0].private_ip
  remote_network_id = var.remote_network_id

  access_group {
    group_id = var.admin_group_id
  }

  protocols = {
    allow_icmp = false
    tcp = {
      policy = "RESTRICTED"
      ports  = [each.key]
    }
    udp = {
      policy = "DENY_ALL"
    }
  }
}
