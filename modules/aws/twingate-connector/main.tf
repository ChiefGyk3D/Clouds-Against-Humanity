locals {
  # Graviton families put a "g" after the generation digit: t4g, m7g, c7gn.
  graviton = can(regex("^[a-z]+[0-9]+g[a-z]*\\.", var.instance_type))
  # CPU credits exist only on the T families, and EC2 rejects the block elsewhere.
  burstable = can(regex("^t[0-9]", var.instance_type))
}

# The cloud-neutral part (Twingate connector, tokens, cloud-init) lives in the
# bootstrap module so every provider shares one copy of the hardening.
module "bootstrap" {
  source = "../../twingate-bootstrap"

  layer                = var.layer
  region               = var.region
  instance             = var.instance
  remote_network_id    = var.remote_network_id
  twingate_network     = var.twingate_network
  admin_ssh_public_key = var.admin_ssh_public_key
  reboot_time          = var.reboot_time
  timezone             = var.timezone
  connector_telemetry  = var.connector_telemetry
  metadata_lock        = var.metadata_lock

  host_firewall             = var.host_firewall
  host_firewall_ssh_sources = var.host_firewall_ssh_sources
}

# Ubuntu 24.04 LTS, from the parameter Canonical publishes in every region's
# public SSM Parameter Store namespace. Chosen over a name-filtered
# data "aws_ami" lookup because there is no owner account number to hard-code,
# no wildcard name that could match a look-alike image, and the path states
# release, architecture and disk type in plain words. The cost is one extra
# permission for the role that plans this stack (ssm:GetParameter on that
# public path); the AMI lookup would instead need ec2:DescribeImages.
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/${var.architecture}/hvm/ebs-gp3/ami-id"

  # A precondition rather than a cross-variable validation: it works on the
  # OpenTofu 1.8 this repository requires, and it fails at plan time before any
  # instance is planned. An arm image on an x86 type (or the reverse) would pass
  # every other check and be refused by EC2 at launch.
  lifecycle {
    precondition {
      condition     = local.graviton == (var.architecture == "arm64")
      error_message = "architecture ${var.architecture} does not match instance_type ${var.instance_type}: Graviton types (t4g, m7g, ...) need arm64, everything else amd64."
    }
  }
}

# ignore_changes = [ami] below hides routine Canonical image updates, but it
# would also hide a deliberate switch of architecture (arm64 to amd64) and keep
# the old image on the new instance type. This value changes only when the
# architecture input does, and replace_triggered_by turns that into a
# replacement. (OpenTofu 1.8 supports both. The replacement itself is
# UNVERIFIED until an apply: mocks show the wiring, not the action.)
resource "terraform_data" "architecture" {
  input = var.architecture
}

resource "aws_instance" "connector" {
  # An AMI id is public, so the non-sensitive attribute is used. Plain `value`
  # would mark the whole instance's ami as sensitive in every plan.
  ami           = data.aws_ssm_parameter.ubuntu.insecure_value
  instance_type = var.instance_type
  subnet_id     = var.subnet_id

  vpc_security_group_ids = [var.security_group_id]

  # The only public-facing setting. The address is what lets the connector
  # reach Twingate and the package mirrors without a NAT gateway (which alone
  # would cost more than this whole stack). It is NOT a way in: the security
  # group has no inbound rule from the internet, and the cost gate prices this
  # address (it is the largest line after the instance).
  associate_public_ip_address = true
  ipv6_address_count          = 0

  # The boot data holds the connector tokens. It is the bootstrap's output,
  # passed on unmodified and never re-exported. A changed cloud-init only runs
  # on a first boot, so a change replaces the instance instead of leaving it
  # silently out of date.
  user_data                   = module.bootstrap.user_data
  user_data_replace_on_change = true

  # IMDSv2 only: a session token is required, and a hop limit of 1 keeps the
  # token response from crossing a container or proxy hop. It does not stop a
  # process already on the instance from reading the boot data (see threat T5).
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  # The root disk is set explicitly because the cost gate refuses an instance
  # whose disk size it would have to guess: var.root_volume_size is the number
  # it prices. gp3 at the baseline iops and throughput (3000 and 125, written
  # out so they are known at plan time and the gate sees the unpriced-extra
  # check pass).
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    iops                  = 3000
    throughput            = 125
    encrypted             = true
    delete_on_termination = true
  }

  # T-family instances launch in "unlimited" CPU-credit mode when nothing is
  # said, and surplus credits are billed on top of the hourly price, which would
  # break the fixed figure. "standard" caps the instance at its earned credits.
  # The cost gate refuses a T-family plan that does not state this.
  dynamic "credit_specification" {
    for_each = local.burstable ? [1] : []
    content {
      cpu_credits = "standard"
    }
  }

  # Detailed monitoring is a per-instance charge the gate does not price.
  monitoring = false

  # Deliberately absent, both decisions:
  #  - iam_instance_profile: the connector never calls AWS, so it gets no
  #    identity at all. The safest permission is the one not granted.
  #  - key_name: no AWS key pair. cloud-init installs admin_ssh_public_key for
  #    the cah-admin user, and SSH is reachable only through Twingate.

  # A newer Canonical image would otherwise replace a running connector (and
  # its public address) on the next plan. The image is chosen at creation;
  # security updates arrive through unattended-upgrades, not through a new AMI.
  lifecycle {
    ignore_changes       = [ami]
    replace_triggered_by = [terraform_data.architecture]
  }

  tags = { Name = module.bootstrap.name }
}
