#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-manual-redeploy}"
REPORT="ops/agents/reports/redeploy_watch.md"
mkdir -p ops/agents/reports ops/agents/state

missing=0

{
  echo "# Redeploy Watch"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Target: $TARGET"
  echo
  echo "## Git status"
  git status --short || true
  echo
  echo "## Required reports"
} > "$REPORT"

for f in \
  ops/agents/reports/guided_review.md \
  ops/agents/reports/unified_gate.md \
  ops/agents/reports/domain_map.md
do
  if [ -f "$f" ]; then
    echo "- OK: $f" >> "$REPORT"
  else
    echo "- MISSING: $f" >> "$REPORT"
    missing=1
  fi
done

{
  echo
  echo "## Candidate regression paths"
  printf '%s\n' \
    "nexora_app/nexora/progress" \
    "nexora_app/nexora/notifications" \
    "nexora_app/nexora/patches" \
    "nexora_app/nexora/public" \
    "nexora_app/nexora/page" \
    ".github/workflows"
  echo
  echo "## Recent changed files"
  git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only || true
  echo
} >> "$REPORT"

dirty_lines=$(git status --porcelain | wc -l | tr -d ' ')
echo "dirty_lines=$dirty_lines" > ops/agents/state/redeploy_watch.env
echo "missing_reports=$missing" >> ops/agents/state/redeploy_watch.env
date -Iseconds >> ops/agents/state/redeploy_watch.env

if [ "$missing" -ne 0 ]; then
  {
    echo "## Verdict"
    echo "BLOCKED: faltan reportes requeridos."
  } >> "$REPORT"
  echo "Redeploy bloqueado por reportes faltantes"
  exit 1
fi

if [ "$dirty_lines" -ne 0 ]; then
  {
    echo "## Verdict"
    echo "BLOCKED: git status no está limpio."
  } >> "$REPORT"
  echo "Redeploy bloqueado porque git status no está limpio"
  exit 1
fi

{
  echo "## Verdict"
  echo "READY: condiciones mínimas satisfechas para redeploy manual."
} >> "$REPORT"

echo "Redeploy watch completado en $REPORT"
