# NEXORA — Estado de ejecución

- Fecha: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `62ebef3e107fe3e419db18460372d6bcbadb8d99`
- Rama técnica: `fix/nexora-net-income-dashboard`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Bloque actual — NXR-EXEC-005

Estado: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**.

Decisión anterior `NXR-EXEC-004`: mostrar ingreso bruto y una tarjeta separada de anulaciones/reversos.

Corrección posterior vigente `NXR-EXEC-005`: mostrar **Ingresos netos**, ocultar la tarjeta **Anulado o reversado** y conservar alerta, FI01, Libro Central y auditoría.

### Implementado

- `gross_received_hnl`: ingreso bruto del período.
- `reversed_inflow_hnl`: solo reversos enlazados a efectos `Received`.
- `net_received_hnl`: bruto menos reversos de ingreso.
- `received_hnl`: valor ejecutivo compatible, ahora neto.
- gráfico por canal recalculado en neto;
- tarjeta separada eliminada;
- `reversed_hnl` general preservado para auditoría;
- permisos server-side `view_reports` y acceso al proyecto preservados.

### Pruebas incorporadas

- positiva: HNL 180,000.00 - HNL 80,000.00 = HNL 100,000.00;
- negativa: reversos ajenos a `Received` no reducen ingresos;
- negativa: una anulación de otro proyecto no altera el proyecto consultado;
- contractual UI: no se renderiza **Anulado o reversado**;
- contractual auditoría: se conserva **Movimientos compensados** y `reversed_hnl`;
- integración Frappe/MariaDB: KPI, resumen y canal usan el neto.

### Evidencia local

- `python -m py_compile`: aprobado para backend y pruebas nuevas;
- `node --check`: aprobado para el dashboard;
- 6 pruebas puras/contractuales nuevas: aprobadas;
- integración Frappe/MariaDB: pendiente de GitHub Actions.

### Pendiente

1. publicar commit semántico;
2. abrir PR hacia `main`;
3. aprobar compuertas CI, incluida MariaDB;
4. registrar PR, SHA y runs;
5. solo entonces declarar **IMPLEMENTADO Y VALIDADO**.

## Último bloque certificado

El bloque ejecutivo/reportes/cierre anterior permanece **IMPLEMENTADO Y VALIDADO** en el SHA funcional `59470c1579ca340a8d3a47473cb62a5f453dd1f9`, PR `#19`. La limitación histórica contractual/documental previamente declarada permanece sin cambios.

## Siguiente acción

Certificar exclusivamente `NXR-EXEC-005`; no iniciar otro bloque antes de cerrar pruebas y SHA verificable.
