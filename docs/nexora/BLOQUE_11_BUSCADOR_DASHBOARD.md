# Bloque 11 — Buscador y dashboard

**SHA funcional certificado:** `3ebb2aa`
**Fecha:** 2026-07-24
**Estado:** IMPLEMENTADO Y VALIDADO

## Requisitos cubiertos

| ID | Título | Estatus |
|---:|---|---|
| NXR-UX-0005 | Buscador universal | CONFIRMADO |
| NXR-UX-0006 | Dashboard NEXORA | CONFIRMADO |

## Arquitectura

### Módulo `dashboard/`

- `service.py` — `universal_search()`, `get_dashboard_summary()`

### Páginas

| Página | Route | Propósito |
|---|---|---|
| `nexora-search` | `/app/nexora-search` | Buscador universal con filtro por ámbito |
| `nexora-dashboard` | `/app/nexora-dashboard` | Dashboard con indicadores y acciones rápidas |

### Workspace

Se agregaron shortcuts para Dashboard NEXORA y Buscador universal al workspace de NEXORA.

## Doctypes buscables

Entidad, Contrato, Perfil de contratista, Perfil de proveedor, Solicitud de compra, Orden de compra, Recepción, Presupuesto, Operación, Compromiso, Evidencia, Fuente de fondos, Movimiento de inventario (13 en total).

## Archivos creados

| Archivo | Descripción |
|---|---|
| `dashboard/__init__.py` | Paquete |
| `dashboard/service.py` | APIs whitelisted |
| `nexora-search/nexora-search.json` | Definición de página |
| `nexora-search/nexora-search.js` | JS de búsqueda |
| `nexora-dashboard/nexora-dashboard.json` | Definición de página |
| `nexora-dashboard/nexora-dashboard.js` | JS de dashboard |
| `tests/test_dashboard_contract.py` | 9 tests |

## Pruebas

- **Contract:** 9 tests (módulo, servicio, páginas, whitelisted, workspace)
- **Regresión:** 129 core + 87 contract = 216 total, 0 fallos
