# The one place site_name is read. It is a telemetry label, so it feeds outputs
# only and never a resource name or tag (tests/test_resource_key.py checks it).
locals {
  site = var.site_name != "" ? var.site_name : format("site-%s", var.region)
}
