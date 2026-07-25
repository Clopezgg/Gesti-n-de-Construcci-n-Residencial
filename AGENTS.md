# NEXORA — reglas obligatorias para agentes

## Identidad y alcance

El producto se llama **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**.

- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama única de trabajo: `nexora-continuidad-total`
- PR único de continuidad: `#12`
- Base del PR #12: `nexora-reconstruccion`
- `main`: protegida
- Matriz documental: `docs/nexora/MATRIZ_REQUISITOS.md`
- Resultados canónicos de auditoría: `docs/nexora/AUDIT_RESULTS.json`
- Defectos canónicos: `docs/nexora/DEFECTS.json`
- Total oficial: **166 requisitos**
- Bloques oficiales: **0–20**

Las referencias a ConstruControl, PR #9, `reconstruccion-definitiva-construcontrol` o 224 requisitos son históricas y no gobiernan esta ejecución.

## Lectura obligatoria al iniciar

Leer completa y obedecer:

1. `docs/nexora/ORDEN_MAESTRA_FINALIZACION.md`
2. `docs/nexora/AUDITORIA_CORRECCION_FINAL.md`
3. `docs/nexora/AUDITORIA_POR_CAPAS.md`
4. `docs/nexora/OPENCODE_AUDIT_MANDATE.md`
5. `docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md`
6. `docs/nexora/DEFECTS.json`
7. `docs/nexora/AUDIT_RESULTS.json`
8. `EXECUTION_STATE.md`
9. `docs/nexora/MATRIZ_REQUISITOS.md`
10. `docs/nexora/LIVE_PROGRESS.json`

La auditoría por capas prevalece frente a cualquier declaración anterior de terminado que no esté demostrada por evidencia reproducible y CI sobre el mismo SHA completo.

## Fuente de certificación

`MATRIZ_REQUISITOS.md` describe requisitos y contiene afirmaciones documentales. Un estado final escrito allí no certifica por sí solo un requisito.

La certificación real se deriva exclusivamente de:

- `AUDIT_RESULTS.json` actualizado mediante `audit_update.js`;
- `DEFECTS.json` sin defectos abiertos;
- pruebas reproducibles;
- evidencia estructurada;
- SHA completo de 40 caracteres;
- GitHub Actions del mismo SHA;
- regresiones de bloques anteriores.

Está prohibido copiar masivamente estados de la matriz hacia la auditoría, contar archivos como avance o aprobar por existencia de código, documentación, commit o interfaz.

## Continuidad automática

No preguntar si debe pasar a la siguiente corrección o requisito. Continuar automáticamente con la siguiente tarea independiente disponible dentro del bloque activo.

Detenerse únicamente ante:

- riesgo destructivo;
- decisión irreversible;
- credencial externa faltante;
- cambio de `main`, producción, AWS, Coolify o DNS;
- fusión, tag, release o despliegue;
- ambigüedad funcional auténtica que no pueda resolverse desde objetivos, decisiones, código y evidencia.

## Orden obligatorio de bloques

La auditoría empieza en el Bloque 0 y avanza secuencialmente:

```text
0 → 1 → 2 → ... → 20
```

No iniciar por el Bloque 7 ni asumir que los Bloques 0–6 siguen certificados.

Un control compartido que bloquee el bloque activo puede corregirse como dependencia global, conservando su defecto en el bloque propietario.

## Protocolo obligatorio del monitor

El panel local usa:

- `AUDIT_RESULTS.json` para validaciones;
- `DEFECTS.json` para problemas y ciclos de corrección;
- `LIVE_PROGRESS.json` para actividad actual;
- Git local y GitHub Actions para HEAD, árbol y CI.

No escribir porcentajes manuales.

El monitor calcula por separado:

```text
avance de auditoría = validaciones ejecutadas / validaciones totales
certificación real = validaciones certificadas o no aplicables / validaciones totales
```

Los estados de auditoría válidos son:

- `certified`
- `technical_error`
- `objective_mismatch`
- `running`
- `pending`
- `blocked`
- `decision_required`
- `not_applicable`

`certified` y `not_applicable` requieren detalle, evidencia y SHA completo.

## Actualización segura de auditoría

Usar:

```text
bun tools/nexora_monitor/audit_cli.js summary
bun tools/nexora_monitor/audit_cli.js validate
bun tools/nexora_monitor/audit_cli.js block <0-20>
bun tools/nexora_monitor/audit_cli.js gate
bun tools/nexora_monitor/audit_update.js <operación> --file <payload.json>
```

No editar manualmente `AUDIT_RESULTS.json` ni `DEFECTS.json` salvo recuperación excepcional documentada.

Antes de una validación marcar `running`. Al terminar registrar el resultado real. Ante incumplimiento crear o actualizar un defecto estable `NXR-DEF-B00-0001`.

## LIVE_PROGRESS.json

Mantenerlo como JSON válido y actualizarlo antes y después de cada requisito, diagnóstico, corrección, prueba, commit, push y consulta de CI.

Campos obligatorios:

- `agent_status`: `idle`, `working`, `blocked`, `finished` o `awaiting_review`
- `phase`: fase real actual
- `current_block`: número 0–20 o `null`
- `task`: acción exacta
- `detail`: resultado o contexto verificable
- `started_at`: fecha/hora ISO-8601
- `last_update`: fecha/hora ISO-8601
- `blocking_issue`: texto o `null`
- `tests`: pruebas recientes
- `events`: eventos recientes

No borrar fallos para hacer ver el panel verde. Al hacer push registrar SHA completo. Al consultar Actions registrar workflow, run, job, step, conclusión y enlace.

## Regla de cierre de bloque

Un bloque solo se certifica cuando:

- todos sus requisitos fueron auditados;
- no tiene `technical_error`;
- no tiene `objective_mismatch`;
- no tiene `pending`, `running`, `blocked` ni `decision_required`;
- cada validación tiene evidencia;
- pruebas positivas y negativas pasan;
- permisos server-side pasan;
- idempotencia, integridad financiera, concurrencia y rollback pasan cuando aplican;
- regresiones anteriores pasan;
- CI aplicable del mismo SHA está verde;
- código y documentos coinciden;
- árbol Git está limpio después del push.

Al cerrar el Bloque N, repetir regresiones representativas de 0..N-1. Después del Bloque 20, ejecutar regresión global.

## Linters y validadores

Agrupar errores por causa raíz:

1. formato automático seguro;
2. error funcional;
3. configuración/parser/inventario defectuoso;
4. falso positivo justificable.

No crear cientos de defectos duplicados cuando una sola configuración los causa.

Prohibido debilitar controles mediante:

- `continue-on-error`;
- exclusiones artificiales;
- reducción de alcance;
- pruebas vacías;
- mocks autorreferenciales;
- silencios masivos como `noqa`, `eslint-disable` o equivalentes.

Después de una corrección de lint: ejecutar archivos afectados, pruebas relacionadas, árbol completo, regresión, pre-commit dos veces sin cambios, Semgrep y CI del mismo SHA.

## Git y publicación

Permitido:

- leer y editar dentro del repositorio;
- ejecutar pruebas, linters, Semgrep y validadores;
- commits semánticos por causa raíz;
- push únicamente a `origin/nexora-continuidad-total`.

Prohibido:

- `git push origin main`
- `git push --force`
- `git reset --hard`
- `git clean -fd`
- rebase destructivo
- borrado masivo
- nueva rama o PR
- merge/cierre de PR #11 o #12
- eliminación de ramas
- tags o releases
- despliegue
- producción, AWS, Coolify o DNS
- lectura o publicación de secretos

## Criterio de terminado

No declarar NEXORA terminado hasta que, sobre el mismo SHA completo:

- auditoría 100%;
- certificación real 100%;
- 166/166 requisitos certificados;
- 21/21 bloques certificados;
- cero defectos abiertos;
- cero errores técnicos;
- cero incumplimientos funcionales;
- cero pendientes, bloqueos o decisiones abiertas;
- todos los workflows obligatorios verdes;
- instalación/migración, uninstall/reinstall y seed doble pasen;
- permisos, finanzas, concurrencia y rollback pasen;
- persistencia, backup y restore aislado estén demostrados;
- UX móvil/iPhone y PWA estén demostradas;
- matriz, auditoría, defectos, checkpoint, `EXECUTION_STATE.md`, paquete final y PR #12 sean coherentes;
- árbol Git esté limpio;
- no exista fusión, tag ni despliegue sin autorización separada.

## Puerta final obligatoria

Al cumplir todo:

1. actualizar `FINAL_REVIEW_PACKAGE.md` con `APTO PARA REVISIÓN` y HEAD exacto;
2. ejecutar último commit y push solo a `origin/nexora-continuidad-total`;
3. actualizar `LIVE_PROGRESS.json` a `awaiting_review`;
4. ejecutar `bun tools/nexora_monitor/final_gate_check.js`;
5. solo si termina con código 0, abrir `final_authorization.ps1`;
6. detenerse sin fusionar, borrar ramas, etiquetar ni desplegar.

La primera ventana final únicamente puede registrar `AUTORIZO PR12`. PR #11 hacia `main`, eliminación de ramas y despliegue requieren autorizaciones posteriores e independientes.

OpenCode no puede controlar la conversación privada de ChatGPT. La revisión independiente se realiza desde GitHub antes de ejecutar cualquier fusión.
