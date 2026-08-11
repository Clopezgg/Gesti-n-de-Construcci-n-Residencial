# NEXORA — Golden Paths (Bloque 12; actualizado en el cierre de los 30 bloques)

No existía en el repositorio un documento formal de "Golden Paths" — solo fragmentos
dispersos de recorridos de smoke-test (`EXECUTION_STATE.md`, `docs/final/
NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md`, `docs/final/NEXORA_ENTREGA_FINAL.md`,
`docs/final/NEXORA_OPERACION_Y_RESPALDO.md`). Este documento los consolida y los mapea
contra los diez recorridos pedidos por la nueva misión maestra, con evidencia real de
código y clasificación honesta de qué se pudo validar en este entorno.

**Nota de actualización (auditoría final de los 30 bloques, ver
`NEXORA_30_BLOCKS_AUDIT.md`):** este documento se escribió en el Bloque 12, a mitad
de la misión. Los Bloques 13 a 30 cerraron con código real la mayoría de las
brechas que aquí se documentaron como faltantes. Las entradas GP-03, GP-05, GP-06 y
GP-10 tienen una nota de actualización con el estado real verificado al cierre —
sin borrar el hallazgo original, para conservar la trazabilidad de qué se encontró
y cuándo se corrigió.

**Entorno de esta sesión:** sin `bench`/Frappe/MariaDB/Redis/Docker/Playwright. Todo lo
que requiere ejecución real en navegador o base de datos se marca **NO DEMOSTRADO AQUÍ**
y se referencia el job de CI que sí lo certifica (`nexora-app.yml` job `browser`,
`server-tests-mariadb.yml`). Esto no significa que el recorrido no funcione — significa
que esta sesión no tiene los medios para reproducirlo, y no se inventa el resultado.

---

### GP-01 — Inicio → consultar saldo → proyecto
**Actor:** cualquier usuario con acceso a NEXORA.
**Pasos:** login → dashboard → filtrar por proyecto → ver disponible/comprometido/ejecutado.
**Código real:** `nexora_dashboard.js:54-88`, `dashboard/service.py:264-361`.
**Permisos:** filtrado por proyecto vía `PROJECT_SCOPED_DOCTYPES` (`boot.py`).
**Auditoría:** solo lectura, sin efecto que auditar.
**Prueba positiva:** `test_dashboard_*` (4 archivos, corren en este entorno sin Frappe
real para la parte de contrato/formato; el cálculo contra datos reales requiere Frappe).
**Estado:** **CONFIRMADO EN CÓDIGO / NO DEMOSTRADO EN NAVEGADOR AQUÍ.**

### GP-02 — Nueva operación → pago → preview → confirmación → documento → saldo
**Código real:** `nexora_guided_operations.js:72-124` (wizard 4 etapas) →
`financial/operations.py:29` `execute()` (savepoint, idempotencia, lock, `require_action`)
→ `financial/core.py:241-268` (saldo antes/después) → `NXR Document Sequence` (12
dígitos) → `NXR Audit Event`.
**Prueba positiva:** 17 tests en `test_financial_core.py` (multifuente, overdraw,
concurrencia, idempotencia, rollback).
**Prueba negativa:** rechazo de saldo negativo confirmado en `core.py:225-227`.
**Estado:** **CONFIRMADO — el recorrido más maduro del producto.**

### GP-03 — Solicitud → compra → recepción → inventario
**Código real:** `purchases/request_service.py` → `quotation_service.py` →
`order_service.py:182` → `receipt_service.py:169`. Vínculo a inventario: **no
automático** — no se encontró llamada de `receipt_service` hacia
`inventory/service.py`; la entrada de inventario requiere una transacción de stock
separada.
**Defecto real encontrado en este bloque:** sobre-recepción acumulada no bloqueada
(`NXR-COM-0010`, ver gap analysis) — una recepción parcial repetida puede superar lo
pedido sin rechazo.
**Estado:** **EXISTENTE PERO DEFECTUOSO** — el recorrido funciona de principio a fin,
pero con un hueco de validación real y una desconexión de integración con inventario
que debe decidirse (¿automática o manual intencional?).

**Actualización (Bloque 13, cierre de los 30 bloques):** la sobre-recepción
acumulada **ya está bloqueada en código real** —
`purchases/receipt_core.py`/`receipt_service.py::_received_totals` calcula la
cantidad acumulada aceptada por línea y rechaza (`cumulative > max_q`) una
recepción que exceda la tolerancia máxima, verificado directamente en el código
actual—. La desconexión con inventario (recepción no crea automáticamente una
transacción de stock) sigue igual, confirmada como decisión de diseño no tomada,
no como un olvido. Estado real hoy: **NO DEMOSTRADO** (código y prueba de contrato
en verde; sin ejecución real contra `bench`/MariaDB en este entorno para el
bloqueo de sobre-recepción).

### GP-04 — Contrato → avance → estimación → pago
**Código real:** `contracts/service.py:718` `create_contract_estimate` →
`contracts/service.py:919` `execute_contract_estimate_payment` →
`contracts/core.py` (`assert_transition`, `amendment_balances`).
**Prueba positiva:** 16 tests en `contracts/` + probe de concurrencia dedicado.
**Estado:** **CONFIRMADO EN CÓDIGO / NO DEMOSTRADO EN NAVEGADOR AQUÍ** (requiere Frappe
real para el recorrido de UI completo con avance físico ligado a evidencia fotográfica).

### GP-05 — Captura de evidencia → proyecto → timeline
**Código real:** captura con contexto heredado confirmada (evidencia con
proyecto/usuario/fecha). **Timeline universal reutilizable: no existe**
(`NXR-UX-0011`) — solo hay un widget de actividad reciente en el dashboard global, no
una línea de tiempo por entidad navegable desde la página de esa entidad.
**Estado:** **EXISTENTE PERO INCOMPLETO** — la evidencia se captura y traza
correctamente; el recorrido "ver la línea de tiempo de este proyecto/contrato" no tiene
una superficie de UI dedicada todavía.

**Actualización (Bloque 17, cierre de los 30 bloques):** la brecha **se cerró con
código real**. `context360/timeline.py::get_project_timeline()` existe, cruza 8
doctypes ya existentes agrupados en 7 categorías reales, con normalización pura
probada por 27 pruebas unitarias, y una página real (`nexora-project`) que la
consume. Estado real hoy: **NO DEMOSTRADO** (código y pruebas puras en verde; sin
recorrido visual real en navegador en este entorno) — ya no es "no existe", es
"existe, falta demostrar visualmente".

### GP-06 — Búsqueda universal → resultado → documento
**Código real:** `boot.py:360-390` `universal_search_consolidated`, permisos reales,
13 doctypes indexados.
**Estado:** **CONFIRMADO** para búsqueda estructurada. La variante en lenguaje natural
de la misión (Sección 24) no existe (ver `NXR-CNV-0001`) — este Golden Path, tal como
existe hoy, es de búsqueda por término/filtro, no de consulta conversacional.

**Actualización (Bloque 18, cierre de los 30 bloques):** la consulta en lenguaje
natural **ya existe como recorrido independiente** — el asistente conversacional
(`nexora-assistant`, `conversation/nlu.py`+`dispatch.py`) interpreta texto libre,
incluida la consulta de saldo. No sustituye ni convierte `nexora_search.js` en un
buscador conversacional (siguen siendo dos superficies separadas: una barra de
búsqueda estructurada y un chat conversacional aparte), así que `NXR-UX-0009`
(convertir la búsqueda misma en lenguaje natural) sigue sin construirse — pero la
premisa "no hay ninguna implementación de NLU en el repo" ya no es cierta: sí la
hay, en una pantalla distinta. Ver GP-10.

### GP-07 — Consulta de fondo → saldo → movimientos
**Código real:** `reports/service.py` `get_source_statement()` con saldo corrido;
`financial/db.py` con historial de efectos por fuente.
**Prueba positiva:** `test_reports_core.py`.
**Estado:** **CONFIRMADO EN CÓDIGO / NO DEMOSTRADO EN NAVEGADOR AQUÍ.**

### GP-08 — Corrección de operación → autorización → reversión/sustitución → auditoría
**Código real:** `financial/corrections.py:147` `_validate_open_period()` bloquea
correcciones sobre períodos cerrados; documentos compensatorios preservan el original
(`NXR Correction` con `Draft/Validada/Aprobada/Ejecutada`).
**Prueba positiva:** confirmado en `test_financial_core.py` (casos de corrección) y en
`Bloque 11` de `EXECUTION_STATE.md` (mensajes de error reales del servidor mostrados en
UI, no genéricos).
**Estado:** **CONFIRMADO.**

### GP-09 — Cierre mensual
**Código real:** `close/service.py:39` `create_monthly_close`, `:78` `reconcile_month`;
inmutabilidad post-cierre verificada vía `_validate_open_period()`.
**Prueba positiva:** 32 tests en `close/`.
**Estado:** **CONFIRMADO EN CÓDIGO / NO DEMOSTRADO EN NAVEGADOR AQUÍ.**

### GP-10 — Consulta natural → interpretación → datos reales → respuesta explicable
**Código real:** ninguno. `nexora_app/nexora/conversation/` está vacío; no hay NLU en
el repositorio. El diseño existe (`NIP_BLOQUE_6_CONVERSATIONAL_OS.md`) pero el propio
documento marca sus sub-bloques de implementación como "Pendiente".
**Estado:** **NO IMPLEMENTADO.** Es el único Golden Path de los diez que no tiene
ningún código de respaldo, no solo una brecha de UI — requiere construcción completa
(`NXR-CNV-0001`).

**Actualización (Bloque 18, cierre de los 30 bloques):** este Golden Path **se
construyó de verdad**. Verificado con `git log` que el commit `714158dc` (PR #104)
construyó `conversation/core.py`/`db.py`/`dispatch.py`/`nlu.py`/`registry.py`/
`resolve.py` (1091 líneas reales) y tres DocTypes nuevos. El motor: interpretación
real → resolución de referencias (proyecto/entidad) → relleno de campos → preview
obligatorio para cualquier escritura → confirmación explícita (botón o texto
"confirmar"/"cancelar") → ejecución vía las mismas funciones de dominio que ya usa
la UI (nunca un segundo camino) → auditoría real. Endurecido en el Bloque 28 (guarda
anti-doble-clic en confirmar/cancelar). Estado real hoy: **NO DEMOSTRADO** (código
real, maduro, 32 pruebas puras + 21 de contrato en verde; sin interpretación real
contra un proveedor de IA vivo ni recorrido de navegador en este entorno) — ya no
es "no implementado", es "implementado, pendiente de certificación en vivo".

---

## Resumen

| Golden Path | Estado (Bloque 12) | Estado real al cierre de los 30 bloques |
|---|---|---|
| GP-01 Saldo por proyecto | Confirmado en código, no demostrado en navegador aquí | Sin cambio |
| GP-02 Operación → pago | **Confirmado** — el más maduro | Sin cambio |
| GP-03 Solicitud → compra → recepción → inventario | Existente pero defectuoso | Sobre-recepción bloqueada en código (Bloque 13); NO DEMOSTRADO en vivo |
| GP-04 Contrato → estimación → pago | Confirmado en código, no demostrado en navegador aquí | Sin cambio |
| GP-05 Evidencia → timeline | Existente pero incompleto (falta timeline) | Timeline construido (Bloque 17); NO DEMOSTRADO en vivo |
| GP-06 Búsqueda → documento | Confirmado (estructurada); natural no existe | NLU existe como pantalla aparte (Bloque 18), no integrada en el buscador mismo |
| GP-07 Fondo → movimientos | Confirmado en código, no demostrado en navegador aquí | Sin cambio |
| GP-08 Corrección → auditoría | **Confirmado** | Sin cambio |
| GP-09 Cierre mensual | Confirmado en código, no demostrado en navegador aquí | Sin cambio |
| GP-10 Consulta natural | **No implementado** | Construido de verdad (Bloque 18, PR #104); NO DEMOSTRADO en vivo con proveedor de IA real |

Ningún Golden Path se declara "IMPLEMENTADO Y VALIDADO" en este documento sin la
validación visual real en las tres superficies (escritorio/iPhone/PWA) que exige la
misión — esa validación pertenece al job `browser` de `nexora-app.yml` (hoy
`Frappe real · escritorio · tableta · iPhone · PWA`), que este entorno no puede
ejecutar de forma interactiva. Los ocho marcados "confirmado en código / no
demostrado en navegador aquí" o su equivalente tienen el motor completo y probado
por unidad o contrato; falta solo la certificación visual de CI (parcialmente ya
lograda de forma real para PWA/WebKit en el Bloque 27, con dos ejecuciones reales
de CI en verde) para poder llamarlos terminados. Ver `NEXORA_30_BLOCKS_AUDIT.md`
para el detalle bloque por bloque.
