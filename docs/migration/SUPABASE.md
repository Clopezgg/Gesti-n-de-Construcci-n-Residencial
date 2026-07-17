# Supabase: destino, Storage y seguridad

La guía operativa autoritativa es [`MANUAL_PASO_A_PASO.md`](../../MANUAL_PASO_A_PASO.md). Esta nota documenta las decisiones técnicas.

## Separación obligatoria

- El proyecto **de origen** se utiliza únicamente para exportación.
- El proyecto **de destino** almacena archivos de ERPNext, paquetes de migración y respaldos.
- `migration/supabase/04_storage_bucket_and_rls.sql` se ejecuta solo en el destino.

## Buckets privados

- `construction-evidence`: JPEG, PNG, WebP y PDF, máximo 12 MiB por archivo.
- `construcontrol-migration`: paquetes ZIP verificables.
- `construcontrol-backups`: respaldos Bench y manifiestos JSON.

Los tres buckets permanecen `public=false`.

## Modelo de autorización

El navegador no consulta Supabase y no recibe una clave. ERPNext valida el permiso del documento `File` y descarga el objeto desde el servidor. El SQL no crea políticas para `anon` ni `authenticated`; el acceso directo queda denegado por defecto.

Use `SUPABASE_SERVER_KEY` con una clave `sb_secret_...`. El adaptador también acepta temporalmente una clave heredada `service_role`. Para una clave moderna solo se envía el encabezado `apikey`; el encabezado Bearer se conserva exclusivamente para el JWT heredado.

## Transferencias

`scripts/supabase_storage_transfer.py` realiza subida, descarga y eliminación privada mediante streaming. No carga respaldos completos en memoria.

El endpoint de eliminación envía `prefixes` al endpoint de borrado de bucket; no intenta eliminar un objeto con una ruta HTTP incompatible.

## Verificaciones mínimas

1. Los tres buckets existen y son privados.
2. La consulta final de `04_storage_bucket_and_rls.sql` no devuelve políticas permisivas asociadas.
3. Una descarga privada sin permiso Frappe es rechazada.
4. La clave server-only no aparece en HTML, JavaScript, logs o repositorio.
5. Una subida de prueba se recupera con el mismo SHA-256.
