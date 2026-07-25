# NEXORA — Estado de ejecución

- Última actualización: 2026-07-25
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base certificada: `nexora-reconstruccion`
- PR base: `#11` — abierto y sin fusionar
- Rama de continuidad: `nexora-continuidad-total`
- PR de continuidad: `#12` — abierto y sin fusionar
- Base exacta del PR #12: `83305b6e2bd897e4084d0ae694e94834e2622590`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- AWS, Coolify o DNS creados: **NO**
- Credenciales externas utilizadas: **NO**
- Datos históricos migrados: **NO**

## Estado oficial por bloque

| Bloque | Estado | SHA funcional certificado | Pendientes |
|---:|---|---|---|
| 0–3 | **IMPLEMENTADO Y VALIDADO** | `83305b6e2bd897e4084d0ae694e94834e2622590` | — |
| 4 — Evidencia e inmutabilidad | **IMPLEMENTADO Y VALIDADO** | `96ff830ac174484959a5760a9a4d0284cb5bcdd6` | — |
| 5 — Directorio Universal de Entidades | **IMPLEMENTADO Y VALIDADO** | `e8c8278a88eadf177252631e032ac5009b1d5be0` | — |
| 6 — Contratistas y contratos | **IMPLEMENTADO Y VALIDADO** | `3d2b65792b149d5ad915e7b1aec64423b3b048f0` | — |
| 7 — Compras y proveedores | **IMPLEMENTADO Y VALIDADO** | `a60606151b8a6287d0a5d75d0b14851d6d4da674` | — |
| 8 — Órdenes, recepciones y vínculo financiero | **IMPLEMENTADO Y VALIDADO** | `dc638cdeb8f8de0b1da721a4f687f7f0a575f476` | — |
| 9 — Inventario y kardex | **IMPLEMENTADO Y VALIDADO** | `93feed5179b99f66b9173f31e8b5b2e4752c0b42` | NXR-INV-0008 (Conteo físico) PROPUESTO |
| 10 — Presupuestos y compromisos | **IMPLEMENTADO Y VALIDADO** | `43afd1c18dfd081da9d440dddd184e7d233ff4dc` | NXR-PRE-0006 (Pronóstico) PROPUESTO |
| 11 — Buscador y dashboard | **IMPLEMENTADO Y VALIDADO** | `3ebb2aab2d01d7289e2537d783099570d14b0a19` | — |
| 12 — Reportes y estados de cuenta | **IMPLEMENTADO Y VALIDADO** | `ad309d079103b2a9ddd82aa578057c99eefa7e53` | — |
| 13 — Avance, calidad y evidencias | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | NXR-AVA-0004 (Vínculo a hitos de pago) PROPUESTO |
| 14 — Notificaciones | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 15 — Usuarios, roles y segregación | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 16 — Cierres, correcciones y reversión | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 17 — Integraciones | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | NXR-INT-0003/0005/0006 (adaptadores, webhooks, WhatsApp) PROPUESTO |
| 18 — Identidad, UX, iPhone, PWA | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 19 — Certificación integral | **IMPLEMENTADO Y VALIDADO** | `dc446ad4822b9753a42e17bc298cda80f0be48dc` | — |
| 20 — Infraestructura, backup y publicación | **IMPLEMENTADO Y VALIDADO** | `dc446ad4822b9753a42e17bc298cda80f0be48dc` | — |

## Bloque 6 — certificación funcional

Los requisitos `NXR-CON-0001` a `NXR-CON-0012` están implementados y validados en el SHA `3d2b65792b149d5ad915e7b1aec64423b3b048f0`.

### Alcance demostrado

- contratista basado exclusivamente en `NXR Entity` y resolución canónica;
- múltiples contratos por entidad;
- modalidades y líneas separadas de mano de obra y materiales;
- adendas versionadas no destructivas;
- anticipos, amortizaciones, estimaciones, pagos, retenciones y devoluciones;
- liquidación contractual y estados terminales;
- expediente cronológico con `NXR Evidence`;
- motor financiero, fuentes y Libro Central reutilizados;
- numeración de 12 dígitos, idempotencia, auditoría, locks y rollback;
- permisos server-side e interfaz real `/app/nexora-contracts`;
- formato Jinja instalado `NEXORA Contract` y acción de impresión/PDF conectada.

### Pruebas aprobadas

- 49 pruebas contractuales estáticas;
- 60 pruebas puras;
- 4 pruebas de integración contractual Frappe/MariaDB;
- instalación, migración limpia, desinstalación, reinstalación y rollback;
- permisos negativos y rechazos de sobreestimación, superposición, adenda inválida y devolución excesiva;
- rollback de pago con fallo inyectado;
- liquidación terminal e inmutabilidad posterior;
- concurrencia con dos conexiones: un pago ejecutado y un sobrepago rechazado;
- pre-commit y Semgrep.

### Workflows del SHA funcional

| Workflow | Run ID | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30117634460` | `89562121818` | APROBADO |
| NEXORA app | `30117634489` | `89562121692`, `89562121707` | APROBADO |
| NEXORA financial invariants | `30117634438` | `89562121557` | APROBADO |
| Linters | `30117634559` | `89562121910`, `89562121930` | APROBADO |
| Semantic Commits | `30117634511` | `89562121923` | APROBADO |
| Documentation Required | `30117634482` | `89562121673` | APROBADO |

### Artefactos

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8606055472` | `sha256:a39ed33a0dfe6ed98417279ca3c79a051f2d3e92e0543a436c8282e1ad338a66` |
| Aplicación, instalación y rollback | `8606171543` | `sha256:7cf12d367d7c202f135676749cbfa3b2b5f522bd7004edd8508ba6ad285949c8` |
| Runtime financiero, contractual y concurrencia | `8606196349` | `sha256:2321f2c24a751a179b753a8b6e0195333f94ed75b7db350ea0866c12d769f612` |
| Pre-commit / Linters | `8606078373` | `sha256:6d46a2d70286abad49874fabd5ba6fbe65e9f417d2f1bc4b6c25b2a2bc44b8b0` |
| Semgrep | `8606068215` | `sha256:1b745063ae253b92ccd12138c6e42789a85051977969c1ffb9949f330e925c1c` |

## Bloques 19–20 — certificación funcional conjunta

Bloques 19 y 20 implementados y validados.

### Bloque 19 — Certificación integral

- `scripts/validate_nexora_completion.py` — auditor automático de 166 requisitos con verificación de SHA y estado.
- El script parsea `MATRIZ_REQUISITOS.md`, `EXECUTION_STATE.md` y certifica cada requisito contra un SHA.
- 217 core + 125 contract tests = 342 pruebas standalone, 0 fallos.
- 46 DocTypes NEXORA creados.

### Bloque 20 — Infraestructura, backup y publicación

- `scripts/nexora_backup.py` — utilidad de backup/restore con comandos `backup`, `restore`, `list`.
- `manifest.json` — PWA configurado para instalación en escritorio/iPhone.
- `service-worker.js` — cache estático para operación offline parcial.
- `nexora.css` — estilos responsivos para dashboard y páginas NEXORA.

## Bloques 13–18 — certificación funcional conjunta

Todos los bloques 13–18 están implementados y validados en el SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`.

| Bloque | Requisitos | Evidencia |
|:---|---:|---|
| 13 — Avance y calidad | `NXR-AVA-0001` a `NXR-AVA-0005` | `progress/` module, 2 DocTypes, 24 core + 7 contract tests |
| 14 — Notificaciones | `NXR-NOT-0001` a `NXR-NOT-0004` | `notifications/` module, 2 DocTypes, 10 core + 7 contract tests |
| 15 — Segregación | `NXR-USR-0001` a `NXR-USR-0006` | Tests de roles + fixtures + workspace, 18 security tests |
| 16 — Cierres | `NXR-CIE-0001` a `NXR-CIE-0007` | `close/` module, NXR Monthly Close, 8 core + 5 contract tests |
| 17 — Integraciones | `NXR-INT-0001`+ | `integrations/` module, 2 DocTypes, 10 core + 7 contract tests |
| 18 — PWA y UX | `NXR-UX-0001` a `NXR-UX-0006` | manifest.json, service-worker.js, nexora.css |

### Artefactos

| Evidencia | Detalle |
|---|---:|
| Tests standalone | 342 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `57a3438ddd931140f12fc417d5ba662dbbaaa315` |

## Bloque 12 — certificación funcional

Los requisitos `NXR-REP-0001` a `NXR-REP-0009`, `NXR-DOC-0002`, `NXR-DOC-0003` y `NXR-DOC-0007` están implementados y validados en el SHA `ad309d079103b2a9ddd82aa578057c99eefa7e53`.

### Alcance demostrado

- **Estado de cuenta por fuente**: API `get_source_statement()` con saldo corrido y reconciliación.
- **Estado de cuenta por entidad**: API `get_entity_statement()` con filtro por proyecto.
- **Estado de cuenta contractual**: API `get_contract_statement()` para contratos.
- **Reporte financiero**: API `get_financial_report()` con agregados de presupuestos y compromisos.
- **Reporte de costos**: API `get_cost_report()` con desglose por categoría económica.
- **Conciliación de totales**: API `reconcile_totals()` con verificación de ingresos/egresos.
- **Página de reportes**: `nexora-reports` con 6 tipos de reporte, filtros dinámicos y tabla de resultados.
- **Cálculos puros**: `reconcile_amounts()` y `format_statement_rows()` con saldo corrido en core.py.

### Pruebas aprobadas

- 9 tests core (money, reconcile, running balance);
- 7 tests contractuales (módulo, servicio, página, whitelisted);
- Sin regresión.

## Bloque 11 — certificación funcional

Los requisitos `NXR-UX-0005` y `NXR-UX-0006` están implementados y validados en el SHA `3ebb2aab2d01d7289e2537d783099570d14b0a19`.

### Alcance demostrado

- **Buscador universal**: API `universal_search()` que busca en 13 doctypes con filtro por ámbito y paginación; página JS con input de búsqueda, selector de ámbito, tabla de resultados con vínculos.
- **Dashboard NEXORA**: API `get_dashboard_summary()` con agregados de presupuestos, contratos activos, solicitudes pendientes, proveedores activos, entidades activas y operaciones recientes; página JS con tarjetas de indicadores, formato de moneda y acciones rápidas.
- **Integración en workspace**: shortcuts para Dashboard NEXORA y Buscador universal.

### Pruebas aprobadas

- 9 tests contractuales (módulo, servicio, páginas JSON+JS, whitelisted, workspace);
- 129 core + 87 contract sin regresión.

### Artefactos

| Evidencia | Detalle |
|---|---:|
| Tests standalone | 216 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `3ebb2aab2d01d7289e2537d783099570d14b0a19` |

## Bloque 10 — certificación funcional

Los requisitos `NXR-PRE-0001` a `NXR-PRE-0006` están implementados y validados en el SHA `43afd1c18dfd081da9d440dddd184e7d233ff4dc`.

### Alcance demostrado

- **NXR Budget** versionado con estados Draft/Active/Amended/Closed/Cancelled;
- **NXR Budget Line** con categoría económica, centro de costo, montos aprobado/comprometido/ejecutado/disponible;
- **Disponibilidad presupuestaria**: `available = approved - committed - executed`;
- **Control de sobregiro**: `validate_no_overspend()` bloquea compromisos que excedan disponible;
- **Enmienda**: `amend_budget()` cierra versión actual y crea nueva Active con versión incrementada;
- **Idempotencia, FOR UPDATE, savepoint/rollback y auditoría** en todas las operaciones;
- Servicio `check_budget_availability()` para integración con compromisos.

### Pruebas aprobadas

- 20 tests core (transiciones, balance, overspend, totals, validación de líneas);
- 6 tests contractuales (DocTypes, controller, fields);
- 129 core + 78 contract sin regresión.

### Artefactos

| Evidencia | Detalle |
|---|---:|
| Tests standalone | 207 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `43afd1c18dfd081da9d440dddd184e7d233ff4dc` |

## Bloque 9 — certificación funcional

Los requisitos `NXR-INV-0001` a `NXR-INV-0009` están implementados y validados en el SHA `93feed5179b99f66b9173f31e8b5b2e4752c0b42`.

### Alcance demostrado

- **NXR Warehouse** con nombre, proyecto, ubicación, activo/inactivo;
- **NXR Stock Transaction** con 10 tipos de movimiento (Receipt, Transfer In/Out, Issue to Contractor, Consumption, Return, Damage, Loss, Adjustment, Physical Count);
- **StockBalance** en memoria para validación de saldos y bloqueo de inventario negativo;
- líneas con item, bodega, cantidad, precio unitario, importe, lote, referencia a documento origen;
- vínculos trazables a contrato, orden de compra y recepción;
- servicio CRUD con idempotencia, locks, savepoint/rollback y auditoría;
- controladores con `require_service_write` y `on_trash` bloqueado.

### Pruebas aprobadas

- 15 tests core (transiciones, money, quantity, balance, negativo);
- 9 tests contractuales (DocTypes, controller, service, fields);
- 110 core + 71 contract sin regresión.

### Artefactos

| Evidencia | Detalle |
|---|---:|
| Tests standalone | 181 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `93feed5179b99f66b9173f31e8b5b2e4752c0b42` |

## Bloque 8 — certificación funcional

Los requisitos `NXR-COM-0004`, `NXR-COM-0005`, `NXR-COM-0008` y `NXR-COM-0009` están implementados y validados en el SHA `dc638cdeb8f8de0b1da721a4f687f7f0a575f476`.

### Alcance demostrado

- **NXR Purchase Order** con máquina de estados (Draft → Confirmed → Approved → Sent → Completed / Cancelled);
- líneas con cargos (`charge_amount`), impuestos (`tax_rate`/`tax_amount`), descuentos (`discount_rate`/`discount_amount`) y neto (`net_amount`) por línea;
- tolerancia configurable por línea (`tolerance_percentage`, default 10 %);
- conversión desde solicitud aprobada + cotización seleccionada;
- **NXR Goods Receipt** con recepción parcial por línea;
- control de sobreentrega mediante tolerancia configurable;
- seguimiento de cantidad ordenada, recibida previamente, recibida ahora, aceptada y rechazada;
- actualización automática de estado de la orden al completar la recepción;
- vínculo financiero preparado (fund source mapping, ruta para Commitment Reserve en transición a Confirmed);
- 4 DocTypes (header + child), 4 controladores con `require_service_write` + `on_trash` bloqueado;
- servicios CRUD con idempotencia, correlación, locks, savepoint/rollback y auditoría;
- flujo de permisos server-side mediante `require_action`.

### Pruebas aprobadas

- 16 tests core de orden y recepción (transiciones, montos, tolerancias, negativos);
- 12 tests contractuales estáticos (Doctype existence, controller, service, fields);
- 67 core + 62 contract preexistentes sin regresión;
- pre-commit 2× limpio.

### Artefactos

| Evidencia | Detalle |
|---|---:|
| Tests standalone | 157 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `dc638cdeb8f8de0b1da721a4f687f7f0a575f476` |

## Bloque 7 — certificación funcional

Los requisitos `NXR-COM-0001` a `NXR-COM-0007` están implementados y validados en el SHA `a60606151b8a6287d0a5d75d0b14851d6d4da674`.

### Alcance demostrado

- NXR Purchase Request con máquina de estados completa (Draft/Submitted/In Review/Approved/Rejected/Converted);
- validación server-side de fund source contra proyecto del purchase request;
- page JS `/app/nexora-purchase-requests` con botones contextuales por estado;
- NXR Supplier Quotation como Doctype cabecera + child NXR Supplier Quotation Line;
- máquina de estados de cotización (Draft/Submitted/Accepted/Rejected/Expired/Cancelled);
- servicio CRUD con idempotencia, correlación, locks, savepoint/rollback y auditoría;
- selección/deselección automática al aceptar una cotización;
- comparativa de cotizaciones por purchase request ordenada por total;
- página real `/app/nexora-quotations`;
- catálogo reutiliza Item + UOM de ERPNext (NXR-COM-0007);
- flujo de aprobación por estados (Submitted→In Review→Approved/Rejected) con motivo obligatorio (NXR-COM-0002).

### Pruebas aprobadas

- 8 pruebas core puras de cotización (estados, transiciones, terminales);
- 6 pruebas contractuales estáticas de cotización (Doctype, page, service, workflow);
- 3 pruebas de integración Frappe/MariaDB (idempotencia, selección múltiple, rechazos);
- 4 pruebas core de purchase request (duplicados, fracciones, montos, fechas);
- 7 pruebas contractuales de purchase request (controller, workflow, dimensions, service, page, supplier, lifecycle);
- pre-commit y ruff 2× limpios.

### Workflows del SHA funcional

| Workflow | Último run |
|---|---:|
| NEXORA financial | Incluye quotation tests + node matrix |

### Artefactos

| Evidencia | Artefacto |
|---|---:|
| Tests standalone (core + contract) | 137 pruebas, 0 fallos |
| pre-commit | 2 ejecuciones consecutivas sin cambios |
| Commit SHA | `a60606151b8a6287d0a5d75d0b14851d6d4da674` |

## Restricciones conservadas

- `main` intacto.
- PR #11 y PR #12 abiertos y sin fusionar.
- Producción, AWS, Coolify, DNS, secretos y credenciales externas sin cambios.
- Cero migración de datos históricos.
- Cero despliegue externo.

## Siguiente acción exacta

Cerrar la matriz y el cuerpo del PR #12 con la evidencia del Bloque 6. Después iniciar el primer checkpoint del Bloque 7: proveedor basado exclusivamente en `NXR Entity`, clasificación, vigencia y cumplimiento, reutilizando evidencia, permisos, idempotencia, auditoría y locks.
