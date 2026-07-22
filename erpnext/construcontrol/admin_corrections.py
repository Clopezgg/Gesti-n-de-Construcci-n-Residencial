from __future__ import annotations

import hashlib
import json
import re
import secrets
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime
from frappe.utils.password import check_password, passlibctx

from erpnext.construcontrol.audit import record_manual_event
from erpnext.construcontrol.business_rules import expense_amounts

_AUTH_TTL = 600
_MAX_FAILURES = 5
_LOCK_MINUTES = 15
_PIN_RE = re.compile(r"^[0-9]{6,12}$")
_ALLOWED_FIELDS = {
	"project",
	"phase",
	"title",
	"posting_date",
	"category",
	"subcategory",
	"commercial_source",
	"unit",
	"quantity",
	"description",
	"provider_name",
	"supplier",
	"payment_method",
	"funding_source",
	"labor_contract",
	"labor_payment_type",
	"subtotal_hnl",
	"tax_hnl",
	"withholding_hnl",
	"discount_hnl",
	"paid_amount_hnl",
	"payment_status",
	"professional_approval_status",
	"invoice_number",
	"invoice_date",
	"due_date",
	"purchase_order_reference",
	"cost_center",
	"notes",
}
_FINANCIAL_FIELDS = {
	"subtotal_hnl",
	"tax_hnl",
	"withholding_hnl",
	"discount_hnl",
	"paid_amount_hnl",
	"payment_status",
	"professional_approval_status",
	"funding_source",
	"labor_contract",
}
_OPERATIONS = {"correct", "annul_migrated", "reverse_imported_payment", "register_reimbursement"}
_SNAPSHOT_FIELDS = tuple(
	sorted(
		_ALLOWED_FIELDS
		| {
			"name",
			"source_id",
			"source_key",
			"calculated_total_hnl",
			"amount_hnl",
			"balance_due_hnl",
			"approved_amount_hnl",
			"approval_status",
			"financial_status",
			"status",
			"is_logically_deleted",
		}
	)
)


def _require_administrator() -> None:
	if str(frappe.session.user or "") != "Administrator":
		frappe.throw(
			_("Solo la cuenta Administrator puede ejecutar correcciones críticas."), frappe.PermissionError
		)


def _settings() -> Any:
	return frappe.get_single("ConstruControl Settings")


def _get(doc: Any, field: str, default: Any = None) -> Any:
	return doc.get(field) if doc.meta.has_field(field) else default


def _set(doc: Any, field: str, value: Any) -> None:
	if doc.meta.has_field(field):
		doc.set(field, value)


def _security_status(doc: Any | None = None) -> dict[str, Any]:
	doc = doc or _settings()
	locked_until = (
		frappe.utils.get_datetime(_get(doc, "correction_locked_until"))
		if _get(doc, "correction_locked_until")
		else None
	)
	return {
		"administrator_only": True,
		"enabled": cint(_get(doc, "correction_access_enabled", 0)),
		"configured": bool(str(_get(doc, "correction_pin_hash", "") or "").strip()),
		"pin_updated_at": _get(doc, "correction_pin_updated_at"),
		"last_used_at": _get(doc, "correction_last_used_at"),
		"failed_attempts": cint(_get(doc, "correction_failed_attempts", 0)),
		"locked_until": locked_until,
		"locked": bool(locked_until and locked_until > now_datetime()),
		"authorization_ttl_seconds": _AUTH_TTL,
	}


def _save_settings(doc: Any) -> None:
	doc.flags.ignore_construcontrol_audit = True
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="ConstruControl Settings")


def _auth_failure(message: str) -> None:
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
		next_state={"failed_attempts": attempts},
		origin="ADMIN_CORRECTION",
	)
	frappe.throw(_("No fue posible autorizar la corrección."), frappe.AuthenticationError)


def _verify_password(password: str) -> None:
	try:
		check_password("Administrator", str(password or ""), delete_tracker_cache=False)
	except Exception:
		_auth_failure("Contraseña de Administrator no válida.")


def _session_id() -> str:
	return str(getattr(frappe.session, "sid", "") or "")


def _token_key(token: str) -> str:
	digest = hashlib.sha256(str(token or "").encode()).hexdigest()
	return f"construcontrol:admin-correction:{_session_id()}:{digest}"


def _require_token(token: str) -> dict[str, Any]:
	_require_administrator()
	payload = frappe.cache.get_value(_token_key(token), expires=True) if token else None
	if not isinstance(payload, dict) or payload.get("session_id") != _session_id():
		frappe.throw(_("La autorización expiró o no pertenece a esta sesión."), frappe.PermissionError)
	return payload


def _reason(value: str) -> str:
	value = " ".join(str(value or "").split())
	if len(value) < 12 or len(value) > 1000:
		frappe.throw(_("Explique el motivo de la corrección con entre 12 y 1000 caracteres."))
	return value


def _evidence(value: str, required: bool) -> str:
	value = str(value or "").strip()
	if required and not value:
		frappe.throw(_("Adjunte una evidencia privada para la corrección financiera."))
	if value:
		file_name = frappe.db.get_value("File", {"file_url": value}, "name")
		if not file_name or not cint(frappe.db.get_value("File", file_name, "is_private")):
			frappe.throw(_("La evidencia debe existir y estar guardada como archivo privado."))
	return value


def _parse_mapping(value: Any) -> dict[str, Any]:
	if isinstance(value, dict):
		return dict(value)
	try:
		parsed = frappe.parse_json(value or "{}")
	except Exception:
		frappe.throw(_("Los cambios no contienen JSON válido."))
	if not isinstance(parsed, dict):
		frappe.throw(_("Los cambios deben enviarse como objeto JSON."))
	return parsed


def _snapshot(doc: Any) -> dict[str, Any]:
	return {field: doc.get(field) for field in _SNAPSHOT_FIELDS if doc.meta.has_field(field)}


def _fingerprint(value: Any) -> str:
	raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
	return hashlib.sha256(raw.encode()).hexdigest()


def _derive(values: dict[str, Any]) -> dict[str, Any]:
	subtotal = flt(
		values.get("subtotal_hnl")
		if values.get("subtotal_hnl") not in (None, "")
		else values.get("amount_hnl")
	)
	total = round(
		subtotal
		+ flt(values.get("tax_hnl"))
		- flt(values.get("withholding_hnl"))
		- flt(values.get("discount_hnl")),
		2,
	)
	if total < 0:
		frappe.throw(_("Las retenciones y descuentos no pueden superar el subtotal más impuestos."))
	paid = round(flt(values.get("paid_amount_hnl")), 2)
	if paid < 0 or paid > total + 0.005:
		frappe.throw(_("El monto pagado debe estar entre cero y el total."))
	payment = str(values.get("payment_status") or "draft").lower()
	approval = str(values.get("professional_approval_status") or "draft").lower()
	if approval == "pending_approval":
		approval = "pending"
	if payment == "cancelled":
		paid, balance, approval, financial, operational = 0.0, 0.0, "draft", "cancelled", "cancelled"
	elif payment == "reimbursed":
		if paid <= 0:
			frappe.throw(_("Un reembolso requiere conservar el monto pagado histórico."))
		balance, financial, operational = 0.0, "reimbursed", "cancelled"
	elif payment == "paid":
		paid, balance, approval, financial, operational = total, 0.0, "approved", "paid", "active"
	elif payment == "partially_paid":
		if not 0 < paid < total:
			frappe.throw(_("Un pago parcial debe ser mayor que cero y menor que el total."))
		balance, approval, financial, operational = round(total - paid, 2), "approved", "paid", "active"
	elif payment in {"approved", "overdue"}:
		balance, approval = round(total - paid, 2), "approved"
		financial, operational = ("paid", "active") if paid > 0 else ("pending", "pending")
	elif payment == "pending_approval":
		balance, approval, financial, operational = round(total - paid, 2), "pending", "pending", "pending"
	else:
		payment, balance, approval, financial, operational = (
			"draft",
			round(total - paid, 2),
			"draft",
			"pending",
			"pending",
		)
	values.update(
		{
			"subtotal_hnl": subtotal,
			"calculated_total_hnl": total,
			"amount_hnl": total,
			"paid_amount_hnl": paid,
			"balance_due_hnl": balance,
			"payment_status": payment,
			"professional_approval_status": approval,
			"approval_status": {
				"draft": "draft",
				"pending": "pending_approval",
				"approved": "approved",
				"rejected": "rejected",
			}.get(approval, "draft"),
			"approved_amount_hnl": total if approval == "approved" else 0.0,
			"financial_status": financial,
			"status": operational,
		}
	)
	return values


def _validate_links(values: dict[str, Any]) -> None:
	project = str(values.get("project") or "")
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(_("El proyecto seleccionado no existe."))
	phase = str(values.get("phase") or "")
	if phase and frappe.db.get_value("CC Construction Phase", phase, "project") != project:
		frappe.throw(_("La fase no pertenece al proyecto."))
	fund = str(values.get("funding_source") or "")
	if fund and frappe.db.get_value("CC Funding Source", fund, "project") != project:
		frappe.throw(_("La fuente de fondos no pertenece al proyecto."))
	contract = str(values.get("labor_contract") or "")
	if contract:
		row = frappe.db.get_value("CC Labor Contract", contract, ["project", "phase", "status"], as_dict=True)
		if not row or row.project != project or (row.phase and phase and row.phase != phase):
			frappe.throw(_("El contrato no corresponde al proyecto y fase seleccionados."))
		if str(row.status or "").lower() == "cancelled":
			frappe.throw(_("No puede usar un contrato anulado."))
	supplier = str(values.get("supplier") or "")
	if supplier and not frappe.db.exists("Supplier", supplier):
		frappe.throw(_("El proveedor seleccionado no existe."))


def _prepare(name: str, operation: str, changes: Any, reason: str, evidence: str) -> dict[str, Any]:
	if not frappe.db.exists("CC Expense Control", name):
		frappe.throw(_("El gasto seleccionado no existe."))
	operation = str(operation or "correct").lower()
	if operation not in _OPERATIONS:
		frappe.throw(_("Seleccione una operación válida."))
	doc = frappe.get_doc("CC Expense Control", name)
	before = _snapshot(doc)
	requested = _parse_mapping(changes)
	unknown = sorted(set(requested) - _ALLOWED_FIELDS)
	if unknown:
		frappe.throw(_("Campos no autorizados: {0}").format(", ".join(unknown)))
	proposed = dict(before)
	proposed.update({key: value for key, value in requested.items() if doc.meta.has_field(key)})
	historical = bool(doc.get("source_id") or doc.get("source_key"))
	if operation == "annul_migrated":
		if not historical or flt(before.get("paid_amount_hnl")) > 0:
			frappe.throw(_("Use esta operación solo para un gasto migrado sin pago."))
		proposed.update(
			{"paid_amount_hnl": 0, "payment_status": "cancelled", "professional_approval_status": "draft"}
		)
	elif operation == "reverse_imported_payment":
		if not historical:
			frappe.throw(_("Esta operación solo aplica a registros migrados."))
		proposed["paid_amount_hnl"] = flt(requested.get("paid_amount_hnl", 0))
		proposed["payment_status"] = str(
			requested.get("payment_status")
			or ("cancelled" if proposed["paid_amount_hnl"] <= 0 else "partially_paid")
		)
		proposed["professional_approval_status"] = (
			"approved" if proposed["payment_status"] in {"approved", "partially_paid", "paid"} else "draft"
		)
	elif operation == "register_reimbursement":
		if flt(before.get("paid_amount_hnl")) <= 0:
			frappe.throw(_("Solo puede reembolsarse un gasto con pago registrado."))
		proposed.update({"paid_amount_hnl": before.get("paid_amount_hnl"), "payment_status": "reimbursed"})
	elif not requested:
		frappe.throw(_("Indique al menos un cambio."))
	proposed = _derive(proposed)
	_validate_links(proposed)
	reason = _reason(reason)
	evidence = _evidence(evidence, operation != "correct" or bool(set(requested) & _FINANCIAL_FIELDS))
	before_amounts = expense_amounts(
		before.get("amount_hnl"),
		before.get("payment_status"),
		before.get("financial_status"),
		before.get("paid_amount_hnl"),
		before.get("balance_due_hnl"),
		before.get("professional_approval_status"),
	)
	after_amounts = expense_amounts(
		proposed.get("amount_hnl"),
		proposed.get("payment_status"),
		proposed.get("financial_status"),
		proposed.get("paid_amount_hnl"),
		proposed.get("balance_due_hnl"),
		proposed.get("professional_approval_status"),
	)
	impact = {
		"recognized_hnl": {
			"before": before_amounts[0],
			"after": after_amounts[0],
			"delta": round(after_amounts[0] - before_amounts[0], 2),
		},
		"paid_hnl": {
			"before": before_amounts[1],
			"after": after_amounts[1],
			"delta": round(after_amounts[1] - before_amounts[1], 2),
		},
		"pending_hnl": {
			"before": before_amounts[2],
			"after": after_amounts[2],
			"delta": round(after_amounts[2] - before_amounts[2], 2),
		},
		"funding_sources": sorted(
			{str(v) for v in (before.get("funding_source"), proposed.get("funding_source")) if v}
		),
		"contracts": sorted(
			{str(v) for v in (before.get("labor_contract"), proposed.get("labor_contract")) if v}
		),
		"projects": sorted({str(v) for v in (before.get("project"), proposed.get("project")) if v}),
	}
	payload = {
		"expense": name,
		"operation": operation,
		"reason": reason,
		"evidence": evidence,
		"before": before,
		"proposed": proposed,
		"impact": impact,
	}
	payload["preview_hash"] = _fingerprint(payload)
	return payload


@contextmanager
def _correction_context() -> Any:
	previous = getattr(frappe.flags, "in_construcontrol_admin_correction", False)
	frappe.flags.in_construcontrol_admin_correction = True
	try:
		yield
	finally:
		frappe.flags.in_construcontrol_admin_correction = previous


def _recalculate(before: dict[str, Any], after: dict[str, Any]) -> None:
	from erpnext.construcontrol.construction import recalculate_contract, recalculate_project_control
	from erpnext.construcontrol.finance import recalculate_funding_source

	for name in {str(v) for v in (before.get("funding_source"), after.get("funding_source")) if v}:
		recalculate_funding_source(name)
	for name in {str(v) for v in (before.get("labor_contract"), after.get("labor_contract")) if v}:
		recalculate_contract(name)
	for project in {str(v) for v in (before.get("project"), after.get("project")) if v}:
		recalculate_project_control(project)


@frappe.whitelist()
def get_security_status() -> dict[str, Any]:
	_require_administrator()
	return _security_status()


@frappe.whitelist(methods=["POST"])
def configure_correction_pin(current_password: str, new_pin: str, enabled: int | str = 1) -> dict[str, Any]:
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
		_auth_failure("Clave de corrección no válida.")
	_set(doc, "correction_failed_attempts", 0)
	_set(doc, "correction_locked_until", None)
	_set(doc, "correction_last_used_at", now_datetime())
	_save_settings(doc)
	token = secrets.token_urlsafe(36)
	authorization_id = f"CCA-{now_datetime().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
	expires_at = now_datetime() + timedelta(seconds=_AUTH_TTL)
	frappe.cache.set_value(
		_token_key(token),
		{"session_id": _session_id(), "authorization_id": authorization_id, "expires_at": expires_at},
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
def preview_expense_correction(
	expense_name: str,
	operation: str,
	changes: Any,
	reason: str,
	evidence: str = "",
	authorization_token: str = "",
) -> dict[str, Any]:
	_require_token(authorization_token)
	return _prepare(str(expense_name or ""), operation, changes, reason, evidence)


@frappe.whitelist(methods=["POST"])
def execute_expense_correction(
	expense_name: str,
	operation: str,
	changes: Any,
	reason: str,
	evidence: str,
	preview_hash: str,
	authorization_token: str,
) -> dict[str, Any]:
	authorization = _require_token(authorization_token)
	payload = _prepare(str(expense_name or ""), operation, changes, reason, evidence)
	if not secrets.compare_digest(str(preview_hash or ""), payload["preview_hash"]):
		frappe.throw(_("La vista previa no coincide con la corrección solicitada."))
	lock = frappe.cache.lock(
		f"construcontrol:admin-correction:expense:{payload['expense']}", timeout=120, blocking_timeout=5
	)
	if not lock.acquire(blocking=True):
		frappe.throw(_("Existe otra corrección sobre este gasto."))
	savepoint = f"cc_expense_{secrets.token_hex(6)}"
	frappe.db.savepoint(savepoint)
	try:
		doc = frappe.get_doc("CC Expense Control", payload["expense"])
		before = _snapshot(doc)
		if before != payload["before"]:
			frappe.throw(_("El gasto cambió después de la vista previa."))
		with _correction_context():
			for field, value in payload["proposed"].items():
				if field != "name" and doc.meta.has_field(field):
					doc.set(field, value)
			for field, value in {
				"last_admin_correction_id": authorization["authorization_id"],
				"last_admin_correction_at": now_datetime(),
				"last_admin_correction_reason": payload["reason"],
				"last_admin_correction_evidence": payload["evidence"] or None,
			}.items():
				if doc.meta.has_field(field):
					doc.set(field, value)
			if payload["evidence"] and doc.meta.has_field("payment_evidence"):
				doc.payment_evidence = payload["evidence"]
			if payload["operation"] != "correct" and doc.meta.has_field("rejection_reason"):
				doc.rejection_reason = payload["reason"]
			doc.flags.ignore_construcontrol_audit = True
			doc.save(ignore_permissions=True)
			after = _snapshot(doc)
			_recalculate(before, after)
			record_manual_event(
				module="MIG",
				action=f"ADMIN_{payload['operation'].upper()}",
				record_type="CC Expense Control",
				record_id=doc.name,
				project=str(after.get("project") or "") or None,
				reason=payload["reason"],
				previous_state=before,
				next_state={
					**after,
					"evidence": payload["evidence"],
					"impact": payload["impact"],
					"authorization_id": authorization["authorization_id"],
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
		"expense": doc.name,
		"operation": payload["operation"],
		"authorization_id": authorization["authorization_id"],
		"before": before,
		"after": _snapshot(doc),
		"impact": payload["impact"],
	}


__all__ = [
	"authorize_correction",
	"configure_correction_pin",
	"execute_expense_correction",
	"get_security_status",
	"preview_expense_correction",
]
