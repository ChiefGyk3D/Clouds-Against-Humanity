# Empty when metrics are off. The addresses are private, so the output is
# sensitive: hidden in plan and run logs, readable with `tofu output -json` by
# someone who may see it. The home generator turns this into the Prometheus
# file_sd target file and the expected-target inventory.
output "scrape_targets" {
  sensitive = true
  value = {
    for k, v in local.scrape_pairs : k => {
      site     = local.site
      instance = "${local.site}-connector-${v.instance}"
      address  = var.connector_private_ips[v.instance]
      port     = v.port
      role     = "connector"
    }
  }
}

# The identity telemetry attaches to this site. No private value.
output "site_identity" {
  value = {
    site              = local.site
    region            = var.region
    provider          = "digitalocean"
    wazuh_agent_group = var.wazuh_agent_group
    labels            = var.labels
  }
}
