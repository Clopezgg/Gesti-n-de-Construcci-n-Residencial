# Riesgos y bloqueos reales

## Bloqueos actuales

### 1. No hay datos operativos en los ZIP auditados

Faltan filas reales de `construction_projects`, export de `localStorage`, objetos del bucket, usuarios de Supabase Auth y credenciales autorizadas.

Impacto: no es posible certificar cantidades, relaciones, usuarios ni archivos históricos reales hasta ejecutar la exportación. Nunca coloque credenciales dentro del ZIP o del repositorio.

### 2. Falta desplegar en la cuenta Oracle del propietario

El repositorio ya contiene Docker Compose, scripts y CI ARM64, pero no existe acceso a la cuenta Oracle ni a la futura instancia para ejecutar el despliegue, el login y la restauración real.

Resolución: seguir `MANUAL_PASO_A_PASO.md` y documentar cada criterio de aprobación.

### 3. Capacidad de Oracle Ampere

Oracle puede mostrar `Out of host capacity` cuando no existe capacidad gratuita temporal en la región principal.

Resolución: probar otro Availability Domain dentro de la misma región o reintentar más tarde. No sustituir automáticamente por una forma pagada.

## Riesgos controlados

| Riesgo | Control |
|---|---|
| Cargo accidental | Render retirado; manual exige etiqueta Always Free y presupuesto de USD 1. |
| Duplicación al reintentar | Hashes y claves deterministas. |
| Pérdida de campos desconocidos | Snapshot completo y Legacy Record. |
| Archivos faltantes o corruptos | Manifiesto, bytes, SHA-256 y bloqueo de importación real. |
| Publicar contabilidad o stock incorrecto | Modo seguro y documentos no presentados por defecto. |
| Escalamiento de permisos | Roles Frappe aislados y pruebas con usuarios no administradores. |
| Pérdida al redeploy | Volúmenes persistentes para MariaDB, sitio, cola y backups. |
| Exposición de base o Redis | Ningún puerto de MariaDB/Redis se publica al host. |
| Eliminación accidental de datos | Prohibición expresa de `docker compose down -v` y eliminación de volúmenes. |
| Regenerar secretos | Variables críticas documentadas como inmutables tras el primer inicio. |
| Backup corrupto | `backup-manifest.json` y verificación SHA-256. |
| Copia local única | Backup de volumen Oracle y copia Supabase opcional. |
| Arquitectura incompatible | CI construye `linux/arm64` para Oracle Ampere. |
| Rollback incompleto | Backup Bench autoritativo antes de importación. |

## Decisiones funcionales pendientes antes de cargar datos

- Correspondencia de compañías, cuentas, centros de costo, almacenes, impuestos y monedas.
- Qué contratos, materiales y socios crearán documentos ERPNext estándar.
- Qué usuarios reales se habilitan y con qué roles.
- Cómo convertir payables y movimientos históricos en saldos o documentos contables.
- Retención legal de auditoría, evidencias y datos personales.
- Aceptación documentada de cualquier diferencia de conciliación.

## Reglas de seguridad

- No exponer secretos en GitHub, capturas o chats públicos.
- No ejecutar SQL de destino en el Supabase de origen.
- No importar sin dry run y respaldo verificado.
- No considerar una Action verde como prueba suficiente de producción.
- No superar cuotas Always Free sin revisar el costo estimado.
