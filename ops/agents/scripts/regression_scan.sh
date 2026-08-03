#!/usr/bin/env bash
set -euo pipefail

REPORT="ops/agents/reports/regression_scan.md"
mkdir -p ops/agents/reports

{
  echo "# Regression Scan"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo
  echo "## Sensitive paths status"
  for p in \
    nexora_app/nexora/progress \
    nexora_app/nexora/notifications \
    nexora_app/nexora/patches \
    nexora_app/nexora/public \
    nexora_app/nexora/page \
    .github/workflows
  do
    if [ -e "$p" ]; then
      count=$(find "$p" -type f 2>/dev/null | wc -l | tr -d ' ')
      echo "- $p :: $count archivos"
    else
      echo "- $p :: no existe"
    fi
  done
  echo
  echo "## Validation refresh"
} > "$REPORT"

bash ops/agents/scripts/validate.sh >> "$REPORT" 2>&1 || true

echo "Regression scan generado en $REPORT"
