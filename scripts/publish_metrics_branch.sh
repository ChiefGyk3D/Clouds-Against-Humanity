#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Publish the daily growth chart bundle to the orphan `metrics` branch (issue #294).
#
# The publish job of .github/workflows/growth-chart.yml runs this with
# contents: write. It never touches main, so main's branch protection is
# untouched. What it does:
#   1. re-validates the bundle offline with gen_repo_metrics.py --verify-bundle
#      (exact two files, size caps, real PNG, matching hashes, only per-day counts,
#      the expected repository, a fresh time stamp), because the bundle crossed an
#      artifact boundary;
#   2. builds a fresh one-commit orphan history holding repo-growth.png,
#      metrics-snapshot.json and as-of.txt;
#   3. skips the push only when the remote branch holds exactly these three files,
#      each byte-identical (a changed snapshot or as-of file is published even
#      when the picture did not change);
#   4. otherwise pushes with --force-with-lease=REF:SHA, naming the value it
#      read, so a branch that moved in the meantime is not overwritten. A first run
#      expects the branch not to exist and creates it.
# No bare force, no merge, no history kept: the branch is a drop box for three files.
#
# Residual risk, stated plainly: GITHUB_TOKEN cannot be limited to one branch, so
# the publish job's token can write the whole repository. This script limits what
# IT does (one hard-coded refspec, refs/heads/metrics, refused for anything else;
# the token reaches only the three git commands that talk to the remote, scoped
# to the remote URL, and never the validator), but it is not access control. The
# control is a repository ruleset: see docs/wiki/Repository-Growth.md.
#
# Usage: publish_metrics_branch.sh BUNDLE_DIR
# Environment:
#   METRICS_REMOTE            remote URL (default https://github.com/$GITHUB_REPOSITORY.git)
#   METRICS_EXPECT_REPO       owner/name the snapshot must be for (default $GITHUB_REPOSITORY)
#   METRICS_MAX_AGE_HOURS     reject a bundle older than this (default 6; 0 = no limit)
#   GH_TOKEN                  optional; sent as an HTTP header scoped to the remote URL,
#                             through git's environment config on the remote commands
#                             only; never on a command line, never written to disk,
#                             and removed from the environment before anything else runs
#   METRICS_BRANCH            test seam; anything but "metrics" is refused

set -euo pipefail

die() {
  echo "publish_metrics_branch: $*" >&2
  exit "${2:-1}"
}

[ "$#" -eq 1 ] && [ -n "$1" ] || die "usage: $0 BUNDLE_DIR" 2
bundle=$1
# The only ref this script may ever write. The check is on the value, not a hope:
# a different, empty or oddly spelled name stops here, before any network call.
branch=${METRICS_BRANCH-metrics}
[ "$branch" = metrics ] || die "refusing to publish to '$branch': only refs/heads/metrics is allowed" 2
here=$(cd "$(dirname "$0")" && pwd)

repo=${METRICS_EXPECT_REPO:-${GITHUB_REPOSITORY:-}}
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "METRICS_EXPECT_REPO or GITHUB_REPOSITORY is not an owner/repository name" 2
remote=${METRICS_REMOTE:-https://github.com/$repo.git}
max_age=${METRICS_MAX_AGE_HOURS:-6}
[[ $max_age =~ ^[0-9]+$ ]] || die "METRICS_MAX_AGE_HOURS must be a whole number" 2

# Take the token out of the environment now; it is handed to git commands one at a time below.
token=${GH_TOKEN:-}
unset GH_TOKEN GITHUB_TOKEN

as_of=$(python3 -I "$here/gen_repo_metrics.py" --verify-bundle "$bundle" --expect-repo "$repo" --max-age-hours "$max_age" --print-as-of) \
  || die "the bundle failed validation; nothing was pushed"
[[ $as_of =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || die "unexpected as-of value"

export GIT_TERMINAL_PROMPT=0
[[ $remote != http://* ]] || die "refusing a plain http remote" 2

# Run git against the remote with the credential header set for this one command
# only, and scoped to the exact remote URL. Local commands never get it.
remote_git() {
  if [ -n "$token" ]; then
    GIT_CONFIG_COUNT=1 \
      GIT_CONFIG_KEY_0="http.${remote}.extraheader" \
      GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$token" | base64 -w0)" \
      git -C "$work" "$@"
  else
    git -C "$work" "$@"
  fi
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git -C "$work" init -q -b "$branch"
git -C "$work" remote add origin "$remote"
cp -- "$bundle/repo-growth.png" "$bundle/metrics-snapshot.json" "$work/"
printf '%s\n' "$as_of" >"$work/as-of.txt"

# The value the lease protects: what the remote branch is right now (empty if absent).
remote_sha=$(remote_git ls-remote origin "refs/heads/$branch" | cut -f1)
if [ -n "$remote_sha" ]; then
  remote_git fetch -q origin "refs/heads/$branch"
  # Skip only when the remote tree is exactly these three files, byte for byte.
  same=1
  [ "$(git -C "$work" ls-tree -r --name-only FETCH_HEAD | sort | tr '\n' ' ')" = "as-of.txt metrics-snapshot.json repo-growth.png " ] || same=0
  for f in repo-growth.png metrics-snapshot.json as-of.txt; do
    git -C "$work" show "FETCH_HEAD:$f" 2>/dev/null | cmp -s - "$work/$f" || same=0
  done
  if [ "$same" = 1 ]; then
    echo "publish_metrics_branch: everything is unchanged (as of $as_of); nothing pushed"
    exit 0
  fi
fi

git -C "$work" add -- repo-growth.png metrics-snapshot.json as-of.txt
git -C "$work" -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit -q -m "Growth chart as of $as_of"
remote_git push -q --force-with-lease="refs/heads/metrics:$remote_sha" origin HEAD:refs/heads/metrics
echo "publish_metrics_branch: pushed refs/heads/metrics (as of $as_of)"
