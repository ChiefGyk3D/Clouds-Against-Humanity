mock_provider "digitalocean" {}

variables {
  layer   = "foundation"
  region  = "tor1"
  purpose = "baseline"
  tag     = "cah-baseline-tor1"
}

run "denies_all_inbound" {
  command = plan
  assert {
    condition     = length(digitalocean_firewall.this.inbound_rule) == 0
    error_message = "The baseline firewall must have zero inbound rules."
  }
  assert {
    condition     = output.inbound_rule_count == 0
    error_message = "inbound_rule_count output must be 0."
  }
}

run "applies_by_tag_with_convention_name" {
  command = plan
  assert {
    condition     = digitalocean_firewall.this.name == "foundation-tor1-baseline"
    error_message = "Name must be <layer>-<region>-<purpose>."
  }
  assert {
    condition     = contains(digitalocean_firewall.this.tags, "cah-baseline-tor1")
    error_message = "Firewall must attach by the given tag."
  }
}

run "default_outbound_is_the_five_expected_rules" {
  command = plan
  assert {
    condition     = output.outbound_rule_count == 5
    error_message = "Default outbound must be tcp 443/80/53 and udp 53/123 only."
  }
}

run "default_outbound_is_exactly_these_rules" {
  command = plan
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
    ]))
    error_message = "Default outbound must be exactly tcp 443/80/53 and udp 53/123, each to 0.0.0.0/0 and ::/0."
  }
  assert {
    condition = jsonencode(sort([
      for r in digitalocean_firewall.this.outbound_rule :
      "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.destination_addresses)))}"
    ])) == jsonencode(output.outbound_rules)
    error_message = "The outbound_rules output must describe the resource's real rules."
  }
}

run "extra_outbound_is_appended" {
  command = plan
  variables {
    extra_outbound_rules = [{ protocol = "tcp", port_range = "30000-31000" }]
  }
  assert {
    condition     = output.outbound_rule_count == 6
    error_message = "Extra outbound rules must be appended to the defaults."
  }
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
      "tcp/30000-31000/0.0.0.0/0,::/0",
    ]))
    error_message = "Extra rules must be appended with the same any-address destinations."
  }
}

run "inbound_from_tag_renders_only_tag_sourced_rules" {
  command = plan
  variables {
    inbound_from_tag_rules = [
      { protocol = "tcp", port_range = "22" },
      { protocol = "udp", port_range = "9999" },
    ]
  }
  assert {
    condition     = output.inbound_rule_count == 2
    error_message = "Exactly the listed inbound rules must render."
  }
  assert {
    condition     = jsonencode(output.inbound_rules) == jsonencode(sort(["tcp/22/cah-baseline-tor1", "udp/9999/cah-baseline-tor1"]))
    error_message = "Each inbound rule must be sourced from this firewall's own tag and nothing else."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.inbound_rule :
      length(coalesce(r.source_addresses, [])) == 0 && length(coalesce(r.source_droplet_ids, [])) == 0 && length(coalesce(r.source_load_balancer_uids, [])) == 0 && toset(r.source_tags) == toset(["cah-baseline-tor1"])
    ])
    error_message = "Inbound rules must carry source_tags equal to the module tag and no source addresses."
  }
  assert {
    condition     = output.outbound_rule_count == 5
    error_message = "Inbound rules must not change the outbound set."
  }
}

run "an_inbound_rule_with_an_unknown_protocol_is_rejected" {
  command = plan
  variables {
    inbound_from_tag_rules = [{ protocol = "icmp", port_range = "22" }]
  }
  expect_failures = [var.inbound_from_tag_rules]
}

run "an_inbound_rule_with_an_empty_port_range_is_rejected" {
  command = plan
  variables {
    inbound_from_tag_rules = [{ protocol = "tcp", port_range = "" }]
  }
  expect_failures = [var.inbound_from_tag_rules]
}

run "default_has_no_tag_scoped_outbound_rules" {
  command = plan
  assert {
    condition     = length(output.outbound_tag_rules) == 0
    error_message = "No tag-scoped outbound rule may render unless outbound_to_tag_rules lists one."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.outbound_rule :
      length(coalesce(r.destination_tags, [])) == 0
    ])
    error_message = "By default no outbound rule may carry destination_tags."
  }
}

run "outbound_to_tag_renders_only_tag_destined_rules" {
  command = plan
  variables {
    outbound_to_tag_rules = [
      { protocol = "tcp", port_range = "22" },
      { protocol = "udp", port_range = "9999" },
    ]
  }
  assert {
    condition     = output.outbound_rule_count == 7
    error_message = "The five defaults plus exactly the two listed tag rules must render."
  }
  assert {
    condition     = jsonencode(output.outbound_tag_rules) == jsonencode(sort(["tcp/22/cah-baseline-tor1", "udp/9999/cah-baseline-tor1"]))
    error_message = "Each tag-scoped outbound rule must be destined to this firewall's own tag and nothing else."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.outbound_rule :
      length(coalesce(r.destination_tags, [])) == 0 ? true : (length(coalesce(r.destination_addresses, [])) == 0 && length(coalesce(r.destination_droplet_ids, [])) == 0 && length(coalesce(r.destination_load_balancer_uids, [])) == 0 && toset(r.destination_tags) == toset(["cah-baseline-tor1"]))
    ])
    error_message = "Tag-scoped outbound rules must carry destination_tags equal to the module tag and no destination addresses."
  }
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
    ]))
    error_message = "The address-based outbound list must be unchanged by tag-scoped rules."
  }
  assert {
    condition     = output.inbound_rule_count == 0
    error_message = "Outbound tag rules must not add inbound rules."
  }
}

run "an_outbound_tag_rule_with_an_unknown_protocol_is_rejected" {
  command = plan
  variables {
    outbound_to_tag_rules = [{ protocol = "icmp", port_range = "22" }]
  }
  expect_failures = [var.outbound_to_tag_rules]
}

run "an_outbound_tag_rule_with_an_empty_port_range_is_rejected" {
  command = plan
  variables {
    outbound_to_tag_rules = [{ protocol = "tcp", port_range = "" }]
  }
  expect_failures = [var.outbound_to_tag_rules]
}

run "contract_roles_are_the_tag_on_digitalocean" {
  command = plan
  variables {
    purpose                = "connector"
    inbound_from_tag_rules = [{ protocol = "tcp", port_range = "22" }]
    outbound_to_tag_rules  = [{ protocol = "tcp", port_range = "22" }]
  }
  assert {
    condition     = jsonencode(output.rule_targets) == jsonencode(["cah-baseline-tor1"])
    error_message = "rule_targets must be the tag the firewall attaches to."
  }
  assert {
    condition     = jsonencode(output.source_members) == jsonencode(["cah-baseline-tor1"]) && jsonencode(output.destination_members) == jsonencode(["cah-baseline-tor1"])
    error_message = "With member rules, source_members and destination_members must name the tag; address rules must not appear in them."
  }
}

run "contract_members_are_empty_without_member_rules" {
  command = plan
  assert {
    condition     = length(output.source_members) == 0 && length(output.destination_members) == 0
    error_message = "A firewall with only address-based rules has no members."
  }
}

run "resource_key_changes_the_name_not_the_tag" {
  command = plan
  variables {
    resource_key = "tor1-b"
  }
  assert {
    condition     = digitalocean_firewall.this.name == "foundation-tor1-b-baseline"
    error_message = "A resource_key must replace the region in the firewall name."
  }
  assert {
    condition     = contains(digitalocean_firewall.this.tags, "cah-baseline-tor1")
    error_message = "The tag is the caller's; resource_key must not touch it."
  }
}

run "an_empty_resource_key_means_the_region_in_the_firewall_name" {
  command = plan
  variables {
    resource_key = ""
  }
  assert {
    condition     = digitalocean_firewall.this.name == "foundation-tor1-baseline"
    error_message = "An empty resource_key must leave the name as before."
  }
}

run "rejects_a_bad_resource_key" {
  command = plan
  variables {
    resource_key = "x"
  }
  expect_failures = [var.resource_key]
}

# ---- inbound_from_other_tags / outbound_to_other_tags (stage 2 design 4.2) ----

# Golden: the connector firewall exactly as stacks/10-access calls it. The new
# inputs are left at their defaults, so the rendered descriptors must be the
# ones the live stack has today (plan no-op).
run "golden_stack_style_call_is_unchanged_with_default_other_tags" {
  command = plan
  variables {
    layer                  = "access"
    purpose                = "connector"
    tag                    = "cah-connector-tor1"
    inbound_from_tag_rules = [{ protocol = "tcp", port_range = "22" }]
    outbound_to_tag_rules  = [{ protocol = "tcp", port_range = "22" }]
    extra_outbound_rules = [
      { protocol = "tcp", port_range = "30000-31000" },
      { protocol = "udp", port_range = "1-65535" },
    ]
  }
  assert {
    condition     = jsonencode(output.inbound_rules) == jsonencode(["tcp/22/cah-connector-tor1"])
    error_message = "Golden inbound descriptors changed."
  }
  assert {
    condition     = jsonencode(output.outbound_tag_rules) == jsonencode(["tcp/22/cah-connector-tor1"])
    error_message = "Golden outbound tag descriptors changed."
  }
  assert {
    condition = jsonencode(output.outbound_rules) == jsonencode(sort([
      "tcp/443/0.0.0.0/0,::/0",
      "tcp/80/0.0.0.0/0,::/0",
      "tcp/53/0.0.0.0/0,::/0",
      "udp/53/0.0.0.0/0,::/0",
      "udp/123/0.0.0.0/0,::/0",
      "tcp/30000-31000/0.0.0.0/0,::/0",
      "udp/1-65535/0.0.0.0/0,::/0",
    ]))
    error_message = "Golden address outbound descriptors changed."
  }
  assert {
    condition     = output.inbound_rule_count == 1 && output.outbound_rule_count == 8
    error_message = "Golden rule counts changed."
  }
  assert {
    condition     = jsonencode(output.source_members) == jsonencode(["cah-connector-tor1"]) && jsonencode(output.destination_members) == jsonencode(["cah-connector-tor1"])
    error_message = "Golden members changed."
  }
}

run "golden_baseline_call_is_unchanged_with_default_other_tags" {
  command = plan
  assert {
    condition     = output.inbound_rule_count == 0 && output.outbound_rule_count == 5 && length(output.source_members) == 0 && length(output.destination_members) == 0
    error_message = "The baseline firewall must plan exactly as before."
  }
}

run "metrics_style_rule_from_another_tag_is_tag_sourced_with_no_address" {
  command = plan
  variables {
    layer                   = "soc"
    purpose                 = "soc"
    tag                     = "cah-soc-tor1"
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "3000", tag = "cah-connector-tor1" }]
  }
  assert {
    condition     = jsonencode(output.inbound_rules) == jsonencode(["tcp/3000/cah-connector-tor1"])
    error_message = "The rule must be sourced from the other tag."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.inbound_rule :
      length(coalesce(r.source_addresses, [])) == 0 && length(coalesce(r.source_droplet_ids, [])) == 0 && length(coalesce(r.source_load_balancer_uids, [])) == 0 && length(coalesce(r.source_kubernetes_ids, [])) == 0
    ])
    error_message = "No inbound rule may have an address (or any non-tag) source."
  }
  assert {
    condition     = jsonencode(output.source_members) == jsonencode(["cah-connector-tor1"])
    error_message = "source_members must include the other tag."
  }
  assert {
    condition     = jsonencode(output.rule_targets) == jsonencode(["cah-soc-tor1"])
    error_message = "rule_targets must stay the firewall's own tag."
  }
}

run "own_and_other_tag_inbound_rules_coexist" {
  command = plan
  variables {
    inbound_from_tag_rules  = [{ protocol = "tcp", port_range = "22" }]
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "9100", tag = "cah-soc-tor1" }, { protocol = "tcp", port_range = "9100", tag = "team:b_1" }]
  }
  assert {
    condition     = jsonencode(output.inbound_rules) == jsonencode(sort(["tcp/22/cah-baseline-tor1", "tcp/9100/cah-soc-tor1", "tcp/9100/team:b_1"]))
    error_message = "Own-tag and other-tag inbound rules must all render."
  }
  assert {
    condition     = jsonencode(output.source_members) == jsonencode(sort(["cah-baseline-tor1", "cah-soc-tor1", "team:b_1"]))
    error_message = "Members must list every tag."
  }
}

run "outbound_to_other_tags_renders_tag_destined_rules_and_members" {
  command = plan
  variables {
    outbound_to_tag_rules  = [{ protocol = "tcp", port_range = "22" }]
    outbound_to_other_tags = [{ protocol = "tcp", port_range = "3000", tag = "cah-soc-tor1" }]
  }
  assert {
    condition     = jsonencode(output.outbound_tag_rules) == jsonencode(sort(["tcp/22/cah-baseline-tor1", "tcp/3000/cah-soc-tor1"]))
    error_message = "Other-tag outbound rule must render with its destination tag."
  }
  assert {
    condition     = jsonencode(output.destination_members) == jsonencode(sort(["cah-baseline-tor1", "cah-soc-tor1"]))
    error_message = "destination_members must include the other tag."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.outbound_rule :
      length(coalesce(r.destination_tags, [])) == 0 ? true : length(coalesce(r.destination_addresses, [])) == 0
    ])
    error_message = "Tag outbound rules must carry no address."
  }
  assert {
    condition     = output.outbound_rule_count == 7 && length(output.outbound_rules) == 5
    error_message = "Address outbound set must be unchanged."
  }
}

run "other_tag_bad_protocol_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "icmp", port_range = "22", tag = "t" }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "other_tag_port_zero_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "0", tag = "t" }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "other_tag_port_above_range_is_rejected" {
  command = plan
  variables {
    outbound_to_other_tags = [{ protocol = "tcp", port_range = "65536", tag = "t" }]
  }
  expect_failures = [var.outbound_to_other_tags]
}

run "other_tag_descending_range_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "200-100", tag = "t" }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "other_tag_non_numeric_port_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "all", tag = "t" }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "other_tag_empty_tag_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "22", tag = "" }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "other_tag_with_bad_characters_is_rejected" {
  command = plan
  variables {
    outbound_to_other_tags = [{ protocol = "tcp", port_range = "22", tag = "0.0.0.0/0" }]
  }
  expect_failures = [var.outbound_to_other_tags]
}

run "other_tag_over_255_characters_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "22", tag = join("", [for i in range(256) : "a"]) }]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "duplicate_other_tag_entries_are_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [
      { protocol = "tcp", port_range = "22", tag = "t" },
      { protocol = "tcp", port_range = "22", tag = "t" },
    ]
  }
  expect_failures = [var.inbound_from_other_tags]
}

run "same_port_for_different_tags_is_allowed" {
  command = plan
  variables {
    inbound_from_other_tags = [
      { protocol = "tcp", port_range = "22", tag = "a" },
      { protocol = "tcp", port_range = "22", tag = "b" },
    ]
  }
  assert {
    condition     = output.inbound_rule_count == 2
    error_message = "Distinct tags on one port are two rules."
  }
}

run "inbound_other_tag_equal_to_own_tag_is_rejected" {
  command = plan
  variables {
    inbound_from_other_tags = [{ protocol = "tcp", port_range = "22", tag = "cah-baseline-tor1" }]
  }
  expect_failures = [digitalocean_firewall.this]
}

run "outbound_other_tag_equal_to_own_tag_is_rejected" {
  command = plan
  variables {
    outbound_to_other_tags = [{ protocol = "tcp", port_range = "22", tag = "cah-baseline-tor1" }]
  }
  expect_failures = [digitalocean_firewall.this]
}
