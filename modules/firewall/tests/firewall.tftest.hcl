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
