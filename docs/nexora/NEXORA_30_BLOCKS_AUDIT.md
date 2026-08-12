# NEXORA — Auditoría y reconstrucción de los 30 bloques

Documento de la misión final de auditoría y cierre. Reconstruye el alcance real de
cada bloque a partir de evidencia directa — no de memoria ni de lo que un documento
*dice* que se hizo — y declara el estado real de cada uno con el mismo criterio de
transparencia que ha regido toda la misión: código real + Git real + pruebas
realmente ejecutadas + comportamiento real, nunca una sola fuente.

## Metodología de esta auditoría

- Lectura directa de `EXECUTION_STATE.md` completo (3976 líneas al momento de este
  bloque), `git log` con SHA completos, y `docs/nexora/MATRIZ_REQUISITOS.md` (184
  filas, columna `BLOQUE`) como columna vertebral de qué requisito pertenece a qué
  bloque.
- Tres auditorías delegadas en paralelo (bloques 2-10, 11-18, 19-22), cada una con
  instrucciones explícitas de verificar una muestra de las afirmaciones más
  relevantes contra el código actual (no contra lo que el documento dice), y de
  señalar cualquier reclamo fabricado como hallazgo propio y distinto.
- Bloques 23-30: conocimiento directo de primera mano — son los bloques que esta
  misma sesión ejecutó, con PR, CI y SHA verificados en cada uno.
- Ninguna afirmación de este documento sobre "el código hace X" se apoya solo en un
  documento anterior sin una verificación directa (grep/lectura) en esta ronda o en
  una ronda anterior de esta misma sesión.

## Nota crítica sobre la numeración — no hay una sola secuencia "1 a 30"

Existen **tres numeraciones reales y distintas**, coexistiendo en el repositorio.
Ninguna es falsa; cada una responde a un momento distinto de la misión. Forzarlas a
una sola secuencia falsificaría la historia real, así que se documentan las tres:

1. **La columna `BLOQUE` de `MATRIZ_REQUISITOS.md`** — la numeración de dominio
   original: qué bloque de construcción posee cada requisito. Va de `BLOQUE 0`
   (gobierno) a `BLOQUE 26` (`NXR-CAL-0001`). Es la que se usa como columna
   vertebral de este documento porque es la única atada, fila por fila, a un
   requisito trazable con estado real.
2. **`docs/nexora/BLOQUE_N_*.md`** (N = 2 a 18) — los documentos de construcción
   original de cada dominio (Finanzas, Libro Central, Evidencia, Entidades,
   Contratos, Compras/Proveedores, Órdenes/Recepciones, Inventario, Presupuestos,
   Buscador/Dashboard, Reportes, Avance/Calidad, Notificaciones, Usuarios/Roles,
   Cierres/Correcciones, Integraciones, Identidad/PWA), fechados alrededor de
   2026-07-24, con su propio SHA "funcional certificado" por bloque. Coinciden con
   la numeración de dominio de la matriz.
3. **Los encabezados cronológicos `## Bloque N` de `EXECUTION_STATE.md`** — el
   diario real de sesiones de trabajo, sin garantía de que el número N coincida con
   el dominio N. Confirmado con fechas y SHA reales: **para los números 2, 7,
   10-18, el "Bloque N" cronológico de `EXECUTION_STATE.md` es una sesión de
   *corrección* posterior (fechada 2026-08-10, "misión de auditoría de brechas"),
   sobre un tema distinto al "Bloque N" de construcción original.** Ejemplo real:
   el "Bloque 11" cronológico corrige un bug de propagación de fechas
   dashboard→reportes; el "Bloque 11" de dominio (`BLOQUE_11_BUSCADOR_DASHBOARD.md`)
   es el buscador universal. Ambos son reales; solo comparten número por
   coincidencia de una sesión de corrección que se numeró igual que el dominio que
   tocaba tangencialmente. El propio `NIP_BLOQUE_6_CONVERSATIONAL_OS.md` advierte
   explícitamente de esta colisión en su propio encabezado.
   **Para los números 19-30, no hay colisión**: el "Bloque N" cronológico de
   `EXECUTION_STATE.md` y el "Bloque N" de dominio de la matriz son la misma sesión
   de trabajo (verificado con SHA y fecha en cada caso).
4. **Una cuarta numeración interna, anidada, no confundir con las anteriores:**
   `docs/nexora/NIP_BLOQUE_1` a `NIP_BLOQUE_6` — la numeración propia de "NEXORA
   Intelligence Platform" (el motor de IA), que vive *dentro* de lo que la matriz
   llama `BLOQUE 18`/`BLOQUE 20`. Su "Bloque 6" (Conversational OS) no es el mismo
   concepto que el "Bloque 6" de dominio (Contratos) ni que ningún "Bloque 6" de
   `EXECUTION_STATE.md`.

No se fuerza ninguna de las cuatro a coincidir con las demás. Este documento usa la
numeración de dominio (columna `BLOQUE` de la matriz) como esqueleto, y anota en cada
entrada cuál sesión cronológica de `EXECUTION_STATE.md` la construyó o la corrigió.

---

## Bloque 0 — Gobierno y arquitectura documental

**Requisitos:** `NXR-GOV-0001` a `NXR-GOV-0011`, `NXR-INF-0001/0006/0007/0009` (15,
todos `IMPLEMENTADO Y VALIDADO`).
**Código/evidencia real:** existencia y coherencia cruzada de
`ARQUITECTURA.md`, `PLAN_MAESTRO.md`, `CATALOGO_MAQUINAS_ESTADO.md` (37 máquinas),
`CATALOGO_CONTROLES.md` (32 controles + 9 pruebas compartidas), `DECISIONES.md` (19
decisiones), `MATRIZ_REQUISITOS.md`, `EXECUTION_STATE.md` — todos activamente
mantenidos y verificados por `scripts/validate_nexora_governance.py` en cada bloque
de esta misión (verde en el último run: 184 requisitos, 38 máquinas, 32 controles, 9
pruebas, 19 decisiones).
**Estado real:** cerrado. Es meta-documentación que se demuestra por su propia
existencia y consistencia cruzada, ya verificada de forma continua durante toda la
sesión 23-30.
**Criterio de cierre:** cumplido (auto-evidente, verificado por validador ejecutable).

## Bloque 1 — Libro Central (fundacional) y documentación transaccional

**Requisitos:** `NXR-LCO-0002/0005/0006/0008/0009`, `NXR-DOC-0001` (6, todos
`IMPLEMENTADO Y VALIDADO`).
**Sesión cronológica relacionada:** `EXECUTION_STATE.md` "Bloque 1.1" (cierre formal
de fase 1, solo alineación documental de identidad NEXORA, sin tocar backend/
frontend/permisos). Commit publicado: `18f7219a3ae4d566c502090b2543c84e11d89768`.
**Estado real:** cerrado a nivel de requisito trazable; el propio `EXECUTION_STATE.md`
anota `NXR-CONS-001` (consolidación de identidad) como `NO DEMOSTRADO` como
requisito independiente — no forma parte de estos 6 IDs y no se ha reclasificado.
**Criterio de cierre:** cumplido para los 6 IDs trazables.

## Bloque 2 — Núcleo financiero y Fondos

**Requisitos:** `NXR-FND-0001` a `NXR-FND-0019` (`IMPLEMENTADO Y VALIDADO`),
`NXR-FND-0020` (`NO DEMOSTRADO`) — 20 total.
**Código verificado en esta ronda:** `financial/service.py` es una fachada que
reexporta exactamente las funciones reales (`create_fund_source`,
`list_source_balances`, `preview_financial_operation`, `execute_financial_operation`,
`create_commitment`, `execute_commitment`, `release_commitment`);
`cancel_fund_source` vive en `financial/sources.py`. DocTypes `NXR Fund Source`,
`NXR Operation Effect`, `NXR Commitment` existen y coinciden con la descripción.
**Sesión cronológica relacionada (distinta, ver nota de numeración):**
`EXECUTION_STATE.md` "Bloque 2" (2026-08-04) es una corrección quirúrgica posterior
—páginas en blanco por resolución de assets de Frappe, `nexora-finance` sin roles
declarados (abierta a todo el sitio autenticado), workspace con 15 de 21 accesos
directos invisibles— más los sub-bloques 2.1 (contexto activo propagado a 5 páginas
más), 2.2 (5 páginas ausentes de la barra superior), 2.3 (formato monetario crudo sin
`Intl.NumberFormat` en `nexora-finance`), 2.4 (precaché PWA incompleto), 2.5 (token
CSS huérfano), 2.6 (helpers `money`/`date`/`escape`/`uuid` duplicados consolidados).
Todas corregidas con pruebas de regresión propias
(`test_page_registry_contract.py`, `test_active_context_contract.py`,
`test_financial_ui_contract.py`, `test_pwa_contract.py`).
**Concurrencia/idempotencia (verificado directamente en código, no solo en
prosa):** `FOR UPDATE`/lock real en `financial/db.py`, `sources.py`,
`commitments.py`, `references.py`, `evidence.py`, `corrections.py`;
`start_idempotency`/`complete_idempotency` (definidos en `financial/db.py`)
verificados con 214 puntos de uso reales en financiero+contratos+compras+
inventario+presupuesto — no es un mecanismo aislado ni solo declarado.
**Estado real:** cerrado en código y pruebas; el permiso abierto de `nexora-finance`
y las páginas en blanco eran defectos reales de producción ya corregidos con
evidencia y prueba de regresión.
**Criterio de cierre:** cumplido para 19/20 IDs; `NXR-FND-0020` sigue `NO DEMOSTRADO`
por requerir ejecución real (bench/MariaDB) no disponible en este entorno.

## Bloque 3 — Libro Central de Operaciones y Centros de Costo

**Requisitos:** `NXR-LCO-0001/0003/0004/0010/0011`, `NXR-CCO-0001/0002/0003/0005`
(`IMPLEMENTADO Y VALIDADO`), `NXR-CCO-0004` (`NO DEMOSTRADO`) — 10 total.
**Código verificado:** DocTypes `NXR Operation Type`/`NXR Economic Category`
existen; `financial/corrections.py` y `financial/references.py` contienen la
reclasificación, devolución real, reversión (`reverses_effect`) y anticipo/
liquidación descritos en la documentación de dominio original.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido para 9/10; `NXR-CCO-0004` `NO DEMOSTRADO`.

## Bloque 4 — Integridad financiera, idempotencia y evidencia documental

**Requisitos:** `NXR-LCO-0007/0012`, `NXR-DOC-0004/0008` (4, todos `IMPLEMENTADO Y
VALIDADO`).
**Código verificado:** DocType `NXR Evidence` existe; `register_evidence`/
`review_evidence`/`list_evidence` son funciones `@frappe.whitelist` reales en
`financial/evidence.py`. `NXROperation.on_trash()` rechaza realmente la eliminación
de operaciones ejecutadas — respalda la inmutabilidad declarada, no es solo una
afirmación de documento.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido.

## Bloque 5 — Directorio Universal de Entidades

**Requisitos:** `NXR-ENT-0001` a `NXR-ENT-0008` (8, todos `IMPLEMENTADO Y
VALIDADO`).
**Código verificado:** los 6 DocTypes (`NXR Entity`, `_Identifier`, `_Contact`,
`_Role`, `_Compliance`, `_Consolidation`) existen; el módulo `directory/` tiene la
separación de servicios (lectura/escritura/duplicados/consolidación/cumplimiento/
rol) descrita.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido.

## Bloque 6 — Contratos, contratistas, adendas, anticipos, pagos y retenciones

**Requisitos:** `NXR-CON-0001` a `NXR-CON-0012` (12, todos `IMPLEMENTADO Y
VALIDADO`).
**Código verificado:** los 8 DocTypes de contrato existen; `contracts/service.py`
tiene la superficie whitelisted completa (crear/transicionar perfil, contrato,
adenda, estimación, desembolsar anticipo, ejecutar pago, devolver retención,
corregir transacción), con un helper de bloqueo `for_update` real que respalda
`NXR-CON-0009` (concurrencia).
**Estado real:** coincide con lo documentado — es, junto con el núcleo financiero,
el dominio más maduro y mejor probado del repositorio.
**Criterio de cierre:** cumplido.

## Bloque 7 — Compras y Proveedores (solicitud, aprobación, cotización)

**Requisitos:** `NXR-COM-0001/0002/0003/0007` (4, todos `IMPLEMENTADO Y
VALIDADO`).
**Código verificado:** `purchases/request_core.py`, `request_service.py`,
`quotation_core.py`, `quotation_service.py` y ambos DocTypes existen como se
describe.
**Nota de numeración:** el "Bloque 7" cronológico de `EXECUTION_STATE.md` es una
auditoría visual/responsive parcial y explícitamente incompleta ("auditoría visual
y corrección responsive quirúrgica (parcial)") — no es este dominio. No se fuerza la
coincidencia.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido.

## Bloque 8 — Órdenes de compra y recepciones

**Requisitos:** `NXR-COM-0004/0005/0006/0008/0009` (5, todos `IMPLEMENTADO Y
VALIDADO`).
**Código verificado:** `order_core.py`, `order_service.py`, `receipt_core.py`,
`receipt_service.py` y ambos DocTypes existen. `fund_source` está enlazado en
`order_service.py`; `check_budget_availability` existe en `budget/service.py` pero
se invoca de forma independiente, no como una única cadena de llamadas encajada
dentro de `create_order` — matiz real, no fabricación, y no cambia el estado del
requisito.
**Nota de numeración:** el "Bloque 8 y 9" cronológico de `EXECUTION_STATE.md` fueron
"cerrados por evidencia ya existente, sin re-trabajo" — auditoría, no reconstrucción.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido.

## Bloque 9 — Inventario y control físico

**Requisitos:** `NXR-INV-0001` a `NXR-INV-0007` y `NXR-INV-0009`
(`IMPLEMENTADO Y VALIDADO`), `NXR-INV-0008` (`NO DEMOSTRADO`) — 9 total.
**Código verificado:** `inventory/core.py` (`StockBalance`, reglas de transición) y
`inventory/service.py` (CRUD + idempotencia) existen como se describe.
**Estado real:** coincide con lo documentado.
**Criterio de cierre:** cumplido para 8/9; `NXR-INV-0008` `NO DEMOSTRADO`.

## Bloque 10 — Presupuestos y compromisos

**Requisitos:** `NXR-PRE-0001` a `NXR-0005` y `NXR-PRE-0007`
(`IMPLEMENTADO Y VALIDADO`), `NXR-PRE-0006` (`OBSOLETO JUSTIFICADO`) — 7 total.
**Código verificado:** `budget/core.py`/`budget/service.py` existen con todas las
funciones citadas (`assert_transition`, `compute_line_balances`,
`validate_no_overspend`, `create_budget`, `check_budget_availability`,
`reserve_budget_commitment`, etc.); `financial/commitments.py` importa y llama
`reserve_budget_commitment`/`release_budget_reservation`/`record_budget_execution`
dentro de un `savepoint()` real.
**Hallazgo real de esta auditoría (corregido en este mismo bloque de cierre):**
`docs/nexora/BLOQUE_10_PRESUPUESTOS_COMPROMISOS.md` afirmaba
`NXR-PRE-0006 | Pronóstico | CONFIRMADO`. No existe ni existió motor de pronóstico
(`grep` de "forecast"/"pronóstico" en `budget/*.py` y pruebas sin resultados). La
matriz **siempre** tuvo la clasificación correcta (`OBSOLETO JUSTIFICADO`, exclusión
de alcance decidida en `DEC-002`); solo el documento de dominio quedó desactualizado
desde su redacción original. **Corregido** en este bloque de cierre (ver sección de
correcciones abajo) — no es un reclamo fabricado activo, es un documento viejo que
nunca se sincronizó con la matriz.
**Estado real:** cerrado, con la corrección documental aplicada.
**Criterio de cierre:** cumplido.

## Bloque 11 — Buscador Universal y Dashboard

**Requisitos:** `NXR-UX-0005` (buscador), `NXR-UX-0006` (dashboard) — 2, ambos
`IMPLEMENTADO Y VALIDADO`.
**Código verificado:** `boot.py:360-390` (`universal_search_consolidated`) filtra
por `PROJECT_SCOPED_DOCTYPES` y usa `frappe.has_permission`; `dashboard/service.py`
respalda los indicadores del panel.
**Nota de numeración:** el "Bloque 11" cronológico de `EXECUTION_STATE.md`
(2026-08-10) es la corrección de propagación de rango de fechas
dashboard→reportes (`setDateRangeSilently`, `businessFilters`, `rangeChanged`) —
verificado presente en `nexora_reports.js` exactamente como se describe. Tema
distinto, mismo número por coincidencia de sesión.
**Estado real:** coincide con lo documentado; el bug de fechas fue una corrección
real posterior, ya cerrada.
**Criterio de cierre:** cumplido.

## Bloque 12 — Reportes, documentos, y auditoría maestra de brechas

**Requisitos "de construcción" (13, `IMPLEMENTADO Y VALIDADO`):** `NXR-REP-0001`
a `NXR-REP-0009`, `NXR-DOC-0002/0003/0007`.
**Requisitos "de brecha encontrada" (defectuosos/no demostrados, 3):**
`NXR-UX-0008` (Command Bar/Ctrl+K — `EXISTENTE PERO DEFECTUOSO`), `NXR-UX-0009`
(búsqueda en lenguaje natural — `NO DEMOSTRADO`, depende de `NXR-CNV-0001`),
`NXR-UX-0015` (captura de cámara nativa — `EXISTENTE PERO DEFECTUOSO`).
**Hecho central de este bloque:** la sesión cronológica "Bloque 12" de
`EXECUTION_STATE.md` ("auditoría maestra de brechas, misión NEXORA, sin cambios de
código") **es una ejecución previa de una misión casi idéntica a la que cerró este
mismo documento.** Produjo `NEXORA_GAP_ANALISIS_BLOQUE_12.md`,
`docs/nexora/NEXORA_GOLDEN_PATHS.md`, `NEXORA_UX_AUDIT.md` y
`NEXORA_EXPERIENCE_SYSTEM.md` — los mismos documentos finales que la misión actual
exige. Cada brecha que encontró se convirtió en un requisito trazable nuevo
(`NXR-UX-0008` a `NXR-UX-0015`, `NXR-COM-0010`, `NXR-PRE-0008`, `NXR-CNV-0001`) y
**todas, sin excepción, fueron cerradas o re-verificadas honestamente en los
bloques 13 a 30** que siguieron. No hay ninguna brecha del Bloque 12 que quedara
sin tocar.
**Re-verificado en este ciclo (Bloque 30, y confirmado otra vez ahora):**
`NXR-UX-0008` sigue sin Ctrl+K/paleta de comandos (cero coincidencias en
`public/js`/`public/css`); `NXR-UX-0015` sigue sin `capture="camera"` en ningún
campo `Attach` de evidencia, incluido el `photos` que el Bloque 25 añadió a
`nexora_progress.js` — ninguna de las dos brechas se cerró por accidente sin
actualizar su fila.
**Estado real:** cerrado como auditoría; las 3 brechas que produjo permanecen
honestamente abiertas donde corresponde (2 defectos de UX conocidos, 1 dependencia
de otro requisito).
**Criterio de cierre:** cumplido como bloque de auditoría (su producto era
documentación y hallazgos, no código).

## Bloque 13 — Integridad de recepción (sobre-recepción) y avance/calidad original

**Requisitos "de construcción" (3, `IMPLEMENTADO Y VALIDADO`):** `NXR-AVA-0001/
0002/0003`. **`NXR-AVA-0004`:** `OBSOLETO JUSTIFICADO`.
**Requisito de brecha:** `NXR-COM-0010` (sobre-recepción acumulada) —
`NO DEMOSTRADO`.
**Código verificado:** `_received_totals`/`compute_po_completion_status` en
`receipt_service.py`/`receipt_core.py` existen exactamente como se describe, con el
bloqueo real por tolerancia máxima acumulada (`cumulative > max_q` lanza error).
**Hecho honesto y verificado de este bloque:** la sesión cronológica lo marcó
primero `IMPLEMENTADO Y VALIDADO` y **luego se autocorrigió a `NO DEMOSTRADO`**
antes de pasar al bloque siguiente, con el razonamiento preservado en
`EXECUTION_STATE.md` — un ejemplo real de la disciplina de transparencia de la
misión funcionando, no un error escondido.
**Estado real:** código real, corrección real, sin ejecución real en bench/MariaDB
para confirmar el bloqueo contra un escenario de recepción parcial repetida.
**Criterio de cierre:** cumplido en código/prueba de contrato; pendiente de
ejecución real para el estado terminal.

## Bloque 14 — Notificaciones (original) y presupuesto bloqueante contra compromisos

**Requisitos "de construcción" (5, `IMPLEMENTADO Y VALIDADO`):** `NXR-NOT-0001`
a `NXR-NOT-0005`.
**Requisito de brecha:** `NXR-PRE-0008` (enforcement transaccional de presupuesto
contra compromisos) — `NO DEMOSTRADO`.
**Código verificado:** `reserve_budget_commitment`, `_lock_and_read_line` y los
campos nuevos `budget`/`budget_line` en `NXR Commitment` existen exactamente como se
describe — el enforcement real está en código, con lock, no solo declarado.
**Estado real:** código real y probado por unidad; sin ejecución real
bench/MariaDB para confirmar el bloqueo bajo concurrencia real.
**Criterio de cierre:** cumplido en código/prueba de contrato; pendiente de
ejecución real.

## Bloque 15 — Usuarios/roles (original) y verificación real de integraciones

**Requisitos "de construcción" (7, `IMPLEMENTADO Y VALIDADO`):** `NXR-USR-0001`
a `NXR-USR-0007`.
**Requisito de brecha:** `NXR-INT-0007` (verificación real de conexión, no
simulada) — `NO DEMOSTRADO`.
**Código verificado:** `integrations/connectivity.py::check_endpoint_connectivity`
existe — reemplazó una comprobación simulada por una prueba HTTP real.
**Estado real:** código real; sin ejecución real contra un endpoint externo vivo en
este entorno.
**Criterio de cierre:** cumplido en código; pendiente de ejecución real.

## Bloque 16 — Cierres/correcciones (original) y resultado explicable + navegación móvil

**Requisitos "de construcción" (9, `IMPLEMENTADO Y VALIDADO`):** `NXR-DOC-0005`,
`NXR-CIE-0001/0002/0003/0005/0006/0007/0008`. **`NXR-CIE-0004`:**
`OBSOLETO JUSTIFICADO`.
**Requisitos de brecha:** `NXR-UX-0012` (resultado explicable), `NXR-UX-0013`
(números explicables/drill-down), `NXR-UX-0014` (navegación móvil inferior) — los
3 `NO DEMOSTRADO`.
**Código verificado:** `TABBAR_ITEMS` existe en `nexora_shell.js` exactamente como
se describe (barra inferior de 4 destinos frecuentes).
**Estado real:** código real y probado por contrato; sin recorrido visual real en
WebKit/Chromium para certificar el resultado final.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 17 — Integraciones (original) y Contexto 360°/Timeline universal

**Requisitos "de construcción" (3, `IMPLEMENTADO Y VALIDADO`):** `NXR-INT-0001/
0002/0004`. **`NXR-INT-0003/0005/0006`:** `OBSOLETO JUSTIFICADO`.
**Requisitos de brecha:** `NXR-UX-0010` (página de contexto 360° por proyecto),
`NXR-UX-0011` (timeline universal reutilizable) — ambos `NO DEMOSTRADO`.
**Código verificado:** `context360/core.py`, `service.py`, `timeline.py` existen con
las funciones descritas (`get_project_overview`, `get_project_timeline`), con
`require_project_access` cerrando el acceso antes de tocar cualquier doctype.
**Además, se encontró y corrigió en esta misma sesión histórica** el hallazgo real
de seguridad que se convertiría en `NXR-SEC-0001`: `dashboard.service.
get_dashboard_summary()` no llamaba `require_project_access`.
**Estado real:** código real, probado por unidad y contrato (27 pruebas puras en
`test_context360_core.py`, incluido un bug real encontrado y corregido durante las
pruebas — `clamp_limit(0)`); sin recorrido visual real en navegador.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 18 — Identidad/PWA (original) y Conversational OS

**Requisitos "de construcción" (6, `IMPLEMENTADO Y VALIDADO`):** `NXR-DOC-0006`,
`NXR-UX-0001/0002/0003/0004/0007`.
**Requisito de brecha:** `NXR-CNV-0001` (Conversational OS) — `NO DEMOSTRADO`.
**Verificación de "no existía → se construyó de verdad" (el hallazgo más
importante de esta franja):** el propio `NIP_BLOQUE_6_CONVERSATIONAL_OS.md` y la
auditoría del Bloque 12 confirmaron que `nexora_app/nexora/conversation/` estaba
**vacío** en ese punto ("código real = 0"). Verificado con `git log` que se
construyó de verdad en el commit `714158dc` (PR #104, "motor conversacional real").
Hoy `conversation/` contiene 1091 líneas reales entre `core.py`, `db.py`,
`dispatch.py`, `nlu.py`, `registry.py`, `resolve.py`, más un subdirectorio
`channels/` (WhatsApp, añadido después en el Bloque 21). Tres DocTypes nuevos
(`NXR Conversation`, `NXR Conversation Message`, `NXR Conversation Pending
Intent`), máquina de estados real, preview obligatorio antes de cualquier
ejecución financiera, auditoría real.
**Endurecimiento posterior confirmado en esta misma sesión (Bloque 28):**
`resolvePending()` (confirmar/cancelar una intención pendiente) no tenía la misma
guarda anti-doble-clic que `send()` — corregido con una bandera `resolving`.
**Estado real:** código real, maduro, probado (32 pruebas puras + 21 de contrato,
100% verde); sin interpretación real de un proveedor de IA vivo ni recorrido de
navegador en este entorno.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real
con proveedor de IA vivo y navegador real.

## Bloque 19 — Calidad/Governance (QA) y fuga de datos entre proyectos

**Requisitos "de construcción" (8, `IMPLEMENTADO Y VALIDADO`):** `NXR-QA-0001`
a `NXR-QA-0008`.
**Requisito de brecha:** `NXR-SEC-0001` (fuga cruzada entre proyectos) —
`NO DEMOSTRADO`.
**Verificación real y profunda de esta auditoría:** se encontraron y corrigieron
**14 funciones** en 7 módulos sin control por proyecto real (`purchases/
quotation_service.py` ×3, `receipt_service.py`, `order_service.py`,
`request_service.py`, `inventory/service.py`, `contracts/service.py`,
`budget/service.py::check_budget_availability`,
`financial/sources.py::list_source_balances`, `financial/analytics.py` ×3,
`financial/operations.py::preview_financial_operation`,
`financial/evidence.py::list_evidence`, `integrations/service.py::list_integrations`),
más un IDOR más sutil en `reports/service.py::get_contract_statement` (validaba el
proyecto que declaraba el cliente, no el proyecto real del contrato), más una fuga
de clase distinta en `notifications/service.py::list_notifications` (cualquier
usuario podía leer notificaciones de otro usuario).
**`require_project_access` (la función que cierra todo esto) confirmada real y
cableada en 30+ archivos** — no una promesa: `dashboard/*.py` (8 puntos),
`reports/*.py` (7 puntos), `purchases/*_service.py`, `financial/*.py`,
`contracts/service.py`, `inventory/service.py`, `close/service.py`,
`context360/*.py`.
**Prueba real, no tautológica:** `tests/test_security_project_scoping_contract.py`
extrae el cuerpo exacto de cada función por expresión regular (no una búsqueda de
substring en todo el archivo, que daría falsos positivos con una función vecina) y
exige la llamada real a `require_project_access`; incluye una aserción específica
para el IDOR de `get_contract_statement` verificando que resuelve el proyecto desde
`frappe.db.get_value("NXR Contract", contract, "project")`, no desde el payload del
cliente. 16/16 verde; ejecutado directamente en esta auditoría: 44/44 (con otros
archivos de seguridad).
**Estado real:** el hallazgo de seguridad es real y ya está corregido con evidencia
de código y prueba — la clasificación `NO DEMOSTRADO` (no `IMPLEMENTADO Y VALIDADO`)
es correcta porque nunca se ejecutó un intento real de fuga cruzada contra un
`bench` vivo, solo verificación estática de la cadena de llamadas.
**Criterio de cierre:** cumplido en código/contrato; pendiente de penetración real
contra `bench`/MariaDB.

## Bloque 20 — Infraestructura y gateway de IA operacional

**Requisitos "de construcción" (5, `IMPLEMENTADO Y VALIDADO`):** `NXR-INF-0002/
0003/0004/0005/0008`.
**Requisito auditado (no reconstruido):** `NXR-AI-0001` — `EXISTENTE Y
REUTILIZABLE`.
**Verificación real y profunda:** `intelligence/orchestrator.py::execute` tiene
fallback real (`orchestrator_core.rank_candidates`/`score_candidate`), disyuntor
real (circuito cerrado/semiabierto/abierto con backoff exponencial acotado,
`orchestrator_core.py`), `should_retry_same_provider` que excluye explícitamente
errores de auth/429/modelo-no-encontrado del reintento único. Redacción de
credenciales confirmada: los llamados a `audit()` pasan siempre `fingerprint` (un
hash), nunca `secret`; el campo `secret` es `fieldtype: Password`. Confirmado por
`grep` que existen **exactamente 2** llamadores reales de `orchestrator.execute` en
todo el repositorio (`conversation/nlu.py:90`, `intelligence/service.py:604`),
pinneados por archivo:línea en `test_ai_data_exposure_contract.py` — no es un
conteo aproximado, es una prueba que falla si aparece un tercer llamador.
**Hallazgo arquitectónico real, no una acción — requiere decisión del
propietario, no se toca en este cierre:** `intelligence/providers/*_stub.py` (9
adaptadores simulados) y `intelligence/gateway.py::dispatch()` +
`adapters.py::build_default_registry()` están confirmados **inalcanzables desde
cualquier camino de ejecución real de usuario** (`orchestrator.execute` →
`runtime.build_ready_adapter` → `runtime_core.prepare_adapter` solo importa clases
`*_live`, nunca las stub; `dispatch()`/`build_default_registry()` solo tienen
llamadores en pruebas). **Pero esta separación es una decisión arquitectónica
deliberada de un bloque anterior**, con su propia prueba de regresión
(`test_intelligence_contract.py::test_block_1_and_block_2_provider_infrastructure_is_unchanged_by_block_4`,
que exige explícitamente que los adaptadores reales *nunca* usen `@register_adapter`
"para no competir por las mismas claves con los stubs ya registrados"). Eliminar el
subsistema de stubs revertiría esa decisión explícita, no solo retiraría código
muerto — cruza a "cambio fundamental de arquitectura" (Sección 43 de la misión).
**No se elimina en este cierre. Se documenta como hallazgo para que el propietario
decida**: ¿el subsistema de stubs sirve un propósito vigente (pruebas/demo sin
credenciales reales) que deba conservarse y documentarse mejor, o es deuda que debe
retirarse formalmente? Ninguna de las dos respuestas afecta la seguridad ni la
integridad financiera hoy: nada en el camino real de producción puede alcanzar una
respuesta simulada y confundirla con una real.
**Estado real:** infraestructura real, auditada, sin llamada viva a un proveedor de
IA en este entorno (sin credenciales).
**Criterio de cierre:** cumplido como auditoría; una pregunta de arquitectura
queda escalada, no resuelta unilateralmente.

## Bloque 21 — WhatsApp Business real

**Requisito:** `NXR-INT-0008` — `NO DEMOSTRADO`.
**Contexto:** el propietario confirmó (2026-08-11) tener la app de Meta configurada,
desbloqueando una espera documentada desde el Bloque 12.
**Verificación real y profunda:** `conversation/channels/whatsapp_core.py`/
`whatsapp.py` implementan verificación de firma real (HMAC-SHA256 con
`hmac.compare_digest`, verificado contra el header `X-Hub-Signature-256` **antes**
de `frappe.parse_json`), verificación GET del challenge del webhook, deduplicación
real por `message_id` vía `frappe.cache()` con TTL de 24h. Dos DocTypes nuevos
(`NXR Channel Credential`, `NXR Channel Account`) con campos `Password` reales
(`app_secret`/`access_token`/`verify_token`), resueltos solo vía
`doc.get_password(...)`. Llamada HTTP real confirmada:
`_graph_get`/`_graph_post_json` usan `urllib.request` contra
`https://graph.facebook.com/v19.0` (URL real de la Graph API de Meta), con timeout
y manejo real de `HTTPError`/`URLError` — sin mock en el archivo de producción (el
mock solo existe en fixtures de prueba). El literal `"Success"` en este módulo
(`last_test_result = "Success"`) solo se alcanza **después** de una llamada real
exitosa a `_graph_get` — no es un éxito fabricado.
**Caveat honesto ya declarado en el propio código:** el mecanismo de respuesta en
texto plano al challenge GET (`frappe.response["type"] = "text"`) no se ha
verificado contra una instancia Frappe real.
**Estado real:** integración real, no simulada, con 18/18 + 19/19 pruebas de
contrato/core en verde; sin ejecución real contra el webhook vivo de Meta en este
entorno.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 22 — Auditoría cruzada de integraciones (anti-simulación)

**Requisito:** `NXR-INT-0009` — `NO DEMOSTRADO`.
**Barrido explícito por "Success"/mocks/stubs/simulaciones en todo
`nexora_app/nexora/` (fuera de `tests/`), repetido de forma independiente en esta
misma auditoría:** solo 2 apariciones no-test del literal `"Success"`, ambas
condicionadas a un resultado HTTP real (`integrations/service.py:61`,
`conversation/channels/whatsapp.py:372`, ya analizado en el Bloque 21) — ninguna es
un éxito fabricado. Cero hallazgos reales de `TODO`/`FIXME`/`hardcoded`/
`not implemented` en código de producción (los únicos "hits" son falsos positivos
de la palabra "Todos" en español o nombres de prueba). El único patrón de
"simulate"/"stub" real es el ya documentado y escalado en el Bloque 20.
**Corrección real aplicada en esa sesión:** `integrations/service.py::test_connection`
y 4 acciones administrativas de WhatsApp no escribían en el registro cruzado
`NXR Audit Event` (solo en su propio log de doctype) — corregido con llamadas
`audit(...)` reales.
**Estado real:** auditoría real con dos correcciones reales aplicadas; sin
ejecución real contra `bench`/MariaDB para confirmar los registros de auditoría en
una base de datos viva.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 23 — Notificaciones (entrega real email/WhatsApp)

**Requisito:** `NXR-NOT-0006` — `NO DEMOSTRADO`. PR #112, SHA
`9fe38bac011c3509357de0cb290f21d7ed62a2e7`.
**Estado real:** entrega real con reintento (no un `Success` fabricado) para
email/WhatsApp; código y pruebas en verde en esta sesión; sin ejecución real contra
un servidor SMTP/WhatsApp vivo en este entorno.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 24 — Endurecimiento de NXR-SEC-0001 en `dashboard/*`

**Requisito afectado:** `NXR-SEC-0001` (nota de endurecimiento, sin nueva fila).
PR #114, SHA `d9875a71e9d02bade352ff13e3415ff9bbe06d65`.
**Hallazgo:** `contract_page()`/`source_statement()`/`source_movement_page()`
parecían desprotegidas a primera vista (no llaman `require_project_access`
directamente) pero delegan en `dashboard.query_utils.project(data)`, que sí la
llama — confirmado con pruebas directas que fijan esa cadena de protección en vez
de "corregir" código que ya era correcto.
**Estado real:** cerrado con pruebas de contrato nuevas; sin regresión.
**Criterio de cierre:** cumplido.

## Bloque 25 — Evidencia + Avance (corrección de reclamo falso)

**Requisitos:** `NXR-AVA-0005`/`NXR-AVA-0006` — `NO DEMOSTRADO`. PR #115, SHA
`96cd2cbf71b6dc61cbb4b2abe0821200fdaaf024`.
**Hallazgo real de reclamo fabricado, encontrado y corregido en esta misión:**
ambas filas estaban marcadas `IMPLEMENTADO Y VALIDADO` citando un commit que, según
su propio mensaje y `git show --stat`, solo agregó `progress/core.py` y
`progress/service.py` — sin página, sin JS, sin cámara. `git log --all
--diff-filter=A --name-only -- "*progress*.js"` confirmó que jamás existió ese
archivo. Corregido construyendo la página real (`nexora-progress`), no solo
relabelando la matriz.
**Estado real:** cerrado con página real, registrada en navegación/workspace/shell,
con pruebas de contrato e integración; sin recorrido de cámara/galería real en un
navegador.
**Criterio de cierre:** cumplido en código/contrato; pendiente de ejecución real.

## Bloque 26 — Cierre de flujos operativos de extremo a extremo (auditoría)

**Requisito nuevo:** `NXR-CAL-0001` — `REQUIERE DECISIÓN`. PR #116, SHA
`b57c22b92c38e8686d2dfd4c0b7ffbd54485a985`.
**Hallazgo real:** todas las máquinas de estado de cierre (compras→recepción,
contratos→liquidación, inventario, presupuesto) confirmadas correctas, sin estado
colgante. `NXR Quality Check` confirmado como doctype muerto: candado
(`require_service_write()`) sin ninguna llave (`quality/service.py` no existe) —
nadie puede crear un registro hoy, ni con autorización ni sin ella. No hay
superficie de ataque, pero tampoco hay una fila previa de la matriz que prometiera
esta función — se agrega como hallazgo nuevo, no como corrección de una promesa.
**Decisión pendiente real, no fabricada:** ¿quién aprueba un control de calidad?
¿bloquea la aprobación del avance vinculado? ¿qué pasa si el resultado es
"Rechazado"? Construir código sobre esto sin que el propietario decida sería
inventar una regla de negocio.
**Estado real:** auditoría cerrada; la decisión de producto sigue abierta y
correctamente escalada, sin bloquear el resto de la misión.
**Criterio de cierre:** cumplido como auditoría; decisión pendiente del propietario.

## Bloque 27 — PWA, iPhone y WebKit

**Requisito afectado:** `NXR-UX-0004` (nota de endurecimiento). PR #118, SHA
`cc2a8a0b0e5f6e4b97b497e5f5e74ff764a33030`.
**Hallazgo real y corregido, con evidencia de CI real:** la etapa `pwa` del
recorrido de navegador (registro del service worker, caché offline, aviso sin
conexión) solo se pedía en `desktop-chromium`; los dos perfiles WebKit reales
(`ipad-gen7-webkit`, `iphone-13-webkit`) nunca la ejecutaban — la afirmación "PWA
segura en iPhone" nunca se había puesto a prueba contra un motor WebKit real.
Corregido activando la etapa en los tres perfiles. **Confirmado en dos ejecuciones
reales de CI** (`Frappe real · escritorio · tableta · iPhone · PWA`): la etapa
`pwa` pasó sin fallo en los tres perfiles, incluidos los dos motores WebKit reales.
**Estado real:** cerrado con evidencia de ejecución real en CI, no solo con la
corrección de código.
**Criterio de cierre:** cumplido con evidencia real.

## Bloque 28 — NEXORA Super Experience (auditoría/pulido de UX)

**Requisito afectado:** `NXR-CNV-0001` (nota de endurecimiento). PR #119, SHA
`360d1bdceb6d7f074d245baa160151d1e16bedea`.
**Hallazgo real y corregido:** `resolvePending()` del asistente conversacional
(confirmar/cancelar una intención pendiente, que puede ser un pago real) no tenía la
misma guarda anti-doble-clic que `send()`. Verificado que el servidor ya es a
prueba de doble ejecución financiera por `idempotency_key` (sin riesgo de dinero
duplicado), pero el doble clic sí producía una llamada sobrante y podía mostrar un
error interno de idempotencia sin sentido al usuario. Corregido con una bandera
`resolving`.
**Estado real:** cerrado con prueba de contrato nueva; auditoría del resto de
pantallas sin más hallazgos que corregir (documentado exhaustivamente en
`EXECUTION_STATE.md`).
**Criterio de cierre:** cumplido.

## Bloque 29 — Certificación integral (inspección masiva)

**Sin nueva fila de requisito.** PR #120, SHA
`31376640a1f6b65215e1ba5603de422436cf256e`.
**Trabajo real:** barrido automatizado de las 155 filas `IMPLEMENTADO Y VALIDADO` —
0 artefactos citados que no existan hoy en el código. Verificados los 17 SHA de 40
caracteres citados en toda la matriz — los 17 existen en git. Auditoría manual del
SHA más citado (36 filas) confirmando que "evidencia validada en X" significa
"cierto en ese punto de control", no "X lo implementó" — convención consistente, no
un reclamo falso. Cerró (más tarde corregido a "intermitente" en el Bloque 30) el
hallazgo residual de `Frappe real`/`operaciones`.
**Estado real:** auditoría real, sin código de producción tocado.
**Criterio de cierre:** cumplido.

## Bloque 30 — Cierre definitivo

**Requisito afectado:** `NXR-UX-0006` (nota de corrección de regresión). PR #121,
SHA `59c64a500cc16388194c6c2d2923d81a638bb287`.
**Hallazgo real, diagnosticado y corregido — la causa raíz de un defecto que
arrastraba toda la misión desde el Bloque 24:** `panel: Dashboard did not expose
the active period` fallaba en cada ejecución real desde el PR #93 ("make dashboard
period selectable"), que sustituyó el texto plano `Período: <mes>` por un
`<select>` y perdió los dos puntos que el recorrido exige. Corregido restaurando el
texto. **Confirmado en CI real:** `panel` pasó sin fallo en los tres perfiles por
primera vez desde el PR #93. Al dejar de enmascararlo, salieron a la luz dos
defectos intermitentes ya catalogados (`operaciones`, `comprobantes`/`project`) —
documentados honestamente como intermitentes tras dos ejecuciones reales sobre el
mismo commit con resultados distintos, sin declarar su cierre por un solo run
favorable.
**Estado real:** cerrado con evidencia real de CI, con dos hallazgos residuales
intermitentes documentados con transparencia, no ocultados.
**Criterio de cierre:** cumplido.

---

## Hallazgos transversales de esta ronda de auditoría (nuevos, no vistos en bloques anteriores)

1. **Corregido:** `docs/nexora/BLOQUE_10_PRESUPUESTOS_COMPROMISOS.md` afirmaba un
   requisito de pronóstico presupuestario como "CONFIRMADO" sin que exista código —
   la matriz siempre tuvo la clasificación correcta; solo el documento de dominio
   quedó desactualizado. Corregido en este mismo cierre.
2. **Escalado, no corregido — decisión del propietario:** el subsistema de
   adaptadores de IA simulados (`intelligence/providers/*_stub.py`,
   `gateway.dispatch()`) está confirmado inalcanzable desde cualquier camino de
   ejecución real, pero fue preservado deliberadamente por una decisión
   arquitectónica de un bloque anterior (con su propia prueba de regresión que
   exige esa separación). Eliminarlo revertiría esa decisión — no es una
   corrección segura y autónoma, es un cambio de arquitectura. Ver Bloque 20.
3. **Confirmado, no un hallazgo nuevo pero sí una verificación directa e
   independiente:** ningún "Success" fabricado, mock, stub o simulación alcanzable
   desde un camino de usuario real existe en `nexora_app/nexora/` fuera de lo ya
   documentado (los stubs de IA, escalados arriba). El barrido se hizo dos veces
   —una vez por un agente de esta sesión, una vez de forma independiente por el
   agente de los Bloques 19-22— con el mismo resultado.
4. **Confirmado con evidencia directa de código, no solo de prosa:** la
   concurrencia (`FOR UPDATE`) y la idempotencia (`start_idempotency`/
   `complete_idempotency`, 214 puntos de uso) son reales y pervasivas en
   financiero, contratos, compras, inventario y presupuesto — el principio
   financiero de la misión (Sección 6/19 de la misión maestra) se cumple en código,
   no solo en documentación.
5. **Ningún reclamo fabricado activo encontrado** en la matriz de 184 requisitos
   ni en `EXECUTION_STATE.md` durante esta ronda — los tres agentes de auditoría y
   el trabajo directo de este documento cubrieron los 30 bloques sin encontrar una
   sola afirmación de éxito que el código actual contradiga.

## Estado consolidado de los 184 requisitos (sin cambios de conteo en este bloque)

155 `IMPLEMENTADO Y VALIDADO` · 16 `NO DEMOSTRADO` · 6 `OBSOLETO JUSTIFICADO` · 3
`NO APLICA JUSTIFICADO` · 2 `EXISTENTE PERO DEFECTUOSO` · 1 `REQUIERE DECISIÓN` · 1
`EXISTENTE Y REUTILIZABLE` = 184.

Ningún requisito cambia de estado como resultado directo de esta auditoría — su
propósito era verificar, no reclasificar. La única corrección aplicada fue
documental (Bloque 10) y no toca ninguna fila de la matriz, que ya era correcta.
