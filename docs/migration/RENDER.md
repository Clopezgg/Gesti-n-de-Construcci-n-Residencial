# Despliegue en Render

`render.yaml` define la arquitectura completa de producción para ERPNext 15:

- `construcontrol-web`: Nginx público y health check `/api/method/ping`.
- `construcontrol-backend`: Gunicorn y pre-deploy de sitio/migraciones.
- `construcontrol-websocket`: Socket.IO.
- `construcontrol-worker`: colas short/default/long.
- `construcontrol-scheduler`: programador continuo.
- `construcontrol-db`: MariaDB 10.6 con disco persistente.
- dos Render Key Value: caché sin persistencia y cola persistente/no-eviction.

## Antes de crear el Blueprint

1. Suba este repositorio a GitHub y confirme que la Action está verde.
2. Cree/verifique el bucket privado con `migration/supabase/04_storage_bucket_and_rls.sql`.
3. Tenga disponibles, sin pegarlas en archivos:

   - contraseña inicial de Administrator;
   - URL externa prevista, por ejemplo `https://construcontrol-web.onrender.com`;
   - URL Supabase;
   - clave `service_role` server-only.

4. Elija planes con RAM suficiente. ERPNext no es apropiado para una topología gratuita suspendible.

## Creación

1. En Render seleccione **New → Blueprint** y conecte el repositorio.
2. Render leerá `render.yaml`.
3. Complete las variables marcadas `sync: false` en `construcontrol-backend`:

   - `FRAPPE_EXTERNAL_URL`
   - `ADMIN_PASSWORD`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

4. Render genera y conserva `MARIADB_ROOT_PASSWORD`, `DB_PASSWORD` y `FRAPPE_ENCRYPTION_KEY`. No regenere estas variables tras crear datos.
5. Lance el Blueprint. El pre-deploy detecta si `tabDocType` existe: crea el sitio solamente en una base vacía; en despliegues posteriores ejecuta `bench migrate`. No usa `--force` ni borra la base.
6. Cuando el health check esté verde, abra la URL, ingrese como `Administrator` y complete Setup Wizard.
7. Asigne dominio personalizado/TLS si corresponde y actualice `FRAPPE_EXTERNAL_URL` sin barra final.

## Primer control de producción

Desde Shell del backend:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" backup --with-files
```

Compruebe login, Desk, workspace ConstruControl, WebSocket, una tarea de cola, scheduler, subida/descarga privada y logs sin secretos.

## Archivos y persistencia

Los contenedores web/backend/worker no comparten un disco Render. Por eso `SUPABASE_STORAGE_MODE=enabled` es obligatorio en el Blueprint para archivos de aplicación. El hook usa Storage privado y evita depender del filesystem efímero. El disco de MariaDB no almacena archivos adjuntos.

## Backups

- Active snapshots/backup externo del disco MariaDB y pruebe restauración.
- Ejecute backups de Bench antes de cada migración funcional.
- Sincronice el bucket Supabase a almacenamiento externo con checksums.
- Conserve `FRAPPE_ENCRYPTION_KEY`; perderla impide descifrar secretos almacenados por Frappe.

## Fallos frecuentes

| Síntoma | Revisión |
|---|---|
| Health check 502 | Backend/WebSocket hostport, migración y logs Nginx. |
| Site not found | `SITE_NAME` y `FRAPPE_SITE_NAME_HEADER` deben coincidir con `construcontrol`. |
| Colas detenidas | Key Value queue, política `noeviction`, worker y scheduler. |
| Archivo 403 | Permiso Frappe, `is_private`, URL/key/bucket y credencial server-only. |
| Archivo 5xx | Límite/MIME del bucket, objeto ausente o RLS/credencial. |
| Base no inicializa | MariaDB lista, root secret estable, DB vacía y pre-deploy logs. No agregue `--force`. |
| Tiempo de espera | Aumente plan/recursos antes de subir timeouts indiscriminadamente. |

La configuración YAML puede validarse con Render CLI 2.7+ antes del sync.
