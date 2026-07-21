from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from erpnext.construcontrol.access import require_construcontrol_access
from erpnext.construcontrol.construction import get_project_center
from erpnext.construcontrol.reporting import get_reporting_summary

_LABELS = {
	"on_track": "En tiempo",
	"at_risk": "En riesgo",
	"delayed": "Atrasado",
	"completed": "Completado",
	"not_started": "Sin iniciar",
	"remittance": "Remesas",
	"deposit": "Depósitos",
	"transfer": "Transferencias",
	"cash": "Efectivo",
	"other": "Otros",
	"labor": "Mano de obra",
	"materials": "Materiales",
	"transport": "Transporte",
	"equipment": "Equipo y maquinaria",
	"services": "Servicios",
	"pending": "Pendiente",
	"partial": "Pago parcial",
	"paid": "Pagado",
	"overdue": "Vencido",
	"cancelled": "Anulado",
	"reimbursed": "Reembolsado",
	"CREATE": "Creación",
	"UPDATE": "Actualización",
	"APPROVE": "Aprobación",
	"REJECT": "Rechazo",
	"PAY": "Pago",
	"CANCEL": "Anulación",
	"REVERSE": "Reversión",
	"DELETE": "Eliminación",
}


def _label(value: Any) -> str:
	raw = str(value or "").strip()
	return _LABELS.get(
		raw,
		_LABELS.get(raw.lower(), raw.replace("_", " ").strip().capitalize() or "Sin clasificar"),
	)


def _filters(project: str) -> dict[str, Any]:
	return {"is_logically_deleted": 0, "project": project}


def _fields(doctype: str, requested: list[str]) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [field for field in requested if field == "name" or meta.has_field(field)]


def _recent_activity(project: str) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"CC Audit Log",
		filters=_filters(project),
		fields=_fields(
			"CC Audit Log",
			[
				"name",
				"posting_date",
				"event_at",
				"action",
				"module",
				"record_type",
				"record_id",
				"actor_name",
				"actor_role",
				"reason",
				"origin",
			],
		),
		order_by="creation desc",
		limit_page_length=10,
	)
	return [
		{
			**dict(row),
			"action_label": _label(row.get("action")),
			"record_type_label": str(row.get("module") or row.get("record_type") or "Registro"),
		}
		for row in rows[:3]
	]


def _empty_dashboard(projects: list[dict[str, Any]]) -> dict[str, Any]:
	return {
		"project": None,
		"project_name": None,
		"projects": projects,
		"financial": {
			"received_hnl": 0.0,
			"expense_total_hnl": 0.0,
			"paid_hnl": 0.0,
			"cash_available_hnl": 0.0,
			"pending_expenses_hnl": 0.0,
			"payable_balance_hnl": 0.0,
			"contract_value_hnl": 0.0,
			"contract_balance_hnl": 0.0,
			"original_budget_hnl": 0.0,
			"updated_budget_hnl": 0.0,
			"committed_hnl": 0.0,
			"actual_cost_hnl": 0.0,
			"available_budget_hnl": 0.0,
			"inventory_value_hnl": 0.0,
		},
		"progress": {
			"physical_percent": 0.0,
			"financial_percent": 0.0,
			"schedule_status": "not_started",
			"schedule_status_label": _label("not_started"),
			"phase_count": 0,
			"delayed_phase_count": 0,
			"at_risk_phase_count": 0,
		},
		"counts": {
			"income_count": 0,
			"expense_count": 0,
			"contract_count": 0,
			"payable_count": 0,
			"low_stock_count": 0,
			"overdue_count": 0,
			"quality_issue_count": 0,
			"closing_count": 0,
		},
		"charts": {"expenses_by_category": [], "income_by_channel": []},
		"alerts": [
			{
				"level": "normal",
				"title": "Sin proyecto asignado",
				"message": _("No tiene proyectos disponibles para consultar."),
				"route": ["construcontrol-profile"],
			}
		],
		"low_stock": [],
		"overdue_payables": [],
		"recent_activity": [],
	}


@frappe.whitelist()
def get_executive_dashboard(project: str | None = None) -> dict[str, Any]:
	"""Return BI01 from the same canonical reporting service used by exports and reports."""
	require_construcontrol_access()
	project_summary = get_project_center(project)
	project = project_summary.get("project")
	if not project:
		return _empty_dashboard(project_summary.get("projects", []))

	summary = get_reporting_summary(date_from="2000-01-01", date_to=today(), project=project)
	totals = summary["totals"]
	counts = summary["counts"]
	payables = frappe.get_all(
		"CC Payable Control",
		filters=_filters(project),
		fields=_fields(
			"CC Payable Control",
			[
				"name",
				"provider_name",
				"invoice_number",
				"due_date",
				"balance_due_hnl",
				"payable_status",
			],
		),
		order_by="due_date asc, creation desc",
	)
	payable_rows = [
		row
		for row in payables
		if str(row.get("payable_status") or "") not in {"paid", "cancelled", "reimbursed"}
	]
	today_date = getdate(today())
	overdue = [
		{**dict(row), "payable_status_label": _label(row.get("payable_status"))}
		for row in payable_rows
		if row.get("due_date") and getdate(row.get("due_date")) < today_date
	]
	low_stock = summary.get("low_stock") or []
	quality_issues = summary.get("quality_issues") or []
	latest_closing = summary.get("latest_closing")

	alerts: list[dict[str, Any]] = []
	if flt(project_summary.get("available_budget_hnl")) < 0:
		alerts.append(
			{
				"level": "critical",
				"title": "Presupuesto excedido",
				"message": _("Los compromisos superan el presupuesto actualizado."),
				"route": ["construcontrol-project-center"],
			}
		)
	if overdue:
		alerts.append(
			{
				"level": "critical",
				"title": "Cuentas vencidas",
				"message": _("{0} cuenta(s) vencida(s).").format(len(overdue)),
				"route": ["List", "CC Payable Control"],
			}
		)
	if low_stock:
		alerts.append(
			{
				"level": "attention",
				"title": "Inventario crítico",
				"message": _("{0} material(es) requieren atención.").format(len(low_stock)),
				"route": ["List", "CC Material Ledger"],
			}
		)
	if quality_issues:
		alerts.append(
			{
				"level": "critical",
				"title": "Calidad pendiente",
				"message": _("{0} hallazgo(s) de calidad requieren seguimiento.").format(len(quality_issues)),
				"route": ["List", "CC Progress Update"],
			}
		)
	if not latest_closing:
		alerts.append(
			{
				"level": "attention",
				"title": "Sin cierre semanal",
				"message": _("El proyecto todavía no dispone de un cierre semanal cerrado."),
				"route": ["construcontrol-weekly-closing"],
			}
		)
	if not alerts:
		alerts.append(
			{
				"level": "normal",
				"title": "Operación controlada",
				"message": _("No se detectaron alertas críticas."),
				"route": ["construcontrol-project-center"],
			}
		)

	schedule_status = str(project_summary.get("schedule_status") or "on_track")
	return {
		"project": project,
		"project_name": project_summary.get("project_name"),
		"projects": project_summary.get("projects", []),
		"financial": {
			"received_hnl": totals["received_hnl"],
			"expense_total_hnl": totals["recognized_expense_hnl"],
			"paid_hnl": totals["spent_hnl"],
			"cash_available_hnl": totals["available_hnl"],
			"pending_expenses_hnl": totals["pending_hnl"],
			"payable_balance_hnl": round(sum(flt(row.get("balance_due_hnl")) for row in payable_rows), 2),
			"contract_value_hnl": totals["contracted_hnl"],
			"contract_balance_hnl": totals["contract_balance_hnl"],
			"original_budget_hnl": project_summary.get("original_budget_hnl", 0),
			"updated_budget_hnl": project_summary.get("updated_budget_hnl", 0),
			"committed_hnl": project_summary.get("committed_hnl", 0),
			"actual_cost_hnl": project_summary.get("actual_cost_hnl", 0),
			"available_budget_hnl": project_summary.get("available_budget_hnl", 0),
			"inventory_value_hnl": totals["inventory_value_hnl"],
		},
		"progress": {
			"physical_percent": project_summary.get("physical_progress_percent", 0),
			"financial_percent": project_summary.get("financial_progress_percent", 0),
			"schedule_status": schedule_status,
			"schedule_status_label": _label(schedule_status),
			"phase_count": project_summary.get("phase_count", 0),
			"delayed_phase_count": project_summary.get("delayed_phase_count", 0),
			"at_risk_phase_count": project_summary.get("at_risk_phase_count", 0),
		},
		"counts": {
			"income_count": counts["funds"],
			"expense_count": counts["expenses"],
			"contract_count": counts["contracts"],
			"payable_count": len(payable_rows),
			"low_stock_count": counts["low_stock"],
			"overdue_count": len(overdue),
			"quality_issue_count": counts["quality_issues"],
			"closing_count": counts["closings"],
		},
		"charts": {
			"expenses_by_category": summary.get("expense_categories", []),
			"income_by_channel": summary.get("income_channels", []),
		},
		"alerts": alerts[:5],
		"low_stock": low_stock[:3],
		"overdue_payables": overdue[:3],
		"recent_activity": _recent_activity(project),
		"latest_closing": latest_closing,
	}


__all__ = ["get_executive_dashboard"]
