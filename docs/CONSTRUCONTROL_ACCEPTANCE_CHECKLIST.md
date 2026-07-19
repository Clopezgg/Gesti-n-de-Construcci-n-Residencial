# ConstruControl — Lista de aceptación final

Esta lista debe completarse con la versión exacta desplegada.

## Arquitectura

- [ ] ConstruControl es la interfaz visible principal.
- [ ] ERPNext funciona como motor interno sin navegación paralela innecesaria.
- [ ] Solo existe una sección visible llamada Integraciones.
- [ ] GitHub `main` contiene todos los cambios desplegados.
- [ ] No existen parches manuales permanentes en AWS o Coolify.

## Datos y migraciones

- [ ] El contrato runtime se valida antes de modificar MariaDB.
- [ ] La huella SHA-256 del contrato instalado queda registrada.
- [ ] Los datos migrados existentes permanecen disponibles.
- [ ] No se duplican registros al repetir una migración idempotente.
- [ ] No se eliminan físicamente usuarios duplicados durante la consolidación.
- [ ] Existe respaldo verificado antes de una importación real.

## Escritorio

- [ ] Menú lateral ConstruControl visible.
- [ ] Encabezado propio con regresar, inicio y perfil.
- [ ] Formularios y listas conservan la identidad visual del producto.
- [ ] Los módulos de ERPNext no necesarios no compiten con la navegación principal.
- [ ] Cada formulario tiene Cerrar, Cancelar cambios, Guardar y Guardar y nuevo.

## Móvil y PWA

- [ ] Barra inferior operativa.
- [ ] Menú Más muestra los módulos adicionales.
- [ ] Formularios se adaptan a una columna.
- [ ] Modales tienen botón Cerrar.
- [ ] `apple-touch-icon-180.png` carga correctamente.
- [ ] Iconos 192 y 512 están presentes.
- [ ] El manifiesto abre `/app/construcontrol-dashboard` en modo independiente.
- [ ] La instalación en iPhone muestra el icono actualizado después de eliminar y volver a agregar el acceso anterior.

## Usuarios

- [ ] El perfil muestra rol empresarial, nombre, seguridad, proyectos y actividad.
- [ ] El correo no reemplaza visualmente el rol.
- [ ] El usuario solo puede cambiar sus datos personales permitidos.
- [ ] Los permisos críticos siguen bajo administración autorizada.

## Ingresos y tesorería

- [ ] Remesa, depósito, transferencia, efectivo y otros ingresos están disponibles.
- [ ] El catálogo financiero permite logo oficial, color y capacidades.
- [ ] Se calculan bruto, comisión, neto, tipo de cambio y neto HNL.
- [ ] La referencia es obligatoria cuando corresponde.
- [ ] La conciliación exige fecha de recepción.
- [ ] Instituciones esenciales pueden desactivarse, pero no eliminarse.

## Gastos y cuentas por pagar

- [ ] Factura, vencimiento, orden, centro de costo y comprobantes están disponibles.
- [ ] Se calculan subtotal, impuestos, retenciones, descuentos y total.
- [ ] Existen aprobación, rechazo y motivo.
- [ ] Se admiten pagos parciales.
- [ ] El saldo pendiente se calcula automáticamente.
- [ ] Las facturas duplicadas por proveedor se bloquean.
- [ ] La cuenta por pagar se sincroniza sin eliminar historial.

## Construcción

- [ ] Centro de proyecto disponible.
- [ ] Presupuesto original y actualizado visibles.
- [ ] Costos reales, compromisos y saldo disponibles.
- [ ] Avance físico y financiero calculados.
- [ ] Fases atrasadas o en riesgo generan alertas.
- [ ] Contratos, materiales y avances tienen acceso directo.

## Integraciones

- [ ] Integraciones esenciales protegidas.
- [ ] Integraciones personalizadas se pueden crear y configurar.
- [ ] Activar y desactivar funciona.
- [ ] Archivar funciona.
- [ ] Eliminar exige escribir ELIMINAR.
- [ ] Las credenciales no se devuelven al navegador.
- [ ] Las URL externas deben usar HTTPS.

## Panel y reportes

- [ ] El inicio muestra ingresos, gastos, caja, compromisos, presupuesto y cuentas por pagar.
- [ ] Muestra avance físico y financiero.
- [ ] Muestra alertas, inventario crítico y actividad.
- [ ] FI03, FI04, PR02, PR03 y MM03 están disponibles.
- [ ] Los reportes pueden filtrarse, imprimirse y exportarse mediante Frappe.

## Seguridad y entrega

- [ ] Todos los validadores finalizan sin errores.
- [ ] Todas las pruebas `test_*_standalone.py` finalizan sin errores.
- [ ] Todo Python compila.
- [ ] Todo JavaScript pasa `node --check`.
- [ ] Docker Compose es válido.
- [ ] La imagen `linux/amd64` se construye correctamente.
- [ ] El contenedor inicia con usuario `frappe`.
- [ ] Los healthchecks terminan saludables.
- [ ] El ZIP de liberación y su SHA-256 se generan.
