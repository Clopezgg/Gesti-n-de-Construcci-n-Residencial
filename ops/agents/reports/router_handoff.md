# Router Handoff

Fecha: 2026-08-03T17:03:37+00:00

## Changed files
.github/workflows/nexora-autoplan.yml
docs/architecture/file_inventory.json
ops/agents/config/autoplan_policy.json
ops/agents/reports/autoplan.md
ops/agents/scripts/autoplan.sh
ops/agents/state/autoplan.env

## Routing decision
- domain: operations
- primary_agent: operations-core
- handoff_agents: repo-governance,ui-public

## Execution order
1. primary_agent analiza y propone
2. handoff_agents revisan impacto cruzado
3. repo-governance valida políticas si aplica

## Constraints
- no auto-merge
- no auto-redeploy
- no branch-delete
- requiere revisión humana
