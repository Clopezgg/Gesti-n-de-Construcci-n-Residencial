from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime
from frappe.utils.password import check_password, passlibctx

from erpnext.construcontrol.admin_corrections import (
	_AUTH_TTL,
	_LOCK_MINUTES,
	_MAX_FAILURES,
	_PIN_RE,
	_get,
	_require_administrator,
	_security_status,
	_session_id,
	_set,
	_settings,
	_token_key,
)
from erpnext.construcontrol.audit import record_manual_event


def _save_settings(doc: Any) -> None:
	doc.flags.ignore_construcontrol_audit = True
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="ConstruControl Settings")


def _persist_failure(message: str) -> None:
	"""Persist lockout evidence before raising an authentication error."""
	doc = _settings()
	attempts = cint(_get(doc, "correction_failed_attempts", 0)) + 1
	_set(doc, "correction_failed_attempts", attempts)
	if attempts >= _MAX_FAILURES:
		_set(doc, "correction_locked_until", now_datetime() + timedelta(minutes=_LOCK_MINUTES))
	_save_settings(doc)
	record_manual_event(
		module="AU01",
		action="CORRECTION_AUTH_FAILED",
		record_type="ConstruControl Settings",
		record_id="ConstruControl Settings",
		reason=message,
		next_state={
			"failed_attempts": attempts,
			"locked_until": _get(doc, "correction_locked_until"),
		},
		origin="ADMIN_CORRECTION",
	)
	# The authentication exception rolls back the request; commit only the lockout evidence first.
	frappe.db.commit()  # nosemgrep
	frappe.throw(_("No fue posible autorizar la corrección."), frappe.AuthenticationError)


def _verify_password(password: str) -> None:
	try:
		check_password("Administrator", str(password or ""), delete_tracker_cache=False)
	except Exception:
		_persist_failure("Contraseña de Administrator no válida.")


def require_authorization_token(token: str) -> dict[str, Any]:
	_require_administrator()
	payload = frappe.cache.get_value(_token_key(token), expires=True) if token else None
	if not isinstance(payload, dict) or payload.get("session_id") != _session_id():
		frappe.throw(_("La autorización expiró o no pertenece a esta sesión."), frappe.PermissionError)
	return payload


@frappe.whitelist()
def get_security_status() -> dict[str, Any]:
	_require_administrator()
	return _security_status()


@frappe.whitelist(methods=["POST"])
def configure_correction_pin(
	current_password: str,
	new_pin: str,
	enabled: int | str = 1,
) -> dict[str, Any]:
	_require_administrator()
	if not _PIN_RE.fullmatch(str(new_pin or "")):
		frappe.throw(_("La clave debe contener entre 6 y 12 dígitos."))
	_verify_password(current_password)
	doc = _settings()
	before = _security_status(doc)
	_set(doc, "correction_pin_hash", passlibctx.hash(str(new_pin)))
	_set(doc, "correction_access_enabled", cint(enabled))
	_set(doc, "correction_pin_updated_at", now_datetime())
	_set(doc, "correction_failed_attempts", 0)
	_set(doc, "correction_locked_until", None)
	_save_settings(doc)
	after = _security_status(doc)
	record_manual_event(
		module="AU01",
		action="CORRECTION_PIN_CONFIGURED",
		record_type="ConstruControl Settings",
		record_id="ConstruControl Settings",
		reason="Administrator configuró o rotó la clave de corrección.",
		previous_state=before,
		next_state=after,
		origin="ADMIN_CORRECTION",
	)
	return after


@frappe.whitelist(methods=["POST"])
def authorize_correction(current_password: str, pin: str) -> dict[str, Any]:
	_require_administrator()
	doc = _settings()
	status = _security_status(doc)
	if not status["configured"] or not status["enabled"]:
		frappe.throw(_("El acceso a correcciones no está configurado o está desactivado."))
	if status["locked"]:
		frappe.throw(_("El acceso está bloqueado temporalmente."), frappe.PermissionError)
	_verify_password(current_password)
	try:
		valid = passlibctx.verify(str(pin or ""), str(_get(doc, "correction_pin_hash", "") or ""))
	except Exception:
		valid = False
	if not valid:
		_persist_failure("Clave de corrección no válida.")

	_set(doc, "correction_failed_attempts", 0)
	_set(doc, "correction_locked_until", None)
	_set(doc, "correction_last_used_at", now_datetime())
	_save_settings(doc)
	token = secrets.token_urlsafe(36)
	authorization_id = f"CCA-{now_datetime().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
	expires_at = now_datetime() + timedelta(seconds=_AUTH_TTL)
	frappe.cache.set_value(
		_token_key(token),
		{
			"session_id": _session_id(),
			"authorization_id": authorization_id,
			"expires_at": expires_at,
		},
		expires_in_sec=_AUTH_TTL,
	)
	record_manual_event(
		module="AU01",
		action="CORRECTION_AUTHORIZED",
		record_type="ConstruControl Settings",
		record_id="ConstruControl Settings",
		reason="Administrator abrió una sesión temporal de corrección.",
		next_state={"authorization_id": authorization_id, "expires_at": expires_at},
		origin="ADMIN_CORRECTION",
		correlation_id=authorization_id,
	)
	return {
		"token": token,
		"authorization_id": authorization_id,
		"expires_at": expires_at,
		"ttl_seconds": _AUTH_TTL,
	}


@frappe.whitelist(methods=["POST"])
def revoke_correction(authorization_token: str) -> dict[str, Any]:
	payload = require_authorization_token(authorization_token)
	frappe.cache.delete_value(_token_key(authorization_token))
	record_manual_event(
		module="AU01",
		action="CORRECTION_AUTH_REVOKED",
		record_type="ConstruControl Settings",
		record_id="ConstruControl Settings",
		reason="Administrator cerró manualmente la sesión de corrección.",
		next_state={"authorization_id": payload.get("authorization_id")},
		origin="ADMIN_CORRECTION",
		correlation_id=payload.get("authorization_id"),
	)
	return {"revoked": True, "authorization_id": payload.get("authorization_id")}


__all__ = [
	"authorize_correction",
	"configure_correction_pin",
	"get_security_status",
	"require_authorization_token",
	"revoke_correction",
]
