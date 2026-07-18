# ConstruControl sobre ERPNext

Sistema de gestión de construcción residencial basado en **ERPNext 15.117.0 / Frappe 15**. ERPNext aporta la plataforma transaccional, mientras que el módulo `ConstruControl` implementa el flujo especializado de fondos, gastos, contratos, fases, materiales, inventario, avance, cierres, reportes, auditoría y migración histórica.

## Fuente única de verdad

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama productiva: `main`
- Despliegue: `docker-compose.yml`
- Infraestructura productiva: AWS EC2 x86_64 + Ubuntu + Coolify
- Base de datos: MariaDB 10.6 en volumen Docker persistente
- Caché y colas: Redis privado

No se deben realizar cambios permanentes únicamente dentro del servidor. Todo cambio de código, esquema, despliegue o documentación debe quedar versionado en `main`.

## Arquitectura productiva vigente

```text
Internet
   |
   v
Dominio HTTPS / proxy de Coolify
   |
   v
frontend Nginx :8080
   |-----------------------------|
   v                             v
backend Gunicorn :8000        WebSocket :9000
   |
   +--> worker short/default
   +--> worker long/default/short
   +--> scheduler
   +--> respaldo automático
   +--> MariaDB 10.6
   +--> Redis cache
   +--> Redis queue
```

MariaDB, Redis y los puertos internos no se publican directamente a Internet. El dominio público se asigna únicamente al servicio `frontend`, puerto interno `8080`.

## Configuración de Coolify

```text
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
```

Variables obligatorias:

```text
DB_PASSWORD
DB_ROOT_PASSWORD
ADMIN_PASSWORD
FRAPPE_ENCRYPTION_KEY
FRAPPE_EXTERNAL_URL
```

La plantilla completa está en `.env.example`. Los valores reales se almacenan en Coolify, no en GitHub.

## Persistencia

Los datos se mantienen en volúmenes Docker nombrados:

- `mariadb-data`: base de datos transaccional;
- `redis-queue-data`: cola persistente;
- `sites`: configuración del sitio, archivos privados y respaldos Bench;
- `logs`: registros de Frappe y servicios.

Los respaldos se guardan bajo:

```text
sites/<SITE_NAME>/private/backups
sites/<SITE_NAME>/private/backup-archive
```

Nunca ejecute:

```bash
docker compose down -v
```

Nunca elimine los volúmenes `mariadb-data`, `sites`, `redis-queue-data` o `logs` desde Coolify.

## ConstruControl

El centro operativo incluye:

- `FI01`: ingresos, remesas, aportes y saldos;
- `FI02`: gastos, compras, pagos y comprobación;
- `CO01`: contratos, pagos y saldos contractuales;
- `PR01`: fases y planificación de obra;
- `MM01`: materiales;
- `MIGO`: movimientos de inventario;
- `MM02`: solicitudes y compras;
- `QC01`: avance de obra;
- `CL01`: cierres semanales;
- `BI01`: reportes;
- `AU01`: auditoría;
- `US01`: usuarios y permisos;
- `MIG`: validación, respaldo, migración y conciliación.

La migración conserva los registros originales y sus huellas, crea relaciones operativas y evita duplicados mediante claves de origen idempotentes.

## Datos históricos de Supabase

Supabase es el **origen histórico**, no la base productiva del ERP nuevo. El respaldo real no debe subirse al repositorio.

El flujo obligatorio es:

```text
respaldo privado
→ validación
→ simulación
→ respaldo Bench de MariaDB
→ importación
→ conciliación
→ limpieza oficial de datos demo
```

Para la migración acordada, las fotografías antiguas no se importan. Solo se conserva metadata de evidencia. La función normal de adjuntar archivos nuevos en ERPNext permanece disponible para la operación futura.

## Despliegue seguro

El backend ejecuta:

```text
start-backend.sh
→ init-site.sh
→ detección de base existente
→ bench migrate
→ Gunicorn
```

Una base existente se migra sin recrearse. Si existe configuración de sitio pero la base aparece vacía, el proceso se detiene para impedir una sobrescritura accidental.

## Validación local

```bash
python -m pip install --disable-pip-version-check PyYAML==6.0.2
python scripts/validate_repository.py
python scripts/validate_construcontrol_integration.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
python erpnext/construcontrol/tests/test_backup_reader_standalone.py -v
bash -n deploy/coolify/*.sh
```

Resultado mínimo esperado:

```text
Repository validation: 0 error(s)
```

GitHub Actions también construye la imagen `linux/amd64`, compila el código y ejecuta las pruebas antes de aprobar `main`.

## Operación desde el backend de Coolify

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

Respaldo manual:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

## Seguridad

- MariaDB y Redis permanecen privados.
- Los secretos se administran en Coolify.
- Los archivos de migración se guardan como archivos privados.
- El backend valida permisos; ocultar botones no sustituye la autorización.
- La importación definitiva exige `System Manager`, huella SHA-256 válida y respaldo verificable.
- Las imágenes históricas están excluidas de la importación actual.
- No se aceptan claves `anon`, `publishable`, `VITE_` ni claves de servicio en JavaScript.

## Documentación vigente

- `MANUAL_PASO_A_PASO.md`: manual técnico y operativo completo.
- `docs/deployment/AWS_COOLIFY.md`: infraestructura productiva.
- `docs/migration/MAPA_CORRESPONDENCIA.md`: correspondencia origen-destino.
- `docs/migration/MIGRACION_Y_ROLLBACK.md`: migración, conciliación y reversión.
- `docs/migration/AUDITORIA_INTEGRAL.md`: criterios de auditoría.
- `docs/migration/VALIDACION_RESULTADOS.md`: aceptación de resultados.

Los manuales antiguos de Render u Oracle no representan la arquitectura productiva actual y no deben utilizarse.

ERPNext conserva la licencia GNU GPL v3 y sus atribuciones originales en `license.txt` y `attributions.md`.
