# ConstruControl sobre ERPNext

ConstruControl es el módulo privado de gestión integral de construcción residencial sobre **ERPNext 15.117.0 / Frappe 15**.

## Fuente única de verdad

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama productiva protegida: `main`
- Rama de revisión: `reconstruccion-definitiva-construcontrol`
- Despliegue productivo: `docker-compose.yml`
- Infraestructura: AWS EC2 x86_64 + Ubuntu + Coolify
- Base productiva: MariaDB 10.6
- Servicios: Redis cache, Redis queue, backend, workers, scheduler, WebSocket, frontend y backup
- Manual oficial: `MANUAL_PASO_A_PASO.md`

Render y Oracle no forman parte de la arquitectura vigente. Supabase se usa únicamente como origen histórico de migración; no es la base productiva ni el destino oficial de respaldos.

## Módulos

`US01`, `FI01`, `FI02`, `PR01`, `CO01`, `MM01`, `MM02`, `MIGO`, `QC01`, `CL01`, `BI01`, `AU01` y `MIG`.

Cada operación crítica se valida desde backend. Los indicadores consumen servicios canónicos y los eventos financieros, inventarios, cierres y auditoría conservan trazabilidad.

## Topología

```text
Internet / HTTPS
        |
Coolify reverse proxy
        |
frontend :8080
   |             |
backend :8000   WebSocket :9000
   |
   +-- MariaDB 10.6
   +-- Redis cache
   +-- Redis queue
   +-- worker short/default
   +-- worker long/default/short
   +-- scheduler
   +-- backup local verificable
```

MariaDB y Redis no publican puertos. Los datos persistentes están en los volúmenes `mariadb-data`, `redis-queue-data`, `sites` y `logs`.

## Despliegue

En Coolify:

```text
Branch: main
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
Public service: frontend
Internal port: 8080
```

Antes de actualizar:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Nunca ejecute `docker compose down -v` en producción y nunca elimine los volúmenes persistentes.

## Respaldo y restauración

El respaldo oficial se crea dentro del volumen `sites`, incorpora base de datos, archivos públicos, archivos privados y configuración, y genera un manifiesto con tamaños y SHA-256.

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
cat "sites/${SITE_NAME}/private/backup-archive/latest-manifest-path"
```

La restauración se prueba únicamente en un sitio aislado:

```bash
bash apps/erpnext/deploy/coolify/restore-verify.sh \
  RUTA_MANIFEST \
  construcontrol-restore-test
```

El script rechaza el sitio productivo, verifica el backup, restaura, ejecuta tres migraciones y corre el smoke test.

## Migración histórica

El flujo obligatorio es:

```text
inventario del origen
→ respaldo y SHA-256
→ simulación
→ importación idempotente
→ conciliación de conteos, montos y relaciones
→ revisión de duplicados y huérfanos
→ rollback disponible
→ inventario de datos demo
```

Las fotografías históricas permanecen fuera de la importación acordada; se conserva la metadata y se permiten evidencias nuevas privadas.

## Certificación

La implementación se certifica sobre un SHA congelado mediante:

1. Puerta A: finanzas, proyectos, contratos y MariaDB 4/4.
2. Puerta B: operación, inventario, avance, cierres, BI y auditoría.
3. Puerta C: PWA, servicios, persistencia, backup y restore.
4. FINAL: instalación limpia, actualización, tres migraciones y redeploy.
5. Auditoría independiente 1:1.

El workflow oficial es `.github/workflows/construcontrol-full-certification.yml`.

## Validación rápida local

```bash
python -m pip install --disable-pip-version-check PyYAML==6.0.2
python scripts/validate_repository.py
python scripts/validate_construcontrol_integration.py
python scripts/validate_construcontrol_completion.py
python -m unittest discover -s erpnext/construcontrol/tests -p 'test_*_standalone.py' -v
python -m compileall -q erpnext/construcontrol scripts
bash -n deploy/coolify/*.sh
DB_PASSWORD=x DB_ROOT_PASSWORD=x ADMIN_PASSWORD=x FRAPPE_ENCRYPTION_KEY=x docker compose config
```

No se considera aprobado hasta disponer de evidencia verde para A, B, C, FINAL y auditoría 1:1.
