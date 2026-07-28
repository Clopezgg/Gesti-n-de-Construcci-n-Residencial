# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `6812ee55f2aa1e723d9c59ea84675bf83b673990`
- Rama técnica fusionada: `feat/nexora-operational-console-dates-accounts`
- Pull Request fusionado: `#26`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-007 / NXR-USR-0007

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR fusionado: `#25`.
- SHA funcional probado: `8ac970290df4d8cc675ab59d44ce22bd3ec85c27`.
- HEAD final certificado del PR: `deda757fa11163e5126aa0001aa20e6ade2729bf`.
- Commit de fusión publicado en `main`: `a3d47d6802944fe9dee6250e6a4d5bd4ba9126dd`.
- HEAD documental previo de `main`: `6812ee55f2aa1e723d9c59ea84675bf83b673990`.

## Bloque actual — Consola operativa, fechas, cuentas y Libro Central

Requisitos:

- `NXR-OPR-20260728-01` — fecha documental histórica;
- `NXR-OPR-20260728-02` — cuentas frecuentes reutilizables;
- `NXR-OPR-20260728-03` — consola numérica `101/102/303/304/501`;
- `NXR-LGR-20260728-01` — Libro Central operativo ampliado;
- `NXR-UX-20260728-01` — dashboard inferior compacto;
- `NXR-LGR-20260728-02` — semántica correctiva sin borrado físico.

Estado: **IMPLEMENTADO Y VALIDADO**.

### Implementación

- nueva página `nexora-operations` como consola operativa diaria;
- código `101` crea una fuente independiente y su operación de ingreso;
- código `102` ejecuta una salida contra fondos disponibles;
- códigos `303`, `304` y `501` exigen documento original y conservan auditoría;
- fecha documental visible y editable, distinta de `creation`;
- rechazo en servidor de fechas futuras, correcciones anteriores al original y meses aprobados;
- nuevo `NXR Financial Account` para reutilizar remitente, banco, cuenta, moneda y canal;
- nuevo `NXR Operation Metadata` para preservar el código numérico visible;
- Libro Central con día, fecha, documento, movimiento, contraparte, institución, cuenta enmascarada, moneda, importe y estado;
- actividad reciente limitada a tres registros con **Ver más actividad**;
- tarjetas inferiores compactas y de altura uniforme;
- accesos rápidos de ingreso y gasto dirigidos a la consola nueva;
- navegación NEXORA incorpora **Operación diaria**.

### Efectos financieros

- `101`: incrementa saldo mediante efecto `Received`;
- `102`: consume asignaciones y conserva efectos de costo/presupuesto según perfil;
- `303`: crea compensación financiera contra el original;
- `304`: crea sustitución documental con importe cero;
- `501`: crea compensación total de la porción reversible;
- ninguna operación contabilizada se elimina físicamente.

### Permisos

- cuentas frecuentes e ingresos: `create_source`;
- salidas: `execute`;
- anulaciones, correcciones y cancelaciones: `reclassify` o `cancel_source` según el documento;
- Libro Central: `preview` y acceso al proyecto;
- Auditor no puede obtener valores completos de cuentas frecuentes.

### Pruebas incorporadas

- unitarias de fecha histórica, fecha futura y secuencia temporal de correcciones;
- contratos de página, servicios, activos, códigos, columnas y ausencia de borrado físico;
- integración Frappe/MariaDB para ingreso histórico, reutilización de cuenta, mes cerrado, anulación y permiso negativo de Auditor;
- navegador actualizado para validar que los accesos rápidos abren `101` y `102` en la consola real;
- navegador actualizado para verificar Libro Central operativo y actividad limitada a tres filas.

### Evidencia publicada de certificación

- PR fusionado: `#26`.
- SHA funcional probado: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD final certificado del PR: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Commit de fusión publicado en `main`: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Linters y Semgrep: run `30362821825`, aprobado.
- NEXORA app, contrato, instalación, migración, rollback, escritorio, iPhone y PWA: run `30362821826`, aprobado.
- Frappe/MariaDB e invariantes financieras: run `30362821878`, aprobado.
- Patch: run `30362821997`, aprobado.
- Gobierno NEXORA: run `30362821743`, aprobado.
- Documentación requerida: run `30362821722`, aprobado.
- Controles estáticos y de parches: runs `30362821872`, `30362821844` y `30362821756`, aprobados.
- Validación de producción en modo seguro: run `30362821746`, aprobado.
- Commits semánticos: run `30362822144`, aprobado.
- Postgres: run `30362821724`, omitido por diseño; MariaDB es la compuerta canónica del bloque.

### Seguridad

- no se modificó producción ni infraestructura;
- no se escribieron secretos;
- no se migraron registros históricos;
- las cuentas se muestran enmascaradas fuera del servicio operativo autorizado;
- el servidor vuelve a comprobar permisos, proyecto, fecha, cierre, saldos, referencia, vista previa e idempotencia.

## Siguiente acción

El bloque funcional y su fusión están cerrados. El despliegue del HEAD vigente de `main` queda fuera de esta ejecución y solo puede realizarse con autorización expresa, respaldo verificable, rollback por SHA, validación posterior y registro de la acción.
