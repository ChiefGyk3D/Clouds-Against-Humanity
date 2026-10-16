variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline firewall tag. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json."
}

variable "remote_network_id" {
  type        = string
  description = "Twingate remote network (site) shared by every connector of the stack."
}

variable "ssh_key_fingerprint" {
  type        = string
  description = "Fingerprint of the stack's admin SSH key. SSH is reachable only through Twingate."
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
  description = "Public key (type and key, no comment) for the cah-admin user. Key-only access; no password exists."
}

variable "reboot_time" {
  type        = string
  description = "HH:MM (America/New_York, the droplet's local time) when unattended-upgrades may reboot this droplet. Give each connector a different time so they never reboot together."
}
