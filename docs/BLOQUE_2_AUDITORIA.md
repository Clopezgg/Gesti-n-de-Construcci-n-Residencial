# NEXORA - Bloque 2: Auditoria funcional de nexora_app

Fecha: 2026-08-03
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

`ruff check nexora_app` y `ruff format --check nexora_app` (307 archivos) en verde antes y despues de los cambios.

## 4. Deduplicacion de helpers del dashboard (aplicada en este PR)

### Evidencia de duplicacion real

Los helpers `_payload`, `_text` y `_period` estaban reimplementados de forma identica en cuatro modulos del mismo dominio funcional (`nexora_app/nexora/dashboard/`), pese a existir las versiones centralizadas `payload`, `text` y `period` en `dashboard/query_utils.py`:

| Modulo | Duplicaba |
| --- | --- |
| `dashboard/expense_query.py` | `_payload`, `_text`, `_period` |
| `dashboard/snapshot_query.py` | `_payload`, `_text` |
| `dashboard/contract_query.py` | `_text` |
| `dashboard/pending_query.py` | `_text` |

### Cambios aplicados

- `dashboard/query_utils.payload` acepta un `message` opcional, de modo que cada modulo conserva su texto de error original.
- Los cuatro modulos mantienen sus nombres locales `_payload` / `_text` / `_period` y ahora delegan en `query_utils`.

### Criterios de contencion respetados

- **Mismo dominio funcional:** solo se toca `nexora_app/nexora/dashboard/`; ningun otro modulo cambia.
- **Sin cambios de comportamiento:** la delegacion es equivalente linea por linea; los mensajes de error, los limites de paginacion y las acciones de permisos son identicos.
- **Sin ruptura de compatibilidad:** se conservan las firmas y los nombres publicos/locales; se mantienen literales exigidos por las pruebas de contrato de `nexora_app/nexora/tests/` (`MAX_PAGE_SIZE = 100`, `DEFAULT_PAGE_SIZE = 25`, `require_project_access`, importaciones verificadas por marcador).
- **Excepcion deliberada:** `snapshot_query._period` conserva su implementacion propia porque usa `frappe.utils.today()` como cierre por omision y por tanto no es equivalente al helper central.

## 5. Fuera de alcance

- Migracion de datos historicos: NO
- Cambios de infraestructura o secretos: NO
- Cambios de comportamiento funcional en endpoints existentes: NO
- Validacion runtime (Frappe/MariaDB, navegador, PWA): depende del CI del repositorio; no ejecutable en este entorno.
