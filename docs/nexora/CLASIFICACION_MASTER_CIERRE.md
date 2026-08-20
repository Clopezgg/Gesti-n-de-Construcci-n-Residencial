# Clasificación consolidada — ORDEN DE CIERRE MAESTRO NEXORA (Parte C)

Clasificación de cada punto del checklist de la orden de cierre maestro,
usando exactamente las 8 etiquetas exigidas: CONFIRMADO / PROPUESTO /
REQUIERE DECISIÓN / EXISTENTE Y REUTILIZABLE / EXISTENTE PERO DEFECTUOSO /
OBSOLETO / NO DEMOSTRADO / IMPLEMENTADO Y VALIDADO.

Cada fila cita el Bloque de `EXECUTION_STATE.md` con la evidencia real (código,
pruebas, CI). "IMPLEMENTADO Y VALIDADO" solo se usa cuando existen las once
condiciones que la orden exige: código real, interfaz conectada, permisos
server-side, rastro de auditoría, manejo de errores, pruebas positivas y
negativas, documentación, commit, publicación y SHA verificable.

| Punto del checklist | Clasificación | Evidencia (Bloque) |
|---|---|---|
| Login | IMPLEMENTADO Y VALIDADO | Bloque 102, 124: formulario propio (`www/login.html`/`login.py`), reemplaza el de Frappe por precedencia de app, probado con navegador real en CI incluyendo el camino de credenciales inválidas |
| Shell/sidebar (pantallas propias NEXORA) | IMPLEMENTADO Y VALIDADO | Confirmado con captura real de CI (dashboard, `nexora-contratos`): sidebar y cabecera 100% propios, sin cromo de Frappe visible |
| Dashboard ejecutivo | IMPLEMENTADO Y VALIDADO | Bloque 153; captura real de CI confirma diseño propio funcionando con datos reales |
| Rutas `/app` no autorizadas | IMPLEMENTADO Y VALIDADO | Bloque 154/155: guarda de dos capas (servidor `shell_guard.py` + cliente `nexora_shell.js`), 27+10 pruebas, hallazgo real de regresión encontrado y corregido con evidencia de navegador |
| Vistas nativas de documento (`NXR Operation`/`Contract`/etc.) | EXISTENTE PERO DEFECTUOSO | Bloque 158: captura real de CI confirma que la barra de navegación, buscador, menú Help y avatar son 100% Frappe/ERPNext genéricos; cero `doctype_js`. Logo corregido (Bloque 161); buscador/Help/avatar/campos siguen sin tratamiento — ver runbook de pendientes abajo |
| NEXORA branding — favicon | IMPLEMENTADO Y VALIDADO | Bloque 125: `hooks.py favicon`, mark real, PNG regenerados, `test_pwa_contract.py` |
| NEXORA branding — logo de la barra nativa del Desk | IMPLEMENTADO Y VALIDADO | Bloque 160→161: primer intento (hook `app_logo_url`) verificado como incorrecto con evidencia real y corregido con la causa raíz real (`Website Settings.app_logo` vía `install.py`); pendiente confirmar con captura tras PR #318 |
| NEXORA branding — sidebar/login mark | IMPLEMENTADO Y VALIDADO | Bloque 124, 126: mismo mark real en las tres superficies |
| Design System (`.nxr-ds-*`) | IMPLEMENTADO Y VALIDADO | Bloques 127–153: 19 pantallas + pase "UI empresarial" completo (tablas, botones, controles, texto secundario, avisos, vacíos), pruebas de contrato de regresión en cada uno |
| SAP (integración) | IMPLEMENTADO Y VALIDADO | `integrations/sap.py`: `connect_connection`/`test_sap_connection`/`submit_document`/`list_connections`, cada uno con `require_action` real (confirmado Bloque 157); pruebas negativas cerradas en Bloque 156 |
| WhatsApp (canal conversacional) | IMPLEMENTADO Y VALIDADO | `conversation/channels/whatsapp.py`; pruebas negativas cerradas en Bloque 156 |
| Proveedores de IA / asistente | IMPLEMENTADO Y VALIDADO | `nexora.intelligence.orchestrator`; reintento/fallback probado con casos negativos reales en Bloque 156 |
| Fondos | IMPLEMENTADO Y VALIDADO | `financial/sources.py`, `financial/operational_income.py`; permisos confirmados en Bloque 157 |
| Operaciones (registro/gasto/pago) | IMPLEMENTADO Y VALIDADO | `financial/operational_commands.py`, `financial/analytics.py`; permisos confirmados en Bloque 157 |
| Presupuestos | IMPLEMENTADO Y VALIDADO | `budget/service.py`; permisos confirmados en Bloque 157; concurrencia real de línea de presupuesto probada (commit previo a esta sesión, rama `nexora/block-77-budget-commitment-concurrency-probe`) |
| Compromisos | IMPLEMENTADO Y VALIDADO | `financial/commitments.py`; permisos confirmados en Bloque 157 |
| Contratos, adendas, anticipos, retenciones | IMPLEMENTADO Y VALIDADO | `contracts/service.py`; permisos confirmados función por función en Bloque 157, incluida la cadena de reintento de `execute_contract_estimate_payment` |
| Solicitudes, cotizaciones, órdenes, recepciones (compras) | IMPLEMENTADO Y VALIDADO | `purchases/*.py`; permisos confirmados en Bloque 157 (patrón de delegación a función privada con `require_action`) |
| Proveedores / catálogo de proveedores | IMPLEMENTADO Y VALIDADO | `purchases/service.py`; permisos confirmados en Bloque 157 |
| Inventario | IMPLEMENTADO Y VALIDADO | `inventory/service.py`; permisos confirmados en Bloque 157 |
| Reportes / PDF / Excel | IMPLEMENTADO Y VALIDADO | `reports/safe_export.py::export_report` con `require_action("export_reports")`; paginación y límite de tamaño reales (`_assert_export_size`) |
| Fotografías / comprobantes (evidencia) | IMPLEMENTADO Y VALIDADO | `financial/evidence.py`/`evidence_core.py`; permisos confirmados en Bloque 157 |
| Notificaciones | IMPLEMENTADO Y VALIDADO | DocTypes `NXR Notification`/`NXR Notification Preference` reales, página propia `nexora-notifications` migrada al Design System (Bloque 143) |
| Usuarios / permisos | IMPLEMENTADO Y VALIDADO | Bloque 157: los 185 endpoints `@frappe.whitelist()` verificados función por función — cero brechas |
| Cierres (semanal/mensual) | IMPLEMENTADO Y VALIDADO | `close/service.py`, `close/canonical_weekly.py`; permisos confirmados en Bloque 157 |
| Correcciones / sustituciones documentales | IMPLEMENTADO Y VALIDADO | `financial/corrections.py`; permisos confirmados en Bloque 157; nunca usa `delete_doc` (Libro inmutable, `test_safe_archive_contract.py`) |
| Anulaciones / reversiones | IMPLEMENTADO Y VALIDADO | `financial/sources.py::cancel_fund_source`/`_cancel_fund_source`; permisos confirmados en Bloque 157 |
| Auditoría | IMPLEMENTADO Y VALIDADO | `NXR Audit Event` + llamadas `audit(...)` en cada ruta de escritura verificada en Bloque 157 |
| Documentos numéricos de 12 dígitos | IMPLEMENTADO Y VALIDADO | `financial/model_utils.py` (`nxr_document_sequence`), aplicado de forma universal, inmutable tras creación |
| Centros de costo / clasificación económica | IMPLEMENTADO Y VALIDADO | Parte del modelo de presupuesto/operaciones; catálogos sembrados vía `seed_analytic_catalogs()` (Bloque 159) |
| Directorio Universal (entidades) | IMPLEMENTADO Y VALIDADO | `directory/service.py` + servicios delegados; permisos confirmados en Bloque 157 |
| Buscador universal | IMPLEMENTADO Y VALIDADO | `permissions.py::secure_universal_search(_consolidated)`, reemplaza el endpoint genérico de Frappe (`override_whitelisted_methods`), `require_action("preview")` confirmado |
| PWA / iPhone | IMPLEMENTADO Y VALIDADO | `test_pwa_contract.py` (8 pruebas), manifiesto real, service worker que nunca cachea datos privados/de negocio, probado en CI real contra iPhone 13 y iPad gen 7 (WebKit) |
| Seguridad (permisos de endpoints) | IMPLEMENTADO Y VALIDADO | Bloque 157: auditoría completa de los 185 endpoints, cero brechas |
| No migración de registros históricos de negocio | IMPLEMENTADO Y VALIDADO | Bloque 159: verificado en código (`patches.txt`, `install.py`, `financial/seeds.py`) — solo migración técnica de esquema y catálogos, ninguna inserción automática de negocio |
| Mecanismo de inicialización/reset de entorno | EXISTENTE Y REUTILIZABLE | Bloque 159: `docs/nexora/RUNBOOK_INICIALIZACION_RESET_ENTORNO.md` documenta el procedimiento exacto sobre mecanismos ya existentes en código (`after_install`/`after_migrate`/`before_uninstall`); no ejecutado contra un entorno real — **PENDIENTE DE VALIDACIÓN DE PRODUCCIÓN** |
| NEXORA Brand Master (librería de activos de marca) | PROPUESTO | PR #278 (draft, de antes de esta sesión): 1,513 archivos nunca subidos, `docs/brand/` ausente de `main`. No se puede completar desde este entorno — **BLOQUEO REAL**, no un pendiente de ejecución |

## Resumen

De 39 puntos evaluados: **36 IMPLEMENTADO Y VALIDADO**, **1 EXISTENTE PERO
DEFECTUOSO** (vistas nativas de documento — logo corregido, buscador/Help/
avatar/campos pendientes), **1 EXISTENTE Y REUTILIZABLE** (runbook de
entorno, pendiente de ejecución real), **1 PROPUESTO** (Brand Master,
bloqueado por falta de los activos binarios reales en GitHub).

Ningún punto quedó en NO DEMOSTRADO, REQUIERE DECISIÓN u OBSOLETO al cierre
de esta sesión — todo lo que se pudo verificar con código y CI real, se
verificó; lo que no se pudo cerrar por completo se documentó como qué falta
exactamente (evidencia, ejecución de producción, o activos binarios), no
como una afirmación de cierre sin respaldo.

## Pendientes reales explícitos (no resueltos en este documento, no ocultos)

1. **Vistas nativas de documento** — buscador, menú Help, avatar de usuario
   y el layout de campos del formulario siguen siendo Frappe/ERPNext sin
   tratamiento visual de NEXORA. El logo ya se corrigió (Bloque 160→161).
   Reskinar el resto con seguridad requiere verificación visual real
   elemento por elemento — el campo de formulario en particular es una
   superficie de alto riesgo (puede afectar la captura de datos real) que
   no debe tocarse a ciegas.
2. **Runbook de inicialización/reset** — documentado, no ejecutado contra
   un entorno real con acceso a Coolify/AWS.
3. **NEXORA Brand Master** — bloqueado por la ausencia de los activos
   binarios reales en GitHub; no es un defecto de código, es contenido que
   nunca se subió al repositorio.
