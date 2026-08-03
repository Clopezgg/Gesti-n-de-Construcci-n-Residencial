#!/usr/bin/env bash
set -euo pipefail

mkdir -p ops/agents/reports ops/agents/state

TARGET="${1:-full-audit}"

echo "target=$TARGET" > ops/agents/state/last_run.env
date -Iseconds >> ops/agents/state/last_run.env

bash ops/agents/scripts/inventory.sh
bash ops/agents/scripts/validate.sh
bash ops/agents/scripts/pr_audit.sh

cat > ops/agents/reports/orchestrator_summary.md <<EOT
# Orchestrator Summary

## Target
$TARGET

## Outputs
- ops/agents/reports/inventory.md
- ops/agents/reports/validation.md
- ops/agents/reports/pr_audit.txt

## Policy
- no auto-fix
- no auto-merge
- no branch-delete
- validation-first
EOT

echo "Orquestación completada. Revisa ops/agents/reports/"
