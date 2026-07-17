# Cambios realizados

## Núcleo consolidado

- Se conservó íntegramente ERPNext 15.117.0 como arquitectura base.
- Se registró el módulo Frappe `ConstruControl` sin reemplazar DocTypes estándar.
- Se creó un workspace con accesos a operaciones, migración, auditoría y conciliación.
- Se añadieron cuatro roles aislados: Manager, Operator, Auditor y Viewer.

## Modelo funcional incorporado

Se añadieron diez DocTypes:

1. ConstruControl Settings.
2. ConstruControl Migration Run.
3. ConstruControl Legacy Record.
4. ConstruControl Fund Entry.
5. ConstruControl Expense Record.
6. ConstruControl Progress Update.
7. ConstruControl Weekly Closing.
8. ConstruControl Change Order.
9. ConstruControl Approval.
10. ConstruControl Audit Event.

Los documentos operativos conservan IDs/fechas/estados/evidencia y enlazan Project, Task, Supplier, Contract o fuente de fondos cuando corresponde. El evento de auditoría es append-only.

## Migración

- Normalizador para backup nativo, export localStorage y respuesta REST Supabase.
- Inventario de 36 colecciones core/operacionales/empresariales más settings.
- Claves y hashes deterministas, versiones inmutables y reutilización idempotente.
- Detección de IDs duplicados, IDs faltantes y referencias huérfanas conocidas.
- Preservación del snapshot completo, incluso campos/colecciones no reconocidos.
- Saneamiento y conteo de contraseñas, hashes, PIN, tokens y service keys.
- Mapeo a documentos custom y, en modo controlado, a Project/Task/Supplier/Contract/Item/User.
- Bloqueo de importación real sin backup y sin export Storage íntegro.
- Manifest de archivos con bytes/SHA-256 y adjuntos al destino o al Legacy Record.
- Informe de conciliación por ejecución.
- Rollback idempotente limitado a borradores creados por la ejecución.

## Supabase

- Tres SQL read-only para preflight, integridad y conciliación.
- SQL idempotente para bucket privado/límites/MIME y retiro de políticas públicas obsoletas.
- Exportador server-only de snapshots y objetos Storage.
- Adaptador Frappe de archivos hacia Supabase Storage con fallback local.
- Descarga mediada por permisos Frappe para adjuntos privados.

## Producción, GitHub y Render

- `.env.example`, `.gitignore`, `.gitattributes` y escaneo de secretos.
- Dockerfile sobre la imagen exacta `frappe/erpnext:v15.117.0`.
- Blueprint Render con Nginx, Gunicorn, Socket.IO, worker, scheduler, MariaDB y Key Value.
- Inicialización no destructiva: crea sólo si no existe esquema; luego `bench migrate`.
- Puerto dinámico, health check, secretos generados/no sincronizados y disco MariaDB.
- Workflow GitHub Actions de validación estática.
- Documentación de instalación, arquitectura, exportación, migración, rollback, Supabase, GitHub, Render, pruebas y riesgos.

## Correcciones/riesgos del origen evitados

- No se trasladó la importación UI5 rota ni el frontend que se automodifica durante `prepare:types`.
- No se copiaron dependencias instaladas, builds, `.env` ni secretos.
- No se activaron asientos, stock, payables, automatizaciones ni overrides de permisos históricos sin datos maestros conciliados.
- No se reutilizó autenticación local/Supabase dentro de Frappe.
- No se presentaron datos demo como datos reales.
