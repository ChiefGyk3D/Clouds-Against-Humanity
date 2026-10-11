#!/usr/bin/env bash
# Publish docs/wiki/*.md to this repository's GitHub wiki.
#
# The pages are written and reviewed in the main repository (so pull requests,
# secret scanning and review cover them), and this script copies them to the
# wiki. Edits made in the wiki editor are overwritten on the next publish.
#
# Usage, from anywhere inside a clone of this repository:
#   scripts/publish-wiki.sh            copy, commit and push
#   scripts/publish-wiki.sh --dry-run  show what would change, push nothing
#
# One-time prerequisite: GitHub only creates the wiki's git repository after
# the first page exists. Open the repository's Wiki tab, create any page, save
# it, then run this script.
#
# What it changes in each page: relative links such as (Twingate.md) or
# (Twingate.md#section) become (Twingate) and (Twingate#section), which is how
# the wiki addresses pages. Absolute links are left alone. Pages that exist in
# the wiki but not in docs/wiki are listed and left in place, never deleted.

set -euo pipefail

dry_run=false
case "${1:-}" in
  "") ;;
  --dry-run) dry_run=true ;;
  *)
    echo "usage: $0 [--dry-run]" >&2
    exit 2
    ;;
esac

repo_root=$(git rev-parse --show-toplevel)
src="$repo_root/docs/wiki"
[ -d "$src" ] || { echo "publish-wiki: $src not found" >&2; exit 1; }

origin=$(git -C "$repo_root" remote get-url origin)
wiki_url="${origin%.git}.wiki.git"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "publish-wiki: cloning $wiki_url"
if ! git clone --quiet --depth 1 "$wiki_url" "$work/wiki"; then
  echo "publish-wiki: could not clone the wiki. If it has no pages yet, create one in the Wiki tab first." >&2
  exit 1
fi

for page in "$src"/*.md; do
  name=$(basename "$page")
  sed -E 's/\]\(([A-Za-z0-9_-]+)\.md(#[^)]*)?\)/](\1\2)/g' "$page" > "$work/wiki/$name"
done

for page in "$work/wiki"/*.md; do
  name=$(basename "$page")
  [ -e "$src/$name" ] || echo "publish-wiki: wiki-only page left in place: $name"
done

cd "$work/wiki"
git add -- *.md
if git diff --cached --quiet; then
  echo "publish-wiki: wiki already up to date"
  exit 0
fi

git diff --cached --stat
if [ "$dry_run" = true ]; then
  echo "publish-wiki: dry run, nothing pushed"
  exit 0
fi

source_rev=$(git -C "$repo_root" rev-parse --short HEAD)
git commit --quiet -m "Publish wiki from docs/wiki at $source_rev"
git push --quiet origin HEAD
echo "publish-wiki: published from $source_rev"
