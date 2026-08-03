# Execution Pack: ui-public

## Scope
- public
- css
- page
- dashboard

## Allowed actions
- revisar estilos y páginas
- validar consistencia visual
- coordinar con governance si toca workflows

## Required checks
- bash ops/agents/scripts/regression_scan.sh
- node --version
- npm test --if-present 2>/dev/null || true

## Expected outputs
- ops/agents/reports/regression_scan.md
- ops/agents/reports/router_handoff.md

## Constraints
- no cambios automáticos de despliegue
