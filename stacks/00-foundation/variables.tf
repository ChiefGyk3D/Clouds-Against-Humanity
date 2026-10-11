variable "region" {
  type        = string
  default     = "tor1"
  description = "DigitalOcean region slug."
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.78.0.0/24"
  description = "Private CIDR. Must not overlap any homelab range (confirmed in the stage 0 guide before apply)."
}

variable "project_name" {
  type    = string
  default = "clouds-against-humanity"
}
