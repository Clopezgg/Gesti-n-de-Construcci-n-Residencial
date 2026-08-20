# Runbook: inicialización segura y reset de un entorno NEXORA

**Estado:** procedimiento documentado, pendiente de ejecución real en un
entorno con acceso a Coolify/AWS (fuera del alcance de este repositorio). No
existe ningún script en este repositorio que ejecute un reset destructivo de
forma automática — este documento es intencionalmente un procedimiento para
que lo ejecute una persona con acceso real, no una herramienta que lo ejecute
sola.

## Decisión oficial (recordatorio)

**NO se migran registros históricos de negocio del sistema anterior.** Solo se
migran esquema y catálogos técnicos. Verificado en código (Bloque 159, este
mismo commit):

- `nexora_app/nexora/patches.txt` tiene un único patch
  (`create_sequence_counter`) y crea únicamente una tabla técnica de contador
  — cero inserción de datos de negocio.
- `nexora_app/nexora/install.py::after_migrate()` llama solo a
  `seed_analytic_catalogs()` (`financial/seeds.py`), que únicamente
  crea/actualiza catálogos de sistema (`NXR Economic Category`,
  `NXR Operation Type`, marcados `system_managed: 1`) — nunca proyectos,
  contratos, entidades ni operaciones.
- `financial/seeds.py::seed_demo_data()` (proyectos, entidad y operaciones de
  ejemplo) existe solo para poblar un entorno de staging con datos de
  demostración — está gateado por `_require_staging_site()`, que exige
  `nexora_staging = 1` en la configuración del sitio y lanza
  `frappe.throw()` si no está presente, y además exige rol de
  System Manager/Administrator. No se llama desde `hooks.py`, `install.py`
  ni ningún patch — solo se ejecuta si alguien la invoca explícitamente
  (`bench execute nexora.financial.seeds.seed_demo_data`) contra un sitio ya
  marcado como staging.
- `install.py::before_uninstall()` **bloquea** la desinstalación si el sitio
  ya tiene `NXR Operation` reales — no permite un reset accidental de un
  sitio con operaciones reales.

## A. Inicializar un entorno NUEVO (sitio limpio)

Aplica a: un ambiente de staging o producción que todavía no existe, o un
sitio Frappe recién creado sin datos de negocio.

1. Crear el sitio Frappe (`bench new-site <site>`), fuera del alcance de este
   repositorio — requiere acceso al servidor/Coolify.
2. Instalar la app: `bench --site <site> install-app nexora`.
   - Ejecuta `after_install()`: crea moneda HNL, país Honduras, los cinco
     roles base de NEXORA, y fija `nexora-dashboard` como página de inicio.
     Ningún dato de negocio.
3. Migrar: `bench --site <site> migrate`.
   - Ejecuta `after_migrate()`: siembra únicamente los catálogos técnicos
     (`seed_analytic_catalogs()`). Ningún dato de negocio.
4. **Resultado esperado:** sitio con NEXORA instalado, catálogos de sistema
   poblados, cero proyectos/contratos/operaciones. Confirmar con:
   ```
   bench --site <site> execute frappe.db.count --args "['NXR Operation']"
   ```
   debe devolver `0`.
5. Si el entorno es de staging y se necesita un panel ejecutivo con datos de
   ejemplo para demostración/QA visual:
   - Fijar `nexora_staging: 1` en `site_config.json` del sitio (no en
     producción).
   - `bench --site <site> execute nexora.financial.seeds.seed_demo_data`
     (requiere sesión de Administrator/System Manager).
   - Verificar con `bench --site <site> execute nexora.financial.seeds.assert_staging_health`.

## B. Reset de un entorno EXISTENTE (staging con datos de prueba viejos)

Aplica solo a un sitio de staging/QA, nunca a producción con datos reales.

1. **Respaldo obligatorio primero**, sin excepción:
   `bench --site <site> backup --with-files`, y confirmar que el archivo de
   respaldo resultante existe y tiene tamaño distinto de cero antes de
   continuar.
2. Confirmar que el sitio es efectivamente de staging (no producción):
   revisar `site_config.json` → `nexora_staging` debe ser `1`, y el dominio
   no debe ser el de producción.
3. Si el reset es "borrar todo y reinstalar":
   - `bench --site <site> uninstall-app nexora` — este comando ejecuta
     `before_uninstall()`, que **rechaza la operación** (`frappe.throw`) si
     el sitio contiene `NXR Operation` reales. Si eso ocurre, es una señal
     real de que el sitio no es un staging descartable — detener el
     procedimiento y confirmar con el responsable antes de forzar nada.
   - Si el bloqueo no se dispara (sitio efectivamente sin operaciones o ya
     limpio), reinstalar con `bench --site <site> install-app nexora` y
     seguir el procedimiento A desde el paso 3.
4. Si el reset es "solo volver a sembrar los datos de demostración" (sin
   reinstalar la app): los `idempotency_key` fijos de `seed_demo_data()`
   (`nexora-staging-01-*`) hacen que reejecutarla sobre el mismo staging
   actualice/reutilice los mismos registros de ejemplo en vez de duplicarlos
   — seguro de reejecutar tal cual.

## C. Rollback

- Si un `install-app`/`migrate` falla a medio camino: restaurar el respaldo
  tomado en B.1 (`bench --site <site> restore <archivo>`).
- Si `seed_demo_data()` deja el staging en un estado inconsistente: como es
  idempotente por clave, volver a ejecutarla corrige los registros que
  gestiona directamente; para un reset completo, usar el respaldo de B.1.
- Ninguna de las rutas de este documento toca AWS, Coolify, DNS, secretos ni
  volúmenes — eso permanece fuera del alcance de este repositorio y requiere
  autorización expresa, respaldo verificable y plan de rollback específico
  del proveedor, según lo exige la política de este proyecto.

## Evidencia de que este runbook describe el código real, no una suposición

Verificado leyendo directamente (no asumido):
`nexora_app/nexora/install.py`, `nexora_app/nexora/patches.txt`,
`nexora_app/nexora/patches/v0_1/create_sequence_counter.py`,
`nexora_app/nexora/financial/seeds.py` (`seed_analytic_catalogs`,
`_require_staging_site`, `seed_demo_data`, `assert_staging_health`).

## Pendiente real

Este runbook no se ha ejecutado contra un entorno real — no hay acceso a
Coolify/AWS desde este repositorio. **PENDIENTE DE VALIDACIÓN DE
PRODUCCIÓN.** Cuando alguien con acceso lo ejecute, debe registrar aquí (o en
`EXECUTION_STATE.md`) la evidencia real: salida de los comandos, confirmación
del conteo de `NXR Operation` tras un sitio nuevo, y el archivo de respaldo
generado antes de cualquier reset.
