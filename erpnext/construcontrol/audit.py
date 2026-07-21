from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe.utils import now_datetime, today

_ROLE_LABELS = (
	("System Manager", "ADMIN"),
	("ConstruControl Manager", "MANAGER"),
	("ConstruControl Operator", "OPERATOR"),
	("ConstruControl Auditor", "AUDITOR"),
	("ConstruControl Viewer", "VIEWER"),
)
_SENSITIVE_KEYS = {
	"password",
	"password_hash",
	"passwordhash",
	"pin_hash",
	"pinhash",
	"access_token",
	"refresh_token",
	"api_key",
	"api_secret",
	"credential_secret",
	"secret",
	"service_role",
	"service_role_key",
	"configuration_json",
	"payload_json",
	"previous_state",
	"next_state",
}
_SYSTEM_KEYS = {
	"doctype",
	"__islocal",
	"__unsaved",
	"_comments",
	"_assign",
	"_liked_by",
}
_AUDIT_DOCTYPES = {"CC Audit Log", "CC Immutable Audit Event"}
_MODULE_BY_DOCTYPE = {
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
	"CC User Access": "US01",
}


def _(value: str) -> str:
	translator = getattr(frappe, "_", None)
	return str(translator(value) if translator else value)


_REASON_FIELDS = (
	"rejection_reason",
	"cancellation_reason",
	"reversal_reason",
	"reason",
	"justification",
	"notes",
)


def _role_label() -> str:
	roles = set(frappe.get_roles())
	for role, label in _ROLE_LABELS:
		if role in roles:
			return label
	return "USER"


def _display_name(user: str) -> str:
	if user == "Guest":
		return "Invitado"
	return str(frappe.db.get_value("User", user, "full_name") or user)


def _sensitive_key(key: Any) -> bool:
	normalized = str(key).replace("-", "_").casefold()
	return (
		normalized in _SENSITIVE_KEYS
		or normalized.endswith(("_password", "_secret", "_token", "_api_key", "_private_key"))
		or normalized.startswith(("password_", "secret_", "token_"))
	)


def _clean(value: Any) -> Any:
	if isinstance(value, list):
		return [_clean(item) for item in value]
	if not isinstance(value, Mapping):
		return value
	result: dict[str, Any] = {}
	for key, item in value.items():
		if _sensitive_key(key) or key in _SYSTEM_KEYS:
			continue
		result[str(key)] = _clean(item)
	return result


def _snapshot(doc: Any) -> dict[str, Any]:
	if not doc:
		return {}
	try:
		raw = dict(doc.as_dict())
		meta = getattr(doc, "meta", None)
		for field in getattr(meta, "fields", []) or []:
			if getattr(field, "fieldtype", "") == "Password" or _sensitive_key(
				getattr(field, "fieldname", "")
			):
				raw.pop(getattr(field, "fieldname", ""), None)
		return _clean(raw)
	except Exception:
		return {
			"doctype": getattr(doc, "doctype", ""),
			"name": getattr(doc, "name", ""),
		}


def _previous_snapshot(doc: Any) -> dict[str, Any]:
	previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	return _snapshot(previous) if previous else {}


def _module_for(doctype: str) -> str:
	return _MODULE_BY_DOCTYPE.get(doctype, "AU01")


def _changed_to(previous: dict[str, Any], following: dict[str, Any], values: set[str]) -> bool:
	for fieldname in (
		"professional_approval_status",
		"approval_status",
		"payment_status",
		"financial_status",
		"status",
	):
		before = str(previous.get(fieldname) or "").strip().casefold()
		after = str(following.get(fieldname) or "").strip().casefold()
		if after in values and after != before:
			return True
	return False


def _derive_action(method: str | None, previous: dict[str, Any], following: dict[str, Any]) -> str:
	if method == "after_insert":
		return "CREATE"
	if method == "on_trash":
		return "DELETE"
	if method == "on_cancel" or _changed_to(previous, following, {"cancelled", "canceled", "annulled"}):
		return "CANCEL"
	if _changed_to(previous, following, {"reimbursed", "reverted", "reversed"}):
		return "REVERSE"
	if _changed_to(previous, following, {"rejected"}):
		return "REJECT"
	if _changed_to(previous, following, {"paid", "partially_paid", "partial"}):
		return "PAY"
	if method == "on_submit" or _changed_to(previous, following, {"approved", "verified", "closed"}):
		return "APPROVE"
	return "UPDATE"


def _reason(previous: dict[str, Any], following: dict[str, Any]) -> str | None:
	for fieldname in _REASON_FIELDS:
		value = following.get(fieldname)
		if value and value != previous.get(fieldname):
			return str(value)
	return None


def _request_origin() -> str:
	local = getattr(frappe, "local", None)
	request = getattr(local, "request", None)
	path = str(getattr(request, "path", "") or "")
	if path.startswith("/api/"):
		return "API"
	if request is not None:
		return "DESK"
	return "SYSTEM"


def _correlation_id() -> str:
	local = getattr(frappe, "local", None)
	request = getattr(local, "request", None)
	headers = getattr(request, "headers", {}) or {}
	value = headers.get("X-Request-ID") if hasattr(headers, "get") else None
	return str(value or getattr(local, "request_id", "") or "").strip()


def _fingerprint(payload: dict[str, Any]) -> str:
	canonical = json.dumps(
		payload,
		ensure_ascii=False,
		sort_keys=True,
		default=str,
		separators=(",", ":"),
	)
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _insert_event(values: dict[str, Any]) -> None:
	if hasattr(frappe, "get_meta"):
		allowed = {field.fieldname for field in frappe.get_meta("CC Audit Log").fields}
		payload = {key: value for key, value in values.items() if key == "doctype" or key in allowed}
	else:
		payload = dict(values)
	original = getattr(frappe.flags, "in_construcontrol_audit_insert", False)
	try:
		frappe.flags.in_construcontrol_audit_insert = True
		frappe.get_doc(payload).insert(ignore_permissions=True)
	finally:
		frappe.flags.in_construcontrol_audit_insert = original


def _event_values(
	*,
	module: str,
	action: str,
	record_type: str,
	record_id: str,
	project: str | None,
	previous_state: dict[str, Any],
	next_state: dict[str, Any],
	reason: str | None,
	origin: str,
	correlation_id: str,
) -> dict[str, Any]:
	user = str(frappe.session.user or "Guest")
	display_name = _display_name(user)
	role = _role_label()
	fingerprint_payload = {
		"user": user,
		"role": role,
		"action": action,
		"module": module,
		"record_type": record_type,
		"record_id": record_id,
		"project": project,
		"previous_state": previous_state,
		"next_state": next_state,
		"reason": reason,
		"origin": origin,
		"correlation_id": correlation_id,
	}
	fingerprint = _fingerprint(fingerprint_payload)
	return {
		"doctype": "CC Audit Log",
		"source_key": fingerprint[:40],
		"source_id": record_id or fingerprint[:40],
		"project": project,
		"code": fingerprint[:12].upper(),
		"title": f"{action} · {module} · {record_type} · {record_id}",
		"status": "recorded",
		"posting_date": today(),
		"event_at": now_datetime(),
		"description": f"{display_name} ejecutó {action} sobre {record_type}.",
		"actor": role,
		"actor_name": display_name,
		"actor_email": user,
		"actor_role": role,
		"actor_user_id": user,
		"actor_label": role,
		"action": action,
		"module": module,
		"record_type": record_type,
		"record_id": record_id,
		"previous_state": json.dumps(previous_state, ensure_ascii=False, sort_keys=True, default=str),
		"next_state": json.dumps(next_state, ensure_ascii=False, sort_keys=True, default=str),
		"reason": reason,
		"origin": origin,
		"correlation_id": correlation_id,
		"fingerprint": fingerprint,
		"payload_json": json.dumps(
			{
				"identity": {
					"name": display_name,
					"email": user,
					"role": role,
					"user_id": user,
				},
				"action": action,
				"module": module,
				"record_type": record_type,
				"record_id": record_id,
				"origin": origin,
				"correlation_id": correlation_id,
				"fingerprint": fingerprint,
			},
			ensure_ascii=False,
			sort_keys=True,
		),
		"is_logically_deleted": 0,
	}


def record_event(doc: Any, method: str | None = None) -> None:
	"""Write one immutable, role-aware and secret-free event for ConstruControl records."""
	doctype = str(getattr(doc, "doctype", "") or "")
	if not doctype.startswith("CC ") or doctype in _AUDIT_DOCTYPES:
		return
	flags = getattr(frappe, "flags", None)
	if (
		getattr(flags, "in_construcontrol_migration", False)
		or getattr(flags, "in_construcontrol_recalculation", False)
		or getattr(flags, "in_install", False)
		or getattr(flags, "in_migrate", False)
		or getattr(getattr(doc, "flags", None), "ignore_construcontrol_audit", False)
	):
		return
	if method == "on_update" and getattr(getattr(doc, "flags", None), "in_insert", False):
		return

	previous = _previous_snapshot(doc)
	following = {} if method == "on_trash" else _snapshot(doc)
	if method == "on_update" and previous == following:
		return
	action = _derive_action(method, previous, following)
	values = _event_values(
		module=_module_for(doctype),
		action=action,
		record_type=doctype,
		record_id=str(getattr(doc, "name", "") or ""),
		project=str(doc.get("project") or "") if hasattr(doc, "get") and doc.get("project") else None,
		previous_state=previous,
		next_state=following,
		reason=_reason(previous, following),
		origin=_request_origin(),
		correlation_id=_correlation_id(),
	)
	exists = getattr(frappe.db, "exists", None)
	if exists and exists("CC Audit Log", {"source_key": values["source_key"]}):
		return
	_insert_event(values)


def record_manual_event(
	*,
	module: str,
	action: str,
	record_type: str,
	record_id: str,
	project: str | None = None,
	reason: str | None = None,
	previous_state: dict[str, Any] | None = None,
	next_state: dict[str, Any] | None = None,
	origin: str | None = None,
	correlation_id: str | None = None,
) -> None:
	values = _event_values(
		module=str(module or "AU01"),
		action=str(action or "CHANGE").upper(),
		record_type=str(record_type or ""),
		record_id=str(record_id or ""),
		project=str(project) if project else None,
		previous_state=_clean(previous_state or {}),
		next_state=_clean(next_state or {}),
		reason=str(reason) if reason else None,
		origin=str(origin or _request_origin()),
		correlation_id=str(correlation_id or _correlation_id()),
	)
	exists = getattr(frappe.db, "exists", None)
	if not exists or not exists("CC Audit Log", {"source_key": values["source_key"]}):
		_insert_event(values)


def protect_audit_record(doc: Any, method: str | None = None) -> None:
	"""Forbid manual creation, mutation and deletion of audit records."""
	flags = getattr(frappe, "flags", None)
	if (
		getattr(flags, "in_construcontrol_audit_insert", False)
		or getattr(flags, "in_construcontrol_migration", False)
		or getattr(flags, "in_install", False)
		or getattr(flags, "in_migrate", False)
	):
		return
	if method == "on_trash" or not getattr(doc, "is_new", lambda: False)():
		frappe.throw(_("La auditoría de ConstruControl es inmutable."), frappe.PermissionError)
	frappe.throw(
		_("Los eventos de auditoría solo pueden ser creados por el backend."),
		frappe.PermissionError,
	)


__all__ = [
	"protect_audit_record",
	"record_event",
	"record_manual_event",
]
