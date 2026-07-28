# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado para la corrección de fecha textual: `ee5282c75754032b18c721e4c0cfb1a60ecabb4c`
- Rama técnica activa: `fix/nexora-date-string-normalization`
- Pull Request activo: `#30`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

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
- edición directa de documentos ejecutados continúa bloqueada;
- botón **Corregir documento** en la consola y en el formulario ejecutado;
- código `304` redirigido al diálogo guiado;
- primer paso reducido al número documental;
- campos cargados automáticamente y editables según reglas financieras;
- comprobante presentado como opcional;
- vista previa con comparación antes/después y diferencia financiera;
- **Últimas operaciones** conserva once columnas sincronizadas;
- funcionamiento validado en escritorio, iPhone y PWA.

## Bloque correctivo de despliegue — NXR-DEP-20260728-01…04

Estado: **IMPLEMENTADO Y VALIDADO**. Bloque cerrado, certificado y fusionado en `main`.

### Incidente confirmado

- despliegue intentado sobre `main` en el SHA `c192be8f71a4580ac4ec6297476c5449d894f306`;
- imagen `nexora-app:v15.117.0` construida correctamente;
- MariaDB, Redis Cache y Redis Queue alcanzaron estado saludable;
- `docker compose up -d` terminó con código `255` mientras los servicios secundarios esperaban `backend: service_healthy`;
- el backend incluye instalación y migración y no había alcanzado salud HTTP dentro de la ventana operativa del comando remoto de Coolify;
- los logs entregados no demostraron un error de compilación, importación ni migración de NEXORA.

### Requisitos trazables

- `NXR-DEP-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Coolify libera `docker compose up -d` después de crear e iniciar contenedores, sin esperar a que termine una migración larga del backend.
- `NXR-DEP-20260728-02`: **IMPLEMENTADO Y VALIDADO**. Workers, scheduler y websocket esperan internamente el endpoint real del backend antes de iniciar.
- `NXR-DEP-20260728-03`: **IMPLEMENTADO Y VALIDADO**. Frontend no se declara saludable hasta que `/api/method/ping` responde para `SITE_NAME`.
- `NXR-DEP-20260728-04`: **IMPLEMENTADO Y VALIDADO**. Un respaldo inicial habilitado espera al backend y no bloquea ni cancela el resto del stack.

### Implementación publicada

- Rama fusionada: `fix/coolify-nonblocking-startup`.
- PR fusionado: `#29`.
- Base verificada: `c192be8f71a4580ac4ec6297476c5449d894f306`.
- SHA funcional probado: `6237735c894dcf5ed4dc7449ab1c4e7192a56412`.
- HEAD final certificado del PR: `b611bc72ce59e070ba8c8c4ffaa7d7a5e807d037`.
- Commit de fusión publicado en `main`: `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Dependencias secundarias cambiadas de `service_healthy` a `service_started`.
- Backend conserva dependencia estricta de MariaDB y Redis saludables.
- `FRAPPE_INTERNAL_URL=http://backend:8000` definido en el entorno compartido.
- Worker corto, worker largo, scheduler y websocket esperan hasta 600 segundos el endpoint `/api/method/ping` con el encabezado `Host` correcto.
- Frontend conserva healthcheck HTTP real y un período de inicio compatible con la migración.
- Respaldo inicial espera al backend cuando `BACKUP_RUN_ON_START=true`.
- Ningún healthcheck fue eliminado, omitido ni reemplazado por una simulación de éxito.

### Certificación final del HEAD del PR

- NEXORA app, contrato, instalación, migración, desinstalación/rollback, reinstalación, stack real, reinicio, escritorio, iPhone y PWA: run `30392389445`, aprobado.
- Invariantes financieras Frappe/MariaDB: run `30392388849`, aprobado.
- Linters y Semgrep: run `30392388417`, aprobado.
- Patch histórico: run `30392387921`, aprobado.
- Gobierno: run `30392387990`, aprobado.
- Documentación: run `30392388158`, aprobado.
- Control estático de servidor: run `30392388400`, aprobado.
- Control no Python: run `30392388300`, aprobado.
- Validación segura, migración repetida, persistencia y respaldo aislado: run `30392390070`, aprobado.
- Commits semánticos: run `30392388541`, aprobado.
- Postgres: run `30392389214`, omitido por diseño; MariaDB es el motor canónico.

### Pruebas positivas aprobadas

1. validar el contrato completo de Compose;
2. construir la imagen NEXORA;
3. iniciar el stack sin bloquear el comando por la salud posterior del backend;
4. instalar, migrar, retirar, reinstalar y sembrar NEXORA;
5. reiniciar el stack conservando datos y volúmenes;
6. alcanzar salud real en backend, frontend, websocket, workers y scheduler;
7. validar escritorio Chromium, iPhone WebKit y PWA;
8. ejecutar respaldo aislado y validaciones financieras.

### Pruebas negativas aprobadas

1. no declarar backend saludable antes de responder `/api/method/ping`;
2. no iniciar procesos dependientes antes de que el backend responda;
3. no desactivar healthchecks;
4. no borrar ni recrear volúmenes;
5. no modificar secretos ni credenciales;
6. no usar Postgres como sustituto del motor MariaDB certificado.

### Seguridad

- no se modificó Coolify, AWS, DNS, secretos, datos ni volúmenes desde esta ejecución;
- no se borraron ni recrearon volúmenes;
- no se cambiaron credenciales;
- la corrección preserva migración, healthchecks, respaldos y rollback por SHA.

## Bloque correctivo activo — NXR-DATE-20260728-01…03

Estado: **IMPLEMENTADO Y VALIDADO** en la rama técnica. Pendiente exclusivamente de certificar el HEAD documental y fusionar el PR `#30`.

### Defecto confirmado por uso real

- al cambiar la fecha mediante el flujo guiado de corrección documental, el servidor devolvía `AttributeError: 'str' object has no attribute 'strftime'`;
- la propuesta convertía la fecha validada a texto ISO;
- la comprobación de período cerrado enviaba ese texto a `month_key()`;
- `month_key()` asumía exclusivamente un objeto `date` y llamaba directamente a `strftime()`.

### Requisitos trazables

- `NXR-DATE-20260728-01`: **IMPLEMENTADO Y VALIDADO**. El cálculo de período acepta `date`, `datetime` y fecha ISO textual.
- `NXR-DATE-20260728-02`: **IMPLEMENTADO Y VALIDADO**. La corrección guiada de fecha valida los períodos anterior y nuevo sin errores de tipo.
- `NXR-DATE-20260728-03`: **IMPLEMENTADO Y VALIDADO**. Un formato inválido produce `OperationalDateError` controlado y no un `AttributeError` interno.

### Implementación publicada

- Rama: `fix/nexora-date-string-normalization`.
- PR: `#30`.
- Base verificada: `ee5282c75754032b18c721e4c0cfb1a60ecabb4c`.
- SHA funcional probado: `9ea31ef72c9d74c72820cac86143e3624a68e537`.
- `month_key()` normaliza toda entrada mediante `parse_document_date()` antes de generar `YYYY-MM`.
- La prueba contractual cubre `date`, `datetime` con zona horaria, texto ISO de fecha, texto ISO con hora y formato inválido.
- La compuerta financiera ejecuta expresamente `test_guided_operation_correction_integration` sobre Frappe/MariaDB.

### Certificación del SHA funcional

- NEXORA app, contrato, instalación, migración, rollback, reinstalación, stack real, escritorio, iPhone y PWA: run `30395927073`, aprobado.
- Invariantes financieras y corrección guiada real sobre MariaDB: run `30395926046`, aprobado.
- Linters y Semgrep: run `30395926769`, aprobado.
- Patch histórico: run `30395926740`, aprobado.
- Documentación: run `30395925984`, aprobado.
- Validación segura, sitio real, persistencia, respaldo e imagen: run `30395925990`, aprobado.
- Commits semánticos: run `30395925978`, aprobado.
- Postgres: run `30395926041`, omitido por diseño; MariaDB es el motor canónico certificado.

### Pruebas positivas aprobadas

1. calcular `2026-07` desde un objeto `date`;
2. calcular `2026-07` desde un `datetime` con zona horaria;
3. calcular `2026-07` desde `2026-07-28` y desde texto ISO con hora;
4. buscar un ingreso, cambiar la fecha mediante el flujo guiado y generar su vista previa;
5. ejecutar la corrección `304`, conservar auditoría y actualizar la fecha efectiva;
6. repetir la solicitud con la misma idempotencia sin duplicar documentos;
7. instalar, migrar, retirar, reinstalar y validar NEXORA sobre MariaDB.

### Pruebas negativas aprobadas

1. rechazar un formato no ISO con `OperationalDateError` accionable;
2. rechazar fecha futura;
3. rechazar fecha anterior al documento original cuando la regla aplica;
4. rechazar período cerrado;
5. rechazar usuario sin permiso de gerente o administrador;
6. no modificar saldos cuando la corrección es únicamente documental;
7. no eliminar ni sustituir físicamente la operación original.

### Seguridad

- no se modificó producción, Coolify, AWS, DNS, secretos, datos ni volúmenes;
- no se relajan períodos cerrados, permisos, idempotencia, auditoría ni bloqueo transaccional;
- el cambio se limita a normalización de fecha y cobertura obligatoria.

## Siguiente acción

Certificar el HEAD documental del PR `#30`, corregir cualquier fallo real, marcarlo listo y fusionarlo con protección por SHA. Después se publicará el nuevo HEAD exacto de `main` para que el usuario solo pulse **Deploy** en Coolify, conservando respaldo verificable y rollback por SHA.
