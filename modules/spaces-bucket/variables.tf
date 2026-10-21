# SPDX-License-Identifier: Apache-2.0
variable "layer" {
  type        = string
  description = "Stack layer, used in the bucket name (for example state)."

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,15}$", var.layer))
    error_message = "layer must be 2 to 16 lowercase letters or digits, starting with a letter."
  }
}

variable "purpose" {
  type        = string
  default     = "state"
  description = "Last part of the bucket name (<layer>-<region or resource_key>-<purpose>)."

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,15}$", var.purpose))
    error_message = "purpose must be 2 to 16 lowercase letters or digits, starting with a letter."
  }
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug (three lowercase letters and a digit, for example tor1). Whether Spaces is offered in that region is not checked here."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be a DigitalOcean region slug: three lowercase letters and a digit, for example tor1."
  }
}

variable "resource_key" {
  type        = string
  default     = ""
  description = "Key used in the bucket NAME in place of region. Empty means region. IMMUTABLE for the life of a bucket: a different name is a different bucket, and the old one is not copied."

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
