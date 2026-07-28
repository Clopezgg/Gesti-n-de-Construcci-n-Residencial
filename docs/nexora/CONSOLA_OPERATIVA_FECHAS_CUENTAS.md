# NEXORA — Consola operativa, fechas documentales y cuentas frecuentes

## Requisitos trazables

- `NXR-OPR-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Ingresos, gastos, anulaciones y correcciones aceptan una fecha documental elegida por el usuario, separada de la fecha real de creación y auditoría.
- `NXR-OPR-20260728-02`: **IMPLEMENTADO Y VALIDADO**. Las combinaciones frecuentes de remitente, institución, cuenta, moneda y canal pueden guardarse y reutilizarse sin copiar manualmente los datos en cada ingreso.
- `NXR-OPR-20260728-03`: **IMPLEMENTADO Y VALIDADO**. La consola diaria reconoce los códigos numéricos `101`, `102`, `303`, `304` y `501` y presenta únicamente los campos aplicables.
- `NXR-LGR-20260728-01`: **IMPLEMENTADO Y VALIDADO**. El Libro Central operativo muestra día, fecha documental, documento, código, movimiento, contraparte, institución, cuenta enmascarada, moneda, importe y estado.
- `NXR-UX-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Actividad reciente se limita a tres movimientos y ofrece **Ver más actividad**; las tarjetas inferiores usan una densidad uniforme y compacta.
- `NXR-LGR-20260728-02`: **IMPLEMENTADO Y VALIDADO**. Los códigos correctivos quedan definidos sin borrado físico: `303` anulación financiera, `304` corrección o sustitución documental y `501` cancelación total.

## Regla operativa de códigos

| Código | Presentación | Implementación canónica | Efecto |
|---|---|---|---|
| `101` | Entrada de saldo | `NXR Fund Source` + `NXR Operation` de ingreso | incrementa una fuente independiente |
| `102` | Salida de saldo / gasto | perfil canónico `CONSTRUCTION_PAYMENT` | consume fuentes y registra clasificación económica |
| `303` | Anulación financiera | cancelación segura del ingreso o `REVERSAL_NO_CASH` | compensa el documento original |
| `304` | Corrección documental | `DOCUMENT_SUBSTITUTION` | conserva el importe financiero y sustituye evidencia o documento |
| `501` | Cancelación total | cancelación segura del ingreso o reversión total | compensa completamente el efecto todavía reversible |

Los códigos numéricos son una capa de operación visible. Los perfiles financieros existentes continúan siendo el motor interno para conservar saldos, efectos, permisos, idempotencia y auditoría.

## Fechas y auditoría

1. **Fecha del documento:** seleccionada por el usuario y usada para el período financiero.
2. **Fecha real de registro:** asignada por Frappe en `creation` y no editable.
3. La fecha documental puede ser histórica.
4. No se acepta una fecha futura.
5. Una corrección, anulación o cancelación no puede fecharse antes de su documento original.
6. Un mes con `NXR Monthly Close` aprobado bloquea nuevos movimientos para ese proyecto y período.
7. La fecha y el proyecto se validan nuevamente en servidor; no se confía en la interfaz.

## Cuentas frecuentes

El DocType `NXR Financial Account` conserva:

- nombre operativo;
- proyecto opcional;
- uso como origen, destino o ambos;
- remitente o titular;
- banco o remesadora;
- cuenta;
- moneda;
- canal habitual;
- estado y cuenta predeterminada;
- huella única para evitar duplicados.

La creación y lectura de valores completos exige rol operativo financiero. El Libro Central y el dashboard muestran únicamente una cuenta enmascarada. No se guardan automáticamente combinaciones no autorizadas: el usuario debe marcar **Guardar como cuenta frecuente** y asignar un nombre.

## Flujo de la consola diaria

1. Escribir o seleccionar el código de movimiento.
2. Elegir la fecha del documento y el proyecto.
3. Completar los campos dinámicos.
4. Para `101`, seleccionar una cuenta frecuente o escribir los datos y guardar la combinación.
5. Para `102`, distribuir el importe entre fondos disponibles.
6. Para `303`, `304` o `501`, seleccionar el documento original y explicar el motivo.
7. Generar una vista previa calculada en servidor.
8. Contabilizar usando huella de vista previa e idempotencia.
9. Actualizar saldos, Libro Central y dashboard únicamente después de una ejecución confirmada.

## Permisos

- `101` y administración de cuentas frecuentes: Operador financiero, Gerente financiero o Administrador.
- `102`: Operador financiero, Gerente financiero o Administrador.
- `303`, `304` y `501`: Gerente financiero o Administrador; se conservan los controles de segregación de los perfiles correctivos.
- Libro Central operativo: roles NEXORA con permiso de vista y alcance de proyecto autorizado.
- Auditor y visor no reciben números de cuenta completos mediante los servicios de cuentas frecuentes.

## Evidencia y conservación

- `NXR Operation Metadata` relaciona cada documento con su código operativo visible.
- Las anulaciones y cancelaciones crean documentos compensatorios; no eliminan el documento original.
- La cuenta frecuente utilizada puede quedar vinculada a la operación `101`.
- La referencia original, la fecha documental, `creation`, el usuario, la idempotencia y las huellas permanecen auditables.
- No se incorporan llamadas a `delete_doc`, `db.delete` ni eliminación física de operaciones contabilizadas.

## Pruebas positivas incorporadas

1. Registrar hoy un ingreso con fecha documental histórica y conservar esa fecha en fuente y operación.
2. Guardar una cuenta frecuente, reutilizarla y evitar una segunda cuenta con la misma huella.
3. Generar los códigos `101`, `102`, `303`, `304` y `501` desde una consola real respaldada por servidor.
4. Anular un ingreso sin eliminar el original y conservar la fecha seleccionada en el documento compensatorio.
5. Mostrar LUN–DOM, datos financieros enmascarados y estado **Contabilizado** en el Libro Central.
6. Abrir los accesos rápidos del dashboard en la nueva consola y verificar escritorio, iPhone y PWA.

## Pruebas negativas incorporadas

1. Rechazar fecha futura.
2. Rechazar movimiento dentro de un mes cerrado.
3. Rechazar corrección anterior al documento original.
4. Rechazar corrección contra un proyecto diferente.
5. Rechazar códigos desconocidos y ejecución sin vista previa vigente.
6. Rechazar `303`, `304` o `501` sin documento original o sin motivo suficiente.
7. Impedir que un Auditor consulte valores completos de cuentas frecuentes.
8. Rechazar una cuenta frecuente perteneciente a otro proyecto.
9. Preservar operaciones contabilizadas sin borrado físico.

## Riesgos y dependencias

- La migración sincroniza dos DocTypes nuevos; debe ejecutarse antes de usar la consola.
- Los meses previamente aprobados permanecen bloqueados; cualquier reapertura requiere un flujo posterior autorizado, no una omisión silenciosa.
- Los códigos `303` y `501` solo pueden compensar la porción todavía reversible según el motor canónico.
- La consola no copia la interfaz, marca ni activos de SAP; reutiliza únicamente el patrón general de captura por código solicitado por el usuario.

## Evidencia de certificación publicada

- SHA funcional probado: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- Linters y Semgrep: run `30362821825`, aprobado.
- Aplicación NEXORA, instalación, migración, rollback, escritorio, iPhone y PWA: run `30362821826`, aprobado.
- Invariantes financieras Frappe/MariaDB: run `30362821878`, aprobado.
- Patch: run `30362821997`, aprobado.
- Gobierno, documentación, controles estáticos, validación segura y commits semánticos: runs `30362821743`, `30362821722`, `30362821872`, `30362821844`, `30362821756`, `30362821746` y `30362822144`, aprobados.
- El control Postgres `30362821724` fue omitido por diseño; la instalación y las invariantes canónicas aprobaron sobre MariaDB.

## Criterio de terminado

Las pruebas, la publicación del código y las compuertas exigidas están aprobadas en el SHA certificado. El cierre operativo del bloque exige fusionar el PR `#26` y registrar el SHA verificable resultante en `main`; producción permanece fuera de alcance sin autorización expresa.
