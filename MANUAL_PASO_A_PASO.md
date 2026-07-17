# ConstruControl: manual operativo paso a paso

**Versión:** 17 de julio de 2026  
**Rama de despliegue:** `main`  
**Objetivo:** desplegar ERPNext/ConstruControl en Render, conectar un Supabase de destino, migrar los datos del sistema anterior y conservar respaldos fuera del filesystem efímero.

> Este manual es lineal. No avances al bloque siguiente hasta cumplir el criterio de aprobación del bloque actual.

## 0. Antes de tocar nada

Vas a trabajar con **dos proyectos Supabase distintos** durante la migración:

| Nombre en este manual | Uso | ¿Se modifica? |
|---|---|---|
| **Supabase de origen** | Contiene los datos y evidencias del sistema anterior | Solo lectura/exportación |
| **Supabase de destino** | Almacenamiento privado del nuevo ERPNext, paquetes de migración y respaldos | Sí |

No ejecutes el SQL de este manual en el Supabase de origen. El Blueprint de Render crea varios recursos pagados: MariaDB, Redis, backend, WebSocket, worker, scheduler, frontend y un cron diario de respaldo. Revisa el resumen de costos antes de confirmar.

Ten disponibles:

- Acceso administrador al repositorio privado de GitHub.
- Cuenta de Render con método de pago.
- Acceso administrador al Supabase de origen.
- Un proyecto Supabase nuevo o vacío para destino.
- PowerShell y Python 3.10 o superior en tu computadora.
- Un gestor de contraseñas.

## 1. Descargar y validar el repositorio

### 1.1 Abrir PowerShell

En Windows, abre **PowerShell** y ejecuta:

```powershell
cd $HOME\Desktop
git clone https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial.git
cd Gesti-n-de-Construcci-n-Residencial
git checkout main
git pull origin main
```

### 1.2 Instalar la única dependencia de validación local

```powershell
python -m pip install PyYAML==6.0.2
```

### 1.3 Ejecutar validaciones

```powershell
python scripts\validate_repository.py
python erpnext\construcontrol\tests\test_schema_standalone.py -v
```

Resultado esperado:

```text
Repository validation: 0 error(s)
```

**Detente** si aparece cualquier error.

## 2. Preparar el Supabase de destino

### 2.1 Crear o seleccionar el proyecto correcto

1. Entra a Supabase.
2. Abre el proyecto nuevo que será usado por ERPNext.
3. Confirma visualmente que **no es el proyecto del sistema anterior**.
4. Ve a **SQL Editor**.
5. Pulsa **New query**.
6. Copia y pega **todo** el siguiente código.
7. Pulsa **Run** una sola vez.

### 2.2 Código SQL completo

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
-- expression references a ConstruControl bucket. Any returned row must be
-- reviewed before production.
select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
  and coalesce(qual, '') || coalesce(with_check, '') ~
      '(construction-evidence|construcontrol-migration|construcontrol-backups)'
order by policyname;
```

### 2.3 Verificar el resultado

La primera tabla de resultados debe mostrar exactamente estos tres buckets y todos deben tener `public = false`:

- `construction-evidence`
- `construcontrol-migration`
- `construcontrol-backups`

La segunda consulta debe devolver **cero políticas** relacionadas con esos buckets en un proyecto de destino limpio.

**Detente** si alguno aparece público o si existe una política que conceda acceso directo a `anon` o `authenticated`.

## 3. Obtener las dos variables de Supabase de destino

En el Supabase de destino:

1. Abre **Project Settings**.
2. Abre **API Keys**.
3. Copia la URL del proyecto, por ejemplo `https://abcxyz.supabase.co`.
4. En **Secret keys**, crea o copia una clave que comience con `sb_secret_`.
5. Guarda ambos valores en tu gestor de contraseñas.

No uses la clave `publishable`, `anon` ni una variable con prefijo `VITE_`. La clave de servidor nunca debe pegarse en GitHub, capturas, chats públicos o JavaScript del navegador.

## 4. Crear el Blueprint en Render

### 4.1 Conectar el repositorio

1. Entra al Dashboard de Render.
2. Pulsa **New**.
3. Selecciona **Blueprint**.
4. Conecta GitHub.
5. Autoriza el repositorio privado `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
6. Selecciona la rama `main`.
7. Confirma que la ruta del Blueprint sea `render.yaml`.
8. Revisa todos los recursos y costos antes de confirmar.

### 4.2 Variables que Render pedirá manualmente

Escribe únicamente estas variables cuando Render las solicite:

| Variable | Valor que debes pegar |
|---|---|
| `FRAPPE_EXTERNAL_URL` | Inicialmente la URL pública esperada, sin `/` final, por ejemplo `https://construcontrol-web.onrender.com` |
| `ADMIN_PASSWORD` | Contraseña nueva, larga y única para el usuario `Administrator` |
| `SUPABASE_URL` | URL del **Supabase de destino** |
| `SUPABASE_SERVER_KEY` | Clave `sb_secret_...` del **Supabase de destino** |

No escribas ni regeneres estas variables generadas por Render:

- `MARIADB_ROOT_PASSWORD`
- `DB_PASSWORD`
- `FRAPPE_ENCRYPTION_KEY`

### 4.3 Lanzar

Pulsa **Deploy Blueprint**. El despliegue crea:

- `construcontrol-db`
- `construcontrol-redis-cache`
- `construcontrol-redis-queue`
- `construcontrol-backend`
- `construcontrol-websocket`
- `construcontrol-worker`
- `construcontrol-scheduler`
- `construcontrol-web`
- `construcontrol-backup`

El servicio `construcontrol-backup` ejecuta un respaldo diario a las **08:00 UTC**, equivalente aproximadamente a las **02:00 de Honduras**.

## 5. Validar el primer arranque

No abras el sistema hasta que MariaDB, backend, WebSocket, worker, scheduler y web aparezcan en verde.

### 5.1 Health check

Abre en el navegador:

```text
https://construcontrol-web.onrender.com/api/method/ping
```

Debe responder correctamente y no mostrar 502.

### 5.2 Iniciar sesión

1. Abre `https://construcontrol-web.onrender.com`.
2. Usuario: `Administrator`.
3. Contraseña: el valor que escribiste en `ADMIN_PASSWORD`.
4. Completa el Setup Wizard de ERPNext.

Configura como mínimo:

- Compañía.
- Moneda HNL.
- Zona horaria `America/Tegucigalpa`.
- Plan de cuentas.
- Almacén principal.
- Centro de costo principal.

### 5.3 ConstruControl Settings

En ERPNext busca **ConstruControl Settings** y establece:

- Compañía predeterminada.
- Proyecto predeterminado, si ya existe.
- Almacén predeterminado.
- Centro de costo predeterminado.
- Modo de migración: primero `Preserve Only`.

**Criterio de aprobación:** login correcto, menú ConstruControl visible, worker y scheduler activos, y subida privada de un archivo de prueba funcionando.

## 6. Exportar el Supabase de origen

Regresa a PowerShell dentro del repositorio local.

### 6.1 Definir temporalmente las credenciales del origen

```powershell
$env:SUPABASE_URL = "https://PROYECTO-ORIGEN.supabase.co"
$env:SUPABASE_SERVER_KEY = "CLAVE-SECRETA-DEL-ORIGEN"
$env:SUPABASE_PROJECT_ID = ""
```

Estas variables duran únicamente en esa ventana de PowerShell.

### 6.2 Exportar datos y evidencias

```powershell
Remove-Item -Recurse -Force migration-output\source-export -ErrorAction SilentlyContinue
python scripts\export_supabase_snapshot.py migration-output\source-export
```

El comando debe terminar con `failed_files: 0`.

### 6.3 Validar relaciones y conteos

```powershell
python scripts\validate_construcontrol_backup.py `
  migration-output\source-export\construcontrol-supabase-export.json `
  --report migration-output\source-export\preflight-report.json
```

El código de salida debe ser `0`. No continúes si hay duplicados, relaciones huérfanas o archivos fallidos.

### 6.4 Crear el paquete ZIP verificable

```powershell
python scripts\create_migration_bundle.py `
  migration-output\source-export `
  migration-output\construcontrol-migration.zip
```

El resultado imprime el SHA-256 del ZIP. Guárdalo.

## 7. Subir el paquete al Supabase de destino

Sustituye las variables de la misma ventana de PowerShell por las del destino:

```powershell
$env:SUPABASE_URL = "https://PROYECTO-DESTINO.supabase.co"
$env:SUPABASE_SERVER_KEY = "sb_secret_<COPIAR_DESDE_SUPABASE>"
$objectKey = "incoming/construcontrol-migration-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
```

Sube el paquete:

```powershell
python scripts\supabase_storage_transfer.py upload `
  migration-output\construcontrol-migration.zip `
  --bucket construcontrol-migration `
  --object $objectKey `
  --content-type application/zip
```

Copia el valor de `object_key` que aparece en la salida. Ese será el valor usado en Render.

## 8. Ejecutar el ensayo de migración en Render

1. En Render abre `construcontrol-backend`.
2. Abre **Shell**.
3. Sustituye `RUTA_DEL_OBJETO.zip` por el `object_key` exacto.
4. Ejecuta:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"RUTA_DEL_OBJETO.zip","dry_run":true,"source_kind":"Supabase Export"}'
```

El sistema descarga el ZIP a una carpeta temporal, verifica rutas, tamaños y SHA-256, extrae el paquete y elimina el staging temporal al terminar.

En ERPNext abre **ConstruControl Migration Run** y luego **Migration Reconciliation**.

**Detente** si el estado contiene advertencias no justificadas, errores de Storage, duplicados o relaciones huérfanas.

## 9. Crear un respaldo persistente antes de la importación real

En el Shell de `construcontrol-backend`, ejecuta:

```bash
bash apps/erpnext/deploy/render/run-backup.sh
```

El comando:

1. Ejecuta `bench backup --with-files`.
2. Sube cada archivo al bucket privado `construcontrol-backups`.
3. Crea y sube `backup-manifest.json` con tamaños y SHA-256.
4. Elimina las copias locales efímeras únicamente después de una subida exitosa.

Copia el valor `manifest_object_key` de la salida, por ejemplo:

```text
construcontrol/2026/07/17/20260717T080000Z/backup-manifest.json
```

## 10. Ejecutar la importación real

En el mismo Shell, sustituye ambos valores:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.remote_importer.run_import_from_supabase \
  --kwargs '{"object_key":"RUTA_DEL_OBJETO.zip","dry_run":false,"source_kind":"Supabase Export","backup_reference":"RUTA_DEL_BACKUP_MANIFEST.json"}'
```

No cierres la ventana hasta ver el resultado final.

## 11. Conciliar la migración

Verifica en **Migration Reconciliation**:

- Registros de entrada = registros preservados.
- `mapped + preserved_only = preserved`.
- Archivos verificados = adjuntados + rechazados justificados.
- No existen errores de checksum.
- No existen relaciones huérfanas.
- Los saldos y conteos coinciden con el reporte de origen.

Prueba con usuarios reales de ERPNext:

- Manager puede administrar.
- Operator puede operar sin administrar configuración.
- Auditor puede leer y exportar sin modificar.
- Viewer no puede editar.
- Un usuario sin permisos no puede descargar un archivo privado.

La seguridad por proyecto se aplica en ERPNext. Los usuarios del navegador no acceden directamente a Supabase ni reciben la clave de servidor.

## 12. Rollback lógico

Solo si la conciliación falla y antes de que los usuarios creen movimientos nuevos:

```bash
bench --site "$SITE_NAME" execute \
  erpnext.construcontrol.migration.importer.rollback \
  --kwargs '{"migration_run":"CC-MIG-2026-00001"}'
```

El rollback lógico elimina únicamente borradores creados por esa corrida y conserva eventos de auditoría. Para una restauración total, descarga el conjunto indicado por `backup-manifest.json` y restáuralo primero en un entorno aislado.

## 13. Verificar el respaldo automático

Después de la primera ejecución programada:

1. En Render abre `construcontrol-backup`.
2. Revisa que el último job termine con estado exitoso.
3. En Supabase abre Storage > `construcontrol-backups`.
4. Confirma que existe una carpeta por fecha y un `backup-manifest.json`.
5. Descarga un respaldo y verifica su SHA-256 antes de considerarlo válido.

## 14. Dominio personalizado

1. En Render abre `construcontrol-web` > **Settings** > **Custom Domains**.
2. Agrega el dominio.
3. Copia exactamente el registro DNS que Render indique.
4. Espera el certificado TLS.
5. En `construcontrol-backend`, cambia `FRAPPE_EXTERNAL_URL` a la URL HTTPS final, sin `/` al final.
6. Realiza redeploy del backend.
7. Prueba `/api/method/ping` en el dominio final.

## 15. Solución de problemas

### Error 502

Revisa en este orden:

1. `construcontrol-db`.
2. `construcontrol-backend`.
3. `construcontrol-websocket`.
4. `construcontrol-web`.

No hagas pública la base ni el bucket para “resolver” el error.

### Site not found

Confirma que `SITE_NAME` y `FRAPPE_SITE_NAME_HEADER` sean `construcontrol`.

### Archivo 403

Confirma:

- `SUPABASE_URL` corresponde al destino.
- `SUPABASE_SERVER_KEY` es una clave `sb_secret_` válida.
- El bucket es privado.
- El usuario tiene permiso de lectura en el documento `File` de ERPNext.

### El paquete no importa

Comprueba:

- Extensión `.zip`.
- Existe `bundle-manifest.json`.
- Existe exactamente un `construcontrol-supabase-export.json`.
- Los SHA-256 coinciden.
- `storage-manifest.json` y la carpeta `evidence` están dentro del ZIP.

### El respaldo programado falla

Abre los logs de `construcontrol-backup` y verifica `SUPABASE_URL`, `SUPABASE_SERVER_KEY` y `SUPABASE_BACKUP_BUCKET`. El job no se considera exitoso hasta que el manifiesto remoto haya sido subido.

## 16. Qué no debes hacer

- No ejecutar el SQL de destino en el Supabase de origen.
- No pegar claves en GitHub.
- No crear buckets públicos.
- No usar `anon`, `publishable` o variables `VITE_` en el backend.
- No regenerar `DB_PASSWORD`, `MARIADB_ROOT_PASSWORD` o `FRAPPE_ENCRYPTION_KEY` después de crear datos.
- No ejecutar la importación real sin dry run y respaldo remoto.
- No considerar una Action verde como prueba de que Render, Supabase y la migración real ya fueron ejecutados.
