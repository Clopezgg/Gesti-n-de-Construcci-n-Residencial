#!/usr/bin/env bash
set -euo pipefail

REPORT="ops/agents/reports/router_handoff.md"
STATE="ops/agents/state/router_handoff.env"
mkdir -p ops/agents/reports ops/agents/state

changed_files="$(git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only || true)"

detect_domain() {
  local files="$1"
  if echo "$files" | grep -Eiq 'financial|fund|ledger|account'; then
    echo "financial|financial-core|repo-governance"
  elif echo "$files" | grep -Eiq 'contract|quotation|supplier'; then
    echo "contracts|contracts-core|repo-governance,ui-public"
  elif echo "$files" | grep -Eiq 'progress|inventory|purchase|operation|nexora_operations'; then
    echo "operations|operations-core|repo-governance,ui-public"
  elif echo "$files" | grep -Eiq 'public|css|page|dashboard'; then
    echo "ui-public|ui-public|repo-governance"
  else
    echo "workflow-governance|repo-governance|"
  fi
}

selection="$(detect_domain "$changed_files")"
domain="$(echo "$selection" | cut -d'|' -f1)"
primary="$(echo "$selection" | cut -d'|' -f2)"
secondary="$(echo "$selection" | cut -d'|' -f3)"

{
  echo "# Router Handoff"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo
  echo "## Changed files"
  echo "$changed_files"
  echo
  echo "## Routing decision"
  echo "- domain: $domain"
  echo "- primary_agent: $primary"
  echo "- handoff_agents: ${secondary:-none}"
  echo
  echo "## Execution order"
  echo "1. primary_agent analiza y propone"
  echo "2. handoff_agents revisan impacto cruzado"
  echo "3. repo-governance valida políticas si aplica"
  echo
  echo "## Constraints"
  echo "- no auto-merge"
  echo "- no auto-redeploy"
  echo "- no branch-delete"
  echo "- requiere revisión humana"
} > "$REPORT"

echo "domain=$domain" > "$STATE"
echo "primary_agent=$primary" >> "$STATE"
echo "handoff_agents=${secondary:-none}" >> "$STATE"
date -Iseconds >> "$STATE"

echo "Router handoff generado en $REPORT"
