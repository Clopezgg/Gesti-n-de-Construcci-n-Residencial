# GitHub y despliegue con Coolify

## Revisión previa

```bash
python -m pip install PyYAML==6.0.2
python scripts/validate_repository.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
bash -n deploy/coolify/*.sh
git status --short
git diff --check
```

Confirme que no existen `.env`, exports, respaldos, ZIP, `sites/`, logs, credenciales, claves SSH ni archivos de evidencia. `.gitignore` cubre esos grupos y `.gitattributes` fija LF para scripts Linux.

## Repositorio de producción

```text
Repository: Clopezgg/Gesti-n-de-Construcci-n-Residencial
Branch: main
Deployment file: /docker-compose.yml
```

Coolify debe conectarse mediante GitHub App o Deploy Key con acceso únicamente al repositorio necesario. Los secretos se guardan en **Environment Variables de Coolify**, nunca en GitHub.

## Flujo de cambios

Por decisión del propietario, la corrección actual se realizó directamente en `main`, sin crear otra rama. Para cambios futuros de alto riesgo se recomienda respaldo previo, validación local, revisión del diff y confirmación de la Action antes de activar el redeploy.

No use `git add -f` para incluir datos ignorados. Si un secreto fue añadido alguna vez, rótelo y elimínelo del historial; borrarlo en un commit posterior no lo protege.

## CI incluida

`.github/workflows/construcontrol-validation.yml`:

1. valida Python, JSON, secretos y la topología Docker Compose;
2. ejecuta las pruebas standalone de migración;
3. valida sintaxis de `deploy/coolify/*.sh`;
4. compila los módulos Python modificados;
5. construye la imagen para `linux/arm64`, arquitectura de Oracle Ampere;
6. verifica el usuario final y los entrypoints de Coolify.

Una Action verde no sustituye el despliegue real. Antes de producción deben comprobarse MariaDB, Redis, init-site, login, permisos, archivos, workers, scheduler, WebSocket y restauración de respaldo.

## Actualización de producción

Antes de cada actualización desde `main`:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Después del redeploy:

```bash
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```
