from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	operation_doc,
	parse_payload,
	persist_effects,
	preview,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.permissions import require_action


def execute(data: dict[str, Any], *, action: str, commitment: str | None = None) -> dict[str, Any]:
	require_action(action)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		preview_data = preview(data, lock=True)
		if data.get("preview_hash") and data["preview_hash"] != preview_data["preview_hash"]:
			frappe.throw(_("La vista previa cambió; revísela nuevamente antes de ejecutar."))
		number, sequence = issue_document_number("NXR Operation", data["idempotency_key"])
		operation = operation_doc(data, number, fingerprint, preview_data, correlation_id, commitment)
		persist_effects(operation, preview_data, correlation_id, commitment)
		link_sequence(sequence, operation.name)
		result = {
			"operation": operation.name,
			"document_number": number,
			"preview_hash": preview_data["preview_hash"],
			"sources": preview_data["sources"],
		}
		audit(
			"financial_operation_executed",
			"NXR Operation",
			operation.name,
			fingerprint,
			correlation_id,
			result,
		)
		complete_idempotency(idem, "NXR Operation", operation.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def preview_financial_operation(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("preview")
	return preview(parse_payload(payload), lock=False)


@frappe.whitelist(methods=["POST"])
def execute_financial_operation(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	operation_type = data.get("operation_type")
	if operation_type not in {"Outflow", "Real Return", "Reclassification"}:
		frappe.throw(_("Use el servicio específico para compromisos."))
	action = (
		"return"
		if operation_type == "Real Return"
		else "reclassify"
		if operation_type == "Reclassification"
		else "execute"
	)
	return execute(data, action=action)
