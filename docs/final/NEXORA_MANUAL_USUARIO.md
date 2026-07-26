# NEXORA — Manual de usuario

## Inicio

Al iniciar sesión, NEXORA abre el dashboard principal. Seleccione el proyecto activo antes de registrar o consultar operaciones. Las tarjetas muestran saldos, presupuesto ejecutado, cuentas pendientes, avance, contratos, alertas y evidencias.

## Registrar un ingreso, remesa o depósito

1. Desde el dashboard pulse **Registrar ingreso**.
2. Seleccione el proyecto.
3. En **Alta rápida de fuente**, elija el canal: remesa, efectivo, depósito, transferencia u otro.
4. Indique importe, moneda, tasa cuando aplique, remitente/procedencia y referencia bancaria cuando corresponda.
5. Pulse **Registrar fuente**.
6. Compruebe el mensaje de confirmación y el saldo actualizado.

## Registrar un gasto

1. Desde el dashboard pulse **Registrar gasto**.
2. Seleccione proyecto, tipo de operación, clasificación económica e importe.
3. Complete centro de costo, beneficiario, medio de pago, referencia y evidencia únicamente cuando el tipo de operación lo requiera.
4. Distribuya el importe entre las fuentes disponibles.
5. Pulse **Vista previa** y revise saldo antes/después, efectos analíticos y documento a generar.
6. Pulse **Ejecutar operación**.

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

Abra NEXORA en Safari, inicie sesión y utilice **Añadir a pantalla de inicio**. Mantenga conexión para operaciones que escriben datos. La PWA puede conservar recursos visuales, pero una operación solo se considera registrada después de recibir confirmación del servidor.

## Errores

Ante un error, no repita varias veces el botón. Revise el mensaje mostrado y confirme primero si el documento o saldo fue actualizado. Las operaciones utilizan idempotencia para evitar duplicaciones, pero la confirmación visible sigue siendo obligatoria.
