# Bloque 9 — Inventario y kardex

**SHA funcional certificado:** `93feed5`
**Fecha:** 2026-07-24
**Estado:** IMPLEMENTADO Y VALIDADO

## Requisitos cubiertos

| ID | Título | Estatus |
|---:|---|---|
| NXR-INV-0001 | Kardex físico por producto y bodega | CONFIRMADO |
| NXR-INV-0002 | No inventario negativo | CONFIRMADO |
| NXR-INV-0003 | Entrega a contratista | CONFIRMADO |
| NXR-INV-0004 | Consumo | CONFIRMADO |
| NXR-INV-0005 | Devolución | CONFIRMADO |
| NXR-INV-0006 | Daño o pérdida | CONFIRMADO |
| NXR-INV-0007 | Valoración canónica | CONFIRMADO |
| NXR-INV-0008 | Conteo físico | CONFIRMADO |
| NXR-INV-0009 | Custodia física por contratista | CONFIRMADO |

## Arquitectura

### Módulo `inventory/`

- `core.py` — `StockBalance` (add/remove/balance), `STOCK_TRANSACTION_TYPES`, `STOCK_TRANSACTION_TRANSITIONS`
- `service.py` — CRUD: `create_stock_transaction`, `transition_stock_transaction`, `get_stock_transaction`, `list_stock_transactions`

### DocTypes

| DocType | Tipo | Propósito |
|---|---|---|
| `NXR Warehouse` | Master | Bodega por proyecto, activa/inactiva |
| `NXR Stock Transaction` | Header | Movimiento de inventario |
| `NXR Stock Transaction Line` | Child | Item, bodega, cantidad, valor, lote, referencia |

### Tipos de movimiento

Receipt, Transfer In, Transfer Out, Issue to Contractor, Consumption, Return, Damage, Loss, Adjustment, Physical Count

### Estados

Draft → Completed / Cancelled

## Archivos creados

| Archivo | Descripción |
|---|---|
| `inventory/__init__.py` | Paquete |
| `inventory/core.py` | State machine, balance, validaciones |
| `inventory/service.py` | CRUD transaccional |
| `nxr_warehouse/` | DocType JSON + controller |
| `nxr_stock_transaction/` | DocType JSON + controller |
| `nxr_stock_transaction_line/` | Child DocType JSON + controller |
| `tests/test_inventory_core.py` | 15 tests |
| `tests/test_inventory_contract.py` | 9 tests |

## Pruebas

- **Core:** 15 tests (transiciones, money, quantity, balance, negativo)
- **Contract:** 9 tests (DocTypes, controller, fields)
- **Regresión:** 110 core + 71 contract = 181 total, 0 fallos
