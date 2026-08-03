# Execution Pack: repo-governance

## Scope
- .github/workflows
- ops/agents
- docs

## Allowed actions
- revisar policies
- ajustar workflows manuales
- actualizar contratos y reportes

## Required checks
- bash ops/agents/scripts/validate.sh
- bash ops/agents/scripts/router_handoff.sh

## Expected outputs
- ops/agents/reports/guided_review.md
- ops/agents/reports/redeploy_watch.md
- ops/agents/reports/router_handoff.md

## Constraints
- no auto-merge
- no branch-delete
- no redeploy automático
