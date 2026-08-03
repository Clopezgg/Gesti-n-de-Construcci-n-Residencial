# Master Runbook

## Objetivo
Operar la plataforma de agentes NEXORA con control, trazabilidad y revisión humana.

## Flujo maestro
1. Ejecutar guided review.
2. Ejecutar redeploy watch.
3. Ejecutar autoplan.
4. Ejecutar router handoff.
5. Materializar execution pack.
6. Construir misión.
7. Encolar misión.
8. Priorizar ejecución.
9. Validar evidencia.
10. Escalar a revisión humana final.

## Reglas
- No auto-merge.
- No auto-redeploy.
- No branch-delete.
- Toda misión debe dejar evidencia en ops/agents/reports.
