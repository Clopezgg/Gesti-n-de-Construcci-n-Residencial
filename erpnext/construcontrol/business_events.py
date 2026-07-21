"""Versioned, project-scoped realtime events for canonical ConstruControl views."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe.utils import now_datetime

EVENT_NAME = "construcontrol:business-event:v1"
EVENT_VERSION = 1

_DOMAIN_BY_DOCTYPE = {
	"CC Funding Source": "FI01",
	"CC Expense Control": "FI02",
	"CC Payable Control": "FI02",
	"CC Project Profile": "PR01",
	"CC Construction Phase": "PR01",
	"CC Labor Contract": "CO01",
	"CC Material Ledger": "MM01",
	"CC Procurement Request": "MM02",
	"CC Inventory Movement": "MIGO",
	"CC Progress Update": "QC01",
	"CC Evidence": "QC01",
	"CC Weekly Closing": "CL01",
	"CC Generated Report": "BI01",
	"CC Notification Log": "BI01",
}
_ACTION_BY_METHOD = {
	"on_submit": "submitted",
	"on_cancel": "cancelled",
	"on_trash": "deleted",
}


def _project_name(doc: Any) -> str:
	if str(getattr(doc, "doctype", "")) == "CC Project Profile":
		return str(getattr(doc, "project", None) or getattr(doc, "name", "") or "").strip()
	for fieldname in ("project", "project_id", "project_name"):
		value = str(getattr(doc, fieldname, "") or "").strip()
		if value:
			return value
	return ""


def _occurred_at(value: datetime | None = None) -> str:
	return (value or now_datetime()).isoformat(timespec="seconds")


def build_business_event(
	doc: Any,
	method: str | None = None,
	*,
	occurred_at: datetime | None = None,
) -> dict[str, Any] | None:
	"""Return the exact public event envelope, or ``None`` outside product scope."""
	doctype = str(getattr(doc, "doctype", "") or "").strip()
	domain = _DOMAIN_BY_DOCTYPE.get(doctype)
	project = _project_name(doc)
	name = str(getattr(doc, "name", "") or "").strip()
	if not domain or not project or not name:
		return None
	action = _ACTION_BY_METHOD.get(str(method or ""))
	if not action:
		previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
		action = "updated" if previous else "created"
	return {
		"version": EVENT_VERSION,
		"project": project,
		"domain": domain,
		"document_type": doctype,
		"document_name": name,
		"action": action,
		"occurred_at": _occurred_at(occurred_at),
	}


def publish_business_event(doc: Any, method: str | None = None) -> None:
	"""Queue a secret-free event for delivery only after the database commits."""
	payload = build_business_event(doc, method)
	if payload is None:
		return
	frappe.publish_realtime(EVENT_NAME, message=payload, after_commit=True)


__all__ = ["EVENT_NAME", "EVENT_VERSION", "build_business_event", "publish_business_event"]
