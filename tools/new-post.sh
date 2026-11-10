#!/usr/bin/env bash
#
# Create a new post from tools/post-template.md
#
# Usage: tools/new-post.sh "CLN: Some Bug DoS" [YYYY-MM-DD]

set -eu

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"IMPL: Title\" [YYYY-MM-DD]"
  exit 1
fi

title="$1"
date="${2:-$(date +%F)}"

# "CLN: Some Bug DoS" -> "CLN-Some-Bug-DoS", matching the existing post URLs
slug="$(printf '%s' "$title" | sed -E 's/: +/-/g; s/ +/-/g; s/[^A-Za-z0-9-]//g')"

root="$(cd "$(dirname "$0")/.." && pwd)"
post="$root/_posts/$date-$slug.md"
impl="${title%%:*}"
impl_tag="$(printf '%s' "$impl" | tr '[:upper:]' '[:lower:]')"
image_slug="$(printf '%s' "$slug" | tr '[:upper:]' '[:lower:]')"

if [[ -e $post ]]; then
  echo "> $post already exists"
  exit 1
fi

sed -e "s|IMPL: Short Bug Name|$title|" \
  -e "s|DATE|$date|" \
  -e "s|SLUG|$image_slug|" \
  -e "s|\[impl,|[$impl_tag,|" \
  -e "s|IMPL|$impl|g" \
  "$root/tools/post-template.md" >"$post"

echo "> Created $post"
echo "> Cover image goes at assets/img/$image_slug.png (1200x630)"
