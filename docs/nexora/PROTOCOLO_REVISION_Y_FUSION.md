# NEXORA — Protocolo obligatorio de revisión final y fusión

## Objetivo

Este protocolo gobierna el cierre de la ejecución automática. Ningún agente puede fusionar, etiquetar, publicar o desplegar NEXORA por iniciativa propia.

## Destino de los cambios

Durante la corrección, todos los commits y pushes se realizan exclusivamente en:

- rama: `nexora-continuidad-total`
- PR: `#12`
- base del PR #12: `nexora-reconstruccion`

`main` permanece intacta.

## Puerta final obligatoria

Cuando el agente crea que terminó, debe volver a validar todo sobre el mismo SHA completo y cumplir simultáneamente:

1. 166/166 requisitos con estado final permitido y evidencia individual.
2. Todos los workflows obligatorios verdes sobre ese mismo SHA.
3. Instalación, migración, uninstall, reinstall y seed doble aprobados.
4. Pruebas positivas, negativas, permisos, idempotencia, concurrencia y rollback aprobadas.
5. Persistencia, backup y restauración aislada demostradas.
6. UX móvil/iPhone y PWA demostradas.
7. `MATRIZ_REQUISITOS.md`, `EXECUTION_STATE.md`, `CHECKPOINT.md` y PR #12 coherentes.
8. Árbol Git limpio después del último push.
9. Cero fusión, cero tag, cero release y cero despliegue.

## Paquete de revisión independiente

Antes de detenerse, el agente debe crear o actualizar `docs/nexora/FINAL_REVIEW_PACKAGE.md` con:

- repositorio, rama, PR y SHA completo;
- fecha y hora UTC;
- resultado 166/166 y desglose por bloque;
- lista de workflows, run, job, conclusión y enlace;
- pruebas ejecutadas y comandos exactos;
- instalación/migración/uninstall/reinstall/seed;
- permisos, finanzas, concurrencia y rollback;
- backup/restore, móvil/PWA y seguridad;
- artifacts y digests disponibles;
- `git status --short` final;
- cualquier limitación, omisión o evidencia aún no demostrada;
- conclusión honesta: `APTO PARA REVISIÓN` o `NO APTO PARA REVISIÓN`.

Está prohibido ocultar fallos, pendientes o resultados omitidos.

## Estado final del monitor

Después del último commit y push, actualizar `docs/nexora/LIVE_PROGRESS.json` con:

```json
{
  "agent_status": "awaiting_review",
  "phase": "Puerta final de revisión independiente",
  "current_block": null,
  "task": "Esperando revisión de ChatGPT y autorización expresa del usuario",
  "detail": "Indicar PR #12, SHA completo y ruta docs/nexora/FINAL_REVIEW_PACKAGE.md",
  "blocking_issue": "Fusión prohibida hasta revisión independiente y autorización expresa"
}
```

Conservar también las pruebas y eventos anteriores. No sustituir el archivo por únicamente este fragmento.

## Intervención de ChatGPT

El agente local no puede abrir ni controlar automáticamente la conversación privada del usuario con ChatGPT. Por eso, al quedar en `awaiting_review`, debe mostrar como última instrucción:

> Regrese a su conversación con ChatGPT y escriba: `Revisa el paquete final de NEXORA y el HEAD actual del PR #12.`

ChatGPT revisará el repositorio conectado, el SHA final, los workflows y el paquete de evidencia. Solo después de una revisión satisfactoria podrá consultar al usuario si autoriza la fusión.

## Secuencia de fusión autorizable

La fusión nunca es automática. La secuencia correcta es:

1. revisión independiente del PR #12;
2. autorización expresa del usuario;
3. PR #12 hacia `nexora-reconstruccion`;
4. nueva validación de la rama resultante;
5. revisión independiente del PR #11;
6. segunda autorización expresa del usuario;
7. PR #11 hacia `main`;
8. despliegue únicamente mediante una autorización separada.

Una autorización para PR #12 no autoriza PR #11, y ninguna fusión autoriza despliegue.
