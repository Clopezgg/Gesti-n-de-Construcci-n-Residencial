#!/usr/bin/env bash
set -euo pipefail

REPORT="ops/agents/reports/domain_map.md"
mkdir -p ops/agents/reports

declare -a DOMAINS=(
  "budget"
  "contracts"
  "dashboard"
  "directory"
  "financial"
  "integrations"
  "inventory"
  "notifications"
  "progress"
  "purchases"
  "reports"
)

{
  echo "# Domain Map"
  echo
  echo "Generado: $(date -Iseconds)"
  echo
  echo "| Dominio | Archivos Python | Archivos JS | Tests relacionados |"
  echo "|---|---:|---:|---:|"
  for d in "${DOMAINS[@]}"; do
    py_count=$(find nexora_app/nexora -type f -path "*${d}*" -name '*.py' 2>/dev/null | wc -l | tr -d ' ')
    js_count=$(find nexora_app/nexora -type f -path "*${d}*" -name '*.js' 2>/dev/null | wc -l | tr -d ' ')
    test_count=$(find nexora_app/nexora/tests -type f -iname "*${d}*" 2>/dev/null | wc -l | tr -d ' ')
    echo "| $d | $py_count | $js_count | $test_count |"
  done
  echo
  echo "## Rutas relevantes"
  echo
  find nexora_app/nexora -maxdepth 2 -type d 2>/dev/null | sort
} > "$REPORT"

echo "Mapa de dominios generado en $REPORT"
