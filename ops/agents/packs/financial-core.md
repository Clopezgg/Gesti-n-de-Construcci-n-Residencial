# Execution Pack: financial-core

## Scope
- financial
- fund
- ledger
- account

## Allowed actions
- revisar núcleo financiero
- validar impacto en doctype y reportes
- preparar evidencia antes de cualquier fix

## Required checks
- pytest --collect-only nexora_app/nexora/tests 2>/dev/null || true
- bash ops/agents/scripts/validate.sh

## Expected outputs
- ops/agents/reports/validation.md
- ops/agents/reports/domain_map.md
- ops/agents/reports/router_handoff.md

## Constraints
- no cambios masivos sin reporte específico
