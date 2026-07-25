from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import frappe

from nexora.permissions import require_action

SEARCHABLE_DOCTYPES: Sequence[dict[str, str]] = [
	{
		"doctype": "NXR Entity",
		"label": "Entidad",
		"title_field": "display_name",
		"search_fields": ("display_name", "normalized_name", "document_number"),
	},
	{
		"doctype": "NXR Contract",
		"label": "Contrato",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Contractor Profile",
		"label": "Perfil de contratista",
		"title_field": "name",
		"search_fields": ("name",),
	},
	{
		"doctype": "NXR Supplier Profile",
		"label": "Perfil de proveedor",
		"title_field": "name",
		"search_fields": ("name",),
	},
	{
		"doctype": "NXR Purchase Request",
		"label": "Solicitud de compra",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Purchase Order",
		"label": "Orden de compra",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Goods Receipt",
		"label": "Recepci\u00f3n",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Budget",
		"label": "Presupuesto",
		"title_field": "title",
		"search_fields": ("document_number", "title"),
	},
	{
		"doctype": "NXR Operation",
		"label": "Operaci\u00f3n",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Commitment",
		"label": "Compromiso",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Evidence",
		"label": "Evidencia",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
	{
		"doctype": "NXR Fund Source",
		"label": "Fuente de fondos",
		"title_field": "source_name",
		"search_fields": ("source_code", "source_name"),
	},
	{
		"doctype": "NXR Stock Transaction",
		"label": "Movimiento de inventario",
		"title_field": "name",
		"search_fields": ("document_number", "name"),
	},
]


@frappe.whitelist(methods=["POST"])
def universal_search(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	query = (data.get("query") or "").strip()
	doctypes_filter = data.get("doctypes")
	limit = min(int(data.get("limit", 20)), 100)
	if not query:
		return []
	results: list[dict[str, Any]] = []
	doctypes = SEARCHABLE_DOCTYPES
	if doctypes_filter and isinstance(doctypes_filter, str):
		doctypes = [d for d in doctypes if d["label"] == doctypes_filter]
	if doctypes_filter and isinstance(doctypes_filter, list):
		doctypes = [d for d in doctypes if d["doctype"] in doctypes_filter]
	for entry in doctypes:
		dt = entry["doctype"]
		remaining = limit - len(results)
		if remaining <= 0:
			break
		filters = []
		for sf in entry["search_fields"]:
			filters.append([sf, "like", f"%{query}%"])
		or_filters = list(filters)
		try:
			matches = frappe.get_all(
				dt,
				fields=["name", entry["title_field"], "status", "document_number"],
				filters={"status": ["!=", "Cancelled"]} if dt != "NXR Evidence" else {},
				or_filters=or_filters if len(or_filters) > 1 else (or_filters[0] if or_filters else None),
				limit_page_length=remaining,
			)
		except (frappe.DoesNotExistError, frappe.ValidationError):
			continue
		for row in matches:
			results.append(
				{
					"doctype": dt,
					"label": entry["label"],
					"name": row["name"],
					"title": row.get(entry["title_field"]) or row.get("document_number") or row["name"],
					"status": row.get("status", ""),
					"document_number": row.get("document_number", ""),
				}
			)
	return results


@frappe.whitelist(methods=["POST"])
def get_dashboard_summary(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	require_action("preview")
	project = data.get("project")
	base_filters = {"project": project} if project else {}
	try:
		budget_docs = frappe.get_all(
			"NXR Budget",
			fields=[
				"name",
				"total_approved_hnl",
				"total_committed_hnl",
				"total_executed_hnl",
				"total_available_hnl",
				"status",
			],
			filters=base_filters,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		budget_docs = []
	total_approved = sum(
		float(b.get("total_approved_hnl") or 0) for b in budget_docs if b.get("status") == "Active"
	)
	total_committed = sum(
		float(b.get("total_committed_hnl") or 0) for b in budget_docs if b.get("status") == "Active"
	)
	total_executed = sum(
		float(b.get("total_executed_hnl") or 0) for b in budget_docs if b.get("status") == "Active"
	)
	total_available = sum(
		float(b.get("total_available_hnl") or 0) for b in budget_docs if b.get("status") == "Active"
	)
	try:
		active_contracts = frappe.db.count("NXR Contract", filters={**base_filters, "status": "Active"})
	except (frappe.DoesNotExistError, frappe.ValidationError):
		active_contracts = 0
	try:
		pending_purchase_requests = frappe.db.count(
			"NXR Purchase Request",
			filters={**base_filters, "status": ["in", ("Draft", "Submitted", "In Review")]},
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pending_purchase_requests = 0
	try:
		active_suppliers = frappe.db.count("NXR Supplier Profile", filters={"status": "Active"})
	except (frappe.DoesNotExistError, frappe.ValidationError):
		active_suppliers = 0
	try:
		total_entities = frappe.db.count("NXR Entity", filters={"status": "Active"})
	except (frappe.DoesNotExistError, frappe.ValidationError):
		total_entities = 0
	try:
		recent_operations = frappe.get_all(
			"NXR Operation",
			fields=["name", "document_number", "operation_type", "amount_hnl", "status", "creation"],
			filters=base_filters,
			order_by="creation desc",
			limit=10,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		recent_operations = []
	return {
		"budgets": {
			"active_budget_count": len([b for b in budget_docs if b.get("status") == "Active"]),
			"total_approved_hnl": round(total_approved, 2),
			"total_committed_hnl": round(total_committed, 2),
			"total_executed_hnl": round(total_executed, 2),
			"total_available_hnl": round(total_available, 2),
		},
		"contracts": {"active_count": active_contracts},
		"purchase_requests": {"pending_count": pending_purchase_requests},
		"suppliers": {"active_count": active_suppliers},
		"entities": {"active_count": total_entities},
		"recent_operations": recent_operations,
	}
