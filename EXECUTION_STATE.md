# NEXORA — Estado de ejecución

- Última actualización: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica activa: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`, abierto, en borrador y no fusionado
- HEAD de `main` verificado: `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- SHA de código verificado antes de este registro: `2051a19d3424d4db4334a2f4cdf0a82af81e06e4`
- Producción modificada: **NO**
- AWS, Coolify, DNS, secretos o volúmenes modificados: **NO**
- Datos históricos migrados: **NO**
- Integración de Mail iniciada: **NO**

## Bloque activo — mejoras ejecutivas, reportes y cierre

Estado: **NO DEMOSTRADO**.

La ejecución mejora componentes existentes. No reconstruye NEXORA, no reemplaza el dashboard certificado, no crea otro sistema, no introduce un ledger paralelo y no elimina documentos financieros como método de corrección.

## Hecho y publicado

### Dashboard y motor analítico

- Se conserva el contrato certificado del dashboard: selector de proyecto, identidad oficial, acciones de ingreso/gasto, alertas, fondos, presupuesto, evidencias, contratos, inventario y actividad.
- Dashboard, BI01, FI01, FI02, CO01, vistas públicas y cierre semanal consumen el mismo snapshot filtrado.
- El snapshot ya no ejecuta primero la carga masiva de `get_dashboard_summary`; compone la respuesta con consultas paginadas o limitadas.
- Límites visibles: 8 fuentes, 8 gastos, 8 contratos, 8 evidencias, 10 operaciones recientes y 25 registros de avance.
- Totales, vencimientos y categorías se calculan mediante agregados server-side.
- Se conserva el refresco automático `nexora:data-changed`.
- Se muestran ingresos, gastos, devoluciones, transferencias, reservas y reversos como conceptos separados.

### Cortes históricos y presupuesto

- La fecha de una fuente coincide con la fecha de su operación en el Libro Central.
- Fuentes futuras quedan fuera de cortes anteriores.
- PR02 y BI01 seleccionan la última versión presupuestaria aplicable por fecha efectiva, versión y creación.
- Aprobado, comprometido, ejecutado y disponible se calculan hasta la fecha final seleccionada.
- Categoría económica y centro de costo se aplican tanto a líneas aprobadas como a efectos presupuestarios.
- Las obligaciones pendientes se derivan de efectos `Reserved` al corte; no se resta dos veces una obligación ya incluida en la disponibilidad.

### FI01, FI02, CO01 y exportaciones

- FI01 conserva moneda, tasa, remitente, saldos inicial/cierre/actual, transferencias, reservas, conciliación y anulación segura.
- FI02 agrega importes desde `NXR Operation Effect`; una operación multifuente devuelve únicamente la porción de la fuente filtrada.
- CO01 conserva vigencia, valor, ejecutado, pagado, saldo, anticipo, amortización, retención, multas y deducciones.
- Excel y PDF se generan en servidor con permiso `export_reports`, control de proyecto y auditoría.
- Los reportes que superan 5,000 filas se rechazan antes de generarse; no se truncan silenciosamente.
- Los reportes guardados se archivan sin borrado físico.

### Anulación y corrección sin borrado

- La anulación de ingresos se realiza mediante operación compensatoria y conserva el documento, efectos originales, reverso y auditoría.
- No se permite anular una fuente cuando ya tiene gastos, reservas o ajustes relacionados.
- Los cierres y reportes guardados no tienen borrado como flujo operativo.
- Las correcciones de cierre crean un documento nuevo enlazado mediante `correction_of`.

### Cierre semanal canónico v3

- `close/service.py` es el único motor interno y usa `dashboard.snapshot_query.get_executive_snapshot`.
- Versión: `nexora-analytics-v3`.
- El adaptador público solo delega; no parchea ni recalcula un segundo motor.
- Fondos, reservas, obligaciones, presupuesto y avance se obtienen del mismo snapshot filtrado.
- La huella excluye únicamente `generated_at`; conserva proyecto, período, totales y contenido financiero.
- Se conservan número único de 12 dígitos, idempotencia, período único, savepoint, rollback, auditoría, inmutabilidad y corrección enlazada.

### Interfaz de cierre

- Un usuario restringido debe seleccionar un proyecto autorizado antes de calcular o consultar historial.
- Cambiar proyecto o fechas invalida el cálculo anterior.
- La corrección toma proyecto y período del cierre histórico seleccionado, no de filtros distintos de la pantalla.
- Se manejan errores de cálculo, guardado, corrección e historial sin simular éxito.

### Navegador, iPhone y PWA

El smoke permanente fue actualizado para probar:

- dashboard ejecutivo y endpoint filtrado;
- acciones rápidas con el contrato actual de un solo handler;
- FI01, FI02, CO01, PR02 y BI01;
- cálculo de cierre v3 sin guardar datos durante el smoke visual;
- rutas canónicas y autenticación;
- Chromium de escritorio;
- iPhone 13 WebKit y desbordamiento responsive;
- manifiesto, service worker, caché limitada a activos públicos y aviso sin conexión.

## Pruebas incorporadas

- contratos estáticos para snapshot histórico, presupuesto, filtros, exportaciones, anulación, archivo, cierre v3, rendimiento y navegador;
- integración MariaDB para filtros multifuente, versiones presupuestarias históricas y cierre canónico v3;
- validaciones negativas de permisos, eliminación, exportación excesiva, conciliación incompleta, anulación no elegible y período duplicado;
- workflow financiero actualizado para ejecutar las nuevas integraciones y comprobar sintaxis del smoke de navegador.

## Evidencia ejecutada fuera de GitHub Actions

Las siguientes comprobaciones fueron ejecutadas localmente durante esta sesión:

- `node --check` del JavaScript de cierre semanal: aprobado;
- `node --check` de `scripts/nexora_browser_smoke.mjs`: aprobado;
- `ast.parse` y `py_compile` de `dashboard/operational_query.py`, `dashboard/snapshot_query.py` y `dashboard/pending_query.py`: aprobados;
- `py_compile` de los módulos históricos y pruebas nuevas materializadas durante la edición: aprobado.

No fue posible ejecutar Ruff, Prettier, Frappe/MariaDB, Playwright ni Docker localmente porque esas herramientas/runtime no están disponibles en este ejecutor y el acceso externo por DNS está bloqueado. Estas comprobaciones locales no sustituyen CI.

## Bloqueo de certificación reproducido

En el SHA `975337c961f77c7f105b8c3bd52271759cd5f78e`, el workflow `NEXORA app` produjo los jobs:

- `contract`;
- `install-rollback`;
- `Frappe real · escritorio · iPhone · PWA`.

Los tres finalizaron en fallo sin publicar pasos, URL de logs ni artefactos. Se solicitó un rerun de los jobs fallidos y la segunda ejecución reprodujo exactamente el mismo resultado: `steps=None`, `logs_url=None`.

Otros workflows del mismo SHA también terminaron inmediatamente en fallo, incluidos linters, invariantes financieras, documentación, semantic commits, controles de parche y gobierno. No existe mensaje verificable que permita atribuir la causa al código, a facturación, a permisos, a capacidad del runner o a otra condición de plataforma.

Por esta ausencia de ejecución observable, no se declara que hayan pasado:

- Ruff, Prettier o pre-commit;
- instalación/migración/rollback Frappe/MariaDB;
- integraciones completas;
- Chromium, iPhone WebKit o PWA;
- controles de parche, documentación o semantic commits.

## Limitación funcional declarada

Fondos, reservas, presupuesto, obligaciones y avance físico se calculan al corte. El estado contractual y la conciliación documental reflejan el estado vigente al generar la fotografía porque todavía no existe un historial canónico completo de todas las transiciones contractuales, adendas y estados documentales. No se presenta esta limitación como resuelta.

## Criterio pendiente de terminado

El bloque solo podrá cambiar a **IMPLEMENTADO Y VALIDADO** cuando un único SHA publique y apruebe todas las validaciones aplicables, incluyendo:

- pruebas contractuales y puras;
- Ruff, Prettier y linters;
- instalación, migración, desinstalación, reinstalación y rollback Frappe/MariaDB;
- integraciones financieras, ejecutivas y de cierre;
- Chromium de escritorio;
- iPhone WebKit;
- PWA;
- documentación, semantic commits, gobierno y controles de parche;
- artefactos y logs verificables.

El PR permanece en borrador y no debe fusionarse mientras estas evidencias no existan.

## Siguiente acción exacta

1. Verificar el nuevo HEAD creado por este registro.
2. Reintentar los workflows sobre ese SHA.
3. Si aparecen pasos o logs, corregir el primer fallo accionable y repetir hasta verde.
4. Si los jobs vuelven a terminar sin pasos ni logs, resolver fuera del código la habilitación/ejecución de GitHub Actions para el repositorio o la cuenta.
5. Solo después actualizar este documento con los run IDs, artefactos y SHA certificados, marcar el PR listo para revisión y comenzar la integración de Mail.
