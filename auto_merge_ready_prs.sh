#!/usr/bin/env bash
set -euo pipefail

REPO="Clopezgg/Gesti-n-de-Construcci-n-Residencial"

echo "== Auto-merge de PRs con label ready-for-merge =="

# Lista PRs abiertas con la etiqueta ready-for-merge
gh pr list --repo "$REPO" --state open --label ready-for-merge \
  --json number,title,headRefName,mergeable,mergeStateStatus,url \
  --jq '.[]' | jq -c '.' | while read -r pr; do
  number=$(echo "$pr" | jq -r '.number')
  title=$(echo "$pr" | jq -r '.title')
  branch=$(echo "$pr" | jq -r '.headRefName')
  mergeable=$(echo "$pr" | jq -r '.mergeable')
  status=$(echo "$pr" | jq -r '.mergeStateStatus')
  url=$(echo "$pr" | jq -r '.url')

  echo "PR #$number | $title"
  echo "  branch=$branch mergeable=$mergeable status=$status url=$url"

  if [ "$mergeable" != "MERGEABLE" ]; then
    echo "  => No merge automático: aún no es MERGEABLE (merge queue/CI no listo)."
    continue
  fi

  if [ "$status" != "CLEAN" ]; then
    echo "  => No merge automático: mergeStateStatus=$status (UNSTABLE/otra condición)."
    continue
  fi

  echo "  => Activando auto-merge vía squash y borrando rama remota cuando se complete..."
  gh pr merge "$number" --repo "$REPO" --squash --delete-branch --auto
done
