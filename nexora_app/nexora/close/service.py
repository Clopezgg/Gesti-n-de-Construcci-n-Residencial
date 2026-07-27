from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.close.as_of import budget_totals_as_of
from nexora.close.core import assert_transition, reconcile
from nexora.dashboard.analytics_core import stable_payload_hash
from nexora.dashboard.executive import get_executive_snapshot
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

WEEKLY_ENGINE_VERSION = "nexora-analytics-v2"


@frappe.whitelist(methods=["POST"])
def create_monthly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	with service_write():
		close = frappe.get_doc(
			{
				"doctype": "NXR Monthly Close",
				"status": "Draft",
				"project": data["project"],
				"close_month": data["close_month"],
				"close_date": data["close_date"],
				"total_inflows_hnl": data.get("total_inflows_hnl", 0),
				"total_outflows_hnl": data.get("total_outflows_hnl", 0),
				"comments": data.get("comments", ""),
				"idempotency_key": data.get("idempotency_key"),
				"payload_hash": data.get("payload_hash"),
				"correlation_id": correlation(data),
			}
		).insert(ignore_permissions=True)
	return {"monthly_close": close.name, "document_number": close.document_number}


@frappe.whitelist(methods=["POST"])
def transition_monthly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	close_name = data["monthly_close"]
	target_status = data["status"]
	close = frappe.get_doc("NXR Monthly Close", close_name)
	assert_transition(close.status, target_status)
	with service_write():
		close.status = target_status
		if target_status in ("Approved", "Cancelled"):
			close.closed_by = frappe.session.user
		close.save(ignore_permissions=True)
	return {"monthly_close": close.name, "status": close.status}


@frappe.whitelist(methods=["POST"])
def reconcile_month(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	before = data["before"]
	after = data["after"]
	result = reconcile(before, after)
	return {"reconciled": True, "data": result}


def _weekly_payload(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	week_start = frappe.utils.getdate(data.get("week_start")) if data.get("week_start") else None
	week_end = frappe.utils.getdate(data.get("week_end")) if data.get("week_end") else None
	if not week_start or not week_end:
		frappe.throw(_("Seleccione el inicio y el final de la semana."))
	if week_end < week_start:
		frappe.throw(_("La semana termina antes de su fecha inicial."))
	project = str(data.get("project") or "").strip() or None
	return {
		"project": project,
		"week_start": week_start.isoformat(),
		"week_end": week_end.isoformat(),
		"comments": str(data.get("comments") or "").strip(),
		"idempotency_key": str(data.get("idempotency_key") or "").strip(),
		"correlation_id": str(data.get("correlation_id") or "").strip() or None,
	}


def _period_key(data: Mapping[str, Any]) -> str:
	return stable_payload_hash(
		{
			"project": data.get("project") or "ALL",
			"week_start": data["week_start"],
			"week_end": data["week_end"],
		}
	)


def _physical_progress(project: str | None, week_end: str) -> float:
	filters: dict[str, Any] = {"status": "Approved", "recorded_date": ["<=", week_end]}
	if project:
		filters["project"] = project
	value = frappe.db.get_value(
		"NXR Progress Record",
		filters,
		"progress_percent",
		order_by="recorded_date desc, creation desc",
	)
	return float(value or 0)


def _compact_snapshot(data: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
	analytics = snapshot.get("analytics", {})
	executive = snapshot.get("executive", {})
	source_totals = analytics.get("source_totals", {})
	budget_totals = budget_totals_as_of(data.get("project"), data["week_end"])
	pagination = {
		"income_count": int(analytics.get("source_pagination", {}).get("total") or 0),
		"expense_count": int(analytics.get("expense_pagination", {}).get("total") or 0),
		"contract_count": int(analytics.get("contract_totals", {}).get("contract_count") or 0),
	}
	physical_progress = _physical_progress(data.get("project"), data["week_end"])
	closing_reserved = source_totals.get("closing_reserved_hnl", 0)
	return {
		"engine_version": WEEKLY_ENGINE_VERSION,
		"generated_at": str(snapshot.get("generated_at") or frappe.utils.now_datetime()),
		"period": {"week_start": data["week_start"], "week_end": data["week_end"]},
		"project": data.get("project"),
		"totals": {
			"received_hnl": executive.get("received_hnl", 0),
			"spent_hnl": executive.get("spent_hnl", 0),
			"pending_hnl": closing_reserved,
			"available_hnl": executive.get("cash_available_hnl", 0),
			"projected_available_hnl": executive.get("projected_available_hnl", 0),
			"committed_hnl": closing_reserved,
			"budget_available_hnl": budget_totals.get("total_available_hnl", 0),
			"opening_funds_hnl": source_totals.get("opening_funds_hnl", 0),
			"closing_funds_hnl": source_totals.get("closing_funds_hnl", 0),
			"opening_reserved_hnl": source_totals.get("opening_reserved_hnl", 0),
			"closing_reserved_hnl": closing_reserved,
		},
		"physical_progress": physical_progress,
		"unreconciled_incomes": int(analytics.get("unreconciled_count") or 0),
		"counts": pagination,
		"contract_totals": analytics.get("contract_totals", {}),
		"budget_totals": budget_totals,
		"snapshot_basis": {
			"funds": "Efectos del Libro Central con fecha de operación hasta el cierre.",
			"pending": "Reserva financiera pendiente al cierre; no usa el estado mutable actual de cuentas por pagar.",
			"budget": budget_totals.get("basis"),
			"progress": "Último avance aprobado con fecha igual o anterior al cierre.",
			"contracts": "Estado contractual vigente al momento de generar el cierre; la versión histórica contractual requiere su propio historial de adendas.",
			"reconciliation": "Estado documental vigente al momento de generar el cierre.",
		},
	}


@frappe.whitelist(methods=["POST"])
def calculate_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_closings")
	data = _weekly_payload(payload)
	require_project_access(data["project"], action="view_closings")
	snapshot = get_executive_snapshot(
		{
			"project": data["project"],
			"from_date": data["week_start"],
			"to_date": data["week_end"],
		}
	)
	compact = _compact_snapshot(data, snapshot)
	return {**compact, "snapshot_hash": stable_payload_hash(compact)}


def _save_close(
	data: Mapping[str, Any],
	*,
	status: str,
	correction_of: str | None = None,
	correction_reason: str | None = None,
) -> dict[str, Any]:
	key = str(data.get("idempotency_key") or "").strip()
	if not key:
		frappe.throw(_("El cierre semanal requiere una clave de idempotencia."))
	normalized = {
		"project": data.get("project"),
		"week_start": data["week_start"],
		"week_end": data["week_end"],
		"comments": data.get("comments"),
		"status": status,
		"correction_of": correction_of,
		"correction_reason": correction_reason,
	}
	fingerprint = canonical_payload_hash(normalized)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		base_period_key = _period_key(data)
		if status == "Closed" and frappe.db.exists("NXR Weekly Close", {"period_key": base_period_key}):
			frappe.throw(_("Ya existe un cierre para este período y proyecto."))
		number, sequence = issue_document_number("NXR Weekly Close", key)
		calculated = calculate_weekly_close(data)
		snapshot_hash = calculated.pop("snapshot_hash")
		period_key = base_period_key if status == "Closed" else f"{base_period_key}:correction:{number}"
		totals = calculated["totals"]
		counts = calculated["counts"]
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Weekly Close",
					"document_number": number,
					"status": status,
					"period_key": period_key,
					"week_start": data["week_start"],
					"week_end": data["week_end"],
					"project": data.get("project"),
					"received_hnl": totals["received_hnl"],
					"spent_hnl": totals["spent_hnl"],
					"pending_hnl": totals["pending_hnl"],
					"available_hnl": totals["available_hnl"],
					"committed_hnl": totals["committed_hnl"],
					"budget_available_hnl": totals["budget_available_hnl"],
					"physical_progress": calculated["physical_progress"],
					"unreconciled_incomes": calculated["unreconciled_incomes"],
					"income_count": counts["income_count"],
					"expense_count": counts["expense_count"],
					"contract_count": counts["contract_count"],
					"snapshot_json": json.dumps(calculated, ensure_ascii=False, sort_keys=True, default=str),
					"snapshot_hash": snapshot_hash,
					"engine_version": WEEKLY_ENGINE_VERSION,
					"correction_of": correction_of,
					"correction_reason": correction_reason,
					"comments": data.get("comments"),
					"closed_by": frappe.session.user,
					"closed_at": frappe.utils.now_datetime(),
					"idempotency_key": key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {
			"weekly_close": doc.name,
			"document_number": number,
			"status": status,
			"snapshot_hash": snapshot_hash,
			"engine_version": WEEKLY_ENGINE_VERSION,
		}
		audit("weekly_close_created", "NXR Weekly Close", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Weekly Close", doc.name, result)
		return result
	except frappe.DuplicateEntryError:
		rollback(point)
		frappe.throw(_("Otro cierre fue registrado simultáneamente para este período y proyecto."))
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def save_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("save_closing")
	data = _weekly_payload(payload)
	require_project_access(data["project"], action="save_closing")
	return _save_close(data, status="Closed")


@frappe.whitelist(methods=["POST"])
def correct_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("save_closing")
	data = _weekly_payload(payload)
	raw = parse_payload(payload)
	original_name = str(raw.get("weekly_close") or "").strip()
	reason = str(raw.get("correction_reason") or "").strip()
	if not original_name:
		frappe.throw(_("Seleccione el cierre que necesita corregir."))
	if len(reason) < 10:
		frappe.throw(_("Explique la corrección con al menos 10 caracteres."))
	original = frappe.get_doc("NXR Weekly Close", original_name)
	if (
		frappe.utils.getdate(original.week_start).isoformat() != data["week_start"]
		or frappe.utils.getdate(original.week_end).isoformat() != data["week_end"]
	):
		frappe.throw(_("La corrección debe conservar el período del cierre original."))
	if (original.project or None) != data["project"]:
		frappe.throw(_("La corrección debe conservar el proyecto del cierre original."))
	require_project_access(data["project"], action="save_closing")
	return _save_close(data, status="Correction", correction_of=original.name, correction_reason=reason)


@frappe.whitelist(methods=["POST"])
def list_weekly_closes(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	require_action("view_closings")
	data = parse_payload(payload or {})
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="view_closings")
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or 25), 1), 100)
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	rows = frappe.get_all(
		"NXR Weekly Close",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"status",
			"week_start",
			"week_end",
			"project",
			"received_hnl",
			"spent_hnl",
			"available_hnl",
			"committed_hnl",
			"physical_progress",
			"unreconciled_incomes",
			"snapshot_hash",
			"engine_version",
			"correction_of",
			"closed_by",
			"closed_at",
		],
		order_by="week_end desc, creation desc",
		limit_start=(page - 1) * page_size,
		limit_page_length=page_size,
	)
	return {
		"rows": rows,
		"pagination": {
			"page": page,
			"page_size": page_size,
			"total": frappe.db.count("NXR Weekly Close", filters=filters),
		},
	}
