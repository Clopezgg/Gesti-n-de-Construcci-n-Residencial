# Migración, conciliación y rollback

## 1. Congelamiento y respaldo del origen

1. Defina una ventana sin cambios en el sistema antiguo.
2. Tome un backup de la base de datos Supabase desde el Dashboard/CLI y conserve su hash y fecha.
3. Ejecute, en orden, los scripts de solo lectura:

   - `migration/supabase/01_preflight.sql`
   - `migration/supabase/02_relational_validation.sql`

4. Guarde sus resultados junto al respaldo. Cualquier consulta de integridad que devuelva filas debe resolverse o justificarse antes de importar.

## 2. Exportación masiva

Configure las variables únicamente en la sesión/gestor de secretos:

```bash
export SUPABASE_URL='https://PROJECT.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='valor-server-only'
export SUPABASE_PROJECT_ID='proyecto-opcional'
python scripts/export_supabase_snapshot.py migration-output/source-export
```

El script genera:

- `construcontrol-supabase-export.json` con todos los snapshots solicitados.
- `evidence/<bucket>/...` con objetos referenciados.
- `storage-manifest.json` con ruta, bytes, SHA-256 y estado de cada objeto.

El proceso retorna código 3 si falla cualquier archivo y código 1 para fallos generales. No continúe con un resultado distinto de 0.

Para un respaldo nativo/localStorage, coloque el JSON y un manifiesto equivalente en el mismo directorio. No edite manualmente IDs ni fechas.

## 3. Prevalidación fuera de Frappe

```bash
python scripts/validate_construcontrol_backup.py \
  migration-output/source-export/construcontrol-supabase-export.json \
  --report migration-output/source-export/preflight-report.json
```

El código 2 indica duplicados o relaciones huérfanas. El informe incluye conteos por entidad, IDs faltantes, evidencia embebida/remota y campos sensibles que serán saneados.

## 4. Preparación del destino

1. Instale/migre este fork en un sitio de ensayo clonado de producción.
2. Complete la compañía, proyecto, almacén y centro de costo en **ConstruControl Settings**.
3. Mantenga `Preserve Only` para la primera carga. Habilite usuarios o documentos estándar sólo después de aprobar el mapa.
4. Tome respaldo y registre el nombre exacto:

   ```bash
   bench --site SITIO backup --with-files
   sha256sum sites/SITIO/private/backups/*
   ```

5. Copie el directorio de exportación completo a una ruta privada legible por el backend; no suba estos datos a GitHub.

## 5. Dry run obligatorio

```bash
bench --site SITIO execute \
  erpnext.construcontrol.migration.importer.run_import \
  --kwargs '{"source_path":"/ruta/privada/construcontrol-supabase-export.json","dry_run":true,"source_kind":"Supabase Export"}'
```

Revise el documento **ConstruControl Migration Run**:

- `source_sha256` coincide con el archivo.
- `input_counts_json` coincide con SQL y preflight externo.
- `validation_report_json.storage_export.errors` está vacío.
- No existen duplicados ni referencias huérfanas sin justificación.
- `redacted_sensitive_fields` se entiende: son credenciales deliberadamente excluidas.

## 6. Importación real

```bash
bench --site SITIO execute \
  erpnext.construcontrol.migration.importer.run_import \
  --kwargs '{"source_path":"/ruta/privada/construcontrol-supabase-export.json","dry_run":false,"source_kind":"Supabase Export","backup_reference":"20260717_...-SITIO"}'
```

La ejecución real se niega sin `backup_reference` y también si el manifiesto de Storage falta, contiene fallos o no coincide en tamaño/SHA-256.

Secuencia interna:

1. Normaliza export nativo, localStorage o REST Supabase.
2. Prevalida colecciones, IDs, duplicados, referencias y archivos.
3. Preserva primero el snapshot completo saneado.
4. Preserva cada registro y versión con clave/hash determinista.
5. Mapea a documentos estándar/custom según configuración.
6. Adjunta evidencia al documento destino o, si no existe, a su Legacy Record.
7. Registra conteos, fallos y enlaces fuente-destino.

## 7. Conciliación posterior

Ejecute `migration/supabase/03_post_export_reconciliation.sql` en el origen y abra **ConstruControl Migration Reconciliation** en ERPNext.

Verifique por entidad:

- `input == preserved`;
- `mapped + preserved_only == preserved`, descontando únicamente fallos explícitos;
- archivos exportados verificados == archivos adjuntados + archivos rechazados;
- `mapping_failures == 0`;
- no hay registros destino huérfanos;
- relaciones Project/Task/Contract/Fund se resuelven;
- usuarios, roles y permisos se prueban con cuentas no administrativas.

Toda diferencia debe anexarse al Migration Run con ID, causa y decisión. No cierre la migración si el estado es `Completed with Warnings` sin resolver o aceptar formalmente cada advertencia.

## Rollback lógico del importador

```bash
bench --site SITIO execute \
  erpnext.construcontrol.migration.importer.rollback \
  --kwargs '{"migration_run":"CC-MIG-2026-00001"}'
```

El rollback es idempotente y:

- elimina sólo destinos en borrador creados por esa ejecución y sin enlaces de otras ejecuciones;
- elimina los Legacy Record de esa ejecución;
- retiene destinos existentes/reutilizados, documentos presentados y eventos append-only;
- registra lo eliminado, retenido y cualquier error.

No puede reconstruir automáticamente el estado anterior de un documento preexistente actualizado. Para una reversión total y verificable use el respaldo Bench:

```bash
bench --site SITIO restore /ruta/database.sql.gz \
  --with-public-files /ruta/files.tar \
  --with-private-files /ruta/private-files.tar
bench --site SITIO migrate
```

Antes de restaurar producción, pruebe el backup en un sitio aislado y detenga web, workers y scheduler durante la ventana.
