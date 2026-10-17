mock_provider "digitalocean" {}

run "defaults_are_a_single_region_deny_all_foundation" {
  command = plan
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-tor1"
    error_message = "Baseline tag must be cah-baseline-<region>."
  }
  assert {
    condition     = module.baseline_firewall.inbound_rule_count == 0
    error_message = "Foundation must ship a firewall with zero inbound rules."
  }
  assert {
    condition     = output.baseline_tag == "cah-baseline-tor1"
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

run "baseline_firewall_has_no_tag_scoped_rules_in_either_direction" {
  command = plan
  assert {
    condition     = module.baseline_firewall.inbound_rule_count == 0 && module.baseline_firewall.outbound_rule_count == 5
    error_message = "The baseline firewall must keep zero inbound rules and exactly its five default outbound rules."
  }
  assert {
    condition     = length(module.baseline_firewall.outbound_tag_rules) == 0 && length(module.baseline_firewall.inbound_rules) == 0
    error_message = "The baseline firewall must not carry any tag-scoped rule; that is the connector firewall's job."
  }
}

# --- golden names ------------------------------------------------------------
# These are the names the live stack has today. They are asserted with the
# defaults, so a change that would rename a live object fails here.

run "golden_names_with_defaults" {
  command = plan
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-tor1"
    error_message = "The baseline tag name changed."
  }
  assert {
    condition     = module.vpc.name == "foundation-tor1-vpc"
    error_message = "The VPC name changed."
  }
  assert {
    condition     = module.baseline_firewall.name == "foundation-tor1-baseline"
    error_message = "The baseline firewall name changed."
  }
  assert {
    condition     = digitalocean_project.this.name == "clouds-against-humanity"
    error_message = "The project name changed."
  }
  assert {
    condition     = module.vpc.ip_range == "10.78.0.0/24"
    error_message = "The VPC range changed."
  }
  assert {
    condition     = output.region == "tor1" && output.baseline_tag == "cah-baseline-tor1"
    error_message = "The outputs stack 10 reads changed."
  }
}

# --- resource_key and site_name ---------------------------------------------

run "an_empty_resource_key_means_the_region" {
  command = plan
  variables {
    resource_key = ""
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-tor1" && module.vpc.name == "foundation-tor1-vpc" && module.baseline_firewall.name == "foundation-tor1-baseline"
    error_message = "An empty resource_key must leave every name as it is today."
  }
}

run "resource_key_names_everything_and_the_region_stays_the_region" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-tor1-b" && module.vpc.name == "foundation-tor1-b-vpc" && module.baseline_firewall.name == "foundation-tor1-b-baseline"
    error_message = "A resource_key must replace the region in the tag, VPC and firewall names."
  }
  assert {
    condition     = output.region == "tor1"
    error_message = "The region output is the real region, never the key."
  }
  assert {
    condition     = length(regexall("region\\s*=\\s*var.region", file("${path.module}/main.tf"))) == 2
    error_message = "Both modules must still receive the real region for their region argument."
  }
}

run "site_name_changes_no_name" {
  command = plan
  variables {
    site_name = "site-tor1"
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-tor1" && module.vpc.name == "foundation-tor1-vpc" && module.baseline_firewall.name == "foundation-tor1-baseline"
    error_message = "site_name is a telemetry label and must change no name."
  }
}

run "no_source_file_uses_site_name" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/main.tf"), "site_name") && !strcontains(file("${path.module}/outputs.tf"), "site_name")
    error_message = "site_name must not appear in main.tf or outputs.tf: it is for telemetry labels only."
  }
}

run "resource_key_rejects_uppercase" {
  command = plan
  variables {
    resource_key = "Tor1"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_a_leading_digit" {
  command = plan
  variables {
    resource_key = "1tor"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_one_character" {
  command = plan
  variables {
    resource_key = "a"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_25_characters" {
  command = plan
  variables {
    resource_key = "abcdefghijklmnopqrstuvwxy"
  }
  expect_failures = [var.resource_key]
}

run "resource_key_rejects_an_underscore" {
  command = plan
  variables {
    resource_key = "tor_1"
  }
  expect_failures = [var.resource_key]
}

run "site_name_rejects_uppercase" {
  command = plan
  variables {
    site_name = "Site-Tor1"
  }
  expect_failures = [var.site_name]
}

run "site_name_rejects_25_characters" {
  command = plan
  variables {
    site_name = "abcdefghijklmnopqrstuvwxy"
  }
  expect_failures = [var.site_name]
}

run "site_name_accepts_the_empty_sentinel_and_a_valid_name" {
  command = plan
  variables {
    site_name = ""
  }
  assert {
    condition     = output.region == "tor1"
    error_message = "An empty site_name must be accepted."
  }
}

# --- region ------------------------------------------------------------------

run "region_accepts_other_digitalocean_slugs" {
  command = plan
  variables {
    region = "sfo3"
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-sfo3"
    error_message = "A valid slug must be accepted and flow into the name."
  }
}

run "region_rejects_uppercase" {
  command = plan
  variables {
    region = "Tor1"
  }
  expect_failures = [var.region]
}

run "region_rejects_a_city_name" {
  command = plan
  variables {
    region = "toronto"
  }
  expect_failures = [var.region]
}

run "region_rejects_no_digit" {
  command = plan
  variables {
    region = "tor"
  }
  expect_failures = [var.region]
}

run "region_rejects_two_digits" {
  command = plan
  variables {
    region = "tor12"
  }
  expect_failures = [var.region]
}

run "region_rejects_empty" {
  command = plan
  variables {
    region = ""
  }
  expect_failures = [var.region]
}

run "region_rejects_a_newline" {
  command = plan
  variables {
    region = "tor1\n"
  }
  expect_failures = [var.region]
}

# --- vpc_ip_range ------------------------------------------------------------

run "vpc_range_accepts_the_slash_16_and_slash_28_limits" {
  command = plan
  variables {
    vpc_ip_range = "10.99.0.0/16"
  }
  assert {
    condition     = module.vpc.ip_range == "10.99.0.0/16"
    error_message = "A /16 must be accepted."
  }
}

run "vpc_range_accepts_a_slash_28" {
  command = plan
  variables {
    vpc_ip_range = "192.168.4.16/28"
  }
  assert {
    condition     = module.vpc.ip_range == "192.168.4.16/28"
    error_message = "A /28 network address must be accepted."
  }
}

run "vpc_range_rejects_a_public_range" {
  command = plan
  variables {
    vpc_ip_range = "8.8.8.0/24"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_documentation_range" {
  command = plan
  variables {
    vpc_ip_range = "192.0.2.0/24"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_host_address_not_the_network" {
  command = plan
  variables {
    vpc_ip_range = "10.78.0.5/24"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_slash_8" {
  command = plan
  variables {
    vpc_ip_range = "10.0.0.0/8"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_slash_15" {
  command = plan
  variables {
    vpc_ip_range = "10.78.0.0/15"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_slash_29" {
  command = plan
  variables {
    vpc_ip_range = "10.78.0.0/29"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_a_malformed_range" {
  command = plan
  variables {
    vpc_ip_range = "not-a-cidr"
  }
  expect_failures = [var.vpc_ip_range]
}

run "vpc_range_rejects_ipv6" {
  command = plan
  variables {
    vpc_ip_range = "fd00::/64"
  }
  expect_failures = [var.vpc_ip_range]
}

# --- reserved_ranges (overlap) -----------------------------------------------
# The VPC range in these runs is the default 10.78.0.0/24.

run "no_reserved_ranges_is_fine" {
  command = plan
  variables {
    reserved_ranges = []
  }
  assert {
    condition     = module.vpc.ip_range == "10.78.0.0/24"
    error_message = "An empty reserved_ranges list must plan."
  }
}

run "a_disjoint_reserved_range_is_fine" {
  command = plan
  variables {
    reserved_ranges = ["10.50.0.0/16", "192.168.0.0/16"]
  }
  assert {
    condition     = module.vpc.ip_range == "10.78.0.0/24"
    error_message = "Disjoint ranges must plan."
  }
}

run "an_adjacent_range_after_is_fine" {
  command = plan
  variables {
    reserved_ranges = ["10.78.1.0/24"]
  }
  assert {
    condition     = module.vpc.ip_range == "10.78.0.0/24"
    error_message = "A range that starts right after the VPC range does not overlap it."
  }
}

run "an_adjacent_range_before_is_fine" {
  command = plan
  variables {
    reserved_ranges = ["10.77.255.0/24"]
  }
  assert {
    condition     = module.vpc.ip_range == "10.78.0.0/24"
    error_message = "A range that ends right before the VPC range does not overlap it."
  }
}

run "an_equal_range_overlaps" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.0/24"]
  }
  expect_failures = [digitalocean_project.this]
}

run "a_reserved_range_containing_the_vpc_range_overlaps" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.0/16"]
  }
  expect_failures = [digitalocean_project.this]
}

run "a_reserved_range_inside_the_vpc_range_overlaps" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.128/25"]
  }
  expect_failures = [digitalocean_project.this]
}

run "sharing_only_the_last_address_overlaps" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.255/32"]
  }
  expect_failures = [digitalocean_project.this]
}

run "sharing_only_the_first_address_overlaps" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.0/32"]
  }
  expect_failures = [digitalocean_project.this]
}

run "the_overlap_is_found_in_any_entry_not_just_the_first" {
  command = plan
  variables {
    reserved_ranges = ["10.50.0.0/16", "172.16.0.0/12", "10.78.0.64/26"]
  }
  expect_failures = [digitalocean_project.this]
}

run "overlap_is_checked_against_a_changed_vpc_range" {
  command = plan
  variables {
    vpc_ip_range    = "172.20.0.0/20"
    reserved_ranges = ["172.16.0.0/12"]
  }
  expect_failures = [digitalocean_project.this]
}

run "a_non_canonical_reserved_range_is_still_compared_by_its_network" {
  command = plan
  variables {
    reserved_ranges = ["10.78.0.77/24"]
  }
  expect_failures = [digitalocean_project.this]
}

run "a_reserved_range_must_be_a_cidr" {
  command = plan
  variables {
    reserved_ranges = ["10.50.0.0/16", "nonsense"]
  }
  expect_failures = [var.reserved_ranges]
}

run "a_reserved_range_must_not_be_a_bare_address" {
  command = plan
  variables {
    reserved_ranges = ["10.50.0.1"]
  }
  expect_failures = [var.reserved_ranges]
}

run "reserved_ranges_are_sensitive_and_in_no_output" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/outputs.tf"), "reserved_ranges")
    error_message = "reserved_ranges identify the owner's network and must not be an output."
  }
}
