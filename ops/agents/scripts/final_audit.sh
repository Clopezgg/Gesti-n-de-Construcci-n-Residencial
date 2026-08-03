#!/usr/bin/env bash
set -euo pipefail

REPORT="ops/agents/reports/final_audit.md"
STATE="ops/agents/state/final_audit.env"

mkdir -p ops/agents/reports ops/agents/state

missing=0

REQUIRED_FILES=(
  "ops/agents/reports/guided_review.md"
  "ops/agents/reports/redeploy_watch.md"
  "ops/agents/reports/autoplan.md"
  "ops/agents/reports/router_handoff.md"
  "ops/agents/reports/mission_runner.md"
  "ops/agents/reports/queue_status.md"
  "ops/agents/dashboard/mission_dashboard.md"
  ".github/workflows/nexora-guided-review.yml"
  ".github/workflows/nexora-redeploy-watch.yml"
)

{
  echo "# Final Audit"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo
  echo "## Required artifacts"
  for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
      echo "- OK: $f"
    else
      echo "- MISSING: $f"
      missing=1
    fi
  done
  echo
  echo "## Git status"
  git status --short || true
  echo
  echo "## Sensitive paths snapshot"
  for p in \
    "nexora_operations.js" \
    "nexora_operations.json" \
    "notifications" \
    "patches" \
    "progress" \
    "public" \
    "page" \
    "public/css/nexora_dashboard_fixes.css" \
    "public/css/nexora_executive.css"
  do
    if [ -e "$p" ]; then
      echo "- PRESENT: $p"
    else
      echo "- NOT_FOUND: $p"
    fi
  done
  echo
  if [ "$missing" -ne 0 ]; then
    echo "## Verdict"
    echo "BLOCKED: faltan artefactos requeridos para RC interno."
  else
    echo "## Verdict"
    echo "READY: auditoría final completa para RC interno."
  fi
} > "$REPORT"

echo "missing_artifacts=$missing" > "$STATE"
date -Iseconds >> "$STATE"

echo "Auditoría final generada en $REPORT"
