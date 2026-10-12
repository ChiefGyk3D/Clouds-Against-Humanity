# Tests for push.rego. Run with `opa test .spacelift/policies -v`; CI runs
# them on every pull request through git-your-ship-together's tofu-ci.yml.
#
# Each test builds the smallest input that the policy reads: the push (branch,
# tag, changed files), the stack (tracked branch, project root) and, where it
# matters, a pull request.

package spacelift_test

import rego.v1

import data.spacelift

stack_10 := {"branch": "main", "project_root": "stacks/10-access"}

event(branch, files) := {
	"push": {"branch": branch, "tag": "", "affected_files": files},
	"pull_request": null,
	"stack": stack_10,
}

pr_event(branch, files) := object.union(
	event(branch, files),
	{"pull_request": {"action": "opened", "head_owner": "ChiefGyk3D", "labels": []}},
)

# The reason the policy exists: a pull request that only changes docs posted a
# red proposed-run check. Nothing may run for it.
test_docs_only_pull_request_starts_nothing if {
	input_doc := pr_event("claude/wiki", ["docs/wiki/Home.md", "README.md"])
	not spacelift.track with input as input_doc
	not spacelift.propose with input as input_doc
	spacelift.ignore with input as input_doc
}

# Even a pull request that changes the stack itself is not planned in
# Spacelift: it would get no credentials and fail. CI's `tofu test` covers it.
test_pull_request_touching_the_stack_is_not_proposed if {
	input_doc := pr_event("feature/firewall", ["stacks/10-access/main.tf"])
	not spacelift.propose with input as input_doc
	not spacelift.track with input as input_doc
	spacelift.ignore with input as input_doc
}

test_merge_changing_the_stack_is_tracked if {
	input_doc := event("main", ["stacks/10-access/main.tf"])
	spacelift.track with input as input_doc
	not spacelift.ignore with input as input_doc
}

# A merge can arrive with pull_request set. It must still deploy.
test_merge_carrying_its_pull_request_is_still_tracked if {
	input_doc := pr_event("main", ["stacks/10-access/variables.tf"])
	spacelift.track with input as input_doc
	not spacelift.ignore with input as input_doc
}

test_merge_changing_only_docs_is_ignored if {
	input_doc := event("main", ["docs/wiki/Spacelift.md", "README.md"])
	not spacelift.track with input as input_doc
	spacelift.ignore with input as input_doc
}

test_merge_changing_a_shared_module_is_tracked if {
	spacelift.track with input as event("main", ["modules/firewall/main.tf"])
}

test_merge_changing_the_secrets_hook_is_tracked if {
	spacelift.track with input as event("main", ["scripts/spacelift/doppler-env.sh"])
}

test_merge_changing_the_runtime_config_is_tracked if {
	spacelift.track with input as event("main", [".spacelift/config.yml"])
}

test_merge_changing_another_stack_only_is_ignored if {
	spacelift.ignore with input as event("main", ["stacks/00-foundation/main.tf"])
}

# The root is compared as a directory, not a string prefix.
test_sibling_directory_with_a_longer_name_is_not_the_stack if {
	spacelift.ignore with input as event("main", ["stacks/10-access-old/main.tf"])
}

test_project_root_with_a_trailing_slash_still_matches if {
	input_doc := object.union(
		event("main", ["stacks/10-access/main.tf"]),
		{"stack": {"branch": "main", "project_root": "stacks/10-access/"}},
	)
	spacelift.track with input as input_doc
}

test_empty_project_root_means_every_file if {
	input_doc := object.union(
		event("main", ["anything.tf"]),
		{"stack": {"branch": "main", "project_root": ""}},
	)
	spacelift.track with input as input_doc
}

test_push_to_another_branch_starts_nothing if {
	input_doc := event("experiment", ["stacks/10-access/main.tf"])
	not spacelift.track with input as input_doc
	not spacelift.propose with input as input_doc
	spacelift.ignore with input as input_doc
}

test_tag_push_is_ignored if {
	input_doc := object.union(
		event("main", ["stacks/10-access/main.tf"]),
		{"push": {"branch": "main", "tag": "v1.0.0", "affected_files": ["stacks/10-access/main.tf"]}},
	)
	spacelift.ignore with input as input_doc
}

test_a_push_with_no_changed_files_is_ignored if {
	spacelift.ignore with input as event("main", [])
}

# Forks run only where a push policy defines allow_fork. This one never may.
test_policy_never_allows_forks if {
	not spacelift.allow_fork with input as pr_event("main", ["stacks/10-access/main.tf"])
}
