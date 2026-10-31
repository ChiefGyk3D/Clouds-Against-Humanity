output "bucket_name" {
  value       = digitalocean_spaces_bucket.this.name
  description = "The bucket name."
}

output "region" {
  value       = digitalocean_spaces_bucket.this.region
  description = "The bucket region."
}

output "endpoint" {
  value       = digitalocean_spaces_bucket.this.endpoint
  description = "The S3-compatible endpoint."
}

output "bucket_domain_name" {
  value       = digitalocean_spaces_bucket.this.bucket_domain_name
  description = "The bucket's domain name."
}

output "urn" {
  value       = digitalocean_spaces_bucket.this.urn
  description = "The bucket's URN."
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
