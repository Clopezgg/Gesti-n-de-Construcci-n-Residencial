# AWS EC2 + Coolify — arquitectura productiva

## Fuente de verdad

- AWS EC2 x86_64.
- Ubuntu Linux.
- Plataforma Docker `linux/amd64`.
- Coolify autogestionado.
- Docker Compose: `/docker-compose.yml`.
- ERPNext/Frappe 15.
- MariaDB 10.6.
- Redis privado.
- Rama productiva: `main`.
- Servicio público: `frontend:8080`.

Render y Oracle están fuera de la arquitectura vigente. Supabase es únicamente origen histórico de migración.

## Servicios y health checks

```text
mariadb
redis-cache
redis-queue
backend
websocket
queue-short
queue-long
scheduler
frontend
backup
```

Todos deben aparecer `healthy`.

```bash
docker compose ps
```

MariaDB y Redis no publican puertos.

## Volúmenes

```text
mariadb-data
redis-queue-data
sites
logs
```

No ejecute `docker compose down -v`.

## Despliegue

En Coolify:

```text
Branch: main
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
Domain service: frontend
Port: 8080
```

Antes de desplegar:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Después:

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
bench --site "$SITE_NAME" doctor
```

## Backup

Ruta de trabajo de Bench:

```text
sites/<SITE_NAME>/private/backups
```

Archivo verificable y manifiestos:

```text
sites/<SITE_NAME>/private/backup-archive
```

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
MANIFEST="$(cat "sites/${SITE_NAME}/private/backup-archive/latest-manifest-path")"
python3 apps/erpnext/scripts/verify_backup_manifest.py --manifest "$MANIFEST"
```

## Restore en ensayo

```bash
bash apps/erpnext/deploy/coolify/restore-verify.sh \
  "$MANIFEST" \
  construcontrol-restore-test
```

El sitio de ensayo debe ser distinto de producción. El script verifica SHA-256, restaura base y archivos, ejecuta tres migraciones, smoke test y conciliación.

## HTTPS

Asigne el dominio al servicio `frontend`, active TLS en Coolify y configure:

```text
FRAPPE_EXTERNAL_URL=https://DOMINIO_PUBLICO
```

No acepte producción por HTTP ni mediante la URL administrativa de Coolify.
