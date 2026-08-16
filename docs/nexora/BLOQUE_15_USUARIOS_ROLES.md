# Bloque 15 — Usuarios, roles y segregación

**SHA funcional certificado:** `57a3438`

## Requisitos

NXR-USR-0001 a NXR-USR-0006

## Implementación

- permissions.py con 6 roles, 5 role sets, 27 acciones
- fixtures/role.json con los 5 roles NEXORA
- 18 tests de seguridad

## Segregación server-side de compras e inventario

- Solicitudes de compra siguen siendo operativas: `create_purchase_request` y `submit_purchase_request` permiten al operador preparar y enviar solicitudes sin otorgarle control sobre órdenes ni movimientos físicos.
- Órdenes de compra tienen acciones explícitas: `create_purchase_order`, `submit_purchase_order` y `approve_purchase_order`, asignadas al conjunto mínimo sensible (`System Manager`, `NEXORA Administrator`, `NEXORA Finance Manager`).
- Inventario tiene acciones propias: `manage_warehouse` para alta/gestión de bodegas, `create_stock_transaction` para captura operativa de movimientos en borrador y `submit_stock_transaction` para completar/cancelar movimientos con efecto de saldo.
- La segregación queda fijada por pruebas negativas de contrato: un usuario representado por `NEXORA Finance Operator` tiene permiso de solicitud, pero no las acciones específicas de orden ni de cierre de inventario.
