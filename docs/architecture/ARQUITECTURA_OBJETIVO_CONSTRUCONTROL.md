# Arquitectura objetivo de ConstruControl

## 1. Principio rector

ConstruControl es el producto visible. ERPNext/Frappe es el motor interno.

El usuario debe reconocer una sola aplicación en escritorio, móvil y PWA. Los servicios nativos de ERPNext se reutilizan cuando aportan documentos, permisos, colas, impresión, archivos, auditoría o persistencia, pero sus workspaces genéricos no constituyen la navegación primaria.

## 2. Capas

### 2.1 Presentación

- Shell único ConstruControl.
- Navegación de escritorio.
- Navegación móvil.
- Cabecera, identidad y proyecto activo.
- Acciones globales: regresar, cerrar, cancelar, guardar borrador, guardar y guardar/nuevo.
- Mensajes de error con contexto y recuperación.
- PWA con activos versionados.

### 2.2 Aplicación

- Tesorería e ingresos.
- Gastos, facturas, pagos y cuentas por pagar.
- Contratos.
- Planificación y avance.
- Materiales e inventario.
- Compras.
- Cierres.
- Reportes.
- Usuarios y seguridad.
- Integraciones.
- Migración y auditoría.

### 2.3 Dominio

Cada operación debe pertenecer, cuando corresponda, a:

```text
Proyecto
→ Fase
→ Centro de costo
→ Fuente de fondos
→ Proveedor/contratista
→ Documento financiero u operativo
→ Evidencia
→ Auditoría
```

### 2.4 Motor interno ERPNext/Frappe

- DocTypes y documentos.
- Roles y permisos.
- Archivos privados.
- Listas, consultas, impresión y exportación.
- Scheduler y workers.
- WebSocket.
- Auditoría técnica.
- API interna.

### 2.5 Persistencia

- MariaDB 10.6.
- Redis queue persistente.
- Volumen `sites` para configuración, adjuntos y respaldos.
- Volumen `logs` para diagnóstico.

## 3. Contrato de navegación

### 3.1 Regla general

Toda ruta registrada en `docs/architecture/module_inventory.json` debe activar el shell ConstruControl.

No se permitirán listas manuales divergentes entre:

- panel;
- menú lateral;
- navegación móvil;
- workspace;
- permisos visuales;
- pruebas.

La navegación se generará desde un registro común versionado.

### 3.2 Escritorio

El shell debe incluir:

- marca ConstruControl;
- proyecto activo;
- menú lateral compacto;
- búsqueda limitada a rutas autorizadas;
- alertas relevantes;
- perfil y rol;
- migas de pan;
- acciones de formulario consistentes.

### 3.3 Móvil

El shell debe incluir:

- barra inferior de cinco destinos;
- botón de creación rápida;
- menú “Más” con módulos autorizados;
- formularios por secciones o pasos;
- regreso y cierre visibles;
- respeto de `safe-area-inset`;
- tamaños táctiles mínimos de 44 px;
- funcionamiento vertical en iPhone y Android.

## 4. Contrato financiero

### 4.1 Ingresos

Tipos mínimos:

- remesa;
- depósito;
- transferencia;
- efectivo;
- aporte;
- anticipo;
- otro ingreso.

Campos mínimos:

- institución;
- remitente;
- beneficiario;
- cuenta o destino;
- referencia;
- fecha de envío;
- fecha de recepción;
- moneda original;
- tipo de cambio;
- comisión;
- monto bruto;
- monto neto HNL;
- proyecto;
- fase;
- propósito;
- estado;
- conciliación;
- comprobante;
- responsable.

### 4.2 Gastos

Campos mínimos:

- proveedor;
- categoría y subcategoría;
- proyecto y fase;
- centro de costo;
- factura;
- orden de compra;
- recepción;
- subtotal;
- impuestos;
- retenciones;
- descuentos;
- total;
- fecha y vencimiento;
- forma de pago;
- pagos parciales;
- saldo;
- fuente de fondos;
- contrato;
- aprobación;
- comprobantes;
- responsable.

Estados mínimos:

```text
Borrador
Pendiente de aprobación
Aprobado
Parcialmente pagado
Pagado
Vencido
Anulado
Reembolsado
```

## 5. Catálogo institucional e iconografía

Las instituciones financieras y remesadoras se administrarán mediante un catálogo propio.

Cada registro contendrá:

- nombre;
- alias;
- tipo;
- país;
- estado;
- icono local;
- color de marca opcional;
- fuente de procedencia;
- indicador de registro protegido;
- orden de visualización.

Reglas:

1. Los activos se almacenan en GitHub; no dependen de enlaces externos.
2. Solo se incorporan logos con fuente oficial o uso permitido.
3. Existirá icono alternativo neutral cuando no haya logo validado.
4. Efectivo, depósito, transferencia y remesa tendrán símbolos propios.
5. Los registros del sistema se desactivan; no se eliminan accidentalmente.
6. Los registros creados por el administrador se pueden eliminar con confirmación y auditoría.

## 6. Contrato de usuarios

El perfil ConstruControl complementará el usuario interno de Frappe sin duplicar credenciales.

Debe contener:

- fotografía;
- nombre completo;
- rol visible;
- teléfono;
- correo interno;
- proyectos asignados;
- permisos;
- estado;
- último acceso;
- sesiones;
- preferencias;
- idioma;
- tema;
- notificaciones;
- actividad y aprobaciones.

Las contraseñas nunca se importan ni se muestran.

## 7. Contrato de integraciones

Existirá una sola sección `Integraciones`.

Cada integración tendrá:

- nombre e icono;
- categoría;
- estado;
- configuración cifrada o referenciada mediante secretos;
- prueba de conexión;
- último uso;
- último error;
- permisos;
- registro de actividad;
- protección contra eliminación si es esencial.

No se expondrán workspaces duplicados ni enlaces técnicos de ERPNext como experiencia principal.

## 8. Contrato de PWA

La PWA debe incluir:

- manifest válido;
- iconos PNG de 192, 512 y variantes maskable;
- `apple-touch-icon` PNG de 180×180;
- nombre y nombre corto;
- color de tema;
- pantalla de inicio;
- `display: standalone`;
- service worker con versión explícita;
- estrategia de actualización que no conserve iconos obsoletos;
- exclusión de respuestas privadas o financieras de caché insegura.

## 9. Contrato de seguridad y datos

- Las autorizaciones se validan en backend.
- Ocultar un botón no sustituye un permiso.
- Las migraciones son idempotentes.
- Toda eliminación funcional sensible queda auditada.
- Los datos ya migrados se conservan.
- Los cambios de esquema usan parches o migraciones versionadas.
- Antes de cambios destructivos se crea respaldo verificable.
- Ninguna fase elimina volúmenes ni recrea la base productiva.

## 10. Contrato de CI

Una fase solo puede cerrarse cuando:

- compila Python y JavaScript;
- valida JSON, YAML y manifest;
- ejecuta pruebas unitarias;
- ejecuta pruebas de contrato del módulo;
- valida permisos;
- valida migraciones idempotentes;
- construye la imagen linux/amd64;
- no contiene secretos;
- no contiene marcadores pendientes;
- mantiene los guardrails de infraestructura.

Las fases de UX y PWA incorporarán pruebas de navegador; las fases financieras incorporarán pruebas de cálculos, estados, conciliación y duplicados.

## 11. Estrategia de evolución sin dañar producción

```text
Commit en main
→ validación estática
→ pruebas de dominio
→ construcción de imagen
→ migración idempotente
→ healthcheck
→ operación
```

Coolify y AWS no recibirán parches manuales permanentes. Las variables secretas seguirán administradas por Coolify. El repositorio contendrá la totalidad del comportamiento reproducible.
