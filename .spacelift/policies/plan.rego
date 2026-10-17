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
#   - an AWS security group rule that admits a CIDR range (IPv4 or IPv6). The
#     AWS firewall module admits only a reference to the group itself.
#   - a droplet with ipv6 turned on, or an AWS VPC, subnet or instance that
#     takes an IPv6 range or address. IPv6 stays closed in this repository.
#
# Pure deletes and no-ops are ignored: removing a rule never opens anything.
#
# The escape hatch is this file. A deliberate inbound rule is allowed only by
# adding the exact resource address of the firewall or rule to
# inbound_allowlist below, in a pull request that gets reviewed. Nothing a plan
# can set itself (a stack label, an environment variable, a field in the plan)
# is read, so a branch cannot grant its own exception. The IPv6 checks have no
# escape hatch.
#
# Two guards turn the "locked and manual" convention into a rule (issue #92):
#
#   - Destroy guard: a plan that deletes, or replaces, a digitalocean_vpc,
#     digitalocean_project, digitalocean_firewall, twingate_remote_network,
#     aws_vpc, aws_security_group, or anything tagged `protected`, is denied.
#     Droplets are deliberately not protected: a connector replace is a normal,
#     reviewed event. Escape hatch: destroy_allowlist, same rule as above.
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

# Exact resource addresses (as shown in the plan, for example
# `module.fw.digitalocean_firewall.this`) whose inbound rules are allowed even
# though they are not tag-scoped. Empty by default. Every entry needs a
# threat-model note (docs/wiki/Threat-Model.md) and a pull request review that
# names the port, the source and the reason. Remove the entry when the rule
# goes away.
inbound_allowlist := set()

# Exact resource addresses whose deletion (or replacement) is allowed even
# though the resource is protected. Empty by default. Same rule as above: a
# pull request that names the address and the reason, reviewed, then the new
# body pasted into Spacelift. Remove the entry once the change has applied.
destroy_allowlist := set()

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	not allowlisted(rc)
	some rule in rc.change.after.inbound_rule
	world_open(rule)
	msg := sprintf(
		"%s: inbound rule %s opens the port to the whole internet (%s). Inbound on core tags must come from a tag only.",
		[rc.address, rule_label(rule), source_summary(rule)],
	)
}

deny contains msg if {
	some rc in changed_resources("digitalocean_firewall")
	not allowlisted(rc)
	some rule in rc.change.after.inbound_rule
	not world_open(rule)
	not tag_scoped(rule)
	msg := sprintf(
		"%s: inbound rule %s is not tag-scoped (%s). Inbound on core tags must come from a tag only.",
		[rc.address, rule_label(rule), source_summary(rule)],
	)
}

deny contains msg if {
	some entry in aws_ingress_cidrs
	not entry.address in inbound_allowlist
	msg := sprintf(
		"%s: %s admits inbound traffic from %s. AWS ingress here may only reference a security group, never a CIDR range.",
		[entry.address, entry.type, entry.cidr],
	)
}

deny contains msg if {
	some rc in removed_resources
	protected(rc)
	not rc.address in destroy_allowlist
	msg := sprintf(
		"%s: this plan deletes (or replaces) a protected %s. A human must add the address to destroy_allowlist in .spacelift/policies/plan.rego, in a pull request, before it can be applied.",
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

allowlisted(rc) if rc.address in inbound_allowlist

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

world_addresses := {"0.0.0.0/0", "::/0"}

world_open(rule) if {
	some address in values(rule, "source_addresses")
	address in world_addresses
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

# AWS ingress from an address. A reference to a security group (or to the group
# itself) carries no CIDR and is the one admitted kind.
aws_ingress_cidrs contains {"address": rc.address, "type": "aws_vpc_security_group_ingress_rule", "cidr": cidr} if {
	some rc in changed_resources("aws_vpc_security_group_ingress_rule")
	some key in {"cidr_ipv4", "cidr_ipv6"}
	filled_string(rc.change.after, key)
	cidr := rc.change.after[key]
}

aws_ingress_cidrs contains {"address": rc.address, "type": "aws_security_group_rule", "cidr": cidr} if {
	some rc in changed_resources("aws_security_group_rule")
	rc.change.after.type == "ingress"
	some key in {"cidr_blocks", "ipv6_cidr_blocks"}
	some cidr in values(rc.change.after, key)
}

aws_ingress_cidrs contains {"address": rc.address, "type": "aws_security_group", "cidr": cidr} if {
	some rc in changed_resources("aws_security_group")
	some block in values(rc.change.after, "ingress")
	some key in {"cidr_blocks", "ipv6_cidr_blocks"}
	some cidr in values(block, key)
}

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
