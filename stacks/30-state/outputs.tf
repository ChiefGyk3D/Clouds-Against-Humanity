# SPDX-License-Identifier: Apache-2.0
# Each output is null while the flag is off.
output "bucket_name" {
  value = one(module.state_bucket[*].name)
}

output "bucket_region" {
  value = one(module.state_bucket[*].region)
}

output "bucket_endpoint" {
  value = one(module.state_bucket[*].endpoint)
}

output "bucket_acl" {
  value = one(module.state_bucket[*].acl)
}

output "bucket_versioning_enabled" {
  value = one(module.state_bucket[*].versioning_enabled)
}
