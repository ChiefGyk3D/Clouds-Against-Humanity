# SPDX-License-Identifier: Apache-2.0
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}
