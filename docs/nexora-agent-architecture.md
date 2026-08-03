# NEXORA Agent Architecture

## Objetivo
Construir una plataforma de ingeniería asistida por agentes para NEXORA que permita:
- inventariar el repositorio,
- entender dominios críticos,
- ejecutar validaciones unificadas,
- proponer cambios pequeños,
- documentar resultados,
- soportar rollback y trazabilidad.

## Fases
1. Baseline y estabilización del repo.
2. Inventario total.
3. Validación unificada.
4. Orquestador mínimo.
5. Agentes especializados.
6. Auto-reparación controlada.

## Dominios iniciales
- budget
- contracts
- dashboard
- directory
- financial
- inventory
- notifications
- progress
- purchases
- reports
- tests
- scripts
- workflows

## Reglas operativas
- No cambios masivos sin validación.
- No merge automático si la rama no está CLEAN.
- No borrar ramas con PR abierta.
- Todo cambio debe generar evidencia en ops/agents/reports.
