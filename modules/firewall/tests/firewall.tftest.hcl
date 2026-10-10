mock_provider "digitalocean" {}

variables {
  layer   = "foundation"
  region  = "nyc3"
  purpose = "baseline"
  tag     = "cah-baseline-nyc3"
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
    condition     = digitalocean_firewall.this.name == "foundation-nyc3-baseline"
    error_message = "Name must be <layer>-<region>-<purpose>."
  }
  assert {
    condition     = contains(digitalocean_firewall.this.tags, "cah-baseline-nyc3")
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
    condition     = jsonencode(output.inbound_rules) == jsonencode(sort(["tcp/22/cah-baseline-nyc3", "udp/9999/cah-baseline-nyc3"]))
    error_message = "Each inbound rule must be sourced from this firewall's own tag and nothing else."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.inbound_rule :
      length(coalesce(r.source_addresses, [])) == 0 && length(coalesce(r.source_droplet_ids, [])) == 0 && length(coalesce(r.source_load_balancer_uids, [])) == 0 && toset(r.source_tags) == toset(["cah-baseline-nyc3"])
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
    condition     = jsonencode(output.outbound_tag_rules) == jsonencode(sort(["tcp/22/cah-baseline-nyc3", "udp/9999/cah-baseline-nyc3"]))
    error_message = "Each tag-scoped outbound rule must be destined to this firewall's own tag and nothing else."
  }
  assert {
    condition = alltrue([
      for r in digitalocean_firewall.this.outbound_rule :
      length(coalesce(r.destination_tags, [])) == 0 ? true : (length(coalesce(r.destination_addresses, [])) == 0 && length(coalesce(r.destination_droplet_ids, [])) == 0 && length(coalesce(r.destination_load_balancer_uids, [])) == 0 && toset(r.destination_tags) == toset(["cah-baseline-nyc3"]))
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
