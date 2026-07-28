# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- Pull Request cerrado: `#24`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#24`.
- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`.
- HEAD final certificado del PR: `e6d041537cbb0d26bdf769eb737141d727e7a43e`.
- Commit de fusión publicado en `main`: `6b75f1bb834566701ede2bef5841cd76b44674c6`.

### Resultado funcional

- ingresos en verde;
- gastos en rojo;
- caja y saldos disponibles en azul;
- anulaciones, cancelaciones y compensaciones totales en rojo y tachadas;
- operaciones asentadas con estado visible **Contabilizado**;
- ingresos identificados como **Ingreso · Remesa**, **Ingreso · Depósito**, **Ingreso · Transferencia**, **Ingreso · Efectivo** o **Ingreso · Otro**;
- `Analytic Adjustment` se presenta como **Anulado** únicamente cuando enlaza `reversal_of`;
- la operación original compensada y su reverso permanecen visibles, enlazados y auditables;
- los borradores permanecen excluidos;
- no existe borrado físico de operaciones.

### Pruebas positivas y negativas aprobadas

- contractual: ingresos, gastos y saldos usan tonos verde, rojo y azul;
- contractual: gráficos, tipo e importe usan el tono y tachado correctos;
- integración Frappe/MariaDB: una transferencia activa se presenta como ingreso contabilizado y verde;
- integración Frappe/MariaDB: una anulación se presenta contabilizada, roja, tachada y con su canal original;
- integración Frappe/MariaDB: el ingreso original compensado permanece visible y tachado;
- aislamiento negativo: una operación de otro proyecto no aparece;
- permiso negativo: `Guest` no puede consultar el resumen financiero;
- navegador real: escritorio Chromium, iPhone WebKit y PWA aprobados;
- instalación, desinstalación, reinstalación, migración, rollback, concurrencia y staging aprobados.

### Evidencia CI

- NEXORA app: run `30326660222`, aprobado;
- invariantes financieras Frappe/MariaDB: run `30326660221`, aprobado;
- linters y Semgrep: run `30326660218`, aprobado;
- Patch: run `30326660219`, aprobado;
- gobierno NEXORA: run `30326660217`, aprobado;
- documentación requerida: run `30326660214`, aprobado;
- commits semánticos: run `30326660224`, aprobado;
- controles estáticos: runs `30326660216` y `30326660212`, aprobados;
- validación de coexistencia: run `30326660220`, aprobado;
- validación final del HEAD documental: NEXORA app, Frappe/MariaDB, Patch, linters, gobierno y documentación aprobados.

### Seguridad y auditoría

- no se relajaron `view_reports` ni `require_project_access`;
- no se modificaron saldos, efectos, estados canónicos ni reglas contables;
- no se modificó producción ni infraestructura;
- los cambios son de presentación y consulta acotada sobre datos autorizados.

## Siguiente acción

Desplegar `main` desde el SHA `6b75f1bb834566701ede2bef5841cd76b44674c6` en Coolify únicamente con respaldo verificable, plan de rollback y validación posterior del dashboard, Libro Central, escritorio, iPhone y PWA.
