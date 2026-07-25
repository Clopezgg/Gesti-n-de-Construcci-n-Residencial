from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.budget.core import (
	OverspendError,
	assert_transition,
	compute_budget_totals,
	compute_line_balances,
	validate_line_amount,
	validate_no_overspend,
)
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
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def create_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	require_action("approve")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		lines = data.get("lines", [])
		if not lines:
			frappe.throw(_("El presupuesto debe tener al menos una línea."))
		for line in lines:
			validate_line_amount(line.get("approved_hnl", 0))
		totals = compute_budget_totals(lines)
		budget_number, budget_sequence = issue_document_number("NXR Budget", data["idempotency_key"])
		with service_write():
			budget = frappe.get_doc(
				{
					"doctype": "NXR Budget",
					"document_number": budget_number,
					"status": "Draft",
					"project": data["project"],
					"title": data.get("title") or f"Presupuesto {budget_number}",
					"version": data.get("version", 1),
					"effective_date": data.get("effective_date") or frappe.utils.today(),
					"amendment_deadline": data.get("amendment_deadline"),
					"total_approved_hnl": totals["total_approved_hnl"],
					"total_committed_hnl": totals["total_committed_hnl"],
					"total_executed_hnl": totals["total_executed_hnl"],
					"total_available_hnl": totals["total_available_hnl"],
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
					"lines": [
						{
							"economic_category": line.get("economic_category"),
							"cost_center": line.get("cost_center"),
							"description": line.get("description", ""),
							"approved_hnl": line["approved_hnl"],
							"committed_hnl": line.get("committed_hnl", 0),
							"executed_hnl": line.get("executed_hnl", 0),
							"available_hnl": compute_line_balances(
								line["approved_hnl"],
								line.get("committed_hnl", 0),
								line.get("executed_hnl", 0),
							)["available_hnl"],
						}
						for line in lines
					],
				}
			).insert(ignore_permissions=True)
		link_sequence(budget_sequence, budget.name)
		result = {
			"budget": budget.name,
			"document_number": budget_number,
			"totals": totals,
		}
		audit("budget_created", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Budget", budget.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def activate_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Active")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Active"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Active"}
		audit("budget_activated", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def amend_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	require_action("approve")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		budget_name = data["budget"]
		budget = frappe.get_doc("NXR Budget", budget_name)
		frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
		assert_transition(budget.status, "Amended")
		lines = data.get("lines", [])
		if not lines:
			frappe.throw(_("La enmienda debe tener al menos una línea."))
		for line in lines:
			validate_line_amount(line.get("approved_hnl", 0))
		totals = compute_budget_totals(lines)
		new_version = (budget.version or 1) + 1
		new_number, new_sequence = issue_document_number("NXR Budget", data["idempotency_key"])
		with service_write():
			budget.status = "Amended"
			budget.save(ignore_permissions=True)
			new_budget = frappe.get_doc(
				{
					"doctype": "NXR Budget",
					"document_number": new_number,
					"status": "Active",
					"project": budget.project,
					"title": data.get("title") or budget.title,
					"version": new_version,
					"effective_date": data.get("effective_date") or frappe.utils.today(),
					"amendment_deadline": data.get("amendment_deadline"),
					"total_approved_hnl": totals["total_approved_hnl"],
					"total_committed_hnl": totals["total_committed_hnl"],
					"total_executed_hnl": totals["total_executed_hnl"],
					"total_available_hnl": totals["total_available_hnl"],
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
					"lines": [
						{
							"economic_category": line.get("economic_category"),
							"cost_center": line.get("cost_center"),
							"description": line.get("description", ""),
							"approved_hnl": line["approved_hnl"],
							"committed_hnl": line.get("committed_hnl", 0),
							"executed_hnl": line.get("executed_hnl", 0),
							"available_hnl": compute_line_balances(
								line["approved_hnl"],
								line.get("committed_hnl", 0),
								line.get("executed_hnl", 0),
							)["available_hnl"],
						}
						for line in lines
					],
				}
			).insert(ignore_permissions=True)
		link_sequence(new_sequence, new_budget.name)
		result = {
			"previous_budget": budget.name,
			"new_budget": new_budget.name,
			"new_document_number": new_number,
			"version": new_version,
			"totals": totals,
		}
		audit("budget_amended", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Budget", new_budget.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def close_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Closed")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Closed"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Closed"}
		audit("budget_closed", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def cancel_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Cancelled")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Cancelled"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Cancelled"}
		audit("budget_cancelled", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def check_budget_availability(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("preview")
	project = data["project"]
	economic_category = data.get("economic_category")
	amount = data["amount"]
	budget = _find_active_budget(project)
	if budget is None:
		return {"available": False, "reason": "No hay presupuesto activo para este proyecto"}
	for line in budget.get("lines", []):
		if not economic_category or line.get("economic_category") == economic_category:
			try:
				validate_no_overspend(
					line.get("approved_hnl", 0),
					line.get("committed_hnl", 0),
					line.get("executed_hnl", 0),
					amount,
				)
				return {"available": True, "budget": budget.name}
			except OverspendError:
				return {
					"available": False,
					"reason": f"Línea {line.get('economic_category', '?')} sin disponibilidad",
					"budget": budget.name,
				}
	return {"available": False, "reason": "Categoría económica no encontrada en presupuesto"}


def _find_active_budget(project: str) -> dict[str, Any] | None:
	budgets = frappe.get_all(
		"NXR Budget",
		filters={"project": project, "status": "Active"},
		fields=["name", "title", "total_approved_hnl", "total_available_hnl"],
		limit=1,
	)
	if not budgets:
		return None
	b = budgets[0]
	doc = frappe.get_doc("NXR Budget", b.name)
	return {
		"name": doc.name,
		"title": doc.title,
		"total_approved_hnl": doc.total_approved_hnl,
		"total_committed_hnl": doc.total_committed_hnl,
		"total_executed_hnl": doc.total_executed_hnl,
		"total_available_hnl": doc.total_available_hnl,
		"lines": [
			{
				"economic_category": line.economic_category,
				"approved_hnl": line.approved_hnl,
				"committed_hnl": line.committed_hnl,
				"executed_hnl": line.executed_hnl,
				"available_hnl": line.available_hnl,
			}
			for line in doc.lines
		],
	}
