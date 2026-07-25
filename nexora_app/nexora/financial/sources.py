from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	operation_doc,
	parse_payload,
	rollback,
	savepoint,
	source_states,
	start_idempotency,
)
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def list_source_balances(project: str) -> list[dict[str, str]]:
	require_action("read_balances")
	names = frappe.get_all(
		"NXR Fund Source",
		filters={"project": project, "status": ["in", ["Active", "Exhausted"]]},
		pluck="name",
		order_by="name asc",
	)
	states = source_states(names)
	return [
		{
			"source": name,
			"balance_hnl": f"{states[name].funds:.2f}",
			"reserved_hnl": f"{states[name].reserved:.2f}",
			"available_hnl": f"{states[name].available:.2f}",
		}
		for name in names
	]


@frappe.whitelist(methods=["POST"])
def create_fund_source(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("create_source")
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		source_number, source_sequence = issue_document_number("NXR Fund Source", data["idempotency_key"])
		with service_write():
			source = frappe.get_doc(
				{
					"doctype": "NXR Fund Source",
					"source_code": source_number,
					"source_name": data.get("source_name") or f"Fuente {source_number}",
					"channel": data["channel"],
					"project": data["project"],
					"source_date": data.get("source_date") or frappe.utils.today(),
					"currency": data.get("currency") or "HNL",
					"original_amount": data["original_amount"],
					"exchange_rate": data.get("exchange_rate") or 1,
					"origin_or_sender": data["origin_or_sender"],
					"custodian": data.get("custodian") or frappe.session.user,
					"institution": data.get("institution"),
					"account_reference": data.get("account_reference"),
					"external_reference": data.get("external_reference"),
					"evidence": data.get("evidence"),
					"status": "Active",
				}
			).insert(ignore_permissions=True)
		link_sequence(source_sequence, source.name)
		operation_number, operation_sequence = issue_document_number("NXR Operation", data["idempotency_key"])
		operation_payload = {
			**data,
			"operation_type": "Inflow",
			"amount_hnl": source.amount_hnl,
			"amount": source.amount_hnl,
			"project": source.project,
		}
		preview_data = {
			"preview_hash": canonical_payload_hash(
				{"source": source.name, "amount_hnl": str(source.amount_hnl)}
			),
			"sources": [],
		}
		operation = operation_doc(
			operation_payload, operation_number, fingerprint, preview_data, correlation_id
		)
		link_sequence(operation_sequence, operation.name)
		with service_write():
			frappe.get_doc(
				{
					"doctype": "NXR Operation Effect",
					"operation": operation.name,
					"fund_source": source.name,
					"dimension": "Funds",
					"effect_type": "Received",
					"amount_hnl": source.amount_hnl,
					"project": source.project,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
		result = {
			"fund_source": source.name,
			"source_number": source_number,
			"operation": operation.name,
			"document_number": operation_number,
			"amount_hnl": f"{money(source.amount_hnl):.2f}",
		}
		audit("fund_source_created", "NXR Fund Source", source.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Fund Source", source.name, result)
		return result
	except Exception:
		rollback(point)
		raise
