output "bucket_name" {
  value       = one(digitalocean_spaces_bucket.this[*].name)
  description = "The bucket name, or null while the module is off."
}

output "region" {
  value       = one(digitalocean_spaces_bucket.this[*].region)
  description = "The bucket region, or null while the module is off."
}

output "endpoint" {
  value       = one(digitalocean_spaces_bucket.this[*].endpoint)
  description = "The S3-compatible endpoint, or null while the module is off."
}

output "bucket_domain_name" {
  value       = one(digitalocean_spaces_bucket.this[*].bucket_domain_name)
  description = "The bucket's domain name, or null while the module is off."
}

output "urn" {
  value       = one(digitalocean_spaces_bucket.this[*].urn)
  description = "The bucket's URN, or null while the module is off."
}

output "access_keys" {
  value       = { for k, v in digitalocean_spaces_key.this : k => v.access_key }
  sensitive   = true
  description = "Access key ids by key name. Sensitive: an id identifies a credential."
}

output "secret_keys" {
  value       = { for k, v in digitalocean_spaces_key.this : k => v.secret_key }
  sensitive   = true
  description = "Secret keys by key name. Sensitive. They are also in OpenTofu state; store them in Doppler and do not print them."
}
