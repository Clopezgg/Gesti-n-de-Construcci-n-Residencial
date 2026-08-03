#!/usr/bin/env bash
set -euo pipefail

mkdir -p ops/agents/reports

{
  echo "# Unified Gate"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo
  echo "## Git status"
  git status --short || true
  echo
  echo "## Inventory"
  bash ops/agents/scripts/inventory.sh
  echo "inventory: ok"
  echo
  echo "## Domain inventory"
  bash ops/agents/scripts/domain_inventory.sh
  echo "domain inventory: ok"
  echo
  echo "## Validation"
  bash ops/agents/scripts/validate.sh
  echo "validation: ok"
} > ops/agents/reports/unified_gate.md

echo "Gate unificado ejecutado. Revisa ops/agents/reports/unified_gate.md"
