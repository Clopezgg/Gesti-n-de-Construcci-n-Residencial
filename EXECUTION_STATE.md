# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Historial certificado

### Consola operativa, fechas, cuentas y Libro Central

- Requisitos: `NXR-OPR-20260728-01…04`, `NXR-LGR-20260728-01…02`, `NXR-UX-20260728-01…02`, `NXR-CAT-20260728-01`, `NXR-VAL-20260728-01`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- PR original: `#26`.
- SHA funcional original: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD original certificado: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Fusión original: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- PR correctivo de cuentas e interfaz: `#27`.
- SHA funcional correctivo: `d4b95dd2b9d86c67215a196c8f791a02f5d202ef`.
- HEAD correctivo certificado: `862e676089e4efc67e6e97dbcef36545aee43fbb`.
- Fusión correctiva: `6363ee429ffb9903e2430463e0652a62b82b374e`.

### Corrección documental guiada

- Requisitos: `NXR-COR-20260728-01…06`, `NXR-UX-20260728-03`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- PR: `#28`.
- Base: `4f24ad57cdcc1b322b268c1502ba0bfbb01511b3`.
- SHA funcional: `9d5002d651a4b0d1afd4f80d7fbd550d812bacf0`.
- HEAD certificado: `6f42bc77f9e755ffdf18585c638f49642d378409`.
- Fusión: `1697bf60b34b270568a674d6544137bf9fbc509b`.
- La corrección `304` conserva original, auditoría, idempotencia, permisos, períodos y bloqueo transaccional.
- La edición directa y el borrado físico de documentos ejecutados permanecen bloqueados.

### Arranque no bloqueante en Coolify

- Requisitos: `NXR-DEP-20260728-01…04`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- PR: `#29`.
- Base: `c192be8f71a4580ac4ec6297476c5449d894f306`.
- SHA funcional: `6237735c894dcf5ed4dc7449ab1c4e7192a56412`.
- HEAD certificado: `b611bc72ce59e070ba8c8c4ffaa7d7a5e807d037`.
- Fusión: `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Backend conserva espera estricta por MariaDB y Redis saludables.
- Workers, scheduler y websocket esperan internamente el endpoint real.
- Frontend no se declara saludable antes de `/api/method/ping`.
- Ningún healthcheck fue eliminado o sustituido por éxito simulado.

## Último bloque fusionado — Normalización de fecha textual

Identificadores: `NXR-DATE-20260728-01…03`.

Estado: **IMPLEMENTADO Y VALIDADO**. Bloque cerrado, certificado y fusionado en `main`.

### Defecto confirmado por uso real

- al cambiar la fecha mediante el flujo guiado, el servidor devolvía `AttributeError: 'str' object has no attribute 'strftime'`;
- la fecha validada se serializaba como texto ISO;
- la comprobación de período cerrado enviaba el texto a `month_key()`;
- `month_key()` asumía exclusivamente un objeto `date`.

### Requisitos trazables

- `NXR-DATE-20260728-01`: **IMPLEMENTADO Y VALIDADO**. El cálculo de período acepta `date`, `datetime` y fecha ISO textual.
- `NXR-DATE-20260728-02`: **IMPLEMENTADO Y VALIDADO**. La corrección guiada valida períodos anterior y nuevo sin errores de tipo.
- `NXR-DATE-20260728-03`: **IMPLEMENTADO Y VALIDADO**. Un formato inválido produce `OperationalDateError` controlado.

### Implementación publicada

- Rama fusionada: `fix/nexora-date-string-normalization`.
- PR fusionado: `#30`.
- Base verificada: `ee5282c75754032b18c721e4c0cfb1a60ecabb4c`.
- SHA funcional probado: `9ea31ef72c9d74c72820cac86143e3624a68e537`.
- HEAD final certificado del PR: `d0702d6402f56c91af73b4365d9788f6f4e90269`.
- Commit de fusión publicado en `main`: `0d8884c5419fca439e4808008fb1e59fbf92c647`.
- `month_key()` normaliza mediante `parse_document_date()` antes de generar `YYYY-MM`.
- La prueba contractual cubre `date`, `datetime` con zona horaria, texto ISO de fecha, texto ISO con hora y formato inválido.
- La compuerta financiera ejecuta `test_guided_operation_correction_integration` sobre Frappe/MariaDB.

### Certificación final del HEAD del PR

- NEXORA app, contrato, instalación, migración, rollback, reinstalación, stack real, escritorio, iPhone y PWA: run `30396561503`, aprobado.
- Invariantes financieras y corrección guiada real sobre MariaDB: run `30396561479`, aprobado.
- Linters y Semgrep: run `30396564004`, aprobado.
- Patch histórico: run `30396561828`, aprobado.
- Gobierno: run `30396561459`, aprobado.
- Documentación: run `30396561415`, aprobado.
- Control estático de servidor: run `30396563720`, aprobado.
- Control no Python: run `30396562166`, aprobado.
- Validación segura, sitio real, persistencia, respaldo e imagen: run `30396562192`, aprobado.
- Commits semánticos: run `30396561859`, aprobado.
- Postgres: run `30396563803`, omitido por diseño; MariaDB es el motor canónico certificado.

### Pruebas positivas aprobadas

1. calcular el período desde `date` y `datetime`;
2. calcular el período desde fecha ISO y fecha/hora ISO;
3. buscar un ingreso y cambiar la fecha mediante el flujo guiado;
4. generar la vista previa y ejecutar el documento `304`;
5. conservar auditoría, original e idempotencia;
6. instalar, migrar, retirar, reinstalar y validar NEXORA sobre MariaDB;
7. validar el stack y la interfaz en escritorio, iPhone y PWA.

### Pruebas negativas aprobadas

1. rechazar formato no ISO con error de dominio;
2. rechazar fecha futura;
3. rechazar fecha anterior al original cuando la regla aplica;
4. rechazar período cerrado;
5. rechazar usuario sin permiso;
6. no modificar saldos en una corrección únicamente documental;
7. no eliminar ni sustituir físicamente la operación original.

### Seguridad

- no se modificó producción, Coolify, AWS, DNS, secretos, datos ni volúmenes;
- no se relajaron períodos, permisos, idempotencia, auditoría ni bloqueos;
- no se migraron registros históricos.

## Bloque UX-A — Verificación y mapa de impacto

Estado: **IMPLEMENTADO Y VALIDADO** para el alcance documental y de verificación del bloque. No clasifica como terminados los requisitos funcionales `NXR-UX-001…015`.

### Estado remoto verificado

- HEAD base de inicio: `a43214659dcd9f8039d1d93c9a5f4f2d8717501a`.
- Rama vigente: `main`.
- Rama histórica `nexora-reconstruccion`: no disponible como rama remota activa.
- PR histórico `#11`: cerrado y fusionado.
- No se creó otro repositorio, rama ni Pull Request.

### Evidencia publicada

- Mapa trazable: `docs/nexora/REDISENO_UX_MAPA_IMPACTO.md`.
- Commit del mapa: `b3bdec5f93604a14556651ee75572160ea87674b`.
- Flujos inventariados: navegación, dashboard, ingreso rápido, gasto rápido, fondos y operaciones, operación diaria, correcciones, contratos, proveedores, evidencias, reportes y buscador universal.
- Duplicaciones confirmadas: motores visibles de ingreso y gasto, contexto de proyecto, vocabulario, confirmaciones, tablas móviles y reglas condicionales.
- Modelos financieros preservados: fuente, cuenta, operación, efecto, asignación, compromiso, evidencia, numeración, auditoría, idempotencia, bloqueos y períodos.

### Clasificación inicial

- `NXR-UX-003`, `NXR-UX-007` y `NXR-UX-011`: **EXISTENTE Y REUTILIZABLE**, con alcance incompleto.
- `NXR-UX-004` y `NXR-UX-012`: **NO DEMOSTRADO** en el alcance exigido.
- Los demás requisitos `NXR-UX`: **EXISTENTE PERO DEFECTUOSO**.

### Seguridad

- producción e infraestructura no modificadas;
- código financiero no modificado;
- sin migraciones;
- sin secretos ni mecanismos temporales.

## Siguiente acción

Ejecutar `UX-B — Vocabulario y sistema de diseño`: publicar el diccionario visible único, normalizar acciones y estados prioritarios, crear componentes compartidos para etiquetas/confirmaciones/errores y establecer la base accesible que usarán los motores unificados posteriores. No continuar a UX-C mientras UX-B tenga errores críticos o pruebas fallidas.
