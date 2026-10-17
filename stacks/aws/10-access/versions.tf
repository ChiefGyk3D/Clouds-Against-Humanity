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

# No account id, profile, access key or role appears in this code; AWS
# credentials come from the environment at run time (the Spacelift AWS
# integration, once the maintainer's check has passed: see
# docs/stages/aws-access.md). Twingate credentials come from the environment
# (Doppler through Spacelift): TWINGATE_API_TOKEN and TWINGATE_NETWORK.
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = var.project_name
    }
  }
}

provider "twingate" {}
