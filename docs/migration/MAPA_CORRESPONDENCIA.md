# Mapa de correspondencia origen → destino

`Legacy Record` significa preservación versionada del payload saneado, con hash, ID original, fechas, estado de eliminación y enlace al documento destino cuando existe.

| Origen | Destino definitivo | Transformación |
|---|---|---|
| settings | ConstruControl Settings + Project + Legacy Record | Conserva configuración; compañía/almacén/centro de costo se seleccionan en ERPNext. |
| phases | Task + Legacy Record | Estado y porcentaje se convierten; ID original queda enlazado. |
| incomes | ConstruControl Fund Entry + Legacy Record | Fechas, moneda, tasa, monto HNL, remitente y evidencia. |
| expenses | ConstruControl Expense Record + Legacy Record | Proveedor, fuente de fondos, contrato, estados, documento y evidencia. |
| laborContracts | Legacy Record; opcional Supplier + Contract | Sólo en modo de documentos estándar y siempre en borrador. |
| materials | Legacy Record; opcional Item | No crea movimientos de stock históricos automáticamente. |
| inventoryMovements | Legacy Record + módulo Stock de ERPNext | Se conserva el movimiento; su contabilización requiere conciliación de almacenes/lotes. |
| progressUpdates | ConstruControl Progress Update + Task + Legacy Record | Avance, calidad, responsable, ubicación, etiquetas y archivos. |
| weeklyClosings | ConstruControl Weekly Closing + Legacy Record | Snapshot financiero y pendientes en JSON auditable. |
| reports | Legacy Record + Report Builder/Query Reports | ERPNext sustituye el generador antiguo. |
| notificationContacts/rules/logs | Legacy Record + Notification/Email Queue | Reglas antiguas se conservan; no se activan automatizaciones sin revisión. |
| auditLogs | ConstruControl Audit Event + Legacy Record | Evento append-only, hashes y estado anterior/siguiente. |
| userAccounts | Legacy Record; opcional User + rol | Sin contraseñas; creación desactivada por defecto y sin correo de bienvenida. |
| procurementRequests | Legacy Record + Material Request/Purchase | ERPNext cubre el flujo; el histórico ambiguo no se publica. |
| equipmentRecords | Legacy Record + Asset/Maintenance | Se conserva serialización/estado para conciliación con Asset. |
| changeOrders | ConstruControl Change Order + Project/Task/Contract | Impacto de costo/plazo y decisión. |
| approvalRequests | ConstruControl Approval + Workflow | Solicitud, prioridad, monto, comentarios y decisión. |
| enterprisePlatform.projects | Project + Legacy Record | Proyecto estándar como registro principal. |
| permissionOverrides | Legacy Record + User Permission/Role Permission | Los overrides no se activan automáticamente para evitar escalamiento. |
| partners | Legacy Record; opcional Supplier | Datos comerciales completos preservados. |
| catalog | Legacy Record; opcional Item | Catálogo estándar cuando se habilita el modo correspondiente. |
| payables | Legacy Record + Accounts Payable/Purchase Invoice | No crea deuda contable sin compañía/cuentas/impuestos conciliados. |
| documentTemplates | Legacy Record + Print Format | Plantillas conservadas para conversión controlada. |
| automationRules/executions | Legacy Record + Workflow/Notification/Scheduled Job | No ejecuta reglas históricas durante importación. |
| dailyLogs | Legacy Record + Project/Communication/Timesheet | ERPNext conserva el contexto operacional. |
| crewMembers/crewAttendance | Legacy Record + Employee/Attendance si HRMS está instalado | ERPNext 15 separado de HRMS; no se inventan empleados. |
| tools/toolLoans | Legacy Record + Asset/Asset Movement | Seriales y préstamos preservados. |
| safetyIncidents | Legacy Record + Issue/Quality/Health & Safety | Se mantiene evidencia y trazabilidad. |
| signatures | Legacy Record + File/Workflow | Firmas se adjuntan; no se reinterpretan como firma criptográfica. |
| immutableAudit | ConstruControl Audit Event + Legacy Record | Cadena de hash preservada y no eliminable. |
| backupHistory | Legacy Record + Migration Run/Backups | Mantiene referencia histórica sin incorporar archivos inexistentes. |

## Roles

| Rol origen | Rol destino |
|---|---|
| admin | ConstruControl Manager |
| operator | ConstruControl Operator |
| auditor | ConstruControl Auditor |
| consultant / viewer | ConstruControl Viewer |

Los permisos Frappe por DocType y documento son definitivos. Los roles no obtienen permisos contables, de compras o stock por esta migración; esos permisos se conceden mediante roles estándar de ERPNext según responsabilidad real.

## Identidad e idempotencia

- Cada fuente se identifica por `project_key + entity_type + source_id`.
- Cada versión preservada agrega el SHA-256 canónico del payload.
- Una fuente completa ya importada se reconoce por SHA-256 y se reutiliza.
- Los documentos ConstruControl usan una clave estable para evitar duplicados.
- IDs sin valor reciben una identidad determinista y se reportan como advertencia.
- IDs duplicados y relaciones huérfanas son errores de preflight.
