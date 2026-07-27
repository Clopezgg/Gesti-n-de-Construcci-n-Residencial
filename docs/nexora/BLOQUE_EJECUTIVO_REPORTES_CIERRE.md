# NEXORA — Mejoras ejecutivas, reportes y cierre semanal

Estado del bloque: **IMPLEMENTADO Y VALIDADO** en el SHA funcional `94e6e8838727ce304500b1d0c4f9d92e6ade96b6`.

PR oficial: [#19](https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/19)

Este bloque completa y mejora la implementación acordada. No reemplaza el dashboard certificado, no crea un sistema paralelo y no reconstruye los módulos funcionales existentes.

## Requisitos trazables

| ID | Requisito | Estado | Evidencia |
|---|---|---|---|
| NXR-EXEC-001 | Un motor financiero canónico para dashboard, FI01, FI02, BI01 y cierres | IMPLEMENTADO Y VALIDADO | `NXR Operation Effect`, adaptadores ejecutivos y CI verde |
| NXR-EXEC-002 | Saldos históricos `as-of` y separación de transferencias, gastos, reservas, devoluciones y reversos | IMPLEMENTADO Y VALIDADO | agregados por fecha de operación y pruebas Frappe/MariaDB |
| NXR-EXEC-003 | Dashboard premium sin perder el contrato certificado | IMPLEMENTADO Y VALIDADO | `nexora-dashboard.js`, contratos y smoke de navegador |
| NXR-EXEC-004 | Anulaciones y reversos visibles, sin ocultar el ingreso bruto original | IMPLEMENTADO Y VALIDADO | KPI y alerta de movimientos compensados |
| NXR-REP-001 | FI01 paginado con moneda, tasa, saldos, transferencias, conciliación y anulación segura | IMPLEMENTADO Y VALIDADO | `get_source_statement_page` y acción compensatoria |
| NXR-REP-002 | FI02 paginado por fuente, categoría, entidad y centro de costo | IMPLEMENTADO Y VALIDADO | `dashboard/expense_query.py` |
| NXR-REP-003 | CO01 paginado por proyecto, contratista, estado y vigencia | IMPLEMENTADO Y VALIDADO | `get_contract_page` |
| NXR-REP-004 | Excel y PDF server-side con permiso, auditoría y rechazo de exceso de filas | IMPLEMENTADO Y VALIDADO | `reports/safe_export.py`; acción `export_reports` |
| NXR-REP-005 | Reportes guardados e historial por usuario | IMPLEMENTADO Y VALIDADO | `NXR Saved Report` y servicios asociados |
| NXR-REP-006 | Archivo de reportes sin borrado ni pérdida de número, filtros o auditoría | IMPLEMENTADO Y VALIDADO | `reports/actions.py` y acción real en interfaz |
| NXR-REP-007 | PR02 y BI01 usan la versión presupuestaria aplicable y efectos hasta la fecha de corte | IMPLEMENTADO Y VALIDADO | `close/as_of.py`, `snapshot_query.py` y prueba MariaDB |
| NXR-SEC-001 | Acciones separadas y control de proyecto en servidor | IMPLEMENTADO Y VALIDADO | `permissions.py` y pruebas negativas |
| NXR-REC-001 | Conciliación explícita con usuario, fecha, método, diferencia y evidencia | IMPLEMENTADO Y VALIDADO | campos de `NXR Fund Source`; `reconcile_fund_source` |
| NXR-CAN-001 | Anulación de ingreso mediante operación compensatoria y sin eliminación física | IMPLEMENTADO Y VALIDADO | `cancel_fund_source`, reverso ligado y auditoría |
| NXR-CLOSE-001 | Cierre semanal con número de 12 dígitos, idempotencia, auditoría, hash e inmutabilidad | IMPLEMENTADO Y VALIDADO | `NXR Weekly Close`; `close/service.py` |
| NXR-CLOSE-002 | Corrección sin sobrescritura mediante nuevo registro enlazado | IMPLEMENTADO Y VALIDADO | `correct_weekly_close` |
| NXR-CLOSE-003 | Reservas, obligaciones y presupuesto calculados al corte histórico | IMPLEMENTADO Y VALIDADO | `canonical_weekly.py`; motor `nexora-analytics-v3` |
| NXR-PERF-001 | Tablas paginadas y paneles con límites explícitos | IMPLEMENTADO Y VALIDADO | máximo 100 filas por endpoint; paneles de 8/10/25 filas |
| NXR-PERF-002 | El resumen ejecutivo no ejecuta primero la carga masiva del dashboard general | IMPLEMENTADO Y VALIDADO | `operational_query.py`; ausencia de `get_dashboard_summary` en el adaptador |
| NXR-TEST-001 | Pruebas positivas, negativas, contractuales e integración MariaDB | IMPLEMENTADO Y VALIDADO | contratos, pruebas puras e integraciones publicadas |
| NXR-TEST-002 | Chromium, iPhone WebKit y PWA prueban dashboard, reportes y cierre | IMPLEMENTADO Y VALIDADO | smoke permanente y artefacto de navegador |

## Reglas operativas

1. Las cifras financieras se derivan del Libro Central y `NXR Operation Effect`; una transferencia interna nunca se clasifica como gasto.
2. La fecha del ingreso y la fecha de su operación canónica coinciden para impedir que una fuente futura altere un corte anterior.
3. Un reporte histórico mantiene saldo inicial, movimientos del período, saldo al cierre y saldo actual como conceptos separados.
4. Un reverso no se suma como gasto ordinario: se informa como importe compensado y mantiene visible el ingreso original.
5. FI02 aplica fuente, categoría y centro de costo a los efectos asignados antes de agregar el importe. Una operación multifuente muestra únicamente la porción seleccionada.
6. PR02 selecciona la última versión presupuestaria vigente a la fecha final y agrega efectos `Budget` hasta ese mismo corte.
7. La conciliación es explícita; una diferencia requiere observación y evidencia.
8. La exportación se construye en servidor. El servidor valida `export_reports`, proyecto y volumen; un reporte superior al límite se rechaza y no se trunca silenciosamente.
9. Un ingreso solo puede anularse directamente cuando conserva íntegro su efecto inicial y no tiene gastos, reservas ni ajustes relacionados. La anulación genera un efecto inverso y conserva auditoría.
10. Un reporte guardado no se elimina: se archiva por su propietario, conservando número, filtros y eventos de auditoría.
11. Un cierre semanal cerrado no se edita ni elimina. Una corrección crea otro documento enlazado y conserva ambas fotografías.
12. El resumen ejecutivo usa consultas paginadas o limitadas; no carga colecciones completas para reemplazarlas después.
13. Los documentos nuevos reciben número numérico único de 12 dígitos mediante la secuencia canónica.

## Estados y transiciones

### Fuente de fondos

- `Active` o `Exhausted` → `Cancelled` únicamente por servicio compensatorio.
- La operación original pasa a `Compensated Total`.
- El reverso contiene `is_reversal=1` y `reverses_effect`.
- No existe borrado como forma de corrección financiera.

### Conciliación de ingreso

- `Pending` → `Reconciled`.
- `Pending` → `Disputed`.
- `Disputed` → `Reconciled`.
- Cualquier cambio pasa por el servicio autorizado y queda auditado.

### Reporte guardado

- `Active` → `Archived` por el propietario.
- No existe transición a borrado físico.

### Cierre semanal

- `Closed`: fotografía original e inmutable.
- `Correction`: fotografía posterior ligada mediante `correction_of`.
- No existe transición a borrado ni sobrescritura.

## Efectos financieros

- `Funds`: modifica el saldo efectivo de la fuente.
- `Reserved`: modifica reserva y disponibilidad.
- `Budget`: modifica comprometido o ejecutado presupuestario según el tipo de operación.
- `Internal Transfer`: se presenta como entrada/salida de transferencia, sin aumentar gasto consolidado.
- `Real Return`: restaura fondos y se identifica por separado.
- `is_reversal`: conserva el histórico original y muestra el importe revertido.
- `closing_available_hnl`: fondos al corte menos reservas al corte.
- `projected_available_hnl`: igual al disponible al corte cuando las reservas ya representan compromisos; las obligaciones informativas se muestran por separado para evitar doble conteo.

## Base histórica del cierre semanal v3

- fondos, gastos, ingresos y reservas: efectos con `operation_date` igual o anterior al cierre;
- presupuesto aprobado: última versión no borrador/no anulada con `effective_date` igual o anterior al cierre;
- líneas PR02: categoría y centro de costo de la versión aplicable;
- comprometido y ejecutado presupuestario: efectos de dimensión `Budget` hasta la fecha de cierre;
- avance físico: último registro aprobado hasta la fecha de cierre;
- cuentas pendientes: reserva financiera al cierre, no el estado mutable actual de cuentas por pagar;
- evidencias: registros creados hasta la fecha final, con estado de revisión vigente;
- el cierre guarda el identificador de motor `nexora-analytics-v3`.

Limitación explícita: el estado contractual y la conciliación documental guardados en el cierre reflejan el estado vigente al momento de generar la fotografía. La reconstrucción histórica exacta de contratos requiere un historial canónico de adendas y transiciones; no se presenta como resuelta por este bloque.

## Rendimiento y límites

- FI01, FI02, CO01 y cuentas pendientes usan paginación server-side con máximo de 100 filas por solicitud.
- Dashboard ejecutivo: 8 fuentes, 8 gastos, 8 contratos, 8 evidencias, 10 operaciones recientes y 25 registros de avance como máximos visibles.
- Totales, conteos, alertas vencidas y categorías se calculan mediante agregados SQL.
- `snapshot_query.py` no llama a `get_dashboard_summary`; conserva el contrato de respuesta mediante `operational_query.py`.
- Las exportaciones superiores a 5,000 filas se rechazan antes de generar el archivo.

## Permisos

- `view_reports`: consulta de reportes.
- `view_financial_details`: acceso a cifras y movimientos.
- `export_reports`: Excel/PDF server-side.
- `view_all_projects`: consulta consolidada sin proyecto.
- `view_closings`: cálculo e historial de cierres.
- `save_closing`: cierre y corrección enlazada.
- `reconcile_source`: conciliación de ingresos.
- `cancel_source`: anulación compensatoria de ingresos.

El acceso a un proyecto se valida nuevamente en el servidor mediante permisos de `Project`.

## Pruebas de aceptación

### Positivas

- ingreso, gasto, reserva, liberación, transferencia interna, devolución y reversión producen totales separados;
- una fuente futura no aparece ni afecta un corte anterior;
- una operación multifuente de HNL 100.00 asignada HNL 60.00/HNL 40.00 devuelve cada porción al filtrar FI02;
- PR02 devuelve HNL 1,000.00 antes de una adenda, incorpora HNL 200.00 ejecutados en su fecha y cambia a HNL 1,500.00 desde la nueva versión;
- consulta histórica devuelve saldo al cierre y saldo actual en columnas distintas;
- Excel y PDF se generan mediante endpoint autorizado;
- anulación elegible crea reverso, conserva el documento original y refresca dashboard/reportes;
- reporte guardado se archiva de forma idempotente y desaparece de la lista activa;
- cierre repetido con la misma clave devuelve respuesta idempotente;
- cierre del mismo período con otra solicitud es rechazado por clave única;
- cierre v3 guarda reservas, obligaciones y presupuesto calculados al corte;
- dashboard conserva proyecto, alertas, saldos, reservas, presupuesto, evidencias, contratos e inventario crítico;
- Chromium y iPhone WebKit cargan dashboard, reportes, cierre y las rutas canónicas;
- PWA valida manifiesto, service worker, caché restringida a activos públicos y aviso sin conexión.

### Negativas

- fecha final anterior a la inicial;
- exportación sin rol autorizado;
- exportación superior al límite autorizado;
- consulta de proyecto no permitido;
- conciliación con diferencia sin evidencia;
- anulación de fuente con movimientos o reservas relacionados;
- archivo de reporte perteneciente a otro usuario;
- inserción directa de cierre o reporte guardado;
- edición o eliminación de cierre;
- segundo cierre lógico del mismo período;
- caché PWA de rutas `/api/`, `/private/`, `/files/` o `/app/`.

## Evidencia de certificación

El SHA funcional `94e6e8838727ce304500b1d0c4f9d92e6ade96b6` aprobó en GitHub Actions:

- NEXORA app `30284969422`: contratos, instalación, migración, desinstalación, reinstalación, rollback, Chromium, iPhone WebKit y PWA;
- invariantes financieras `30284969713`: MariaDB, integraciones ejecutivas, presupuesto histórico, cierre v3 y concurrencia;
- linters `30284969342`: pre-commit y Semgrep;
- gobierno `30284969347`, documentación `30284969319`, commits semánticos `30284969324` y Patch `30284969475`;
- controles estáticos y de compatibilidad aplicables.

Artefactos principales: aplicación `8660533568`, navegador/PWA `8660543711`, MariaDB `8660589834`, linters `8660425340` y Semgrep `8660405729`.

## Criterio verificable de terminado

**CUMPLIDO.** El bloque tiene código conectado a la interfaz, permisos server-side, auditoría, manejo de errores, pruebas positivas y negativas, documentación, commits publicados, logs y artefactos verificables. El registro documental final debe mantener las mismas compuertas en verde antes de fusionar el PR.
