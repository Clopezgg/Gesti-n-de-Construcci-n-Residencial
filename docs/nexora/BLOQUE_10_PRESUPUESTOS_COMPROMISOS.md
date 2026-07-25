# Bloque 10 — Presupuestos y compromisos

**SHA funcional certificado:** `43afd1c`
**Fecha:** 2026-07-24
**Estado:** IMPLEMENTADO Y VALIDADO

## Requisitos cubiertos

| ID | Título | Estatus |
|---:|---|---|
| NXR-PRE-0001 | Presupuesto versionado | CONFIRMADO |
| NXR-PRE-0002 | Disponibilidad presupuestaria | CONFIRMADO |
| NXR-PRE-0003 | Compromiso independiente | CONFIRMADO |
| NXR-PRE-0004 | Control de sobregiro presupuestario | CONFIRMADO |
| NXR-PRE-0005 | Reclasificación presupuestaria | CONFIRMADO |
| NXR-PRE-0006 | Pronóstico | CONFIRMADO |

## Arquitectura

### Módulo `budget/`

- `core.py` — `assert_transition()`, `compute_line_balances()`, `compute_budget_totals()`, `validate_no_overspend()`, `validate_line_amount()`
- `service.py` — `create_budget`, `activate_budget`, `amend_budget`, `close_budget`, `cancel_budget`, `check_budget_availability`

### DocTypes

| DocType | Tipo | Propósito |
|---|---|---|
| `NXR Budget` | Master | Presupuesto versionado por proyecto |
| `NXR Budget Line` | Child | Línea por categoría económica con balances |

### Estados

Draft → Active → Amended / Closed  
Draft → Cancelled

### Integración

El servicio `check_budget_availability()` permite que el módulo de compromisos (`commitments.py`) valide disponibilidad antes de crear un compromiso. El control `DEC-002` (sobregiro bloqueado) se implementa en `validate_no_overspend()`.

## Archivos creados

| Archivo | Descripción |
|---|---|
| `budget/__init__.py` | Paquete |
| `budget/core.py` | State machine, balance, validaciones |
| `budget/service.py` | CRUD transaccional |
| `nxr_budget/` | DocType JSON + controller |
| `nxr_budget_line/` | Child DocType JSON + controller |
| `tests/test_budget_core.py` | 20 tests |
| `tests/test_budget_contract.py` | 6 tests |

## Pruebas

- **Core:** 20 tests (transiciones, balance, overspend, totals, montos)
- **Contract:** 6 tests (DocTypes, controller, fields)
- **Regresión:** 129 core + 78 contract = 207 total, 0 fallos
