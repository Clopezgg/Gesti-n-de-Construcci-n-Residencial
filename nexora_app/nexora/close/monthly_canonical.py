from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import stable_payload_hash
from nexora.dashboard.snapshot_query import get_executive_snapshot
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	parse_payload,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.permissions import require_action, require_project_access

MONTHLY_ENGINE_VERSION = "nexora-analytics-v3-monthly"


def _month_bounds(close_month: str) -> tuple[Any, Any]:
	try:
		month = frappe.utils.getdate(f"{close_month}-01")
	except (TypeError, ValueError):
		frappe.throw(_("El mes de cierre debe tener formato AAAA-MM."))
	if not month or month.strftime("%Y-%m") != close_month:
		frappe.throw(_("El mes de cierre debe tener formato AAAA-MM."))
	return frappe.utils.get_first_day(month), frappe.utils.get_last_day(month)


def _monthly_period_key(
	project: str | None, close_month: str, correction_of: str | None = None, key: str | None = None
) -> str:
	base = stable_payload_hash({"project": project or "ALL", "close_month": close_month})
	if correction_of:
		return f"{base}:correction:{stable_payload_hash({'original': correction_of, 'key': key or ''})}"
	return base


def _without_generated_at(value: Any) -> Any:
	if isinstance(value, Mapping):
		return {str(k): _without_generated_at(v) for k, v in value.items() if str(k) != "generated_at"}
	if isinstance(value, list):
		return [_without_generated_at(v) for v in value]
	return value


def _calculate(data: Mapping[str, Any]) -> dict[str, Any]:
	close_month = str(data.get("close_month") or "").strip()
	start_date, end_date = _month_bounds(close_month)
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="view_closings")
	snapshot = get_executive_snapshot(
		{"project": project, "from_date": start_date.isoformat(), "to_date": end_date.isoformat()}
	)
	analytics = snapshot.get("analytics", {})
	executive = snapshot.get("executive", {})
	source_totals = analytics.get("source_totals", {})
	budgets = dict(snapshot.get("budgets", {}))
	budgets.pop("lines", None)
	totals = {
		"received_hnl": executive.get("received_hnl", 0),
		"spent_hnl": executive.get("spent_hnl", 0),
		"reserved_hnl": source_totals.get("closing_reserved_hnl", 0),
		"available_hnl": executive.get("cash_available_hnl", 0),
		"committed_hnl": source_totals.get("closing_reserved_hnl", 0),
		"budget_available_hnl": budgets.get("total_available_hnl", 0),
	}
	payload = {
		"engine_version": MONTHLY_ENGINE_VERSION,
		"period": {
			"close_month": close_month,
			"start_date": start_date.isoformat(),
			"end_date": end_date.isoformat(),
		},
		"project": project,
		"totals": totals,
		"net_flow_hnl": executive.get("received_hnl", 0) - executive.get("spent_hnl", 0),
		"physical_progress": float(snapshot.get("progress", {}).get("physical_percent") or 0),
		"unreconciled_incomes": int(analytics.get("unreconciled_count") or 0),
		"counts": {
			"income_count": int(analytics.get("source_pagination", {}).get("total") or 0),
			"expense_count": int(analytics.get("expense_pagination", {}).get("total") or 0),
			"contract_count": int(analytics.get("contract_totals", {}).get("contract_count") or 0),
		},
		"contract_totals": analytics.get("contract_totals", {}),
		"budget_totals": budgets,
		"snapshot": snapshot,
		"snapshot_basis": {
			"funds": "Efectos del Libro Central con fecha de operación hasta el fin del mes.",
			"budget": budgets.get("basis"),
			"progress": "Último avance aprobado con fecha igual o anterior al cierre.",
			"pending": "Reservas financieras al fin del mes.",
		},
	}
	snapshot_hash = stable_payload_hash(_without_generated_at(payload))
	return {**payload, "snapshot_hash": snapshot_hash}


@frappe.whitelist(methods=["POST"])
def create_monthly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("save_closing")
	key = str(data.get("idempotency_key") or "").strip()
	if not key:
		frappe.throw(_("El cierre mensual requiere una clave de idempotencia."))
	project = str(data.get("project") or "").strip() or None
	close_month = str(data.get("close_month") or "").strip()
	correction_of = str(data.get("correction_of") or "").strip() or None
	period_key = _monthly_period_key(project, close_month, correction_of, key)
	calculated = _calculate(data)
	fingerprint = canonical_payload_hash(
		{
			"project": project,
			"close_month": close_month,
			"correction_of": correction_of,
			"snapshot_hash": calculated["snapshot_hash"],
		}
	)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		if not correction_of and frappe.db.exists(
			"NXR Monthly Close", {"period_key": period_key, "status": ["in", ["Closed", "Approved"]]}
		):
			frappe.throw(_("Ya existe un cierre mensual para este proyecto y período."))
		number, sequence = issue_document_number("NXR Monthly Close", key)
		totals = calculated["totals"]
		with service_write():
			close = frappe.get_doc(
				{
					"doctype": "NXR Monthly Close",
					"document_number": number,
					"status": "Draft",
					"period_key": period_key,
					"project": project,
					"close_month": close_month,
					"close_date": _month_bounds(close_month)[1],
					"total_inflows_hnl": totals["received_hnl"],
					"total_outflows_hnl": totals["spent_hnl"],
					"net_flow_hnl": calculated["net_flow_hnl"],
					"total_reserved_hnl": totals["reserved_hnl"],
					"total_committed_hnl": totals["committed_hnl"],
					"total_available_hnl": totals["available_hnl"],
					"budget_available_hnl": totals["budget_available_hnl"],
					"physical_progress": calculated["physical_progress"],
					"unreconciled_incomes": calculated["unreconciled_incomes"],
					"snapshot_json": json.dumps(calculated, ensure_ascii=False, sort_keys=True, default=str),
					"snapshot_hash": calculated["snapshot_hash"],
					"engine_version": MONTHLY_ENGINE_VERSION,
					"comments": data.get("comments"),
					"correction_of": correction_of,
					"correction_reason": data.get("correction_reason"),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, close.name)
		result = {
			"monthly_close": close.name,
			"document_number": number,
			"snapshot_hash": calculated["snapshot_hash"],
			"engine_version": MONTHLY_ENGINE_VERSION,
		}
		audit("monthly_close_created", "NXR Monthly Close", close.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Monthly Close", close.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def transition_monthly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("save_closing")
	name = str(data.get("monthly_close") or "").strip()
	target = str(data.get("status") or "").strip()
	if target not in {"In Review", "Approved", "Cancelled"}:
		frappe.throw(_("Transición de cierre mensual no permitida."))
	close = frappe.get_doc("NXR Monthly Close", name)
	require_project_access(close.project, action="save_closing")
	if close.status in {"Approved", "Cancelled"}:
		frappe.throw(_("Un cierre mensual terminal no puede modificarse directamente."))
	if target == "Approved":
		calculated = _calculate({"project": close.project, "close_month": close.close_month})
		if calculated["snapshot_hash"] != close.snapshot_hash:
			frappe.throw(_("La fotografía financiera del cierre cambió; genere nuevamente el cierre."))
	with service_write():
		close.status = target
		if target == "Approved":
			close.closed_by = frappe.session.user
			close.close_date = _month_bounds(close.close_month)[1]
			close.closed_at = frappe.utils.now_datetime()
		close.save(ignore_permissions=True)
	result = {"monthly_close": close.name, "status": close.status, "snapshot_hash": close.snapshot_hash}
	# Hallazgo real de auditoría: `create_monthly_close`, en este mismo archivo, ya
	# audita la creación del cierre, pero la transición de estado —incluida la
	# aprobación y la cancelación, ambas terminales— nunca dejó rastro en
	# `NXR Audit Event`. Mismo hueco que ya se cerró para `register_integration`.
	audit(
		"monthly_close_transitioned",
		"NXR Monthly Close",
		close.name,
		canonical_payload_hash(result),
		correlation(data),
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def correct_monthly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("save_closing")
	original_name = str(data.get("monthly_close") or "").strip()
	reason = str(data.get("correction_reason") or "").strip()
	if not original_name or len(reason) < 10:
		frappe.throw(_("Seleccione el cierre y explique la corrección con al menos 10 caracteres."))
	original = frappe.get_doc("NXR Monthly Close", original_name)
	require_project_access(original.project, action="save_closing")
	if original.status != "Approved":
		frappe.throw(_("Solo un cierre mensual aprobado puede corregirse mediante un documento enlazado."))
	data = {
		**data,
		"project": original.project,
		"close_month": original.close_month,
		"correction_of": original.name,
		"comments": data.get("comments") or "",
	}
	result = create_monthly_close(data)
	correction = frappe.get_doc("NXR Monthly Close", result["monthly_close"])
	with service_write():
		correction.status = "Approved"
		correction.closed_by = frappe.session.user
		correction.closed_at = frappe.utils.now_datetime()
		correction.save(ignore_permissions=True)
	return {**result, "correction_of": original.name, "status": correction.status}


@frappe.whitelist(methods=["POST"])
def list_monthly_closes(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	data = parse_payload(payload or {})
	require_action("view_closings")
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="view_closings")
	rows = frappe.get_all(
		"NXR Monthly Close",
		filters={"project": project} if project else {},
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"close_month",
			"close_date",
			"net_flow_hnl",
			"total_available_hnl",
			"snapshot_hash",
			"correction_of",
		],
		order_by="close_month desc, modified desc",
		limit_page_length=min(max(int(data.get("page_size") or 50), 1), 100),
	)
	return {"rows": rows, "count": len(rows)}
