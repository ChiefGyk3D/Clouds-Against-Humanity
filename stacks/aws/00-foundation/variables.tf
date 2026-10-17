variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region name. The price table (docs/cost-prices/aws.json) was recorded for us-east-1; another region needs its own check."

  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]$", var.region))
    error_message = "region must look like us-east-1."
  }
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.78.0.0/24"
  description = "Private CIDR. Must not overlap any homelab range (confirmed in the stage guide before apply)."
}

variable "availability_zone" {
  type        = string
  default     = null
  description = "Availability zone of the one subnet (for example us-east-1a). Null lets AWS choose."
}

variable "project_name" {
  type        = string
  default     = "clouds-against-humanity"
  description = "Value of the Project tag that every AWS resource of the stack receives."
}
