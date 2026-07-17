# ERPNext ConstruControl consolidado

Sistema consolidado sobre **ERPNext 15.117.0 / Frappe 15**. ERPNext conserva la arquitectura definitiva y el módulo nativo `ConstruControl` incorpora la información, reglas y procesos recuperables del sistema React/Supabase de origen.

## Estado real de la entrega

El código, esquema, importador, validaciones, almacenamiento Supabase, CI y Blueprint de Render están preparados. Los ZIP recibidos **no contienen un dump de los registros operativos, una exportación de `localStorage`, los objetos del bucket ni credenciales de acceso**. Por tanto, esta entrega no inventa datos ni afirma haber migrado registros inexistentes: incluye el procedimiento verificable para exportarlos e importarlos cuando se proporcione acceso o un respaldo.

Los seis estados/fases de `EMPTY_DATA` se conservan como configuración de referencia en `erpnext/construcontrol/fixtures/default_phases.json`; no se contabilizan como registros operativos migrados.

## Arquitectura

- ERPNext/Frappe sigue siendo el núcleo: Project, Task, Supplier, Contract, Item, Asset, compras, inventario, contabilidad, permisos y autenticación.
- `erpnext/construcontrol`: diez DocTypes, roles, workspace, informe de conciliación, importador y adaptador de archivos.
- `ConstruControl Legacy Record`: preservación versionada del payload original saneado y su relación con el documento destino.
- `ConstruControl Migration Run`: hash de fuente, respaldo obligatorio, conteos, incidencias, errores y estado de rollback.
- Supabase: fuente histórica y almacenamiento privado opcional de adjuntos. La clave `service_role` se usa únicamente en servidor.
- Render: Nginx público, backend Gunicorn, WebSocket, worker, scheduler, MariaDB persistente y dos instancias Key Value.

La correspondencia completa está en [docs/migration/MAPA_CORRESPONDENCIA.md](docs/migration/MAPA_CORRESPONDENCIA.md).

## Requisitos

- Docker para despliegue reproducible, o Frappe Bench con Python 3.10+, Node y MariaDB 10.6.
- Un sitio Frappe/ERPNext 15.
- Para recuperar datos reales: URL y clave server-only del proyecto Supabase de origen, o un JSON nativo/localStorage y sus archivos.
- No copie valores reales a `.env`; use un gestor de secretos. `.env.example` documenta todas las variables.

## Validación rápida del repositorio

```bash
python scripts/validate_repository.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
python -m compileall -q erpnext/construcontrol scripts
bash -n deploy/render/*.sh
```

La validación integral de Frappe requiere un sitio real:

```bash
bench --site construcontrol.localhost migrate
bench --site construcontrol.localhost run-tests --app erpnext --module erpnext.construcontrol
bench --site construcontrol.localhost doctor
```

## Instalación local en Bench

Este repositorio es un fork completo de ERPNext, no una SPA independiente. Instálelo como la aplicación `erpnext` del bench:

```bash
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench
bench get-app https://github.com/USUARIO/REPOSITORIO.git
bench new-site construcontrol.localhost
bench --site construcontrol.localhost install-app erpnext
bench --site construcontrol.localhost migrate
bench start
```

Después abra `http://construcontrol.localhost:8000`, complete el Setup Wizard y configure **ConstruControl Settings**. El modo seguro inicial es `Preserve Only`; la creación de usuarios y documentos estándar está desactivada por defecto.

## Migración resumida

1. Respalde Supabase y ejecute los SQL de solo lectura `01_preflight.sql` y `02_relational_validation.sql`.
2. Exporte snapshots y archivos:

   ```bash
   python scripts/export_supabase_snapshot.py migration-output/source-export
   python scripts/validate_construcontrol_backup.py \
     migration-output/source-export/construcontrol-supabase-export.json \
     --report migration-output/source-export/preflight-report.json
   ```

3. Respalde el destino:

   ```bash
   bench --site construcontrol.localhost backup --with-files
   ```

4. Ejecute primero un dry run y luego la importación con la referencia exacta del respaldo:

   ```bash
   bench --site construcontrol.localhost execute \
     erpnext.construcontrol.migration.importer.run_import \
     --kwargs '{"source_path":"/ruta/construcontrol-supabase-export.json","dry_run":true,"source_kind":"Supabase Export"}'

   bench --site construcontrol.localhost execute \
     erpnext.construcontrol.migration.importer.run_import \
     --kwargs '{"source_path":"/ruta/construcontrol-supabase-export.json","dry_run":false,"source_kind":"Supabase Export","backup_reference":"/ruta/al/respaldo"}'
   ```

5. Compare `input_counts_json`, `output_counts_json`, el informe **ConstruControl Migration Reconciliation** y `03_post_export_reconciliation.sql`.

El procedimiento completo y el rollback están en [docs/migration/MIGRACION_Y_ROLLBACK.md](docs/migration/MIGRACION_Y_ROLLBACK.md).

## Despliegue

- GitHub: [docs/migration/GITHUB.md](docs/migration/GITHUB.md)
- Supabase y RLS: [docs/migration/SUPABASE.md](docs/migration/SUPABASE.md)
- Render: [docs/migration/RENDER.md](docs/migration/RENDER.md)
- Auditoría y pruebas: [docs/migration/AUDITORIA_INTEGRAL.md](docs/migration/AUDITORIA_INTEGRAL.md) y [docs/migration/VALIDACION_RESULTADOS.md](docs/migration/VALIDACION_RESULTADOS.md)
- Informe de cierre: [docs/migration/INFORME_FINAL.md](docs/migration/INFORME_FINAL.md)
- Riesgos y bloqueos: [docs/migration/RIESGOS_Y_BLOQUEOS.md](docs/migration/RIESGOS_Y_BLOQUEOS.md)

## Seguridad y rollback

- No hay secretos reales versionados.
- Contraseñas, PIN, tokens y claves `service_role` encontrados dentro del payload se eliminan del legado preservado y se cuentan en la conciliación.
- Los usuarios no se crean salvo autorización explícita; nunca se importan sus contraseñas.
- El bucket de evidencia permanece privado y Frappe autoriza cada descarga privada.
- El rollback del importador elimina solamente destinos en borrador creados por esa ejecución; conserva eventos de auditoría. La restauración del backup de Bench es el rollback autoritativo para cualquier actualización preexistente.

ERPNext conserva su licencia GNU GPL v3 y atribuciones originales en `license.txt` y `attributions.md`.
