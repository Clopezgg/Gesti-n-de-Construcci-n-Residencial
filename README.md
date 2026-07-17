# ERPNext ConstruControl consolidado

Sistema consolidado sobre **ERPNext 15.117.0 / Frappe 15**. ERPNext conserva la arquitectura transaccional y el módulo `ConstruControl` incorpora la información, reglas, auditoría y migración recuperables del sistema React/Supabase de origen.

## Empiece aquí

La guía principal es **[MANUAL_PASO_A_PASO.md](MANUAL_PASO_A_PASO.md)**. Explica desde cero:

- creación de una máquina Oracle Cloud Always Free;
- instalación gratuita y autogestionada de Coolify;
- conexión del repositorio privado de GitHub en la rama `main`;
- despliegue mediante `docker-compose.yml`;
- variables, contraseñas, dominio gratuito, HTTPS y primer acceso;
- configuración inicial y uso de ERPNext/ConstruControl;
- migración desde Supabase, respaldos, restauración y mantenimiento.

## Arquitectura gratuita

La topología pagada de Render fue retirada. El despliegue vigente utiliza una sola VM ARM64 de Oracle Cloud dentro de los límites Always Free y Coolify autogestionado:

- MariaDB 10.6 con volumen persistente;
- Redis separado para caché y colas;
- inicializador idempotente del sitio;
- backend Gunicorn;
- WebSocket;
- workers corto y largo;
- scheduler;
- frontend Nginx;
- respaldo local automático con manifiesto SHA-256;
- copia remota opcional a Supabase privado.

El archivo **`docker-compose.yml`** es la única fuente de verdad del despliegue. Coolify debe usar:

```text
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
```

## Persistencia

Los datos no dependen del filesystem efímero de un contenedor. Se conservan en volúmenes Docker:

- `mariadb-data`: base transaccional;
- `redis-queue-data`: cola persistente;
- `sites`: configuración, adjuntos y archivos del sitio;
- `logs`: registros;
- `backups`: copias automáticas locales verificables.

No ejecute `docker compose down -v` ni elimine volúmenes desde Coolify: ambos actos destruyen datos.

## Supabase es opcional para el sistema nuevo

Por defecto:

```text
SUPABASE_STORAGE_MODE=disabled
```

Los archivos de ERPNext se guardan en el volumen persistente `sites`. Supabase puede seguir utilizándose para:

- leer y exportar el sistema anterior;
- alojar temporalmente un paquete privado de migración;
- conservar una copia remota adicional de respaldos dentro de los límites del plan disponible.

Nunca coloque claves reales en `.env`, GitHub, JavaScript, variables `VITE_`, capturas o documentos públicos.

## Validación local

```bash
python -m pip install PyYAML==6.0.2
python scripts/validate_repository.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
python -m py_compile \
  erpnext/construcontrol/migration/importer.py \
  erpnext/construcontrol/migration/remote_importer.py \
  erpnext/construcontrol/storage/supabase.py \
  scripts/export_supabase_snapshot.py \
  scripts/create_migration_bundle.py \
  scripts/archive_backup_set.py \
  scripts/verify_backup_manifest.py \
  scripts/supabase_storage_transfer.py \
  scripts/upload_backup_set.py
bash -n deploy/coolify/*.sh
```

Resultado esperado:

```text
Repository validation: 0 error(s)
```

## Operación rápida

Desde la terminal del servicio `backend` en Coolify:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

Respaldo manual:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Los conjuntos persistentes se guardan en `/backups` con un `backup-manifest.json` y SHA-256 por archivo.

## Seguridad y rollback

- MariaDB y Redis no se publican a Internet.
- Solo el servicio `frontend` debe recibir un dominio en Coolify, dirigido al puerto interno `8080`.
- Los secretos se administran en Coolify, no en el repositorio.
- Los paquetes de migración se validan por ruta, cantidad, tamaño y SHA-256 antes de importarse.
- El rollback lógico elimina únicamente borradores creados por una corrida.
- La reversión autoritativa utiliza un respaldo Bench verificado y, como protección adicional, copias de volumen de Oracle Cloud.

## Documentación

- [Manual operativo completo](MANUAL_PASO_A_PASO.md)
- [Oracle Cloud y Coolify](docs/deployment/ORACLE_COOLIFY.md)
- [Mapa de correspondencia](docs/migration/MAPA_CORRESPONDENCIA.md)
- [Supabase](docs/migration/SUPABASE.md)
- [Migración y rollback](docs/migration/MIGRACION_Y_ROLLBACK.md)
- [Auditoría integral](docs/migration/AUDITORIA_INTEGRAL.md)
- [Validación de resultados](docs/migration/VALIDACION_RESULTADOS.md)

ERPNext conserva su licencia GNU GPL v3 y atribuciones originales en `license.txt` y `attributions.md`.
