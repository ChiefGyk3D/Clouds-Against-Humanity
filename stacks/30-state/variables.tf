# SPDX-License-Identifier: Apache-2.0
variable "state_bucket_enabled" {
  type        = bool
  default     = false
  description = "Create the private, versioned Spaces bucket for the daemons' state. Off by default: with it off this stack plans zero resources. Turning it on is a maintainer decision (stage 3 is not approved) and needs the cost gate to price the bucket first; see docs/stages/03-state-bucket.md."
}

variable "region" {
  type        = string
  default     = "tor1"
  description = "DigitalOcean region slug (three lowercase letters and a digit, for example tor1). The bucket is created here. Whether Spaces is offered in the region is not checked."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the bucket NAME (cah-<key>-state). Empty means region. Bucket names are unique per region across all of Spaces, so a taken name needs a key. IMMUTABLE for the life of the bucket: a different name is a different, empty bucket."

  validation {
    condition     = var.resource_key == "" || can(regex("^[a-z][a-z0-9-]{1,23}$", var.resource_key))
    error_message = "resource_key must be empty (meaning region) or 2 to 24 characters: a lowercase letter, then lowercase letters, digits or hyphens."
  }
}

variable "noncurrent_version_days" {
  type        = number
  default     = 90
  description = "Days a replaced or deleted version is kept before it expires. This is the restore window."

  validation {
    condition     = var.noncurrent_version_days == floor(var.noncurrent_version_days) && var.noncurrent_version_days >= 1 && var.noncurrent_version_days <= 3650
    error_message = "noncurrent_version_days must be a whole number of days from 1 to 3650."
  }
}

variable "abort_incomplete_upload_days" {
  type        = number
  default     = 7
  description = "Days after which an unfinished multipart upload is aborted."

  validation {
    condition     = var.abort_incomplete_upload_days == floor(var.abort_incomplete_upload_days) && var.abort_incomplete_upload_days >= 1 && var.abort_incomplete_upload_days <= 365
    error_message = "abort_incomplete_upload_days must be a whole number of days from 1 to 365."
  }
}
