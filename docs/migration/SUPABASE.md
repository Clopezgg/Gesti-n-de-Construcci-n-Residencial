# Supabase: exportación, RLS y Storage

## Responsabilidad en el sistema consolidado

Frappe/MariaDB es la base transaccional del destino. Supabase se utiliza como fuente histórica y, opcionalmente, como almacenamiento privado de archivos compartido entre los servicios de Render. No se hacen consultas Supabase desde el navegador del ERP.

## Variables

- `SUPABASE_URL`: URL del proyecto.
- `SUPABASE_SERVICE_ROLE_KEY`: sólo backend/worker; nunca `VITE_*`, nunca GitHub.
- `SUPABASE_STORAGE_MODE=enabled`: activa el hook remoto.
- `SUPABASE_STORAGE_BUCKET=construction-evidence`.
- `SUPABASE_PROJECT_ID`: filtro opcional para exportación.
- Credenciales S3: únicamente para herramientas administrativas de backup, no para la aplicación.

## Orden seguro

1. Backup de base de datos y Storage.
2. `01_preflight.sql` y captura de conteos/políticas.
3. `02_relational_validation.sql`; el resultado esperado es cero filas por consulta.
4. Exportación con `scripts/export_supabase_snapshot.py`.
5. Verificación local del JSON/manifiesto.
6. Sólo después del respaldo, aplicar `04_storage_bucket_and_rls.sql` si se usará el bucket con Frappe.
7. Importar en ERPNext y conciliar con `03_post_export_reconciliation.sql`.

## Modelo de seguridad

- El bucket se mantiene `public=false`, límite 12 MiB y MIME permitidos JPEG/PNG/WebP/PDF.
- Objetos históricos conservan las políticas por proyecto encontradas en el origen.
- Objetos de Frappe usan `frappe/<site>/<private|public>/<hash>-<nombre>`.
- No se concede acceso `anon`/`authenticated` al prefijo `frappe`; el servidor usa `service_role`, que no se comparte con clientes.
- La URL guardada en Frappe apunta a un método interno. Para archivos privados, dicho método exige permiso de lectura del documento File; los públicos conservan la semántica pública de Frappe.
- Eliminaciones se realizan por Storage API, no borrando directamente filas de `storage.objects`.

## Pruebas RLS obligatorias en un proyecto real

Con usuarios A/B de proyectos diferentes:

1. A puede leer su snapshot y sus evidencias históricas.
2. A no puede leer/escribir objetos de B.
3. Viewer no inserta/actualiza datos restringidos.
4. Admin del proyecto puede las operaciones permitidas y no accede a otros proyectos.
5. `anon` no enumera ni descarga el bucket privado.
6. La clave `service_role` funciona sólo desde backend y no aparece en HTML, JS, logs ni repositorio.
7. Una descarga Frappe privada sin sesión devuelve permiso denegado.

Estas pruebas no se pueden ejecutar sin las credenciales y datos del proyecto real; deben documentarse con usuario, política, operación y resultado antes de producción.

## Respaldo y restauración de archivos

Con S3 habilitado en Supabase, use una herramienta S3 compatible para sincronizar el bucket y conserve checksums. Supabase Storage no ofrece versionado de objetos; mantenga copias externas con retención. `storage-manifest.json` es parte inseparable del paquete de migración.
