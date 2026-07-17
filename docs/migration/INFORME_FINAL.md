# Informe final de consolidación

## Resultado entregado

Se entrega un sistema basado en ERPNext 15.117.0 con el módulo nativo ConstruControl, scripts de migración, validación, rollback, respaldo y una arquitectura gratuita de producción mediante Oracle Cloud Always Free + Coolify + Docker Compose.

La topología pagada de Render fue eliminada del repositorio y ya no forma parte del procedimiento vigente.

## Qué se encontró

- Origen: SPA React/TypeScript/Vite con snapshot AppData en localStorage, sincronización Supabase, RLS y Storage.
- Destino: ERPNext/Frappe completo, con autenticación, roles, formularios, APIs, reportes, tareas y modelo ERP.
- Datos reales: ausentes de los ZIP auditados. Solo se detectaron fases de configuración estática y colecciones operativas vacías.

## Qué se conservó e integró

- ERPNext y sus DocTypes estándar son la base final.
- Se preservan snapshots y registros históricos por hash y versión.
- Se integran fases, fondos, gastos, avance, cierres, cambios, aprobaciones y auditoría.
- Las entidades restantes se preservan y se enlazan con módulos estándar cuando su contabilización y maestros hayan sido aprobados.
- Roles, permisos, trazabilidad, archivos y mecanismos de importación y conciliación están documentados.

## Qué se transformó o mejoró

- El almacenamiento local/JSON se normaliza, verifica y versiona.
- Los adjuntos se exportan con manifiesto, tamaño y SHA-256.
- Los ZIP se rechazan si contienen rutas inseguras, archivos no declarados, miembros cifrados o checksums incorrectos.
- Los archivos nuevos se guardan en un volumen persistente del servidor; Supabase es opcional.
- Los respaldos incluyen base, archivos, manifiesto y retención local.
- La infraestructura se concentra en una VM ARM64 con MariaDB, Redis, backend, WebSocket, workers, scheduler y Nginx.

## Validación incluida

- Validación estática de estructura, Python, JSON y secretos.
- Pruebas standalone del normalizador y migración.
- Sintaxis Bash de scripts Coolify.
- Validación del Docker Compose y cinco volúmenes persistentes.
- Construcción CI para `linux/arm64`.
- Verificación de paquetes de migración y respaldos mediante SHA-256.

## Límites y cierre

No se afirma que el despliegue real ya haya sido ejecutado en Oracle ni que datos históricos reales hayan sido migrados. Faltan la cuenta Oracle, la instancia, las credenciales y la exportación real del propietario.

La puesta en producción debe seguir exactamente `MANUAL_PASO_A_PASO.md` y solo aprobarse después de comprobar costo cero, health check, login, permisos, persistencia, archivos, workers, scheduler, WebSocket, backup y restauración.
