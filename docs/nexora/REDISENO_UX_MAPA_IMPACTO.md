# NEXORA — Rediseño UX: verificación y mapa de impacto

## Identificación del bloque

- Bloque: `UX-A — Verificación y mapa de impacto`.
- Fecha de verificación: 2026-07-28.
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
- Rama vigente: `main`.
- HEAD base verificado: `a43214659dcd9f8039d1d93c9a5f4f2d8717501a`.
- Rama histórica `nexora-reconstruccion`: no disponible como rama remota activa en la verificación.
- PR histórico `#11`: cerrado y fusionado; no es un PR de continuidad disponible.
- Producción, AWS, Coolify, DNS, secretos, datos y volúmenes modificados durante UX-A: **NO**.
- Migración de registros históricos: **NO**.

## Decisión de continuidad

La orden más reciente prohíbe crear otro repositorio, rama o Pull Request. Como `#11` ya está fusionado y la rama histórica no está activa, la continuidad real se ejecutará sobre `main`, mediante bloques funcionales coherentes y commits semánticos verificables. No se reabrirá ni recreará el PR histórico.

## Inventario confirmado de experiencia actual

### Navegación y shell

Archivos principales:

- `nexora_app/nexora/public/js/nexora.js`
- `nexora_app/nexora/public/js/nexora_quick_flows.js`
- `nexora_app/nexora/public/js/nexora_operational_ui.js`
- `nexora_app/nexora/public/css/nexora_operational.css`
- `nexora_app/nexora/public/css/nexora_dashboard_fixes.css`
- `nexora_app/nexora/hooks.py`

Hallazgos:

- existe navegación NEXORA por módulos;
- existen acciones rápidas globales para ingresos y gastos;
- los accesos rápidos no utilizan un único componente de captura;
- no existe un contexto global persistente demostrado para proyecto, período, rol, saldo y pendientes;
- el proyecto se transporta de forma puntual mediante `frappe.route_options` y se vuelve a solicitar en varias páginas.

### Dashboard ejecutivo

Archivos principales:

- `nexora_app/nexora/nexora/page/nexora-dashboard/nexora-dashboard.js`
- `nexora_app/nexora/dashboard/executive.py`
- `nexora_app/nexora/dashboard/service.py`
- `nexora_app/nexora/tests/test_dashboard_contract.py`

Hallazgos:

- presenta ingresos, gastos, caja disponible, reservado, presupuesto, contratos, cuentas por pagar, alertas y actividad;
- contiene acciones principales de ingreso y gasto;
- las acciones del dashboard navegan hacia `nexora-finance`;
- todavía no presenta como tareas principales factura, pago, corrección, consulta de saldo, pendientes y reporte;
- no muestra de manera uniforme período activo, usuario, rol y fecha de actualización;
- conserva tablas operativas que en móvil dependen de desplazamiento horizontal.

### Flujo rápido de ingreso

Archivo principal:

- `nexora_app/nexora/public/js/nexora.js`

Servicios utilizados:

- `nexora.financial.service.create_fund_source`

Hallazgos:

- utiliza un diálogo propio;
- fija `currency = HNL` y `exchange_rate = 1` en el cliente;
- no presenta una vista previa financiera visible antes de registrar;
- utiliza la etiqueta visible **Guardar ingreso**;
- no comparte el formulario de la consola operativa;
- no ofrece en el mismo recorrido cuenta guardada, moneda extranjera, tasa visible, saldo anterior y saldo resultante.

### Flujo rápido de gasto

Archivo principal:

- `nexora_app/nexora/public/js/nexora_quick_flows.js`

Servicios utilizados:

- `nexora.financial.service.list_source_balances`
- `nexora.financial.service.preview_central_operation`
- `nexora.financial.service.execute_central_operation`

Hallazgos:

- utiliza un diálogo independiente;
- genera vista previa en servidor, pero no se la muestra al usuario antes de ejecutar;
- fija `operation_date` al día actual;
- exige una sola fuente y no permite distribución multifuente;
- utiliza la etiqueta visible **Guardar gasto**;
- no comparte componente ni esquema visible con `nexora-finance` o `nexora-operations`.

### Fondos y operaciones

Archivo principal:

- `nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js`

Servicios principales:

- `nexora.financial.service.list_analytic_catalogs`
- `nexora.financial.service.list_source_balances`
- `nexora.financial.service.preview_central_operation`
- `nexora.financial.service.execute_central_operation`
- servicios de compromisos;
- `nexora.financial.service.create_fund_source`.

Hallazgos:

- contiene operaciones frecuentes y avanzadas;
- expone simultáneamente numerosos campos técnicos;
- mantiene un alta rápida de fuente separada del registro avanzado;
- usa textos como **Asignaciones por fuente**, **Ejecutar operación**, **Fuente** y **Libro Central**;
- permite distribución multifuente y vista previa real;
- el ingreso se crea mediante una sección separada, no mediante el mismo formulario de gasto;
- utiliza fecha actual en operaciones generales y no el mismo control documental de `nexora-operations`.

### Operación diaria

Archivo principal:

- `nexora_app/nexora/nexora/page/nexora-operations/nexora-operations.js`

Archivos de soporte:

- `nexora_app/nexora/financial/operational_commands.py`
- `nexora_app/nexora/financial/operational_common.py`
- `nexora_app/nexora/financial/operational_income.py`
- `nexora_app/nexora/financial/operational_ledger.py`
- `nexora_app/nexora/financial/operational_accounts.py`
- `nexora_app/nexora/financial/service.py`

Hallazgos:

- implementa cabecera, línea, detalle, vista previa y registro definitivo;
- utiliza códigos `101/102/303/304/501` como punto de entrada;
- ya invalida la vista previa cuando cambian datos;
- separa cuenta existente, cuenta nueva y datos manuales mediante opciones técnicas visibles;
- conserva vocabulario como **Código de movimiento**, **Cuenta frecuente existente**, **Contabilizar**, **Libro Central operativo** y **Evidencia**;
- es reutilizable como base del motor único, pero no es todavía el recorrido guiado predeterminado.

### Correcciones

Archivos principales:

- `nexora_app/nexora/public/js/nexora_operational_ui.js`
- servicios financieros y operativos relacionados con corrección `304`, anulación `303` y reversión `501`;
- formularios de `NXR Operation` y `NXR Fund Source`.

Hallazgos:

- existe corrección guiada por número documental;
- conserva original, auditoría, idempotencia, permisos y efectos;
- la edición directa de documentos ejecutados está bloqueada;
- no todas las acciones correctivas se presentan todavía desde una vista consolidada del documento original;
- los códigos técnicos aún forman parte de la navegación operativa avanzada.

### Contratos y proveedores

Archivos principales:

- `nexora_app/nexora/nexora/page/nexora_contracts/nexora_contracts.js`
- `nexora_app/nexora/nexora/page/nexora_suppliers/nexora_suppliers.js`
- `nexora_app/nexora/contracts/service.py`
- `nexora_app/nexora/purchases/service.py`

Hallazgos:

- existen expedientes, transiciones y servicios reales;
- múltiples opciones y estados aparecen todavía en inglés;
- contratos solicita nuevamente proyecto y fuente principal;
- proveedores muestra clasificaciones y transiciones internas en inglés;
- los mensajes de éxito son breves y no siempre explican la siguiente acción.

### Evidencias

Archivos principales:

- `nexora_app/nexora/nexora/page/nexora_evidence/nexora_evidence.js`
- servicios de evidencia en `nexora_app/nexora/financial/service.py`.

Hallazgos:

- registra archivos privados, hash, versión y revisión humana;
- tipos, canales y estados contienen valores ingleses visibles;
- la página mezcla registro, revisión y listado en una sola vista;
- la tabla reciente no se transforma en tarjetas móviles demostradas.

### Reportes

Archivos principales:

- `nexora_app/nexora/nexora/page/nexora-reports/nexora-reports.js`
- `nexora_app/nexora/reports/service.py`
- `nexora_app/nexora/dashboard/executive.py`

Hallazgos:

- existen BI01, FI01, FI02, FI03, CO01, PR02, PR03 y MM03;
- se reutiliza el motor analítico canónico;
- varios filtros y estados visibles permanecen en inglés;
- utiliza **Fuente** en vez de **Fondo**;
- los códigos de reporte son útiles para usuarios avanzados, pero dominan la experiencia inicial;
- no existe una entrada guiada por pregunta de negocio.

### Buscador universal

Archivos principales:

- `nexora_app/nexora/nexora/page/nexora-search/nexora-search.js`
- `nexora_app/nexora/dashboard/service.py`

Hallazgos:

- busca entidades, contratos, perfiles, compras, presupuestos, operaciones, compromisos, evidencias, fondos e inventario;
- valida permiso `preview` en servidor;
- no incluye todavía proyecto, factura, cuenta guardada, remitente, beneficiario ni referencia externa como alcances explícitos;
- abre formularios técnicos por DocType;
- no ofrece una vista consolidada de documento con efecto financiero, evidencia, historial y acciones autorizadas;
- los resultados se presentan como tabla, sin adaptación móvil mediante tarjetas.

## Duplicaciones confirmadas

1. Registro de ingreso en `nexora.js`, alta de fuente en `nexora_finance.js` e ingreso `101` en `nexora-operations.js`.
2. Registro de gasto en `nexora_quick_flows.js`, gasto general en `nexora_finance.js` y gasto `102` en `nexora-operations.js`.
3. Generación de UUID/idempotencia repetida en múltiples archivos de cliente.
4. Selección de proyecto repetida por página.
5. Traducciones visibles y diccionarios de estados repetidos.
6. Confirmaciones de éxito diferentes para acciones equivalentes.
7. Renderizado de tablas sin un componente móvil común.
8. Reglas condicionales de campos bancarios implementadas en más de un formulario.
9. Vista previa visible en unos recorridos y oculta en otros.

## Modelos y controles financieros que deben conservarse

- `NXR Fund Source`;
- `NXR Financial Account`;
- `NXR Operation`;
- `NXR Operation Effect`;
- `NXR Operation Allocation`;
- `NXR Commitment`;
- `NXR Evidence`;
- numeración documental única de 12 dígitos;
- idempotencia;
- auditoría;
- permisos server-side;
- bloqueo transaccional;
- períodos cerrados;
- saldos independientes por fondo;
- compensaciones, correcciones, anulaciones y reversiones no destructivas.

## Matriz trazable NXR-UX

| Requisito | Estado inicial verificado | Archivos principales de impacto | Bloque previsto |
|---|---|---|---|
| `NXR-UX-001` Motor único | **EXISTENTE PERO DEFECTUOSO** | `nexora.js`, `nexora_quick_flows.js`, `nexora_finance.js`, `nexora-operations.js`, servicios financieros | UX-D / UX-E |
| `NXR-UX-002` Guiado y avanzado | **EXISTENTE PERO DEFECTUOSO** | `nexora-operations.js`, CSS operacional, componentes compartidos | UX-B / UX-D / UX-E |
| `NXR-UX-003` Navegación por tareas | **EXISTENTE Y REUTILIZABLE** con alcance incompleto | dashboard, shell, workspace | UX-C |
| `NXR-UX-004` Contexto persistente | **NO DEMOSTRADO** | shell global, dashboard, páginas, permisos, nuevo servicio de contexto si resulta necesario | UX-C |
| `NXR-UX-005` Vocabulario unificado | **EXISTENTE PERO DEFECTUOSO** | todas las páginas, mensajes, reportes y documentos visibles | UX-B / UX-H |
| `NXR-UX-006` Cuentas simplificadas | **EXISTENTE PERO DEFECTUOSO** | operación diaria, cuentas financieras y servicio de cuentas | UX-D |
| `NXR-UX-007` Dashboard decisional | **EXISTENTE Y REUTILIZABLE** con información/contexto incompleto | dashboard y servicio ejecutivo | UX-C |
| `NXR-UX-008` Ingreso guiado | **EXISTENTE PERO DEFECTUOSO** | tres entradas de ingreso y servicios de fuente/operación | UX-D |
| `NXR-UX-009` Gasto y pago guiados | **EXISTENTE PERO DEFECTUOSO** | tres entradas de gasto, compromisos, proveedores y asignaciones | UX-E |
| `NXR-UX-010` Efecto financiero | **EXISTENTE PERO DEFECTUOSO** | servicios preview/execute y confirmaciones de cliente | UX-D / UX-E |
| `NXR-UX-011` Corrección desde original | **EXISTENTE Y REUTILIZABLE** con acceso contextual incompleto | UI correctiva, operación, fuente y buscador | UX-F |
| `NXR-UX-012` Tarjetas móviles | **NO DEMOSTRADO** para tablas complejas | dashboard, operación, buscador, evidencia, reportes, CSS | UX-G |
| `NXR-UX-013` Revelación progresiva | **EXISTENTE PERO DEFECTUOSO** | operación diaria, finanzas, contratos, proveedores, evidencia | UX-B / UX-D / UX-E |
| `NXR-UX-014` Estados comprensibles | **EXISTENTE PERO DEFECTUOSO** | páginas, servicios, diccionarios visibles, reportes | UX-B / UX-H |
| `NXR-UX-015` Búsqueda y acceso directo | **EXISTENTE PERO DEFECTUOSO** | `nexora-search.js`, `dashboard/service.py`, vista consolidada | UX-H |

## Riesgos

### Integridad financiera

- reemplazar flujos visibles sin conservar `preview_hash` e idempotencia;
- modificar el significado de una operación al ocultar campos avanzados;
- permitir diferencias entre acceso rápido y consola;
- reutilizar cálculos de cliente para saldos críticos;
- perder relaciones de cuenta, fondo, proyecto, evidencia o clasificación.

### Operación diaria

- cambio involuntario del proyecto activo con datos sin guardar;
- botones rápidos que abran una ruta incorrecta;
- formularios extensos en iPhone;
- doble envío durante cargas lentas;
- traducciones visibles que no coincidan con estados canónicos.

### Compatibilidad

- Frappe utiliza nombres internos y estados en inglés que no deben renombrarse destructivamente;
- los documentos existentes y reportes dependen de códigos canónicos;
- la consolidación debe mantener contratos públicos de servicios mientras migra la interfaz;
- las pruebas contractuales actuales verifican textos y rutas que deberán actualizarse junto con la implementación.

## Dependencias por bloque

1. UX-B debe definir un diccionario visible y componentes compartidos antes de unificar formularios.
2. UX-C debe establecer el contexto global antes de conectar los accesos rápidos.
3. UX-D y UX-E deben reutilizar servicios canónicos y conservar compatibilidad temporal controlada.
4. UX-F depende de la vista consolidada de documento y de las reglas correctivas existentes.
5. UX-G depende de componentes y tablas estabilizados.
6. UX-H cierra buscador, consistencia terminológica, regresión y documentación.

## Estrategia de implementación confirmada

- no crear otro repositorio, aplicación, rama o PR;
- trabajar secuencialmente sobre `main` por bloques coherentes;
- no modificar producción ni infraestructura;
- preservar servicios financieros centrales;
- migrar los accesos rápidos para que abran el mismo flujo principal;
- introducir compatibilidad temporal únicamente cuando esté probada y documentada;
- publicar cada bloque con commit semántico y SHA remoto;
- ejecutar CI y corregir cualquier fallo antes de continuar.

## Criterio de cierre UX-A

UX-A queda terminado cuando este mapa y `EXECUTION_STATE.md` estén publicados en GitHub sobre el HEAD remoto vigente. No clasifica como implementado ninguno de los requisitos UX funcionales; únicamente fija el estado inicial, archivos de impacto, riesgos, dependencias y orden de ejecución.
