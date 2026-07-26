# NEXORA — Entrega final

## Identificación

- Producto: **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama final: `main`
- Versión de entrega: se deriva de `nexora_app/nexora/__init__.py`.
- SHA final: lo inserta y demuestra el workflow `NEXORA final acceptance and delivery` para cada ejecución.
- Artefacto: `NEXORA-ENTREGA-FINAL-<VERSION>-<SHA_CORTO>.zip`.

## Arquitectura entregada

NEXORA es la experiencia principal visible. Frappe/ERPNext funciona como motor interno para persistencia, permisos, workflows, DocTypes, instalación y migraciones. El producto integra fondos, operaciones, proyectos, contratos, proveedores, compras, inventario, presupuestos, evidencias, avance, reportes, usuarios y cierres sin crear un segundo motor financiero.

## Criterios obligatorios

La entrega solamente se considera aprobada cuando, sobre el mismo SHA de `main`:

1. aprueba `ConstruControl production validation`;
2. aprueba `NEXORA app`, incluido Frappe real, escritorio, WebKit/iPhone y PWA;
3. aprueban invariantes financieras, gobierno, linters y seguridad;
4. aprueba `NEXORA final acceptance and delivery`;
5. se genera el ZIP y su SHA-256 verificable;
6. se ejecuta `NEXORA live deployment verification` contra la URL real y el SHA esperado;
7. no quedan cambios necesarios fuera de `main`.

## Recorridos cubiertos

- ingreso/remesa/depósito y creación de fuente;
- gasto y operación financiera con vista previa;
- contratos, anticipos, estimaciones, pagos y retenciones;
- proveedores, solicitudes, cotizaciones, órdenes y recepciones;
- inventario y kardex;
- presupuestos, compromisos y ejecución;
- avance y evidencias;
- estados de cuenta, reportes y conciliación;
- navegación por proyecto, permisos y rechazo server-side;
- escritorio, iPhone/WebKit y PWA.

## Seguridad de la entrega

El paquete excluye archivos `.env` reales, claves privadas, certificados, credenciales, datos productivos y respaldos privados. Incluye únicamente archivos rastreados por Git y documentación/configuración segura de ejemplo.

## Estado honesto

Este documento no certifica por sí solo la entrega. La certificación corresponde al resultado verde de los workflows del SHA exacto, al artefacto generado por GitHub Actions y a la comprobación del SHA realmente desplegado. Cualquier job rojo o diferencia de SHA rechaza automáticamente la entrega hasta ser corregido.
