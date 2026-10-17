terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# No account id, profile, access key or role appears in this code. The
# credentials arrive from the environment at run time (the Spacelift AWS
# integration, once the maintainer's check has passed: see
# docs/stages/aws-access.md), never from a variable or a file.
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = var.project_name
    }
  }
}
