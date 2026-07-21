from __future__ import annotations

import secrets
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from erpnext.construcontrol.admin_corrections import (
	_correction_context,
	_fingerprint,
	_reason,
	_require_token,
)
from erpnext.construcontrol.audit import record_manual_event

_OPERATIONS = {"archive", "consolidate", "anonymize_profile"}
_PROTECTED = {"Administrator", "Guest"}


def _user_snapshot(user: str) -> dict[str, Any]:
	if not frappe.db.exists("User", user):
		frappe.throw(_("El usuario seleccionado no existe."))
	meta = frappe.get_meta("User")
	fields = [
		field
		for field in (
			"name",
			"email",
			"first_name",
			"last_name",
			"full_name",
			"enabled",
			"user_type",
			"last_login",
			"last_active",
			"mobile_no",
			"phone",
			"user_image",
			"cc_archived_by_correction",
			"cc_replacement_user",
			"cc_correction_note",
		)
		if field == "name" or meta.has_field(field)
	]
	row = frappe.db.get_value("User", user, fields, as_dict=True)
	result = dict(row or {})
	result["roles"] = sorted(
		str(role)
		for role in frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "parent": user},
			pluck="role",
		)
		if role
	)
	return result


def _enabled_system_managers(exclude: str = "") -> list[str]:
	users = {
		str(user)
		for user in frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "role": "System Manager"},
			pluck="parent",
		)
		if user
	}
	users.add("Administrator")
	return sorted(
		user
		for user in users
		if user != exclude
		and frappe.db.exists("User", user)
		and cint(frappe.db.get_value("User", user, "enabled")) == 1
	)


def _permission_rows(user: str) -> list[dict[str, Any]]:
	meta = frappe.get_meta("User Permission")
	fields = [
		field
		for field in (
			"name",
			"allow",
			"for_value",
			"is_default",
			"apply_to_all_doctypes",
			"applicable_for",
		)
		if field == "name" or meta.has_field(field)
	]
	return [
		dict(row)
		for row in frappe.get_all(
			"User Permission",
			filters={"user": user},
			fields=fields,
			order_by="creation asc",
		)
	]


def _assignment_report(user: str) -> dict[str, Any]:
	phases: list[str] = []
	if frappe.db.exists("DocType", "CC Construction Phase") and frappe.get_meta(
		"CC Construction Phase"
	).has_field("responsible_user"):
		phases = frappe.get_all(
			"CC Construction Phase",
			filters={"responsible_user": user, "is_logically_deleted": 0},
			pluck="name",
		)
	return {
		"user_permissions": _permission_rows(user),
		"responsible_phases": phases,
		"historical_authorship_preserved": True,
		"legacy_user_access_preserved": bool(
			frappe.db.exists("CC User Access", {"email": user})
			if frappe.db.exists("DocType", "CC User Access")
			else False
		),
	}


def _prepare(user: str, operation: str, replacement_user: str, reason: str) -> dict[str, Any]:
	user = str(user or "").strip()
	operation = str(operation or "archive").strip().lower()
	replacement_user = str(replacement_user or "").strip()
	if operation not in _OPERATIONS:
		frappe.throw(_("Seleccione una operación de usuario válida."))
	if user in _PROTECTED or user == str(frappe.session.user or ""):
		frappe.throw(_("No puede archivar la cuenta protegida o la sesión que está utilizando."))
	before = _user_snapshot(user)
	if "System Manager" in set(before.get("roles") or []) and not _enabled_system_managers(exclude=user):
		frappe.throw(_("La última cuenta administrativa habilitada no puede archivarse."))
	if operation == "consolidate" and not replacement_user:
		frappe.throw(_("Seleccione la cuenta que conservará el acceso."))
	if replacement_user:
		if replacement_user == user or replacement_user in _PROTECTED:
			frappe.throw(_("Seleccione una cuenta sustituta distinta y no protegida."))
		replacement = _user_snapshot(replacement_user)
		if not cint(replacement.get("enabled")):
			frappe.throw(_("La cuenta sustituta debe estar habilitada."))
	else:
		replacement = None
	reason = _reason(reason)
	assignments = _assignment_report(user)
	payload = {
		"user": before,
		"operation": operation,
		"replacement": replacement,
		"assignments": assignments,
		"reason": reason,
		"changes": {
			"enabled": 0,
			"profile_anonymized": operation == "anonymize_profile",
			"permissions_copied": bool(replacement),
			"responsibilities_reassigned": bool(replacement),
			"historical_owner_modified_by_unchanged": True,
		},
	}
	payload["preview_hash"] = _fingerprint(payload)
	return payload


def _copy_permissions(source: str, target: str) -> int:
	created = 0
	meta = frappe.get_meta("User Permission")
	for row in _permission_rows(source):
		filters = {
			"user": target,
			"allow": row.get("allow"),
			"for_value": row.get("for_value"),
		}
		if meta.has_field("applicable_for"):
			filters["applicable_for"] = row.get("applicable_for") or ""
		if not frappe.db.exists("User Permission", filters):
			values: dict[str, Any] = {"doctype": "User Permission", **filters}
			for field in ("is_default", "apply_to_all_doctypes"):
				if meta.has_field(field):
					values[field] = cint(row.get(field))
			frappe.get_doc(values).insert(ignore_permissions=True)
			created += 1
	return created


def _remove_permissions(user: str) -> int:
	names = frappe.get_all("User Permission", filters={"user": user}, pluck="name")
	for name in names:
		frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)
	return len(names)


def _reassign_responsibilities(source: str, target: str) -> int:
	if not frappe.db.exists("DocType", "CC Construction Phase") or not frappe.get_meta(
		"CC Construction Phase"
	).has_field("responsible_user"):
		return 0
	names = frappe.get_all(
		"CC Construction Phase",
		filters={"responsible_user": source, "is_logically_deleted": 0},
		pluck="name",
	)
	for name in names:
		frappe.db.set_value(
			"CC Construction Phase",
			name,
			"responsible_user",
			target,
			update_modified=True,
		)
	return len(names)


@frappe.whitelist(methods=["POST"])
def preview_user_correction(
	user: str,
	operation: str,
	replacement_user: str = "",
	reason: str = "",
	authorization_token: str = "",
) -> dict[str, Any]:
	_require_token(authorization_token)
	return _prepare(user, operation, replacement_user, reason)


@frappe.whitelist(methods=["POST"])
def execute_user_correction(
	user: str,
	operation: str,
	replacement_user: str,
	reason: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _prepare(user, operation, replacement_user, reason)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa del usuario cambió. Genérela nuevamente."))
	source = str(payload["user"]["name"])
	target = str(payload["replacement"]["name"]) if payload.get("replacement") else ""
	lock = frappe.cache.lock(
		f"construcontrol:user-correction:{source}", timeout=120, blocking_timeout=5
	)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra corrección sobre este usuario."))
	savepoint = f"cc_user_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	permission_count = responsibility_count = 0
	try:
		with _correction_context():
			if target:
				permission_count = _copy_permissions(source, target)
				responsibility_count = _reassign_responsibilities(source, target)
				_remove_permissions(source)
			updates: dict[str, Any] = {
				"enabled": 0,
				"cc_archived_by_correction": 1,
				"cc_replacement_user": target or None,
				"cc_correction_note": payload["reason"],
			}
			if payload["operation"] == "anonymize_profile":
				updates.update(
					{
						"first_name": "Usuario archivado",
						"last_name": "",
						"mobile_no": "",
						"phone": "",
						"user_image": "",
					}
				)
			meta = frappe.get_meta("User")
			updates = {key: value for key, value in updates.items() if meta.has_field(key)}
			frappe.db.set_value("User", source, updates, update_modified=True)
			frappe.clear_cache(user=source)
			if target:
				frappe.clear_cache(user=target)
			record_manual_event(
				module="US01",
				action=f"ADMIN_USER_{payload['operation'].upper()}",
				record_type="User",
				record_id=source,
				reason=payload["reason"],
				previous_state=payload,
				next_state={
					"user": _user_snapshot(source),
					"replacement": _user_snapshot(target) if target else None,
					"permissions_created": permission_count,
					"responsibilities_reassigned": responsibility_count,
					"historical_authorship_preserved": True,
					"authorization_id": authorization["authorization_id"],
					"executed_at": now_datetime(),
				},
				origin="ADMIN_CORRECTION",
				correlation_id=authorization["authorization_id"],
			)
		frappe.db.release_savepoint(savepoint)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	finally:
		try:
			lock.release()
		except Exception:
			pass
	return {
		"user": source,
		"operation": payload["operation"],
		"replacement_user": target or None,
		"permissions_created": permission_count,
		"responsibilities_reassigned": responsibility_count,
		"authorization_id": authorization["authorization_id"],
	}


__all__ = ["execute_user_correction", "preview_user_correction"]
