#!/usr/bin/env bash
set -euo pipefail

REPORT="ops/agents/release/release_candidate.md"
mkdir -p ops/agents/release

{
  echo "# Release Candidate Interno"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo
  echo "## Componentes consolidados"
  echo "- guided review"
  echo "- redeploy watch"
  echo "- autoplan"
  echo "- router handoff"
  echo "- execution packs"
  echo "- mission runner"
  echo "- mission queue"
  echo "- manual dispatcher"
  echo "- dashboard de misiones"
  echo
  echo "## Objetivo"
  echo "Dejar la plataforma de agentes NEXORA lista para operación interna controlada."
  echo
  echo "## Criterios"
  echo "- sin auto-merge"
  echo "- sin auto-redeploy"
  echo "- con evidencia por fase"
  echo "- con revisión humana obligatoria"
} > "$REPORT"

echo "Release candidate generado en $REPORT"
