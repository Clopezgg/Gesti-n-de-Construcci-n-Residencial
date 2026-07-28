# NEXORA — Despliegue en EC2 y Coolify

Este paquete es el despliegue oficial de NEXORA y utiliza únicamente artefactos con alcance NEXORA. ERPNext/Frappe permanece como motor técnico interno.

## Archivos canónicos

- `Dockerfile.nexora`
- `docker-compose.nexora.yml`
- `.env.nexora.example`
- `deploy/nexora/*.sh`

## Configuración en Coolify

1. Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
2. Rama: `main`.
3. Build pack: **Docker Compose**.
4. Compose path: `/docker-compose.nexora.yml`.
5. Servicio público: `frontend`.
6. Puerto interno: `8080`.
7. Variables: usar `.env.nexora.example` como referencia y conservar los secretos existentes.

## Arranque controlado

### Backend

`backend` conserva la responsabilidad exclusiva de inicialización mediante `deploy/nexora/init-site.sh`:

1. espera a MariaDB y Redis saludables;
2. detecta si la base ya contiene un sitio Frappe;
3. crea el sitio únicamente cuando la base está vacía y no existe configuración persistente;
4. instala ERPNext y NEXORA cuando corresponde;
5. ejecuta `bench migrate`;
6. limpia caché, habilita el scheduler y verifica `list-apps`;
7. inicia Gunicorn;
8. solo entonces el healthcheck HTTP pasa a `healthy`.

### Servicios secundarios

Coolify no debe mantener bloqueado `docker compose up -d` mientras el backend instala o migra. Por eso:

- `websocket`, workers, scheduler, frontend y backup dependen de que `backend` haya iniciado, no de que ya esté saludable;
- websocket, workers y scheduler esperan internamente hasta 600 segundos el endpoint real `/api/method/ping` antes de iniciar su proceso;
- frontend puede iniciar Nginx, pero su healthcheck permanece fallando hasta que el backend y el sitio respondan;
- el respaldo inicial, cuando está habilitado, espera al backend antes de ejecutarse;
- ningún healthcheck se desactiva y ningún servicio se declara saludable mediante una simulación.

Esta separación permite que Coolify cree los contenedores y libere el comando de despliegue sin confundir una migración normal con un fallo de orquestación.

## Incidente corregido — 2026-07-28

El despliegue del SHA `c192be8f71a4580ac4ec6297476c5449d894f306` construyó correctamente la imagen y dejó MariaDB y Redis saludables. Sin embargo, Coolify terminó el comando con código `255` mientras varios servicios permanecían bloqueados por `depends_on: condition: service_healthy` sobre el backend.

La corrección se implementó en el PR `#29`:

- dependencias secundarias cambiadas a `service_started`;
- espera real trasladada al interior de los procesos que requieren el sitio;
- tiempo de inicialización tolerado ampliado sin relajar la salud real;
- instalación, migración, rollback, reinicio y stack completo reproducidos en CI.

## Base existente

Cuando la base ya está inicializada:

1. se conserva la base y el volumen `sites`;
2. NEXORA se instala solo si falta;
3. se ejecuta `bench migrate`;
4. se limpia caché;
5. los servicios arrancan después de comprobar el endpoint real.

No se recrean datos ni se reemplaza automáticamente una configuración persistente existente.

## Volúmenes persistentes

- `nexora-mariadb-data`
- `nexora-redis-queue-data`
- `nexora-sites`
- `nexora-logs`

MariaDB y Redis no publican puertos al host. Coolify administra el enrutamiento y la red.

## Despliegue y rollback

Antes de pulsar **Deploy**:

1. confirmar el SHA actual de `main` indicado en `EXECUTION_STATE.md`;
2. comprobar que existe un respaldo verificable de MariaDB y archivos privados;
3. conservar el SHA previamente desplegado como referencia de rollback;
4. no eliminar ni recrear volúmenes.

Después del despliegue:

1. esperar a que `frontend`, `backend`, websocket, workers y scheduler queden saludables;
2. comprobar `/api/method/ping`;
3. iniciar sesión;
4. abrir el Dashboard NEXORA y la consola operativa;
5. verificar una consulta no destructiva del Libro Central;
6. revisar `nexora-backend-startup.log` y `nexora-backend-healthcheck.log` si algún servicio no alcanza salud.

Si la validación falla, volver al SHA anterior sin borrar volúmenes y conservar los logs del intento.

## Validación local y CI

```bash
docker compose -f docker-compose.nexora.yml config
bash -n deploy/nexora/*.sh
```

La compuerta **NEXORA app** construye el stack real, ejecuta instalación, migración, reinicio y valida escritorio, iPhone y PWA antes de permitir la fusión.
