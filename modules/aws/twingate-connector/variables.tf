variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "subnet_id" {
  type        = string
  description = "Public subnet the instance launches into. From the vpc module's subnet_id."
}

variable "security_group_id" {
  type        = string
  description = "The one security group attached to the instance's network interface at launch, so there is no unprotected moment. From the firewall module's id (its single rule target). A single string, not a list: security group rules are additive, so any second group a caller added could open inbound access to the public address."

  validation {
    condition     = can(regex("^sg-[0-9a-f]+$", var.security_group_id))
    error_message = "security_group_id must be a security group id (sg-...), not an empty value: an instance with none gets the VPC's default group."
  }
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type. The stack reads it from cost.json (local.<x>.type) so the price and the plan can never disagree."

  validation {
    condition     = can(regex("^[a-z][a-z0-9]*\\.(nano|micro|small|medium|large|[0-9]*xlarge)$", var.instance_type))
    error_message = "instance_type must look like t4g.micro: a family, a dot and a size."
  }
}

variable "architecture" {
  type        = string
  default     = "arm64"
  description = "CPU architecture of the Ubuntu image: arm64 (Graviton types such as t4g) or amd64 (types such as t3). Must match instance_type."

  validation {
    condition     = contains(["arm64", "amd64"], var.architecture)
    error_message = "architecture must be arm64 or amd64."
  }
}

variable "root_volume_size" {
  type        = number
  default     = 8
  description = "Root disk size in GiB (gp3). This number is an input to the cost gate: the AMI's own default is not priced, so the size is always set here. 8 GiB is the smallest the Ubuntu image accepts."

  validation {
    condition     = var.root_volume_size >= 8 && var.root_volume_size <= 64 && var.root_volume_size == floor(var.root_volume_size)
    error_message = "root_volume_size must be a whole number of GiB from 8 to 64."
  }
}

variable "remote_network_id" {
  type        = string
  description = "Twingate remote network (site) shared by every connector of the stack."
}

variable "instance" {
  type        = string
  description = "One lowercase letter or digit that tells this connector from its siblings (a, b)."
}

variable "twingate_network" {
  type        = string
  sensitive   = true
  description = "Bare Twingate network subdomain (acme for acme.twingate.com). Sensitive because the tenant slug identifies the tenant."
}

variable "admin_ssh_public_key" {
  type        = string
  description = "Public key (type and key, no comment) for the cah-admin user. Installed by cloud-init; no AWS key pair is used."
}

variable "reboot_time" {
  type        = string
  description = "HH:MM (in `timezone`, the instance's local time; America/New_York by default) when unattended-upgrades may reboot this instance. Give each connector a different time so they never reboot together."
}

variable "timezone" {
  type        = string
  default     = "America/New_York"
  description = "IANA time zone name of the machine (UTC or Area/Location, for example America/New_York), also the zone reboot_time and the weekly update are read in. Default America/New_York. Passed to the bootstrap module; changing it replaces the instance."

  validation {
    condition     = can(regex("^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$", var.timezone))
    error_message = "timezone must be UTC or an IANA name such as America/New_York (Area/Location, letters, digits and _ + - only, no spaces or line breaks)."
  }
}
