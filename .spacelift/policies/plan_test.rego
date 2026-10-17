# Tests for plan.rego. Run with `opa test .spacelift/policies -v`; CI runs
# them on every pull request through git-your-ship-together's tofu-ci.yml.
#
# The fixtures follow the shape of Spacelift's plan input: a list of
# input.terraform.resource_changes, each with an address, a type and a change
# holding actions and the planned `after` values. Only the fields the policy
# reads are filled in, plus the ones a real plan leaves empty or null.

package spacelift_test

import rego.v1

import data.spacelift

plan(changes) := {"terraform": {"resource_changes": changes}}

change(address, type, actions, after) := {
	"address": address,
	"type": type,
	"change": {"actions": actions, "after": after},
}

create(address, type, after) := change(address, type, ["create"], after)

fw := "module.fw.digitalocean_firewall.this"

# What the firewall module renders for the connector: zero inbound rules.
connector_firewall := create(fw, "digitalocean_firewall", {
	"name": "access-nyc3-connector",
	"tags": ["cah-access"],
	"inbound_rule": [],
	"outbound_rule": [{"protocol": "tcp", "port_range": "443", "destination_addresses": ["0.0.0.0/0", "::/0"]}],
})

# What inbound_from_tag_rules / inbound_from_other_tags can render.
tag_rule := {
	"protocol": "tcp",
	"port_range": "8080",
	"source_tags": ["cah-access"],
	"source_addresses": null,
	"source_droplet_ids": [],
	"source_load_balancer_uids": [],
	"source_kubernetes_ids": [],
}

# The same rule with its source replaced.
with_source(overrides) := object.union(tag_rule, overrides)

firewall_with(rules) := create(fw, "digitalocean_firewall", {"inbound_rule": rules})

denied(changes) := reasons if {
	reasons := spacelift.deny with input as plan(changes)
}

# Clean plans.

test_connector_firewall_with_zero_inbound_passes if {
	count(denied([connector_firewall])) == 0
}

test_tag_scoped_inbound_rule_passes if {
	count(denied([firewall_with([tag_rule])])) == 0
}

test_empty_plan_passes if {
	count(denied([])) == 0
}

# Denials on DigitalOcean.

test_source_address_is_denied if {
	rule := with_source({"source_tags": null, "source_addresses": ["203.0.113.7/32"]})
	reasons := denied([firewall_with([rule])])
	count(reasons) == 1
	some reason in reasons
	contains(reason, fw)
	contains(reason, "tcp/8080")
	contains(reason, "203.0.113.7/32")
}

test_open_to_ipv4_world_is_denied if {
	rule := with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0"]})
	reasons := denied([firewall_with([rule])])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "whole internet")
}

test_open_to_ipv6_world_is_denied if {
	rule := with_source({"source_tags": [], "source_addresses": ["::/0"]})
	reasons := denied([firewall_with([rule])])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "whole internet")
}

# A tag next to an address is still an address: the address opens the port.
test_tag_plus_address_is_denied if {
	rule := with_source({"source_addresses": ["0.0.0.0/0"]})
	count(denied([firewall_with([rule])])) == 1
}

test_droplet_id_source_is_denied if {
	rule := with_source({"source_tags": [], "source_droplet_ids": [12345]})
	count(denied([firewall_with([rule])])) == 1
}

test_load_balancer_source_is_denied if {
	rule := with_source({"source_tags": [], "source_load_balancer_uids": ["lb-1"]})
	count(denied([firewall_with([rule])])) == 1
}

test_kubernetes_source_is_denied if {
	rule := with_source({"source_tags": [], "source_kubernetes_ids": ["k8s-1"]})
	count(denied([firewall_with([rule])])) == 1
}

test_rule_with_no_source_at_all_is_denied if {
	count(denied([firewall_with([{"protocol": "tcp", "port_range": "22"}])])) == 1
}

test_one_bad_rule_among_good_ones_is_denied if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	count(denied([firewall_with([tag_rule, bad])])) == 1
}

test_firewall_update_is_checked_too if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	update := change(fw, "digitalocean_firewall", ["update"], {"inbound_rule": [bad]})
	count(denied([update])) == 1
}

test_firewall_replacement_is_checked_too if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	replace := change(fw, "digitalocean_firewall", ["delete", "create"], {"inbound_rule": [bad]})
	count(denied([replace])) == 1
}

# Empty and null fields do not crash and do not deny.

test_missing_and_null_inbound_rule_do_not_crash if {
	count(denied([
		create(fw, "digitalocean_firewall", {"name": "x"}),
		create("module.fw2.digitalocean_firewall.this", "digitalocean_firewall", {"inbound_rule": null}),
	])) == 0
}

test_delete_with_null_after_is_ignored if {
	gone := change(fw, "digitalocean_firewall", ["delete"], null)
	count(denied([gone])) == 0
}

test_deleting_an_open_rule_is_ignored if {
	bad := with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0"]})
	gone := change(fw, "digitalocean_firewall", ["delete"], {"inbound_rule": [bad]})
	count(denied([gone])) == 0
}

test_no_op_is_ignored if {
	bad := with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0"]})
	same := change(fw, "digitalocean_firewall", ["no-op"], {"inbound_rule": [bad]})
	count(denied([same])) == 0
}

test_plan_without_resource_changes_does_not_crash if {
	reasons := spacelift.deny with input as {"terraform": {}}
	count(reasons) == 0
}

# The escape hatch: exact addresses in the policy file, nothing a plan sets.

test_allowlisted_address_passes if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	reasons := spacelift.deny with input as plan([firewall_with([bad])]) with data.spacelift.inbound_allowlist as {fw}
	count(reasons) == 0
}

test_same_rule_at_another_address_still_fails if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	other := create("module.other.digitalocean_firewall.this", "digitalocean_firewall", {"inbound_rule": [bad]})
	reasons := spacelift.deny with input as plan([other]) with data.spacelift.inbound_allowlist as {fw}
	count(reasons) == 1
}

test_allowlist_is_empty_by_default if {
	count(spacelift.inbound_allowlist) == 0
}

# A plan cannot allowlist itself: a field or label in the input changes nothing.
test_plan_cannot_set_its_own_exception if {
	bad := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})
	doc := object.union(plan([firewall_with([bad])]), {
		"inbound_allowlist": [fw],
		"spacelift": {"stack": {"labels": ["allow-inbound", "cah"]}},
	})
	reasons := spacelift.deny with input as doc
	count(reasons) == 1
}

# Denials on AWS.

ingress_rule_address := "module.aws_fw.aws_vpc_security_group_ingress_rule.web"

sg_cidr := create(ingress_rule_address, "aws_vpc_security_group_ingress_rule", {
	"ip_protocol": "tcp",
	"from_port": 443,
	"to_port": 443,
	"cidr_ipv4": "0.0.0.0/0",
	"cidr_ipv6": null,
	"referenced_security_group_id": null,
})

test_aws_ingress_rule_from_cidr_is_denied if {
	reasons := denied([sg_cidr])
	count(reasons) == 1
	some reason in reasons
	contains(reason, ingress_rule_address)
	contains(reason, "0.0.0.0/0")
}

test_aws_ingress_rule_from_ipv6_cidr_is_denied if {
	rule := create("a.aws_vpc_security_group_ingress_rule.v6", "aws_vpc_security_group_ingress_rule", {"cidr_ipv4": null, "cidr_ipv6": "::/0"})
	count(denied([rule])) == 1
}

# The module's own member rule: a reference to the group, no address.
test_aws_ingress_rule_from_security_group_passes if {
	member := create("module.aws_fw.aws_vpc_security_group_ingress_rule.member[\"tcp-8080\"]", "aws_vpc_security_group_ingress_rule", {
		"ip_protocol": "tcp",
		"from_port": 8080,
		"to_port": 8080,
		"cidr_ipv4": null,
		"cidr_ipv6": null,
		"referenced_security_group_id": "sg-0abc",
	})
	count(denied([member])) == 0
}

test_aws_egress_rule_to_cidr_passes if {
	egress := create("module.aws_fw.aws_vpc_security_group_egress_rule.internet[\"tcp-443\"]", "aws_vpc_security_group_egress_rule", {"cidr_ipv4": "0.0.0.0/0"})
	count(denied([egress])) == 0
}

test_aws_security_group_rule_ingress_from_cidr_is_denied if {
	rule := create("a.aws_security_group_rule.in", "aws_security_group_rule", {"type": "ingress", "cidr_blocks": ["10.0.0.0/8"], "ipv6_cidr_blocks": null})
	count(denied([rule])) == 1
}

test_aws_security_group_rule_ingress_from_ipv6_is_denied if {
	rule := create("a.aws_security_group_rule.in6", "aws_security_group_rule", {"type": "ingress", "cidr_blocks": [], "ipv6_cidr_blocks": ["::/0"]})
	count(denied([rule])) == 1
}

test_aws_security_group_rule_ingress_from_group_passes if {
	rule := create("a.aws_security_group_rule.in", "aws_security_group_rule", {"type": "ingress", "cidr_blocks": null, "ipv6_cidr_blocks": null, "source_security_group_id": "sg-0abc", "self": false})
	count(denied([rule])) == 0
}

test_aws_security_group_rule_egress_to_cidr_passes if {
	rule := create("a.aws_security_group_rule.out", "aws_security_group_rule", {"type": "egress", "cidr_blocks": ["0.0.0.0/0"]})
	count(denied([rule])) == 0
}

test_aws_security_group_inline_ingress_from_cidr_is_denied if {
	sg := create("a.aws_security_group.this", "aws_security_group", {"ingress": [{"from_port": 22, "to_port": 22, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"], "ipv6_cidr_blocks": [], "security_groups": []}], "egress": []})
	reasons := denied([sg])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "a.aws_security_group.this")
}

test_aws_security_group_with_no_rules_passes if {
	sg := create("module.aws_fw.aws_security_group.this", "aws_security_group", {"name": "x", "ingress": null, "egress": null})
	count(denied([sg])) == 0
}

test_aws_allowlisted_address_passes if {
	reasons := spacelift.deny with input as plan([sg_cidr]) with data.spacelift.inbound_allowlist as {ingress_rule_address}
	count(reasons) == 0
}

# IPv6 stays closed.

droplet(ipv6) := create("module.connector.digitalocean_droplet.this", "digitalocean_droplet", {"name": "c", "ipv6": ipv6})

test_droplet_with_ipv6_is_denied if {
	reasons := denied([droplet(true)])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "module.connector.digitalocean_droplet.this")
	contains(reason, "ipv6")
}

test_droplet_without_ipv6_passes if {
	count(denied([droplet(false), create("d.digitalocean_droplet.x", "digitalocean_droplet", {"name": "x"})])) == 0
}

test_aws_vpc_with_generated_ipv6_is_denied if {
	vpc := create("module.vpc.aws_vpc.this", "aws_vpc", {"assign_generated_ipv6_cidr_block": true})
	count(denied([vpc])) == 1
}

test_aws_vpc_with_ipv6_pool_is_denied if {
	vpc := create("module.vpc.aws_vpc.this", "aws_vpc", {"assign_generated_ipv6_cidr_block": false, "ipv6_ipam_pool_id": "ipam-pool-1"})
	count(denied([vpc])) == 1
}

test_aws_vpc_without_ipv6_passes if {
	vpc := create("module.vpc.aws_vpc.this", "aws_vpc", {"cidr_block": "10.0.0.0/16", "assign_generated_ipv6_cidr_block": false, "ipv6_cidr_block": null, "ipv6_ipam_pool_id": null})
	count(denied([vpc])) == 0
}

test_aws_subnet_with_ipv6_cidr_is_denied if {
	subnet := create("module.vpc.aws_subnet.this", "aws_subnet", {"ipv6_cidr_block": "2001:db8::/64"})
	count(denied([subnet])) == 1
}

test_aws_subnet_assigning_ipv6_addresses_is_denied if {
	subnet := create("module.vpc.aws_subnet.this", "aws_subnet", {"assign_ipv6_address_on_creation": true})
	count(denied([subnet])) == 1
}

test_aws_subnet_without_ipv6_passes if {
	subnet := create("module.vpc.aws_subnet.this", "aws_subnet", {"cidr_block": "10.0.1.0/24", "ipv6_cidr_block": null, "assign_ipv6_address_on_creation": false})
	count(denied([subnet])) == 0
}

test_aws_instance_with_ipv6_address_count_is_denied if {
	inst := create("module.c.aws_instance.this", "aws_instance", {"ipv6_address_count": 1})
	count(denied([inst])) == 1
}

test_aws_instance_with_zero_ipv6_passes if {
	inst := create("module.c.aws_instance.this", "aws_instance", {"ipv6_address_count": 0})
	count(denied([inst])) == 0
}

# Findings accumulate: two problems in one plan are two reasons.
test_two_problems_are_two_reasons if {
	count(denied([sg_cidr, droplet(true)])) == 2
}
