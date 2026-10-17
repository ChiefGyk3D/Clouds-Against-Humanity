terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    twingate = {
      source  = "twingate/twingate"
      version = "~> 3.0"
    }
  }
}
