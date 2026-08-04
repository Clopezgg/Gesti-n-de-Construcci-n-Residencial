# NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones

NEXORA es la plataforma empresarial para la gestión integral de fondos, proyectos y operaciones.

La base tecnológica utiliza **ERPNext / Frappe** como motor técnico interno cuando corresponde. ERPNext/Frappe no representa el producto comercial; funciona como infraestructura tecnológica sobre la cual se construyen los módulos y flujos NEXORA.

## Fuente única de verdad

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama productiva protegida: `main`
- Despliegue productivo: `docker-compose.yml`
- Infraestructura: AWS EC2 + Ubuntu + Coolify
- Plataforma de contenedor: `linux/amd64`
- Base productiva: MariaDB 10.6
- Servicios técnicos: Redis, backend, workers, scheduler, WebSocket y frontend

## Respaldos

Los respaldos productivos se escriben dentro del volumen del sitio, en
`sites/<SITE_NAME>/private/backups`, y los archivos comprimidos se conservan en
`sites/<SITE_NAME>/private/backup-archive`. Los genera `deploy/coolify/backup-now.sh`
mediante `bench backup --with-files`, de modo que el respaldo incluye base de datos y
archivos adjuntos. El detalle operativo —retención, hora local y ejecución al arranque—
está en `docs/deployment/AWS_COOLIFY.md`.

Límite real: respaldo y archivo viven en el mismo volumen del sitio y `backup-now.sh` no
replica fuera de él, así que este flujo cubre recuperación local (borrado accidental,
error de migración) pero no la pérdida o corrupción del volumen. Una copia externa
cifrada y una prueba periódica de restauración siguen pendientes de decisión del
propietario.

## Arquitectura

NEXORA mantiene una arquitectura empresarial basada en ERPNext/Frappe e incorpora módulos especializados para:

- fondos y operaciones financieras;
- proyectos y centros de costo;
- contratos y proveedores;
- inventario;
- auditoría y permisos;
- reportes y seguimiento operativo.

## Módulos

Los módulos existentes deben interpretarse dentro de la evolución hacia NEXORA. Las aplicaciones técnicas heredadas de ERPNext/Frappe permanecen como componentes internos mientras sean necesarias para la operación.

## Seguridad y operación

Cada operación crítica debe validarse desde backend, conservar trazabilidad y respetar permisos definidos por usuario, proyecto y documento.

No se realizan modificaciones de producción, infraestructura, secretos o datos reales sin autorización, respaldo verificable y plan de reversión.

## Certificación

La plataforma se valida mediante pruebas técnicas, permisos, integridad financiera, recorridos operativos y controles de despliegue antes de considerar una funcionalidad terminada.
