# NEXORA — Presentación financiera del dashboard y Libro Central

## Requisitos trazables

- `NXR-EXEC-004`: **OBSOLETO**. Mostraba ingreso bruto y una tarjeta separada de anulaciones o reversos.
- `NXR-EXEC-005`: **IMPLEMENTADO Y VALIDADO**. El dashboard muestra el ingreso vigente neto de anulaciones y oculta la tarjeta separada, sin perder la auditoría del Libro Central.
- `NXR-EXEC-006`: **IMPLEMENTADO Y VALIDADO**. Los ingresos se presentan en verde, los gastos en rojo y los saldos disponibles en azul.
- `NXR-LGR-0021`: **IMPLEMENTADO Y VALIDADO**. El listado reciente usa etiquetas de negocio para operaciones contabilizadas, anuladas y compensadas.
- `NXR-LGR-0022`: **IMPLEMENTADO Y VALIDADO**. Cada ingreso muestra su canal real: remesa, depósito, transferencia, efectivo u otro.

## Evidencia certificada

- PR fusionado: `#24`.
- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`.
- HEAD final certificado del PR: `e6d041537cbb0d26bdf769eb737141d727e7a43e`.
- Commit de fusión publicado en `main`: `6b75f1bb834566701ede2bef5841cd76b44674c6`.
- NEXORA app, instalación, rollback, escritorio, iPhone y PWA: aprobado.
- Frappe/MariaDB, invariantes financieras, casos positivos, negativos y concurrencia: aprobado.
- Linters, Semgrep, Patch, gobierno NEXORA, documentación y commits semánticos: aprobados.

## Regla operativa de ingreso neto

`Ingresos netos = ingresos brutos del período - reversos ligados a efectos Received`.

Un reverso de gasto, reserva, transferencia, devolución u otro tipo no se descuenta de ingresos. La métrica general `reversed_hnl` permanece disponible para la alerta de movimientos compensados, FI01 y el Libro Central.

## Contrato de datos financieros

- `gross_received_hnl`: suma de efectos `Received` no reversos del período.
- `reversed_inflow_hnl`: suma absoluta de efectos reversos cuyo `reverses_effect` apunta a un efecto `Received`.
- `net_received_hnl`: diferencia entre los dos campos anteriores.
- `received_hnl`: alias ejecutivo compatible, con valor neto.

## Contrato de presentación del Libro Central

Las operaciones recientes conservan sus valores canónicos y agregan metadatos de presentación:

- `presentation_kind`: `Income`, `Expense`, `Cancellation` o el tipo canónico restante;
- `presentation_status`: `Posted` para operaciones ejecutadas, anuladas o compensadas que ya tienen asiento;
- `presentation_tone`: `income`, `expense`, `voided` o `neutral`;
- `presentation_struck`: indica que el tipo y el importe deben mostrarse tachados;
- `source_channel`: canal de la fuente asociada al efecto financiero;
- `source_channels`: lista acotada de canales vinculados a la operación.

Una operación `Analytic Adjustment` solo se presenta como **Anulado** cuando posee `reversal_of`. Los ajustes analíticos ordinarios no se reclasifican falsamente como anulaciones.

Una operación original con estado `Compensated Total` permanece como **Ingreso · canal**, pero se muestra en rojo y tachada. Su operación de reverso se muestra como **Anulado**, también en rojo y tachada. Ambas muestran **Contabilizado** porque permanecen registradas en el Libro Central.

Los documentos no se eliminan físicamente. El estado `Cancelled`, una compensación total y su reverso permanecen visibles y auditables.

## Interfaz

- **Ingresos netos**, devoluciones e ingresos por canal: verde cuando su importe es positivo.
- **Gastos ejecutados**, pagado contractual, presupuesto ejecutado y gastos por categoría: rojo.
- **Caja disponible**, reservado y saldos de fondos: azul.
- Un ingreso neto o canal negativo por anulaciones del período cambia a rojo para no comunicarlo como disponibilidad positiva.
- El KPI se denomina **Ingresos netos**.
- La tarjeta **Anulado o reversado** permanece eliminada.
- La alerta **Movimientos compensados** sigue visible cuando `reversed_hnl > 0`.
- La tabla **Últimas operaciones** muestra **Contabilizado** en lugar de exponer estados técnicos para asientos ya registrados.
- Los ingresos muestran **Ingreso · Remesa**, **Ingreso · Depósito**, **Ingreso · Transferencia**, **Ingreso · Efectivo** o **Ingreso · Otro**.

## Permisos y auditoría

No se relajan permisos. El endpoint conserva `view_reports` y la validación server-side de acceso al proyecto. Las consultas auxiliares de canales están limitadas a las diez operaciones recientes y a un máximo acotado de efectos. No se eliminan documentos ni efectos: la operación original y su reverso permanecen enlazados y auditables.

## Pruebas positivas aprobadas

1. HNL 180,000.00 brutos menos HNL 80,000.00 anulados producen HNL 100,000.00 netos.
2. Una transferencia activa se devuelve como `Income`, `Posted`, `income`, sin tachado y con canal `Transfer`.
3. Una anulación se devuelve como `Cancellation`, `Posted`, `voided`, tachada y con el canal de la fuente original.
4. Un ingreso compensado total conserva `Income`, pero se devuelve como `voided` y tachado.
5. La interfaz asigna verde a ingresos, rojo a gastos y azul a caja y fondos.
6. El navegador real renderiza el dashboard en escritorio Chromium, iPhone WebKit y PWA sin errores.

## Pruebas negativas aprobadas

1. Un reverso no ligado a `Received` no reduce ingresos netos.
2. Una anulación de otro proyecto no altera el KPI ni aparece en las operaciones recientes del proyecto consultado.
3. Un ajuste analítico sin `reversal_of` no se etiqueta como **Anulado**.
4. Un registro `Draft` no aparece en las operaciones recientes.
5. Una operación compensada o anulada no se elimina ni pierde su enlace al documento original.
6. La etiqueta **Anulado o reversado** no reaparece como tarjeta.
7. La alerta y el agregado general de reversos no desaparecen.
8. Una anulación ocurrida en un período sin ingresos puede producir ingreso neto negativo; no se fuerza a cero ni se muestra en verde.
9. Un usuario `Guest` no puede consultar el resumen financiero.

## Criterio de terminado

El código está publicado en `main`, conectado a la interfaz y respaldado por pruebas contractuales, Frappe/MariaDB, navegador real, linters, Semgrep, Patch, gobierno y documentación. Los requisitos `NXR-EXEC-006`, `NXR-LGR-0021` y `NXR-LGR-0022` quedan **IMPLEMENTADOS Y VALIDADOS** en el commit de fusión `6b75f1bb834566701ede2bef5841cd76b44674c6`.
