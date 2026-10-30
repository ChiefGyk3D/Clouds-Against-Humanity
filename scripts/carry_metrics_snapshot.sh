#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Carry the previously published growth snapshot out of the `metrics` branch (issue #296).
#
# The render job runs this before it draws. The branch is mutable, so nothing read from
# it is trusted: this script only gets one file out, safely, and prints the commit it
# read, so the publish job can insist on pushing a child of exactly that commit.
#
# Usage: carry_metrics_snapshot.sh REMOTE_URL DEST_DIR      (stdout: tip=<sha or empty>)
#   - the branch does not exist (ls-remote exit 2): a first run; DEST_DIR stays empty, tip=
#   - any other ls-remote or fetch failure: exit non-zero, so a network error can never
#     look like a first run and start a ledger from nothing
#   - the branch exists: metrics-snapshot.json must be a regular file (not a symlink); its
#     size is read from git WITHOUT writing it (git cat-file -s) and refused over the cap
#     before any byte reaches DEST_DIR; the content is then streamed through head -c cap+1
#     into a private temp file, re-checked, and only then moved into DEST_DIR
# The strict JSON checks (duplicate keys, schema, hashes, baseline match, staleness) are
# done afterwards by gen_repo_metrics.py --refresh, which loads the file with load_carried.
# The fetch lands in a throwaway repository, deleted on exit; no token is used (public repo).

set -euo pipefail

die() {
  echo "carry_metrics_snapshot: $*" >&2
  exit "${2:-1}"
}

[ "$#" -eq 2 ] && [ -n "$1" ] && [ -n "$2" ] || die "usage: $0 REMOTE_URL DEST_DIR" 2
remote=$1
dest=$2
cap=${CARRY_MAX_BYTES:-262144} # MAX_SNAPSHOT_BYTES in gen_repo_metrics.py
[[ $cap =~ ^[0-9]+$ ]] || die "CARRY_MAX_BYTES must be a whole number" 2
export GIT_TERMINAL_PROMPT=0

mkdir -p -- "$dest"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

rc=0
listing=$(git ls-remote --exit-code --heads "$remote" metrics) || rc=$?
if [ "$rc" -eq 2 ]; then
  echo "carry_metrics_snapshot: no metrics branch yet; the ledger starts today" >&2
  echo "tip="
  exit 0
elif [ "$rc" -ne 0 ]; then
  die "could not read the metrics branch (ls-remote exit $rc)" "$rc"
fi
[ -n "$listing" ] || die "ls-remote returned nothing for an existing branch"

git -C "$work" init -q
git -C "$work" fetch -q --depth=1 --no-tags "$remote" refs/heads/metrics
tip=$(git -C "$work" rev-parse FETCH_HEAD)
[[ $tip =~ ^[0-9a-f]{40}$ ]] || die "unexpected commit id"

entry=$(git -C "$work" ls-tree FETCH_HEAD -- metrics-snapshot.json)
[ -n "$entry" ] || die "the metrics branch has no metrics-snapshot.json"
mode=${entry%% *}
[ "$mode" = 100644 ] || [ "$mode" = 100755 ] || die "metrics-snapshot.json is not a regular file (mode $mode)"

size=$(git -C "$work" cat-file -s "FETCH_HEAD:metrics-snapshot.json")
[[ $size =~ ^[0-9]+$ ]] || die "could not read the size of metrics-snapshot.json"
[ "$size" -le "$cap" ] || die "metrics-snapshot.json is larger than $cap bytes ($size); refusing it"

staged="$work/snapshot.json"
git -C "$work" cat-file blob "FETCH_HEAD:metrics-snapshot.json" | head -c "$((cap + 1))" >"$staged"
[ "$(wc -c <"$staged")" -le "$cap" ] || die "metrics-snapshot.json is larger than $cap bytes; refusing it"
mv -- "$staged" "$dest/metrics-snapshot.json"
echo "tip=$tip"
