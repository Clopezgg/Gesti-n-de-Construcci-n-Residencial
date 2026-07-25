# NEXORA — Mandato ejecutable para OpenCode

## Autorización y alcance

La palabra **SIRILAN** autorizó la auditoría completa, las correcciones, las pruebas, los commits y los pushes exclusivamente a `origin/nexora-continuidad-total` / PR #12.

No autorizó:

- fusionar PR #12;
- fusionar PR #11;
- modificar `main`;
- eliminar ramas;
- crear tags o releases;
- desplegar;
- tocar producción, AWS, Coolify o DNS.

## Lectura obligatoria

Leer completamente, en este orden:

1. `AGENTS.md`
2. `docs/nexora/ORDEN_MAESTRA_FINALIZACION.md`
3. `docs/nexora/AUDITORIA_CORRECCION_FINAL.md`
4. `docs/nexora/AUDITORIA_POR_CAPAS.md`
5. `docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md`
6. `docs/nexora/DEFECTS.json`
7. `docs/nexora/AUDIT_RESULTS.json`
8. `docs/nexora/MATRIZ_REQUISITOS.md`
9. `EXECUTION_STATE.md`

## Regla principal

Los estados escritos en `MATRIZ_REQUISITOS.md` son afirmaciones documentales. No constituyen certificación real.

Está prohibido copiar esos estados a `AUDIT_RESULTS.json`, realizar reemplazos masivos, aprobar por existencia de archivos o reutilizar evidencia de otro SHA sin demostrar que sigue siendo válida después de las regresiones necesarias.

## Herramientas canónicas

```text
bun tools/nexora_monitor/audit_cli.js summary
bun tools/nexora_monitor/audit_cli.js validate
bun tools/nexora_monitor/audit_cli.js block <0-20>
bun tools/nexora_monitor/audit_cli.js gate
bun tools/nexora_monitor/audit_update.js <operación> --file <payload.json>
```

Operaciones de `audit_update.js`:

- `set-audit-state`
- `set-requirement`
- `set-validation`
- `upsert-defect`
- `resolve-defect`

No editar manualmente `AUDIT_RESULTS.json` ni `DEFECTS.json` salvo recuperación excepcional documentada. Usar el escritor controlado.

## Inicio obligatorio

1. Confirmar rama y HEAD completo.
2. Ejecutar `bun tools/nexora_monitor/audit_cli.js init <HEAD_COMPLETO>`.
3. Ejecutar `bun tools/nexora_monitor/audit_cli.js validate`.
4. Marcar `active_block: 0`.
5. Actualizar `LIVE_PROGRESS.json` con estado `working`, Bloque 0 y tarea exacta.
6. Auditar el Bloque 0 requisito por requisito.

No iniciar por el Bloque 7 ni dar por certificados los Bloques 0–6.

## Flujo por requisito

Para cada requisito del bloque activo:

1. reconstruir el objetivo original;
2. registrar `objective_summary`;
3. localizar implementación, datos, servicios, permisos, interfaz y pruebas;
4. registrar `implementation_files`;
5. obtener el perfil con `bun tools/nexora_monitor/audit_cli.js block <N>`;
6. recorrer todas sus validaciones obligatorias;
7. marcar cada validación `running` antes de ejecutarla;
8. ejecutar prueba/comando o revisión verificable;
9. registrar resultado real;
10. crear o actualizar defecto cuando no cumple;
11. corregir causa raíz;
12. repetir prueba específica, negativa y regresión;
13. certificar únicamente con detalle, evidencia y SHA completo;
14. revisar el resumen del bloque antes de avanzar.

## Estados válidos

- `certified`
- `technical_error`
- `objective_mismatch`
- `running`
- `pending`
- `blocked`
- `decision_required`
- `not_applicable`

`certified` y `not_applicable` requieren:

- detalle concreto;
- evidencia estructurada;
- SHA completo de 40 caracteres;
- resultado reproducible.

## Defectos

Usar identificadores estables `NXR-DEF-B00-0001`.

Cada defecto debe incluir:

- requisito;
- bloque;
- categoría;
- severidad;
- comportamiento esperado;
- comportamiento encontrado;
- causa raíz;
- archivos;
- evidencia;
- número de intentos;
- último resultado.

Antes de corregir, cambiar a `diagnosing` o `correcting`. Antes de repetir pruebas, cambiar a `retesting`. Solo resolver con evidencia y SHA completo.

## Linters y validadores compartidos

Aunque la auditoría sea secuencial, un linter, inventario, contrato estático o configuración compartida que impida certificar el Bloque 0 se trata como dependencia global del bloque activo.

Agrupar fallos por causa raíz:

1. formato automático seguro;
2. error funcional;
3. configuración/parser/inventario defectuoso;
4. falso positivo justificable.

No crear cientos de defectos duplicados cuando una configuración explica todos los casos.

Prohibido:

- `continue-on-error`;
- exclusiones artificiales;
- reducir archivos o pruebas cubiertas;
- `noqa`, `eslint-disable`, `type: ignore` o equivalentes masivos;
- pruebas vacías;
- mocks autorreferenciales;
- marcar verde sin volver a ejecutar.

Después de corregir un paquete de lint:

1. ejecutar sobre archivos afectados;
2. ejecutar pruebas relacionadas;
3. ejecutar árbol completo;
4. ejecutar regresión;
5. ejecutar pre-commit dos veces sin cambios;
6. ejecutar Semgrep;
7. commit y push;
8. esperar CI del mismo SHA.

## Orden de bloques

```text
0 → 1 → 2 → ... → 20
```

Un bloque no avanza hasta que su resumen tenga:

- cero `technical_error`;
- cero `objective_mismatch`;
- cero `pending`;
- cero `running`;
- cero `blocked`;
- cero `decision_required`;
- todos sus requisitos certificados;
- regresiones anteriores aprobadas;
- CI aplicable del mismo SHA verde.

Al cerrar el Bloque N, repetir pruebas representativas de 0..N-1. Al cerrar el Bloque 20, ejecutar regresión global.

## GitHub Actions

Para cada push:

1. registrar SHA completo;
2. esperar ejecuciones de ese SHA;
3. leer jobs y logs completos de cada fallo;
4. registrar run, job, step y enlace;
5. corregir causa raíz;
6. repetir hasta que todos los workflows obligatorios estén verdes sobre un mismo SHA.

No usar ejecuciones verdes de un SHA anterior como certificación final.

## Commits

- una causa raíz coherente por commit;
- mensaje semántico;
- revisar diff antes de commit;
- push únicamente a `origin/nexora-continuidad-total`;
- nunca force push;
- nunca `reset --hard` ni `clean -fd`.

## Estado en tiempo real

Actualizar `LIVE_PROGRESS.json` antes y después de:

- requisito;
- validación;
- diagnóstico;
- corrección;
- prueba;
- commit;
- push;
- consulta de CI.

No escribir porcentajes manuales. El monitor los calcula desde la auditoría canónica.

## Puerta final

Solo intentar el cierre cuando:

```text
bun tools/nexora_monitor/audit_cli.js gate
```

termine con código 0 y, además:

- todos los workflows obligatorios del HEAD estén verdes;
- instalación/migración/uninstall/reinstall/seed doble estén demostrados;
- permisos, finanzas, concurrencia y rollback estén demostrados;
- backup/restore y móvil/PWA estén demostrados;
- árbol limpio;
- `FINAL_REVIEW_PACKAGE.md` sea coherente y diga `APTO PARA REVISIÓN`;
- PR #12, matriz, checkpoint y estado coincidan.

Entonces actualizar `LIVE_PROGRESS.json` a `awaiting_review`, hacer el último commit/push y detenerse. No fusionar ni eliminar ramas.
