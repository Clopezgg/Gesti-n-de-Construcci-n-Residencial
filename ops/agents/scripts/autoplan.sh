#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-manual-plan}"
REPORT="ops/agents/reports/autoplan.md"
STATE="ops/agents/state/autoplan.env"

mkdir -p ops/agents/reports ops/agents/state

missing=0

for f in \
  ops/agents/reports/guided_review.md \
  ops/agents/reports/redeploy_watch.md \
  ops/agents/reports/domain_map.md
do
  [ -f "$f" ] || missing=1
done

changed_files="$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only || true)"

detect_domain() {
  local files="$1"
  if echo "$files" | grep -Eq 'financial|fund|ledger|account'; then
    echo "financial"
  elif echo "$files" | grep -Eq 'contract|quotation|supplier'; then
    echo "contracts"
  elif echo "$files" | grep -Eq 'progress|inventory|purchase|operation'; then
    echo "operations"
  elif echo "$files" | grep -Eq 'public|css|page|dashboard'; then
    echo "ui-public"
  elif echo "$files" | grep -Eq '.github/workflows|ops/agents|docs'; then
    echo "workflow-governance"
  else
    echo "workflow-governance"
  fi
}

domain="$(detect_domain "$changed_files")"

{
  echo "# Autoplan"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Target: $TARGET"
  echo
  echo "## Required evidence"
  for f in \
    ops/agents/reports/guided_review.md \
    ops/agents/reports/redeploy_watch.md \
    ops/agents/reports/domain_map.md
  do
    if [ -f "$f" ]; then
      echo "- OK: $f"
    else
      echo "- MISSING: $f"
    fi
  done
  echo
  echo "## Changed files"
  echo "$changed_files"
  echo
  echo "## Selected domain"
  echo "$domain"
  echo
  echo "## Proposed next actions"
  case "$domain" in
    financial)
      echo "- revisar financial core y doctypes relacionados"
      echo "- correr pruebas de colección y smoke financiero"
      ;;
    contracts)
      echo "- revisar contracts, quotations y suppliers"
      echo "- validar integridad de páginas relacionadas"
      ;;
    operations)
      echo "- revisar progress, purchases e inventory"
      echo "- validar flujos operativos guiados"
      ;;
    ui-public)
      echo "- revisar public/css, page y dashboard"
      echo "- validar assets y consistencia visual"
      ;;
    workflow-governance)
      echo "- revisar workflows y contratos de agentes"
      echo "- validar gates y reportes requeridos"
      ;;
  esac
  echo
  if [ "$missing" -ne 0 ]; then
    echo "## Verdict"
    echo "BLOCKED: faltan evidencias previas para ejecutar un autoplan confiable."
  else
    echo "## Verdict"
    echo "READY: plan generado; ejecutar revisión humana antes de cualquier cambio."
  fi
} > "$REPORT"

echo "selected_domain=$domain" > "$STATE"
echo "missing_evidence=$missing" >> "$STATE"
date -Iseconds >> "$STATE"

echo "Autoplan generado en $REPORT"
