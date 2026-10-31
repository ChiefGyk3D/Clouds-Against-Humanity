variable "enabled" {
  type        = bool
  default     = false
  description = "Master switch. False (the default) plans nothing at all, so merging a call to this module changes no infrastructure. It must stay false until the maintainer approves the Spaces cost (see cost.json in this directory)."
}

variable "name" {
  type        = string
  description = "Bucket name. Unique across all of Spaces in the region. 3 to 63 characters: lowercase letters, digits and hyphens, starting and ending with a letter or digit."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.name))
    error_message = "name must be 3 to 63 characters: lowercase letters, digits and hyphens, starting and ending with a letter or digit."
  }
}

variable "region" {
  type        = string
  description = "Spaces region slug, such as tor1 (three letters and a digit)."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a Spaces region slug: three lowercase letters and a digit, such as tor1."
  }
}

variable "acl" {
  type        = string
  default     = "private"
  description = "Bucket ACL. Only private is accepted: the bucket holds daemon state and must never be listable or readable by the public. The variable exists so that a public value fails loudly instead of being ignored."

  validation {
    condition     = var.acl == "private"
    error_message = "acl must be private. public-read, public-read-write and every other value are refused."
  }
}

variable "noncurrent_version_expiration_days" {
  type        = number
  default     = 90
  description = "Days after which a noncurrent (overwritten or deleted) object version expires. This is how long a restore from a previous version stays possible."

  validation {
    condition     = var.noncurrent_version_expiration_days == floor(var.noncurrent_version_expiration_days) && var.noncurrent_version_expiration_days >= 1 && var.noncurrent_version_expiration_days <= 3650
    error_message = "noncurrent_version_expiration_days must be a whole number from 1 to 3650."
  }
}

variable "create_access_keys" {
  type        = bool
  default     = false
  description = "Create the Spaces access keys named in access_key_names. Off by default: a key's secret lands in OpenTofu state, which the stage 3 design accepts only once state access is restricted; until then create keys by hand and keep them in Doppler. Needs enabled = true as well."
}

variable "access_key_names" {
  type        = list(string)
  default     = []
  description = "Names of the access keys to create, one per daemon. Each key gets readwrite on this one bucket and nothing else. Only used when create_access_keys and enabled are both true."

  validation {
    condition     = alltrue([for n in var.access_key_names : can(regex("^[a-z0-9][a-z0-9-]{0,62}$", n))])
    error_message = "Each access key name must be 1 to 63 characters: lowercase letters, digits and hyphens, starting with a letter or digit."
  }

  validation {
    condition     = length(var.access_key_names) == length(distinct(var.access_key_names))
    error_message = "access_key_names must not repeat a name."
  }
}
