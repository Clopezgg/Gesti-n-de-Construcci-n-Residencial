# Deuda de validación controlada

Ningún registro de esta tabla equivale a aprobación. La deuda se conserva hasta que la puerta indicada produzca evidencia completa y revisada.

| Identificador | Módulo | SHA | Prueba o workflow | Severidad | Evidencia disponible | Razón para diferir | Puerta | Estado |
|---|---|---|---|---|---|---|---|---|
| VAL-A-001 | FI01/FI02/PR01/CO01 | `17d7323dd171a08238137c02c37bcbd3683cea6e` y posteriores | MariaDB 4/4, runtime financiero, migraciones y persistencia | Alta | Pruebas dirigidas y commits funcionales publicados | La orden exige una sola certificación conjunta y prohíbe detener implementación por validación pesada | A | Pendiente |
| VAL-B08-001 | MM01/MM02/MIGO | `40409c46da58028c74abe92a47cdfe56373dfb77` | CRUD MariaDB, reinicio, recepción, transferencia y conciliación FI02 | Alta | 7/7 pruebas dirigidas, Ruff y compilación | Se agrupa con QC01, CL01, BI01 y AU01 | B | Pendiente |
| VAL-B09-001 | QC01/CL01 | `5dd5379ea04578e4748dfe374562f688908f6ffc` | CRUD MariaDB, archivo privado, permisos de descarga, reapertura y repetición | Alta | 6/6 pruebas dirigidas, Ruff y compilación | Requiere entorno Frappe, File privado y transacciones reales del Sprint B | B | Pendiente |
| VAL-C-001 | PWA/infraestructura | Pendiente | iPhone, PWA, servicios, reinicio, redeploy, backup y restore | Alta | Evidencia base histórica de contenedor/runtime | Los Bloques 11 y 12 aún no están implementados | C | Pendiente |
