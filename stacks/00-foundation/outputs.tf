output "project_id" {
  value = digitalocean_project.this.id
}

output "vpc_id" {
  value = module.vpc.id
}

output "vpc_ip_range" {
  value = module.vpc.ip_range
}

output "baseline_tag" {
  value = digitalocean_tag.baseline.name
}

output "region" {
  value = var.region
}
