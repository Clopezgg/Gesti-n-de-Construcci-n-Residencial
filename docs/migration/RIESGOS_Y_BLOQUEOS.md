# Riesgos y bloqueos reales

## Bloqueos actuales

### 1. No hay datos operativos en los ZIP

Faltan:

- filas reales de `construction_projects` y tablas relacionadas;
- export `localStorage`/backup AppData;
- objetos y metadata del bucket `construction-evidence`;
- usuarios reales de Supabase Auth;
- credenciales/acceso a Supabase.

Impacto: no es posible ejecutar ni certificar cantidades, relaciones, usuarios, archivos o RLS reales. El código y los scripts están listos, pero la migración de registros permanece sin ejecutar.

Resolución: proporcionar el directorio producido por `scripts/export_supabase_snapshot.py`, un dump autorizado y export de Storage, o acceso temporal server-only. Nunca enviar credenciales dentro del ZIP/repositorio.

### 2. No hay runtime Frappe/Docker local en el entorno de auditoría

No se encontró `bench` ni Docker. Se pudo validar sintaxis/estructura y lógica standalone, pero no instalar un sitio, ejecutar migraciones Frappe ni arrancar la topología.

Resolución: ejecutar la lista de `VALIDACION_RESULTADOS.md` en CI/staging con MariaDB/Redis/Bench antes de producción.

### 3. No hay cuenta/proyecto Render

`render.yaml` está preparado, pero la plataforma debe generar/solicitar secretos, crear recursos y validar el Blueprint. No se afirmó un despliegue que no ocurrió.

## Riesgos controlados

| Riesgo | Control |
|---|---|
| Duplicación al reintentar | Hash de archivo, claves estables y versiones deterministas. |
| Pérdida de campos desconocidos | Snapshot completo + Legacy Record por entidad. |
| Archivos faltantes/corruptos | Manifest, bytes, SHA-256 y bloqueo de import real. |
| Publicar contabilidad/stock erróneo | No se presentan documentos; modo seguro por defecto. |
| Escalamiento de permisos | Overrides históricos no se aplican; roles Frappe aislados. |
| Migrar credenciales inseguras | Campos sensibles saneados y contabilizados; usuarios opcionales. |
| Pérdida de archivos en Render | Storage remoto privado, no filesystem efímero. |
| Regenerar secretos Frappe/DB | Variables persistentes generadas por Render y documentación de no rotación accidental. |
| Rollback incompleto de updates | Backup Bench autoritativo antes de importación. |
| Divergencia futura de ERPNext | Módulo aislado y upstream documentado. |

## Decisiones que requieren propietario funcional antes de cargar producción

- Correspondencia de compañías, cuentas, centros de costo, almacenes, impuestos y monedas.
- Si contratos/materiales/socios deben crear documentos ERPNext estándar.
- Qué usuarios reales se habilitan y con qué roles estándar adicionales.
- Cómo convertir payables/movimientos históricos en saldos o documentos contables.
- Retención legal de auditoría, evidencias y datos personales.
- Aceptación documentada de cualquier advertencia/diferencia de conciliación.
