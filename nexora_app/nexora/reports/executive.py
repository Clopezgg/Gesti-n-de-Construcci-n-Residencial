from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import frappe

from nexora.financial.db import source_states
from nexora.permissions import require_action


def _payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	return dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)


def _project_filters(project: str | None) -> dict[str, Any]:
	return {"project": project} if project else {}


def _get_all(
	doctype: str,
	*,
	fields: list[str],
	filters: dict[str, Any] | None = None,
	order_by: str | None = None,
	limit: int = 10000,
) -> list[dict[str, Any]]:
	try:
		return list(
			frappe.get_all(
				doctype,
				fields=fields,
				filters=filters,
				order_by=order_by,
				limit_page_length=limit,
			)
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		return []


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


@frappe.whitelist(methods=["POST"])
def get_income_register(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _payload(payload)
	require_action("preview")
	project = str(data.get("project") or "").strip() or None
	filters: dict[str, Any] = {"status": ["!=", "Cancelled"]}
	if project:
		filters["project"] = project
	sources = _get_all(
		"NXR Fund Source",
		fields=[
			"name",
			"source_code",
			"source_name",
			"source_date",
			"channel",
			"project",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
			"amount_hnl",
			"status",
		],
		filters=filters,
		order_by="source_date desc, creation desc",
	)
	states = source_states([str(row["name"]) for row in sources]) if sources else {}
	rows: list[dict[str, Any]] = []
	total_received = Decimal(0)
	total_spent = Decimal(0)
	total_reserved = Decimal(0)
	total_available = Decimal(0)
	for source in sources:
		state = states[str(source["name"])]
		received = Decimal(str(source.get("amount_hnl") or 0))
		spent = received - state.funds
		total_received += received
		total_spent += spent
		total_reserved += state.reserved
		total_available += state.available
		rows.append(
			{
				**source,
				"received_hnl": round(float(received), 2),
				"spent_hnl": round(float(spent), 2),
				"reserved_hnl": round(float(state.reserved), 2),
				"available_hnl": round(float(state.available), 2),
				"reconciliation_status": "Conciliado" if source.get("external_reference") else "Pendiente",
			}
		)
	return {
		"rows": rows,
		"totals": {
			"received_hnl": round(float(total_received), 2),
			"spent_hnl": round(float(total_spent), 2),
			"reserved_hnl": round(float(total_reserved), 2),
			"available_hnl": round(float(total_available), 2),
		},
		"count": len(rows),
		"unreconciled_count": sum(1 for row in rows if row["reconciliation_status"] == "Pendiente"),
	}


@frappe.whitelist(methods=["POST"])
def get_contract_register(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _payload(payload)
	require_action("preview")
	project = str(data.get("project") or "").strip() or None
	contracts = _get_all(
		"NXR Contract",
		fields=[
			"name",
			"document_number",
			"contractor",
			"project",
			"status",
			"current_start_date",
			"current_end_date",
			"currency",
			"exchange_rate",
			"current_amount",
			"paid_amount",
			"pending_amount",
		],
		filters=_project_filters(project),
		order_by="current_start_date desc, creation desc",
	)
	labels = _entity_labels({str(row.get("contractor")) for row in contracts if row.get("contractor")})
	rows: list[dict[str, Any]] = []
	for contract in contracts:
		rate = Decimal(str(contract.get("exchange_rate") or 1))
		value_hnl = Decimal(str(contract.get("current_amount") or 0)) * rate
		paid_hnl = Decimal(str(contract.get("paid_amount") or 0)) * rate
		rows.append(
			{
				**contract,
				"contractor_label": labels.get(str(contract.get("contractor") or ""), ""),
				"value_hnl": round(float(value_hnl), 2),
				"paid_hnl": round(float(paid_hnl), 2),
				"balance_hnl": round(float(max(value_hnl - paid_hnl, Decimal(0))), 2),
			}
		)
	return {"rows": rows, "count": len(rows)}


@frappe.whitelist(methods=["POST"])
def get_executive_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = _payload(payload)
	require_action("preview")
	project = str(data.get("project") or "").strip() or None
	income = get_income_register({"project": project})
	contracts = get_contract_register({"project": project})
	operations = _get_all(
		"NXR Operation",
		fields=["operation_type", "economic_category", "amount_hnl", "beneficiary", "status"],
		filters=_project_filters(project),
		limit=5000,
	)
	costs: dict[str, Decimal] = {}
	providers: dict[str, Decimal] = {}
	for operation in operations:
		if operation.get("operation_type") not in {"Outflow", "Commitment Execution"}:
			continue
		amount = Decimal(str(operation.get("amount_hnl") or 0))
		category = str(operation.get("economic_category") or "Sin clasificar")
		beneficiary = str(operation.get("beneficiary") or "Sin beneficiario")
		costs[category] = costs.get(category, Decimal(0)) + amount
		providers[beneficiary] = providers.get(beneficiary, Decimal(0)) + amount
	labels = _entity_labels({name for name in providers if name != "Sin beneficiario"})
	return {
		"generated_at": frappe.utils.now_datetime(),
		"project": project,
		"income": income,
		"contracts": contracts,
		"costs": [
			{"code": code, "amount_hnl": round(float(amount), 2)}
			for code, amount in sorted(costs.items(), key=lambda item: item[1], reverse=True)
		],
		"providers": [
			{"name": labels.get(name, name), "amount_hnl": round(float(amount), 2)}
			for name, amount in sorted(providers.items(), key=lambda item: item[1], reverse=True)[:8]
		],
		"operation_count": len(operations),
	}
