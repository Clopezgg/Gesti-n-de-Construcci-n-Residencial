#!/usr/bin/env bash
set -euo pipefail

REPO="Clopezgg/Gesti-n-de-Construcci-n-Residencial"
mkdir -p ops/agents/reports

gh pr list --repo "$REPO" --state open \
  --json number,title,headRefName,baseRefName,mergeable,mergeStateStatus,isDraft,url \
| jq -r '.[] | @base64' | while read -r row; do
  _jq() { echo "$row" | base64 -d | jq -r "$1"; }

  number=$(_jq '.number')
  title=$(_jq '.title')
  branch=$(_jq '.headRefName')
  base=$(_jq '.baseRefName')
  mergeable=$(_jq '.mergeable')
  status=$(_jq '.mergeStateStatus')
  draft=$(_jq '.isDraft')
  url=$(_jq '.url')

  ahead=$(gh api "repos/$REPO/compare/$base...$branch" --jq '.ahead_by // 0' 2>/dev/null || echo "ERR")
  behind=$(gh api "repos/$REPO/compare/$base...$branch" --jq '.behind_by // 0' 2>/dev/null || echo "ERR")

  verdict="needs-review"
  if [ "$ahead" = "0" ]; then
    verdict="already-integrated"
  elif [ "$mergeable" = "MERGEABLE" ] && [ "$status" = "CLEAN" ] && [ "$draft" = "false" ]; then
    verdict="ready-to-merge"
  elif [ "$draft" = "true" ]; then
    verdict="draft"
  elif [ "$mergeable" = "CONFLICTING" ] || [ "$status" = "DIRTY" ]; then
    verdict="conflicts"
  fi

  printf "#%s | %s | branch=%s | ahead=%s | behind=%s | mergeable=%s | status=%s | draft=%s | verdict=%s | %s\n" \
    "$number" "$title" "$branch" "$ahead" "$behind" "$mergeable" "$status" "$draft" "$verdict" "$url"
done > ops/agents/reports/pr_audit.txt

echo "PR audit generado en ops/agents/reports/pr_audit.txt"
