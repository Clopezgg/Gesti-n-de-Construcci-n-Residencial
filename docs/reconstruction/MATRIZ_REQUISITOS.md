# Matriz de requisitos de reconstrucción de ConstruControl

> Documento vivo. Ningún requisito se considera completado sin implementación, commit publicado y prueba de comportamiento.

| ID | Requisito | Fuente recuperada | Módulo | Estado actual | Problema | Corrección requerida | Prueba de aceptación | Commit de implementación | Resultado final |
|---|---|---|---|---|---|---|---|---|---|
| GOV-01 | Trabajar exclusivamente mediante una rama y un único PR borrador contra `main` | Orden definitiva | Gobierno Git | Implementado y vigilado | Workflows podían escribir en `main` o borrar ramas | Convertirlos en validadores de solo lectura y bloquear regresiones | Escaneo de workflows, PR DRAFT y refs verificadas | `33e79a50` | Aprobado |
| AUD-01 | Verificar acceso, permisos, rama predeterminada y SHA base | Orden definitiva, GitHub | Auditoría | Completado | La base avanzó concurrentemente | Registrar SHA y reconciliar sin reescribir historial | Merge de dos padres, 0 commits detrás después de reconciliar | `22b65cbf` | Aprobado |
| AUD-02 | Auditar todas las ramas y recuperar solo cambios válidos | Orden definitiva, historial | Ramas | Completado | Rama secundaria contiene patches, no implementación lista | Revisar propuestas individualmente, sin merge ciego | Inventario y comparación documentados | `9bdb1cab` | Aprobado; ninguna rama eliminada |
| AUD-03 | Auditar PR, tags, Actions, estructura y scripts | Orden definitiva | Auditoría | Completado | Evidencia histórica fragmentada | Consolidar auditoría y corregir CI | Auditoría B01, validadores, linters, runtime y contenedor | `33e79a50`, `22b65cbf`, `4071454c` | Aprobado remotamente |
| ARC-01 | Establecer una única arquitectura oficial | Conversaciones, código e historial | Arquitectura | Completado para páginas y rutas | Cuatro escritores creaban registros `Page` paralelos | Un registro canónico con controladores físicos únicos | 8 páginas únicas, sin scripts embebidos, prueba 4/4 y runtime | `e96213b6`, `4071454c` | Aprobado remotamente |
| UI-01 | Consolidar páginas, rutas, menús, workspaces e integraciones | Problemas de manual y navegación | UI / Desk | Bloque 2 completado | Scripts DB desfasados y rutas susceptibles a duplicación | Propietario único y contrato exacto de rutas/roles | 111/111 pruebas, JS válido, runtime y validador de finalización | `e96213b6`, `4071454c` | Aprobado remotamente |
| DB-01 | Eliminar DocFields/Custom Fields duplicados | Orden definitiva | Esquema | Bloque 3 completado | Colisiones estándar/custom/migración | Reutilizar campos y fallar ante metadata duplicada | Auditoría runtime de 37 DocTypes y 125 Custom Fields | `4df16b97` | Cero colisiones y cero duplicados; aprobado remotamente |
| DB-02 | Hacer instalación y migraciones idempotentes y compatibles | Orden definitiva | Migraciones | Bloque 3 completado | Riesgo de metadata duplicada y contrato desalineado | Verificar huella, campos y migración repetida | Dos `bench migrate`, contrato SHA, CRUD, reinicio y backup | `4df16b97`, `3bc75624` | Aprobado remotamente |
| SEC-01 | Roles, permisos, URL y autorización backend | US01 | Seguridad | Bloque 4 completado | UI no sustituye autorización y las cuentas ADMIN podían quedar expuestas a transiciones inválidas | Centralizar límites por proyecto, rol y ciclo de vida en backend | Matriz positiva/negativa para System Manager, Manager, Operator, Auditor, Viewer y usuario sin permisos | `08d1e043`, `f1d574fa`, `e0171728`, `786663b2`, `443afc43`, `0b968247` | 119/119; static, linters, Semgrep, contenedor y runtime aprobados |
| FI01-01 | Remesas, aportes, depósitos, transferencias, monedas, deducciones y saldos | FI01 | Fondos | Bloque 5 iniciado | Riesgo de fórmulas divergentes | Regla financiera canónica | Casos multimoneda y conciliación | Pendiente | Pendiente |
| FI02-01 | Gastos, facturas, proveedores, aprobaciones, pagos y CxP | FI02 | Gastos | Pendiente de bloque específico | Estados pueden contaminar totales | Flujo profesional y sincronización | Aprobado/rechazado/parcial/completo | Pendiente | Pendiente |
| PRO-01 | Proyectos, fases, presupuestos, contratos y compromisos | PR01/CO01 | Proyectos | Pendiente | Costos y saldos inconsistentes | Consolidar reglas | Pruebas de compromiso, costo y saldo | Pendiente | Pendiente |
| INV-01 | Materiales, solicitudes, compras y movimientos | MM01/MM02/MIGO | Inventario | Pendiente | Stock puede divergir | Servicio canónico | Entradas, consumos, ajustes y bloqueo negativo | Pendiente | Pendiente |
| QC-01 | Avance, calidad, evidencias, alertas y cierre | QC01/CL01 | Ejecución | Pendiente | Cierres pueden usar estados incorrectos | Reconciliar reglas físicas/financieras | Cierre repetible y alertas | Pendiente | Pendiente |
| BI-01 | Dashboard, indicadores, filtros y reportes | BI01 | Analítica | Pendiente | Totales pueden diferir | Reutilizar servicios canónicos | Dashboard contra transacciones | Pendiente | Pendiente |
| AU-01 | Identidad, acción y valores anterior/posterior | AU01 | Auditoría | Ciclo de usuarios completado; auditoría global pendiente | Trazabilidad incompleta fuera del ciclo US01 | Extender el mismo contrato a los módulos posteriores | CRUD con actor, rol, acción y diff | `08d1e043`, `e0171728` | US01 aprobado; resto se valida por bloque |
| MOB-01 | Escritorio, iPhone, móvil y PWA | Orden definitiva | Responsive/PWA | Pendiente | Navegación y recarga pueden fallar | Validar shell y ciclo PWA | E2E escritorio/iPhone | Pendiente | Pendiente |
| INF-01 | Docker, DB, Redis, workers, scheduler, WebSocket y persistencia | Orden definitiva | Infraestructura | Evidencia base aprobada; Bloque 12 pendiente | Falta cierre integral de servicios | Consolidar servicios y healthchecks | Compose, reinicio, persistencia y backup | `beb4b48c`, `4071454c`, `3bc75624` | Runtime base aprobado |
| BAK-01 | Respaldo y restauración en ensayo | Orden definitiva | Operación | Backup aprobado; restauración pendiente | Declaración no demuestra restauración | Ejecutar restore seguro | Datos antes/después | `3bc75624` | Backup real aprobado; restore pendiente |
| DOC-01 | Manual coincidente con código | Manual confuso | Documentación | Pendiente | Instrucciones contradictorias | Guía única con comandos completos | Instalación reproducible | Pendiente | Pendiente |
| REG-01 | Regresión integral no autorreferencial | Orden definitiva | Calidad | En ejecución | Checks históricos podían ser superficiales | Pruebas de comportamiento y artifacts | 119 standalone; runtime, migración, CRUD, permisos, persistencia y backup | `33e79a50`, `e96213b6`, `4df16b97`, `3bc75624`, `f1d574fa`, `e0171728` | Bloques 1-4 aprobados; faltan bloques 5-12 |

## Fuentes recuperadas

1. Orden definitiva de corrección controlada mediante Pull Request.
2. Contexto persistente de «Manual de problema confuso» y «Análisis problema manual».
3. Historial, código, Pull Requests, workflows, artifacts y pruebas de GitHub.

## Regla de actualización

Cada fila se actualiza únicamente con SHA publicado y resultado comprobado de su prueba de aceptación.
