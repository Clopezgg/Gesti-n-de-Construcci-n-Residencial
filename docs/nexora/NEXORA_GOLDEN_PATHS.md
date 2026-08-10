# NEXORA — Golden Paths (Bloque 12)

No existía en el repositorio un documento formal de "Golden Paths" — solo fragmentos
dispersos de recorridos de smoke-test (`EXECUTION_STATE.md`, `docs/final/
NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md`, `docs/final/NEXORA_ENTREGA_FINAL.md`,
`docs/final/NEXORA_OPERACION_Y_RESPALDO.md`). Este documento los consolida y los mapea
contra los diez recorridos pedidos por la nueva misión maestra, con evidencia real de
código y clasificación honesta de qué se pudo validar en este entorno.

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

### GP-06 — Búsqueda universal → resultado → documento
**Código real:** `boot.py:360-390` `universal_search_consolidated`, permisos reales,
13 doctypes indexados.
**Estado:** **CONFIRMADO** para búsqueda estructurada. La variante en lenguaje natural
de la misión (Sección 24) no existe (ver `NXR-CNV-0001`) — este Golden Path, tal como
existe hoy, es de búsqueda por término/filtro, no de consulta conversacional.

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

---

## Resumen

| Golden Path | Estado |
|---|---|
| GP-01 Saldo por proyecto | Confirmado en código, no demostrado en navegador aquí |
| GP-02 Operación → pago | **Confirmado** — el más maduro |
| GP-03 Solicitud → compra → recepción → inventario | Existente pero defectuoso |
| GP-04 Contrato → estimación → pago | Confirmado en código, no demostrado en navegador aquí |
| GP-05 Evidencia → timeline | Existente pero incompleto (falta timeline) |
| GP-06 Búsqueda → documento | Confirmado (estructurada); natural no existe |
| GP-07 Fondo → movimientos | Confirmado en código, no demostrado en navegador aquí |
| GP-08 Corrección → auditoría | **Confirmado** |
| GP-09 Cierre mensual | Confirmado en código, no demostrado en navegador aquí |
| GP-10 Consulta natural | **No implementado** |

Ningún Golden Path se declara "IMPLEMENTADO Y VALIDADO" en este documento sin la
validación visual real en las tres superficies (escritorio/iPhone/PWA) que exige la
misión — esa validación pertenece al job `browser` de `nexora-app.yml`, que este
entorno no puede ejecutar. Los seis marcados "confirmado en código / no demostrado en
navegador aquí" tienen el motor completo y probado por unidad; falta solo la
certificación visual de CI para poder llamarlos terminados según el Capítulo 60 de la
Constitución.
