# Supabase: origen, migración y copia remota opcional

La guía operativa autoritativa es [`MANUAL_PASO_A_PASO.md`](../../MANUAL_PASO_A_PASO.md). Esta nota documenta las decisiones técnicas vigentes para Oracle Cloud + Coolify.

## Supabase ya no es obligatorio para almacenar archivos nuevos

El despliegue gratuito usa por defecto:

```text
SUPABASE_STORAGE_MODE=disabled
```

Los adjuntos de ERPNext se conservan en el volumen persistente `sites` de Docker, alojado en el volumen de Oracle Cloud. Esto permite desplegar y utilizar ConstruControl sin crear un segundo proyecto Supabase.

## Uso del Supabase de origen

El proyecto del sistema anterior se utiliza únicamente para:

- ejecutar consultas de diagnóstico de solo lectura;
- exportar `construction_projects`;
- descargar las evidencias referenciadas;
- conciliar conteos después de la migración.

No ejecute `04_storage_bucket_and_rls.sql` en el origen.

## Supabase de destino opcional

Puede utilizar un proyecto separado para:

- `construcontrol-migration`: transferencia privada del ZIP verificable;
- `construcontrol-backups`: copia remota adicional de los respaldos;
- `construction-evidence`: almacenamiento remoto de archivos solo cuando se habilite expresamente.

El SQL `migration/supabase/04_storage_bucket_and_rls.sql` se ejecuta únicamente en ese proyecto opcional.

## Modelo de autorización

El navegador no recibe una clave Supabase. Use `SUPABASE_SERVER_KEY` con una clave `sb_secret_...` solo en Coolify o en una sesión local privada. El adaptador conserva compatibilidad temporal con una clave heredada `service_role`.

Los buckets permanecen `public=false` y no se crean políticas para `anon` ni `authenticated`. ERPNext continúa siendo la frontera de permisos.

## Transferencias

`scripts/supabase_storage_transfer.py` realiza subida, descarga y eliminación privada mediante streaming. `scripts/create_migration_bundle.py` crea un manifiesto SHA-256 antes de transferir datos.

## Verificaciones mínimas

1. Ninguna clave está versionada en GitHub.
2. El origen no fue modificado durante la exportación.
3. Los objetos descargados coinciden con `storage-manifest.json`.
4. El ZIP de migración coincide con `bundle-manifest.json`.
5. Los buckets opcionales son privados.
6. La copia local de `/backups` se valida aunque la copia remota opcional falle.
