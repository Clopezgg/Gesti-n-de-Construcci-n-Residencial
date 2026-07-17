# Cambios realizados

## Núcleo consolidado

- Se conservó ERPNext 15.117.0 como arquitectura base.
- Se registró el módulo Frappe `ConstruControl` sin reemplazar DocTypes estándar.
- Se añadió workspace, conciliación, migración, auditoría y cuatro roles aislados.

## Modelo funcional

Se incorporaron DocTypes para configuración, corridas de migración, preservación histórica, fondos, gastos, avance, cierres, cambios, aprobaciones y auditoría.

Los registros conservan IDs, fechas, estados, evidencia y enlaces con Project, Task, Supplier, Contract o fuente de fondos cuando corresponde.

## Migración

- Normalizador para backup nativo, localStorage y respuesta REST Supabase.
- Inventario de colecciones y preservación del snapshot completo.
- Claves, versiones y hashes deterministas.
- Detección de duplicados y referencias huérfanas.
- Saneamiento de credenciales históricas.
- Paquete ZIP con manifiesto, tamaño y SHA-256.
- Importación remota temporal con controles de rutas, tamaño y cantidad.
- Dry run, conciliación y rollback lógico.

## Despliegue gratuito vigente

La topología pagada de Render fue retirada. Se agregó:

- `docker-compose.yml` compatible con Oracle Ampere ARM64 y Coolify;
- MariaDB 10.6 persistente;
- Redis cache y Redis queue persistente;
- configurator e init-site idempotentes;
- backend Gunicorn;
- WebSocket;
- workers corto y largo;
- scheduler;
- frontend Nginx;
- cinco volúmenes nombrados para base, cola, sitio, logs y backups;
- servicio automático de respaldo.

## Respaldos y recuperación

- `backup-now.sh` ejecuta `bench backup --with-files`.
- `archive_backup_set.py` conserva el conjunto en `/backups`.
- Cada conjunto incluye `backup-manifest.json`, bytes y SHA-256.
- `verify_backup_manifest.py` valida integridad antes de restaurar.
- Puede enviarse una copia remota opcional a Supabase, sin volverlo requisito del sistema nuevo.

## GitHub y CI

- Validación de Docker Compose, persistencia y servicios privados.
- Rechazo automático de `render.yaml`.
- Escaneo de secretos.
- Compilación Python y sintaxis Bash.
- Pruebas standalone de migración.
- Construcción de la imagen `linux/arm64` mediante QEMU/Buildx.

## Documentación

- Manual completo desde la creación de Oracle hasta el uso diario, migración, backup y recuperación.
- Referencia específica de Oracle Cloud + Coolify.
- Documentos de Supabase, GitHub, auditoría, riesgos, migración y rollback actualizados.

No se copiaron datos reales, contraseñas, ZIP, builds, `node_modules`, `.env`, backups ni claves privadas al repositorio.
