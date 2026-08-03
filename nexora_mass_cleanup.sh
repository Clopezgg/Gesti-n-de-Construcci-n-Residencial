#!/usr/bin/env bash
set -euo pipefail

REPO="Clopezgg/Gesti-n-de-Construcci-n-Residencial"

echo "== Nexora: auditoría masiva de PRs y ramas =="

# 1) Recalcular auditoría de PRs abiertas contra main
echo "-- Recalculando pr_audit_report.txt --"
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
done | tee pr_audit_report.txt

echo
echo "== Paso 2: Cerrar PRs ya integradas (ahead=0) sin merge =="

# 2) Cerrar PRs cuyos cambios ya están en main (ahead=0)
grep 'verdict=already-integrated' pr_audit_report.txt || echo "No hay PRs already-integrated."
grep 'verdict=already-integrated' pr_audit_report.txt | while read -r line; do
  number=$(echo "$line" | cut -d' ' -f1 | tr -d '#')
  echo "Cerrando PR #$number (ya integrada en main)..."
  gh pr close "$number" --repo "$REPO" --comment "Cerrada automáticamente: cambios ya presentes en main."
done

echo
echo "== Paso 3: Auto-merge seguro de PRs listas (ready-to-merge) =="

# 3) Auto-merge de PRs con verdict=ready-to-merge
grep 'verdict=ready-to-merge' pr_audit_report.txt || echo "No hay PRs ready-to-merge."
grep 'verdict=ready-to-merge' pr_audit_report.txt | while read -r line; do
  number=$(echo "$line" | cut -d' ' -f1 | tr -d '#')
  url=$(echo "$line" | awk '{print $NF}')
  echo "Activando auto-merge para PR #$number ($url)..."
  gh pr merge "$number" --repo "$REPO" --squash --delete-branch --auto
done

echo
echo "== Paso 4: Listar ramas remotas candidatas a borrado =="

# 4) Listar ramas remotas ya fusionadas en main y sin PR abierta
echo "-- Obteniendo lista de PRs abiertas por rama --"
OPEN_BRANCHES=$(gh pr list --repo "$REPO" --state open --json headRefName --jq '.[].headRefName')

echo "-- Cambiando a main y actualizando --"
git checkout main
git pull --prune

echo "-- Ramas remotas ya fusionadas en main --"
git branch -r --merged origin/main | sed 's#origin/##' | while read -r branch; do
  # Ignorar main y develop
  if [[ "$branch" == "main" || "$branch" == "develop" ]]; then
    continue
  fi
  # Ignorar ramas que todavía tienen PR abierta
  if grep -qx "$branch" <<< "$OPEN_BRANCHES"; then
    continue
  fi
  echo "CANDIDATA_A_BORRADO: $branch"
done | tee branches_candidates_for_delete.txt

echo
echo "Revisión manual recomendada:"
echo "  - Ver pr_audit_report.txt para ver decisiones de PR."
echo "  - Ver branches_candidates_for_delete.txt para ver las ramas candidatas."
echo
echo "Para borrar ramas candidatas (cuando estés seguro), puedes usar:"
echo "  while read -r b; do git push origin --delete \"\$b\"; done < branches_candidates_for_delete.txt"
