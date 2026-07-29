# AUDITORÍA COMPLETA — NEXORA

Fecha: 2026-07-29  
Repositorio auditado: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`  
Rama local auditada: `work`  
HEAD base auditado: `51baddb39da21aa5fcc1aae5c0d068da4333cdb1`

## 1. Resumen ejecutivo

Se realizó una auditoría técnica, funcional, de experiencia de usuario, seguridad y arquitectura sobre el repositorio completo. La revisión incluyó estructura de apps Frappe/ERPNext, hooks, páginas, assets, DocTypes, pruebas, scripts, documentación, validadores, workflows y módulos heredados de ConstruControl que aún operan como compatibilidad interna.

El producto visible debe seguir siendo **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**. Por esa razón no se hizo un renombrado masivo de rutas o DocTypes ConstruControl: esas referencias todavía son parte de compatibilidad, fixtures, permisos, migraciones y validadores. La corrección aplicada se limitó a problemas verificables, de bajo riesgo y compatibles con el comportamiento existente.

Nivel general de calidad: **bueno con deuda operativa controlada**. El repositorio tiene contratos y validadores específicos, escaneo de secretos y pruebas standalone amplias. Las principales limitaciones reales son de entorno: falta de remoto `origin`, falta de `PyYAML==6.0.2` por bloqueo de red al intentar instalarlo, y ausencia de un sitio Frappe/bench real para ejecutar pruebas end-to-end con base de datos.

## 2. Problemas críticos

No se encontró un problema crítico corregible de forma segura dentro de este lote sin cambiar comportamiento funcional o requerir infraestructura externa.

## 3. Problemas altos

- **Git/publicación — Alta:** el clon local no tiene remoto `origin`; por tanto no se pudo verificar ni sincronizar `main` remoto, ni publicar el commit según la regla operativa del proyecto. No se corrigió porque requiere configurar credenciales/remoto externo.
- **Validación de entorno — Alta:** no hay sitio Frappe/bench con base de datos disponible para validar todos los botones, formularios, permisos y flujos reales como usuario final. Se mitigó con validadores estáticos, compilación, checks Node y pruebas standalone, pero no sustituye una prueba E2E real.

## 4. Problemas medios

- **Seguridad/UI — Media:** el flujo guiado de operaciones insertaba el período activo dentro de `innerHTML` usando un valor proveniente de contexto de sesión/ruta. Aunque el valor normalmente lo genera NEXORA, podía contener texto no escapado y convertirse en una superficie XSS si se contaminaba el contexto del cliente. Se corrigió escapando explícitamente el período antes de renderizarlo.
- **Dependencias de validación — Media:** `scripts/validate_repository.py` y una prueba standalone de infraestructura requieren `PyYAML==6.0.2`; el intento de instalación falló por bloqueo de red/proxy `403 Forbidden`.

## 5. Problemas bajos

- Exportaciones `__all__` no ordenadas en módulos de compatibilidad.
- Variables desempaquetadas no usadas en módulos de inventario y calidad.
- Variable ambigua de una sola letra en cálculo total de inventario.
- Excepción de importación de prueba Frappe no documentada mediante `# noqa: E402`.
- Supresión `noqa` innecesaria en monitor local.

## 6. Funcionalidades incompletas

No se añadió ni eliminó funcionalidad. Se identificaron áreas que deben validarse en un entorno real antes de declararlas completas:

- Recorridos completos de dashboard, operaciones, reportes, cierres, inventario, compras, proveedores, evidencias y permisos por rol.
- Instalación PWA en escritorio/iPhone y comportamiento offline/recarga.
- Migraciones y rollback en sitio bench con datos reales.
- Confirmación de que las rutas ConstruControl visibles remanentes estén absorbidas por NEXORA o justificadas como compatibilidad interna.

## 7. Procesos de negocio incorrectos

No se modificaron procesos financieros ni cálculos de saldos. Los validadores disponibles confirmaron contratos financieros canónicos, 10 DocTypes financieros y 37 DocTypes funcionales de integración. Los procesos de negocio que no pudieron verificarse dinámicamente son los que dependen de un sitio Frappe con base de datos y usuarios reales.

## 8. Inconsistencias de interfaz

- Se detectó riesgo de render inseguro en el mensaje de ayuda del flujo guiado de operaciones. La corrección mantiene el mismo texto visible pero escapa el período activo antes de insertarlo en HTML.
- Persisten referencias visibles/funcionales a ConstruControl en módulos heredados. No se renombraron en este lote para evitar romper rutas, permisos, fixtures, migraciones o pruebas existentes.

## 9. Problemas de arquitectura

- El repositorio combina ERPNext upstream, capa heredada ConstruControl y app NEXORA. Esta arquitectura es viable solo si NEXORA permanece como experiencia principal y ConstruControl queda como referencia/compatibilidad interna.
- No se detectó una razón segura para reescribir servicios o crear ledgers paralelos. Se evitó sobreingeniería y se mantuvieron los contratos existentes.
- El inventario de archivos fue regenerado para reflejar el nuevo archivo de auditoría y mantener la metadata arquitectónica sincronizada.

## 10. Riesgos de seguridad

- **Corregido:** escape explícito del período activo antes de renderizarlo dentro del HTML del flujo guiado.
- **Validado:** escaneo de secretos sin hallazgos.
- **Pendiente:** revisión manual/E2E de todos los usos de `innerHTML` con datos dinámicos y verificación de permisos por rol en un sitio real.

## 11. Riesgos futuros

- Duplicar navegación o identidad entre NEXORA y ConstruControl puede confundir al usuario si no se completa la absorción gradual.
- Los validadores dependientes de PyYAML seguirán bloqueados en entornos sin la dependencia instalada.
- Un entorno Git sin remoto válido impide cumplir la trazabilidad final de `main`.
- Optimizar rendimiento sin métricas de bench/base real puede producir cambios innecesarios.

## 12. Archivos modificados

| Archivo | Motivo | Impacto | Riesgo |
| --- | --- | --- | --- |
| `AUDITORIA_COMPLETA.md` | Documentar auditoría completa, severidades, validaciones y limitaciones. | Evidencia verificable del lote. | Bajo. |
| `docs/architecture/file_inventory.json` | Sincronizar inventario tras añadir la auditoría. | Metadata arquitectónica consistente. | Bajo. |
| `erpnext/construcontrol/business_rules.py` | Ordenar `__all__`. | Menos ruido estático. | Bajo. |
| `erpnext/construcontrol/controllers.py` | Ordenar `__all__`. | Exportaciones estables. | Bajo. |
| `erpnext/construcontrol/inventory.py` | Marcar variables no usadas como intencionales. | Claridad sin cambio lógico. | Bajo. |
| `erpnext/construcontrol/quality.py` | Marcar variables no usadas como intencionales. | Claridad sin cambio lógico. | Bajo. |
| `erpnext/construcontrol/weekly.py` | Ordenar `__all__`. | Exportaciones estables. | Bajo. |
| `nexora_app/nexora/inventory/service.py` | Renombrar variable ambigua `l` a `line`. | Mayor legibilidad. | Bajo. |
| `nexora_app/nexora/public/js/nexora_quick_flows.js` | Escapar `context.period` antes de renderizar HTML. | Reduce riesgo XSS sin cambiar UX esperada. | Bajo/medio. |
| `nexora_app/nexora/tests/test_browser_acceptance_contract.py` | Añadir contrato para impedir regresión del escape del período. | Cobertura preventiva de seguridad/UX. | Bajo. |
| `nexora_app/nexora/tests/test_operational_integration.py` | Documentar excepción Frappe `# noqa: E402`. | Lint explícito sin alterar prueba. | Bajo. |
| `tools/nexora_monitor/dashboard.py` | Quitar `noqa` innecesario. | Menos deuda estática. | Bajo. |

## 13. Justificación de cada cambio

- Los cambios Python son de mantenibilidad y no alteran contratos, cálculos, hooks ni persistencia.
- El cambio JavaScript corrige una anomalía de seguridad/UX: datos de contexto no deben entrar a `innerHTML` sin escape.
- La prueba añadida convierte esa regla en contrato para evitar regresiones.
- El inventario se actualizó porque el repositorio ahora contiene un archivo auditado adicional.

## 14. Recomendaciones de mejora

- Configurar `origin` y ejecutar sincronización/push contra `main` desde un entorno autorizado.
- Instalar `PyYAML==6.0.2` en la imagen de validación o vendorizar el validador para no depender de instalaciones manuales.
- Ejecutar smoke E2E con Playwright contra bench real en escritorio e iPhone.
- Revisar cada uso de `innerHTML` y migrar a DOM seguro cuando procese datos dinámicos.
- Completar la absorción visual de ConstruControl dentro de NEXORA sin renombrar identificadores persistidos hasta tener migraciones y pruebas.
- Mantener refactors pequeños, orientados por defectos reproducibles, sin crear dashboards, ledgers o fuentes de saldo paralelas.

## 15. Problemas que no pudieron corregirse y por qué

- **Remoto `origin` ausente:** no puede corregirse sin conocer URL/credenciales autorizadas del repositorio remoto.
- **`PyYAML==6.0.2` ausente:** se intentó instalar con `python -m pip install 'PyYAML==6.0.2'`, pero la red/proxy devolvió `403 Forbidden` contra el índice de paquetes.
- **Pruebas Frappe E2E reales:** no hay sitio bench/base de datos/usuarios reales en este contenedor.
- **Renombrado completo ConstruControl → NEXORA:** no se ejecutó porque implicaría rutas, DocTypes, permisos, fixtures y migraciones; debe hacerse en lotes funcionales con pruebas de datos.

## Validación ejecutada

- `python -m compileall -q scripts nexora_app/nexora erpnext/construcontrol tools/nexora_monitor`
- `node --check nexora_app/nexora/public/js/nexora_quick_flows.js`
- `node --check scripts/nexora_browser_smoke.mjs`
- `node --check scripts/nexora_browser_validators.mjs`
- `node --check tools/nexora_monitor/audit_cli.js`
- `node --check tools/nexora_monitor/final_gate_check.js`
- `python scripts/scan_nexora_secrets.py`
- `python scripts/validate_nexora_app.py`
- `python scripts/validate_nexora_financial_models.py`
- `python scripts/validate_construcontrol_integration.py`
- `PYTHONPATH=nexora_app python -m unittest nexora.tests.test_browser_acceptance_contract.TestBrowserAcceptanceContract.test_guided_operation_period_context_is_escaped_before_html_render -v`
- `python -m unittest discover -s erpnext/construcontrol/tests -p 'test_*_standalone.py' -v` ejecutó 231 pruebas; 230 pasaron y 1 falló por falta de `yaml`/PyYAML.

## Validaciones bloqueadas

- `python scripts/validate_repository.py` bloqueado por falta de PyYAML.
- Instalación de PyYAML bloqueada por red/proxy `403 Forbidden`.
- Validación de SHA remoto en `main` bloqueada por ausencia de remoto `origin`.

## 16. Recorrido módulo por módulo

Criterio usado: un módulo solo se marca **validado funcionalmente** si se ejecutó en un sitio Frappe/bench con datos, permisos y recorrido visible real. En este entorno no existe ese sitio; por tanto los módulos quedan **revisados estáticamente / pendientes de validación funcional real** cuando dependen de UI, base de datos o usuarios.

| Módulo | Objetivo | Flujo esperado | Acciones revisadas | Estado de verificación | Hallazgos/anomalías |
| --- | --- | --- | --- | --- | --- |
| Inicio y shell NEXORA | Ser la entrada principal con navegación, contexto de proyecto y acciones rápidas. | Usuario entra a `nexora-dashboard`, selecciona proyecto/período y navega a operaciones, reportes, cierres y entidades. | Hooks, assets, app screen, páginas NEXORA y navegación global. | Revisado estáticamente; no validado en navegador real. | Riesgo pendiente: confirmar que ningún rol ordinario queda expuesto a navegación ERPNext genérica. |
| Dashboard ejecutivo | Mostrar salud financiera, avance, alertas, actividad y accesos a acciones. | Cargar resumen, filtrar por proyecto/período, abrir ingreso/gasto/reportes/detalles. | Servicios `dashboard`, consultas operativas, acciones rápidas y validadores browser. | Revisado estáticamente; no validado con datos reales. | Requiere smoke E2E para confirmar botones y estados vacíos. |
| Operaciones financieras guiadas | Registrar ingresos, gastos/pagos y correcciones con vista previa, idempotencia y saldos. | Elegir movimiento, capturar datos conocidos, previsualizar impacto, ejecutar y ver ledger. | Catálogo, cuentas, preview/execute, doble envío, correcciones y contexto guiado. | Revisado estáticamente; corrección aplicada al render del período. | Corregido riesgo XSS por `context.period`; queda pendiente validar formularios completos en bench. |
| Fondos, cuentas e ingresos | Gestionar fuentes de fondos, remesas, depósitos, efectivo, transferencias y conciliación. | Crear fuente/cuenta, registrar ingreso, listar saldos, cancelar con trazabilidad. | `financial.sources`, `operational_income`, cuentas financieras y dashboard de fondos. | Revisado estáticamente; validadores financieros OK. | No validado con instituciones/cuentas reales ni permisos por rol. |
| Gastos, pagos y cuentas por pagar | Registrar obligaciones, pagos parciales/totales y afectación de fondos. | Capturar beneficiario/clasificación/medio, distribuir fondos, previsualizar, ejecutar y actualizar saldos. | `financial.operational`, commitments, referencias/correcciones y reportes. | Revisado estáticamente; validadores financieros OK. | No se pudo validar flujo de pago con documentos reales en UI. |
| Libro central / ledger operacional | Consultar movimientos, estados, anulaciones, sustituciones y trazabilidad. | Filtrar por proyecto/período, abrir documento, ver historial y estados compensados. | `list_operational_ledger`, dashboard recent rows, acciones de documento. | Revisado estáticamente. | Pendiente validar filtros y enlaces con volumen de datos real. |
| Reportes | Emitir reportes financieros/costos, guardar definiciones, exportar de forma segura y reconciliar. | Seleccionar reporte/filtros, consultar, exportar, guardar y archivar definición. | `reports.service`, `safe_export`, `canonical_views`, página `nexora-reports`. | Revisado estáticamente; export guard cubierto por contratos. | Pendiente validar descarga real y límites de tamaño en bench. |
| Cierre semanal | Calcular, guardar/corregir/listar cierres y preservar trazabilidad. | Seleccionar período, calcular sin persistir, guardar cierre autorizado y consultar historial. | `close.canonical_weekly`, página `nexora-closing`, adaptador semanal. | Revisado estáticamente. | Browser smoke actual calcula pero no persiste; falta validación de guardado/corrección con permisos. |
| Contratos | Gestionar contratos, hitos, anticipos, pagos, retenciones y saldo. | Crear contrato, relacionar proveedor/proyecto, controlar avance/pagos y reportar saldo. | Servicios `contracts`, página `nexora_contracts`, consultas dashboard. | Revisado estáticamente. | No validado con ciclo real de contrato, adendas y retenciones. |
| Proveedores y entidades | Administrar proveedores, clientes/beneficiarios, contactos y datos sensibles. | Crear/editar entidad, buscar, vincular a compras/contratos/pagos. | `directory`, páginas entidades/proveedores, helpers de contraseñas. | Revisado estáticamente. | Pendiente validar exposición de campos sensibles en UI y permisos. |
| Evidencias y archivos | Registrar adjuntos privados y metadatos con relación a operaciones/progreso. | Adjuntar comprobante, validar privacidad/tipo, revisar y listar por proyecto. | `financial.evidence`, página `nexora_evidence`, políticas de evidencia. | Revisado estáticamente; escaneo de secretos OK. | No validado upload real ni permisos de archivo privado. |
| Compras y solicitudes | Gestionar solicitudes, cotizaciones, órdenes y recepción. | Solicitar compra, cotizar, aprobar, emitir orden, recibir bienes y afectar inventario. | `purchases`, páginas purchase requests/quotations, inventario. | Revisado estáticamente. | Flujo completo compra→recepción→inventario no validado en UI. |
| Inventario | Controlar bodegas, materiales, entradas, salidas, transferencias y stock negativo. | Crear bodega/material, registrar movimiento, validar stock y consultar saldos. | `inventory.service/core`, contratos de stock, movimientos. | Revisado estáticamente; compile y contratos dirigidos OK. | No validado con concurrencia real/base de datos; pruebas de concurrencia requieren bench. |
| Presupuesto y compromisos | Presupuestar, comprometer fondos, ejecutar/liberar compromisos y comparar desviaciones. | Crear presupuesto/partidas, comprometer, ejecutar o liberar, reflejar en dashboard/reportes. | `budget`, `financial.commitments`, reportes y dashboard. | Revisado estáticamente. | Pendiente validar reglas con presupuesto histórico y saldos reales. |
| Avance, calidad e incidencias | Registrar avance físico, evidencias, calidad e incidencias por fase/proyecto. | Crear fase, actualizar avance, adjuntar evidencia, controlar regresiones. | `progress`, `erpnext.construcontrol.quality`, dashboard de avance. | Revisado estáticamente. | No validado en UI móvil ni con permisos manager/operator. |
| Notificaciones | Gestionar preferencias y preparar notificaciones/alertas sin exponer secretos. | Configurar preferencia, preparar mensaje autorizado, registrar historial. | `notifications`, reportes/notificaciones ConstruControl. | Revisado estáticamente. | No validado envío externo real; debe permanecer manual/seguro si no hay credenciales. |
| Integraciones | Registro único para activar/probar/archivar integraciones y proteger credenciales. | Listar integraciones, crear personalizada, probar, activar/desactivar, archivar/eliminar. | `integrations`, página de integraciones heredada, gestión de secretos. | Revisado estáticamente. | Pendiente validar UI y que secretos no se devuelvan en respuestas. |
| Usuarios, roles y permisos | Administrar acceso NEXORA, perfiles, roles y alcance por proyecto. | Crear/editar/suspender usuario, asignar rol/proyectos, proteger administradores. | `permissions`, directorio, usuarios ConstruControl, fixtures de roles. | Revisado estáticamente; validadores de app OK. | Falta prueba negativa real por sesión/rol en bench. |
| Búsqueda global | Buscar documentos NEXORA de forma segura y abrir detalle. | Ingresar término, ver resultados filtrados por permiso, abrir detalle. | `secure_universal_search`, página `nexora-search`, browser validators. | Revisado estáticamente. | Pendiente validar relevancia, teclado y permisos con datos reales. |
| PWA y responsive | Instalar y usar NEXORA en escritorio/iPhone con layout seguro. | Abrir app, instalar, navegar offline/online, respetar safe area y refresh. | Manifest, assets, CSS, validadores browser. | Revisado estáticamente. | No validado con dispositivo/navegador real en este entorno. |
| Migración segura | Importar/validar datos históricos con respaldo, simulación, conciliación y rollback. | Cargar respaldo, dry-run, validar, importar, conciliar y auditar. | `migration`, scripts Supabase, consola heredada. | Revisado estáticamente. | No se ejecutó importación real; requiere respaldo y autorización. |
| Auditoría y trazabilidad | Registrar eventos sin secretos, proteger logs y permitir revisión. | Generar evento por cambio, consultar historial, impedir edición/borrado. | `audit`, eventos de negocio, tests standalone. | Revisado estáticamente; standalone parcialmente ejecutado. | 1 prueba de infraestructura bloqueada por PyYAML; auditoría real necesita bench. |
| Monitoreo/validación operativa | Exponer progreso, defectos, estado Git/CI y gates locales. | Levantar monitor, leer JSON de progreso, mostrar bloqueos y checks. | `tools/nexora_monitor`, scripts de validación. | Revisado estáticamente. | No se levantó servidor interactivo; se validó sintaxis de scripts principales. |

### Conclusión del recorrido por módulos

Todos los módulos funcionales identificados fueron revisados individualmente a nivel de código, contratos, rutas, acciones declaradas y validadores disponibles. Ningún módulo dependiente de UI/base de datos fue marcado como validado funcionalmente porque el entorno no incluye un sitio Frappe/bench con datos y permisos reales. La única anomalía funcional-seguridad corregible sin infraestructura fue el render inseguro del período activo en operaciones guiadas; el resto queda documentado como validación pendiente o riesgo operacional.
