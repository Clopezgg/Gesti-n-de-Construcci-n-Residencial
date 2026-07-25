# NEXORA — Auditoría y orden de corrección final

## Mandato

Este documento invalida cualquier declaración prematura de finalización y ordena corregir NEXORA sobre la rama `nexora-continuidad-total`, PR #12, sin fusionar, etiquetar ni desplegar.

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama única: `nexora-continuidad-total`
- PR único de continuidad: `#12`
- Base del PR #12: `nexora-reconstruccion`
- `main`: protegida
- Producción, AWS, Coolify y DNS: prohibido modificar

## Estado remoto verificado

HEAD auditado antes de este documento:

`bae7c022cfc4b9e07d275a89d383562e0542201b`

El PR #12 seguía abierto, sin fusionar. El HEAD había declarado los Bloques 19–20 como implementados y validados, pero sus controles remotos no estaban verdes.

## Fallos confirmados del mismo HEAD

1. **Read-only non-Python patch control**
   - Run `30138268248`
   - Job `89626407386`
   - Falló: `Validate changed non-Python sources without writing repository state`

2. **Read-only static server control**
   - Run `30138268286`
   - Job `89626406880`
   - Falló: `Verify server contracts even when no Python file changed`

3. **NEXORA governance**
   - Run `30138268235`
   - Job `89626406694`
   - Falló: `Verify canonical repository inventory`

4. **NEXORA financial invariants**
   - Run `30138268245`
   - Job `89626406717`
   - Falló: `Static and deterministic gates`
   - La instalación, MariaDB, concurrencia e idempotencia quedaron omitidas por el fallo temprano.

5. **NEXORA app — contrato**
   - Run `30138268266`
   - Job `89626406810`
   - Falló: `Validate NEXORA app, models, services and UI`

6. **NEXORA app — instalación/rollback**
   - Run `30138268266`
   - Job `89626406852`
   - Falló: `Install and migrate NEXORA`
   - Desinstalación, reinstalación, fixtures y seed quedaron omitidos.

Solo estaban aprobados `Linters`, `Semantic Commits` y `Documentation Required`. Por tanto, el sistema no estaba certificado.

## Contradicciones documentales confirmadas

`EXECUTION_STATE.md` declara los Bloques 7–20 como `IMPLEMENTADO Y VALIDADO`, pero `docs/nexora/MATRIZ_REQUISITOS.md` conserva filas con estados no finales, entre ellas:

- `NXR-GOV-0003`: `EXISTENTE PERO DEFECTUOSO`
- `NXR-FND-0005`: `EXISTENTE PERO DEFECTUOSO`
- `NXR-LCO-0001`: `PROPUESTO`
- `NXR-LCO-0004`: `PROPUESTO`
- `NXR-CCO-0004`: `REQUIERE DECISIÓN`
- `NXR-INF-0002` a `NXR-INF-0005`: `EXISTENTE Y REUTILIZABLE`
- `NXR-INF-0007`: `REQUIERE DECISIÓN`
- `NXR-INF-0009`: `NO DEMOSTRADO`
- `NXR-QA-0007`: `EXISTENTE PERO DEFECTUOSO`
- `NXR-FND-0020`: `PROPUESTO`

No existe certificación 166/166 mientras una fila no esté en uno de estos estados finales con evidencia individual:

- `IMPLEMENTADO Y VALIDADO`
- `OBSOLETO JUSTIFICADO`
- `NO APLICA JUSTIFICADO`

También se detectó:

- uso de SHA abreviado en la certificación de numerosos bloques;
- ausencia previa de `docs/nexora/CHECKPOINT.md`;
- cuerpo del PR #12 documentado solamente hasta el Bloque 6;
- afirmaciones standalone presentadas como certificación integral pese a fallos de instalación y CI.

## Orden obligatoria de corrección

### Fase 1 — sincronización segura

1. Confirmar `nexora-continuidad-total`.
2. Revisar `git status --short`.
3. Actualizar solo mediante fast-forward.
4. Capturar HEAD completo.
5. No crear rama ni PR.
6. No destruir cambios locales.

### Fase 2 — reproducir cada fallo exacto

Para cada workflow fallido:

1. localizar su YAML en `.github/workflows/`;
2. extraer el comando exacto del step fallido;
3. leer el log remoto completo;
4. reproducir localmente cuando sea viable;
5. registrar archivo, línea y causa raíz;
6. corregir sin debilitar el control;
7. prohibido usar `continue-on-error`, omisiones artificiales o pruebas autorreferenciales.

### Fase 3 — prioridad de corrección

1. **Inventario y gobierno**: archivos nuevos, conteos, rutas, DocTypes, hooks, fixtures, módulos y workspace.
2. **Contratos estáticos**: imports, JSON/controladores, servicios whitelisted, páginas, rutas, roles, campos y referencias cruzadas.
3. **No-Python**: JS, JSON, HTML, CSS, YAML y Markdown; el verificador debe pasar dos veces sin modificar el árbol.
4. **Puertas financieras**: saldos, idempotencia, locks, rollback, reservas, compras, inventario, presupuestos y Libro Central.
5. **Instalación real**: sitio limpio Frappe/ERPNext + MariaDB, `install-app`, `migrate`, migraciones repetidas, uninstall, reinstall y seed doble.

### Fase 4 — auditoría fila por fila

Recorrer las 166 filas sin reemplazos masivos. Cada requisito debe registrar:

- archivo de implementación;
- prueba positiva;
- prueba negativa;
- permiso server-side;
- idempotencia/concurrencia/rollback cuando aplique;
- workflow, run y job;
- artifact y digest cuando corresponda;
- SHA completo de 40 caracteres.

Lo no demostrado permanece pendiente.

### Fase 5 — coherencia documental

Después de corregir código y pruebas:

1. crear/actualizar `docs/nexora/CHECKPOINT.md`;
2. corregir `EXECUTION_STATE.md` con estado real;
3. corregir la matriz fila por fila;
4. actualizar Bloques 7–20;
5. actualizar el cuerpo del PR #12;
6. eliminar afirmaciones sin evidencia remota.

### Fase 6 — cierre técnico sin fusión

1. pruebas específicas;
2. regresión completa;
3. `pre-commit run --all-files` dos veces;
4. Semgrep;
5. revisión de diff/status;
6. commits semánticos por causa raíz;
7. push solo a `origin/nexora-continuidad-total`;
8. esperar Actions del nuevo SHA;
9. corregir todo fallo nuevo;
10. repetir hasta que todos los controles obligatorios estén verdes en el mismo SHA.

## Criterio final

No declarar terminado hasta cumplir simultáneamente:

- 166/166 con evidencia individual;
- todos los workflows obligatorios verdes sobre el mismo SHA completo;
- instalación/migración, uninstall/reinstall y seed idempotente aprobados;
- finanzas, permisos, concurrencia y rollback aprobados;
- persistencia, backup y restauración aislada demostrados;
- móvil/PWA demostrado;
- matriz, checkpoint, estado y PR coherentes;
- cero tags, cero fusión, cero `main`, cero producción.

## Prohibiciones

No ejecutar:

- `git push origin main`
- `git push --force`
- `git reset --hard`
- `git clean -fd`
- borrado masivo
- merge/cierre de PR #11 o #12
- tags o releases
- despliegue
- AWS/Coolify/DNS
- publicación de secretos

El agente debe continuar automáticamente con la siguiente corrección independiente y detenerse solo ante un bloqueo real, una decisión irreversible o un riesgo expresamente prohibido.