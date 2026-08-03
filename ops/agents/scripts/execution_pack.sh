#!/usr/bin/env bash
set -euo pipefail

PACK="${1:-repo-governance}"
REPORT="ops/agents/reports/execution_pack_${PACK}.md"
mkdir -p ops/agents/reports ops/agents/state

SOURCE="ops/agents/packs/${PACK}.md"

if [ ! -f "$SOURCE" ]; then
  echo "Pack no encontrado: $SOURCE"
  exit 1
fi

{
  echo "# Materialized Execution Pack"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Pack: $PACK"
  echo
  cat "$SOURCE"
} > "$REPORT"

echo "selected_pack=$PACK" > ops/agents/state/execution_pack.env
date -Iseconds >> ops/agents/state/execution_pack.env

echo "Execution pack materializado en $REPORT"
