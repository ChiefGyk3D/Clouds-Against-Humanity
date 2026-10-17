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
# OUT_DIR must not exist or must be empty: the whole directory is published, so
# a leftover file would be published too. A non-empty one is refused.
#
# What it changes in each page: relative links such as (Twingate.md) or
# (Twingate.md#section) become (Twingate) and (Twingate#section), which is how
# the wiki addresses pages. Absolute links are left alone.
#
# Images: the .png files in docs/wiki/images/ are copied flat into OUT_DIR (the
# wiki has no directories worth using), and an image link
# ![alt](images/name.png) becomes an absolute raw URL,
#   https://raw.githubusercontent.com/wiki/OWNER/REPO/name.png
# OWNER/REPO come from GITHUB_REPOSITORY (set in Actions), else from
# WIKI_REPO, else the upstream repository, and must look like a GitHub
# owner/repository name or the script stops. The value is handed to awk as a
# variable, never written into a program. Links inside fenced code blocks,
# indented code blocks and inline code are left as written, so a documentation
# example shows what the author typed. docs/wiki/images/ may hold only regular
# .png files; a symlink, a subdirectory or any other file is an error, and so is
# a symlinked page.

set -euo pipefail

die() {
  echo "gen-wiki: $*" >&2
  exit "${2:-1}"
}

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo "usage: $0 OUT_DIR" >&2
  exit 2
fi
out=$1

repo_root=$(cd "$(dirname "$0")/.." && pwd)
src="$repo_root/docs/wiki"
[ -d "$src" ] || die "$src not found"

wiki_repo=${GITHUB_REPOSITORY:-${WIKI_REPO:-ChiefGyk3D/Clouds-Against-Humanity}}
# Owner and repository names: letters, digits, dash, underscore, dot; one slash.
# Names made only of dots are path segments, not repositories.
if ! [[ $wiki_repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] \
  || [[ ${wiki_repo%%/*} =~ ^\.+$ ]] || [[ ${wiki_repo##*/} =~ ^\.+$ ]]; then
  die "GITHUB_REPOSITORY/WIKI_REPO is not an owner/repository name" 2
fi
raw_base="https://raw.githubusercontent.com/wiki/$wiki_repo"

if [ -e "$out" ] || [ -L "$out" ]; then
  [ -d "$out" ] && [ ! -L "$out" ] || die "$out exists and is not a plain directory" 2
  [ -z "$(ls -A "$out")" ] || die "$out is not empty; give an empty or new directory" 2
fi

# Check the sources before writing anything.
if [ -L "$src/images" ]; then
  die "$src/images is a symlink"
fi
if [ -d "$src/images" ]; then
  for entry in "$src"/images/* "$src"/images/.[!.]*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    [ -L "$entry" ] && die "$entry is a symlink; images must be regular files"
    [ -f "$entry" ] || die "$entry is not a regular file"
    case "$(basename "$entry")" in
      *.png) ;;
      *) die "$entry: only .png files are allowed in docs/wiki/images/" ;;
    esac
  done
fi
for page in "$src"/*.md; do
  [ -e "$page" ] || [ -L "$page" ] || continue
  [ -L "$page" ] && die "$page is a symlink; pages must be regular files"
done

# Rewrites ](images/NAME.png) to ](RAW/NAME.png) outside code.
# Fences open and close on a line starting with three or more backticks or
# tildes. An indented code block is a line indented four spaces or a tab after
# a blank line, unless the text above it is a list item (then it is a nested
# list line). Inline code spans (between single backticks) are skipped.
awk_prog='
function rewrite(s,   res, name) {
  res = ""
  while (match(s, /\]\(images\/[A-Za-z0-9_-]+\.png\)/)) {
    name = substr(s, RSTART + 9, RLENGTH - 10)
    res = res substr(s, 1, RSTART - 1) "](" raw "/" name ")"
    s = substr(s, RSTART + RLENGTH)
  }
  return res s
}
function prose(line,   n, parts, i, res) {
  n = split(line, parts, "`")
  res = ""
  for (i = 1; i <= n; i++) {
    res = res (i > 1 ? "`" : "") ((i % 2 == 1) ? rewrite(parts[i]) : parts[i])
  }
  return res
}
BEGIN { fence = 0; prev_blank = 1; inlist = 0 }
{
  line = $0
  if (line ~ /^[ ]*(```|~~~)/) { fence = !fence; print line; prev_blank = 0; next }
  if (fence) { print line; next }
  if (line ~ /^[ ]*$/) { print line; prev_blank = 1; next }
  if (line ~ /^(    |\t)/ && prev_blank && !inlist) { print line; prev_blank = 0; next }
  if (line !~ /^(    |\t)/) { inlist = (line ~ /^[ ]?[ ]?[ ]?([-*+]|[0-9]+[.)]) /) }
  print prose(line)
  prev_blank = 0
}
'

mkdir -p "$out"
count=0
for page in "$src"/*.md; do
  [ -e "$page" ] || continue
  name=$(basename "$page")
  sed -E 's/\]\(([A-Za-z0-9_-]+)\.md(#[^)]*)?\)/](\1\2)/g' "$page" \
    | awk -v raw="$raw_base" "$awk_prog" > "$out/$name"
  count=$((count + 1))
done

if [ -d "$src/images" ]; then
  for img in "$src"/images/*.png; do
    [ -e "$img" ] || continue
    cp "$img" "$out/$(basename "$img")"
  done
fi

# An empty tree would empty the wiki; wiki-publish.yml refuses one too, but
# failing here names the cause.
if [ "$count" -eq 0 ]; then
  echo "gen-wiki: no pages in $src" >&2
  exit 1
fi
echo "gen-wiki: wrote $count pages to $out"
