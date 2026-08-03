# Materialized Execution Pack

Fecha: 2026-08-03T17:04:36+00:00
Pack: operations-core

# Execution Pack: operations-core

## Scope
- nexora_operations.js
- nexora_operations.json
- progress
- purchases
- inventory

## Allowed actions
- revisar operación guiada
- validar progress/inventory/purchase impact
- preparar handoff a ui-public si toca dashboard/page/public

## Required checks
- pytest --collect-only nexora_app/nexora/tests 2>/dev/null || true
- bash ops/agents/scripts/regression_scan.sh

## Expected outputs
- ops/agents/reports/regression_scan.md
- ops/agents/reports/router_handoff.md
- ops/agents/reports/autoplan.md

## Constraints
- cambios operativos requieren revisión humana final
