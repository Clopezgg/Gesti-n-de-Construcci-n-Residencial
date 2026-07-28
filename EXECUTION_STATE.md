# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado para la corrección: `4f24ad57cdcc1b322b268c1502ba0bfbb01511b3`
- Rama técnica fusionada: `fix/nexora-guided-document-correction`
- Pull Request fusionado: `#28`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-007 / NXR-USR-0007

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR fusionado: `#25`.
- SHA funcional probado: `8ac970290df4d8cc675ab59d44ce22bd3ec85c27`.
- HEAD final certificado del PR: `deda757fa11163e5126aa0001aa20e6ade2729bf`.
- Commit de fusión publicado en `main`: `a3d47d6802944fe9dee6250e6a4d5bd4ba9126dd`.
- HEAD documental previo de `main`: `6812ee55f2aa1e723d9c59ea84675bf83b673990`.

## Bloque original con defecto confirmado — Consola operativa, fechas, cuentas y Libro Central

Requisitos originales:

- `NXR-OPR-20260728-01` — fecha documental histórica;
- `NXR-OPR-20260728-02` — cuentas frecuentes reutilizables;
- `NXR-OPR-20260728-03` — consola numérica `101/102/303/304/501`;
- `NXR-LGR-20260728-01` — Libro Central operativo ampliado;
- `NXR-UX-20260728-01` — dashboard inferior compacto;
- `NXR-LGR-20260728-02` — semántica correctiva sin borrado físico.

Estado histórico: **EXISTENTE PERO DEFECTUOSO** para el alta inicial de cuentas y la estructura visual de la consola. El defecto fue corregido y cerrado mediante el PR `#27`.

### Evidencia histórica del bloque original

- PR fusionado: `#26`.
- SHA funcional probado: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD final certificado del PR: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Commit de fusión publicado en `main`: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- La evidencia automatizada anterior no sustituyó la validación de uso real que reveló el defecto.

## Bloque correctivo fusionado — NXR-OPR-20260728-04 / NXR-UX-20260728-02

Estado: **IMPLEMENTADO Y VALIDADO**. Bloque cerrado y fusionado en `main`.

- Rama fusionada: `fix/nexora-financial-account-entry-ui`.
- PR fusionado: `#27`.
- SHA funcional probado: `d4b95dd2b9d86c67215a196c8f791a02f5d202ef`.
- HEAD final certificado del PR: `862e676089e4efc67e6e97dbcef36545aee43fbb`.
- Commit de fusión publicado en `main`: `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Linters y Semgrep: run `30379176902`, aprobado.
- Aplicación NEXORA, instalación, migración, rollback, escritorio, iPhone y PWA: run `30379177027`, aprobado.
- Invariantes financieras Frappe/MariaDB: run `30379176679`, aprobado.
- Patch: run `30379176591`, aprobado.

## Bloque correctivo fusionado — NXR-COR-20260728-01…06 / NXR-UX-20260728-03

Estado: **IMPLEMENTADO Y VALIDADO**. Bloque cerrado y fusionado en `main`.

### Defectos confirmados por uso real

- modificar directamente `operation_date` en una operación ejecutada producía un mensaje de inmutabilidad sin ofrecer el flujo operativo correcto;
- el flujo `304` heredado exigía evidencia aunque solo se corrigiera fecha, nombre de remesa o metadatos;
- **Últimas operaciones** podía conservar once encabezados con filas de cinco celdas y desplazar documento, movimiento e importe a columnas equivocadas.

### Evidencia publicada

- Rama fusionada: `fix/nexora-guided-document-correction`.
- PR fusionado: `#28`.
- Base verificada: `4f24ad57cdcc1b322b268c1502ba0bfbb01511b3`.
- SHA funcional probado: `9d5002d651a4b0d1afd4f80d7fbd550d812bacf0`.
- HEAD final certificado del PR: `6f42bc77f9e755ffdf18585c638f49642d378409`.
- Commit de fusión publicado en `main`: `1697bf60b34b270568a674d6544137bf9fbc509b`.

### Certificación final del HEAD del PR

- Linters y Semgrep: run `30387158451`, aprobado.
- Aplicación NEXORA, contrato, instalación, migración, desinstalación/rollback, reinstalación, escritorio, iPhone y PWA: run `30387163072`, aprobado.
- Invariantes financieras Frappe/MariaDB: run `30387163618`, aprobado.
- Patch histórico v13→v14→v15: run `30387160826`, aprobado.
- Gobierno: run `30387162569`, aprobado.
- Documentación: run `30387164167`, aprobado.
- Control estático de servidor: run `30387164210`, aprobado.
- Control de patch no Python: run `30387159932`, aprobado.
- Validación segura, migración repetida, persistencia y respaldo aislado: run `30387161336`, aprobado.
- Commits semánticos: run `30387160086`, aprobado.
- Postgres: run `30387161198`, omitido por diseño; MariaDB es la instalación canónica validada.

### Alcance funcional terminado

- búsqueda de la operación base mediante número documental único de 12 dígitos;
- carga de fecha documental, remesa o fuente, canal, moneda, valor original, tasa, importe HNL, remitente, institución, cuenta, referencia y comprobante;
- evidencia opcional para correcciones de fecha y metadatos;
- documento correctivo `304` con número nuevo, referencia al original y sin borrado físico;
- auditoría con antes/después, actor, motivo, correlación e idempotencia;
- bloqueo transaccional de operación, fuente y efecto recibido;
- corrección atómica de importe únicamente cuando la fuente permanece íntegra y sin usos posteriores;
- correcciones no financieras disponibles aunque el fondo ya tenga movimientos;
- períodos anterior y nuevo validados cuando cambia la fecha;
- edición directa de documentos ejecutados continúa bloqueada.

### Alcance de interfaz terminado

- botón **Corregir documento** en la consola y en el formulario ejecutado;
- código `304` redirigido al diálogo guiado;
- primer paso reducido al número documental;
- campos cargados automáticamente y editables según reglas financieras;
- comprobante presentado como opcional;
- vista previa con comparación antes/después y diferencia financiera;
- **Últimas operaciones** repara automáticamente encabezados y filas para conservar once columnas sincronizadas;
- funcionamiento validado en escritorio, iPhone y PWA.

### Permisos y seguridad

- lectura, vista previa y ejecución usan la acción de servidor `reclassify`;
- roles autorizados: `System Manager`, `NEXORA Administrator` y `NEXORA Finance Manager`;
- operador financiero, auditor y visor son rechazados;
- el alcance de proyecto se valida nuevamente en servidor;
- una vista previa vencida o una clave de idempotencia reutilizada con otro payload es rechazada;
- no se modificó producción ni infraestructura.

### Pruebas positivas aprobadas

1. buscar un ingreso por número de 12 dígitos;
2. corregir fecha, nombre de remesa y remitente sin evidencia;
3. generar documento `304` y evento de auditoría;
4. repetir la misma solicitud sin duplicar documentos;
5. corregir importe de una fuente íntegra y sincronizar fuente, operación y efecto;
6. instalar, migrar, retirar, reinstalar y sembrar NEXORA de forma idempotente;
7. validar escritorio, iPhone y PWA;
8. mantener once columnas coherentes en **Últimas operaciones**.

### Pruebas negativas aprobadas

1. rechazar número inexistente o que no contenga 12 dígitos;
2. rechazar operaciones que no sean ingresos base ejecutados;
3. rechazar usuarios sin rol de gerente o administrador;
4. rechazar fecha futura o período cerrado;
5. rechazar solicitudes sin cambios o sin motivo suficiente;
6. rechazar cambio de importe cuando la fuente ya fue utilizada;
7. rechazar vista previa vencida o idempotencia incompatible;
8. mantener bloqueada la edición directa y la eliminación de operaciones ejecutadas.

## Siguiente acción

El bloque correctivo está cerrado. El despliegue del nuevo HEAD de `main` en Coolify permanece fuera de esta ejecución y requiere autorización expresa, respaldo verificable, plan de rollback por SHA, validación posterior y registro de la acción.
