terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    twingate = {
      source  = "twingate/twingate"
      version = "~> 3.0"
    }
  }
}
