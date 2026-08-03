# Current Mission

Fecha: 2026-08-03T17:05:47+00:00
Mission target: default-mission
Domain: operations
Primary agent: operations-core
Execution pack: operations-core

## Objective
Ejecutar revisión guiada del dominio seleccionado sin automatismos peligrosos.

## Mandatory inputs
- ops/agents/reports/autoplan.md
- ops/agents/reports/router_handoff.md
- ops/agents/packs/operations-core.md

## Steps
1. Leer autoplan y confirmar dominio.
2. Leer router_handoff y validar handoff.
3. Cargar execution pack correspondiente.
4. Ejecutar checks mínimos del pack.
5. Escribir evidencia en ops/agents/reports.
6. Escalar a revisión humana.

## Constraints
- no auto-merge
- no auto-redeploy
- no borrar archivos
- no tocar producción
