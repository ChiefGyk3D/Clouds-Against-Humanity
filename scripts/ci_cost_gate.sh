#!/usr/bin/env bash
# The cost gate as CI runs it.
#
# On a pull request the gate is given the base branch's docs/stages/approved.json
# (--base-approved), so the phase lifecycle is checked against history: a done
# phase cannot be edited or switched back on, no phase can be deleted, and a
# change of the effective ceiling is printed. One file cannot show any of that.
#
# The base is the tip of the pull request's base branch, fetched shallow. The
# checkout of a pull request is the merge of that tip and the head, so comparing
# the two is exactly what merging changes. If the base cannot be fetched or does
# not contain the file, this FAILS: a check that quietly does not run is the
# thing this script exists to prevent.
#
# On other events (a push to main, a manual run, a local run) there is no base to
# compare with; the plain gate runs and the reason is printed.
#
#   bash scripts/ci_cost_gate.sh [extra cost_check.py arguments]
#
# Environment: GITHUB_EVENT_NAME and GITHUB_BASE_REF (set by GitHub Actions),
# PYTHON (default python), CAH_BASE_REMOTE (default origin).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${PYTHON:-python}"
remote="${CAH_BASE_REMOTE:-origin}"
event="${GITHUB_EVENT_NAME:-}"
gate=("$python_bin" -I "$here/cost_check.py" --root .)

case "$event" in
pull_request | pull_request_target)
  base_ref="${GITHUB_BASE_REF:-}"
  if [ -z "$base_ref" ]; then
    echo "ci-cost-gate: FAIL: $event without GITHUB_BASE_REF; cannot find the base branch" >&2
    exit 1
  fi
  if ! git fetch --no-tags --depth=1 "$remote" "refs/heads/${base_ref}" >&2; then
    echo "ci-cost-gate: FAIL: could not fetch ${remote}/${base_ref}; the lifecycle check needs the base's approved.json" >&2
    exit 1
  fi
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  if ! git show "FETCH_HEAD:docs/stages/approved.json" >"$tmp/approved.json"; then
    echo "ci-cost-gate: FAIL: ${base_ref} has no docs/stages/approved.json to compare with" >&2
    exit 1
  fi
  echo "ci-cost-gate: comparing with ${base_ref} ($(git rev-parse --short FETCH_HEAD))"
  "${gate[@]}" --base-approved "$tmp/approved.json" "$@"
  ;;
*)
  echo "ci-cost-gate: event '${event:-none}' has no base branch; lifecycle check skipped, plain gate only"
  "${gate[@]}" "$@"
  ;;
esac
