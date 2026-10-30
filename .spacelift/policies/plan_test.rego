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

# The same plan, as Spacelift sends it for one stack.
on_stack(id, changes) := object.union(plan(changes), {"spacelift": {"stack": {"id": id, "autodeploy": false}}})

denied_on(id, changes) := reasons if {
	reasons := spacelift.deny with input as on_stack(id, changes)
}

# Clean plans.

# The fixture also has the world-open outbound 443 rule the module renders, so
# it passes only where an outbound entry covers it (issue #253).
test_connector_firewall_with_zero_inbound_passes if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	count(reasons_with_outbound("svc-a", [connector_firewall], allow)) == 0
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
	count(denied_destroy_allowed([replace])) == 1
}

# The inbound checks in isolation: the firewall's destroy is allowlisted for
# the stack, so only the inbound rules can deny. The destroy guard has its own
# tests below.
denied_destroy_allowed(changes) := reasons if {
	reasons := spacelift.deny with input as on_stack("svc-a", changes) with data.spacelift.destroy_allowlist as {"svc-a": [fw]}
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
	count(denied_destroy_allowed([gone])) == 0
}

test_deleting_an_open_rule_is_ignored if {
	bad := with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0"]})
	gone := change(fw, "digitalocean_firewall", ["delete"], {"inbound_rule": [bad]})
	count(denied_destroy_allowed([gone])) == 0
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

# The escape hatch: entries in the policy file keyed by stack id, then address
# or group, each saying what it allows. Nothing a plan sets.

bad_rule := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})

entry(overrides) := object.union(
	{
		"direction": "inbound",
		"protocol": "tcp",
		"ports": ["8080"],
		"sources": ["198.51.100.0/24"],
	},
	overrides,
)

allow_for(stack, key, entries) := {stack: {key: entries}}

reasons_with(id, changes, allowlist) := reasons if {
	reasons := spacelift.deny with input as on_stack(id, changes) with data.spacelift.inbound_allowlist as allowlist
}

test_allowlisted_entry_passes_in_its_stack if {
	allow := allow_for("svc-a", fw, [entry({})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 0
}

# The defect from the stack-per-service note: one module reused in several
# stacks gives the same address in each. An entry covers only its own stack.
test_same_address_in_another_stack_still_fails if {
	allow := allow_for("svc-a", fw, [entry({})])
	count(reasons_with("svc-b", [firewall_with([bad_rule])], allow)) == 1
}

test_same_stack_other_address_still_fails if {
	allow := allow_for("svc-a", fw, [entry({})])
	other := create("module.other.digitalocean_firewall.this", "digitalocean_firewall", {"inbound_rule": [bad_rule]})
	count(reasons_with("svc-a", [other], allow)) == 1
}

test_plan_with_no_stack_id_gets_no_exception if {
	allow := allow_for("svc-a", fw, [entry({})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 0
	reasons := spacelift.deny with input as plan([firewall_with([bad_rule])]) with data.spacelift.inbound_allowlist as allow
	count(reasons) == 1
	empty := spacelift.deny with input as on_stack("", [firewall_with([bad_rule])]) with data.spacelift.inbound_allowlist as {"": {fw: [entry({})]}}
	count(empty) == 1
	nulled := spacelift.deny with input as object.union(plan([firewall_with([bad_rule])]), {"spacelift": {"stack": null}}) with data.spacelift.inbound_allowlist as allow
	count(nulled) == 1
}

# Each field narrows the entry. A mismatch, or a field left out, denies.

test_entry_for_another_port_denies if {
	allow := allow_for("svc-a", fw, [entry({"ports": ["9090"]})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 1
}

test_entry_for_another_protocol_denies if {
	allow := allow_for("svc-a", fw, [entry({"protocol": "udp"})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 1
}

test_entry_for_another_source_denies if {
	allow := allow_for("svc-a", fw, [entry({"sources": ["203.0.113.7/32"]})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 1
}

test_every_source_of_the_rule_must_be_listed if {
	two := with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24", "203.0.113.7/32"]})
	allow := allow_for("svc-a", fw, [entry({})])
	count(reasons_with("svc-a", [firewall_with([two])], allow)) == 1
	both := allow_for("svc-a", fw, [entry({"sources": ["198.51.100.0/24", "203.0.113.7/32"]})])
	count(reasons_with("svc-a", [firewall_with([two])], both)) == 0
}

test_entry_with_another_direction_denies if {
	allow := allow_for("svc-a", fw, [entry({"direction": "outbound"})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 1
}

test_entry_missing_a_field_denies if {
	every field in ["direction", "protocol", "ports", "sources"] {
		partial := object.remove(entry({}), [field])
		count(reasons_with("svc-a", [firewall_with([bad_rule])], allow_for("svc-a", fw, [partial]))) == 1
	}
}

test_entry_with_empty_lists_denies if {
	allow := allow_for("svc-a", fw, [entry({"ports": [], "sources": []})])
	count(reasons_with("svc-a", [firewall_with([bad_rule])], allow)) == 1
}

test_rule_without_a_port_is_never_covered if {
	no_port := object.remove(bad_rule, ["port_range"])
	allow := allow_for("svc-a", fw, [entry({"ports": ["", "?"]})])
	count(reasons_with("svc-a", [firewall_with([no_port])], allow)) == 1
}

# World-open needs both ranges named; one does not cover the other.
test_world_open_entry_must_list_both_ranges if {
	world := with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0", "::/0"]})
	v4 := allow_for("svc-a", fw, [entry({"sources": ["0.0.0.0/0"]})])
	count(reasons_with("svc-a", [firewall_with([world])], v4)) == 1
	both := allow_for("svc-a", fw, [entry({"sources": ["0.0.0.0/0", "::/0"]})])
	count(reasons_with("svc-a", [firewall_with([world])], both)) == 0
}

# A different port on the same firewall is not covered by the first entry.
test_rules_are_judged_one_by_one if {
	second := object.union(bad_rule, {"port_range": "9090"})
	allow := allow_for("svc-a", fw, [entry({})])
	reasons := reasons_with("svc-a", [firewall_with([bad_rule, second])], allow)
	count(reasons) == 1
	some reason in reasons
	contains(reason, "tcp/9090")
	both := allow_for("svc-a", fw, [entry({}), entry({"ports": ["9090"]})])
	count(reasons_with("svc-a", [firewall_with([bad_rule, second])], both)) == 0
}

test_other_kinds_of_source_are_never_covered_by_an_address_entry if {
	with_droplet := object.union(bad_rule, {"source_droplet_ids": [12345]})
	allow := allow_for("svc-a", fw, [entry({})])
	count(reasons_with("svc-a", [firewall_with([with_droplet])], allow)) == 1
}

# A named group covers its addresses, in its stack only.
test_group_covers_its_members_in_its_stack_only if {
	fw2 := "module.edge.digitalocean_firewall.this"
	changes := [firewall_with([bad_rule]), create(fw2, "digitalocean_firewall", {"inbound_rule": [bad_rule]})]
	allow := allow_for("svc-a", "edge-pair", [entry({})])
	groups := {"svc-a": {"edge-pair": [fw, fw2]}}
	in_a := spacelift.deny with input as on_stack("svc-a", changes) with data.spacelift.inbound_allowlist as allow with data.spacelift.address_groups as groups
	count(in_a) == 0
	in_b := spacelift.deny with input as on_stack("svc-b", changes) with data.spacelift.inbound_allowlist as allow with data.spacelift.address_groups as groups
	count(in_b) == 2

	# A third address that is not in the group stays denied.
	third := create("module.third.digitalocean_firewall.this", "digitalocean_firewall", {"inbound_rule": [bad_rule]})
	only_third := spacelift.deny with input as on_stack("svc-a", [third]) with data.spacelift.inbound_allowlist as allow with data.spacelift.address_groups as groups
	count(only_third) == 1
}

test_groups_of_another_stack_do_not_apply if {
	allow := allow_for("svc-a", "edge-pair", [entry({})])
	groups := {"svc-b": {"edge-pair": [fw]}}
	reasons := spacelift.deny with input as on_stack("svc-a", [firewall_with([bad_rule])]) with data.spacelift.inbound_allowlist as allow with data.spacelift.address_groups as groups
	count(reasons) == 1
}

test_allowlists_are_empty_by_default if {
	count(spacelift.inbound_allowlist) == 0
	count(object.keys(spacelift.outbound_allowlist)) == 2
	count(spacelift.address_groups) == 0
	count(spacelift.destroy_allowlist) == 0
	count(spacelift.whole_service_teardown_stacks) == 0
}

# Today's stacks: with the shipped (empty) allowlists their verdicts are the
# ones they had before the keyed allowlists, whatever the stack id says.

current_stacks := ["cah-00-foundation", "cah-10-access", "cah-20-telemetry", "cah-aws-00-foundation", "cah-aws-10-access"]

test_current_stacks_keep_their_verdicts if {
	every id in current_stacks {
		count(denied_on(id, [firewall_with([tag_rule])])) == 0
		count(denied_on(id, [connector_firewall])) == 1
		count(denied_on(id, [firewall_with([bad_rule])])) == 1
		count(denied_on(id, [firewall_with([with_source({"source_tags": [], "source_addresses": ["0.0.0.0/0"]})])])) == 1
		count(denied_on(id, [sg_cidr])) == 1
		count(denied_on(id, [delete_of(fw, "digitalocean_firewall", {"name": "core"})])) == 1
		count(denied_on(id, [delete_of(vpc_addr, "digitalocean_vpc", {"name": "core"})])) == 1
		count(denied_on(id, [delete_of("module.c.digitalocean_droplet.this", "digitalocean_droplet", {"tags": ["cah-access"]})])) == 0
		count(denied_on(id, [droplet(true)])) == 1
	}
}

# Even a whole-service teardown stays denied on today's stacks: none opted in.
test_current_stacks_have_no_whole_service_teardown if {
	every id in current_stacks {
		count(denied_on(id, teardown_changes)) == 1
	}
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
	allow := allow_for("aws-a", ingress_rule_address, [aws_entry({})])
	count(reasons_with("aws-a", [sg_cidr], allow)) == 0
}

aws_entry(overrides) := object.union(
	{
		"direction": "inbound",
		"protocol": "tcp",
		"ports": ["443"],
		"sources": ["0.0.0.0/0"],
	},
	overrides,
)

test_aws_entry_is_keyed_by_stack if {
	allow := allow_for("aws-a", ingress_rule_address, [aws_entry({})])
	count(reasons_with("aws-b", [sg_cidr], allow)) == 1
}

test_aws_entry_is_scoped_by_port_protocol_and_cidr if {
	every overrides in [{"ports": ["80"]}, {"protocol": "udp"}, {"sources": ["10.0.0.0/8"]}, {"direction": "outbound"}] {
		allow := allow_for("aws-a", ingress_rule_address, [aws_entry(overrides)])
		count(reasons_with("aws-a", [sg_cidr], allow)) == 1
	}
}

test_aws_port_range_is_matched_as_text if {
	ranged := create("a.aws_security_group_rule.r", "aws_security_group_rule", {"type": "ingress", "protocol": "tcp", "from_port": 8000, "to_port": 8100, "cidr_blocks": ["10.0.0.0/8"], "ipv6_cidr_blocks": null})
	ok := allow_for("aws-a", "a.aws_security_group_rule.r", [aws_entry({"ports": ["8000-8100"], "sources": ["10.0.0.0/8"]})])
	count(reasons_with("aws-a", [ranged], ok)) == 0
	narrow := allow_for("aws-a", "a.aws_security_group_rule.r", [aws_entry({"ports": ["8000"], "sources": ["10.0.0.0/8"]})])
	count(reasons_with("aws-a", [ranged], narrow)) == 1
}

test_aws_rule_with_unknown_ports_is_never_covered if {
	no_ports := create("a.aws_security_group_rule.r", "aws_security_group_rule", {"type": "ingress", "cidr_blocks": ["10.0.0.0/8"]})
	allow := allow_for("aws-a", "a.aws_security_group_rule.r", [aws_entry({"ports": ["", "null"], "sources": ["10.0.0.0/8"]})])
	count(reasons_with("aws-a", [no_ports], allow)) == 1
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

# Destroy guard. A deleting change carries its old values in `before`.

removal(address, type, actions, before) := {
	"address": address,
	"type": type,
	"change": {"actions": actions, "before": before, "after": null},
}

delete_of(address, type, before) := removal(address, type, ["delete"], before)

vpc_addr := "module.vpc.digitalocean_vpc.this"

test_replace_of_firewall_is_denied if {
	rc := removal(fw, "digitalocean_firewall", ["delete", "create"], {"name": "core"})
	reasons := denied([rc])
	count(reasons) == 1
	some msg in reasons
	contains(msg, fw)
	contains(msg, "destroy_allowlist")
}

test_create_before_destroy_replace_of_firewall_is_denied if {
	rc := removal(fw, "digitalocean_firewall", ["create", "delete"], {"name": "core"})
	count(denied([rc])) == 1
}

test_delete_of_vpc_is_denied if {
	count(denied([delete_of(vpc_addr, "digitalocean_vpc", {"name": "core"})])) == 1
}

test_delete_of_each_protected_type_is_denied if {
	types := {
		"digitalocean_vpc",
		"digitalocean_project",
		"digitalocean_firewall",
		"twingate_remote_network",
		"aws_vpc",
		"aws_security_group",
	}
	every type in types {
		count(denied([delete_of(sprintf("module.m.%s.this", [type]), type, {"name": "x"})])) == 1
	}
}

test_delete_of_droplet_is_allowed if {
	rc := delete_of("module.c.digitalocean_droplet.this", "digitalocean_droplet", {"tags": ["cah-access"]})
	count(denied([rc])) == 0
}

test_replace_of_droplet_is_allowed if {
	rc := removal("module.c.digitalocean_droplet.this", "digitalocean_droplet", ["delete", "create"], {"tags": ["cah-access"]})
	count(denied([rc])) == 0
}

test_delete_of_tag_protected_resource_is_denied if {
	rc := delete_of("module.s.digitalocean_volume.state", "digitalocean_volume", {"tags": ["env", "protected"]})
	count(denied([rc])) == 1
}

test_delete_of_aws_resource_with_protected_tag_key_is_denied if {
	rc := delete_of("module.s.aws_s3_bucket.state", "aws_s3_bucket", {"tags": {"protected": "true"}})
	count(denied([rc])) == 1
}

test_delete_of_untagged_other_resource_is_allowed if {
	rc := delete_of("module.s.digitalocean_volume.scratch", "digitalocean_volume", {"tags": ["env"]})
	count(denied([rc])) == 0
}

test_create_update_and_noop_never_trigger_destroy_guard if {
	every actions in [["create"], ["update"], ["no-op"], ["read"]] {
		rc := removal(vpc_addr, "digitalocean_vpc", actions, {"name": "core", "tags": ["protected"]})
		count(denied([rc])) == 0
	}
}

test_missing_and_null_fields_do_not_crash_destroy_guard if {
	count(denied([{"address": "a.b", "type": "digitalocean_volume", "change": {"actions": ["delete"]}}])) == 0
	count(denied([removal("a.b", "digitalocean_volume", ["delete"], null)])) == 0
	count(denied([removal("a.b", "digitalocean_volume", ["delete"], {"tags": null})])) == 0
	count(denied([{"address": "a.b", "type": "digitalocean_vpc", "change": {"actions": null}}])) == 0
	count(denied([{"address": "a.b", "type": "digitalocean_vpc", "change": null}])) == 0
}

test_allowlisted_address_is_allowed_while_another_is_denied if {
	other := "module.other.digitalocean_vpc.this"
	changes := [
		delete_of(vpc_addr, "digitalocean_vpc", {"name": "a"}),
		delete_of(other, "digitalocean_vpc", {"name": "b"}),
	]
	reasons := spacelift.deny with input as on_stack("svc-a", changes) with data.spacelift.destroy_allowlist as {"svc-a": [vpc_addr]}
	count(reasons) == 1
	some msg in reasons
	contains(msg, other)
}

test_destroy_entry_is_keyed_by_stack if {
	changes := [delete_of(vpc_addr, "digitalocean_vpc", {"name": "a"})]
	allow := {"svc-a": [vpc_addr]}
	in_b := spacelift.deny with input as on_stack("svc-b", changes) with data.spacelift.destroy_allowlist as allow
	count(in_b) == 1
	no_stack := spacelift.deny with input as plan(changes) with data.spacelift.destroy_allowlist as allow
	count(no_stack) == 1
}

test_destroy_group_covers_members_in_its_stack_only if {
	other := "module.other.digitalocean_vpc.this"
	changes := [delete_of(vpc_addr, "digitalocean_vpc", {"name": "a"}), delete_of(other, "digitalocean_vpc", {"name": "b"})]
	allow := {"svc-a": ["both-vpcs"]}
	groups := {"svc-a": {"both-vpcs": [vpc_addr, other]}}
	in_a := spacelift.deny with input as on_stack("svc-a", changes) with data.spacelift.destroy_allowlist as allow with data.spacelift.address_groups as groups
	count(in_a) == 0
	in_b := spacelift.deny with input as on_stack("svc-b", changes) with data.spacelift.destroy_allowlist as allow with data.spacelift.address_groups as groups
	count(in_b) == 2
}

# Whole-service teardown: a firewall delete next to its droplet's delete, in a
# stack that opted in.

svc_fw := "module.service_host.digitalocean_firewall.this"

svc_droplet := "module.service_host.digitalocean_droplet.this"

teardown_changes := [
	delete_of(svc_fw, "digitalocean_firewall", {"name": "svc", "tags": ["svc-a"], "droplet_ids": []}),
	delete_of(svc_droplet, "digitalocean_droplet", {"name": "svc", "id": "111", "tags": ["svc-a"]}),
]

teardown_reasons(id, changes) := reasons if {
	reasons := spacelift.deny with input as on_stack(id, changes) with data.spacelift.whole_service_teardown_stacks as {"svc-a"}
}

test_whole_service_teardown_is_allowed_in_an_opted_in_stack if {
	count(teardown_reasons("svc-a", teardown_changes)) == 0
}

test_whole_service_teardown_is_denied_in_another_stack if {
	count(teardown_reasons("svc-b", teardown_changes)) == 1
	reasons := spacelift.deny with input as plan(teardown_changes) with data.spacelift.whole_service_teardown_stacks as {"svc-a"}
	count(reasons) == 1
}

test_lone_firewall_delete_is_denied_even_when_opted_in if {
	count(teardown_reasons("svc-a", [teardown_changes[0]])) == 1
}

test_firewall_replace_with_droplet_delete_is_denied if {
	replace := removal(svc_fw, "digitalocean_firewall", ["delete", "create"], {"tags": ["svc-a"]})
	count(teardown_reasons("svc-a", [replace, teardown_changes[1]])) == 1
}

test_firewall_delete_with_droplet_replace_is_denied if {
	replace := removal(svc_droplet, "digitalocean_droplet", ["delete", "create"], {"id": "111", "tags": ["svc-a"]})
	count(teardown_reasons("svc-a", [teardown_changes[0], replace])) == 1
}

test_firewall_delete_with_an_unrelated_droplet_is_denied if {
	other := delete_of(svc_droplet, "digitalocean_droplet", {"id": "222", "tags": ["svc-b"]})
	count(teardown_reasons("svc-a", [teardown_changes[0], other])) == 1
}

test_a_shared_protected_tag_does_not_link_them if {
	fw_rc := delete_of(svc_fw, "digitalocean_firewall", {"tags": ["protected"]})
	droplet_rc := delete_of(svc_droplet, "digitalocean_droplet", {"id": "1", "tags": ["protected"]})

	# The tagged droplet is itself protected, so both are denied.
	reasons := teardown_reasons("svc-a", [fw_rc, droplet_rc])
	count(reasons) == 2
	some reason in reasons
	contains(reason, svc_fw)
}

test_firewall_naming_the_droplet_id_is_linked if {
	fw_rc := delete_of(svc_fw, "digitalocean_firewall", {"droplet_ids": [111]})
	droplet_rc := delete_of(svc_droplet, "digitalocean_droplet", {"id": "111"})
	count(teardown_reasons("svc-a", [fw_rc, droplet_rc])) == 0
}

# The whole-service rule is for the firewall only: other protected types, and
# anything tagged protected, still need the destroy allowlist.
test_whole_service_teardown_does_not_cover_other_protected_types if {
	vpc := delete_of(vpc_addr, "digitalocean_vpc", {"name": "a", "tags": ["svc-a"]})
	count(teardown_reasons("svc-a", array.concat(teardown_changes, [vpc]))) == 1
}

# Autodeploy guard. The plan input carries input.spacelift.stack.autodeploy.

with_stack(autodeploy) := object.union(plan([]), {"spacelift": {"stack": {"id": "cah-10-access", "autodeploy": autodeploy}}})

denied_input(inp) := reasons if {
	reasons := spacelift.deny with input as inp
}

test_autodeploy_on_is_denied if {
	reasons := denied_input(with_stack(true))
	count(reasons) == 1
	some msg in reasons
	contains(msg, "autodeploy")
}

test_autodeploy_off_passes if {
	count(denied_input(with_stack(false))) == 0
}

test_missing_or_null_stack_does_not_crash_autodeploy_guard if {
	count(denied_input(plan([]))) == 0
	count(denied_input({"spacelift": {"stack": null}, "terraform": {"resource_changes": []}})) == 0
	count(denied_input({"spacelift": {"stack": {"autodeploy": null}}})) == 0
}

# Review fixes (PR 252).

# A second droplet that the firewall still targets keeps the firewall guarded.
test_teardown_denied_when_another_droplet_keeps_the_tag if {
	kept := {
		"address": "module.service_host.digitalocean_droplet.second",
		"type": "digitalocean_droplet",
		"change": {"actions": ["no-op"], "before": {"id": "222", "tags": ["svc-a"]}, "after": {"id": "222", "tags": ["svc-a"]}},
	}
	count(teardown_reasons("svc-a", array.concat(teardown_changes, [kept]))) == 1
}

test_teardown_denied_when_another_droplet_is_replaced if {
	replaced := removal("module.service_host.digitalocean_droplet.second", "digitalocean_droplet", ["delete", "create"], {"id": "222", "tags": ["svc-a"]})
	count(teardown_reasons("svc-a", array.concat(teardown_changes, [replaced]))) == 1
}

test_teardown_denied_when_a_created_droplet_takes_the_tag if {
	made := create("module.service_host.digitalocean_droplet.new", "digitalocean_droplet", {"id": "333", "tags": ["svc-a"]})
	count(teardown_reasons("svc-a", array.concat(teardown_changes, [made]))) == 1
}

test_teardown_allowed_when_every_matching_droplet_is_deleted if {
	second := delete_of("module.service_host.digitalocean_droplet.second", "digitalocean_droplet", {"id": "222", "tags": ["svc-a"]})
	count(teardown_reasons("svc-a", array.concat(teardown_changes, [second]))) == 0
}

test_teardown_denied_when_firewall_lists_an_id_not_deleted if {
	fw_rc := delete_of(svc_fw, "digitalocean_firewall", {"droplet_ids": [111, 999]})
	droplet_rc := delete_of(svc_droplet, "digitalocean_droplet", {"id": "111"})
	count(teardown_reasons("svc-a", [fw_rc, droplet_rc])) == 1
	both := delete_of("module.service_host.digitalocean_droplet.b", "digitalocean_droplet", {"id": "999"})
	count(teardown_reasons("svc-a", [fw_rc, droplet_rc, both])) == 0
}

# One AWS rule with two ranges needs one entry that covers both.
test_aws_two_ranges_need_one_entry_covering_both if {
	two := create("a.aws_security_group_rule.r", "aws_security_group_rule", {"type": "ingress", "protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["10.0.0.0/8", "172.16.0.0/12"], "ipv6_cidr_blocks": null})
	one_each := {"aws-a": {"a.aws_security_group_rule.r": [
		aws_entry({"sources": ["10.0.0.0/8"]}),
		aws_entry({"sources": ["172.16.0.0/12"]}),
	]}}
	count(reasons_with("aws-a", [two], one_each)) == 1
	both := {"aws-a": {"a.aws_security_group_rule.r": [aws_entry({"sources": ["10.0.0.0/8", "172.16.0.0/12"]})]}}
	count(reasons_with("aws-a", [two], both)) == 0
}

test_aws_inline_block_with_two_ranges_needs_one_entry if {
	sg := create("a.aws_security_group.this", "aws_security_group", {"ingress": [{"from_port": 22, "to_port": 22, "protocol": "tcp", "cidr_blocks": ["10.0.0.0/8"], "ipv6_cidr_blocks": ["fd00::/8"], "security_groups": []}]})
	split := {"aws-a": {"a.aws_security_group.this": [
		aws_entry({"ports": ["22"], "sources": ["10.0.0.0/8"]}),
		aws_entry({"ports": ["22"], "sources": ["fd00::/8"]}),
	]}}
	count(reasons_with("aws-a", [sg], split)) == 1
}

# World-open outbound rules (issue #253).

out_world := ["0.0.0.0/0", "::/0"]

out_rule(protocol, port, destinations) := {
	"protocol": protocol,
	"port_range": port,
	"destination_addresses": destinations,
	"destination_tags": [],
	"destination_droplet_ids": [],
	"destination_load_balancer_uids": [],
	"destination_kubernetes_ids": [],
}

firewall_out(rules) := create(fw, "digitalocean_firewall", {"inbound_rule": [], "outbound_rule": rules})

out_entry(overrides) := object.union(
	{
		"direction": "outbound",
		"protocol": "tcp",
		"ports": ["443"],
		"destinations": out_world,
	},
	overrides,
)

reasons_with_outbound(id, changes, allowlist) := reasons if {
	reasons := spacelift.deny with input as on_stack(id, changes) with data.spacelift.outbound_allowlist as allowlist
}

test_world_open_outbound_is_denied_by_default if {
	reasons := denied_on("svc-a", [firewall_out([out_rule("tcp", "443", out_world)])])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "outbound rule tcp/443 reaches the whole internet")
}

test_world_open_ipv4_only_outbound_is_denied if {
	count(denied_on("svc-a", [firewall_out([out_rule("tcp", "443", ["0.0.0.0/0"])])])) == 1
}

test_world_open_ipv6_only_outbound_is_denied if {
	count(denied_on("svc-a", [firewall_out([out_rule("tcp", "443", ["::/0"])])])) == 1
}

test_world_mixed_with_named_destination_is_denied if {
	count(denied_on("svc-a", [firewall_out([out_rule("tcp", "443", ["203.0.113.0/24", "0.0.0.0/0"])])])) == 1
}

# Narrowed or tag-scoped outbound rules are not world-open.
test_outbound_to_named_addresses_passes if {
	rule := out_rule("tcp", "443", ["203.0.113.0/24", "198.51.100.7/32", "2001:db8::/32"])
	count(denied_on("svc-a", [firewall_out([rule])])) == 0
}

test_outbound_to_tag_passes if {
	rule := object.union(out_rule("tcp", "22", []), {"destination_tags": ["cah-access"]})
	count(denied_on("svc-a", [firewall_out([rule])])) == 0
}

test_outbound_with_null_destinations_does_not_crash if {
	rule := {"protocol": "tcp", "port_range": "22", "destination_addresses": null}
	count(denied_on("svc-a", [firewall_out([rule])])) == 0
	count(denied_on("svc-a", [create(fw, "digitalocean_firewall", {"inbound_rule": []})])) == 0
}

test_outbound_allowlisted_entry_passes_in_its_stack if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", out_world)])], allow)) == 0
}

test_outbound_entry_is_keyed_by_stack if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	count(reasons_with_outbound("svc-b", [firewall_out([out_rule("tcp", "443", out_world)])], allow)) == 1
}

test_outbound_entry_is_keyed_by_address if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	other := create("module.other.digitalocean_firewall.this", "digitalocean_firewall", {"outbound_rule": [out_rule("tcp", "443", out_world)]})
	count(reasons_with_outbound("svc-a", [other], allow)) == 1
}

test_outbound_plan_with_no_stack_id_gets_no_exception if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	reasons := spacelift.deny with input as plan([firewall_out([out_rule("tcp", "443", out_world)])]) with data.spacelift.outbound_allowlist as allow
	count(reasons) == 1
}

test_outbound_group_covers_its_members_in_its_stack_only if {
	allow := allow_for("svc-a", "web", [out_entry({})])
	changes := [firewall_out([out_rule("tcp", "443", out_world)])]
	groups := {"svc-a": {"web": [fw]}}
	covered := spacelift.deny with input as on_stack("svc-a", changes) with data.spacelift.outbound_allowlist as allow with data.spacelift.address_groups as groups
	count(covered) == 0
	elsewhere := spacelift.deny with input as on_stack("svc-b", changes) with data.spacelift.outbound_allowlist as allow with data.spacelift.address_groups as groups
	count(elsewhere) == 1
}

# Each field narrows the entry.

test_outbound_entry_for_another_port_denies if {
	allow := allow_for("svc-a", fw, [out_entry({"ports": ["80"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", out_world)])], allow)) == 1
}

test_outbound_entry_for_another_protocol_denies if {
	allow := allow_for("svc-a", fw, [out_entry({"protocol": "udp"})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", out_world)])], allow)) == 1
}

test_outbound_entry_for_another_destination_denies if {
	allow := allow_for("svc-a", fw, [out_entry({"destinations": ["203.0.113.0/24"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", ["203.0.113.0/24", "0.0.0.0/0"])])], allow)) == 1
}

test_outbound_world_entry_must_list_both_ranges if {
	rule := out_rule("tcp", "443", out_world)
	only4 := allow_for("svc-a", fw, [out_entry({"destinations": ["0.0.0.0/0"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], only4)) == 1
	only_v4_rule := out_rule("tcp", "443", ["0.0.0.0/0"])
	both := allow_for("svc-a", fw, [out_entry({})])
	count(reasons_with_outbound("svc-a", [firewall_out([only_v4_rule])], both)) == 0
}

test_outbound_entry_with_wrong_direction_denies if {
	rule := out_rule("tcp", "443", out_world)
	inbound := allow_for("svc-a", fw, [out_entry({"direction": "inbound"})])
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], inbound)) == 1
	missing := allow_for("svc-a", fw, [object.remove(out_entry({}), ["direction"])])
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], missing)) == 1
}

test_outbound_entry_missing_a_field_denies if {
	rule := out_rule("tcp", "443", out_world)
	every field in ["protocol", "ports", "destinations"] {
		allow := allow_for("svc-a", fw, [object.remove(out_entry({}), [field])])
		count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow)) == 1
	}
}

test_outbound_entry_with_empty_lists_denies if {
	rule := out_rule("tcp", "443", out_world)
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow_for("svc-a", fw, [out_entry({"ports": []})]))) == 1
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow_for("svc-a", fw, [out_entry({"destinations": []})]))) == 1
}

# An outbound entry never admits an inbound rule, and an inbound entry never
# admits an outbound one.
test_outbound_entry_does_not_cover_inbound_rules if {
	allow := allow_for("svc-a", fw, [out_entry({"ports": ["8080"], "destinations": ["198.51.100.0/24"]})])
	reasons := spacelift.deny with input as on_stack("svc-a", [firewall_with([bad_rule])]) with data.spacelift.outbound_allowlist as allow
	count(reasons) == 1
}

test_inbound_entry_does_not_cover_outbound_rules if {
	allow := allow_for("svc-a", fw, [entry({"ports": ["443"], "sources": out_world})])
	reasons := spacelift.deny with input as on_stack("svc-a", [firewall_out([out_rule("tcp", "443", out_world)])]) with data.spacelift.inbound_allowlist as allow
	count(reasons) == 1
}

test_outbound_rule_with_another_destination_kind_is_never_covered if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	rule := object.union(out_rule("tcp", "443", out_world), {"destination_tags": ["cah-access"]})
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow)) == 1
}

test_outbound_rules_are_judged_one_by_one if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	rules := [out_rule("tcp", "443", out_world), out_rule("tcp", "8443", out_world), out_rule("tcp", "22", ["203.0.113.7/32"])]
	reasons := reasons_with_outbound("svc-a", [firewall_out(rules)], allow)
	count(reasons) == 1
	some reason in reasons
	contains(reason, "tcp/8443")
}

# Decision: icmp and all-port rules are never allowlistable (issue #253).

test_world_open_icmp_is_denied if {
	count(denied_on("svc-a", [firewall_out([out_rule("icmp", "", out_world)])])) == 1
	count(denied_on("svc-a", [firewall_out([{"protocol": "icmp", "destination_addresses": out_world}])])) == 1
}

test_icmp_is_never_covered_by_an_entry if {
	allow := allow_for("svc-a", fw, [out_entry({"protocol": "icmp", "ports": ["", "all", "0"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("icmp", "", out_world)])], allow)) == 1
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("icmp", "0", out_world)])], allow)) == 1
}

test_all_port_rule_is_never_covered_by_an_entry if {
	allow := allow_for("svc-a", fw, [out_entry({"ports": ["", "all", "443"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "all", out_world)])], allow)) == 1
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "", out_world)])], allow)) == 1
	count(reasons_with_outbound("svc-a", [firewall_out([{"protocol": "tcp", "destination_addresses": out_world}])], allow)) == 1
	udp_allow := allow_for("svc-a", fw, [out_entry({"protocol": "udp", "ports": ["", "all"]})])
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("udp", null, out_world)])], udp_allow)) == 1
}

# A literal range is judged as written: the entry must name the exact string.
test_explicit_full_range_needs_its_own_entry if {
	rule := out_rule("udp", "1-65535", out_world)
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow_for("svc-a", fw, [out_entry({"protocol": "udp"})]))) == 1
	count(reasons_with_outbound("svc-a", [firewall_out([rule])], allow_for("svc-a", fw, [out_entry({"protocol": "udp", "ports": ["1-65535"]})]))) == 0
}

# Outbound handling reads firewall create and update, like inbound.
test_outbound_delete_and_noop_are_ignored if {
	after := {"outbound_rule": [out_rule("tcp", "443", out_world)]}
	count(denied_on("svc-a", [change(fw, "digitalocean_firewall", ["no-op"], after)])) == 0
	count(denied_on("svc-a", [change(fw, "digitalocean_firewall", ["update"], after)])) == 1
}

# Today's stacks: the rules the firewall module renders for them pass with the
# shipped entries, at their real addresses, and nothing wider does.

default_outbound := [
	out_rule("tcp", "443", out_world),
	out_rule("tcp", "80", out_world),
	out_rule("tcp", "53", out_world),
	out_rule("udp", "53", out_world),
	out_rule("udp", "123", out_world),
]

baseline_addr := "module.baseline_firewall.digitalocean_firewall.this"

connector_addr := "module.connector_firewall.digitalocean_firewall.this"

baseline_fw := create(baseline_addr, "digitalocean_firewall", {"inbound_rule": [], "outbound_rule": default_outbound})

connector_extra := [out_rule("tcp", "30000-31000", out_world), out_rule("udp", "1-65535", out_world)]

connector_fw := create(connector_addr, "digitalocean_firewall", {"inbound_rule": [], "outbound_rule": array.concat(default_outbound, connector_extra)})

test_shipped_baseline_firewall_passes_in_foundation if {
	count(denied_on("cah-00-foundation", [baseline_fw])) == 0
}

test_shipped_connector_firewall_passes_in_access if {
	count(denied_on("cah-10-access", [connector_fw])) == 0
}

test_shipped_entries_do_not_cross_stacks_or_addresses if {
	count(denied_on("cah-10-access", [baseline_fw])) == 5
	count(denied_on("cah-00-foundation", [connector_fw])) == 7
	count(denied_on("cah-20-telemetry", [baseline_fw])) == 5
	count(denied_on("cah-20-telemetry", [connector_fw])) == 7
}

test_shipped_entries_do_not_allow_more_than_they_name if {
	wider := [
		out_rule("tcp", "8443", out_world),
		out_rule("tcp", "1-65535", out_world),
		out_rule("tcp", "all", out_world),
		out_rule("udp", "30000-31000", out_world),
		out_rule("icmp", "", out_world),
	]
	extra := create(connector_addr, "digitalocean_firewall", {"outbound_rule": wider})
	count(denied_on("cah-10-access", [extra])) == 5
	foundation_extra := create(baseline_addr, "digitalocean_firewall", {"outbound_rule": connector_extra})
	count(denied_on("cah-00-foundation", [foundation_extra])) == 2
}

# Review of PR #283: the whole internet is judged by prefix length, not by
# exact spelling, and an unknown value never passes.

# Spellings of "everything", split halves, and values that cannot be parsed.
# Unparseable text fails closed: it is treated as the whole internet.
world_spellings := [
	["0.0.0.0/1", "128.0.0.0/1"],
	["::/1", "8000::/1"],
	["0::/0"],
	["0:0:0:0:0:0:0:0/0"],
	["::0/0"],
	["::/00"],
	["0.0.0.0/00"],
	["0.0.0.0/01"],
	["128.0.0.0/1"],
	["203.0.113.0/24", "0.0.0.0/00"],
	["banana"],
	["0.0.0.0/"],
	["0.0.0.0/33"],
	["10.0.0.0/-1"],
	[" 0.0.0.0/0"],
	[""],
]

test_outbound_world_spellings_are_denied if {
	every destinations in world_spellings {
		reasons := denied_on("svc-a", [firewall_out([out_rule("tcp", "443", destinations)])])
		count(reasons) == 1
		some reason in reasons
		contains(reason, "reaches the whole internet")
	}
}

test_outbound_world_spelling_is_not_covered_by_an_exact_entry if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	every destinations in world_spellings {
		count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", destinations)])], allow)) == 1
	}

	# ::/0 spelled differently next to the listed range is still not listed.
	count(reasons_with_outbound("svc-a", [firewall_out([out_rule("tcp", "443", ["0.0.0.0/0", "0::/0"])])], allow)) == 1
}

test_outbound_narrow_destinations_are_not_world_open if {
	every destinations in [
		["64.0.0.0/2"],
		["10.0.0.0/8"],
		["203.0.113.0/24"],
		["203.0.113.7"],
		["203.0.113.7/32"],
		["2001:db8::/32"],
		["2001:db8::1"],
		["2001:db8::1/128"],
	] {
		count(denied_on("svc-a", [firewall_out([out_rule("tcp", "443", destinations)])])) == 0
	}
}

test_inbound_world_spellings_are_called_out_as_the_whole_internet if {
	every sources in world_spellings {
		reasons := denied([firewall_with([with_source({"source_tags": [], "source_addresses": sources})])])
		count(reasons) == 1
		some reason in reasons
		contains(reason, "opens the port to the whole internet")
	}
}

test_inbound_narrow_sources_are_not_called_the_whole_internet if {
	reasons := denied([firewall_with([with_source({"source_tags": [], "source_addresses": ["198.51.100.0/24"]})])])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "is not tag-scoped")
}

test_inbound_world_spelling_is_not_covered_by_an_exact_entry if {
	allow := allow_for("svc-a", fw, [entry({"sources": ["0.0.0.0/0", "::/0"]})])
	rule := with_source({"source_tags": [], "source_addresses": ["0::/0"]})
	count(reasons_with("svc-a", [firewall_with([rule])], allow)) == 1
}

# Unknown values. A real plan lists them in change.after_unknown, which mirrors
# change.after: true for a value, or a list whose elements are objects.

firewall_unknown(after, unknown) := {
	"address": fw,
	"type": "digitalocean_firewall",
	"change": {"actions": ["create"], "after": after, "after_unknown": unknown},
}

test_unknown_outbound_rule_list_is_denied if {
	reasons := denied([firewall_unknown({"inbound_rule": []}, {"outbound_rule": true})])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "outbound_rule")
	contains(reason, "not known")
}

test_unknown_destination_addresses_in_one_rule_is_denied if {
	after := {"inbound_rule": [], "outbound_rule": [out_rule("tcp", "443", ["203.0.113.0/24"]), out_rule("udp", "53", [])]}
	reasons := denied([firewall_unknown(after, {"outbound_rule": [{}, {"destination_addresses": true}]})])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "outbound_rule")
	contains(reason, "destination_addresses")
}

test_unknown_element_of_destination_addresses_is_denied if {
	after := {"inbound_rule": [], "outbound_rule": [out_rule("tcp", "443", ["203.0.113.0/24"])]}
	reasons := denied([firewall_unknown(after, {"outbound_rule": [{"destination_addresses": [false, true]}]})])
	count(reasons) == 1
}

test_unknown_whole_outbound_rule_element_is_denied if {
	after := {"inbound_rule": [], "outbound_rule": [out_rule("tcp", "443", ["203.0.113.0/24"])]}
	count(denied([firewall_unknown(after, {"outbound_rule": [true]})])) == 1
}

test_unknown_outbound_is_not_allowlistable if {
	allow := allow_for("svc-a", fw, [out_entry({})])
	after := {"inbound_rule": [], "outbound_rule": [out_rule("tcp", "443", out_world)]}
	changes := [firewall_unknown(after, {"outbound_rule": [{"destination_addresses": [true, false]}]})]
	count(reasons_with_outbound("svc-a", changes, allow)) == 1
}

test_unknown_inbound_rule_list_is_denied if {
	reasons := denied([firewall_unknown({"outbound_rule": []}, {"inbound_rule": true})])
	count(reasons) == 1
	some reason in reasons
	contains(reason, "inbound_rule")
	contains(reason, "not known")
}

test_unknown_inbound_sources_are_denied if {
	after := {"outbound_rule": [], "inbound_rule": [tag_rule, tag_rule]}
	every key in ["source_addresses", "source_droplet_ids", "source_load_balancer_uids", "source_kubernetes_ids"] {
		reasons := denied([firewall_unknown(after, {"inbound_rule": [{}, {key: true}]})])
		count(reasons) == 1
		some reason in reasons
		contains(reason, key)
	}
}

test_unknown_on_update_is_denied_too if {
	update := {
		"address": fw,
		"type": "digitalocean_firewall",
		"change": {"actions": ["update"], "after": {"inbound_rule": []}, "after_unknown": {"outbound_rule": true}},
	}
	count(denied([update])) == 1
}

# Unknown values elsewhere are not this policy's business, and the empty and
# absent shapes of after_unknown do not crash it.
test_unrelated_and_empty_unknowns_pass if {
	after := {"inbound_rule": [tag_rule], "outbound_rule": [out_rule("tcp", "443", ["203.0.113.0/24"])]}
	count(denied([firewall_unknown(after, {"id": true, "droplet_ids": true, "outbound_rule": [{"protocol": false}], "inbound_rule": [{"source_tags": true}]})])) == 0
	count(denied([firewall_unknown(after, {})])) == 0
	count(denied([firewall_unknown(after, null)])) == 0
	count(denied([firewall_unknown(after, {"outbound_rule": false, "inbound_rule": false})])) == 0
}

test_unknown_on_a_delete_is_ignored if {
	gone := {
		"address": fw,
		"type": "digitalocean_firewall",
		"change": {"actions": ["delete"], "before": {"inbound_rule": []}, "after": null, "after_unknown": {"outbound_rule": true}},
	}
	not any_not_known(denied([gone]))
}

any_not_known(reasons) if {
	some reason in reasons
	contains(reason, "not known")
}
