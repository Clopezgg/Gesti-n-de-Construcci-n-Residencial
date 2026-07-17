# Auditoría integral de origen, destino y despliegue

Fecha de auditoría inicial: 17 de julio de 2026. Arquitectura de despliegue actualizada posteriormente a Oracle Cloud + Coolify para eliminar la topología pagada de Render.

## Sistemas analizados

### Origen

- SPA React/TypeScript/Vite.
- Snapshot `AppData` en `localStorage` y sincronización opcional con Supabase.
- Autenticación, perfiles, RLS y bucket privado de evidencia.
- Módulos de proyectos, fases, ingresos, egresos, contratos, inventario, avance, cierres, reportes, usuarios y auditoría.
- Los ZIP no incluyeron registros operativos reales, dump de base, export de `localStorage` ni objetos del bucket.

### Destino

- ERPNext 15.117.0 / Frappe 15.
- DocTypes estándar para proyectos, tareas, compras, inventario, contabilidad, contratos, proveedores y archivos.
- Módulo nativo `ConstruControl`, roles, conciliación, importador y preservación de payload histórico.

## Decisiones vigentes

| Conflicto | Decisión |
|---|---|
| SPA/localStorage frente a Frappe/ORM | ERPNext permanece como plataforma definitiva. |
| JSON histórico frente a modelo relacional | Preservación íntegra versionada y mapeo controlado. |
| Auth/RLS de origen frente a permisos Frappe | Frappe es la autoridad de acceso. |
| Registros financieros ambiguos | No se presentan asientos ni stock histórico sin conciliación. |
| Render con costo mensual | Blueprint retirado; despliegue mediante `docker-compose.yml` en Oracle Cloud Always Free + Coolify. |
| Filesystem de contenedores | Volúmenes persistentes para MariaDB, sitios, colas, logs y respaldos. |
| Copias de seguridad | Backup Bench con archivos, manifiesto SHA-256, retención local y copia remota opcional. |

## Arquitectura de producción vigente

Una VM ARM64 ejecuta:

- MariaDB 10.6;
- Redis cache y Redis queue;
- inicialización idempotente;
- backend Gunicorn;
- WebSocket;
- workers corto y largo;
- scheduler;
- frontend Nginx;
- backup automático.

MariaDB y Redis no publican puertos al host. Solo `frontend` expone el puerto interno 8080 al proxy de Coolify.

## Validaciones incluidas

- Sintaxis de Python y JSON.
- Pruebas standalone del normalizador y la migración.
- Validación estructural del Docker Compose y sus cinco volúmenes persistentes.
- Rechazo de `render.yaml` como configuración activa.
- Escaneo de secretos.
- Sintaxis Bash de scripts Coolify.
- Construcción CI de la imagen `linux/arm64`.
- Verificación de paquetes ZIP y manifiestos SHA-256.

## Límites honestos

No se certifica todavía:

- despliegue real en una cuenta Oracle;
- login y permisos en producción;
- migración de registros históricos reales;
- restauración completa en una VM aislada.

Esas validaciones requieren las cuentas, credenciales y datos reales del propietario y deben ejecutarse siguiendo `MANUAL_PASO_A_PASO.md`.
