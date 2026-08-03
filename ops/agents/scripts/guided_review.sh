#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-manual}"
REPORT="ops/agents/reports/guided_review.md"
mkdir -p ops/agents/reports ops/agents/state

{
  echo "# Guided Review"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Target: $TARGET"
  echo
  echo "## Git status"
  git status --short || true
  echo
  echo "## Archivos modificados"
  git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only || true
  echo
  echo "## Domain map refresh"
} > "$REPORT"

bash ops/agents/scripts/domain_inventory.sh >> "$REPORT" 2>&1 || true

{
  echo
  echo "## Validation refresh"
} >> "$REPORT"

bash ops/agents/scripts/validate.sh >> "$REPORT" 2>&1 || true

{
  echo
  echo "## Policy assertions"
  echo "- auto-merge: disabled"
  echo "- branch-delete: disabled"
  echo "- validation-first: enabled"
  echo "- report-required: enabled"
} >> "$REPORT"

echo "last_guided_review_target=$TARGET" > ops/agents/state/guided_review.env
date -Iseconds >> ops/agents/state/guided_review.env

echo "Guided review generado en $REPORT"
