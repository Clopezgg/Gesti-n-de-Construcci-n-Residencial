# NEXORA — Manual de usuario

## Inicio

Al iniciar sesión, NEXORA abre el dashboard principal. Seleccione el proyecto activo antes de registrar o consultar operaciones. Las tarjetas muestran saldos, presupuesto ejecutado, cuentas pendientes, avance, contratos, alertas y evidencias.

## Registrar un ingreso, remesa o depósito

1. Pulse **Registrar ingreso** en la cabecera de NEXORA.
2. Seleccione el proyecto.
3. Escriba el monto recibido.
4. Elija cómo se recibió: remesa, efectivo, depósito bancario, transferencia u otro.
5. Indique el remitente u origen.
6. Complete banco/remesadora, cuenta o número de referencia únicamente cuando existan.
7. Pulse **Guardar ingreso**.
8. Compruebe el número generado y el saldo actualizado.

NEXORA registra internamente la fuente, la trazabilidad y el efecto financiero. El usuario no tiene que seleccionar tipos técnicos de operación, servicios canónicos, secuencias ni documentos internos.

## Registrar un gasto

1. Pulse **Registrar gasto** en la cabecera de NEXORA.
2. Seleccione el proyecto.
3. Escriba el monto pagado.
4. Seleccione el fondo que pagará; NEXORA muestra únicamente fuentes con saldo disponible.
5. Seleccione la categoría del gasto.
6. Complete centro de costo, contratista/proveedor, medio de pago, referencia, concepto y comprobante según corresponda.
7. Pulse **Guardar gasto**.
8. NEXORA comprueba el saldo, genera la vista previa en servidor y ejecuta la operación atómica.
9. Compruebe el número de documento y el saldo actualizado.

Para operaciones especiales como reclasificaciones, devoluciones, anticipos, compromisos o correcciones autorizadas, utilice **Fondos y operaciones**, donde permanece disponible el flujo avanzado con vista previa detallada.

## Contratos y pagos

Abra **Contratos** para consultar el expediente, registrar adendas, anticipos, estimaciones, pagos, retenciones, devoluciones y liquidación. NEXORA bloquea sobrepagos, modificaciones terminales y acciones sin permiso.

## Compras y proveedores

Use **Proveedores** para consultar perfiles y cumplimiento. Use **Solicitudes de compra** para crear líneas, enviar, aprobar/rechazar, comparar cotizaciones y convertir a orden. Las recepciones parciales o completas actualizan compromisos, cuentas e inventario según el flujo aprobado.

## Evidencias y avance

Desde **Evidencias** puede adjuntar fotografías o documentos autorizados vinculados al proyecto. En **Avance** registre el progreso físico y su revisión. Los originales no deben eliminarse destructivamente.

## Reportes

En **Reportes** seleccione proyecto y tipo de reporte: estado de cuenta por fuente, entidad o contrato; reporte financiero; costos; o conciliación. Los totales provienen del Libro Central y servicios canónicos.

## Correcciones

No edite registros ejecutados directamente. Utilice los flujos autorizados de reversión, devolución, reclasificación o compensación. Los cierres mensuales son inmutables y las correcciones posteriores quedan auditadas.

## Uso en iPhone/PWA

Abra NEXORA en Safari, inicie sesión y utilice **Añadir a pantalla de inicio**. Los botones **Registrar ingreso** y **Registrar gasto** permanecen disponibles dentro de la navegación principal. Mantenga conexión para operaciones que escriben datos. Una operación solo se considera registrada después de recibir confirmación del servidor.

## Errores

Ante un error, no repita varias veces el botón. Revise el mensaje mostrado y confirme primero si el documento o saldo fue actualizado. Las operaciones utilizan idempotencia para evitar duplicaciones, pero la confirmación visible sigue siendo obligatoria.
