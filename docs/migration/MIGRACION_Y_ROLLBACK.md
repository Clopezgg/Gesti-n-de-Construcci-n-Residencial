# Migración, conciliación y rollback

Use el procedimiento literal de [`MANUAL_PASO_A_PASO.md`](../../MANUAL_PASO_A_PASO.md). Este documento resume el mecanismo técnico actualizado.

## Paquete verificable

La exportación local contiene:

- `construcontrol-supabase-export.json`;
- `storage-manifest.json`;
- `preflight-report.json`;
- `evidence/...`.

`scripts/create_migration_bundle.py` valida el JSON y crea un ZIP con `bundle-manifest.json`, tamaño y SHA-256 de cada archivo.

## Transferencia a Render

El paquete se sube al bucket privado `construcontrol-migration`. Ya no se requiere copiar manualmente una carpeta a una ruta desconocida del contenedor.

El comando de Render utiliza:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/paquete.zip","dry_run":true,"source_kind":"Supabase Export"}'
```

El importador:

1. descarga el ZIP a un directorio temporal;
2. limita tamaño y cantidad de miembros;
3. rechaza rutas absolutas, `..` y enlaces simbólicos;
4. verifica el manifiesto y SHA-256;
5. exige exactamente un archivo de exportación;
6. ejecuta el importador existente;
7. elimina el staging al finalizar.

## Respaldo obligatorio

Antes de la importación real ejecute:

```bash
bash apps/erpnext/deploy/render/run-backup.sh
```

El resultado incluye `manifest_object_key`. Ese valor se utiliza como `backup_reference`. El respaldo no se considera válido si el manifiesto remoto no se pudo subir.

## Conciliación

Compruebe:

- `input == preserved`;
- `mapped + preserved_only == preserved`, salvo fallos explícitos;
- archivos verificados = adjuntados + rechazados justificados;
- `mapping_failures == 0`;
- saldos, relaciones y permisos coinciden con el origen.

## Rollback

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.importer.rollback \
  --kwargs '{"migration_run":"CC-MIG-2026-00001"}'
```

El rollback lógico elimina únicamente destinos en borrador creados por la corrida y conserva eventos append-only. Para una reversión total, restaure en un entorno aislado los archivos enumerados por `backup-manifest.json` y valide el resultado antes de tocar producción.
