# Resultados de validación

Fecha: 2026-07-17. Este documento distingue pruebas ejecutadas de pruebas bloqueadas por infraestructura/datos.

## Ejecutado sobre los ZIP originales

| Validación | Resultado |
|---|---|
| Hash SHA-256 e inventario ZIP | OK; hashes registrados en auditoría. |
| Rutas ZIP inseguras | 0 encontradas. |
| JSON del destino original | 1,093/1,093 válidos. |
| Python destino original | 2,433/2,433 parsean con AST. |
| Suites de contenido del origen | 356 aserciones pasaron. |
| Auditoría del origen | Pasó. |
| Compilación TypeScript real del origen | FALLÓ por dependencia directa UI5 no declarada. |
| Búsqueda de secretos obvios | Sin credenciales reales detectadas; placeholders únicamente. |
| Dump/export operativo en ZIP | NO PRESENTE. |
| Archivos del bucket en ZIP | NO PRESENTES. |

## Ejecutado sobre el sistema consolidado

| Validación | Resultado esperado/registrado |
|---|---|
| `test_schema_standalone.py` | OK: 5/5 pruebas pasadas. |
| `compileall` de módulo/scripts | OK. Los bytecode generados se excluyen del entregable. |
| Parseo Python/JSON de extensión, scripts y despliegue | OK: 0 errores mediante `scripts/validate_repository.py`. |
| Detección de secretos obvios | OK: 0 hallazgos del validador. |
| `render.yaml` | OK: 0 errores contra el schema oficial de Render. |
| Sintaxis de scripts Render | OK con parser `sh -n`; la ejecución Bash real queda para imagen/Render. |
| Conteo/manifest SHA-256 del ZIP final | Pendiente de empaquetado. |

## Validaciones que requieren infraestructura externa

No pueden afirmarse como aprobadas sin un sitio Bench/Docker, Supabase real y Render:

1. Instalación completa de dependencias Frappe.
2. `bench migrate` contra MariaDB y sincronización de DocTypes.
3. Inicio real Nginx/Gunicorn/WebSocket/worker/scheduler.
4. Login, autenticación, roles y permisos con usuarios de prueba.
5. RLS con cuentas/proyectos distintos.
6. CRUD end-to-end de formularios.
7. Conteos de registros/relaciones/archivos reales.
8. Despliegue y health check real en Render.
9. Backup y restauración reales.

## Criterio de aceptación de la migración de datos

La migración real sólo se acepta cuando:

- existe export con hash y manifiesto;
- las consultas de integridad no retornan incidencias no justificadas;
- cada conteo de entrada coincide con `preserved.<entidad>`;
- fallos y adjuntos rechazados son cero;
- todas las diferencias tienen ID/causa/aprobación;
- se prueban usuarios/roles/RLS/CRUD;
- se restaura exitosamente el backup en un entorno aislado.

Hasta recibir la exportación real, el resultado correcto de “registros migrados” es **0 registros operativos verificables**, no una cifra estimada.
