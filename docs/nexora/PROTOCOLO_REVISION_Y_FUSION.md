# NEXORA — Protocolo obligatorio de revisión final y fusión

## Objetivo

Este protocolo gobierna el cierre de la auditoría por capas y cualquier autorización posterior. Ningún agente puede fusionar, eliminar ramas, etiquetar, publicar o desplegar NEXORA por iniciativa propia.

## Destino de los cambios

Durante auditoría y corrección, todos los commits y pushes se realizan exclusivamente en:

- rama: `nexora-continuidad-total`
- PR: `#12`
- base del PR #12: `nexora-reconstruccion`

`main` permanece intacta.

## Fuentes de certificación

La matriz documental no certifica por sí sola.

La puerta final usa simultáneamente:

- `docs/nexora/AUDIT_RESULTS.json`;
- `docs/nexora/DEFECTS.json`;
- `docs/nexora/MATRIZ_REQUISITOS.md`;
- pruebas y regresiones;
- GitHub Actions del mismo SHA;
- `docs/nexora/FINAL_REVIEW_PACKAGE.md`;
- árbol Git limpio;
- `tools/nexora_monitor/final_gate_check.js`.

## Puerta final obligatoria

Cuando el agente crea que terminó, debe volver a validar todo sobre el mismo SHA completo y cumplir simultáneamente:

1. avance de auditoría 100%;
2. certificación real 100%;
3. 166/166 requisitos certificados con evidencia individual;
4. 21/21 bloques certificados;
5. cero defectos abiertos;
6. cero errores técnicos e incumplimientos funcionales;
7. cero pendientes, bloqueos y decisiones abiertas;
8. todos los workflows obligatorios verdes sobre ese mismo SHA;
9. instalación, migración, uninstall, reinstall y seed doble aprobados;
10. pruebas positivas, negativas, permisos, idempotencia, concurrencia y rollback aprobadas;
11. persistencia, backup y restauración aislada demostradas;
12. UX móvil/iPhone y PWA demostradas;
13. auditoría, matriz, defectos, `EXECUTION_STATE.md`, `CHECKPOINT.md` y PR #12 coherentes;
14. árbol Git limpio después del último push;
15. cero fusión, cero eliminación de ramas, cero tag, cero release y cero despliegue.

Ejecutar:

```text
bun tools/nexora_monitor/audit_cli.js validate
bun tools/nexora_monitor/audit_cli.js gate
bun tools/nexora_monitor/final_gate_check.js
```

Los tres comandos deben terminar con código 0.

## Paquete de revisión independiente

Antes de detenerse, el agente debe crear o actualizar `docs/nexora/FINAL_REVIEW_PACKAGE.md` con:

- repositorio, rama, PR y SHA completo;
- fecha y hora UTC;
- avance de auditoría y certificación real;
- desglose por Bloques 0–20;
- desglose de validaciones por estado;
- defectos resueltos y evidencia de cada resolución;
- lista de workflows, run, job, conclusión y enlace del mismo SHA;
- pruebas ejecutadas y comandos exactos;
- instalación/migración/uninstall/reinstall/seed;
- permisos, finanzas, concurrencia y rollback;
- backup/restore, móvil/PWA y seguridad;
- artifacts y digests disponibles;
- `git status --short` final;
- cualquier limitación u omisión;
- conclusión honesta: `APTO PARA REVISIÓN` o `NO APTO PARA REVISIÓN`.

Está prohibido ocultar fallos, pendientes, resultados omitidos o evidencia de otro SHA presentada como final.

## Estado final del monitor

Después del último commit y push, y solo tras aprobar las puertas anteriores, actualizar `LIVE_PROGRESS.json` con:

```json
{
  "agent_status": "awaiting_review",
  "phase": "Puerta final de revisión independiente",
  "current_block": null,
  "task": "Esperando revisión de ChatGPT y autorización expresa del usuario",
  "detail": "Indicar PR #12, SHA completo, FINAL_REVIEW_PACKAGE.md y final-gate.json",
  "blocking_issue": "Fusión prohibida hasta revisión independiente y autorización expresa"
}
```

Conservar también las pruebas y eventos anteriores.

## Ventana de autorización

`final_authorization.ps1` solo puede abrirse cuando `final_gate_check.js` termina con código 0.

La primera ventana permite únicamente:

```text
AUTORIZO PR12
```

Esta autorización:

- no autoriza PR #11 hacia `main`;
- no autoriza eliminar ramas;
- no autoriza tags o releases;
- no autoriza despliegue.

La ventana registra la autorización local para revisión independiente. No ejecuta una fusión oculta.

## Secuencia de fusiones autorizables

1. auditoría completa del PR #12;
2. puerta final automática aprobada;
3. revisión independiente desde ChatGPT/GitHub;
4. autorización expresa `AUTORIZO PR12`;
5. fusión controlada PR #12 → `nexora-reconstruccion`;
6. nueva validación completa de la rama resultante;
7. revisión independiente del PR #11;
8. segunda autorización expresa para PR #11 → `main`;
9. fusión controlada a `main`;
10. nueva validación completa de `main`;
11. inventario de ramas con SHA y commits exclusivos;
12. autorización independiente para eliminar únicamente ramas totalmente fusionadas;
13. despliegue solo mediante otra autorización independiente.

## Conflictos o fallos de fusión

Ante conflicto o fallo posterior:

- detener la operación;
- no usar force push, reset destructivo ni borrar cambios;
- registrar causa y evidencia;
- devolver a OpenCode en una rama o estado seguro permitido por la autorización correspondiente;
- corregir y repetir pruebas;
- volver a solicitar autorización cuando cambie el SHA certificado.

Una autorización queda invalidada si el HEAD cambia antes de la fusión.
