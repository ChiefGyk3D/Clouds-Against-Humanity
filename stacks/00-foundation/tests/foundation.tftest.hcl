mock_provider "digitalocean" {}

run "defaults_are_a_single_region_deny_all_foundation" {
  command = plan
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-nyc3"
    error_message = "Baseline tag must be cah-baseline-<region>."
  }
  assert {
    condition     = module.baseline_firewall.inbound_rule_count == 0
    error_message = "Foundation must ship a firewall with zero inbound rules."
  }
  assert {
    condition     = output.baseline_tag == "cah-baseline-nyc3"
    error_message = "The baseline tag must be exported for the access stack."
  }
}

run "region_flows_into_names" {
  command = plan
  variables {
    region = "fra1"
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-fra1"
    error_message = "Changing region must change the tag name."
  }
}

run "foundation_declares_no_costed_resources" {
  command = plan
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 0
    error_message = "Stage 0 must cost nothing."
  }
}
