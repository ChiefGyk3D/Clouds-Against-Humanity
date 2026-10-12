# Git push policy for every stack in this repository (cah-00-foundation,
# cah-10-access, and later ones). Explained in docs/spacelift-secrets.md,
# section 9, and on the Spacelift wiki page.
#
# Spacelift does not read this file from the repository. Create a push policy
# in Spacelift with this body and attach it to each stack (or give it the
# label autoattach:cah, the same label the Doppler context uses). The tests
# next to it run in CI on every pull request.
#
# What it decides:
#
#   - A push to the stack's tracked branch that changes a file the stack's
#     plan depends on starts a tracked run. A human still confirms the apply;
#     autodeploy stays off.
#   - Nothing else starts a run. In particular, no event ever proposes a run.
#     A proposed run is the plan Spacelift makes for a pull request, and in
#     this repository it gets no credentials by design (the Doppler hook skips
#     it), so it can only fail at the provider and post a red check to the
#     pull request. Pull requests are covered instead by `tofu test` with
#     mocked providers in GitHub Actions. Never proposing also means no pull
#     request's code runs in Spacelift next to the Doppler context, which is
#     threat T3 in the threat model.
#   - Forks need nothing here: Spacelift only runs a fork's pull request when
#     a push policy defines `allow_fork`, and this one never does.
#
# Why the rules do not test input.pull_request: a merge to the tracked branch
# can arrive with input.pull_request set (Spacelift's own "PRs only" example
# tracks merges that way). Ignoring every event that carries a pull request
# would stop merges from deploying. The branch and the changed files are what
# decide.

package spacelift

import rego.v1

# Paths outside the stack's own root that still change what its plan does:
# shared modules, the Spacelift hook that loads secrets, and the Spacelift
# runtime configuration. A change here starts a run on every stack; a stack
# that does not use the changed module plans "no changes", which costs a
# minute and nothing else.
shared_prefixes := {"modules/", "scripts/spacelift/", ".spacelift/"}

track if {
	on_tracked_branch
	not is_tag
	affected
}

# Spacelift's rule names: `ignore` wins over `track` when both hold. Here
# ignore is exactly "not track", so every event has one clear outcome and the
# tests can say which.
ignore if not track

# Deliberately absent: `propose` and `allow_fork`. See the header.

on_tracked_branch if {
	input.push.branch == input.stack.branch
}

is_tag if {
	input.push.tag != ""
}

affected if {
	some path in input.push.affected_files
	in_stack_root(path)
}

affected if {
	some path in input.push.affected_files
	some prefix in shared_prefixes
	startswith(path, prefix)
}

# The project root is compared as a directory, with a trailing slash, so a
# root of "stacks/10-access" does not also match "stacks/10-access-old/". An
# empty root means the repository root, where every file is the stack's.
in_stack_root(_) if {
	trim_suffix(input.stack.project_root, "/") == ""
}

in_stack_root(path) if {
	root := trim_suffix(input.stack.project_root, "/")
	root != ""
	startswith(path, concat("", [root, "/"]))
}

# Keep a sample of real inputs in Spacelift's policy workbench (private to the
# account, kept for a limited time), so the input shape this policy assumes can
# be checked against a real event.
sample := true
