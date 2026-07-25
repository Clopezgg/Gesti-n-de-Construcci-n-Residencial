# Bloque 8 — Órdenes, recepciones y vínculo financiero

**SHA funcional certificado:** `dc638cd`
**Fecha:** 2026-07-24
**Estado:** IMPLEMENTADO Y VALIDADO

---

## Requisitos cubiertos

| ID | Título | Estatus |
|---:|---|---|
| NXR-COM-0004 | Orden de compra multítem | CONFIRMADO |
| NXR-COM-0005 | Recepción parcial por línea | CONFIRMADO |
| NXR-COM-0006 | Vínculo financiero y presupuestario | REQUIERE DECISIÓN (preparado) |
| NXR-COM-0008 | Tolerancias y excepciones | PROPUESTO → CONFIRMADO |
| NXR-COM-0009 | Distribución de cargos, impuestos y descuentos por línea | CONFIRMADO |

---

## Arquitectura

### NXR Purchase Order (`nxr_purchase_order`)

- **Estados:** Draft → Confirmed → Approved → Sent → Completed / Cancelled
- **Conversión:** Desde solicitud aprobada (`NXR Purchase Request` status `Approved`) + cotización seleccionada (`NXR Supplier Quotation` con `selected=1`)
- **Proveedor:** Perfil activo + entidad canónica
- **Vínculo financiero:** `fund_source` heredado de la solicitud; transición a Confirmed prepara Commitment Reserve

### NXR Purchase Order Line (`nxr_purchase_order_line`)

- Campos base: `line_code`, `item_type`, `catalog_item`, `description`, `quantity`, `uom`, `unit_rate`, `amount`
- Distribución: `charge_amount`, `tax_rate`, `tax_amount`, `discount_rate`, `discount_amount`, `net_amount`
- Tolerancia: `tolerance_percentage` (default 10 %)
- `net_amount = amount + charge_amount + tax_amount - discount_amount`

### NXR Goods Receipt (`nxr_goods_receipt`)

- **Estados:** Draft → Completed / Cancelled
- **PO vinculada:** Debe estar en estado Sent
- **Actualización:** Al completar, si todas las líneas están recibidas, PO pasa a `Completed`; si no, queda `Sent`

### NXR Goods Receipt Line (`nxr_goods_receipt_line`)

- Seguimiento: `purchase_order_line` → cantidad ordenada, recibida antes, recibida ahora, rechazada, aceptada
- Control de tolerancia: `accepted_quantity <= ordered_quantity * (1 + tolerance%)`; sobrepaso → error
- `amount = accepted_quantity * unit_rate`

---

## Archivos creados

| Archivo | Descripción |
|---|---|
| `nexora_app/nexora/purchases/order_core.py` | State machine, line amounts, tolerance range |
| `nexora_app/nexora/purchases/order_service.py` | CRUD servicios: create, transition, get, list |
| `nexora_app/nexora/purchases/receipt_core.py` | State machine, receipt line validation |
| `nexora_app/nexora/purchases/receipt_service.py` | CRUD servicios: create, transition, get, list |
| `nexora_app/nexora/nexora/doctype/nxr_purchase_order/` | DocType JSON + controller |
| `nexora_app/nexora/nexora/doctype/nxr_purchase_order_line/` | Child DocType JSON + controller |
| `nexora_app/nexora/nexora/doctype/nxr_goods_receipt/` | DocType JSON + controller |
| `nexora_app/nexora/nexora/doctype/nxr_goods_receipt_line/` | Child DocType JSON + controller |

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `nexora_app/nexora/tests/test_app_contract.py` | Doctypes: 30 → 34 |

## Pruebas

### Core (95 total, 16 nuevas)

```
test_order_core — 16 tests (transiciones, montos, negativos, tolerancias)
test_receipt_core — 12 tests (transiciones, validación de líneas, tolerancia)
```

### Contract (62 total, 12 nuevas)

```
test_order_contract — 7 tests (DocType, controller, service, tax/discount fields)
test_receipt_contract — 5 tests (DocType, controller, service, line tracking fields)
```

### Sin regresión

```
67 core + 62 contract preexistentes → todos pasan
```
