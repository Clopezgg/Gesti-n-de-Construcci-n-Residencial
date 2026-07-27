# NEXORA — Mejoras ejecutivas, reportes y cierre semanal

Estado del bloque: **NO DEMOSTRADO hasta completar CI, instalación, migración y pruebas de navegador sobre un único SHA publicado**.

PR oficial: [#19](https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/19)

Este bloque mejora la implementación acordada. No reemplaza el dashboard certificado, no crea un sistema paralelo y no reconstruye los módulos funcionales existentes.

## Requisitos trazables

| ID | Requisito | Estado | Evidencia esperada |
|---|---|---|---|
| NXR-EXEC-001 | Un motor financiero canónico para dashboard, FI01, FI02, BI01 y cierres | NO DEMOSTRADO | `NXR Operation Effect`, adaptadores ejecutivos y CI verde |
| NXR-EXEC-002 | Saldos históricos `as-of` y separación de transferencias, gastos, reservas, devoluciones y reversos | NO DEMOSTRADO | agregados por fecha de operación y pruebas Frappe |
| NXR-EXEC-003 | Dashboard premium sin perder el contrato certificado | NO DEMOSTRADO | `nexora-dashboard.js`; contratos y smoke de navegador |
| NXR-EXEC-004 | Anulaciones y reversos visibles, sin ocultar el ingreso bruto original | NO DEMOSTRADO | KPI y alerta de movimientos compensados |
| NXR-REP-001 | FI01 paginado con moneda, tasa, saldos, transferencias, conciliación y anulación segura | NO DEMOSTRADO | `get_source_statement_page` y acción compensatoria |
| NXR-REP-002 | FI02 paginado por fuente, categoría, entidad y centro de costo | NO DEMOSTRADO | `dashboard/expense_query.py` |
| NXR-REP-003 | CO01 paginado por proyecto, contratista, estado y vigencia | NO DEMOSTRADO | `get_contract_page` |
| NXR-REP-004 | Excel y PDF server-side con permiso, auditoría y rechazo de exceso de filas | NO DEMOSTRADO | `reports/safe_export.py`; acción `export_reports` |
| NXR-REP-005 | Reportes guardados e historial por usuario | NO DEMOSTRADO | `NXR Saved Report` y servicios asociados |
| NXR-REP-006 | Archivo de reportes sin borrado ni pérdida de número, filtros o auditoría | NO DEMOSTRADO | `reports/actions.py` y acción real en interfaz |
| NXR-SEC-001 | Acciones separadas y control de proyecto en servidor | NO DEMOSTRADO | `permissions.py` y pruebas negativas |
| NXR-REC-001 | Conciliación explícita con usuario, fecha, método, diferencia y evidencia | NO DEMOSTRADO | campos de `NXR Fund Source`; `reconcile_fund_source` |
| NXR-CAN-001 | Anulación de ingreso mediante operación compensatoria y sin eliminación física | NO DEMOSTRADO | `cancel_fund_source`; reverso ligado y auditoría |
| NXR-CLOSE-001 | Cierre semanal con número de 12 dígitos, idempotencia, auditoría, hash e inmutabilidad | NO DEMOSTRADO | `NXR Weekly Close`; `close/service.py` |
| NXR-CLOSE-002 | Corrección sin sobrescritura mediante nuevo registro enlazado | NO DEMOSTRADO | `correct_weekly_close` |
| NXR-CLOSE-003 | Reservas y presupuesto calculados al corte histórico | NO DEMOSTRADO | `close/as_of.py`; motor `nexora-analytics-v2` |
| NXR-PERF-001 | Tablas paginadas y paneles con límites | NO DEMOSTRADO | máximo 100 filas por endpoint; paneles de 8 filas |
| NXR-TEST-001 | Pruebas positivas, negativas, contractuales e integración MariaDB | NO DEMOSTRADO | módulos `test_*executive*`, `test_*archive*`, `test_*history*` |

## Reglas operativas

1. Las cifras financieras se derivan del Libro Central y `NXR Operation Effect`; una transferencia interna nunca se clasifica como gasto.
2. La fecha del ingreso y la fecha de su operación canónica deben coincidir, para que una fuente futura no altere un corte anterior.
3. Un reporte histórico mantiene saldo inicial, movimientos del período, saldo al cierre y saldo actual como conceptos separados.
4. Un reverso no se suma como gasto ordinario: se informa como importe compensado y mantiene visible el ingreso original.
5. FI02 aplica fuente, categoría y centro de costo a los efectos asignados antes de agregar el importe. Una operación multifuente muestra únicamente la porción seleccionada.
6. La conciliación no se infiere por una referencia escrita. El estado es explícito y la diferencia requiere observación y evidencia.
7. La exportación no se construye en el navegador. El servidor valida `export_reports`, proyecto y volumen; un reporte superior al límite se rechaza y nunca se trunca silenciosamente.
8. Un ingreso solo puede anularse directamente cuando conserva íntegro su efecto inicial y no tiene gastos, reservas ni ajustes relacionados. La anulación genera un efecto inverso, marca la operación original como compensada y conserva auditoría.
9. Un reporte guardado no se elimina: se archiva por su propietario, conservando número, filtros y eventos de auditoría.
10. Un cierre semanal cerrado no se edita ni elimina. Una corrección crea otro documento enlazado y conserva ambas fotografías.
11. Los documentos nuevos reciben número numérico único de 12 dígitos mediante la secuencia canónica.

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
- Cualquier cambio pasa exclusivamente por el servicio autorizado y queda auditado.

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
- `Internal Transfer`: se presenta como entrada/salida de transferencia, sin aumentar gasto consolidado.
- `Real Return`: restaura fondos y se identifica por separado.
- `is_reversal`: conserva el histórico original y muestra el importe revertido.
- `closing_available_hnl`: fondos al corte menos reservas al corte.
- `projected_available_hnl`: igual al disponible al corte cuando las reservas ya representan compromisos; las obligaciones informativas se muestran por separado para evitar doble conteo.

## Base histórica del cierre semanal v2

- fondos, gastos, ingresos y reservas: efectos con `operation_date` igual o anterior al cierre;
- presupuesto aprobado: última versión no borrador/no anulada con `effective_date` igual o anterior al cierre;
- comprometido y ejecutado presupuestario: efectos de dimensión `Budget` hasta la fecha de cierre;
- avance físico: último registro aprobado hasta la fecha de cierre;
- cuentas pendientes: reserva financiera al cierre, no el estado mutable actual de cuentas por pagar.

Limitación explícita: el estado contractual y la conciliación documental guardados en el cierre reflejan el estado vigente al momento de generar la fotografía. La reconstrucción histórica exacta de contratos requiere un historial canónico de adendas y transiciones; no se presenta como resuelta por este bloque.

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
- consulta histórica devuelve saldo al cierre y saldo actual en columnas distintas;
- Excel y PDF se generan mediante endpoint autorizado;
- anulación elegible crea reverso, conserva el documento original y refresca dashboard/reportes;
- reporte guardado se archiva de forma idempotente y desaparece de la lista activa;
- cierre repetido con la misma clave devuelve respuesta idempotente;
- cierre del mismo período con otra solicitud es rechazado por clave única;
- cierre v2 guarda reservas y presupuesto calculados al corte;
- dashboard conserva proyecto, alertas, saldos, reservas, presupuesto, evidencias, contratos e inventario crítico;
- escritorio Chromium, iPhone WebKit y PWA cargan las rutas canónicas.

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
- segundo cierre lógico del mismo período.

## Criterio verificable de terminado

Este bloque cambia a **IMPLEMENTADO Y VALIDADO** únicamente cuando el SHA publicado tenga en verde pruebas contractuales, invariantes financieras, linters, instalación/migración Frappe/MariaDB, escritorio, iPhone WebKit, PWA, documentación, semantic commits y controles de parche. El PR permanece en borrador y no se fusiona con validaciones fallidas o pendientes.
