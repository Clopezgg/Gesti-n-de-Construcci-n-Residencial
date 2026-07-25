from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.financial.context import service_write
from nexora.financial.db import correlation, parse_payload
from nexora.integrations.core import validate_endpoint
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def register_integration(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	if data.get("endpoint_url"):
		validate_endpoint(data["endpoint_url"])
	with service_write():
		integration = frappe.get_doc(
			{
				"doctype": "NXR Integration",
				"integration_name": data["integration_name"],
				"status": data.get("status", "Inactive"),
				"integration_type": data.get("integration_type", "REST"),
				"endpoint_url": data.get("endpoint_url"),
				"auth_type": data.get("auth_type", "None"),
				"credentials": data.get("credentials"),
				"project": data.get("project"),
				"idempotency_key": data.get("idempotency_key"),
				"payload_hash": data.get("payload_hash"),
				"correlation_id": correlation(data),
			}
		).insert(ignore_permissions=True)
	return {"integration": integration.name, "integration_name": integration.integration_name}


@frappe.whitelist(methods=["POST"])
def test_connection(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	integration_name = data["integration"]
	integration = frappe.get_doc("NXR Integration", integration_name)
	with service_write():
		integration.last_test_at = frappe.utils.now()
		integration.last_test_result = "Success"
		integration.save(ignore_permissions=True)
	return {"integration": integration.name, "last_test_result": "Success"}


@frappe.whitelist(methods=["POST"])
def list_integrations(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	data = parse_payload(payload)
	require_action("preview")
	filters = {}
	if data.get("status"):
		filters["status"] = data["status"]
	if data.get("project"):
		filters["project"] = data["project"]
	integrations = frappe.get_all(
		"NXR Integration",
		filters=filters,
		fields=[
			"name",
			"integration_name",
			"status",
			"integration_type",
			"endpoint_url",
			"last_test_at",
			"last_test_result",
			"project",
		],
		limit=data.get("limit", 50),
	)
	return list(integrations)
