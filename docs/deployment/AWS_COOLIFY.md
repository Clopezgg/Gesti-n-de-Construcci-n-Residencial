# AWS EC2 + Coolify: arquitectura productiva de ConstruControl

## 1. Fuente de verdad

La producción vigente utiliza:

- AWS EC2;
- Ubuntu Linux x86_64, plataforma Docker `linux/amd64`;
- Coolify autogestionado;
- Docker Compose desde `/docker-compose.yml`;
- repositorio privado `Clopezgg/Gesti-n-de-Construcci-n-Residencial`;
- rama `main`.

Render y Oracle no forman parte de la arquitectura productiva. Supabase se conserva únicamente como origen histórico y como copia remota opcional.

## 2. Topología

Servicios definidos en `docker-compose.yml`:

- `mariadb`: MariaDB 10.6, privado;
- `redis-cache`: caché, privado;
- `redis-queue`: colas, privado y persistente;
- `backend`: Frappe/ERPNext y API ConstruControl;
- `websocket`: tiempo real;
- `queue-short`: tareas cortas y predeterminadas;
- `queue-long`: tareas largas;
- `scheduler`: tareas programadas;
- `frontend`: Nginx, único servicio con dominio público;
- `backup`: respaldo programado.

El dominio se asigna al servicio `frontend` en el puerto interno `8080`.

## 3. Volúmenes persistentes

```text
mariadb-data       Base de datos
redis-queue-data   Cola persistente
sites              Configuración, archivos privados y respaldos
logs               Logs operativos
```

No ejecute `docker compose down -v` y no elimine volúmenes desde Coolify.

## 4. Inicio seguro del backend

`deploy/coolify/start-backend.sh` ejecuta `deploy/coolify/init-site.sh` antes de Gunicorn.

`init-site.sh`:

1. espera MariaDB;
2. detecta si la base ya contiene ERPNext;
3. en una base existente ejecuta `bench --site "$SITE_NAME" migrate`;
4. en una instalación vacía crea el sitio una sola vez;
5. si existe configuración del sitio pero la base está vacía, se detiene para evitar sobrescritura.

## 5. Variables obligatorias

Configure en Coolify, nunca en GitHub:

```text
DB_PASSWORD
DB_ROOT_PASSWORD
ADMIN_PASSWORD
FRAPPE_ENCRYPTION_KEY
FRAPPE_EXTERNAL_URL
```

Mantenga estables `DB_PASSWORD`, `DB_ROOT_PASSWORD` y `FRAPPE_ENCRYPTION_KEY` después de crear datos.

## 6. Security Group de AWS

Reglas mínimas recomendadas:

| Tipo | Puerto | Origen |
|---|---:|---|
| HTTP | 80 | `0.0.0.0/0` |
| HTTPS | 443 | `0.0.0.0/0` |
| SSH | 22 | EC2 Instance Connect o una IP administrativa controlada |
| Coolify | 8000 | rango administrativo controlado |
| Coolify realtime | 6001 | rango administrativo controlado |
| Coolify terminal | 6002 | rango administrativo controlado |

No publique 3306, 6379, 8000 del backend ni 9000 del WebSocket.

## 7. Despliegue desde GitHub

En Coolify:

```text
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
```

Antes de desplegar:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Después del despliegue, desde la terminal del backend:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" clear-cache
```

## 8. Health checks

Compruebe por la URL pública:

```text
https://DOMINIO/api/method/ping
```

Debe responder sin 502. En Coolify deben permanecer saludables backend, frontend, MariaDB, Redis, workers, scheduler y WebSocket.

## 9. Respaldos

`backup-now.sh` crea una copia Bench con archivos dentro de:

```text
sites/<SITE_NAME>/private/backups
```

Luego crea un archivo verificable en:

```text
sites/<SITE_NAME>/private/backup-archive
```

Si existen `SUPABASE_URL` y `SUPABASE_SERVER_KEY`, puede enviarse una copia adicional al bucket privado. Sin esas variables, el respaldo local continúa funcionando.

## 10. Restauración

La restauración total debe probarse en un sitio aislado antes de afectar producción. No restaure encima de producción sin:

1. confirmar el archivo y SHA-256;
2. crear una copia nueva del estado actual;
3. detener escrituras;
4. validar la versión de ERPNext;
5. ejecutar la restauración en un entorno aislado;
6. verificar login, permisos, datos, archivos, workers y scheduler.

## 11. HTTPS

La URL administrativa de Coolify no es la URL pública de ConstruControl. Asigne un dominio al servicio `frontend`, active HTTPS en Coolify y establezca:

```text
FRAPPE_EXTERNAL_URL=https://DOMINIO
```

No declare producción terminada mientras el acceso dependa de una URL administrativa o HTTP sin certificado.
