# NEXORA — Corrección de ingresos netos del dashboard

## Requisito trazable

- `NXR-EXEC-004`: **OBSOLETO**. Mostraba ingreso bruto y una tarjeta separada de anulaciones o reversos.
- `NXR-EXEC-005`: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**. El dashboard debe mostrar el ingreso vigente neto de anulaciones de ingresos y ocultar la tarjeta separada, sin perder la auditoría del Libro Central.

## Regla operativa

`Ingresos netos = ingresos brutos del período - reversos ligados a efectos Received`.

Un reverso de gasto, reserva, transferencia, devolución u otro tipo no se descuenta de ingresos. La métrica general `reversed_hnl` permanece disponible para la alerta de movimientos compensados, FI01 y el Libro Central.

## Contrato de datos

- `gross_received_hnl`: suma de efectos `Received` no reversos del período.
- `reversed_inflow_hnl`: suma absoluta de efectos reversos cuyo `reverses_effect` apunta a un efecto `Received`.
- `net_received_hnl`: diferencia entre los dos campos anteriores.
- `received_hnl`: alias ejecutivo compatible, ahora con valor neto.

## Interfaz

- El KPI se denomina **Ingresos netos**.
- Se elimina del conjunto de KPI la tarjeta **Anulado o reversado**.
- El gráfico **Ingresos por canal** usa importes netos.
- La alerta **Movimientos compensados** sigue visible cuando `reversed_hnl > 0`.

## Permisos y auditoría

No se relajan permisos. El endpoint conserva `view_reports` y la validación server-side de acceso al proyecto. No se eliminan documentos ni efectos: la operación original y su reverso permanecen enlazados y auditables.

## Pruebas positivas

1. HNL 180,000.00 brutos menos HNL 80,000.00 anulados producen HNL 100,000.00 netos.
2. El KPI, el resumen financiero y el gráfico por canal muestran HNL 100,000.00.
3. Los campos bruto, reversado específico y neto permanecen disponibles en la respuesta para trazabilidad.

## Pruebas negativas

1. Un reverso no ligado a `Received` no reduce ingresos netos.
2. Una anulación de otro proyecto no altera el KPI del proyecto consultado.
3. La etiqueta **Anulado o reversado** no se renderiza como tarjeta.
4. La alerta y el agregado general de reversos no desaparecen.
5. Una anulación ocurrida en un período sin ingresos puede producir ingreso neto negativo para ese período; no se fuerza a cero.

## Criterio de terminado

La corrección solo podrá cambiar a **IMPLEMENTADO Y VALIDADO** cuando exista commit publicado, PR, pruebas puras/contractuales aprobadas, integración Frappe/MariaDB aprobada y SHA verificable registrado en `EXECUTION_STATE.md`.
