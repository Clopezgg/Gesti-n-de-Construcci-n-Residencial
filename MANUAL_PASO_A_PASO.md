# CONSTRUCONTROL
## Manual completo de instalación gratuita, configuración, uso, migración, respaldo y recuperación

**Plataforma vigente:** Oracle Cloud Always Free + Coolify autogestionado + Docker Compose + GitHub + ERPNext/Frappe 15  
**Repositorio:** `Clopezgg/Gesti-n-de-Construcci-n-Residencial`  
**Rama:** `main`  
**Archivo de despliegue:** `/docker-compose.yml`  
**Versión del manual:** 17 de julio de 2026

> Este manual reemplaza por completo el procedimiento de Render. No use `render.yaml`, no cree un Blueprint y no confirme ningún cargo de Render.

> Avance en orden. Cada bloque termina con un criterio de aprobación. Si el resultado no coincide, deténgase y revise el bloque antes de continuar.

---

# 0. Qué se va a instalar y cuánto cuesta

La arquitectura queda alojada en una sola máquina virtual ARM64 de Oracle Cloud. Dentro de esa máquina se instala Coolify, que funciona como un panel similar a Render, y Coolify despliega todos los contenedores de ConstruControl.

```text
Internet
   |
   v
Coolify Proxy + HTTPS
   |
   v
frontend Nginx :8080
   |--------------------------|
   v                          v
backend Gunicorn :8000     WebSocket :9000
   |
   +--> worker corto
   +--> worker largo
   +--> scheduler
   +--> backup automático
   |
   +--> MariaDB 10.6
   +--> Redis cache
   +--> Redis queue
   +--> volúmenes persistentes
```

## 0.1 Recursos gratuitos que debe seleccionar

En Oracle Cloud seleccione únicamente recursos marcados como **Always Free Eligible**:

- Forma: `VM.Standard.A1.Flex`.
- Arquitectura: ARM64.
- 2 OCPU.
- 12 GB de RAM.
- Ubuntu 24.04 LTS.
- Volumen de arranque recomendado: 100 GB.

Oracle documenta que el total gratuito de Ampere A1 equivale a 2 OCPU y 12 GB de memoria, con hasta 200 GB combinados de almacenamiento en bloque en la región principal. La disponibilidad depende de la capacidad de la región.

## 0.2 Reglas para mantener costo cero

1. No seleccione una forma que no diga **Always Free Eligible**.
2. No cree recursos fuera de la región principal de la cuenta.
3. No agregue balanceadores, bases administradas ni volúmenes que excedan la cuota gratuita.
4. Revise que el estimado indique costo cero antes de crear la instancia.
5. Cree una alerta de presupuesto de `USD 1` para detectar cualquier recurso accidental.
6. No confirme una actualización a pago por consumo si su objetivo es mantener el proyecto exclusivamente gratuito.
7. Use una cuenta que cumpla los requisitos de edad y verificación del proveedor. No intente evadir sus controles.

**Criterio de aprobación:** comprende que el repositorio ya no usa Render y que solo debe continuar con recursos Always Free.

---

# 1. Antes de comenzar

Prepare lo siguiente:

- Acceso administrador al repositorio privado de GitHub.
- Cuenta de Oracle Cloud con región principal seleccionada.
- Computadora Windows con PowerShell.
- Navegador actualizado.
- Gestor de contraseñas.
- Acceso al Supabase anterior, solo si migrará datos históricos.
- Un dominio propio es opcional. Coolify puede generar un dominio gratuito `sslip.io`.

## 1.1 Contraseñas que deberá crear

Necesitará cuatro valores distintos:

| Variable | Uso | ¿Puede cambiarse después? |
|---|---|---|
| `DB_ROOT_PASSWORD` | Administrador interno de MariaDB | No después de crear datos |
| `DB_PASSWORD` | Usuario de la base de ConstruControl | No después de crear datos |
| `ADMIN_PASSWORD` | Primer acceso de `Administrator` | Sí, desde ERPNext |
| `FRAPPE_ENCRYPTION_KEY` | Cifrado de secretos de Frappe | No después de crear datos |

No use la misma contraseña para varias variables.

## 1.2 Generar valores seguros

Más adelante podrá abrir la terminal de Oracle y ejecutar:

```bash
openssl rand -base64 36
openssl rand -base64 36
openssl rand -base64 36
openssl rand -base64 32
```

Guarde cada resultado inmediatamente en el gestor de contraseñas y etiquételo con su variable.

**Criterio de aprobación:** tiene acceso a GitHub, Oracle y un lugar seguro para guardar secretos.

---

# 2. Crear la máquina gratuita en Oracle Cloud

## 2.1 Entrar a Compute

1. Inicie sesión en Oracle Cloud.
2. Abra el menú principal.
3. Entre en **Compute**.
4. Entre en **Instances**.
5. Pulse **Create instance**.

## 2.2 Nombre y ubicación

Use:

```text
Name: construcontrol-produccion
```

Confirme que la instancia se creará en la región principal de la cuenta.

## 2.3 Imagen del sistema operativo

1. En **Image and shape**, pulse **Edit**.
2. En **Image**, seleccione **Canonical Ubuntu**.
3. Seleccione **Ubuntu 24.04 LTS**.
4. Confirme que la arquitectura sea **aarch64 / ARM64**.

No seleccione una imagen x86 para la instancia Ampere.

## 2.4 Forma de la máquina

1. En **Shape**, pulse **Change shape**.
2. Seleccione **Ampere**.
3. Seleccione:

```text
VM.Standard.A1.Flex
```

4. Configure:

```text
OCPU: 2
Memory: 12 GB
```

5. Confirme que aparezca la etiqueta **Always Free Eligible**.

## 2.5 Red

En **Networking**:

1. Seleccione **Create new virtual cloud network** si no tiene una.
2. Seleccione **Create new public subnet**.
3. Active **Assign a public IPv4 address**.
4. Mantenga el puerto SSH 22 habilitado.

Anote después la dirección IPv4 pública de la instancia.

## 2.6 Clave SSH

En **Add SSH keys**:

1. Seleccione **Generate a key pair for me**.
2. Descargue la clave privada.
3. Descargue la clave pública si Oracle lo ofrece.
4. Guarde la clave privada en una carpeta que no comparta públicamente.

Ejemplo de nombre:

```text
construcontrol-oracle.key
```

Nunca suba esa clave a GitHub ni la envíe por chat.

## 2.7 Volumen de arranque

1. Abra **Boot volume**.
2. Seleccione un tamaño de `100 GB`.
3. Confirme que el volumen continúe dentro de la cuota Always Free.
4. No active opciones que indiquen un cargo adicional.

## 2.8 Crear

Antes de pulsar **Create** verifique:

```text
Shape: VM.Standard.A1.Flex
OCPU: 2
RAM: 12 GB
Image: Ubuntu 24.04 ARM64
Public IPv4: Yes
Boot volume: 100 GB
Always Free Eligible: Yes
Estimated cost: 0
```

Pulse **Create** y espere a que el estado sea **Running**.

**Criterio de aprobación:** la instancia está Running, tiene IP pública y todos los recursos seleccionados son Always Free.

---

# 3. Abrir los puertos necesarios en Oracle

Coolify necesita acceso inicial a los siguientes puertos:

| Puerto | Uso | Origen recomendado |
|---:|---|---|
| 22 | SSH | Su IP pública |
| 80 | HTTP y certificados | `0.0.0.0/0` |
| 443 | HTTPS | `0.0.0.0/0` |
| 8000 | Panel inicial Coolify | Su IP pública |
| 6001 | Tiempo real Coolify | Su IP pública |
| 6002 | Terminal Coolify | Su IP pública |

## 3.1 Editar Security List

1. En la instancia abra **Attached VNICs**.
2. Abra la VNIC principal.
3. Abra la subnet.
4. Abra la **Security List** asociada.
5. Pulse **Add Ingress Rules**.

Cree reglas TCP para los puertos anteriores.

Para 80 y 443 utilice:

```text
Source CIDR: 0.0.0.0/0
```

Para 22, 8000, 6001 y 6002 es preferible usar su IP pública en formato `/32`, por ejemplo:

```text
181.000.000.000/32
```

Si su IP cambia y pierde acceso, actualice la regla.

**No abra al público** los puertos 3306, 6379, 8000 del backend ni 9000 del WebSocket. MariaDB y Redis permanecerán dentro de la red Docker.

**Criterio de aprobación:** 80 y 443 están públicos, y los puertos administrativos están limitados a su IP cuando sea posible.

---

# 4. Conectarse por SSH desde Windows

## 4.1 Ubicar la clave

Suponga que la clave está en:

```text
C:\Users\SU_USUARIO\Downloads\construcontrol-oracle.key
```

Abra PowerShell.

## 4.2 Restringir permisos de la clave

Ejecute, sustituyendo la ruta:

```powershell
$Key = "$HOME\Downloads\construcontrol-oracle.key"
icacls $Key /inheritance:r
icacls $Key /grant:r "$env:USERNAME:(R)"
```

## 4.3 Conectarse

Sustituya `IP_PUBLICA`:

```powershell
ssh -i $Key ubuntu@IP_PUBLICA
```

La primera vez escriba:

```text
yes
```

El prompt debe cambiar a algo parecido a:

```text
ubuntu@construcontrol-produccion:~$
```

**Criterio de aprobación:** puede ejecutar comandos dentro de la instancia como usuario `ubuntu`.

---

# 5. Preparar Ubuntu

Ejecute un bloque a la vez.

## 5.1 Actualizar

```bash
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y
sudo apt install -y curl wget git jq openssl ca-certificates ufw
```

## 5.2 Zona horaria

```bash
sudo timedatectl set-timezone America/Tegucigalpa
timedatectl
```

Debe mostrar:

```text
Time zone: America/Tegucigalpa
```

## 5.3 Crear swap de 4 GB

El swap ayuda durante la construcción de la imagen Docker.

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

La salida debe mostrar aproximadamente `4.0Gi` en Swap.

## 5.4 Firewall de Ubuntu

Ejecute:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 6001/tcp
sudo ufw allow 6002/tcp
sudo ufw --force enable
sudo ufw status
```

Las reglas de Oracle continúan siendo la primera barrera. Mantenga también las restricciones por IP en Oracle.

## 5.5 Reinicio recomendado

```bash
sudo reboot
```

Espere dos minutos y vuelva a conectarse:

```powershell
ssh -i $Key ubuntu@IP_PUBLICA
```

**Criterio de aprobación:** Ubuntu está actualizado, la zona horaria es correcta, existe swap y el firewall está activo.

---

# 6. Instalar Coolify gratuitamente

Coolify autogestionado es gratuito. Se instala dentro de la propia VM.

## 6.1 Ejecutar instalador oficial

Desde SSH:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

La instalación puede tardar varios minutos.

## 6.2 Verificar Docker y Coolify

```bash
docker --version
sudo docker ps
```

Debe ver contenedores de Coolify activos.

## 6.3 Abrir el panel

En el navegador abra:

```text
http://IP_PUBLICA:8000
```

Cree inmediatamente la primera cuenta administradora de Coolify. La primera persona que complete ese registro obtiene control del panel.

Use una contraseña larga y única.

## 6.4 Configurar el servidor localhost

1. Entre en **Servers**.
2. Abra **localhost**.
3. Confirme que el servidor aparezca conectado y validado.
4. En **Proxy**, confirme que Traefik esté disponible.

Coolify puede generar dominios gratuitos `sslip.io` si no configura un dominio propio.

**Criterio de aprobación:** puede entrar al panel, el servidor localhost aparece saludable y Docker está operativo.

---

# 7. Generar y guardar los secretos

Desde SSH ejecute cada comando por separado y guarde cada resultado:

```bash
openssl rand -base64 36
```

Guárdelo como:

```text
DB_ROOT_PASSWORD
```

Repita:

```bash
openssl rand -base64 36
```

Guárdelo como:

```text
DB_PASSWORD
```

Repita:

```bash
openssl rand -base64 36
```

Guárdelo como:

```text
ADMIN_PASSWORD
```

Finalmente:

```bash
openssl rand -base64 32
```

Guárdelo como:

```text
FRAPPE_ENCRYPTION_KEY
```

No incluya espacios al copiar. No cambie las dos contraseñas de base ni la clave de cifrado después del primer despliegue.

**Criterio de aprobación:** tiene cuatro valores distintos guardados de forma segura.

---

# 8. Conectar el repositorio privado de GitHub

## 8.1 Crear una fuente GitHub

En Coolify:

1. Abra **Sources**.
2. Pulse **Add**.
3. Seleccione **GitHub App**.
4. Autorice Coolify en su cuenta de GitHub.
5. Permita acceso al repositorio:

```text
Clopezgg/Gesti-n-de-Construcci-n-Residencial
```

6. No autorice repositorios adicionales si no son necesarios.

También existe la opción Deploy Key, pero GitHub App facilita el autodespliegue de `main`.

## 8.2 Verificar rama

La rama correcta es:

```text
main
```

No cree otra rama para este despliegue.

**Criterio de aprobación:** Coolify puede ver el repositorio privado y la rama `main`.

---

# 9. Crear el proyecto en Coolify

## 9.1 Proyecto

1. Abra **Projects**.
2. Pulse **Add**.
3. Nombre:

```text
ConstruControl
```

4. Cree o abra el entorno:

```text
Production
```

## 9.2 Crear recurso

1. Pulse **New Resource**.
2. Seleccione el repositorio privado mediante la GitHub App.
3. Seleccione el repositorio de ConstruControl.
4. Seleccione la rama `main`.

## 9.3 Build Pack

Cambie el Build Pack a:

```text
Docker Compose
```

Configure exactamente:

```text
Base Directory: /
Docker Compose Location: /docker-compose.yml
```

No seleccione Nixpacks. No pegue el antiguo `render.yaml`.

## 9.4 Autodespliegue

Active el autodespliegue para la rama `main` solo después de que el primer despliegue funcione correctamente.

**Criterio de aprobación:** Coolify detecta los 12 servicios del archivo `docker-compose.yml`.

---

# 10. Variables de entorno de Coolify

Abra **Environment Variables** del recurso Docker Compose.

## 10.1 Variables obligatorias

Cree estas variables:

| Variable | Valor |
|---|---|
| `ERPNEXT_VERSION` | `v15.117.0` |
| `SITE_NAME` | `construcontrol` |
| `DB_NAME` | `_construcontrol` |
| `DB_ROOT_PASSWORD` | Valor generado |
| `DB_PASSWORD` | Valor generado diferente |
| `ADMIN_PASSWORD` | Valor generado para Administrator |
| `FRAPPE_ENCRYPTION_KEY` | Valor generado con 32 bytes |
| `TZ` | `America/Tegucigalpa` |
| `SUPABASE_STORAGE_MODE` | `disabled` |

Deje inicialmente:

```text
FRAPPE_EXTERNAL_URL=
```

## 10.2 Ajustes recomendados

```text
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
PROXY_READ_TIMEOUT=120
CLIENT_MAX_BODY_SIZE=50m
BACKUP_LOCAL_HOUR=2
BACKUP_RETENTION_DAYS=14
BACKUP_RUN_ON_START=true
```

## 10.3 Supabase opcional

Para desplegar el ERP sin Supabase deje vacías:

```text
SUPABASE_URL=
SUPABASE_SERVER_KEY=
```

Mantenga:

```text
SUPABASE_STORAGE_MODE=disabled
SUPABASE_STORAGE_BUCKET=construction-evidence
SUPABASE_MIGRATION_BUCKET=construcontrol-migration
SUPABASE_BACKUP_BUCKET=construcontrol-backups
```

Esto significa:

- ERPNext guardará sus archivos nuevos en el volumen persistente `sites`.
- Supabase solo se configurará si necesita migración o una copia remota adicional.

## 10.4 Variables que nunca debe regenerar

Después de la primera creación de datos, no cambie:

```text
DB_ROOT_PASSWORD
DB_PASSWORD
FRAPPE_ENCRYPTION_KEY
SITE_NAME
DB_NAME
```

Cambiar esas variables puede impedir que el sistema abra la base o descifre secretos internos.

**Criterio de aprobación:** no existe ninguna variable obligatoria vacía y Supabase Storage está desactivado por defecto.

---

# 11. Primer despliegue

## 11.1 Iniciar

Pulse **Deploy**.

La primera construcción puede tardar porque el servidor compila la imagen personalizada para ARM64.

## 11.2 Orden esperado

Coolify creará:

```text
mariadb
redis-cache
redis-queue
configurator
init-site
backend
websocket
queue-short
queue-long
scheduler
frontend
backup
```

Los servicios `configurator` e `init-site` deben terminar con código `0`; no deben permanecer ejecutándose.

Los demás servicios deben quedar activos.

## 11.3 Revisar logs

Revise en este orden:

1. `mariadb`: debe indicar que acepta conexiones.
2. `redis-cache`: debe estar listo.
3. `redis-queue`: debe estar listo.
4. `configurator`: debe terminar exitosamente.
5. `init-site`: debe crear el sitio o ejecutar migraciones.
6. `backend`: debe iniciar Gunicorn.
7. `websocket`: debe iniciar Socket.IO.
8. `queue-short` y `queue-long`: deben escuchar colas.
9. `scheduler`: debe permanecer activo.
10. `frontend`: debe iniciar Nginx.
11. `backup`: debe crear una primera copia si `BACKUP_RUN_ON_START=true`.

## 11.4 Errores que obligan a detenerse

Deténgase si aparece:

```text
Required runtime variable is missing
MariaDB did not become ready
A site configuration exists but the database is empty
Access denied for user
No matching manifest for linux/arm64
```

No elimine volúmenes para intentar corregir rápidamente un error.

**Criterio de aprobación:** init-site terminó con éxito y todos los servicios permanentes están en estado Running/Healthy.

---

# 12. Asignar el dominio gratuito y HTTPS

## 12.1 Dominio del servicio frontend

En Coolify abra el servicio:

```text
frontend
```

No asigne dominio a backend, MariaDB, Redis, workers o scheduler.

En el campo de dominio utilice el dominio gratuito generado por Coolify y diríjalo al puerto interno 8080. La interfaz puede mostrar un valor parecido a:

```text
https://identificador.IP_PUBLICA.sslip.io:8080
```

El `:8080` indica a Coolify el puerto interno del contenedor; el usuario final accederá mediante HTTPS estándar.

## 12.2 Esperar certificado

Coolify solicitará y renovará el certificado HTTPS automáticamente.

Espere a que el dominio abra sin advertencia de certificado.

## 12.3 Actualizar URL externa

Copie la URL pública visible, sin `/` final y sin el puerto interno. Ejemplo:

```text
https://identificador.IP_PUBLICA.sslip.io
```

En Environment Variables establezca:

```text
FRAPPE_EXTERNAL_URL=https://identificador.IP_PUBLICA.sslip.io
```

Guarde y haga **Redeploy**.

## 12.4 Cerrar puertos administrativos públicos

Cuando el panel tenga dominio seguro o cuando termine la instalación:

- limite 8000, 6001 y 6002 a su IP;
- mantenga 80 y 443 públicos;
- mantenga 22 limitado a su IP cuando sea posible.

**Criterio de aprobación:** el dominio HTTPS abre el frontend y `FRAPPE_EXTERNAL_URL` coincide exactamente con la URL pública.

---

# 13. Validar el sistema antes de usarlo

## 13.1 Health check

Abra:

```text
https://SU_DOMINIO/api/method/ping
```

Debe responder correctamente.

## 13.2 Iniciar sesión

Abra:

```text
https://SU_DOMINIO
```

Use:

```text
Usuario: Administrator
Contraseña: valor de ADMIN_PASSWORD
```

## 13.3 Verificación desde la terminal de backend

En Coolify abra el servicio `backend`, entre a **Terminal** y ejecute:

```bash
bench --site "$SITE_NAME" list-apps
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

En `list-apps` debe aparecer ERPNext.

## 13.4 Probar servicios

1. Cree una nota o registro de prueba.
2. Actualice la página y confirme que el dato permanece.
3. Suba un PDF o imagen de prueba.
4. Descárguelo.
5. Cierre sesión y confirme que un usuario sin permiso no accede al archivo privado.
6. Revise que los workers no muestren errores repetidos.
7. Revise que scheduler continúe activo.

**Criterio de aprobación:** health check, login, persistencia, adjuntos, worker, scheduler y WebSocket funcionan.

---

# 14. Completar el Setup Wizard de ERPNext

Configure como mínimo:

## 14.1 Idioma y zona

```text
Language: Spanish
Time Zone: America/Tegucigalpa
Country: Honduras
Currency: HNL
```

## 14.2 Compañía

Use el nombre legal o administrativo de la organización familiar responsable de la construcción.

Ejemplo de abreviatura:

```text
CCR
```

## 14.3 Plan de cuentas

Seleccione un plan apropiado para Honduras o cree uno básico. No cargue saldos históricos sin conciliación.

## 14.4 Año fiscal

Configure el año fiscal vigente y su fecha de inicio real.

## 14.5 Almacén y centro de costo

Cree al menos:

```text
Almacén Principal - CCR
Centro de Costo Principal - CCR
```

## 14.6 Cambiar contraseña de Administrator

Después del primer ingreso:

1. Abra el perfil de `Administrator`.
2. Cambie la contraseña.
3. Guarde la nueva contraseña en el gestor.
4. No elimine todavía el valor original de Coolify; podría ser necesario para recrear un entorno vacío, pero no vuelve a cambiar una cuenta ya creada.

**Criterio de aprobación:** compañía, moneda, zona horaria, año fiscal, almacén y centro de costo están configurados.

---

# 15. Configurar ConstruControl

En la barra de búsqueda de ERPNext escriba:

```text
ConstruControl Settings
```

Configure:

- Compañía predeterminada.
- Proyecto predeterminado, cuando exista.
- Almacén predeterminado.
- Centro de costo predeterminado.
- Modo inicial de migración: `Preserve Only`.

No habilite creación masiva de documentos estándar hasta terminar el ensayo y la conciliación de la migración.

## 15.1 Roles incluidos

Asigne usuarios según su función:

| Rol | Uso recomendado |
|---|---|
| `ConstruControl Manager` | Administración funcional y configuración |
| `ConstruControl Operator` | Registro diario y seguimiento |
| `ConstruControl Auditor` | Consulta, conciliación y auditoría |
| `ConstruControl Viewer` | Lectura sin edición |

No entregue `Administrator` a usuarios operativos.

## 15.2 Prueba de permisos

Cree una cuenta de prueba para cada rol y confirme:

- Viewer no edita.
- Auditor no cambia transacciones.
- Operator registra sin administrar configuración.
- Manager administra ConstruControl.
- Usuario sin permisos no ve documentos restringidos.

**Criterio de aprobación:** ConstruControl Settings está completo y los permisos funcionan sin depender de Administrator.

---

# 16. Uso diario del sistema

## 16.1 Crear el proyecto de construcción

1. Busque **Project**.
2. Pulse **New**.
3. Defina nombre, compañía, fechas y estado.
4. Guarde.
5. Regrese a **ConstruControl Settings** y selecciónelo como proyecto predeterminado si corresponde.

## 16.2 Fases y tareas

Use **Task** para fases, actividades y pendientes. Defina:

- asunto claro;
- proyecto;
- fecha esperada de inicio;
- fecha esperada de finalización;
- estado;
- progreso;
- descripción y evidencia.

## 16.3 Proveedores y contratos

1. Registre cada proveedor antes de asociar compras o contratos.
2. Evite duplicados por variaciones de nombre.
3. Adjunte identidad, contrato y comprobantes solo con permisos adecuados.
4. Use Contract para formalizar condiciones y vigencia.

## 16.4 Materiales e inventario

1. Cree Item para cada material controlado.
2. Defina unidad de medida correcta.
3. Use el almacén del proyecto.
4. Registre entradas y salidas mediante documentos de inventario.
5. No modifique saldos directamente en la base de datos.

## 16.5 Compras y gastos

Use los documentos estándar de ERPNext según el nivel de control requerido:

- Material Request.
- Purchase Order.
- Purchase Receipt.
- Purchase Invoice.
- Payment Entry.

Adjunte cotizaciones, facturas y recibos al documento correspondiente.

## 16.6 Evidencias

Los archivos nuevos se guardan por defecto en el volumen persistente `sites` porque:

```text
SUPABASE_STORAGE_MODE=disabled
```

Use archivos privados cuando contengan información sensible. Pruebe siempre la descarga con un usuario no administrador.

## 16.7 Revisión semanal

Cada semana revise:

- tareas vencidas;
- avance por fase;
- compras pendientes;
- materiales recibidos y utilizados;
- compromisos con proveedores;
- respaldo más reciente;
- errores de backend, workers y scheduler.

---

# 17. Respaldos automáticos

El servicio `backup` ejecuta una copia al iniciar y después diariamente.

Configuración predeterminada:

```text
BACKUP_LOCAL_HOUR=2
BACKUP_RETENTION_DAYS=14
BACKUP_RUN_ON_START=true
TZ=America/Tegucigalpa
```

## 17.1 Qué guarda

`bench backup --with-files` genera:

- base de datos comprimida;
- archivos públicos;
- archivos privados;
- configuración cuando corresponda.

Luego `archive_backup_set.py` copia el conjunto al volumen `/backups` y crea:

```text
backup-manifest.json
```

Cada archivo incluye tamaño y SHA-256.

## 17.2 Ejecutar respaldo manual

Desde la terminal del servicio `backend`:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

## 17.3 Ver respaldos

Desde terminal de `backend`:

```bash
find /backups -name backup-manifest.json -type f | sort
```

Para ver el más reciente:

```bash
LATEST="$(find /backups -name backup-manifest.json -type f | sort | tail -n 1)"
echo "$LATEST"
cat "$LATEST"
```

## 17.4 Verificar SHA-256

```bash
python3 apps/erpnext/scripts/verify_backup_manifest.py "$LATEST"
```

Resultado correcto:

```text
"errors": []
```

## 17.5 Copia de volumen de Oracle

Como protección adicional:

1. En Oracle abra **Storage > Block Storage > Boot Volumes**.
2. Abra el volumen de la instancia.
3. Cree un backup del volumen.
4. Mantenga como máximo la cantidad incluida en Always Free.
5. Elimine el más antiguo antes de superar el límite.

Una copia Bench permite restaurar la aplicación; una copia del volumen protege toda la VM.

## 17.6 Prohibición crítica

Nunca ejecute:

```bash
docker compose down -v
```

La opción `-v` elimina volúmenes y puede destruir MariaDB, archivos y respaldos.

**Criterio de aprobación:** existe al menos un manifiesto validado y una estrategia de copia de volumen.

---

# 18. Actualizar el sistema desde GitHub

## 18.1 Antes de actualizar

Desde backend:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Verifique el manifiesto.

## 18.2 Desplegar nuevo commit

Si Autodeploy está activo, Coolify desplegará cuando `main` cambie. También puede pulsar **Redeploy** manualmente.

El servicio `init-site` detecta una base existente y ejecuta:

```bash
bench --site "$SITE_NAME" migrate
```

No borra la base ni usa `--force`.

## 18.3 Después de actualizar

Ejecute:

```bash
bench --site "$SITE_NAME" doctor
bench --site "$SITE_NAME" clear-cache
```

Pruebe login, creación de un registro, archivos, workers y scheduler.

---

# 19. Supabase opcional para migración o copia remota

Esta sección solo es necesaria si migrará el sistema anterior o desea una copia remota adicional.

## 19.1 Separar origen y destino

| Proyecto | Uso | Regla |
|---|---|---|
| Supabase de origen | Datos del sistema anterior | Solo lectura y exportación |
| Supabase de destino opcional | ZIP de migración y copias remotas | Puede modificarse |

No ejecute el SQL de destino en el origen.

## 19.2 Crear proyecto de destino

En Supabase cree un proyecto nuevo dentro del plan disponible. Guarde:

```text
SUPABASE_URL
SUPABASE_SERVER_KEY
```

La clave debe ser server-only, preferentemente `sb_secret_...`.

## 19.3 SQL completo para los buckets privados

En el Supabase de destino:

1. Abra **SQL Editor**.
2. Pulse **New query**.
3. Pegue todo el código.
4. Pulse **Run**.

```sql
-- ConstruControl destination Storage setup.
-- Run this ONLY in the Supabase project used by the new ERPNext deployment,
-- after taking a database backup. Do not run it in the legacy source project.
--
-- Security model: browser clients never receive a Supabase server key and never
-- access these buckets directly. ERPNext is the authorization boundary and uses
-- a server-only sb_secret_ key (or a temporary legacy service_role key) to bypass
-- Storage RLS. Therefore this script intentionally creates NO anon/authenticated
-- policies for the three buckets.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  (
    'construction-evidence',
    'construction-evidence',
    false,
    12582912,
    array['image/jpeg', 'image/png', 'image/webp', 'application/pdf']::text[]
  ),
  (
    'construcontrol-migration',
    'construcontrol-migration',
    false,
    2147483648,
    array['application/zip', 'application/x-zip-compressed', 'application/octet-stream']::text[]
  ),
  (
    'construcontrol-backups',
    'construcontrol-backups',
    false,
    5368709120,
    array[
      'application/gzip',
      'application/x-gzip',
      'application/x-tar',
      'application/json',
      'application/octet-stream'
    ]::text[]
  )
on conflict (id) do update set
  name = excluded.name,
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Remove only obsolete ConstruControl policies created by earlier project drafts.
-- No replacement client policies are created: direct browser access remains denied.
drop policy if exists "ConstruControl evidence public read" on storage.objects;
drop policy if exists "ConstruControl evidence authenticated read" on storage.objects;
drop policy if exists "ConstruControl evidence upload" on storage.objects;
drop policy if exists "ConstruControl evidence update" on storage.objects;
drop policy if exists "ConstruControl evidence delete" on storage.objects;
drop policy if exists "ConstruControl migration access" on storage.objects;
drop policy if exists "ConstruControl backup access" on storage.objects;

-- Fail immediately if any managed bucket is public.
do $$
begin
  if exists (
    select 1
    from storage.buckets
    where id in ('construction-evidence', 'construcontrol-migration', 'construcontrol-backups')
      and public is true
  ) then
    raise exception 'One or more ConstruControl buckets are public; aborting.';
  end if;
end
$$;

-- Expected result: three rows, all with public = false.
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
where id in ('construction-evidence', 'construcontrol-migration', 'construcontrol-backups')
order by id;

-- Expected result for a clean destination project: zero policies whose SQL
-- expression references a ConstruControl bucket. Any returned row must be reviewed.
select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
  and coalesce(qual, '') || coalesce(with_check, '') ~
      '(construction-evidence|construcontrol-migration|construcontrol-backups)'
order by policyname;
```

La primera consulta debe mostrar tres buckets con `public=false`. La segunda debe devolver cero políticas permisivas en un proyecto limpio.

## 19.4 Agregar variables a Coolify

Solo después de crear el destino:

```text
SUPABASE_URL=https://PROYECTO.supabase.co
SUPABASE_SERVER_KEY=sb_secret_...
SUPABASE_MIGRATION_BUCKET=construcontrol-migration
SUPABASE_BACKUP_BUCKET=construcontrol-backups
```

Mantenga:

```text
SUPABASE_STORAGE_MODE=disabled
```

De esta forma Supabase ayuda con migración y copia remota, pero los archivos diarios permanecen en el volumen persistente del ERP.

---

# 20. Exportar el sistema anterior

Este bloque se realiza en su computadora Windows.

## 20.1 Descargar repositorio

Abra PowerShell:

```powershell
cd $HOME\Desktop
git clone https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial.git
cd Gesti-n-de-Construcci-n-Residencial
git checkout main
git pull origin main
```

## 20.2 Instalar dependencia de validación

```powershell
python -m pip install PyYAML==6.0.2
```

## 20.3 Validar repositorio

```powershell
python scripts\validate_repository.py
python erpnext\construcontrol\tests\test_schema_standalone.py -v
```

Resultado esperado:

```text
Repository validation: 0 error(s)
```

## 20.4 Definir credenciales del origen

```powershell
$env:SUPABASE_URL = "https://PROYECTO-ORIGEN.supabase.co"
$env:SUPABASE_SERVER_KEY = "CLAVE-SECRETA-DEL-ORIGEN"
$env:SUPABASE_PROJECT_ID = ""
```

Las variables duran solo en esa ventana de PowerShell.

## 20.5 Exportar

```powershell
Remove-Item -Recurse -Force migration-output\source-export -ErrorAction SilentlyContinue
python scripts\export_supabase_snapshot.py migration-output\source-export
```

Debe terminar con:

```text
failed_files: 0
```

## 20.6 Validar

```powershell
python scripts\validate_construcontrol_backup.py `
  migration-output\source-export\construcontrol-supabase-export.json `
  --report migration-output\source-export\preflight-report.json
```

No continúe con duplicados, relaciones huérfanas o archivos fallidos.

## 20.7 Crear ZIP verificable

```powershell
python scripts\create_migration_bundle.py `
  migration-output\source-export `
  migration-output\construcontrol-migration.zip
```

Guarde el SHA-256 mostrado.

---

# 21. Subir el paquete y ejecutar ensayo

## 21.1 Cambiar variables a Supabase de destino

```powershell
$env:SUPABASE_URL = "https://PROYECTO-DESTINO.supabase.co"
$env:SUPABASE_SERVER_KEY = "sb_secret_<COPIAR_DESDE_SUPABASE>"
$objectKey = "incoming/construcontrol-migration-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
```

## 21.2 Subir

```powershell
python scripts\supabase_storage_transfer.py upload `
  migration-output\construcontrol-migration.zip `
  --bucket construcontrol-migration `
  --object $objectKey `
  --content-type application/zip
```

Copie el `object_key` exacto.

## 21.3 Ensayo desde Coolify

Abra terminal del servicio `backend` y ejecute, sustituyendo la ruta:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/RUTA-EXACTA.zip","dry_run":true,"source_kind":"Supabase Export"}'
```

Abra en ERPNext:

```text
ConstruControl Migration Run
ConstruControl Migration Reconciliation
```

Deténgase si hay:

- diferencias de SHA-256;
- archivos ausentes;
- duplicados;
- relaciones huérfanas;
- advertencias no justificadas;
- fallos de mapeo.

---

# 22. Respaldo e importación real

## 22.1 Respaldo obligatorio

Desde backend:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Localice el manifiesto más reciente:

```bash
LATEST="$(find /backups -name backup-manifest.json -type f | sort | tail -n 1)"
echo "$LATEST"
python3 apps/erpnext/scripts/verify_backup_manifest.py "$LATEST"
```

No continúe si `errors` no está vacío.

## 22.2 Importación real

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"incoming/RUTA-EXACTA.zip","dry_run":false,"source_kind":"Supabase Export","backup_reference":"RUTA_DEL_BACKUP_MANIFEST.json"}'
```

Use la ruta exacta de `$LATEST` como `backup_reference`, o la clave remota si se cargó una copia a Supabase.

## 22.3 Conciliación

Verifique:

```text
input = preserved
mapped + preserved_only = preserved
archivos verificados = adjuntados + rechazados justificados
mapping_failures = 0
```

Compare también:

- proyectos;
- fases y tareas;
- proveedores;
- contratos;
- materiales;
- fondos y movimientos;
- archivos;
- usuarios y permisos.

No cierre la migración mientras existan diferencias no explicadas.

---

# 23. Rollback y restauración

## 23.1 Rollback lógico

Solo antes de que los usuarios creen movimientos nuevos:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.importer.rollback \
  --kwargs '{"migration_run":"CC-MIG-2026-00001"}'
```

Este rollback elimina únicamente borradores creados por esa corrida y conserva auditoría.

## 23.2 Restauración total

1. Detenga temporalmente backend, workers y scheduler desde Coolify.
2. Abra terminal de backend.
3. Verifique el manifiesto:

```bash
python3 apps/erpnext/scripts/verify_backup_manifest.py /backups/RUTA/backup-manifest.json
```

4. Identifique los nombres exactos de base, archivos públicos y privados dentro del manifiesto.
5. Restaure usando esos archivos:

```bash
bench --site "$SITE_NAME" restore /backups/RUTA/database.sql.gz \
  --with-public-files /backups/RUTA/files.tar \
  --with-private-files /backups/RUTA/private-files.tar
bench --site "$SITE_NAME" migrate
bench --site "$SITE_NAME" clear-cache
```

Los nombres reales pueden contener fechas o extensiones distintas. No invente nombres: use el manifiesto.

6. Reinicie los servicios.
7. Pruebe primero en un entorno aislado cuando sea posible.

---

# 24. Solución de problemas

## 24.1 Oracle dice Out of host capacity

La región no tiene capacidad Ampere gratuita en ese momento.

- pruebe otro Availability Domain dentro de la región principal;
- vuelva a intentar más tarde;
- no seleccione una forma pagada para continuar.

## 24.2 No abre Coolify en el puerto 8000

Revise:

```bash
sudo docker ps
sudo ufw status
```

Confirme reglas de Oracle para 8000, 6001 y 6002 desde su IP.

## 24.3 Build falla con no matching manifest for linux/arm64

1. Confirme que la instancia es ARM64.
2. Confirme que usa el Dockerfile actualizado de `main`.
3. Revise que GitHub Actions ARM64 haya pasado.
4. No agregue `platform: linux/amd64` al Compose.

## 24.4 MariaDB no inicia

Revise logs de `mariadb`. Confirme que `DB_ROOT_PASSWORD` está definida y no fue cambiada después del primer inicio.

## 24.5 init-site falla con Access denied

Confirme:

```text
DB_ROOT_PASSWORD
DB_PASSWORD
DB_NAME=_construcontrol
SITE_NAME=construcontrol
```

No elimine el volumen para probar otra contraseña.

## 24.6 Site not found

Confirme:

```text
SITE_NAME=construcontrol
FRAPPE_SITE_NAME_HEADER=construcontrol
```

El Compose configura el header del frontend desde `SITE_NAME`.

## 24.7 Error 502

Revise en orden:

1. `mariadb`.
2. `redis-cache`.
3. `redis-queue`.
4. `init-site`.
5. `backend`.
6. `websocket`.
7. `frontend`.

## 24.8 El dominio no obtiene HTTPS

Confirme que 80 y 443 están abiertos en Oracle y UFW. Espere la propagación del dominio `sslip.io` o del DNS propio.

## 24.9 Archivo no permanece después del redeploy

Confirme que `frontend`, `backend` y workers montan:

```text
sites:/home/frappe/frappe-bench/sites
```

No cambie el nombre del volumen.

## 24.10 Backup no aparece

Revise logs del servicio `backup` y ejecute manualmente:

```bash
bash apps/erpnext/deploy/coolify/backup-now.sh
```

Confirme que backend y backup montan `/backups`.

## 24.11 Se queda sin espacio

Desde SSH:

```bash
df -h
docker system df
```

Use la limpieza automática de Coolify para imágenes y caché. No elimine volúmenes en uso.

---

# 25. Rutina operativa recomendada

## Diario

- confirmar que el sistema abre;
- revisar errores críticos;
- confirmar workers y scheduler;
- verificar que no exista alerta de espacio.

## Semanal

- revisar tareas, compras y archivos;
- verificar el último respaldo;
- ejecutar `doctor`;
- revisar usuarios y permisos nuevos.

## Mensual

- descargar o probar un respaldo;
- crear o rotar una copia de volumen Oracle sin superar el límite gratuito;
- actualizar Ubuntu y Coolify en una ventana controlada;
- verificar uso de CPU, RAM y disco;
- revisar presupuesto y confirmar costo cero.

## Antes de cada migración o cambio importante

1. respaldo manual;
2. verificar manifiesto;
3. registrar commit actual de GitHub;
4. desplegar;
5. validar health, login, permisos y archivos.

---

# 26. Lista final de prohibiciones

- No usar Render para esta arquitectura.
- No crear un Blueprint.
- No confirmar planes pagados.
- No usar una forma Oracle sin etiqueta Always Free Eligible.
- No publicar MariaDB ni Redis.
- No subir secretos a GitHub.
- No usar `anon` o `publishable` como clave de servidor.
- No cambiar `DB_PASSWORD` ni `FRAPPE_ENCRYPTION_KEY` después de crear datos.
- No ejecutar SQL de destino en el Supabase de origen.
- No importar sin dry run y respaldo.
- No ejecutar `docker compose down -v`.
- No eliminar volúmenes desde Coolify para corregir un error.
- No afirmar que una Action verde sustituye una prueba real de despliegue y restauración.

---

# 27. Criterio de puesta en producción

ConstruControl solo está listo para uso real cuando todos estos puntos sean verdaderos:

- Oracle muestra recursos Always Free y costo cero.
- Coolify está protegido por contraseña y HTTPS.
- El repositorio conectado es el privado correcto en `main`.
- El Compose detecta 12 servicios.
- MariaDB y Redis no están expuestos.
- init-site terminó correctamente.
- health check responde.
- Administrator puede entrar.
- roles no administrativos fueron probados.
- los datos sobreviven al refresh y redeploy.
- los archivos privados respetan permisos.
- workers, scheduler y WebSocket funcionan.
- existe un respaldo con manifiesto SHA-256 validado.
- la restauración fue ensayada o planificada con archivos identificados.
- cualquier migración fue conciliada sin diferencias pendientes.

---

# Fuentes técnicas oficiales consultadas

- Oracle Cloud Infrastructure Free Tier y Always Free Resources.
- Coolify: Installation, Docker Compose, GitHub Integration, Domains, Firewall y Server Introduction.
- Frappe Docker: producción, ARM64, servicios y operaciones.
