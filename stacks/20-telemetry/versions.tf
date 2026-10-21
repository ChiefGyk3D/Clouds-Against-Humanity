terraform {
  required_version = ">= 1.8"
  required_providers {
    twingate = {
      source  = "twingate/twingate"
      version = "~> 5.0"
    }
  }
}

# Credentials come from the environment (Doppler through Spacelift):
# TWINGATE_API_TOKEN and TWINGATE_NETWORK. This stack has no other provider and
# creates nothing in any cloud.
provider "twingate" {}
