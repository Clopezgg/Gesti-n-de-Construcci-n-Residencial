# Despliegue gratuito en Oracle Cloud + Coolify

## Estado vigente

El despliegue activo de ConstruControl usa `docker-compose.yml`. El Blueprint pagado de Render fue retirado para evitar cargos accidentales.

## Topología

Una sola VM ARM64 ejecuta Coolify y la pila Docker Compose:

- MariaDB 10.6;
- Redis cache;
- Redis queue persistente;
- configurator e init-site de una sola ejecución;
- backend Gunicorn;
- WebSocket;
- workers corto y largo;
- scheduler;
- frontend Nginx;
- respaldo automático local.

## Requisitos mínimos

- Oracle Cloud Compute `VM.Standard.A1.Flex` dentro de los límites Always Free;
- Ubuntu 24.04 LTS ARM64;
- 2 OCPU, 12 GB RAM y al menos 80 GB de volumen de arranque;
- puertos 22, 80, 443, 8000, 6001 y 6002 durante la instalación inicial de Coolify;
- repositorio privado accesible mediante GitHub App o Deploy Key.

## Configuración de Coolify

Cree una aplicación desde el repositorio y seleccione:

```text
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
```

Asigne el dominio únicamente al servicio `frontend` y al puerto interno `8080`. MariaDB y Redis deben permanecer sin dominio y sin publicación de puertos.

## Variables obligatorias

```text
DB_PASSWORD
DB_ROOT_PASSWORD
ADMIN_PASSWORD
FRAPPE_ENCRYPTION_KEY
```

Valores recomendados:

```bash
openssl rand -base64 36
openssl rand -base64 36
openssl rand -base64 36
openssl rand -base64 32
```

No regenere `DB_PASSWORD` ni `FRAPPE_ENCRYPTION_KEY` después de crear datos.

## Persistencia

Los volúmenes nombrados son parte de la base de datos y del sitio. Nunca use:

```bash
docker compose down -v
```

Nunca elimine los volúmenes `mariadb-data`, `sites` o `backups` desde Coolify.

## Respaldos

El contenedor `backup` ejecuta `backup-now.sh` al iniciar y luego diariamente a la hora local definida por `BACKUP_LOCAL_HOUR`. Los conjuntos se guardan en el volumen `backups` con manifiesto SHA-256.

Supabase es opcional. Si se definen `SUPABASE_URL` y `SUPABASE_SERVER_KEY`, se envía una copia adicional al bucket privado configurado. Sin esas variables, el sistema continúa funcionando con almacenamiento local persistente.

## Actualizaciones

Un cambio en `main` puede activar un redeploy automático desde Coolify. Antes de actualizar:

1. ejecute un respaldo manual;
2. confirme que el manifiesto se valida;
3. despliegue el nuevo commit;
4. revise `init-site`, `backend`, workers y scheduler;
5. ejecute `bench --site "$SITE_NAME" doctor`.

El manual completo y lineal está en `MANUAL_PASO_A_PASO.md`.
