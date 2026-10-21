# SPDX-License-Identifier: Apache-2.0
# Stage 3, state bucket (issue #113). UNBUILT: nothing here has been applied, and
# with state_bucket_enabled left at false this stack plans zero resources.
#
# The bucket sits in its own stack rather than next to the workload droplet so
# that the droplet can be destroyed and rebuilt without ever touching the
# versioned state (see docs/stages/03-state-bucket.md).
#
# The flag is a count on the MODULE call, not on the bucket resource: the cost
# gate refuses count and for_each on a costed resource.
module "state_bucket" {
  count = var.state_bucket_enabled ? 1 : 0

  source                  = "../../modules/spaces-bucket"
  layer                   = "cah"
  purpose                 = "state"
  region                  = var.region
  resource_key            = var.resource_key
  noncurrent_version_days = var.noncurrent_version_days

  abort_incomplete_upload_days = var.abort_incomplete_upload_days
}
