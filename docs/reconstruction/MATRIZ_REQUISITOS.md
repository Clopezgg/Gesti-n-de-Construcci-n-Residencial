# Matriz de requisitos de reconstrucción de ConstruControl

> Implementación y certificación se registran por separado. Ningún requisito se acepta por porcentajes declarativos.

| ID | Requisito | Módulo | Implementación | Evidencia funcional | Certificación requerida |
|---|---|---|---|---|---|
| GOV-01 | Rama única, PR único, `main` protegido y sin force push | Gobierno | Completa | PR #9 y validadores de gobierno | Auditoría 1:1 |
| ARC-01 | Arquitectura productiva única | Infraestructura | Completa | AWS EC2 + Coolify + Docker Compose + MariaDB | C / FINAL |
| US01-01 | Usuarios, perfiles, roles y permisos backend | US01 | Completa | Matriz positiva y negativa | FINAL |
| FI01-01 | Fondos, remesas, monedas, conciliación y saldos | FI01 | Completa | Reglas financieras canónicas | A / FINAL |
| FI02-01 | Gastos, proveedores, facturas, aprobaciones, pagos y CxP | FI02 | Completa | Ciclo pendiente/aprobado/rechazado/reabierto/pagado/anulado/revertido | A / FINAL |
| PR01-01 | Proyectos, fases, planificación y presupuestos | PR01 | Completa | Costos reales, comprometidos y pendientes | A / FINAL |
| CO01-01 | Contratos, anticipos, retenciones, pagos y saldos | CO01 | Completa | Regresiones contractuales | A / FINAL |
| MM01-01 | Materiales, unidades y categorías | MM01 | Completa | Validación de datos y costos | B / FINAL |
| MM02-01 | Solicitudes, cotizaciones, compras y recepciones | MM02 | Completa | Relaciones proveedor/orden/recepción/FI02 | B / FINAL |
| MIGO-01 | Entradas, consumos, devoluciones, transferencias y ajustes | MIGO | Completa | Bloqueo de stock negativo y duplicados | B / FINAL |
| QC01-01 | Avance, calidad, evidencias y alertas | QC01 | Completa | Evidencia privada y regresiones de avance | B / FINAL |
| CL01-01 | Cierres semanales y conciliación | CL01 | Completa | Cierre idempotente y reapertura autorizada | B / FINAL |
| BI01-01 | Dashboard, indicadores, filtros, drill-down y CSV | BI01 | Completa | Resumen canónico y exportación privada | B / FINAL |
| AU01-01 | Identidad, acción, origen, correlación, huella e inmutabilidad | AU01 | Completa | Eventos y snapshots sin secretos | B / FINAL |
| MOB-01 | Escritorio, iPhone, móvil y PWA | UI/PWA | Completa | Manifest, service worker, versión y caché segura | C / FINAL |
| INF-01 | MariaDB, Redis, workers, scheduler, WebSocket y HTTPS | Infraestructura | Completa | Diez servicios con health check y puertos privados | C / FINAL |
| PERSIST-01 | Persistencia tras recarga, reinicio y redeploy | Infraestructura | Completa | Marcador runtime antes/después del restart | C / FINAL |
| BAK-01 | Backup completo verificable | Operación | Completa | Base, archivos, configuración, tamaños y SHA-256 | C / FINAL |
| RESTORE-01 | Restauración en ensayo | Operación | Completa | Sitio aislado, tres migraciones, smoke y conciliación | C / FINAL |
| MIG-01 | Migración, idempotencia, conciliación y rollback | MIG | Completa en código | Runtime, contratos y evidencia de importación | C / FINAL |
| DEMO-01 | Clasificación segura de datos demo | Operación | Completa | Inventario no destructivo y dependencias | C / FINAL |
| DOC-01 | Manual oficial único y arquitectura sin contradicciones | Documentación | Completa | `MANUAL_PASO_A_PASO.md` | C / AUDIT |
| REG-01 | Puertas agrupadas no autorreferenciales | Calidad | Completa | Workflow secuencial con artifacts | A/B/C/FINAL |
| AUDIT-01 | Auditoría independiente 1:1 | Auditoría | Implementada | Script independiente, tests y snapshot de fuente | AUDIT_1_TO_1 |

## Commits funcionales relevantes

- Bloques 1–4: commits documentados en las auditorías de reconstrucción.
- Sprint A: commits documentados en el historial del PR #9.
- Bloque 8: `6f60d782683c28e5514f8dfbecd4b47c90e5db80`, `40409c46da58028c74abe92a47cdfe56373dfb77`.
- Bloque 9: `5dd5379ea04578e4748dfe374562f688908f6ffc`, `4726ca09d869eb6b201c227478f9b6c0a459c361`.
- Bloque 10: `01ec1389282023b3a53d1cba7d452caeabbda678`.
- Bloque 11: `43846b02b8b7d69f0e4c03e56780a4464a47405c`.
- Bloque 12 y certificación: commit que contiene esta matriz.

## Regla final

El sistema no se declara aprobado mientras exista una puerta fallida, pendiente o cancelada, un restore no demostrado, una migración no conciliada o una auditoría 1:1 sin evidencia.
