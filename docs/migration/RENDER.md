# Despliegue en Render

La secuencia completa está en [`MANUAL_PASO_A_PASO.md`](../../MANUAL_PASO_A_PASO.md).

## Servicios del Blueprint

`render.yaml` define nueve recursos:

- MariaDB privada con disco persistente.
- Redis cache.
- Redis queue persistente.
- Backend Gunicorn.
- WebSocket.
- Worker.
- Scheduler.
- Frontend Nginx.
- Cron diario de respaldo remoto.

## Corrección del frontend

El frontend utiliza `deploy/render/Dockerfile.frontend`, no el Dockerfile del backend. El master de Nginx arranca con permisos suficientes para generar su configuración y los workers bajan a `frappe` mediante `nginx-main.conf`. Esto elimina el intento anterior de escribir `/etc/nginx/conf.d/frappe.conf` desde un contenedor cuyo usuario final era `frappe`.

## Filesystem

Los servicios Render no comparten disco y su filesystem normal es efímero. Por eso:

- MariaDB conserva sus datos en su propio disco.
- Los adjuntos se almacenan en Supabase Storage.
- Los paquetes de migración se descargan a un directorio temporal dentro de la misma ejecución.
- El backup cron crea el respaldo, lo sube y elimina la copia local solo después de confirmar la subida.

## Variables manuales

- `FRAPPE_EXTERNAL_URL`
- `ADMIN_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_SERVER_KEY`

No regenere `MARIADB_ROOT_PASSWORD`, `DB_PASSWORD` ni `FRAPPE_ENCRYPTION_KEY` después de crear datos.

## Validación

GitHub Actions construye tanto la imagen de aplicación como la imagen frontend y ejecuta `nginx -t` con una configuración renderizada. La aprobación final todavía requiere un Blueprint real, health check, login, cola, WebSocket, archivo privado y restauración de respaldo.
