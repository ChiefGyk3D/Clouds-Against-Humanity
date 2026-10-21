# Empty when metrics are off. The addresses are private, so the output is
# sensitive: hidden in plan and run logs, readable with `tofu output -json` by
# someone who may see it. The home generator turns this into the Prometheus
# file_sd target file and the expected-target inventory.
output "scrape_targets" {
  sensitive = true
  value = merge(
    {
      for k, v in local.scrape_pairs : k => {
        site     = local.site
        instance = "${local.site}-connector-${v.instance}"
        address  = var.connector_private_ips[v.instance]
        port     = v.port
        role     = "connector"
      }
    },
    # Additional sites (var.sites): the same shape, each with its own site label.
    {
      for k, v in local.extra_scrape_pairs : k => {
        site     = local.extra_site_labels[v.skey].site
        instance = "${local.extra_site_labels[v.skey].site}-connector-${v.instance}"
        address  = var.sites[v.skey].connector_private_ips[v.instance]
        port     = v.port
        role     = "connector"
      }
    }
  )
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

# One entry per additional site (var.sites): the label and region telemetry
# attaches to it. Empty by default. No private value.
output "extra_site_identities" {
  value = local.extra_site_labels

  # The site label is the identity in every metric: two sites must not resolve
  # to the same one, nor may one equal the default site's label.
  precondition {
    condition     = length(distinct(concat([local.site], [for k, v in local.extra_site_labels : v.site]))) == length(local.extra_site_labels) + 1
    error_message = "Every site label must be distinct: the default site's label (its own setting, or site-<region>) and each sites entry's (its own setting, or site-<key>)."
  }
}
