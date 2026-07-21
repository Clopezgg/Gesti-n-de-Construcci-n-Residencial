from __future__ import annotations

from typing import Any

import frappe

_REPORT_ROLES = (
	"System Manager",
	"ConstruControl Manager",
	"ConstruControl Auditor",
	"ConstruControl Operator",
	"ConstruControl Viewer",
)

_REPORTS: tuple[dict[str, Any], ...] = (
	{
		"name": "FI03 Cuentas por Pagar",
		"ref_doctype": "CC Payable Control",
		"query": """
            SELECT
                p.name AS "Cuenta:Link/CC Payable Control:170",
                p.provider_name AS "Proveedor:Data:190",
                p.invoice_number AS "Factura:Data:130",
                p.due_date AS "Vencimiento:Date:110",
                p.original_amount_hnl AS "Monto original:Currency:130",
                p.paid_amount_hnl AS "Pagado:Currency:120",
                p.balance_due_hnl AS "Saldo:Currency:120",
                p.payable_status AS "Estado:Data:110"
            FROM `tabCC Payable Control` p
            WHERE IFNULL(p.is_logically_deleted, 0) = 0
            ORDER BY p.due_date ASC, p.creation DESC
        """,
	},
	{
		"name": "PR02 Presupuesto vs Ejecución",
		"ref_doctype": "CC Project Profile",
		"query": """
            SELECT
                p.project_name AS "Proyecto:Data:220",
                p.original_budget_hnl AS "Presupuesto original:Currency:150",
                p.updated_budget_hnl AS "Presupuesto actualizado:Currency:160",
                p.committed_hnl AS "Comprometido:Currency:130",
                p.actual_cost_hnl AS "Costo real:Currency:130",
                p.available_budget_hnl AS "Disponible:Currency:130",
                p.physical_progress_percent AS "Avance físico:Percent:115",
                p.financial_progress_percent AS "Avance financiero:Percent:130",
                p.schedule_status AS "Cronograma:Data:110",
                p.alert_level AS "Alerta:Data:90"
            FROM `tabCC Project Profile` p
            WHERE IFNULL(p.is_logically_deleted, 0) = 0
            ORDER BY p.is_current DESC, p.modified DESC
        """,
	},
	{
		"name": "PR03 Fases y Desviaciones",
		"ref_doctype": "CC Construction Phase",
		"query": """
            SELECT
                f.name AS "Fase:Link/CC Construction Phase:180",
                f.phase_name AS "Nombre:Data:190",
                f.budget_hnl AS "Presupuesto:Currency:125",
                f.committed_hnl AS "Comprometido:Currency:125",
                f.actual_cost_hnl AS "Costo real:Currency:125",
                f.available_budget_hnl AS "Disponible:Currency:125",
                f.progress_percent AS "Avance físico:Percent:110",
                f.financial_progress_percent AS "Avance financiero:Percent:125",
                f.schedule_status AS "Cronograma:Data:110",
                f.target_end_date AS "Fin previsto:Date:105"
            FROM `tabCC Construction Phase` f
            WHERE IFNULL(f.is_logically_deleted, 0) = 0
            ORDER BY f.phase_order ASC, f.modified DESC
        """,
	},
	{
		"name": "MM03 Inventario Crítico",
		"ref_doctype": "CC Material Ledger",
		"query": """
            SELECT
                m.name AS "Material:Link/CC Material Ledger:180",
                m.material_name AS "Nombre:Data:220",
                m.current_qty AS "Existencia:Float:105",
                m.unit AS "Unidad:Data:80",
                m.low_stock_threshold AS "Mínimo:Float:95",
                m.stock_status AS "Estado:Data:105",
                m.unit_cost_hnl AS "Costo unitario:Currency:120",
                (m.current_qty * m.unit_cost_hnl) AS "Valor disponible:Currency:135"
            FROM `tabCC Material Ledger` m
            WHERE IFNULL(m.is_logically_deleted, 0) = 0
              AND m.stock_status IN ('low', 'depleted')
            ORDER BY FIELD(m.stock_status, 'depleted', 'low'), m.material_name ASC
        """,
	},
	{
		"name": "FI04 Ingresos y Conciliación",
		"ref_doctype": "CC Funding Source",
		"query": """
            SELECT
                f.name AS "Ingreso:Link/CC Funding Source:175",
                f.date_received AS "Recepción:Date:105",
                f.transaction_channel AS "Canal:Data:105",
                f.financial_institution AS "Institución:Link/CC Financial Institution:170",
                f.sender AS "Remitente:Data:170",
                f.gross_amount AS "Bruto:Currency:115",
                f.fee_amount AS "Comisión:Currency:105",
                f.net_amount_hnl AS "Neto HNL:Currency:120",
                f.spent_hnl AS "Gastado:Currency:115",
                f.available_hnl AS "Disponible:Currency:120",
                f.reconciliation_status AS "Conciliación:Data:115"
            FROM `tabCC Funding Source` f
            WHERE IFNULL(f.is_logically_deleted, 0) = 0
            ORDER BY f.date_received DESC, f.creation DESC
        """,
	},
)


def _ensure_report(definition: dict[str, Any]) -> None:
	name = definition["name"]
	existing = frappe.db.exists("Report", name)
	doc = frappe.get_doc("Report", name) if existing else frappe.new_doc("Report")
	doc.report_name = name
	doc.ref_doctype = definition["ref_doctype"]
	doc.report_type = "Query Report"
	doc.is_standard = "No"
	doc.query = definition["query"].strip()
	if doc.meta.has_field("disabled"):
		doc.disabled = 0
	existing_roles = {row.role for row in doc.get("roles") or []}
	for role in _REPORT_ROLES:
		if role not in existing_roles:
			doc.append("roles", {"role": role})
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def ensure_executive_reports() -> None:
	for definition in _REPORTS:
		_ensure_report(definition)
	frappe.clear_cache(doctype="Report")


__all__ = ["ensure_executive_reports"]
