#!/usr/bin/env bash
# Write the GitHub wiki tree for this repository from docs/wiki/.
#
# The pages are written and reviewed in the main repository, so pull requests,
# secret scanning and review cover them. Publishing is not done here: the Wiki
# workflow (.github/workflows/wiki.yml) runs this script as the generate step
# of git-your-ship-together's wiki-publish.yml, which pushes the tree to the
# wiki from main only and never from a pull request. Edits made in the wiki
# editor are overwritten on the next publish, and a page that is not in
# docs/wiki/ is removed from the wiki.
#
# Usage, from anywhere inside a clone:
#   scripts/gen-wiki.sh OUT_DIR
#
# What it changes in each page: relative links such as (Twingate.md) or
# (Twingate.md#section) become (Twingate) and (Twingate#section), which is how
# the wiki addresses pages. Absolute links are left alone.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo "usage: $0 OUT_DIR" >&2
  exit 2
fi
out=$1

repo_root=$(cd "$(dirname "$0")/.." && pwd)
src="$repo_root/docs/wiki"
[ -d "$src" ] || { echo "gen-wiki: $src not found" >&2; exit 1; }

mkdir -p "$out"
count=0
for page in "$src"/*.md; do
  [ -e "$page" ] || continue
  name=$(basename "$page")
  sed -E 's/\]\(([A-Za-z0-9_-]+)\.md(#[^)]*)?\)/](\1\2)/g' "$page" > "$out/$name"
  count=$((count + 1))
done

# An empty tree would empty the wiki; wiki-publish.yml refuses one too, but
# failing here names the cause.
if [ "$count" -eq 0 ]; then
  echo "gen-wiki: no pages in $src" >&2
  exit 1
fi
echo "gen-wiki: wrote $count pages to $out"
