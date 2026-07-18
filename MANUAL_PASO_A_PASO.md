# CONSTRUCONTROL
## Manual técnico y operativo de producción

**Arquitectura vigente:** AWS EC2 x86_64 + Ubuntu + Coolify + Docker Compose + GitHub + ERPNext/Frappe 15  
**Repositorio:** `Clopezgg/Gesti-n-de-Construcci-n-Residencial`  
**Rama:** `main`  
**Despliegue:** `/docker-compose.yml`  
**Zona horaria:** `America/Tegucigalpa`

Este manual reemplaza los procedimientos anteriores de Render y Oracle. Supabase es únicamente el origen histórico o una copia remota opcional. La base productiva es MariaDB dentro de AWS.

## 1. Comprobar AWS EC2

Abra:

```text
AWS Console → EC2 → Instances → instancia de ConstruControl
```

Resultado esperado:

```text
State: Running
Architecture: x86_64
Public IPv4: asignada
Private IPv4: asignada
```

Abra el Security Group desde:

```text
EC2 → Instance → Security → Security groups → Edit inbound rules
```

Mantenga 80 y 443 públicos. Limite 22, 8000, 6001 y 6002 al acceso administrativo controlado. No publique 3306, 6379 ni 9000.

## 2. Entrar al servidor

Mediante navegador:

```text
EC2 → Instances → Connect → EC2 Instance Connect → Connect
```

El prompt debe comenzar con:

```text
ubuntu@ip-
```

Mediante PowerShell, desde la laptop:

```powershell
$Key = "$HOME\Downloads\NOMBRE-DE-LA-LLAVE.pem"
icacls $Key /inheritance:r
icacls $Key /grant:r "$env:USERNAME:(R)"
ssh -i $Key ubuntu@IP_PUBLICA_EC2
```

## 3. Comprobar Docker y Coolify

En EC2:

```bash
docker --version
sudo docker info
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Abra el panel administrativo:

```text
http://IP_PUBLICA_EC2:8000
```

Esa dirección es el panel de Coolify, no la URL pública final del sistema.

## 4. Configurar el repositorio en Coolify

Abra:

```text
Coolify → Projects → ConstruControl → Application → Source
```

Configure:

```text
Repository: Clopezgg/Gesti-n-de-Construcci-n-Residencial
Branch: main
Base Directory: /
Build Pack: Docker Compose
Docker Compose Location: /docker-compose.yml
```

No utilice un ZIP antiguo como fuente productiva.

## 5. Variables de entorno

Abra:

```text
Application → Environment Variables
```

Configure, con valores guardados en un gestor de contraseñas:

```text
ERPNEXT_VERSION=v15.117.0
SITE_NAME=construcontrol
DB_NAME=_construcontrol
DB_PASSWORD=<VALOR_PRIVADO>
DB_ROOT_PASSWORD=<VALOR_PRIVADO>
ADMIN_PASSWORD=<VALOR_PRIVADO>
FRAPPE_ENCRYPTION_KEY=<VALOR_PRIVADO>
FRAPPE_EXTERNAL_URL=https://DOMINIO_PUBLICO
TZ=America/Tegucigalpa
BACKUP_LOCAL_HOUR=2
BACKUP_RETENTION_DAYS=14
BACKUP_RUN_ON_START=false
SUPABASE_STORAGE_MODE=disabled
```

No regenere `DB_PASSWORD`, `DB_ROOT_PASSWORD` o `FRAPPE_ENCRYPTION_KEY` después de crear datos. No ponga claves `anon`, `publishable`, `VITE_` ni claves de servicio en JavaScript.

## 6. Desplegar desde GitHub

Antes de actualizar una instalación con datos, abra la terminal del servicio `backend` y ejecute:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Después pulse:

```text
Application → Deploy / Redeploy
```

El log correcto para una base existente incluye:

```text
Existing ERPNext database detected. Running migrations.
```

El backend ejecuta `start-backend.sh`, luego `init-site.sh`, después `bench migrate` y finalmente Gunicorn. Si detecta configuración de sitio con una base vacía, se detiene y no sobrescribe datos.

## 7. Comprobar los servicios

En Coolify deben estar activos:

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

Desde backend:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" clear-cache
```

Por la URL pública pruebe:

```text
https://DOMINIO_PUBLICO/api/method/ping
```

No continúe ante errores 500, 502 o servicios `unhealthy`.

## 8. Configurar ERPNext

Inicie sesión como `Administrator` y complete:

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

No seleccione datos de demostración.

## 9. Configurar ConstruControl

En la búsqueda escriba:

```text
ConstruControl Settings
```

Configure:

```text
Default Company: compañía real
Default Project: proyecto real cuando exista
Default Warehouse: almacén real
Default Cost Center: centro de costo real
Require backup before import: activado
Cleanup demo after migration: activado
Import historical evidence files: desactivado
```

Las fotografías históricas no se importan. La carga de evidencias nuevas sigue disponible para la operación futura.

## 10. Migrar el sistema original

Archivo requerido:

```text
construcontrol-supabase-database-AAAAMMDD-HHMMSS.tar.gz
```

No seleccione por separado `roles.sql`, `schema.sql` o `data.sql`.

Abra:

```text
ConstruControl → MIG · Migración segura
```

Ruta directa:

```text
/app/construcontrol-migration-console
```

Procedimiento:

1. Pulse **Seleccionar y validar respaldo**.
2. Seleccione el archivo `.tar.gz`.
3. Espere **VALIDACIÓN APROBADA**.
4. Confirme cantidades, totales, relaciones y `Imágenes a importar: 0`.
5. Deténgase si aparecen duplicados sin resolver, relaciones huérfanas o diferencias de conciliación.
6. Pulse **Migrar y limpiar demo**.
7. Escriba exactamente `MIGRAR`.
8. Pulse **Ejecutar migración**.
9. No cierre la pestaña.

La operación verifica SHA-256, crea un respaldo Bench, importa, concilia, conserva el registro original, omite fotografías históricas e inicia la limpieza oficial de DEMO.

Solo `System Manager` puede ejecutar la migración.

## 11. Comprobar la migración

Revise:

```text
FI01 Fondos e ingresos
FI02 Gastos y facturas
CO01 Contratos
PR01 Fases
MM01 Materiales
MIGO Movimientos
QC01 Avance
CL01 Cierres
AU01 Auditoría
US01 Usuarios
```

Confirme:

- cada gasto está ligado a la fuente correcta;
- los saldos FI01 se recalculan;
- contratos conservan valor, pagado y saldo;
- inventario no queda negativo;
- auditoría separa nombre, correo, rol e identificador;
- registros anulados permanecen trazables;
- imágenes históricas importadas son cero;
- productos y empresas DEMO ya no aparecen.

Abra `ConstruControl Migration Run`. La ejecución real debe mostrar:

```text
Dry Run: No
Status: Completed o Completed with Warnings justificadas
Backup Reference: no vacío
Input Counts y Output Counts: conciliados
```

## 12. Roles

| Rol | Permiso |
|---|---|
| System Manager | administración técnica y migración |
| ConstruControl Manager | administración funcional sin borrar trazabilidad |
| ConstruControl Operator | registro operativo sin configuración crítica |
| ConstruControl Auditor | lectura, impresión y exportación sin editar |
| ConstruControl Viewer | lectura permitida |

Pruebe una cuenta por rol. El backend debe negar acceso no autorizado aunque alguien escriba una URL directamente.

## 13. Flujo diario

### FI01

Abra `FI01`, pulse `Add`, registre tipo, estado, fecha, monto, remitente, remesadora, banco y referencia. Guarde y compruebe recibido, gastado, pendiente y disponible.

### FI02

Abra `FI02`, pulse `Add`, seleccione proyecto, fase, proveedor y fuente FI01. Registre categoría, unidad, cantidad y monto. Adjunte evidencia nueva cuando corresponda. Guarde y compruebe el nuevo saldo FI01.

### Inventario

Cree materiales reales de construcción en MM01. Registre entrada, consumo o ajuste en MIGO. El sistema debe bloquear una salida superior a la existencia.

### Avance y cierre

Registre avance por fase en QC01. Cree el cierre semanal en CL01 y compare saldo inicial, ingresos, gastos y saldo final.

## 14. Uso móvil

Abra la misma URL HTTPS en el teléfono. Compruebe navegación inferior, formularios en una columna, botones táctiles, carga de evidencia nueva desde cámara o galería, mensajes claros y persistencia después de actualizar.

El manifest de ConstruControl permite agregar el acceso a la pantalla de inicio cuando el navegador y HTTPS lo admiten. Escritorio y teléfono utilizan el mismo backend y la misma base.

## 15. Respaldos

Crear respaldo manual:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Listar copias:

```bash
find "sites/${SITE_NAME}/private/backups" -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
find "sites/${SITE_NAME}/private/backup-archive" -maxdepth 2 -type f -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
```

Calcular hash:

```bash
sha256sum "RUTA_EXACTA_DEL_ARCHIVO"
```

No suba respaldos a GitHub.

## 16. Restauración en ensayo

Pruebe la restauración en un sitio aislado con la misma versión:

```bash
bench --site SITIO_DE_PRUEBA restore RUTA_DATABASE_SQL_GZ --with-public-files RUTA_PUBLIC_FILES_TGZ --with-private-files RUTA_PRIVATE_FILES_TGZ
bench --site SITIO_DE_PRUEBA migrate
bench --site SITIO_DE_PRUEBA clear-cache
```

Después pruebe login, roles, conteos, archivos, workers, scheduler y WebSocket. No restaure directamente encima de producción sin validar primero el ensayo.

## 17. Solución de errores

### 502

Revise `frontend`, `backend` y el health check. Ejecute:

```bash
bench --site "$SITE_NAME" doctor
```

### 403

Revise el rol asignado. No conceda permisos globales para ocultar el problema.

### Página ConstruControl 404

```bash
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

Luego recargue con `Ctrl + Shift + R`.

### DEMO continúa visible

Abra el último `ConstruControl Migration Run` y revise `Error Log`. No borre registros uno por uno sin identificar la compañía demo y sus transacciones.

### Redeploy sin datos

Detenga operaciones. No elimine volúmenes. Confirme que `mariadb-data` y `sites` siguen montados y restaure únicamente una copia verificada.

## 18. Criterio de aceptación

No declare terminado el sistema hasta comprobar:

```text
main aprobado
imagen linux/amd64 construida
Coolify desplegado desde GitHub
HTTPS funcional
login y roles probados
FI01 y FI02 recalculan saldos
inventario bloquea stock negativo
auditoría separa identidad y rol
DEMO eliminado
una sola sección de Integraciones
escritorio y celular probados
workers, scheduler y WebSocket activos
respaldo generado
restauración probada
persistencia después de reinicio y redeploy
```

Una compilación o una GitHub Action verde no sustituyen estas pruebas reales.
