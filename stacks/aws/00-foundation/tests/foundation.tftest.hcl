mock_provider "aws" {
  mock_resource "aws_security_group" {
    defaults = {
      id = "sg-00000000000000001"
    }
  }
}

run "defaults_are_a_single_region_deny_all_foundation" {
  command = plan
  assert {
    condition     = module.vpc.name == "foundation-us-east-1-vpc" && module.baseline_firewall.name == "foundation-us-east-1-baseline"
    error_message = "Names must be foundation-<region>-<role>."
  }
  assert {
    condition     = length(module.baseline_firewall.inbound_rules) == 0 && length(module.baseline_firewall.outbound_member_rules) == 0
    error_message = "The baseline firewall must have no inbound rule and no member rule."
  }
  assert {
    condition     = length(module.baseline_firewall.outbound_rules) == 5
    error_message = "The baseline firewall must carry exactly its five default outbound rules."
  }
}

run "region_flows_into_names" {
  command = plan
  variables {
    region = "eu-west-1"
  }
  assert {
    condition     = module.vpc.name == "foundation-eu-west-1-vpc" && output.region == "eu-west-1"
    error_message = "Changing region must change the names and the output."
  }
}

run "a_malformed_region_is_rejected" {
  command = plan
  variables {
    region = "us east 1"
  }
  expect_failures = [var.region]
}

run "nothing_in_the_baseline_admits_the_internet" {
  command = plan
  assert {
    condition     = length(module.baseline_firewall.inbound_rules) == 0 && !strcontains(file("${path.module}/main.tf"), "0.0.0.0/0") && !strcontains(file("${path.module}/main.tf"), "::/0")
    error_message = "Nothing in stack 00 may open inbound access from an address."
  }
}

run "outputs_feed_the_access_stack" {
  command = plan
  assert {
    condition     = output.vpc_ip_range == "10.78.0.0/24" && output.baseline_security_group_id == "sg-00000000000000001"
    error_message = "vpc_ip_range and the baseline security group id must be exported."
  }
  assert {
    condition     = strcontains(file("${path.module}/outputs.tf"), "output \"vpc_id\"") && strcontains(file("${path.module}/outputs.tf"), "output \"subnet_id\"")
    error_message = "vpc_id and subnet_id must be exported for the access stack."
  }
}

run "provider_is_tagged_and_carries_no_account_identity" {
  command = plan
  assert {
    condition     = strcontains(file("${path.module}/versions.tf"), "default_tags") && strcontains(file("${path.module}/versions.tf"), "Project = var.project_name")
    error_message = "The provider must tag every resource with the project."
  }
  assert {
    condition     = alltrue([for f in ["main.tf", "variables.tf", "outputs.tf"] : length(regexall("(?i)(profile|access_key|secret_key|assume_role|allowed_account_ids|shared_credentials|[0-9]{12})", file("${path.module}/${f}"))) == 0])
    error_message = "No account id, profile, key or role may appear in the stack code."
  }
  assert {
    condition     = length(regexall("(?i)(profile|access_key|secret_key|assume_role|allowed_account_ids|shared_credentials|[0-9]{12})", replace(file("${path.module}/versions.tf"), "/#[^\n]*/", ""))) == 0
    error_message = "The provider block must not name a profile, key, role or account (comments excluded)."
  }
}

run "foundation_declares_no_costed_resources" {
  command = plan
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 0
    error_message = "Stage 0 must cost nothing."
  }
}
