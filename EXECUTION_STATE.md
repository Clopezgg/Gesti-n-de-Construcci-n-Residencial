# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado para la corrección de despliegue: `c192be8f71a4580ac4ec6297476c5449d894f306`
- Rama técnica activa: `fix/coolify-nonblocking-startup`
- Pull Request activo: `#29`
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

Estado: **NO DEMOSTRADO** únicamente hasta que concluya la certificación final del HEAD documental del PR `#29`. El código funcional y las pruebas aplicables previas ya están publicados.

### Incidente confirmado

- despliegue intentado sobre `main` en el SHA `c192be8f71a4580ac4ec6297476c5449d894f306`;
- imagen `nexora-app:v15.117.0` construida correctamente;
- MariaDB, Redis Cache y Redis Queue alcanzaron estado saludable;
- `docker compose up -d` terminó con código `255` mientras los servicios secundarios esperaban `backend: service_healthy`;
- el backend incluye instalación y migración y no había alcanzado salud HTTP dentro de la ventana operativa del comando remoto de Coolify;
- los logs entregados no demostraron un error de compilación, importación ni migración de NEXORA.

### Requisitos trazables

- `NXR-DEP-20260728-01`: Coolify debe liberar `docker compose up -d` después de crear e iniciar contenedores, sin esperar a que termine una migración larga del backend.
- `NXR-DEP-20260728-02`: workers, scheduler y websocket deben esperar internamente el endpoint real del backend antes de iniciar.
- `NXR-DEP-20260728-03`: frontend no puede declararse saludable hasta que `/api/method/ping` responda para `SITE_NAME`.
- `NXR-DEP-20260728-04`: un respaldo inicial habilitado debe esperar al backend y nunca bloquear ni cancelar el resto del stack.

### Implementación publicada

- Rama: `fix/coolify-nonblocking-startup`.
- PR: `#29`.
- Base verificada: `c192be8f71a4580ac4ec6297476c5449d894f306`.
- SHA funcional: `6237735c894dcf5ed4dc7449ab1c4e7192a56412`.
- Dependencias secundarias cambiadas de `service_healthy` a `service_started`.
- Backend conserva dependencia estricta de MariaDB y Redis saludables.
- `FRAPPE_INTERNAL_URL=http://backend:8000` definido en el entorno compartido.
- Worker corto, worker largo, scheduler y websocket esperan hasta 600 segundos el endpoint `/api/method/ping` con el encabezado `Host` correcto.
- Frontend conserva healthcheck HTTP real y un período de inicio compatible con la migración.
- Respaldo inicial espera al backend cuando `BACKUP_RUN_ON_START=true`.
- Ningún healthcheck fue eliminado, omitido ni reemplazado por una simulación de éxito.

### Evidencia de la primera ronda funcional

- Contrato NEXORA y Compose: aprobado dentro del run `30390438397`.
- Instalación, migración, desinstalación/rollback, reinstalación y semillas: aprobado dentro del run `30390438397`.
- Construcción, arranque, salud de los diez servicios y reinicio del stack real: aprobado dentro del run `30390438397`.
- Navegador escritorio, iPhone y PWA: en curso al momento de este commit documental.
- Linters y Semgrep: run `30390438436`, aprobado.
- Patch histórico: run `30390438425`, aprobado.
- Documentación: run `30390438409`, aprobado.
- Validación segura: run `30390438456`, aprobado.
- Commits semánticos: run `30390438488`, aprobado.
- Postgres: run `30390438547`, omitido por diseño; MariaDB es el motor canónico.

### Seguridad

- no se modificó Coolify, AWS, DNS, secretos, datos ni volúmenes desde esta ejecución;
- no se borraron ni recrearon volúmenes;
- no se cambiaron credenciales;
- la corrección preserva migración, healthchecks, respaldos y rollback por SHA.

## Siguiente acción

Esperar la ronda final del HEAD documental, corregir cualquier fallo real, registrar el HEAD certificado, marcar el PR `#29` listo, fusionarlo con protección por SHA y publicar el nuevo HEAD de `main`. Solo después el usuario podrá pulsar **Deploy** en Coolify conservando respaldo y rollback.
