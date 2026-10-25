#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Publish the daily growth chart bundle to the `metrics` branch (issues #294, #296).
#
# The publish job of .github/workflows/growth-chart.yml runs this with
# contents: write. It never touches main, so main's branch protection is
# untouched. The branch is mutable, so it is never treated as authoritative:
#   1. the bundle is re-validated offline with gen_repo_metrics.py --verify-bundle,
#      which also checks that it descends from the committed baseline and from the
#      snapshot currently on the branch (identity fields equal, every earlier ledger
#      point kept in order; only today's point may be added or replaced);
#   2. the push is FAST-FORWARD ONLY: the commit is a child of the tip the render job
#      fetched (METRICS_EXPECTED_TIP, passed as a job output), and the script refuses
#      when the remote tip is anything else. A first run (empty tip, no branch) creates
#      an orphan root. The push is an exact compare-and-swap,
#      --force-with-lease=refs/heads/metrics:<expected tip> (empty on a first run: the
#      branch must not exist), after the script has proved the new commit's only
#      parent is exactly that tip. A branch that moved, was rewound to an ancestor,
#      or was deleted and recreated makes the push fail, and the run with it. The
#      lease can only succeed as a pure fast-forward from the expected tip; there is
#      no other force, no -f and no +ref;
#   3. nothing is pushed when the branch already holds exactly these three files,
#      byte-identical (a changed snapshot or as-of file is published even when the
#      picture did not change).
# History is kept on purpose: one small commit per day, which also makes a bad
# publish visible and revertible. A deliberate reset (a newer baseline, a lost
# ledger) is a separate, reviewed action: delete the branch, and the next run starts
# a ledger afresh.
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
#   METRICS_EXPECTED_TIP      required: the metrics commit the render job fetched (40 hex),
#                             or empty when it found no branch
#   METRICS_BASELINE          committed baseline snapshot (default docs/wiki/.metrics-snapshot.json)
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

# The tip the render job read. It must be set (empty means "no branch yet") and well formed.
[ "${METRICS_EXPECTED_TIP+set}" = set ] || die "METRICS_EXPECTED_TIP must be set (empty when the branch did not exist)" 2
expected_tip=$METRICS_EXPECTED_TIP
[[ -z $expected_tip || $expected_tip =~ ^[0-9a-f]{40}$ ]] || die "the expected tip is not a 40-character lowercase commit id" 2
baseline=${METRICS_BASELINE:-$here/../docs/wiki/.metrics-snapshot.json}

repo=${METRICS_EXPECT_REPO:-${GITHUB_REPOSITORY:-}}
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "METRICS_EXPECT_REPO or GITHUB_REPOSITORY is not an owner/repository name" 2
remote=${METRICS_REMOTE:-https://github.com/$repo.git}
max_age=${METRICS_MAX_AGE_HOURS:-6}
[[ $max_age =~ ^[0-9]+$ ]] || die "METRICS_MAX_AGE_HOURS must be a whole number" 2

# Take the token out of the environment now; it is handed to git commands one at a time below.
token=${GH_TOKEN:-}
unset GH_TOKEN GITHUB_TOKEN

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

# What the remote branch is right now, compared with what the render job read.
remote_sha=$(remote_git ls-remote origin "refs/heads/$branch" | cut -f1)
if [ -z "$expected_tip" ]; then
  [ -z "$remote_sha" ] || die "the metrics branch exists ($remote_sha) but the render job saw none; refusing to start a second history"
else
  [ "$remote_sha" = "$expected_tip" ] || die "the metrics branch moved since it was read (expected $expected_tip, found ${remote_sha:-none}); nothing was pushed"
fi

previous=()
if [ -n "$expected_tip" ]; then
  remote_git fetch -q --no-tags origin "refs/heads/$branch"
  [ "$(git -C "$work" rev-parse FETCH_HEAD)" = "$expected_tip" ] || die "fetched a different commit than expected; nothing was pushed"
  size=$(git -C "$work" cat-file -s FETCH_HEAD:metrics-snapshot.json 2>/dev/null || echo 0)
  [ "$size" -gt 0 ] && [ "$size" -le 262144 ] || die "the snapshot on the branch is missing or over the size cap"
  git -C "$work" cat-file blob FETCH_HEAD:metrics-snapshot.json >"$work/previous.json"
  previous=(--previous "$work/previous.json")
fi

as_of=$(env -u GH_TOKEN python3 -I "$here/gen_repo_metrics.py" --verify-bundle "$bundle" --expect-repo "$repo" \
  --max-age-hours "$max_age" --baseline "$baseline" --root / ${previous[@]+"${previous[@]}"} --print-as-of) \
  || die "the bundle failed validation; nothing was pushed"
[[ $as_of =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || die "unexpected as-of value"

# Build the commit in a clean tree: a child of the tip, or an orphan root on a first run.
if [ -n "$expected_tip" ]; then
  git -C "$work" checkout -q -B "$branch" FETCH_HEAD
  same=1
  [ "$(git -C "$work" ls-tree -r --name-only HEAD | sort | tr '\n' ' ')" = "as-of.txt metrics-snapshot.json repo-growth.png " ] || same=0
  new_dir=$(mktemp -d)
  trap 'rm -rf "$work" "$new_dir"' EXIT
  cp -- "$bundle/repo-growth.png" "$bundle/metrics-snapshot.json" "$new_dir/"
  printf '%s\n' "$as_of" >"$new_dir/as-of.txt"
  for f in repo-growth.png metrics-snapshot.json as-of.txt; do
    git -C "$work" show "HEAD:$f" 2>/dev/null | cmp -s - "$new_dir/$f" || same=0
  done
  if [ "$same" = 1 ]; then
    echo "publish_metrics_branch: everything is unchanged (as of $as_of); nothing pushed"
    exit 0
  fi
  git -C "$work" rm -q -r --ignore-unmatch -- . >/dev/null
  cp -- "$new_dir/repo-growth.png" "$new_dir/metrics-snapshot.json" "$new_dir/as-of.txt" "$work/"
else
  cp -- "$bundle/repo-growth.png" "$bundle/metrics-snapshot.json" "$work/"
  printf '%s\n' "$as_of" >"$work/as-of.txt"
fi

rm -f -- "$work/previous.json"
git -C "$work" add -- repo-growth.png metrics-snapshot.json as-of.txt
git -C "$work" -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit -q -m "Growth chart as of $as_of"

# Prove the shape of what is about to be pushed: its only parent is exactly the expected
# tip (a first run has no parent at all).
parents=$(git -C "$work" rev-parse "HEAD^@" 2>/dev/null | tr '\n' ' ' | sed 's/ $//')
[ "$parents" = "$expected_tip" ] || die "the new commit's parent ($parents) is not the expected tip; nothing was pushed"

# An exact lease, not a plain push: the push succeeds only if the remote branch is STILL the
# expected tip (or still absent on a first run), so it can only be a fast-forward from there.
# A plain push would also accept a remote that was rewound to an ancestor in the meantime.
if [ -n "$expected_tip" ]; then
  remote_git push -q --force-with-lease="refs/heads/metrics:$expected_tip" origin HEAD:refs/heads/metrics
else
  remote_git push -q --force-with-lease="refs/heads/metrics:" origin HEAD:refs/heads/metrics
fi
echo "publish_metrics_branch: pushed refs/heads/metrics (as of $as_of)"
