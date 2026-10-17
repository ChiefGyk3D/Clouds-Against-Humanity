output "vpc_id" {
  value = module.vpc.id
}

output "vpc_ip_range" {
  value = module.vpc.ip_range
}

output "subnet_id" {
  value = module.vpc.subnet_id
}

output "baseline_security_group_id" {
  value = module.baseline_firewall.id
}

output "region" {
  value = var.region
}
