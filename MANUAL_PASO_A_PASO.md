# CONSTRUCONTROL
## Manual técnico y operativo oficial de producción

**Arquitectura vigente:** AWS EC2 x86_64 + Ubuntu + Coolify + Docker Compose + ERPNext/Frappe 15
**Base productiva:** MariaDB 10.6
**Repositorio:** `Clopezgg/Gesti-n-de-Construcci-n-Residencial`  
**Rama productiva:** `main`
**Zona horaria:** `America/Tegucigalpa`

Este es el único manual vigente. Render y Oracle no pertenecen a la arquitectura productiva. Supabase se conserva únicamente como origen histórico de migración. Los respaldos productivos se almacenan en los volúmenes persistentes de AWS/Coolify.

---

## 1. Reglas de seguridad

No ejecute en producción:

```bash
docker compose down -v
docker volume rm construcontrol_mariadb-data
docker volume rm construcontrol_sites
git push --force
```

No publique secretos, archivos `.env`, respaldos, llaves privadas ni configuraciones reales en GitHub.

Antes de una actualización, migración o restauración:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

La restauración siempre se prueba primero en un sitio aislado.

---

## 2. AWS EC2

La instancia debe ser Linux x86_64. En AWS:

```text
EC2 → Instances → ConstruControl
State: Running
Architecture: x86_64
```

Security Group:

| Puerto | Uso | Origen |
|---:|---|---|
| 80 | HTTP para redirección | público |
| 443 | HTTPS | público |
| 22 | administración | IP controlada o EC2 Instance Connect |
| 8000 | panel Coolify | rango administrativo |
| 6001/6002 | funciones administrativas Coolify | rango administrativo |

No publique 3306, 6379, 8000 del backend ni 9000 del WebSocket.

Acceso por PowerShell:

```powershell
$Key = "$HOME\Downloads\NOMBRE-LLAVE.pem"
icacls $Key /inheritance:r
icacls $Key /grant:r "$env:USERNAME:(R)"
ssh -i $Key ubuntu@IP_PUBLICA_EC2
```

---

## 3. Docker y Coolify

Compruebe:

```bash
docker --version
sudo docker info
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

En Coolify:

```text
Project: ConstruControl
Source: Clopezgg/Gesti-n-de-Construcci-n-Residencial
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
Public service: frontend
Internal port: 8080
```

Asigne el dominio al servicio `frontend`, active HTTPS y no asigne dominio a MariaDB, Redis, backend, workers, scheduler o WebSocket.

---

## 4. Variables de entorno

Configure en Coolify:

```text
ERPNEXT_VERSION=v15.117.0
SITE_NAME=construcontrol
DB_NAME=_construcontrol
DB_PASSWORD=<SECRETO_ESTABLE>
DB_ROOT_PASSWORD=<SECRETO_ESTABLE>
ADMIN_PASSWORD=<SECRETO_INICIAL>
FRAPPE_ENCRYPTION_KEY=<SALIDA_OPENSSL_RAND_BASE64_32>
FRAPPE_EXTERNAL_URL=https://DOMINIO_PUBLICO
TZ=America/Tegucigalpa

GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
PROXY_READ_TIMEOUT=120
CLIENT_MAX_BODY_SIZE=50m

BACKUP_LOCAL_HOUR=2
BACKUP_RETENTION_DAYS=14
BACKUP_RUN_ON_START=false

SUPABASE_STORAGE_MODE=disabled
```

Genere la clave de cifrado:

```bash
openssl rand -base64 32
```

No cambie `DB_PASSWORD`, `DB_ROOT_PASSWORD` ni `FRAPPE_ENCRYPTION_KEY` después de crear datos.

Las variables `SUPABASE_URL` y `SUPABASE_SERVER_KEY`, cuando sean necesarias, se usan únicamente del lado servidor para leer el origen histórico. Nunca use claves `anon`, `publishable` o variables `VITE_`.

---

## 5. Servicios

`docker-compose.yml` define:

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

Todos poseen health check.

Volúmenes persistentes:

```text
mariadb-data
redis-queue-data
sites
logs
```

Comprobar desde EC2:

```bash
docker compose ps
docker compose logs --tail=200 backend
docker compose logs --tail=200 frontend
docker compose logs --tail=200 websocket
docker compose logs --tail=200 queue-short
docker compose logs --tail=200 queue-long
docker compose logs --tail=200 scheduler
docker compose logs --tail=200 backup
```

---

## 6. Instalación limpia

En una instalación nueva, Coolify construye la imagen y el backend ejecuta:

```text
configure-site.sh
→ espera MariaDB
→ bench new-site
→ instala ERPNext/ConstruControl
→ bench migrate
→ habilita scheduler
→ inicia Gunicorn
```

No cree manualmente una segunda base.

Por la terminal del backend:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" clear-cache
```

URL de comprobación:

```text
https://DOMINIO_PUBLICO/api/method/ping
```

No continúe ante 500, 502, `unhealthy`, reinicios continuos o `Site not found`.

---

## 7. Actualización y redeploy

Antes de actualizar:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Luego:

```text
Coolify → ConstruControl → Deploy / Redeploy
```

El backend detecta la base existente y ejecuta migración sin recrearla.

Después:

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
bench --site "$SITE_NAME" doctor
```

Para la aceptación final deben aprobar tres migraciones consecutivas:

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" migrate
```

---

## 8. Configuración inicial de ERPNext

Como `Administrator`:

```text
Language: Spanish
Time Zone: America/Tegucigalpa
Country: Honduras
Currency: HNL
Company: compañía real
Fiscal Year: año vigente
Warehouse: Almacén Principal
Cost Center: Centro de Costo Principal
```

No seleccione datos demo.

En `ConstruControl Settings`:

```text
Default Company: compañía real
Default Project: proyecto real
Default Warehouse: almacén real
Default Cost Center: centro de costo real
Require backup before import: activado
Cleanup demo after migration: activado
Import historical evidence files: desactivado
```

---

## 9. Usuarios y roles

| Rol | Alcance |
|---|---|
| System Manager | administración técnica, migración y configuración crítica |
| ConstruControl Manager | administración funcional |
| ConstruControl Operator | operación y registros |
| ConstruControl Auditor | lectura, auditoría y exportación |
| ConstruControl Viewer | lectura autorizada |

Pruebe cada rol. El backend debe rechazar URLs y acciones no autorizadas aunque el botón esté oculto.

---

## 10. Módulos operativos

### FI01 — fondos

Registre remesa, aporte, depósito o transferencia con moneda, tasa, deducciones, referencia y conciliación.

Compruebe:

```text
recibido
gastado
comprometido
pendiente
disponible
proyectado
```

### FI02 — gastos

Registre proyecto, fase, proveedor, factura, fechas, orden de compra, fuente FI01, categoría, material, unidad, cantidad, subtotal, impuestos, retenciones, descuentos, total, moneda y evidencia.

Estados:

```text
pendiente
aprobado
rechazado
reabierto
pago parcial
pago completo
anulado
reembolsado
revertido
```

### PR01 y CO01

Controle fases, responsables, fechas, presupuesto, costo real, compromisos, contratos, anticipos, retenciones, pagos y saldos.

### MM01, MM02 y MIGO

Registre materiales, solicitudes, cotizaciones, órdenes, recepciones, entradas, consumos, devoluciones, transferencias y ajustes.

El sistema debe bloquear stock negativo, movimientos duplicados, consumos sin proyecto y ajustes sin justificación.

### QC01 y CL01

Registre avance físico, calidad, responsable, fecha, observaciones, alertas, incidencias y evidencias privadas.

Los cierres semanales son idempotentes y muestran saldo inicial, ingresos, gastos, comprometido y saldo final.

### BI01 y AU01

Dashboard, filtros, drill-down y CSV utilizan datos reales y servicios canónicos.

La auditoría registra identidad, rol, acción, módulo, registro, fecha, antes, después, motivo, origen, correlación y huella.

---

## 11. Escritorio, iPhone y PWA

Abra la misma URL HTTPS.

Valide:

```text
login
perfil
dashboard
menú lateral
barra superior
navegación móvil
regresar
cerrar
guardar
cancelar
guardar y nuevo
listas
tablas
filtros
modales
estados vacíos
mensajes
errores
cámara
galería
recarga
cierre y reapertura
```

Instalación en iPhone:

```text
Safari → Compartir → Añadir a pantalla de inicio
```

La PWA no guarda APIs, páginas `/app/`, archivos ni datos privados en caché. Al cambiar la versión de despliegue elimina cachés anteriores y recarga una sola vez.

---

## 12. Respaldo

Crear:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Obtener manifiesto:

```bash
MANIFEST="$(cat "sites/${SITE_NAME}/private/backup-archive/latest-manifest-path")"
echo "$MANIFEST"
```

Verificar:

```bash
python3 apps/erpnext/scripts/verify_backup_manifest.py \
  --manifest "$MANIFEST"
```

El conjunto aprobado debe incluir:

```text
database.sql.gz
archivos públicos
archivos privados
site_config_backup.json
backup-manifest.json
verification.json
```

Cada archivo debe tener tamaño mayor que cero y SHA-256 válido.

No suba respaldos a GitHub.

---

## 13. Restauración en ensayo

Ejecute desde backend:

```bash
MANIFEST="$(cat "sites/${SITE_NAME}/private/backup-archive/latest-manifest-path")"

bash apps/erpnext/deploy/coolify/restore-verify.sh \
  "$MANIFEST" \
  construcontrol-restore-test
```

El script rechaza el nombre productivo, verifica tamaños y SHA-256, crea un sitio aislado, restaura base y archivos, ejecuta tres migraciones, ejecuta el smoke test, reconcilia conteos y genera evidencia.

Para conservar temporalmente el ensayo:

```bash
KEEP_RESTORE_TEST_SITE=true \
bash apps/erpnext/deploy/coolify/restore-verify.sh \
  "$MANIFEST" \
  construcontrol-restore-test
```

---

## 14. Migración histórica

Supabase es únicamente origen histórico.

Archivo de entrada:

```text
construcontrol-supabase-database-AAAAMMDD-HHMMSS.tar.gz
```

Ruta:

```text
/app/construcontrol-migration-console
Botón: Migrar y limpiar demo
```

Secuencia:

1. inventariar origen;
2. validar respaldo y SHA-256;
3. revisar mapa origen-destino;
4. ejecutar simulación;
5. generar backup Bench;
6. importar;
7. conciliar conteos, montos y relaciones;
8. revisar duplicados y huérfanos;
9. repetir para comprobar idempotencia;
10. comprobar rollback.

Deténgase ante montos no conciliados, duplicados sin resolver, relaciones huérfanas, archivos faltantes, respaldo incompleto o rollback inexistente.

Las fotografías históricas no se importan. Se conserva metadata y almacenamiento original; las evidencias nuevas continúan disponibles.

---

## 15. Datos demo

Inventario sin borrado:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.demo_data.inventory_demo_data
```

El resultado clasifica candidatos y cuenta dependencias. No elimina registros.

Antes de eliminar un candidato confirme que es demo, confirme dependencias, cree backup, obtenga aprobación y registre auditoría.

---

## 16. Persistencia y reinicio

Cree un registro de prueba autorizado y anote su identificador.

Reinicie desde Coolify o, en ensayo:

```bash
docker compose restart backend websocket queue-short queue-long scheduler frontend
docker compose ps
```

Compruebe login, registro de prueba, archivos, saldos, inventario, workers, scheduler y WebSocket.

---

## 17. Certificación A, B, C y FINAL

Solicitud:

```text
docs/reconstruction/CERTIFICATION_REQUEST.yml
```

Workflow:

```text
.github/workflows/construcontrol-full-certification.yml
```

Secuencia obligatoria:

```text
Puerta A
→ Puerta B
→ Puerta C
→ FINAL
→ Auditoría independiente 1:1
```

Puerta A ejecuta MariaDB 4/4, finanzas, proyectos, contratos, permisos y cálculos.

Puerta B ejecuta materiales, compras, inventario, avance, calidad, cierres, BI y auditoría.

Puerta C ejecuta PWA, stack completo, reinicio, persistencia, backup y restauración aislada.

FINAL ejecuta validadores, instalación limpia, actualización, tres migraciones, redeploy, backup y restore.

La auditoría 1:1 ejecuta:

```bash
python scripts/audit_requirements_1to1.py
```

No se acepta una puerta fallida, cancelada o sin artifacts.

---

## 18. Solución de errores

### 502

```bash
docker compose ps
docker compose logs --tail=400 frontend backend
bench --site "$SITE_NAME" doctor
```

### 403

Revise proyecto, usuario y rol. No conceda permisos globales para ocultar el defecto.

### 404

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

### Backend unhealthy

```bash
docker compose logs --tail=600 backend
docker compose logs --tail=300 mariadb redis-cache redis-queue
```

No elimine volúmenes.

### Workers o scheduler detenidos

```bash
docker compose logs --tail=400 queue-short queue-long scheduler
bench --site "$SITE_NAME" doctor
```

### Restore fallido

No restaure encima de producción. Conserve el backup, manifiesto, verificación y logs del ensayo.

---

## 19. Criterio de aceptación

No declare aprobado hasta comprobar:

```text
cero errores bloqueantes
cero conflictos con main
todos los cambios publicados
MariaDB 4/4
instalación limpia
actualización sobre base existente
tres migraciones consecutivas
permisos backend
cálculos reconciliados
inventario sin stock negativo
cierres idempotentes
dashboard y reportes reales
auditoría inmutable
escritorio aprobado
iPhone aprobado
PWA aprobada
stack saludable
persistencia tras reinicio
backup completo verificado
restore aislado demostrado
migración conciliada
manual coincidente
Puertas A, B, C y FINAL aprobadas
auditoría independiente 1:1 aprobada
```

La fusión del PR corresponde únicamente al propietario.
