"""Persistencia de estado conversacional (Bloque 18, NXR-CNV-0001).

Mismo patrón exacto que ``financial/db.py::audit`` (inserción con
``service_write()`` + ``ignore_permissions=True``; ningún rol tiene
``create``/``write`` directo sobre estos DocTypes). No se crea un segundo
sistema de auditoría: ``NXR Conversation Message`` es la bitácora propia de
la conversación (quién dijo qué), y cada ejecución real sigue auditándose
además con ``financial.db.audit`` en ``dispatch.py``, igual que cualquier
otro origen.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import frappe

from nexora.conversation.core import assert_pending_intent_transition
from nexora.financial.context import service_write


def get_or_create_conversation(user: str) -> str:
	existing = frappe.get_all(
		"NXR Conversation",
		filters={"user": user, "status": "Active"},
		order_by="modified desc",
		limit=1,
		pluck="name",
	)
	if existing:
		return existing[0]
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": "NXR Conversation",
				"user": user,
				"channel": "App",
				"status": "Active",
				"last_activity_at": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
	return doc.name


def touch_conversation(conversation: str) -> None:
	frappe.db.set_value(
		"NXR Conversation", conversation, "last_activity_at", frappe.utils.now_datetime(), update_modified=False
	)


def append_message(
	conversation: str,
	direction: str,
	content: str,
	*,
	correlation_id: str,
	intent_key: str | None = None,
	intent_json: Mapping[str, Any] = None,
) -> str:
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": "NXR Conversation Message",
				"conversation": conversation,
				"direction": direction,
				"content": content,
				"intent_key": intent_key or "",
				"intent_json": json.dumps(intent_json, ensure_ascii=False, sort_keys=True, default=str)
				if intent_json is not None
				else "",
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)
	touch_conversation(conversation)
	return doc.name


def get_open_pending_intent(conversation: str) -> dict[str, Any] | None:
	rows = frappe.get_all(
		"NXR Conversation Pending Intent",
		filters={"conversation": conversation, "status": ["in", ("Collecting", "AwaitingConfirmation")]},
		order_by="modified desc",
		limit=1,
	)
	if not rows:
		return None
	return frappe.get_doc("NXR Conversation Pending Intent", rows[0]["name"]).as_dict()


def create_pending_intent(
	conversation: str,
	intent_key: str,
	payload: Mapping[str, Any],
	*,
	correlation_id: str,
	status: str = "Collecting",
	missing: list[str] | None = None,
) -> dict[str, Any]:
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": "NXR Conversation Pending Intent",
				"conversation": conversation,
				"intent_key": intent_key,
				"status": status,
				"payload_json": json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str),
				"missing_slots_json": json.dumps(list(missing or []), ensure_ascii=False),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)
	return doc.as_dict()


def update_pending_intent(
	name: str,
	*,
	payload: Mapping[str, Any] | None = None,
	missing: list[str] | None = None,
	preview: Mapping[str, Any] | None = None,
	preview_hash: str | None = None,
	idempotency_key: str | None = None,
	result: Mapping[str, Any] | None = None,
	status: str | None = None,
) -> dict[str, Any]:
	doc = frappe.get_doc("NXR Conversation Pending Intent", name)
	if status is not None and status != doc.status:
		assert_pending_intent_transition(str(doc.status), status)
		doc.status = status
	if payload is not None:
		doc.payload_json = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str)
	if missing is not None:
		doc.missing_slots_json = json.dumps(list(missing), ensure_ascii=False)
	if preview is not None:
		doc.preview_json = json.dumps(dict(preview), ensure_ascii=False, sort_keys=True, default=str)
	if preview_hash is not None:
		doc.preview_hash = preview_hash
	if idempotency_key is not None:
		doc.idempotency_key = idempotency_key
	if result is not None:
		doc.result_json = json.dumps(dict(result), ensure_ascii=False, sort_keys=True, default=str)
	with service_write():
		doc.save(ignore_permissions=True)
	return doc.as_dict()
