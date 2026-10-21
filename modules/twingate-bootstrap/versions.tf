terraform {
  required_version = ">= 1.8"
  required_providers {
    twingate = {
      source  = "twingate/twingate"
      version = "~> 5.0"
    }
  }
}
