#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="ops/agents/quarantine/$STAMP"
REPORT="ops/agents/reports/backup_cleanup.md"

mkdir -p "$DEST" ops/agents/reports

mapfile -t FILES < <(find . -maxdepth 1 -type f -name '.backup-codebase-autofix*' | sort)

{
  echo "# Backup Cleanup Report"
  echo
  echo "## Fecha"
  date -Iseconds
  echo
  echo "## Destino"
  echo "$DEST"
  echo
  echo "## Archivos detectados"
  printf '%s\n' "${FILES[@]:-}"
  echo
} > "$REPORT"

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "No se encontraron backups .backup-codebase-autofix*" | tee -a "$REPORT"
  exit 0
fi

for f in "${FILES[@]}"; do
  mv "$f" "$DEST"/
done

{
  echo "## Resultado"
  echo "Movidos ${#FILES[@]} archivos a cuarentena."
} >> "$REPORT"

echo "Backups enviados a $DEST"
echo "Reporte: $REPORT"
