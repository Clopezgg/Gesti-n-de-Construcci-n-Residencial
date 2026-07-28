# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `7d37e0b6a293961470e13bdb737ebd204f91016e`
- Rama técnica: `feat/nexora-ledger-visual-semantics`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-FND-0013

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#23`.
- Commit de fusión en `main`: `7d37e0b6a293961470e13bdb737ebd204f91016e`.
- Resultado: selector de fondos operativo mediante `Autocomplete`, sin franja negra, con permisos y pruebas reales en escritorio, iPhone y PWA.

## Bloque actual — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**.

### Decisión confirmada

- ingresos en verde;
- gastos en rojo;
- caja y saldos disponibles en azul;
- anulaciones, cancelaciones y compensaciones totales en rojo y tachadas;
- operaciones ya asentadas con estado visible **Contabilizado**;
- ingresos identificados por remesa, depósito, transferencia, efectivo u otro.

### Implementación

- el dashboard asigna tonos financieros explícitos a KPI, gráficos y saldos;
- los gastos por categoría usan rojo y los ingresos por canal usan verde;
- un ingreso neto negativo por anulaciones se presenta en rojo;
- las operaciones recientes reciben metadatos server-side de clase, estado, tono, tachado y canal;
- `Analytic Adjustment` se muestra como **Anulado** solo cuando enlaza `reversal_of`;
- la operación original `Compensated Total` permanece visible, roja y tachada;
- el reverso permanece visible como **Anulado**, rojo y tachado;
- `Executed`, `Cancelled`, `Compensated Partial` y `Compensated Total` se presentan como **Contabilizado** sin alterar su estado canónico;
- las operaciones `Draft` continúan excluidas;
- las operaciones `Cancelled` dejan de ocultarse para conservar visibilidad de auditoría;
- la consulta de canales está acotada a las operaciones recientes y sus efectos.

### Pruebas incorporadas

- contractual: ingresos, gastos y saldos usan tonos verde, rojo y azul;
- contractual: los gráficos reciben el tono financiero correcto;
- contractual: existen **Anulado**, **Contabilizado** y canales singulares en español;
- contractual: tipo e importe anulados usan tachado;
- integración Frappe/MariaDB positiva: una transferencia activa se presenta como ingreso contabilizado y verde;
- integración Frappe/MariaDB positiva: una anulación se presenta contabilizada, roja, tachada y con canal original;
- integración Frappe/MariaDB positiva: el ingreso original compensado permanece visible y tachado;
- integración negativa: una operación de otro proyecto no aparece en la respuesta;
- navegador existente: el dashboard completo debe continuar aprobando escritorio Chromium, iPhone WebKit y PWA.

### Seguridad y auditoría

- no existe borrado físico de operaciones;
- no se relajan `view_reports` ni `require_project_access`;
- no se modifican saldos, efectos, estados canónicos ni reglas contables;
- el cambio añade presentación y consulta acotada de canales sobre datos ya autorizados.

### Pendiente

1. publicar commits semánticos en la rama;
2. abrir PR hacia `main`;
3. aprobar contratos, JavaScript, Frappe/MariaDB, linters, Semgrep, Patch y navegador real;
4. corregir cualquier fallo real;
5. fusionar y registrar el SHA final en `main`.

## Siguiente acción

Certificar exclusivamente `NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022`; no iniciar otro bloque antes de cerrar PR, pruebas y SHA verificable.
