from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.core import money
from nexora.financial.operational_common import CHANNEL_LABELS, DAY_LABELS, MOVEMENT_CATALOG, _masked_account
from nexora.permissions import require_action, require_project_access


def _derived_movement_code(row: Mapping[str, Any], explicit: str | None) -> str:
	if explicit in MOVEMENT_CATALOG:
		return str(explicit)
	operation_code = str(row.get("operation_code") or "")
	operation_type = str(row.get("operation_type") or "")
	if operation_type == "Inflow":
		return "101"
	if operation_code == "DOCUMENT_SUBSTITUTION":
		return "304"
	if operation_code == "REVERSAL_NO_CASH" or row.get("reversal_of"):
		return "303"
	if operation_type in {"Outflow", "Commitment Execution"}:
		return "102"
	return "102"


def _operation_status(row: Mapping[str, Any]) -> str:
	status = str(row.get("status") or "")
	if status == "Draft":
		return "Borrador"
	if status == "Rejected":
		return "Rechazado"
	return "Contabilizado"


def _ledger_tone(code: str, row: Mapping[str, Any]) -> tuple[str, bool]:
	status = str(row.get("status") or "")
	voided = code in {"303", "304", "501"} or status in {"Cancelled", "Compensated Total"}
	if voided:
		return "voided", True
	if code == "101":
		return "income", False
	return "expense", False


@frappe.whitelist(methods=["POST"])
def list_operational_ledger(project: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
	require_action("preview")
	project_name = str(project or "").strip() or None
	require_project_access(project_name, action="preview")
	page_limit = min(max(int(limit or 100), 1), 200)
	operations = frappe.get_all(
		"NXR Operation",
		filters={"project": project_name} if project_name else None,
		fields=[
			"name",
			"document_number",
			"operation_date",
			"creation",
			"operation_code",
			"operation_type",
			"project",
			"amount_hnl",
			"currency",
			"beneficiary",
			"status",
			"reference_name",
			"reversal_of",
		],
		order_by="operation_date desc, creation desc",
		limit_page_length=page_limit,
	)
	operation_names = [str(row["name"]) for row in operations]
	if not operation_names:
		return []
	metadata_rows = frappe.get_all(
		"NXR Operation Metadata",
		filters={"operation": ["in", operation_names]},
		fields=["operation", "movement_code", "financial_account"],
		limit_page_length=len(operation_names),
	)
	metadata = {str(row["operation"]): dict(row) for row in metadata_rows}
	effects = frappe.get_all(
		"NXR Operation Effect",
		filters={"operation": ["in", operation_names], "fund_source": ["is", "set"]},
		fields=["operation", "fund_source", "creation", "name"],
		order_by="creation asc, name asc",
		limit_page_length=page_limit * 20,
	)
	allocations = frappe.get_all(
		"NXR Fund Allocation",
		filters={"operation": ["in", operation_names]},
		fields=["operation", "fund_source", "creation", "name"],
		order_by="creation asc, name asc",
		limit_page_length=page_limit * 20,
	)
	sources_by_operation: dict[str, list[str]] = {}
	for row in [*effects, *allocations]:
		operation = str(row.get("operation") or "")
		source = str(row.get("fund_source") or "")
		if operation and source and source not in sources_by_operation.setdefault(operation, []):
			sources_by_operation[operation].append(source)
	source_names = sorted({source for rows in sources_by_operation.values() for source in rows})
	source_rows = (
		frappe.get_all(
			"NXR Fund Source",
			filters={"name": ["in", source_names]} if source_names else None,
			fields=[
				"name",
				"origin_or_sender",
				"institution",
				"account_reference",
				"currency",
				"channel",
				"original_amount",
			],
			limit_page_length=max(len(source_names), 1),
		)
		if source_names
		else []
	)
	sources = {str(row["name"]): dict(row) for row in source_rows}
	result = []
	for operation in operations:
		name = str(operation["name"])
		meta = metadata.get(name, {})
		code = _derived_movement_code(operation, meta.get("movement_code"))
		date_value = frappe.utils.getdate(operation.get("operation_date"))
		source_list = sources_by_operation.get(name, [])
		primary_source = sources.get(source_list[0], {}) if source_list else {}
		channel = str(primary_source.get("channel") or "")
		movement_label = MOVEMENT_CATALOG[code]["label"]
		if code == "101" and channel:
			movement_label = f"{movement_label} · {CHANNEL_LABELS.get(channel, channel)}"
		counterparty = str(
			primary_source.get("origin_or_sender")
			if code == "101"
			else operation.get("beneficiary") or primary_source.get("origin_or_sender") or "—"
		)
		institution = str(primary_source.get("institution") or "—")
		account = _masked_account(primary_source.get("account_reference"))
		currency = str(primary_source.get("currency") or operation.get("currency") or "HNL")
		if len(source_list) > 1:
			account = _("{0} fuentes").format(len(source_list))
		tone, struck = _ledger_tone(code, operation)
		result.append(
			{
				"name": name,
				"document_number": operation.get("document_number"),
				"movement_code": code,
				"movement_label": movement_label,
				"day": DAY_LABELS[date_value.weekday()],
				"document_date": date_value.isoformat(),
				"registered_at": str(operation.get("creation") or ""),
				"counterparty": counterparty,
				"institution": institution,
				"account": account,
				"currency": currency,
				"amount_hnl": f"{money(operation.get('amount_hnl')):.2f}",
				"status": _operation_status(operation),
				"tone": tone,
				"struck": struck,
				"source_count": len(source_list),
				"reference_name": operation.get("reference_name") or operation.get("reversal_of"),
			}
		)
	return result
