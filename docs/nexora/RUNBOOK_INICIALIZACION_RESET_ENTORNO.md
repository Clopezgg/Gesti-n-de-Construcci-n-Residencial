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

## Identificación exacta de qué es "registro histórico de negocio" (cierre de producción, Paso 5)

Verificada leyendo el árbol real de DocTypes (`nexora_app/nexora/nexora/doctype/`,
50 DocTypes independientes de NEXORA, ninguna tabla hija contada aparte —
cascadea con su padre real), clasificados en
`nexora_app/nexora/financial/reset_readiness.py`, con un test de contrato
(`test_reset_readiness_contract.py`) que falla si la clasificación deja de
cubrir exactamente los DocTypes reales del repositorio:

- **Registros transaccionales** (21 DocTypes: `NXR Operation`, `NXR Fund
  Source`, `NXR Contract`, `NXR Purchase Order`, `NXR Weekly Close`, etc. —
  lista completa en `TRANSACTIONAL_BUSINESS_DOCTYPES`). Esto es lo que un
  lanzamiento limpio de producción debe empezar en cero — la lectura más
  directa de "mis registros históricos de negocio".
- **Datos maestros, requiere decisión** (8 DocTypes: `NXR Entity` y sus
  sub-registros, `NXR Warehouse`, `NXR Financial Account`, `NXR Contractor
  Profile`, `NXR Supplier Profile` — `MASTER_DATA_REQUIRES_DECISION`).
  Describen entidades del mundo real (proveedores, bodegas, cuentas), no
  eventos fechados — probablemente deben sobrevivir a un reset, pero es una
  decisión de producto, no algo que este runbook decida solo.
- **Bitácora y sistema** (10 DocTypes: `NXR Audit Event`, `NXR Document
  Sequence`, `NXR Conversation`, etc. — `AUDIT_AND_SYSTEM_LOG_DOCTYPES`).
  Referencian los registros transaccionales; limpiar estos sin tocar aquellos
  deja una bitácora huérfana. `NXR Document Sequence` en particular: si no se
  reinicia junto con los registros transaccionales, la numeración de
  documentos nuevos no vuelve a empezar en 1.
- **Configuración, nunca se toca** (7 DocTypes: `NXR AI Provider`, `NXR
  Channel Account`, `NXR Integration`, `NXR SAP Connection`, `NXR SAP Field
  Mapping`, etc. — `CONFIGURATION_DOCTYPES_NEVER_PURGED`). Un reset de datos
  de negocio no debe obligar a reconfigurar cómo se conecta el sistema a SAP,
  WhatsApp o un proveedor de IA, ni a recrear el catálogo de mapeos de campo
  SAP ya definido.
- **Catálogos técnicos, nunca se tocan** (`NXR Economic Category`, `NXR
  Operation Type` — ya documentados en el Bloque 159, `system_managed: 1`).

**Conteo real, de solo lectura, seguro de ejecutar en cualquier momento
—incluida producción, ahora mismo, sin que se haya decidido ningún reset
todavía—:**
```
bench --site <site> execute nexora.financial.reset_readiness.count_business_records
```
Devuelve el conteo real por DocType en cada una de las cinco categorías de
arriba, más el total de usuarios de sistema. Esto es el "conteo previo" (y,
ejecutado de nuevo después de cualquier reset real, el "conteo posterior")
que este runbook exige — nunca estimado, siempre la cifra real de la base de
datos consultada en el momento.

**Sobre el principio de libro inmutable:** el resto del código de NEXORA
nunca borra un registro financiero directamente (`test_safe_archive_contract.py`
lo verifica: anular una fuente de fondos es una reversión compensatoria
auditada, nunca un `delete_doc`) — las correcciones se registran, no se
esconden. Esto NO entra en conflicto con un reset de entorno completo (Sección
B: desinstalar y reinstalar la app borra las tablas enteras junto con toda su
estructura, no elimina registros individuales de un libro que sigue vivo). Sí
entraría en conflicto con una "purga selectiva en un sitio que sigue en
producción" — borrar solo algunos documentos mientras el resto del sistema
sigue operando activamente contradice ese mismo principio y **no está
construida en este repositorio a propósito**. Si el objetivo real es limpiar
datos de un sitio que debe seguir vivo (no un reset completo de ambiente),
eso es una decisión de producto nueva, distinta de este runbook, que
requeriría diseñar su propio mecanismo auditado — no algo que deba
improvisarse ejecutando `frappe.delete_doc` a mano contra producción.

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

1. **Conteo previo, real, antes de tocar nada:**
   `bench --site <site> execute nexora.financial.reset_readiness.count_business_records`
   — registrar la salida completa (o en `EXECUTION_STATE.md`) antes de
   continuar.
2. **Respaldo obligatorio**, sin excepción:
   `bench --site <site> backup --with-files`, y confirmar que el archivo de
   respaldo resultante existe y tiene tamaño distinto de cero antes de
   continuar.
3. Confirmar que el sitio es efectivamente de staging (no producción):
   revisar `site_config.json` → `nexora_staging` debe ser `1`, y el dominio
   no debe ser el de producción.
4. Si el reset es "borrar todo y reinstalar":
   - `bench --site <site> uninstall-app nexora` — este comando ejecuta
     `before_uninstall()`, que **rechaza la operación** (`frappe.throw`) si
     el sitio contiene `NXR Operation` reales. Si eso ocurre, es una señal
     real de que el sitio no es un staging descartable — detener el
     procedimiento y confirmar con el responsable antes de forzar nada.
   - Si el bloqueo no se dispara (sitio efectivamente sin operaciones o ya
     limpio), reinstalar con `bench --site <site> install-app nexora` y
     seguir el procedimiento A desde el paso 3.
5. Si el reset es "solo volver a sembrar los datos de demostración" (sin
   reinstalar la app): los `idempotency_key` fijos de `seed_demo_data()`
   (`nexora-staging-01-*`) hacen que reejecutarla sobre el mismo staging
   actualice/reutilice los mismos registros de ejemplo en vez de duplicarlos
   — seguro de reejecutar tal cual.
6. **Conteo posterior, real, para confirmar el resultado:** repetir el
   comando del paso 1 y comparar contra la salida registrada antes de
   empezar — la evidencia de que el reset hizo exactamente lo esperado, no
   una suposición.

## B2. El sitio ya tiene registros reales del usuario (no es staging descartable)

Este es el escenario que describió el propietario del producto: un entorno
que ya se ha usado de verdad, con `NXR Operation`/`NXR Fund Source`/etc.
reales creados por él mismo, y que debe quedar limpio antes del lanzamiento
definitivo. **No es el caso que cubre la Sección B** — ese procedimiento es
explícitamente solo para staging descartable, y `before_uninstall()`
**rechazará la operación por diseño** en cuanto detecte una sola `NXR
Operation` real, exactamente la situación descrita aquí. Eso no es un error
que rodear: es la protección contra pérdida accidental de datos funcionando
como se construyó (ver `install.py::before_uninstall()`, Bloque 159).

Para este escenario específico, este runbook **no ejecuta nada por su
cuenta** — deja el procedimiento exacto para que lo ejecute
conscientemente quien tiene autoridad real sobre esos datos:

1. **Conteo previo real** (mismo comando de la Sección B.1) — registrar la
   cifra exacta de lo que se va a perder, por categoría, antes de decidir.
2. **Respaldo verificable** (mismo comando de B.2) — sin este paso, no hay
   forma de deshacer la decisión.
3. **Decisión explícita y documentada** de quién autoriza el reset y bajo
   qué alcance exacto — ¿solo los DocTypes transaccionales, o también los
   datos maestros (`MASTER_DATA_REQUIRES_DECISION`)? ¿se conserva la
   bitácora de auditoría del período anterior o se limpia también? Esa
   decisión no la toma este runbook.
4. Con esa decisión tomada, **`bench --site <site> uninstall-app nexora`
   seguido de `install-app`** es el mecanismo real y ya construido (mismo
   flujo que A/B) — rechazará la operación hasta que quien lo ejecuta
   confirme conscientemente que el bloqueo de `before_uninstall()` es
   correcto y aun así procede (leyendo su código real: el `frappe.throw`
   se dispara sobre una condición explícita y legible, no hay una bandera
   oculta de "forzar" en este repositorio, ni la habrá sin una decisión de
   producto aparte). Una purga selectiva que borre documentos de negocio
   uno por uno mientras el sitio sigue en producción activa **no existe en
   este repositorio** (ver la nota sobre el libro inmutable arriba) y no se
   improvisa aquí.
5. **Conteo posterior real** (mismo comando) — confirmar que cada categoría
   quedó exactamente como se decidió en el paso 3, ni más ni menos.

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
`_require_staging_site`, `seed_demo_data`, `assert_staging_health`),
`nexora_app/nexora/financial/reset_readiness.py` (clasificación completa de
los 50 DocTypes independientes de NEXORA, verificada 1:1 contra el árbol
real de DocTypes por `test_reset_readiness_contract.py`),
`nexora_app/nexora/tests/test_safe_archive_contract.py` (principio de libro
inmutable, sin `delete_doc` en las rutas de corrección/anulación).

## Pendiente real

Este runbook no se ha ejecutado contra un entorno real — no hay acceso a
Coolify/AWS desde este repositorio. **PENDIENTE DE VALIDACIÓN DE
PRODUCCIÓN.** Cuando alguien con acceso lo ejecute, debe registrar aquí (o en
`EXECUTION_STATE.md`) la evidencia real: salida completa de
`count_business_records` (antes y después), confirmación del conteo de `NXR
Operation` tras un sitio nuevo, el archivo de respaldo generado antes de
cualquier reset, y — para el escenario B2 — quién autorizó el reset y con
qué alcance exacto.
