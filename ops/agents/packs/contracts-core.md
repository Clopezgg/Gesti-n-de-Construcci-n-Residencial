# Execution Pack: contracts-core

## Scope
- nexora_quotations
- nexora_suppliers
- contract*
- quotation*
- supplier*

## Allowed actions
- revisar contratos, cotizaciones y proveedores
- validar relación con page/public si aplica
- preparar smoke review por dominio

## Required checks
- pytest --collect-only nexora_app/nexora/tests 2>/dev/null || true
- bash ops/agents/scripts/domain_inventory.sh

## Expected outputs
- ops/agents/reports/domain_map.md
- ops/agents/reports/autoplan.md
- ops/agents/reports/router_handoff.md

## Constraints
- no editar workflows sin handoff a governance
