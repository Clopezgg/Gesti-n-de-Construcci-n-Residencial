from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.close.core import assert_transition, reconcile
from nexora.financial.context import service_write
from nexora.financial.db import correlation, parse_payload
from nexora.permissions import require_action


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
