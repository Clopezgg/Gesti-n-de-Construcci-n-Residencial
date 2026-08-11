from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import frappe

from nexora.financial.db import source_states
from nexora.permissions import require_action, require_project_access

MONEY_QUANTUM = Decimal("0.01")

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


def _money(value: object) -> Decimal:
	return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _number(value: object) -> float:
	return float(_money(value))


def _get_all(
	doctype: str,
	*,
	fields: list[str],
	filters: dict[str, Any] | None = None,
	order_by: str | None = None,
	limit: int | None = None,
) -> list[dict[str, Any]]:
	try:
		return list(
			frappe.get_all(
				doctype,
				fields=fields,
				filters=filters,
				order_by=order_by,
				limit_page_length=limit or 10000,
			)
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		return []


def _count(doctype: str, filters: dict[str, Any] | None = None) -> int:
	try:
		return int(frappe.db.count(doctype, filters=filters))
	except (frappe.DoesNotExistError, frappe.ValidationError):
		return 0


def _project_filters(project: str | None) -> dict[str, Any]:
	return {"project": project} if project else {}


def _project_context(project: str | None) -> dict[str, str | None]:
	if not project:
		return {"project": None, "project_label": "Todos los proyectos"}
	label = frappe.db.get_value("Project", project, "project_name") or project
	return {"project": project, "project_label": str(label)}


def _operation_totals(project: str | None) -> dict[str, float]:
	if project:
		rows = frappe.db.sql(
			"""
			SELECT operation_type, COALESCE(SUM(amount_hnl), 0)
			FROM `tabNXR Operation`
			WHERE status='Executed' AND project=%s
			GROUP BY operation_type
			""",
			(project,),
		)
	else:
		rows = frappe.db.sql(
			"""
			SELECT operation_type, COALESCE(SUM(amount_hnl), 0)
			FROM `tabNXR Operation`
			WHERE status='Executed'
			GROUP BY operation_type
			"""
		)
	by_type = {str(operation_type): _money(amount) for operation_type, amount in rows}
	inflows = sum(
		(by_type.get(operation_type, Decimal(0)) for operation_type in ("Inflow", "Real Return")),
		Decimal(0),
	)
	outflows = sum(
		(by_type.get(operation_type, Decimal(0)) for operation_type in ("Outflow", "Commitment Execution")),
		Decimal(0),
	)
	return {
		"inflows_hnl": _number(inflows),
		"outflows_hnl": _number(outflows),
		"net_flow_hnl": _number(inflows - outflows),
	}


def _fund_summary(project: str | None) -> dict[str, Any]:
	sources = _get_all(
		"NXR Fund Source",
		fields=["name", "source_code", "source_name", "channel", "project", "status", "source_date"],
		filters={**_project_filters(project), "status": ["in", ["Active", "Exhausted"]]},
		order_by="source_date desc, creation desc",
	)
	states = source_states([str(source["name"]) for source in sources])
	rows: list[dict[str, Any]] = []
	total_balance = Decimal(0)
	total_reserved = Decimal(0)
	total_available = Decimal(0)
	for source in sources:
		state = states[str(source["name"])]
		total_balance += state.funds
		total_reserved += state.reserved
		total_available += state.available
		rows.append(
			{
				**source,
				"balance_hnl": _number(state.funds),
				"reserved_hnl": _number(state.reserved),
				"available_hnl": _number(state.available),
			}
		)
	return {
		"source_count": len(rows),
		"total_balance_hnl": _number(total_balance),
		"total_reserved_hnl": _number(total_reserved),
		"total_available_hnl": _number(total_available),
		"sources": rows,
		**_operation_totals(project),
	}


def _budget_summary(project: str | None) -> dict[str, Any]:
	active_budgets = _get_all(
		"NXR Budget",
		fields=["name", "document_number", "title", "project", "status"],
		filters={**_project_filters(project), "status": "Active"},
		order_by="effective_date desc, creation desc",
	)
	budget_names = [str(row["name"]) for row in active_budgets]
	lines = (
		_get_all(
			"NXR Budget Line",
			fields=["parent", "economic_category", "description", "approved_hnl"],
			filters={"parent": ["in", budget_names], "parenttype": "NXR Budget"},
		)
		if budget_names
		else []
	)
	approved_by_category: dict[str, Decimal] = {}
	for line in lines:
		category = str(line.get("economic_category") or "Sin clasificar")
		approved_by_category[category] = approved_by_category.get(category, Decimal(0)) + _money(
			line.get("approved_hnl")
		)

	effects = _get_all(
		"NXR Operation Effect",
		fields=["operation", "commitment", "dimension", "effect_type", "amount_hnl", "economic_category"],
		filters={
			**_project_filters(project),
			"dimension": ["in", ["Reserved", "Budget"]],
		},
	)
	operation_names = sorted({str(row["operation"]) for row in effects if row.get("operation")})
	operation_types = {
		str(row["name"]): str(row.get("operation_type") or "")
		for row in (
			_get_all(
				"NXR Operation",
				fields=["name", "operation_type"],
				filters={"name": ["in", operation_names]},
			)
			if operation_names
			else []
		)
	}
	committed_by_category: dict[str, Decimal] = {}
	executed_by_category: dict[str, Decimal] = {}
	for effect in effects:
		category = str(effect.get("economic_category") or "Sin clasificar")
		amount = _money(effect.get("amount_hnl"))
		if effect.get("dimension") == "Reserved":
			committed_by_category[category] = committed_by_category.get(category, Decimal(0)) + amount
			continue
		operation_type = operation_types.get(str(effect.get("operation") or ""), "")
		if operation_type not in {"Commitment Reserve", "Commitment Release"}:
			executed_by_category[category] = executed_by_category.get(category, Decimal(0)) + amount

	categories = sorted(set(approved_by_category) | set(committed_by_category) | set(executed_by_category))
	category_codes = [category for category in categories if category != "Sin clasificar"]
	category_labels = {
		str(row["code"]): str(row.get("category_name") or row["code"])
		for row in (
			_get_all(
				"NXR Economic Category",
				fields=["code", "category_name"],
				filters={"code": ["in", category_codes]},
			)
			if category_codes
			else []
		)
	}
	category_rows: list[dict[str, Any]] = []
	for category in categories:
		approved = approved_by_category.get(category, Decimal(0))
		committed = committed_by_category.get(category, Decimal(0))
		executed = executed_by_category.get(category, Decimal(0))
		category_rows.append(
			{
				"category": category,
				"label": category_labels.get(category, category),
				"approved_hnl": _number(approved),
				"committed_hnl": _number(committed),
				"executed_hnl": _number(executed),
				"available_hnl": _number(approved - committed - executed),
			}
		)

	total_approved = sum(approved_by_category.values(), Decimal(0))
	total_committed = sum(committed_by_category.values(), Decimal(0))
	total_executed = sum(executed_by_category.values(), Decimal(0))
	total_used = total_committed + total_executed
	return {
		"active_budget_count": len(active_budgets),
		"total_approved_hnl": _number(total_approved),
		"total_committed_hnl": _number(total_committed),
		"total_executed_hnl": _number(total_executed),
		"total_available_hnl": _number(total_approved - total_used),
		"utilization_percent": round(float(total_used / total_approved * 100), 2) if total_approved else 0,
		"lines": category_rows,
	}


def _entity_labels(names: set[str]) -> dict[str, str]:
	if not names:
		return {}
	return {
		str(row["name"]): str(row.get("display_name") or row["name"])
		for row in _get_all(
			"NXR Entity",
			fields=["name", "display_name"],
			filters={"name": ["in", sorted(names)]},
		)
	}


def _due_state(value: object) -> str:
	if not value:
		return "undated"
	days = (frappe.utils.getdate(value) - frappe.utils.getdate()).days
	if days < 0:
		return "overdue"
	if days == 0:
		return "today"
	if days <= 30:
		return "upcoming"
	return "later"


def _pending_accounts(project: str | None) -> dict[str, Any]:
	reserved_effects = _get_all(
		"NXR Operation Effect",
		fields=["commitment", "amount_hnl"],
		filters={**_project_filters(project), "dimension": "Reserved"},
	)
	outstanding_by_commitment: dict[str, Decimal] = {}
	for effect in reserved_effects:
		name = str(effect.get("commitment") or "")
		if name:
			outstanding_by_commitment[name] = outstanding_by_commitment.get(name, Decimal(0)) + _money(
				effect.get("amount_hnl")
			)
	commitment_names = sorted(name for name, amount in outstanding_by_commitment.items() if amount > 0)
	commitments = (
		_get_all(
			"NXR Commitment",
			fields=[
				"name",
				"document_number",
				"description",
				"beneficiary",
				"expiry_date",
				"status",
				"project",
			],
			filters={"name": ["in", commitment_names]},
		)
		if commitment_names
		else []
	)

	contracts = _get_all(
		"NXR Contract",
		fields=[
			"name",
			"document_number",
			"contractor",
			"project",
			"currency",
			"exchange_rate",
		],
		filters=_project_filters(project) or None,
	)
	contract_map = {str(row["name"]): row for row in contracts}
	contract_names = sorted(contract_map)
	estimates = (
		_get_all(
			"NXR Contract Estimate",
			fields=[
				"name",
				"document_number",
				"contract",
				"period_end",
				"payable_amount",
				"status",
			],
			filters={"contract": ["in", contract_names], "status": "Approved"},
			order_by="period_end asc, creation asc",
		)
		if contract_names
		else []
	)
	entity_names = {str(row.get("contractor")) for row in contracts if row.get("contractor")} | {
		str(row.get("beneficiary")) for row in commitments if row.get("beneficiary")
	}
	labels = _entity_labels(entity_names)

	items: list[dict[str, Any]] = []
	for commitment in commitments:
		amount = outstanding_by_commitment[str(commitment["name"])]
		due_date = commitment.get("expiry_date")
		items.append(
			{
				"kind": "commitment",
				"doctype": "NXR Commitment",
				"name": commitment["name"],
				"document_number": commitment.get("document_number") or commitment["name"],
				"title": commitment.get("description") or "Compromiso aprobado",
				"beneficiary": labels.get(
					str(commitment.get("beneficiary") or ""),
					str(commitment.get("beneficiary") or ""),
				),
				"amount_hnl": _number(amount),
				"due_date": due_date,
				"due_state": _due_state(due_date),
			}
		)
	for estimate in estimates:
		contract = contract_map[str(estimate["contract"])]
		due_date = estimate.get("period_end")
		exchange_rate = _money(contract.get("exchange_rate") or 1)
		amount_hnl = _money(estimate.get("payable_amount")) * exchange_rate
		items.append(
			{
				"kind": "contract_estimate",
				"doctype": "NXR Contract Estimate",
				"name": estimate["name"],
				"document_number": estimate.get("document_number") or estimate["name"],
				"title": f"Estimación de {contract.get('document_number') or contract['name']}",
				"beneficiary": labels.get(str(contract.get("contractor") or ""), ""),
				"amount_hnl": _number(amount_hnl),
				"currency": contract.get("currency") or "HNL",
				"source_amount": _number(estimate.get("payable_amount")),
				"due_date": due_date,
				"due_state": _due_state(due_date),
			}
		)
	items.sort(key=lambda row: (row["due_date"] or "9999-12-31", row["document_number"]))
	total = sum((_money(row["amount_hnl"]) for row in items), Decimal(0))
	return {
		"count": len(items),
		"total_hnl": _number(total),
		"overdue_count": sum(1 for row in items if row["due_state"] == "overdue"),
		"items": items[:10],
		"upcoming": [row for row in items if row["due_state"] in {"overdue", "today", "upcoming"}][:6],
	}


def _photo_urls(value: object) -> list[str]:
	if not value:
		return []
	if isinstance(value, (list, tuple)):
		return [str(item).strip() for item in value if str(item).strip()]
	text = str(value).strip()
	if not text:
		return []
	try:
		decoded = json.loads(text)
	except (TypeError, ValueError):
		decoded = None
	if isinstance(decoded, list):
		return [str(item).strip() for item in decoded if str(item).strip()]
	return [item.strip() for item in text.replace(",", "\n").splitlines() if item.strip()]


def _progress_summary(project: str | None) -> dict[str, Any]:
	records = _get_all(
		"NXR Progress Record",
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"phase",
			"description",
			"progress_percent",
			"recorded_date",
			"photos",
		],
		filters={**_project_filters(project), "status": ["!=", "Cancelled"]},
		order_by="recorded_date desc, creation desc",
		limit=25,
	)
	approved = next((row for row in records if row.get("status") == "Approved"), None)
	photos: list[str] = []
	for record in records:
		for url in _photo_urls(record.get("photos")):
			if url not in photos:
				photos.append(url)
	open_quality = _count(
		"NXR Quality Check",
		{**_project_filters(project), "status": ["in", ["Open", "Failed"]]},
	)
	open_orders = _count(
		"NXR Purchase Order",
		{**_project_filters(project), "status": ["in", ["Draft", "Confirmed", "Approved", "Sent"]]},
	)
	return {
		"physical_percent": _number(approved.get("progress_percent")) if approved else 0,
		"latest": approved,
		"record_count": len(records),
		"pending_review_count": sum(1 for row in records if row.get("status") == "Submitted"),
		"photos": photos[:8],
		"operational": {
			"active_contracts": _count(
				"NXR Contract",
				{**_project_filters(project), "status": ["in", ["Active", "Suspended", "In Liquidation"]]},
			),
			"pending_requests": _count(
				"NXR Purchase Request",
				{
					**_project_filters(project),
					"status": ["in", ["Draft", "Submitted", "In Review", "Pending Approval"]],
				},
			),
			"open_orders": open_orders,
			"open_quality_issues": open_quality,
		},
	}


def _evidence_summary(project: str | None) -> dict[str, Any]:
	filters: dict[str, Any] = {
		**_project_filters(project),
		"status": ["!=", "Superseded"],
	}
	items = _get_all(
		"NXR Evidence",
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"evidence_kind",
			"channel",
			"file_url",
			"file_name",
			"mime_type",
			"uploaded_at",
			"uploaded_by",
		],
		filters=filters,
		order_by="uploaded_at desc, creation desc",
		limit=8,
	)
	return {
		"count": _count("NXR Evidence", filters),
		"pending_review_count": _count(
			"NXR Evidence",
			{**_project_filters(project), "status": "Uploaded"},
		),
		"items": items,
	}


def _contract_summary(project: str | None) -> dict[str, Any]:
	rows = _get_all(
		"NXR Contract",
		fields=[
			"name",
			"document_number",
			"status",
			"contractor",
			"currency",
			"exchange_rate",
			"current_amount",
			"executed_amount",
			"pending_amount",
			"paid_amount",
			"current_end_date",
		],
		filters={
			**_project_filters(project),
			"status": ["in", ["Active", "Suspended", "In Liquidation"]],
		},
		order_by="current_end_date asc, modified desc",
		limit=6,
	)
	labels = _entity_labels({str(row["contractor"]) for row in rows if row.get("contractor")})
	for row in rows:
		row["contractor_label"] = labels.get(str(row.get("contractor") or ""), "")
		row["pending_amount_hnl"] = _number(
			_money(row.get("pending_amount")) * _money(row.get("exchange_rate") or 1)
		)
	return {"active_count": len(rows), "items": rows}


def _alerts(
	project: str | None,
	funds: Mapping[str, Any],
	budgets: Mapping[str, Any],
	pending: Mapping[str, Any],
	progress: Mapping[str, Any],
	evidence: Mapping[str, Any],
) -> list[dict[str, str]]:
	alerts: list[dict[str, str]] = []
	if pending["overdue_count"]:
		alerts.append(
			{
				"level": "danger",
				"title": "Pagos vencidos",
				"message": f"{pending['overdue_count']} cuenta(s) requieren atención inmediata.",
			}
		)
	if evidence["pending_review_count"]:
		alerts.append(
			{
				"level": "warning",
				"title": "Evidencias por revisar",
				"message": f"{evidence['pending_review_count']} archivo(s) esperan validación.",
			}
		)
	if progress["operational"]["open_quality_issues"]:
		alerts.append(
			{
				"level": "warning",
				"title": "Calidad pendiente",
				"message": f"{progress['operational']['open_quality_issues']} revisión(es) abiertas o fallidas.",
			}
		)
	if budgets["total_approved_hnl"] and budgets["utilization_percent"] >= 90:
		alerts.append(
			{
				"level": "warning",
				"title": "Presupuesto próximo al límite",
				"message": f"El {budgets['utilization_percent']:.1f}% está comprometido o ejecutado.",
			}
		)
	if project and not budgets["active_budget_count"]:
		alerts.append(
			{
				"level": "info",
				"title": "Sin presupuesto activo",
				"message": "El proyecto todavía no tiene un presupuesto vigente.",
			}
		)
	if project and not funds["source_count"]:
		alerts.append(
			{
				"level": "info",
				"title": "Sin fondos registrados",
				"message": "Registre un ingreso para comenzar a operar este proyecto.",
			}
		)
	return alerts[:6]


@frappe.whitelist(methods=["POST"])
def get_dashboard_summary(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(payload) if isinstance(payload, Mapping) else frappe.parse_json(payload)
	project = str(data.get("project") or "").strip() or None
	# NXR-UX-0010 (Bloque 17): esta función usa `_get_all`/`frappe.get_all` en cada
	# ayudante interno, que ignora permisos de fila por diseño de Frappe. Antes solo
	# exigía `require_action("preview")` — un permiso amplio, el mismo para cualquier
	# proyecto — sin verificar si el usuario tiene acceso al proyecto solicitado.
	# "NEXORA Project Viewer" existe específicamente para quedar restringido a
	# proyectos concretos (vía User Permission); sin este chequeo, cualquier usuario
	# con ese rol podía pedir el resumen ejecutivo completo de un proyecto ajeno
	# llamando el endpoint directamente, sin pasar por el selector del frontend.
	# `require_project_access` ya existe y ya se usa para exactamente este caso en
	# `permissions.py` — no es lógica nueva, es la misma regla que faltaba aplicar
	# aquí. Para los roles que ya tienen `view_all_projects` (Administrator, Finance
	# Manager/Operator, Auditor) esto es un no-op: siguen viendo cualquier proyecto
	# igual que antes.
	require_project_access(project, action="view_reports")
	funds = _fund_summary(project)
	budgets = _budget_summary(project)
	pending = _pending_accounts(project)
	progress = _progress_summary(project)
	evidence = _evidence_summary(project)
	contracts = _contract_summary(project)
	recent_operations = _get_all(
		"NXR Operation",
		fields=[
			"name",
			"document_number",
			"operation_type",
			"operation_code",
			"amount_hnl",
			"status",
			"operation_date",
			"creation",
		],
		filters=_project_filters(project) or None,
		order_by="operation_date desc, creation desc",
		limit=10,
	)
	return {
		"context": _project_context(project),
		"generated_at": frappe.utils.now_datetime(),
		"finance": funds,
		"budgets": budgets,
		"pending_accounts": pending,
		"progress": progress,
		"evidence": evidence,
		"contracts": contracts,
		"alerts": _alerts(project, funds, budgets, pending, progress, evidence),
		"recent_operations": recent_operations,
	}
