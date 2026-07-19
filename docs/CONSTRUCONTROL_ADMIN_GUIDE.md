# ConstruControl — Guía de administración

## Objetivo operativo

ConstruControl es la interfaz principal para la gestión residencial. ERPNext permanece como motor interno de documentos, permisos, auditoría y procesos; el trabajo cotidiano debe realizarse desde las rutas y módulos de ConstruControl.

## Navegación principal

- **Inicio:** resumen total financiero y operativo.
- **Centro de proyecto:** presupuesto, fases, contratos, materiales y avances.
- **Ingresos:** remesas, depósitos, transferencias, efectivo y conciliación.
- **Gastos:** facturas, aprobación, pagos parciales y comprobantes.
- **Cuentas por pagar:** saldos y vencimientos sincronizados desde gastos.
- **Integraciones:** sección única para conexiones esenciales y personalizadas.
- **Reportes:** consultas ejecutivas, reportes guardados y exportaciones.
- **Perfil:** información personal, seguridad, proyectos y actividad reciente.

## Tesorería

Al registrar un ingreso:

1. Seleccione el canal: remesa, depósito, transferencia, efectivo u otro.
2. Seleccione la institución financiera.
3. Complete remitente, beneficiario, cuenta y referencia según corresponda.
4. Registre monto bruto, comisión, moneda y tipo de cambio.
5. ConstruControl calculará el monto neto y el equivalente en HNL.
6. Adjunte el comprobante y actualice la conciliación.

El catálogo financiero incluye instituciones base protegidas. Pueden desactivarse, pero no eliminarse. El administrador puede cargar la imagen oficial autorizada en el campo **Logo oficial** de cada institución.

## Gastos y cuentas por pagar

1. Complete proveedor, factura, fechas, fase y centro de costo.
2. Registre subtotal, impuestos, retenciones y descuentos.
3. Envíe el gasto a aprobación.
4. El administrador o gerente puede aprobar o rechazar.
5. Registre pagos parciales hasta completar el total.
6. La cuenta por pagar se crea o actualiza automáticamente.

Los registros anulados o reembolsados permanecen en la trazabilidad y no se eliminan de forma silenciosa.

## Integraciones

La sección **Integraciones** es la única administración visible.

- Las integraciones esenciales pueden activarse o desactivarse.
- Las integraciones personalizadas pueden crearse, configurar, probar localmente, archivar o eliminar.
- Las credenciales se guardan en campos protegidos y no se devuelven al navegador.
- Las URL personalizadas deben utilizar HTTPS.
- ConstruControl no ejecuta conexiones arbitrarias a destinos locales o privados.

## Usuarios y perfiles

El usuario puede editar únicamente sus datos personales seguros. Los roles y permisos críticos se administran por el responsable del sistema. El rol empresarial visible se presenta como ADMIN, MANAGER, OPERATOR, AUDITOR o VIEWER, sin sustituirlo por el correo.

## Instalación móvil

En iPhone:

1. Abra ConstruControl en Safari.
2. Pulse Compartir.
3. Seleccione **Agregar a pantalla de inicio**.
4. Confirme el nombre ConstruControl.

En Android, use la opción **Instalar aplicación** del navegador compatible. La PWA incluye iconos PNG, modo independiente, orientación vertical y área segura para la barra inferior.

## Regla de seguridad

No edite código directamente en AWS o Coolify. Todo cambio debe existir primero en la rama `main` de GitHub y superar la validación automática antes del despliegue.
