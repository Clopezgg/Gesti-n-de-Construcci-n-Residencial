# NEXORA — Bloque ejecutivo, reportes y cierre semanal

Estado del bloque: **NO DEMOSTRADO hasta completar CI, instalación, migración y pruebas de navegador sobre el SHA publicado**.

PR oficial: [#19](https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/19)

## Requisitos trazables

| ID | Requisito | Estado | Evidencia esperada |
|---|---|---|---|
| NXR-EXEC-001 | Un único motor analítico para dashboard, FI01, FI02, CO01, BI01 y cierres | NO DEMOSTRADO | `nexora/dashboard/analytics_core.py`, `nexora/dashboard/executive.py`, CI verde |
| NXR-EXEC-002 | Saldos históricos as-of y separación de transferencias, gastos, reservas y reversos | NO DEMOSTRADO | agregados sobre `NXR Operation Effect`; pruebas puras y Frappe |
| NXR-EXEC-003 | Dashboard premium sin perder el contrato certificado | NO DEMOSTRADO | `nexora-dashboard.js`; contratos y smoke de navegador |
| NXR-REP-001 | FI01 paginado con moneda, tasa, saldos, transferencias y conciliación | NO DEMOSTRADO | endpoint `get_source_statement_page` |
| NXR-REP-002 | FI02 paginado por fuente, categoría, entidad y centro de costo | NO DEMOSTRADO | endpoint `get_expense_page` |
| NXR-REP-003 | CO01 paginado por proyecto, contratista, estado y vigencia | NO DEMOSTRADO | endpoint `get_contract_page` |
| NXR-REP-004 | Excel y PDF server-side con permiso y auditoría | NO DEMOSTRADO | `export_report`; acción `export_reports` |
| NXR-REP-005 | Reportes guardados e historial por usuario | NO DEMOSTRADO | `NXR Saved Report` y servicios asociados |
| NXR-SEC-001 | Acciones separadas y control de proyecto | NO DEMOSTRADO | `permissions.py` y pruebas negativas |
| NXR-REC-001 | Conciliación explícita con usuario, fecha, método, diferencia y evidencia | NO DEMOSTRADO | campos de `NXR Fund Source`; `reconcile_fund_source` |
| NXR-CLOSE-001 | Cierre semanal con número de 12 dígitos, idempotencia, auditoría, hash e inmutabilidad | NO DEMOSTRADO | `NXR Weekly Close`; `close/service.py` |
| NXR-CLOSE-002 | Corrección sin sobrescritura mediante registro compensatorio | NO DEMOSTRADO | `correct_weekly_close` |
| NXR-PERF-001 | Tablas paginadas y paneles con límites | NO DEMOSTRADO | máximo 100 filas por endpoint; paneles de 8 filas |
| NXR-TEST-001 | Pruebas positivas y negativas de cálculo y contratos | NO DEMOSTRADO | `test_executive_analytics.py`, `test_executive_reconstruction_contract.py` |

## Reglas operativas

1. Las cifras financieras se derivan del Libro Central y `NXR Operation Effect`; una transferencia interna nunca se clasifica como gasto.
2. Un reporte histórico mantiene saldo inicial, movimientos del período, saldo al cierre y saldo actual como conceptos separados.
3. La conciliación no se infiere por una referencia escrita. El estado es explícito y la diferencia requiere observación y evidencia.
4. La exportación no se construye en el navegador. El servidor valida `export_reports`, el proyecto, el límite de filas y registra auditoría.
5. Un cierre semanal cerrado no se edita ni elimina. Una corrección crea otro documento enlazado y conserva ambas fotografías.
6. Los documentos nuevos de este bloque reciben número numérico único de 12 dígitos mediante la secuencia canónica.

## Estados y transiciones

### Conciliación de ingreso

- `Pending` → `Reconciled`
- `Pending` → `Disputed`
- `Disputed` → `Reconciled`
- cualquier cambio pasa exclusivamente por el servicio autorizado y queda auditado.

### Cierre semanal

- `Closed`: fotografía original e inmutable.
- `Correction`: fotografía compensatoria ligada mediante `correction_of`.
- no existe transición a borrado ni sobrescritura.

## Efectos financieros

- `Funds`: modifica saldo efectivo de la fuente.
- `Reserved`: modifica reserva y disponibilidad.
- `Internal Transfer`: se presenta como entrada/salida de transferencia, sin aumentar gasto consolidado.
- `Real Return`: restaura fondos y se identifica por separado.
- `is_reversal`: conserva el histórico original y muestra el importe revertido.

## Permisos

- `view_reports`: consulta de reportes.
- `view_financial_details`: acceso a cifras y movimientos.
- `export_reports`: Excel/PDF server-side.
- `view_all_projects`: consulta consolidada sin proyecto.
- `view_closings`: cálculo e historial de cierres.
- `save_closing`: cierre y corrección compensatoria.
- `reconcile_source`: conciliación de ingresos.

El acceso a un proyecto se valida nuevamente en el servidor mediante permisos de `Project`.

## Pruebas de aceptación

### Positivas

- ingreso, gasto, reserva, liberación, transferencia interna, devolución y reversión producen totales esperados;
- consulta histórica devuelve saldo al cierre y saldo actual en columnas distintas;
- Excel y PDF se generan mediante endpoint autorizado;
- cierre repetido con la misma clave devuelve respuesta idempotente;
- cierre del mismo período con otra solicitud concurrente es rechazado por clave única;
- dashboard conserva proyecto, alertas, saldos, reservas, presupuesto, evidencias, contratos e inventario crítico;
- escritorio Chromium, iPhone WebKit y PWA cargan las rutas canónicas.

### Negativas

- fecha final anterior a la inicial;
- exportación sin rol autorizado;
- consulta de proyecto no permitido;
- conciliación con diferencia sin evidencia;
- inserción directa de cierre o reporte guardado;
- edición o eliminación de cierre;
- segundo cierre lógico del mismo período;
- carga mayor al límite de exportación.

## Criterio verificable de terminado

Este bloque cambia a **IMPLEMENTADO Y VALIDADO** únicamente cuando el SHA publicado tenga en verde las pruebas contractuales, invariantes financieras, linters, instalación/migración Frappe/MariaDB, escritorio, iPhone WebKit, PWA, documentación, semantic commits y controles de parche. El PR permanece en borrador y no se fusiona durante esta ejecución.
