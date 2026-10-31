# SPDX-License-Identifier: Apache-2.0
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    twingate = {
      source  = "twingate/twingate"
      version = "~> 5.0"
    }
  }
}

# Credentials come from the environment (Doppler through Spacelift):
# DIGITALOCEAN_TOKEN, TWINGATE_API_TOKEN and TWINGATE_NETWORK. Never a variable.
provider "digitalocean" {}
provider "twingate" {}
