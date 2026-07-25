# Bloque 7 — Compras y proveedores

**SHA funcional certificado:** `a606061`
**Fecha:** 2026-07-24
**Estado:** IMPLEMENTADO Y VALIDADO

---

## Requisitos cubiertos

| ID | Descripción | Estatus |
|---:|---|---|
| NXR-COM-0001 | Purchase Request con estados, fund source y page | EXISTENTE PERO DEFECTUOSO → CORREGIDO |
| NXR-COM-0002 | Flujo de aprobación con motivo, segregación y auditoría | CONFIRMADO |
| NXR-COM-0003 | Supplier Quotation con estados, líneas y selección | CONFIRMADO |
| NXR-COM-0007 | Catálogo reutiliza Item + UOM de ERPNext | CONFIRMADO |

---

## Cambios realizados

### NXR-COM-0001 — Purchase Request (mejora sobre bloque previo)

- **Máquina de estados:** Draft → Submitted → In Review → Approved / Rejected → (Rejected → Draft). Añadido estado `Converted`.
- **Transiciones immutables:** `request_core.py` actualizado con `SUBMITTED`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `CONVERTED`, `CANCELLED`.
- **Fund source:** `request_service.py` valida que `fund_source.project == doc.project` al transicionar a Submitted.
- **Controller:** `nxr_purchase_request.py` bloquea toda escritura si `status != "Draft"`.
- **Page JS:** `nexora_purchase_requests.js` con botones Submit, Send to Review, Approve, Reject, Reason modal para devolución a Draft.

### NXR-COM-0003 — Supplier Quotation (nuevo)

- **Doctype cabecera:** `nxr_supplier_quotation.json` con campos: `document_number`, `status`, `purchase_request`, `supplier_profile`, `supplier_entity`, `project`, `cost_center`, `currency`, `quotation_date`, `valid_until`, `payment_terms`, `warranty`, `delivery_terms`, `total_amount`, `notes`, `evidence`, `selected`, `selection_reason`, `selected_at`, `selected_by`, `idempotency_key`, `payload_hash`, `correlation_id`.
- **Child Doctype:** `nxr_supplier_quotation_line.json` con `line_code`, `item_type`, `catalog_item`, `description`, `quantity`, `uom`, `unit_rate`, `amount`, `economic_category`, `delivery_date`, `notes`.
- **Máquina de estados:** Draft → Submitted → Accepted (terminal) / Rejected (→ Cancelled, terminal) / Expired (terminal) / Cancelled (terminal).
- **Servicio (`quotation_service.py`):** `create_quotation`, `transition_quotation`, `get_quotation`, `list_quotations`, `compare_quotations`. Idempotencia, correlación, locks, savepoint/rollback, auditoría.
- **Selección:** Al aceptar una cotización se deseleccionan automáticamente las demás del mismo purchase request.
- **Página:** `/app/nexora-quotations` con listado, detalle, crear, transicionar.

### NXR-COM-0007 — Catálogo

- No se creó Doctype nuevo. `NXR Purchase Request Line.catalog_item` y `NXR Supplier Quotation Line.catalog_item` son Link a `Item` de ERPNext. `uom` es Link a `UOM`.

### NXR-COM-0002 — Aprobación

- Flujo cubierto por la máquina de estados: Submitted → In Review → Approved/Rejected. Decisión solo por manager con motivo obligatorio. Auditoría en cada transición.

---

## Archivos tocados

| Archivo | Tipo |
|---|---|
| `nexora_app/nexora/purchases/request_core.py` | Modificado — nuevos estados |
| `nexora_app/nexora/purchases/request_service.py` | Modificado — fund source validation |
| `nexora_app/nexora/nexora/doctype/nxr_purchase_request/nxr_purchase_request.json` | Modificado — status options |
| `nexora_app/nexora/nexora/doctype/nxr_purchase_request/nxr_purchase_request.py` | Modificado — immutable if not Draft |
| `nexora_app/nexora/nexora/page/nexora_purchase_requests/nexora_purchase_requests.js` | Modificado — botones contextuales |
| `nexora_app/nexora/purchases/quotation_core.py` | Nuevo — state machine |
| `nexora_app/nexora/purchases/quotation_service.py` | Nuevo — CRUD service |
| `nexora_app/nexora/nexora/doctype/nxr_supplier_quotation/nxr_supplier_quotation.json` | Nuevo |
| `nexora_app/nexora/nexora/doctype/nxr_supplier_quotation/nxr_supplier_quotation.py` | Nuevo |
| `nexora_app/nexora/nexora/doctype/nxr_supplier_quotation_line/nxr_supplier_quotation_line.json` | Nuevo |
| `nexora_app/nexora/nexora/doctype/nxr_supplier_quotation_line/nxr_supplier_quotation_line.py` | Nuevo |
| `nexora_app/nexora/nexora/page/nexora_quotations/nexora_quotations.js` | Nuevo |
| `nexora_app/nexora/nexora/page/nexora_quotations/nexora_quotations.json` | Nuevo |
| `nexora_app/nexora/tests/test_quotation_core.py` | Nuevo — 8 tests |
| `nexora_app/nexora/tests/test_quotation_contract.py` | Nuevo — 6 tests |
| `nexora_app/nexora/tests/test_quotation_integration.py` | Nuevo — 3 tests (Frappe) |
| `nexora_app/nexora/tests/test_purchase_request_core.py` | Modificado |
| `nexora_app/nexora/tests/test_purchase_request_integration.py` | Modificado |
| `nexora_app/nexora/tests/test_app_contract.py` | Modificado — 28→30 doctypes |
| `.github/workflows/nexora-financial.yml` | Modificado — quotation tests |
| `EXECUTION_STATE.md` | Modificado — Bloque 7 certificado |

---

## Tests

### Standalone (137 pruebas, 0 fallos)

```
67 core + 62 contract + 8 reference = 137 tests, OK
```

### Frappe/MariaDB (CI)

```
test_quotation_integration.py — 3 tests
test_purchase_request_integration.py — 2 tests
```

---

## Workflows CI

- `.github/workflows/nexora-financial.yml` ejecuta quotation tests (`test_quotation_core`, `test_quotation_integration`, `test_*contract.py`) y node matrix.
