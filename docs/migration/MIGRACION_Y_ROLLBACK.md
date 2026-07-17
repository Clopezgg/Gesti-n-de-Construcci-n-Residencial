# Migración, conciliación y rollback

Use el procedimiento literal de [`MANUAL_PASO_A_PASO.md`](../../MANUAL_PASO_A_PASO.md). Este documento resume el mecanismo técnico vigente para Oracle Cloud + Coolify.

## Paquete verificable

La exportación local contiene:

- `construcontrol-supabase-export.json`;
- `storage-manifest.json`;
- `preflight-report.json`;
- `evidence/...`.

`scripts/create_migration_bundle.py` valida el JSON y crea un ZIP con `bundle-manifest.json`, tamaño y SHA-256 de cada archivo.

## Transferencia al entorno Coolify

El mecanismo recomendado conserva el paquete en el bucket privado `construcontrol-migration`. Desde la terminal del servicio `backend` en Coolify, el importador descarga el ZIP a un directorio temporal:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/paquete.zip","dry_run":true,"source_kind":"Supabase Export"}'
```

El importador:

1. descarga el ZIP a un directorio temporal;
2. limita tamaño y cantidad de miembros;
3. rechaza rutas absolutas, `..`, miembros cifrados y enlaces simbólicos;
4. verifica el manifiesto y SHA-256;
5. exige exactamente un archivo de exportación;
6. ejecuta el importador existente;
7. elimina el staging al finalizar.

## Respaldo obligatorio

Antes de la importación real ejecute desde la terminal del servicio `backend`:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

El respaldo se archiva en el volumen persistente `/backups` y genera `backup-manifest.json`. Si existen credenciales de Supabase de destino, también se carga una copia remota y se devuelve `manifest_object_key`.

Para una importación con respaldo local, utilice como `backup_reference` la ruta del manifiesto mostrada por `archive_backup_set.py`. Para una copia remota, utilice el `manifest_object_key`.

## Ensayo e importación real

Ensayo:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/paquete.zip","dry_run":true,"source_kind":"Supabase Export"}'
```

Importación real:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/paquete.zip","dry_run":false,"source_kind":"Supabase Export","backup_reference":"RUTA_O_CLAVE_DEL_MANIFIESTO"}'
```

## Conciliación

Compruebe:

- `input == preserved`;
- `mapped + preserved_only == preserved`, salvo fallos explícitos;
- archivos verificados = adjuntados + rechazados justificados;
- `mapping_failures == 0`;
- saldos, relaciones y permisos coinciden con el origen.

## Rollback lógico

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.importer.rollback \
  --kwargs '{"migration_run":"CC-MIG-2026-00001"}'
```

El rollback lógico elimina únicamente destinos en borrador creados por la corrida y conserva eventos append-only.

## Restauración total

La restauración autoritativa utiliza los archivos enumerados por `backup-manifest.json`:

```bash
python3 apps/erpnext/scripts/verify_backup_manifest.py /backups/RUTA/backup-manifest.json
bench --site "$SITE_NAME" restore /backups/RUTA/database.sql.gz \
  --with-public-files /backups/RUTA/files.tar \
  --with-private-files /backups/RUTA/private-files.tar
bench --site "$SITE_NAME" migrate
```

Los nombres reales pueden incluir fechas y extensiones diferentes. Use exactamente los archivos listados en el manifiesto. Pruebe primero la restauración en un entorno aislado y no elimine volúmenes de producción.
