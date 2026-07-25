# NEXORA — reglas obligatorias para agentes

## Identidad y alcance

El producto se llama **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**.

- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama única de trabajo: `nexora-continuidad-total`
- PR único de continuidad: `#12`
- Base del PR #12: `nexora-reconstruccion`
- `main`: protegida
- Matriz oficial: `docs/nexora/MATRIZ_REQUISITOS.md`
- Total oficial: **166 requisitos**

Las referencias a ConstruControl, PR #9, `reconstruccion-definitiva-construcontrol` o 224 requisitos son históricas y no gobiernan esta ejecución.

## Lectura obligatoria al iniciar

Leer completa y obedecer:

1. `docs/nexora/ORDEN_MAESTRA_FINALIZACION.md`
2. `docs/nexora/AUDITORIA_CORRECCION_FINAL.md`
3. `EXECUTION_STATE.md`
4. `docs/nexora/MATRIZ_REQUISITOS.md`
5. `docs/nexora/LIVE_PROGRESS.json`

La auditoría final prevalece frente a cualquier declaración anterior de terminado que no esté demostrada por CI sobre el mismo SHA completo.

## Continuidad automática

No preguntar si debe pasar a la siguiente corrección o bloque. Continuar automáticamente con la siguiente tarea independiente disponible.

Detenerse únicamente ante:

- riesgo destructivo;
- decisión irreversible;
- credencial externa faltante;
- cambio de `main`, producción, AWS, Coolify o DNS;
- fusión, tag, release o despliegue;
- ambigüedad funcional que no pueda resolverse con la matriz y el código.

## Protocolo obligatorio del monitor en tiempo real

El panel local lee `docs/nexora/LIVE_PROGRESS.json`. Mantenerlo como JSON válido y actualizarlo antes y después de cada grupo de trabajo, de cada prueba y de cada corrección importante.

No escribir ningún porcentaje manual. El porcentaje real lo calcula el monitor exclusivamente desde las 166 filas de `MATRIZ_REQUISITOS.md`.

Campos obligatorios:

- `agent_status`: `idle`, `working`, `blocked` o `finished`
- `phase`: fase real actual
- `current_block`: número 0–20 o `null`
- `task`: acción exacta en ejecución
- `detail`: resultado o contexto verificable
- `started_at`: fecha/hora ISO-8601
- `last_update`: fecha/hora ISO-8601
- `blocking_issue`: texto o `null`
- `tests`: lista de pruebas recientes
- `events`: lista de eventos recientes
- `block_overrides`: solo para marcar `running` o `failed`; nunca para fingir que un bloque pasó

Cada entrada de `tests` debe incluir cuando aplique:

```json
{
  "name": "nombre legible",
  "command": "comando exacto",
  "status": "running|passed|failed|skipped",
  "detail": "resultado real o error",
  "started_at": "ISO-8601",
  "finished_at": "ISO-8601 o null"
}
```

Reglas:

1. Antes de ejecutar una prueba, añadirla como `running`.
2. Al terminar, cambiarla a `passed`, `failed` o `skipped` con el resultado real.
3. Ante fallo, marcar `agent_status` como `working` si puede corregirse, o `blocked` si requiere intervención.
4. Mantener como máximo las 100 pruebas y 100 eventos más recientes.
5. No borrar fallos para hacer ver el panel verde.
6. Al hacer push, registrar el SHA completo.
7. Al consultar GitHub Actions, registrar run, job, conclusión y enlace en `events`.
8. Un bloque solo puede quedar verde cuando todas sus filas tienen estado final permitido y evidencia real.

## Estados finales permitidos en la matriz

Solo cuentan para el porcentaje real:

- `IMPLEMENTADO Y VALIDADO`
- `OBSOLETO JUSTIFICADO`
- `NO APLICA JUSTIFICADO`

`CONFIRMADO`, `PROPUESTO`, `EXISTENTE PERO DEFECTUOSO`, `EXISTENTE Y REUTILIZABLE`, `REQUIERE DECISIÓN` y `NO DEMOSTRADO` no cuentan como terminados.

No realizar reemplazos masivos de estados. Resolver y evidenciar cada fila individualmente.

## Corrección de CI obligatoria

Corregir todos los fallos descritos en `docs/nexora/AUDITORIA_CORRECCION_FINAL.md`, empezando por:

1. inventario canónico y gobierno;
2. contratos estáticos de aplicación y servidor;
3. archivos no Python;
4. puertas financieras deterministas;
5. instalación y migración real en Frappe/MariaDB;
6. desinstalación, reinstalación, seed idempotente, concurrencia y rollback.

No debilitar workflows mediante `continue-on-error`, exclusiones artificiales, pruebas vacías, mocks autorreferenciales o reducción de alcance.

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
- tags o releases
- despliegue
- producción, AWS, Coolify o DNS
- lectura o publicación de secretos

## Criterio de terminado

No declarar NEXORA terminado hasta que, sobre el mismo SHA completo:

- los 166 requisitos estén resueltos con evidencia individual;
- todos los workflows obligatorios estén verdes;
- instalación/migración, uninstall/reinstall y seed doble pasen;
- permisos, finanzas, concurrencia y rollback pasen;
- persistencia, backup y restore aislado estén demostrados;
- UX móvil/iPhone y PWA estén demostradas;
- matriz, checkpoint, `EXECUTION_STATE.md` y PR #12 sean coherentes;
- no exista fusión, tag ni despliegue sin autorización expresa.
