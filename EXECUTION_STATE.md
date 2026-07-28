# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `7d37e0b6a293961470e13bdb737ebd204f91016e`
- Rama técnica: `feat/nexora-ledger-visual-semantics`
- Pull Request: `#24`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-FND-0013

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#23`.
- Commit de fusión en `main`: `7d37e0b6a293961470e13bdb737ebd204f91016e`.
- Resultado: selector de fondos operativo mediante `Autocomplete`, sin franja negra, con permisos y pruebas reales en escritorio, iPhone y PWA.

## Bloque actual — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **CERTIFICADO EN RAMA, FUSIÓN PENDIENTE**.

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

### Pruebas positivas y negativas aprobadas

- contractual: ingresos, gastos y saldos usan tonos verde, rojo y azul;
- contractual: los gráficos reciben el tono financiero correcto;
- contractual: existen **Anulado**, **Contabilizado** y canales singulares en español;
- contractual: tipo e importe anulados usan tachado;
- integración Frappe/MariaDB positiva: una transferencia activa se presenta como ingreso contabilizado y verde;
- integración Frappe/MariaDB positiva: una anulación se presenta contabilizada, roja, tachada y con canal original;
- integración Frappe/MariaDB positiva: el ingreso original compensado permanece visible y tachado;
- integración negativa: una operación de otro proyecto no aparece en la respuesta;
- permiso negativo: `Guest` no puede consultar el resumen financiero;
- navegador real: el dashboard completo aprobó escritorio Chromium, iPhone WebKit y PWA.

### Evidencia certificada

- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`;
- PR: `#24`;
- NEXORA app, contratos, instalación, rollback, escritorio, iPhone y PWA: run `30326660222`, aprobado;
- invariantes financieras Frappe/MariaDB, pruebas positivas, negativas y concurrencia: run `30326660221`, aprobado;
- linters y Semgrep: run `30326660218`, aprobado;
- Patch: run `30326660219`, aprobado;
- gobierno NEXORA: run `30326660217`, aprobado;
- documentación requerida: run `30326660214`, aprobado;
- commits semánticos: run `30326660224`, aprobado;
- controles estáticos de servidor y parches: runs `30326660216` y `30326660212`, aprobados;
- validación heredada de coexistencia: run `30326660220`, aprobado.

### Seguridad y auditoría

- no existe borrado físico de operaciones;
- no se relajan `view_reports` ni `require_project_access`;
- no se modifican saldos, efectos, estados canónicos ni reglas contables;
- el cambio añade presentación y consulta acotada de canales sobre datos ya autorizados.

### Pendiente

1. validar este cierre documental sobre el HEAD final del PR;
2. marcar el PR `#24` listo para revisión;
3. fusionar únicamente si todas las compuertas aplicables continúan aprobadas;
4. registrar el SHA de fusión en la entrega ejecutiva.

## Siguiente acción

Cerrar exclusivamente `NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022` mediante la fusión del PR `#24`; no iniciar otro bloque antes de publicar y verificar el SHA final en `main`.
