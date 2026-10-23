# SPDX-License-Identifier: Apache-2.0
# Piece 1: a DigitalOcean project of its own, so the whole lab can be found and removed together.
# Flag-off by default: with enabled = false, `tofu plan` creates nothing.
variable "enabled" {
  type    = bool
  default = false
}

variable "name" {
  type    = string
  default = "mail-lab"
}

variable "resources" {
  description = "URNs of the resources to place in the project (filled by the other pieces)."
  type        = list(string)
  default     = []
}

resource "digitalocean_project" "this" {
  count       = var.enabled ? 1 : 0
  name        = var.name
  description = "Mail-in-a-Box learning lab. Destroy when done."
  purpose     = "Just trying out DigitalOcean"
  environment = "Development"
  resources   = var.resources
}

output "project_id" {
  value = try(digitalocean_project.this[0].id, "")
}
