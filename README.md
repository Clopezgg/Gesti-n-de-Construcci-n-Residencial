# ERPNext ConstruControl consolidado

Sistema consolidado sobre **ERPNext 15.117.0 / Frappe 15**. ERPNext conserva la arquitectura transaccional y el módulo `ConstruControl` incorpora la información, reglas, auditoría, migración y almacenamiento recuperables del sistema React/Supabase de origen.

## Empiece aquí

La guía operativa principal es **[MANUAL_PASO_A_PASO.md](MANUAL_PASO_A_PASO.md)**. Incluye el orden exacto, las pantallas, todas las variables, comandos completos y el SQL íntegro que debe pegarse en Supabase.

No ejecute el SQL de destino en el Supabase del sistema anterior. Durante la migración se utilizan dos proyectos claramente separados:

- **Supabase de origen:** solo para exportar los datos históricos.
- **Supabase de destino:** Storage privado del nuevo ERPNext, paquetes de migración y respaldos.

## Estado verificable

El repositorio contiene código, DocTypes, importador, validaciones, almacenamiento remoto, Blueprint de Render, mecanismo de transferencia de paquetes y respaldo remoto. No contiene contraseñas ni una exportación real de los datos del usuario.

Las comprobaciones del repositorio y la construcción de las imágenes Docker se ejecutan en GitHub Actions. Un resultado verde no sustituye las pruebas reales de Render, Supabase, permisos, migración y restauración descritas en el manual.

## Arquitectura

- ERPNext/Frappe: Project, Task, Supplier, Contract, Item, compras, inventario, contabilidad, permisos y autenticación.
- `erpnext/construcontrol`: DocTypes, roles, workspace, conciliación, importador y adaptador Storage.
- MariaDB: datos transaccionales, con disco persistente en Render.
- Redis cache y queue: caché, colas, workers y scheduler.
- Supabase Storage privado:
  - `construction-evidence`: archivos administrados por Frappe.
  - `construcontrol-migration`: paquetes ZIP verificados de migración.
  - `construcontrol-backups`: respaldos Bench y manifiestos SHA-256.
- Render:
  - backend Gunicorn;
  - frontend Nginx con imagen separada y permisos corregidos;
  - WebSocket;
  - worker;
  - scheduler;
  - cron diario de respaldo remoto.

El navegador nunca recibe la clave de Supabase. ERPNext valida los permisos y actúa como única frontera de autorización para las descargas privadas.

## Variables de Supabase

Use `SUPABASE_SERVER_KEY` con una clave `sb_secret_...`. El código conserva compatibilidad temporal con la variable heredada `SUPABASE_SERVICE_ROLE_KEY`, pero el Blueprint nuevo no la utiliza.

Nunca coloque claves reales en `.env`, GitHub, JavaScript, variables `VITE_`, capturas o documentos públicos.

## Validación local

```bash
python -m pip install PyYAML==6.0.2
python scripts/validate_repository.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
python -m py_compile \
  erpnext/construcontrol/migration/importer.py \
  erpnext/construcontrol/storage/supabase.py \
  scripts/export_supabase_snapshot.py \
  scripts/create_migration_bundle.py \
  scripts/supabase_storage_transfer.py \
  scripts/upload_backup_set.py
bash -n deploy/render/*.sh
```

Resultado esperado:

```text
Repository validation: 0 error(s)
```

## Flujo de migración resumido

1. Respalde y congele el origen.
2. Exporte el snapshot y las evidencias.
3. Valide relaciones, archivos y SHA-256.
4. Cree un paquete con `scripts/create_migration_bundle.py`.
5. Súbalo al bucket privado `construcontrol-migration` mediante `scripts/supabase_storage_transfer.py`.
6. Ejecute `run_import_from_supabase` primero con `dry_run=true`.
7. Ejecute `deploy/render/run-backup.sh` y conserve el `manifest_object_key`.
8. Ejecute la importación real utilizando ese manifiesto como `backup_reference`.
9. Concilie conteos, relaciones, permisos y archivos.

## Seguridad y rollback

- Los buckets son privados y no se crean políticas para `anon` o `authenticated`.
- La clave server-only permanece únicamente en procesos controlados.
- Contraseñas, PIN, tokens y claves encontradas dentro del payload histórico se eliminan del legado preservado.
- Los usuarios no se crean salvo autorización explícita y nunca se importan contraseñas.
- Los ZIP de migración se extraen en un directorio temporal con validación de rutas, tamaño, cantidad de archivos y SHA-256.
- El rollback lógico elimina únicamente borradores creados por una corrida; la restauración del respaldo Bench es la reversión autoritativa.

## Documentación técnica

- [Manual operativo completo](MANUAL_PASO_A_PASO.md)
- [Mapa de correspondencia](docs/migration/MAPA_CORRESPONDENCIA.md)
- [Supabase](docs/migration/SUPABASE.md)
- [Render](docs/migration/RENDER.md)
- [Migración y rollback](docs/migration/MIGRACION_Y_ROLLBACK.md)
- [Auditoría integral](docs/migration/AUDITORIA_INTEGRAL.md)
- [Validación de resultados](docs/migration/VALIDACION_RESULTADOS.md)

ERPNext conserva su licencia GNU GPL v3 y atribuciones originales en `license.txt` y `attributions.md`.
