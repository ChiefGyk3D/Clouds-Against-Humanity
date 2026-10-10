terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# The token comes from the DIGITALOCEAN_TOKEN environment variable, injected
# by Spacelift from Doppler. It is never a variable and never written down.
provider "digitalocean" {}
