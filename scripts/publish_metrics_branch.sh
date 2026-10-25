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
#   3. skips the push when the remote picture is byte-identical;
#   4. otherwise pushes with --force-with-lease=REF:SHA, naming the value it
#      read, so a branch that moved in the meantime is not overwritten. A first run
#      expects the branch not to exist and creates it.
# No bare force, no merge, no history kept: the branch is a drop box for two files.
#
# Usage: publish_metrics_branch.sh BUNDLE_DIR
# Environment:
#   METRICS_REMOTE            remote URL (default https://github.com/$GITHUB_REPOSITORY.git)
#   METRICS_EXPECT_REPO       owner/name the snapshot must be for (default $GITHUB_REPOSITORY)
#   METRICS_MAX_AGE_HOURS     reject a bundle older than this (default 6; 0 = no limit)
#   GH_TOKEN                  optional; sent as an HTTP header through git's environment
#                             config, never on a command line and never written to disk

set -euo pipefail

die() {
  echo "publish_metrics_branch: $*" >&2
  exit "${2:-1}"
}

[ "$#" -eq 1 ] && [ -n "$1" ] || die "usage: $0 BUNDLE_DIR" 2
bundle=$1
branch=metrics
here=$(cd "$(dirname "$0")" && pwd)

repo=${METRICS_EXPECT_REPO:-${GITHUB_REPOSITORY:-}}
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "METRICS_EXPECT_REPO or GITHUB_REPOSITORY is not an owner/repository name" 2
remote=${METRICS_REMOTE:-https://github.com/$repo.git}
max_age=${METRICS_MAX_AGE_HOURS:-6}
[[ $max_age =~ ^[0-9]+$ ]] || die "METRICS_MAX_AGE_HOURS must be a whole number" 2

as_of=$(python3 -I "$here/gen_repo_metrics.py" --verify-bundle "$bundle" --expect-repo "$repo" --max-age-hours "$max_age" --print-as-of) \
  || die "the bundle failed validation; nothing was pushed"
[[ $as_of =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || die "unexpected as-of value"

if [ -n "${GH_TOKEN:-}" ]; then
  export GIT_CONFIG_COUNT=1
  export GIT_CONFIG_KEY_0="http.https://github.com/.extraheader"
  GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
  export GIT_CONFIG_VALUE_0
fi
export GIT_TERMINAL_PROMPT=0

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git -C "$work" init -q -b "$branch"
git -C "$work" remote add origin "$remote"
cp -- "$bundle/repo-growth.png" "$bundle/metrics-snapshot.json" "$work/"
printf '%s\n' "$as_of" >"$work/as-of.txt"

# The value the lease protects: what the remote branch is right now (empty if absent).
remote_sha=$(git -C "$work" ls-remote origin "refs/heads/$branch" | cut -f1)
if [ -n "$remote_sha" ]; then
  git -C "$work" fetch -q origin "refs/heads/$branch"
  if git -C "$work" show FETCH_HEAD:repo-growth.png 2>/dev/null | cmp -s - "$work/repo-growth.png"; then
    echo "publish_metrics_branch: the picture is unchanged (as of $as_of); nothing pushed"
    exit 0
  fi
fi

git -C "$work" add -- repo-growth.png metrics-snapshot.json as-of.txt
git -C "$work" -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit -q -m "Growth chart as of $as_of"
git -C "$work" push -q --force-with-lease="refs/heads/$branch:$remote_sha" origin "HEAD:refs/heads/$branch"
echo "publish_metrics_branch: pushed $branch (as of $as_of)"
