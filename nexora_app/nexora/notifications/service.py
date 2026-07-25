from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.financial.context import service_write
from nexora.financial.db import correlation, parse_payload
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def create_notification(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	with service_write():
		notification = frappe.get_doc(
			{
				"doctype": "NXR Notification",
				"subject": data["subject"],
				"body": data.get("body", ""),
				"notification_type": data.get("notification_type", "Info"),
				"channel": data.get("channel", "Inbox"),
				"priority": data.get("priority", "Normal"),
				"recipient_user": data["recipient_user"],
				"sender_user": data.get("sender_user"),
				"reference_doctype": data.get("reference_doctype"),
				"reference_name": data.get("reference_name"),
				"idempotency_key": data.get("idempotency_key"),
				"payload_hash": data.get("payload_hash"),
				"correlation_id": correlation(data),
			}
		).insert(ignore_permissions=True)
	return {"notification": notification.name, "document_number": notification.document_number}


@frappe.whitelist(methods=["POST"])
def list_notifications(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	data = parse_payload(payload)
	require_action("preview")
	user = data.get("user") or frappe.session.user
	filters = {"recipient_user": user}
	if data.get("channel"):
		filters["channel"] = data["channel"]
	if data.get("read") is not None:
		filters["read"] = data["read"]
	notifications = frappe.get_all(
		"NXR Notification",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"subject",
			"body",
			"notification_type",
			"channel",
			"priority",
			"read",
			"read_on",
			"creation",
		],
		order_by="creation desc",
		limit=data.get("limit", 50),
	)
	return list(notifications)


@frappe.whitelist(methods=["POST"])
def mark_read(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	notification_name = data["notification"]
	with service_write():
		notification = frappe.get_doc("NXR Notification", notification_name)
		notification.read = 1
		notification.read_on = frappe.utils.now()
		notification.save(ignore_permissions=True)
	return {"notification": notification.name, "read": 1}
