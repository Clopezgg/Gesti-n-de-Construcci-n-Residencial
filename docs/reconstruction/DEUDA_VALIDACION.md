# Deuda de validación controlada

Ningún registro de esta tabla equivale a aprobación. La deuda se conserva hasta que la puerta indicada produzca evidencia completa y revisada.

| Identificador | Módulo | SHA | Prueba o workflow | Severidad | Evidencia disponible | Razón para diferir | Puerta | Estado |
|---|---|---|---|---|---|---|---|---|
| VAL-A-001 | FI01/FI02/PR01/CO01 | `17d7323dd171a08238137c02c37bcbd3683cea6e` y posteriores | MariaDB 4/4, runtime financiero, migraciones y persistencia | Alta | Pruebas dirigidas y commits funcionales publicados | La certificación se ejecuta una sola vez después de completar Bloques 10–12 | A | Pendiente |
| VAL-B08-001 | MM01/MM02/MIGO | `40409c46da58028c74abe92a47cdfe56373dfb77` | CRUD MariaDB, reinicio, recepción, transferencia y conciliación FI02 | Alta | 7/7 pruebas dirigidas, Ruff y compilación | Se agrupa con QC01, CL01, BI01 y AU01 | B | Pendiente |
| VAL-B09-001 | QC01/CL01 | `4726ca09d869eb6b201c227478f9b6c0a459c361` | CRUD MariaDB, archivo privado, permisos de descarga, reapertura y repetición | Alta | 9/9 pruebas dirigidas y de migración | Requiere entorno Frappe, File privado y transacciones reales | B | Pendiente |
| VAL-B10-001 | BI01/AU01 | SHA del commit funcional de Bloque 10 | Reconciliación real de dashboard/reportes, exportación privada, auditoría inmutable y permisos | Alta | 12/12 pruebas dirigidas, compilación, Ruff y JavaScript | La validación MariaDB/runtime se agrupa en una sola Puerta B | B | Pendiente |
| VAL-C-001 | PWA/infraestructura | SHA del commit funcional de Bloque 11 y Bloque 12 pendiente | iPhone real, PWA instalada, servicios, reinicio, redeploy, backup y restore | Alta | 9/9 pruebas dirigidas PWA y evidencia base histórica de contenedor/runtime | Los dispositivos y servicios reales se validan una sola vez después de cerrar Bloque 12 | C | Pendiente |
