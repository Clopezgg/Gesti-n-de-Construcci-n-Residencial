# NEXORA - Bloque 2: Auditoria funcional de nexora_app

Fecha: 2026-08-02
Rama: `nexora/bloque-2-auditoria`
Alcance: auditoria estatica del paquete `nexora_app` y correcciones estructurales. Sin cambios en produccion, AWS, DNS, secretos ni datos reales.

## 1. Hallazgo critico corregido: paquetes DocType incompletos

18 directorios de DocType no incluian `__init__.py`, por lo que Frappe no puede importar de forma fiable sus controladores (`ModuleNotFoundError` al cargar el modulo del DocType, y fallos silenciosos de hooks/tests segun la ruta de importacion).

DocTypes afectados y corregidos:

- nxr_budget, nxr_budget_line
- nxr_purchase_order, nxr_purchase_order_line
- nxr_supplier_quotation, nxr_supplier_quotation_line
- nxr_goods_receipt, nxr_goods_receipt_line
- nxr_stock_transaction, nxr_stock_transaction_line
- nxr_warehouse, nxr_progress_record, nxr_quality_check
- nxr_monthly_close, nxr_integration, nxr_integration_log
- nxr_notification, nxr_notification_preference

Correccion: se agrego `__init__.py` en cada directorio, siguiendo la convencion del resto de DocTypes del paquete.

## 2. Seguridad de endpoints (verificado, sin cambios necesarios)

Se revisaron los endpoints `@frappe.whitelist` del dominio de dashboard y contratos:

- `dashboard/snapshot_query.get_executive_snapshot`: exige `require_action("view_reports")` y `require_project_access(..., action="view_reports")`.
- `dashboard/expense_query.get_expense_page`: exige `require_action("view_financial_details")` y `require_project_access(..., action="view_financial_details")`.
- `dashboard/contract_query.contract_totals` y `dashboard/pending_query.pending_commitments`: exigen `require_project_access(..., action="view_reports")`.

Todas las consultas usan parametros vinculados (`%(name)s`), sin interpolacion de entrada de usuario en SQL, y la paginacion esta acotada por `MAX_PAGE_SIZE = 100`.

## 3. Calidad estatica

`ruff check nexora_app` se ejecuta sin hallazgos tras las correcciones.

## 4. Deuda tecnica identificada (pendiente de publicar)

Los helpers `_payload`, `_text` y `_period` estan duplicados en `expense_query.py`, `snapshot_query.py`, `contract_query.py` y `pending_query.py`, pese a existir versiones centralizadas en `dashboard/query_utils.py`. La delegacion a `query_utils` esta preparada y validada localmente (conservando `MAX_PAGE_SIZE` literal y el `_period` propio de `snapshot_query`, exigidos por los tests de contrato en `nexora_app/nexora/tests/`). Queda pendiente de publicacion en un commit posterior.

## 5. Fuera de alcance

- Migracion de datos historicos: NO
- Cambios de infraestructura o secretos: NO
- Cambios de comportamiento funcional en endpoints existentes: NO
