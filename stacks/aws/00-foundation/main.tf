module "vpc" {
  source            = "../../../modules/aws/vpc"
  layer             = "foundation"
  region            = var.region
  ip_range          = var.vpc_ip_range
  availability_zone = var.availability_zone
}

# Baseline: a security group with no inbound rule at all and only the five
# default outbound ports. No machine of stage 1 wears it (an instance carries
# exactly one group, and the connector's own group is built in the access
# stack); it exists so later stages have the same deny-all starting point
# DigitalOcean's baseline tag gives.
module "baseline_firewall" {
  source  = "../../../modules/aws/firewall"
  layer   = "foundation"
  region  = var.region
  purpose = "baseline"
  vpc_id  = module.vpc.id
}
