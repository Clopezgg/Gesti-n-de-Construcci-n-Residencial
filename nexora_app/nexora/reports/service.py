from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import frappe

from nexora.permissions import require_action
from nexora.reports.core import format_statement_rows, reconcile_amounts


@frappe.whitelist(methods=["POST"])
def get_source_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	source = data["source"]
	project = data.get("project")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	try:
		operations = frappe.get_all(
			"NXR Operation",
			fields=[
				"name",
				"document_number",
				"operation_type",
				"amount_hnl",
				"status",
				"creation",
				"description",
			],
			filters={"source": source, **filters} if project else filters,
			order_by="creation asc",
			limit_page_length=1000,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operations = []
	totals = reconcile_amounts(operations)
	rows = format_statement_rows(operations)
	return {"source": source, "totals": totals, "rows": rows, "row_count": len(rows)}


@frappe.whitelist(methods=["POST"])
def get_entity_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	entity = data["entity"]
	project = data.get("project")
	filters: dict[str, Any] = {"beneficiary": entity}
	if project:
		filters["project"] = project
	try:
		operations = frappe.get_all(
			"NXR Operation",
			fields=[
				"name",
				"document_number",
				"operation_type",
				"amount_hnl",
				"status",
				"creation",
				"description",
			],
			filters=filters,
			order_by="creation asc",
			limit_page_length=1000,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operations = []
	totals = reconcile_amounts(operations)
	rows = format_statement_rows(operations)
	return {"entity": entity, "totals": totals, "rows": rows, "row_count": len(rows)}


@frappe.whitelist(methods=["POST"])
def get_contract_statement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	contract = data["contract"]
	try:
		operations = frappe.get_all(
			"NXR Operation",
			fields=[
				"name",
				"document_number",
				"operation_type",
				"amount_hnl",
				"status",
				"creation",
				"description",
			],
			filters={"contract": contract},
			order_by="creation asc",
			limit_page_length=1000,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operations = []
	totals = reconcile_amounts(operations)
	rows = format_statement_rows(operations)
	return {"contract": contract, "totals": totals, "rows": rows, "row_count": len(rows)}


@frappe.whitelist(methods=["POST"])
def get_financial_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	project = data.get("project")
	filters = {"project": project} if project else {}
	try:
		budgets = frappe.get_all(
			"NXR Budget",
			fields=[
				"name",
				"title",
				"total_approved_hnl",
				"total_committed_hnl",
				"total_executed_hnl",
				"total_available_hnl",
				"status",
			],
			filters={"status": "Active", **filters},
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		budgets = []
	try:
		commitments = frappe.get_all(
			"NXR Commitment", fields=["name", "document_number", "amount_hnl", "status"], filters={**filters}
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		commitments = []
	try:
		operation_count = frappe.db.count("NXR Operation", filters=filters)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operation_count = 0
	total_approved = sum(float(b.get("total_approved_hnl") or 0) for b in budgets)
	total_committed = sum(float(b.get("total_committed_hnl") or 0) for b in budgets)
	total_executed = sum(float(b.get("total_executed_hnl") or 0) for b in budgets)
	total_available = sum(float(b.get("total_available_hnl") or 0) for b in budgets)
	total_commitment_amount = sum(float(c.get("amount_hnl") or 0) for c in commitments)
	return {
		"budgets": {
			"active_count": len(budgets),
			"total_approved_hnl": round(total_approved, 2),
			"total_committed_hnl": round(total_committed, 2),
			"total_executed_hnl": round(total_executed, 2),
			"total_available_hnl": round(total_available, 2),
		},
		"commitments": {"count": len(commitments), "total_amount_hnl": round(total_commitment_amount, 2)},
		"operations": {"count": operation_count},
	}


@frappe.whitelist(methods=["POST"])
def get_cost_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	project = data.get("project")
	filters: dict[str, Any] = {"project": project} if project else {}
	try:
		categories: dict[str, Decimal] = {}
		ops = frappe.get_all(
			"NXR Operation",
			fields=["economic_category", "amount_hnl", "operation_type"],
			filters={**filters, "operation_type": ["in", ("Outflow", "Commitment Execution")]},
			limit_page_length=5000,
		)
		for op in ops:
			cat = op.get("economic_category") or "Sin clasificar"
			categories.setdefault(cat, Decimal(0))
			categories[cat] += Decimal(str(op.get("amount_hnl", 0)))
	except (frappe.DoesNotExistError, frappe.ValidationError):
		categories = {}
	return {
		"categories": {k: round(float(v), 2) for k, v in sorted(categories.items())},
		"total": round(sum(float(v) for v in categories.values()), 2),
	}


@frappe.whitelist(methods=["POST"])
def reconcile_totals(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	project = data.get("project")
	entity = data.get("entity")
	filters: dict[str, Any] = {}
	if project:
		filters["project"] = project
	if entity:
		filters["beneficiary"] = entity
	try:
		operations = frappe.get_all(
			"NXR Operation",
			fields=["operation_type", "amount_hnl"],
			filters=filters,
			limit_page_length=10000,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		operations = []
	inflow = sum(
		float(op.get("amount_hnl", 0))
		for op in operations
		if op.get("operation_type") in ("Inflow", "Real Return")
	)
	outflow = sum(
		float(op.get("amount_hnl", 0))
		for op in operations
		if op.get("operation_type") in ("Outflow", "Commitment Execution")
	)
	net = inflow - outflow
	return {
		"inflows": round(inflow, 2),
		"outflows": round(outflow, 2),
		"net": round(net, 2),
		"operation_count": len(operations),
	}
