# Plan policy for every stack in this repository (cah-00-foundation,
# cah-10-access, the AWS stacks, and later ones). Explained in
# docs/spacelift-secrets.md, section 9a, and on the Spacelift wiki page.
#
# Spacelift does not read this file from the repository. Create a plan policy
# in Spacelift with this body and attach it to each stack (or give it the
# label autoattach:cah, the same label the push policy and the Doppler context
# use). The tests next to it run in CI on every pull request.
#
# What it decides: whether a plan may be applied. A plan that would open a
# port on a core machine, or turn on IPv6, is denied before anything is
# applied. The firewall module's own tests catch the same mistakes in CI, but
# only for the code they exercise; this checks the plan Spacelift is about to
# apply, whatever code produced it.
#
# It denies a created or updated resource that is:
#
#   - a digitalocean_firewall with an inbound rule that is not tag-scoped.
#     The firewall module only ever emits source_tags (the firewall's own tag,
#     or one other group's tag), so a source address, droplet id, load
#     balancer or Kubernetes source is a change the module cannot produce, and
#     0.0.0.0/0 or ::/0 is the whole internet.
#   - a digitalocean_firewall with an outbound rule whose destination is the
#     whole internet (0.0.0.0/0 or ::/0), unless outbound_allowlist has an
#     entry for that stack and address (issue #253). Outbound rules to a tag,
#     or to named addresses, are not judged. icmp rules and rules with no
#     port range (or "all") are never allowlistable: see outbound_allowlist.
#     "The whole internet" is judged by prefix length (/0 through /8, IPv4 and IPv6),
#     not by exact spelling; see wide_address.
#   - a digitalocean_firewall whose inbound_rule or outbound_rule, or a rule's
#     source or destination addresses, are unknown until apply. They could
#     resolve to the whole internet, so they are denied; see unknown_in_rules.
#   - an AWS security group rule that admits a CIDR range (IPv4 or IPv6). The
#     AWS firewall module admits only a reference to the group itself. AWS
#     egress rules are not judged here.
#   - a droplet with ipv6 turned on, or an AWS VPC, subnet or instance that
#     takes an IPv6 range or address. IPv6 stays closed in this repository.
#
# Pure deletes and no-ops are ignored: removing a rule never opens anything.
#
# The policy does not read a rule's `action`. DigitalOcean rules can allow or
# deny, and a deny rule takes precedence over an allow rule (Configure
# Firewall Rules page, last verified 4 Aug 2026, read 2026-10-30). This module
# only emits allow rules, so every rule is judged as if it opens something. A
# deny rule by address or with a world-wide destination is therefore refused
# like an allow rule would be (it fails closed, and it is not tested); if
# deny rules are ever used on purpose, teach the checks to read `action` first.
#
# The escape hatch is this file. A deliberate inbound rule is allowed only by
# an entry in inbound_allowlist below, and a deliberate world-open outbound
# rule only by an entry in outbound_allowlist, in a pull request that gets
# reviewed.
# Nothing a plan can set itself (a stack label, an environment variable, a
# field in the plan) is read, so a branch cannot grant its own exception. The
# IPv6 checks have no escape hatch.
#
# Allowlists are keyed by stack id, then by resource address (or the name of a
# group of addresses), because an address such as
# `module.service_host.digitalocean_firewall.this` is stack-relative: one
# module reused in five stacks gives five resources with the same address, and
# an exception for one must not cover the others (issue #246). The stack id is
# input.spacelift.stack.id. An entry is added only when that service's stack is
# approved, and an entry says exactly what it allows: its direction, protocol,
# ports and sources (see inbound_allowlist). A missing or unknown stack id, key,
# or field allows nothing: the policy fails closed.
#
# Two guards turn the "locked and manual" convention into a rule (issue #92):
#
#   - Destroy guard: a plan that deletes, or replaces, a digitalocean_vpc,
#     digitalocean_project, digitalocean_firewall, twingate_remote_network,
#     aws_vpc, aws_security_group, or anything tagged `protected`, is denied.
#     Droplets are deliberately not protected: a connector replace is a normal,
#     reviewed event. Escape hatches: destroy_allowlist (stack id, then address or group),
#     and, for a stack listed in whole_service_teardown_stacks, a firewall that
#     the same plan deletes together with the droplet it protects.
#   - Autodeploy guard: a stack with autodeploy on is denied. Spacelift's plan
#     input does expose it (input.spacelift.stack.autodeploy; the contract
#     lists it as required), so this is a real check, not a note. It has no
#     allowlist. It runs inside a plan, so it cannot stop a stack from being
#     created with autodeploy on; it blocks the apply it would have made. The
#     setting itself is enforced where stacks are made (issue #96).
#
# Plan policies run on tracked runs here, before the apply. Proposed runs do
# not exist in this repository (see push.rego), so this is the gate on the
# plan a human is about to confirm.

package spacelift

import rego.v1

# Inbound exceptions, keyed by stack id, then by a resource address (as shown
# in the plan, for example `module.fw.digitalocean_firewall.this`) or the name
# of a group in address_groups. Each key holds a list of entries; an entry
# allows one kind of inbound rule and nothing else:
#
#   {
#     "direction": "inbound",         # required; only "inbound" is read
#     "protocol": "tcp",              # required, exact match
#     "ports": ["5201"],              # required, exact port_range strings
#     "sources": ["203.0.113.7/32"],  # required, every non-tag source address
#                                     # the rule has must be in this list
#   }
#
# World-open is just the sources list naming "0.0.0.0/0" and "::/0": listing
# only one of them does not allow the other. A rule that adds a droplet,
# load balancer or Kubernetes source is never covered. Rules are judged one by
# one, so a firewall with two rules needs an entry for each rule that is not
# tag-scoped. The same entries judge AWS ingress rules (sources are the CIDR
# ranges; ports are "443" or "8000-8100").
#
# Empty by default. Every entry needs a threat-model note
# (docs/wiki/Threat-Model.md) and a pull request review that names the stack,
# the port, the source and the reason, and lands together with that service's
# stack approval. Remove the entry when the rule goes away.
inbound_allowlist := {}

# World-open outbound exceptions (issue #253), same shape as inbound_allowlist:
# keyed by stack id, then by a resource address or a group name from
# address_groups. An entry allows one kind of outbound rule and nothing else:
#
#   {
#     "direction": "outbound",          # required, exactly "outbound"
#     "protocol": "tcp",                # required, exact match
#     "ports": ["443", "80"],           # required, exact port_range strings
#     "destinations": ["0.0.0.0/0", "::/0"],  # required, every destination
#                                       # address the rule has must be listed
#   }
#
# Only a rule with 0.0.0.0/0 or ::/0 among its destination_addresses is
# judged; a rule to a tag, or to named addresses only, needs no entry. Rules
# are judged one by one, so one entry covers one protocol and a firewall with
# tcp and udp rules needs an entry for each. An entry naming only one of the
# two world ranges does not cover a rule that uses both.
#
# Decision on icmp and all-port rules: they are NEVER allowlistable, even if an
# entry tries to name them. An icmp rule has no port, and a tcp or udp rule
# whose port_range is missing, empty or "all" has no limit; with a world-open
# destination, nothing narrows either of them, so the way to get them is to
# name destinations instead of the world. A literal range such as "1-65535"
# is judged as written: an entry must name that exact string, which puts the
# widest range in the reviewed pull request with its reason. Empty entries,
# missing fields and unknown stacks allow nothing.
#
# Every entry below exists because the firewall module renders it today: the
# five default outbound rules (tcp 443, 80, 53; udp 53, 123) on any address,
# plus the extra rules the connector firewall in cah-10-access adds. Remove an
# entry when its rule goes away.
outbound_allowlist := {
	# stacks/00-foundation: the baseline firewall. Defaults only: package
	# mirrors, DNS and NTP have no fixed addresses to pin.
	"cah-00-foundation": {"module.baseline_firewall.digitalocean_firewall.this": [
		{"direction": "outbound", "protocol": "tcp", "ports": ["443", "80", "53"], "destinations": ["0.0.0.0/0", "::/0"]},
		{"direction": "outbound", "protocol": "udp", "ports": ["53", "123"], "destinations": ["0.0.0.0/0", "::/0"]},
	]},
	# stacks/10-access: the connector firewall. The defaults, plus Twingate's
	# documented outbound needs: tcp 30000-31000 and udp to any port for
	# peer-to-peer connections (see the comment above the module call).
	"cah-10-access": {"module.connector_firewall.digitalocean_firewall.this": [
		{"direction": "outbound", "protocol": "tcp", "ports": ["443", "80", "53", "30000-31000"], "destinations": ["0.0.0.0/0", "::/0"]},
		{"direction": "outbound", "protocol": "udp", "ports": ["53", "123", "1-65535"], "destinations": ["0.0.0.0/0", "::/0"]},
	]},
}

# Named groups of resource addresses, per stack id, so one entry can cover
# several resources in that stack: {"stack-id": {"group-name": ["address"]}}.
# A group of one stack means nothing in another.
address_groups := {}

# Resource addresses (or group names) whose deletion or replacement is allowed
# even though the resource is protected, per stack id:
# {"stack-id": ["module.vpc.digitalocean_vpc.this"]}. Empty by default. Same
# rule as above: a pull request that names the stack, the address and the
# reason, reviewed, then the new body pasted into Spacelift. Remove the entry
# once the change has applied.
destroy_allowlist := {}

# Stack ids where a whole-service teardown is routine: a plan there that
# deletes (not replaces) a digitalocean_firewall and the droplet it protects,
# in the same plan, is allowed without a destroy_allowlist entry. Protection
# is shown by a shared target tag or by the firewall naming the droplet id. A
# lone firewall delete, a replacement, an unrelated droplet and every other
# protected type are still denied. A stack id is added here when that service's
# stack is approved. Empty by default.
whole_service_teardown_stacks := set()

# The stack this plan belongs to, or "" when the plan does not say. Nothing is
# allowlisted for "".
stack_id := id if {
	stack := input.spacelift.stack
	is_object(stack)
	id := stack.id
	is_string(id)
} else := ""

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	some rule in rc.change.after.inbound_rule
	world_open(rule)
	not rule_allowed(rc, rule)
	msg := sprintf(
		"%s: inbound rule %s opens the port to the whole internet (%s). Inbound on core tags must come from a tag only, unless inbound_allowlist has an entry for this stack and address.",
		[rc.address, rule_label(rule), source_summary(rule)],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	some rule in rc.change.after.inbound_rule
	not world_open(rule)
	not tag_scoped(rule)
	not rule_allowed(rc, rule)
	msg := sprintf(
		"%s: inbound rule %s is not tag-scoped (%s). Inbound on core tags must come from a tag only, unless inbound_allowlist has an entry for this stack and address.",
		[rc.address, rule_label(rule), source_summary(rule)],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	some rule in values(rc.change.after, "outbound_rule")
	world_open_outbound(rule)
	not outbound_rule_allowed(rc, rule)
	msg := sprintf(
		"%s: outbound rule %s reaches the whole internet (%s). Outbound world-open rules need an outbound_allowlist entry for this stack and address, naming the direction, protocol, port and destinations. icmp and all-port rules are never allowed: name destinations instead.",
		[rc.address, rule_label(rule), destination_summary(rule)],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	some where in unknown_in_rules(rc, "inbound_rule", non_tag_sources)
	msg := sprintf(
		"%s: %s is not known until apply, so the plan cannot show whether the rule is tag-scoped. Inbound sources must be known at plan time; make the value static. No allowlist entry covers an unknown value.",
		[rc.address, where],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	some where in unknown_in_rules(rc, "outbound_rule", {"destination_addresses"})
	msg := sprintf(
		"%s: %s is not known until apply, so the plan cannot show whether the rule reaches the whole internet. Outbound destinations must be known at plan time; make the value static. No allowlist entry covers an unknown value.",
		[rc.address, where],
	)
}

deny contains msg if {
	some entry in aws_ingress_cidrs
	not aws_allowed(entry)
	msg := sprintf(
		"%s: %s admits inbound traffic from %s. AWS ingress here may only reference a security group, never a CIDR range.",
		[entry.address, entry.type, concat(", ", entry.cidrs)],
	)
}

deny contains msg if {
	some rc in removed_resources
	protected(rc)
	not destroy_allowed(rc)
	msg := sprintf(
		"%s: this plan deletes (or replaces) a protected %s. A human must add the address to destroy_allowlist under this stack's id in .spacelift/policies/plan.rego, in a pull request, before it can be applied.",
		[rc.address, rc.type],
	)
}

# The stack settings are part of the plan input, so a stack with autodeploy on
# is denied here. Stacks in this repository stay manual: a human reads every
# plan and confirms. Turning autodeploy back off is the fix; there is no
# allowlist. The setting itself belongs to the stack (the stack factory, issue
# #96, should create stacks with autodeploy off).
deny contains msg if {
	input.spacelift.stack.autodeploy == true
	msg := sprintf(
		"stack %s has autodeploy enabled. Stacks here are manual: turn autodeploy off so a human confirms every apply.",
		[object.get(input.spacelift.stack, "id", "(unknown)")],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_droplet")
	rc.change.after.ipv6 == true
	msg := sprintf("%s: ipv6 = true. IPv6 must stay closed on droplets.", [rc.address])
}

deny contains msg if {
	some entry in ipv6_findings
	msg := sprintf("%s: %s. IPv6 must stay closed.", [entry.address, entry.reason])
}

# Resources of one type that this plan creates or updates. A replacement
# (delete then create) counts; a pure delete or no-op does not.
changed_resources(type) := {rc |
	some rc in input.terraform.resource_changes
	rc.type == type
	some action in rc.change.actions
	action in {"create", "update"}
}

# Does a key in this stack's allowlist (an address, or a group name) cover
# this resource address?
key_covers(key, address) if key == address

key_covers(key, address) if address in object.get(object.get(address_groups, stack_id, {}), key, [])

# The entries that apply to one resource in this stack. Another stack's
# entries, and a plan with no stack id, give none.
entries_for(address) := [entry |
	stack_id != ""
	some key, entries in object.get(inbound_allowlist, stack_id, {})
	key_covers(key, address)
	some entry in entries
]

# The same for outbound rules, from outbound_allowlist.
outbound_entries_for(address) := [entry |
	stack_id != ""
	some key, entries in object.get(outbound_allowlist, stack_id, {})
	key_covers(key, address)
	some entry in entries
]

# One entry admits one rule when every part matches exactly. Anything missing
# from the entry, or from the rule, admits nothing.
admits(entry, protocol, port, addresses) if {
	object.get(entry, "direction", "") == "inbound"
	protocol != ""
	protocol == object.get(entry, "protocol", "")
	port != ""
	port in object.get(entry, "ports", [])
	count(addresses) > 0
	every address in addresses {
		address in object.get(entry, "sources", [])
	}
}

# An outbound entry admits a world-open rule when the direction is outbound,
# the protocol and port_range match exactly, and every destination address of
# the rule is listed. icmp, a missing or empty port_range and "all" are never
# admitted (see outbound_allowlist).
outbound_admits(entry, rule) if {
	object.get(entry, "direction", "") == "outbound"
	protocol := object.get(rule, "protocol", "")
	protocol in {"tcp", "udp"}
	protocol == object.get(entry, "protocol", "")
	port := object.get(rule, "port_range", "")
	is_string(port)
	not port in {"", "all"}
	port in object.get(entry, "ports", [])
	addresses := values(rule, "destination_addresses")
	count(addresses) > 0
	every address in addresses {
		address in object.get(entry, "destinations", [])
	}
}

# A world-open outbound rule is allowed only when it names no other kind of
# destination and an entry admits it.
outbound_rule_allowed(rc, rule) if {
	not has_other_destination(rule)
	some entry in outbound_entries_for(rc.address)
	outbound_admits(entry, rule)
}

has_other_destination(rule) if {
	some key in {"destination_tags", "destination_droplet_ids", "destination_load_balancer_uids", "destination_kubernetes_ids"}
	filled(rule, key)
}

# A DigitalOcean inbound rule is allowed only when it carries source
# addresses, no other non-tag source kind, and an entry admits it.
rule_allowed(rc, rule) if {
	filled(rule, "source_addresses")
	not has_other_source(rule)
	some entry in entries_for(rc.address)
	admits(entry, object.get(rule, "protocol", ""), object.get(rule, "port_range", ""), values(rule, "source_addresses"))
}

has_other_source(rule) if {
	some key in (non_tag_sources - {"source_addresses"})
	filled(rule, key)
}

aws_allowed(finding) if {
	some entry in entries_for(finding.address)
	admits(entry, finding.protocol, finding.port, finding.cidrs)
}

destroy_allowed(rc) if {
	stack_id != ""
	some key in object.get(destroy_allowlist, stack_id, [])
	key_covers(key, rc.address)
}

destroy_allowed(rc) if whole_service_teardown(rc)

# A firewall delete that comes with the delete of the droplet it protects, in
# a stack that opted in. Both must be pure deletes: a replacement is a change
# to a live service, not a teardown.
whole_service_teardown(rc) if {
	stack_id in whole_service_teardown_stacks
	rc.type == "digitalocean_firewall"
	actions_of(rc) == ["delete"]
	some droplet in removed_resources
	droplet.type == "digitalocean_droplet"
	actions_of(droplet) == ["delete"]
	protects(rc, droplet)
	not survivor_protected(rc)
	every id in values(before_of(rc), "droplet_ids") {
		id_deleted(id)
	}
}

# A droplet this firewall still protects after the plan: any droplet in the
# plan that is not a pure delete (kept, replaced, updated or created) and
# matches by tag or id. A shared tag or a second droplet id must not let the
# firewall go while another droplet keeps running.
survivor_protected(firewall) if {
	some droplet in input.terraform.resource_changes
	droplet.type == "digitalocean_droplet"
	actions_of(droplet) != ["delete"]
	protects(firewall, droplet)
}

# A droplet id the firewall lists must belong to a droplet this plan deletes.
id_deleted(id) if {
	some droplet in removed_resources
	droplet.type == "digitalocean_droplet"
	actions_of(droplet) == ["delete"]
	sprintf("%v", [object.get(before_of(droplet), "id", null)]) == sprintf("%v", [id])
}

protects(firewall, droplet) if {
	some view in droplet_views(droplet)
	some tag in values(before_of(firewall), "tags")
	tag != "protected"
	tag in values(view, "tags")
}

protects(firewall, droplet) if {
	some view in droplet_views(droplet)
	id := object.get(view, "id", null)
	id != null
	some listed in values(before_of(firewall), "droplet_ids")
	sprintf("%v", [listed]) == sprintf("%v", [id])
}

# The values a droplet has before and after the plan (after is null for a
# delete, and before is null for a create).
droplet_views(droplet) := [before_of(droplet), after_view(droplet)]

after_view(rc) := a if {
	a := object.get(object.get(rc, "change", {}), "after", {})
	is_object(a)
} else := {}

actions_of(rc) := object.get(object.get(rc, "change", {}), "actions", [])

# Resources this plan deletes, including the delete half of a replacement
# (either order). Creates, updates, reads and no-ops are not removals.
removed_resources contains rc if {
	some rc in input.terraform.resource_changes
	some action in object.get(object.get(rc, "change", {}), "actions", [])
	action == "delete"
}

# Types whose loss breaks the network, the access path or the project. The
# droplets (the connectors) are deliberately absent: replacing one is a normal,
# reviewed event.
protected_types := {
	"digitalocean_vpc",
	"digitalocean_project",
	"digitalocean_firewall",
	"twingate_remote_network",
	"aws_vpc",
	"aws_security_group",
}

protected(rc) if rc.type in protected_types

# Anything tagged `protected` (a DigitalOcean tag list, or an AWS tag map with
# that key), judged by the values being destroyed.
protected(rc) if "protected" in values(before_of(rc), "tags")

protected(rc) if {
	tags := object.get(before_of(rc), "tags", null)
	is_object(tags)
	"protected" in object.keys(tags)
}

before_of(rc) := b if {
	b := object.get(object.get(rc, "change", {}), "before", {})
	is_object(b)
} else := {}

# A list-valued field, or [] when it is missing or null (a real plan uses
# both for "nothing here").
values(obj, key) := v if {
	v := object.get(obj, key, [])
	v != null
} else := []

filled(obj, key) if count(values(obj, key)) > 0

filled_string(obj, key) if {
	v := object.get(obj, key, null)
	is_string(v)
	v != ""
}

# "The whole internet" is judged by prefix length, not by spelling: 0.0.0.0/0,
# ::/0, 0::/0, ::0/0, 0.0.0.0/00, the two halves 0.0.0.0/1 + 128.0.0.0/1 (or
# ::/1 + 8000::/1) and the four /2 ranges all count. Decision for issue #309
# (maintainer, 2026-10-30): an address with a prefix length of 8 or smaller
# (/0 through /8, IPv4 and IPv6, the same numeric rule) is world-open. Ranges
# narrower than /8 (/9, /16, /24, 2001:db8::/32) are named addresses the policy
# does not judge. Anything that does not parse as an address or a CIDR range,
# or that is not text, fails closed and counts as world-open too. A rule
# listing such an address can then never match an allowlist entry, which names
# exact strings.
wide_address(address) if not is_string(address)

wide_address(address) if {
	is_string(address)
	not valid_address(address)
}

wide_address(address) if {
	is_string(address)
	net.cidr_is_valid(address)
	to_number(split(address, "/")[1]) <= 8
}

# A CIDR range, or a bare address (a single host).
valid_address(address) if net.cidr_is_valid(address)

valid_address(address) if {
	not contains(address, "/")
	not contains(address, ":")
	net.cidr_is_valid(concat("/", [address, "32"]))
}

valid_address(address) if {
	not contains(address, "/")
	contains(address, ":")
	net.cidr_is_valid(concat("/", [address, "128"]))
}

world_open(rule) if {
	some address in values(rule, "source_addresses")
	wide_address(address)
}

world_open_outbound(rule) if {
	some address in values(rule, "destination_addresses")
	wide_address(address)
}

# Values that are not known until apply. A plan lists them in
# change.after_unknown, which mirrors change.after: true for a value, or for a
# whole list, and a list of objects (one per element) where only some fields
# are unknown. An unknown rule list or address list may resolve to the whole
# internet at apply time, so the policy cannot judge it: it is denied, and no
# allowlist entry covers it.
unknown_flag(v) if v == true

unknown_flag(v) if {
	is_array(v)
	some x in v
	x == true
}

after_unknown_of(rc) := u if {
	u := object.get(object.get(rc, "change", {}), "after_unknown", {})
	is_object(u)
} else := {}

# What is unknown in one rule list of a firewall: the whole list, a whole rule,
# or one of the named address fields of a rule.
unknown_in_rules(rc, list_key, address_keys) := (whole_list | whole_rules) | fields if {
	unknown_rules := object.get(after_unknown_of(rc), list_key, false)
	whole_list := {list_key | unknown_rules == true}
	whole_rules := {sprintf("%s[%d]", [list_key, i]) |
		is_array(unknown_rules)
		some i, el in unknown_rules
		el == true
	}
	fields := {sprintf("%s[%d].%s", [list_key, i, key]) |
		is_array(unknown_rules)
		some i, el in unknown_rules
		is_object(el)
		some key in address_keys
		unknown_flag(object.get(el, key, false))
	}
}

# The only sources the firewall module emits are tags. Any other kind of
# source, next to a tag or alone, makes the rule not tag-scoped.
non_tag_sources := {
	"source_addresses",
	"source_droplet_ids",
	"source_load_balancer_uids",
	"source_kubernetes_ids",
}

tag_scoped(rule) if {
	filled(rule, "source_tags")
	not has_non_tag_source(rule)
}

has_non_tag_source(rule) if {
	some key in non_tag_sources
	filled(rule, key)
}

rule_label(rule) := sprintf("%s/%s", [object.get(rule, "protocol", "?"), object.get(rule, "port_range", "?")])

# What the rule admits, for the message. Tags are not listed: they are the
# allowed kind, and a tag name is not what is wrong.
source_summary(rule) := concat(", ", sort(parts)) if {
	parts := array.concat(
		[sprintf("address %s", [a]) | some a in values(rule, "source_addresses")],
		array.concat(
			[sprintf("droplet id %v", [i]) | some i in values(rule, "source_droplet_ids")],
			array.concat(
				[sprintf("load balancer %v", [l]) | some l in values(rule, "source_load_balancer_uids")],
				[sprintf("kubernetes cluster %v", [k]) | some k in values(rule, "source_kubernetes_ids")],
			),
		),
	)
	count(parts) > 0
} else := "no source tag"

destination_summary(rule) := concat(", ", sort([sprintf("address %s", [a]) | some a in values(rule, "destination_addresses")]))

# AWS ingress from an address. A reference to a security group (or to the group
# itself) carries no CIDR and is the one admitted kind.
# One finding per rule (or inline block), holding every CIDR range it admits,
# so an allowlist entry must cover the whole rule, not one range of it.
aws_ingress_cidrs contains {
	"address": rc.address,
	"type": "aws_vpc_security_group_ingress_rule",
	"cidrs": cidrs,
	"protocol": aws_protocol(rc.change.after, "ip_protocol"),
	"port": aws_port(rc.change.after),
} if {
	some rc in changed_resources("aws_vpc_security_group_ingress_rule")
	cidrs := sort([cidr |
		some key in {"cidr_ipv4", "cidr_ipv6"}
		filled_string(rc.change.after, key)
		cidr := rc.change.after[key]
	])
	count(cidrs) > 0
}

aws_ingress_cidrs contains {
	"address": rc.address,
	"type": "aws_security_group_rule",
	"cidrs": cidrs,
	"protocol": aws_protocol(rc.change.after, "protocol"),
	"port": aws_port(rc.change.after),
} if {
	some rc in changed_resources("aws_security_group_rule")
	rc.change.after.type == "ingress"
	cidrs := listed_cidrs(rc.change.after)
	count(cidrs) > 0
}

aws_ingress_cidrs contains {
	"address": rc.address,
	"type": "aws_security_group",
	"cidrs": cidrs,
	"protocol": aws_protocol(block, "protocol"),
	"port": aws_port(block),
} if {
	some rc in changed_resources("aws_security_group")
	some block in values(rc.change.after, "ingress")
	cidrs := listed_cidrs(block)
	count(cidrs) > 0
}

listed_cidrs(obj) := sort([cidr |
	some key in {"cidr_blocks", "ipv6_cidr_blocks"}
	some cidr in values(obj, key)
])

aws_protocol(obj, key) := p if {
	p := object.get(obj, key, "")
	is_string(p)
} else := ""

# "443" for from_port = to_port = 443, "8000-8100" for a range, "" when the
# ports are not both numbers (so no entry can match).
aws_port(obj) := port if {
	from := object.get(obj, "from_port", null)
	to := object.get(obj, "to_port", null)
	is_number(from)
	is_number(to)
	port := port_text(from, to)
} else := ""

port_text(from, to) := sprintf("%d", [from]) if from == to

port_text(from, to) := sprintf("%d-%d", [from, to]) if from != to

# AWS settings that give a network, subnet or machine an IPv6 range or address.
ipv6_findings contains {"address": rc.address, "reason": "assign_generated_ipv6_cidr_block = true"} if {
	some rc in changed_resources("aws_vpc")
	rc.change.after.assign_generated_ipv6_cidr_block == true
}

ipv6_findings contains {"address": rc.address, "reason": sprintf("%s is set", [key])} if {
	some type, keys in {
		"aws_vpc": {"ipv6_cidr_block", "ipv6_ipam_pool_id"},
		"aws_subnet": {"ipv6_cidr_block"},
	}
	some rc in changed_resources(type)
	some key in keys
	filled_string(rc.change.after, key)
}

ipv6_findings contains {"address": rc.address, "reason": sprintf("%s = true", [key])} if {
	some rc in changed_resources("aws_subnet")
	some key in {"assign_ipv6_address_on_creation", "ipv6_native"}
	rc.change.after[key] == true
}

ipv6_findings contains {"address": rc.address, "reason": "ipv6_address_count is above zero"} if {
	some rc in changed_resources("aws_instance")
	rc.change.after.ipv6_address_count > 0
}

ipv6_findings contains {"address": rc.address, "reason": "ipv6_addresses is set"} if {
	some rc in changed_resources("aws_instance")
	filled(rc.change.after, "ipv6_addresses")
}

# Keep a sample of real plan inputs in Spacelift's policy workbench, so the
# input shape this policy assumes can be checked against a real run.
sample := true
