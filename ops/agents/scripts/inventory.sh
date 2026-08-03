#!/usr/bin/env bash
set -euo pipefail

mkdir -p ops/agents/reports

{
  echo "# NEXORA Inventory"
  echo
  echo "## Fecha"
  date -Iseconds
  echo
  echo "## Git status"
  git status --short || true
  echo
  echo "## Top-level tree"
  find . -maxdepth 2 -type d | sort
  echo
  echo "## Nexora modules"
  find nexora_app/nexora -maxdepth 2 -type d 2>/dev/null | sort || true
  echo
  echo "## Tests"
  find . -path '*tests*' | sort || true
  echo
  echo "## Workflows"
  find .github/workflows -maxdepth 1 -type f | sort || true
  echo
  echo "## Scripts"
  find scripts -maxdepth 1 -type f | sort || true
  echo
  echo "## Backup autofix files"
  find . -maxdepth 1 -name '.backup-codebase-autofix*' | sort || true
} > ops/agents/reports/inventory.md

echo "Inventario generado en ops/agents/reports/inventory.md"
