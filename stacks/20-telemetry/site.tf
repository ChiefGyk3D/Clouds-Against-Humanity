# The one place site_name is read. It is a telemetry label, so it feeds outputs
# only and never a resource name or tag (tests/test_resource_key.py checks it).
locals {
  site = var.site_name != "" ? var.site_name : format("site-%s", var.region)

  # Labels of the additional sites (var.sites), keyed by each site's resource_key.
  # Not private: no address and no network id.
  extra_site_labels = {
    for k, v in nonsensitive(var.sites) : k => {
      site   = v.site_name != "" ? v.site_name : format("site-%s", k)
      region = v.region != "" ? v.region : var.region
    }
  }
}
