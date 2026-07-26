# NEXORA deployment package (EC2 + Coolify)

This package is isolated from legacy ConstruControl runtime files and uses only NEXORA-scoped artifacts.

## Files

- `Dockerfile.nexora`
- `docker-compose.nexora.yml`
- `.env.nexora.example`
- `deploy/nexora/*.sh`

## Coolify setup

1. Repository branch: your current NEXORA branch.
2. Build pack: **Docker Compose**.
3. Compose path: `/docker-compose.nexora.yml`.
4. Public service: `frontend`.
5. Internal port: `8080`.
6. Environment file: start from `.env.nexora.example` and fill all required variables.

## One-time bootstrap (empty base)

`backend` runs `deploy/nexora/init-site.sh` and performs:

1. Wait for MariaDB.
2. Create `SITE_NAME`.
3. Install ERPNext.
4. Register app source as Frappe app `nexora`.
5. Install app `nexora`.
6. Run `migrate`.
7. Build NEXORA assets.
8. Enable scheduler.
9. Clear cache.
10. Verify `list-apps`.

## Existing base bootstrap

If schema already exists, startup does not overwrite data. It:

1. Keeps existing site/database.
2. Installs `nexora` only when missing.
3. Runs `migrate`.
4. Clears cache.
5. Starts services normally.

## Operational notes

- Compose project name is `nexora`.
- Platform is fixed to `linux/amd64`.
- MariaDB and Redis do not publish host ports.
- No custom Docker networks are defined (Coolify manages network wiring).
- Persistent volumes are NEXORA-only:
  - `nexora-mariadb-data`
  - `nexora-redis-queue-data`
  - `nexora-sites`
  - `nexora-logs`
- Backup and restore scripts:
  - `backup-now.sh`
  - `backup-loop.sh`
  - `restore-verify.sh`

## Local validation commands

```bash
docker compose -f docker-compose.nexora.yml config
bash -n deploy/nexora/*.sh
```
