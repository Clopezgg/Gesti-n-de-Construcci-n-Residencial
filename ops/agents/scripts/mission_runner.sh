#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-default-mission}"
REPORT="ops/agents/reports/mission_runner.md"
MISSION="ops/agents/missions/current_mission.md"
STATE="ops/agents/state/mission_runner.env"

mkdir -p ops/agents/reports ops/agents/state ops/agents/missions

missing=0
for f in \
  ops/agents/reports/autoplan.md \
  ops/agents/reports/router_handoff.md
do
  [ -f "$f" ] || missing=1
done

domain="workflow-governance"
agent="repo-governance"
pack="repo-governance"

if [ -f ops/agents/state/router_handoff.env ]; then
  domain="$(grep '^domain=' ops/agents/state/router_handoff.env | cut -d'=' -f2- || echo workflow-governance)"
  agent="$(grep '^primary_agent=' ops/agents/state/router_handoff.env | cut -d'=' -f2- || echo repo-governance)"
fi

case "$agent" in
  financial-core) pack="financial-core" ;;
  contracts-core) pack="contracts-core" ;;
  operations-core) pack="operations-core" ;;
  ui-public) pack="ui-public" ;;
  repo-governance) pack="repo-governance" ;;
  *) pack="repo-governance" ;;
esac

PACK_FILE="ops/agents/packs/${pack}.md"
if [ ! -f "$PACK_FILE" ]; then
  missing=1
fi

{
  echo "# Mission Runner"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Target: $TARGET"
  echo
  echo "## Inputs"
  echo "- domain: $domain"
  echo "- agent: $agent"
  echo "- pack: $pack"
  echo "- autoplan: ops/agents/reports/autoplan.md"
  echo "- router_handoff: ops/agents/reports/router_handoff.md"
  echo
  echo "## Evidence check"
  for f in \
    ops/agents/reports/autoplan.md \
    ops/agents/reports/router_handoff.md \
    "$PACK_FILE"
  do
    if [ -f "$f" ]; then
      echo "- OK: $f"
    else
      echo "- MISSING: $f"
    fi
  done
  echo
  if [ "$missing" -ne 0 ]; then
    echo "## Verdict"
    echo "BLOCKED: faltan insumos para construir una misión confiable."
  else
    echo "## Verdict"
    echo "READY: misión construida para ejecución humana."
  fi
} > "$REPORT"

{
  echo "# Current Mission"
  echo
  echo "Fecha: $(date -Iseconds)"
  echo "Mission target: $TARGET"
  echo "Domain: $domain"
  echo "Primary agent: $agent"
  echo "Execution pack: $pack"
  echo
  echo "## Objective"
  echo "Ejecutar revisión guiada del dominio seleccionado sin automatismos peligrosos."
  echo
  echo "## Mandatory inputs"
  echo "- ops/agents/reports/autoplan.md"
  echo "- ops/agents/reports/router_handoff.md"
  echo "- $PACK_FILE"
  echo
  echo "## Steps"
  echo "1. Leer autoplan y confirmar dominio."
  echo "2. Leer router_handoff y validar handoff."
  echo "3. Cargar execution pack correspondiente."
  echo "4. Ejecutar checks mínimos del pack."
  echo "5. Escribir evidencia en ops/agents/reports."
  echo "6. Escalar a revisión humana."
  echo
  echo "## Constraints"
  echo "- no auto-merge"
  echo "- no auto-redeploy"
  echo "- no borrar archivos"
  echo "- no tocar producción"
} > "$MISSION"

echo "domain=$domain" > "$STATE"
echo "agent=$agent" >> "$STATE"
echo "pack=$pack" >> "$STATE"
echo "target=$TARGET" >> "$STATE"
date -Iseconds >> "$STATE"

echo "Mission runner generado en $REPORT"
echo "Misión materializada en $MISSION"
