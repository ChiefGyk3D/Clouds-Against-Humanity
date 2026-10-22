#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# The pipeline stages from example-wordpress-ci.yml as plain local steps. No cloud, no account.
# "Deploy" copies into .state/ next to the lab; "current" is a pointer file, as it would be a
# symlink on a server.
#
#   ./ci_local.sh all        lint, policy, build, deploy to staging, smoke test, promote to production
#   ./ci_local.sh negative   build a deliberately bad copy at run time and show the policy check refuse it
#   ./ci_local.sh rollback   point production back at the previous release
#   ./ci_local.sh status     which release each environment points at
#   ./ci_local.sh clean      delete .state/
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB="$(dirname "$HERE")"
STATE="$LAB/.state"
CHECK=(python3 -I "$HERE/ci_policy_check.py")

step() { printf '\n== %s\n' "$*"; }
pointer() { cat "$STATE/$1/current" 2>/dev/null || echo "(none)"; }

lint() {
  step "lint"
  bash -n "$LAB/lab.sh" && echo "lab.sh: syntax ok"
  python3 -I -m py_compile "$LAB/app/app.py" "$HERE/ci_policy_check.py" && echo "python: syntax ok"
  if command -v php >/dev/null 2>&1; then
    find "$LAB/site" -name '*.php' -print0 | xargs -0 -n1 php -l
  else
    echo "php not installed here: skipping php -l (the CI job runs it in a php container)"
  fi
}
policy() {
  step "policy (the reviewer's rules)"
  "${CHECK[@]}" --workflow "$HERE/example-wordpress-ci.yml" --site "$LAB/site"
}
build() {
  step "build one artifact"
  mkdir -p "$STATE/artifacts"
  tar -czf "$STATE/artifacts/release.tar.gz" -C "$LAB" site
  (cd "$STATE/artifacts" && sha256sum release.tar.gz > release.tar.gz.sha256)
  RELEASE="$(cut -c1-12 "$STATE/artifacts/release.tar.gz.sha256")"
  echo "release id: $RELEASE"
}
deploy() { # deploy ENV : unpack the SAME artifact into releases/<id>, then switch the pointer
  step "deploy to $1"
  (cd "$STATE/artifacts" && sha256sum -c release.tar.gz.sha256)
  mkdir -p "$STATE/$1/releases/$RELEASE"
  tar -xzf "$STATE/artifacts/release.tar.gz" -C "$STATE/$1/releases/$RELEASE"
  [ -f "$STATE/$1/current" ] && cp "$STATE/$1/current" "$STATE/$1/previous"
  echo "$RELEASE" > "$STATE/$1/current"
  echo "$1 now points at $(pointer "$1")"
}
smoke() { # smoke ENV : the release the pointer names must exist and pass the same site rules
  step "smoke test on $1"
  local id; id="$(pointer "$1")"
  [ -f "$STATE/$1/releases/$id/site/composer.json" ] || { echo "SMOKE FAIL: release $id has no composer.json"; return 1; }
  "${CHECK[@]}" --site "$STATE/$1/releases/$id/site"
}

case "${1:-}" in
  all)
    lint; policy; build; deploy staging; smoke staging
    echo; echo "(a person approves here in a real pipeline: the production environment has required reviewers)"
    deploy production
    smoke production || { echo "smoke failed: rolling back"; exec "$0" rollback; }
    ;;
  negative)
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    cp -r "$LAB/site" "$tmp/site"
    # Break the site three ways: a floating version, a secret as a literal, file changes allowed.
    sed -i 's/"2.3.1"/"^2.3"/' "$tmp/site/composer.json"
    sed -i "s/define('DB_PASSWORD', env_required('DB_PASSWORD'));/define('DB_PASSWORD', 'literal-for-the-demo');/" "$tmp/site/config/application.php"
    sed -i "s/'DISALLOW_FILE_MODS', true/'DISALLOW_FILE_MODS', false/" "$tmp/site/config/application.php"
    # Break the workflow four ways: an unpinned action, pull_request_target, inherited secrets, no permissions.
    {
      echo "name: bad"; echo "on:"; echo "  pull_request_target:"
      echo "jobs:"; echo "  a:"; echo "    uses: some-owner/some-repo/.github/workflows/x.yml@main"; echo "    secrets: inherit"
    } > "$tmp/bad.yml"
    "${CHECK[@]}" --workflow "$tmp/bad.yml" --site "$tmp/site" && { echo "UNEXPECTED: bad input passed"; exit 1; }
    echo "(exit 1 is the point: the bad copy was refused)" ;;
  rollback)
    [ -f "$STATE/production/previous" ] || { echo "nothing to roll back to"; exit 1; }
    cp "$STATE/production/previous" "$STATE/production/current"
    echo "production now points at $(pointer production)" ;;
  status) echo "staging: $(pointer staging)   production: $(pointer production)" ;;
  clean) rm -rf "$STATE" ;;
  *) sed -n '3,12p' "$0"; exit 2 ;;
esac
