from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.construcontrol.access import require_construcontrol_access, validate_document_project_access
from erpnext.construcontrol.business_rules import funding_amounts

_ALLOWED_CHANNELS = {"remittance", "deposit", "transfer", "cash", "other"}
_ALLOWED_RECONCILIATION = {"pending", "verified", "reconciled", "rejected"}


def _has_field(doc: Document, fieldname: str) -> bool:
	return bool(doc.meta.has_field(fieldname))


def _first_present(doc: Document, *fieldnames: str, default: Any = None) -> Any:
	for fieldname in fieldnames:
		value = doc.get(fieldname)
		if value not in (None, ""):
			return value
	return default


def validate_treasury_source(doc: Document, method: str | None = None) -> None:
	"""Validate and calculate a professional ConstruControl funding record."""
	if not _has_field(doc, "transaction_channel"):
		return
	validate_document_project_access(doc)

	channel = str(doc.get("transaction_channel") or "").strip().lower()
	if channel not in _ALLOWED_CHANNELS:
		frappe.throw(_("Seleccione un canal de ingreso válido."))

	institution = str(doc.get("financial_institution") or "").strip()
	if channel == "cash" and not institution and frappe.db.exists("CC Financial Institution", "CASH"):
		doc.financial_institution = "CASH"
		institution = "CASH"
	if channel != "cash" and not institution:
		frappe.throw(_("Seleccione el banco o la remesadora que procesó el ingreso."))

	if institution:
		values = frappe.db.get_value(
			"CC Financial Institution",
			institution,
			[
				"institution_type",
				"is_active",
				"is_logically_deleted",
				"supports_remittance",
				"supports_deposit",
				"supports_transfer",
			],
			as_dict=True,
		)
		if not values or not values.is_active or values.is_logically_deleted:
			frappe.throw(_("La institución financiera seleccionada no está activa."))
		capability = {
			"remittance": "supports_remittance",
			"deposit": "supports_deposit",
			"transfer": "supports_transfer",
		}.get(channel)
		if capability and not values.get(capability):
			frappe.throw(_("La institución seleccionada no está habilitada para este canal."))
		if channel == "cash" and values.institution_type != "cash":
			frappe.throw(_("Los ingresos en efectivo deben utilizar la institución Efectivo."))

	try:
		amounts = funding_amounts(
			_first_present(doc, "gross_amount", "original_amount", "amount_hnl", default=0),
			doc.get("fee_amount"),
			_first_present(doc, "original_currency", "currency", default="HNL"),
			_first_present(doc, "treasury_exchange_rate", "exchange_rate", default=1),
		)
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))

	gross = float(amounts["gross"])
	fee = float(amounts["fee"])
	net = gross - fee
	rate = float(amounts["exchange_rate"])
	net_hnl = net * rate
	if round(net_hnl, 2) != amounts["net_hnl"]:
		frappe.throw(_("La conversión FI01 produjo un resultado inconsistente."))

	doc.gross_amount = gross
	doc.fee_amount = fee
	doc.net_amount = net
	doc.original_currency = amounts["currency"]
	doc.treasury_exchange_rate = rate
	doc.net_amount_hnl = round(net_hnl, 2)
	doc.amount_hnl = round(net_hnl, 2)
	if _has_field(doc, "original_amount"):
		doc.original_amount = amounts["gross"]
	if _has_field(doc, "exchange_rate"):
		doc.exchange_rate = amounts["exchange_rate"]
	if _has_field(doc, "currency"):
		doc.currency = amounts["currency"]

	reconciliation = str(doc.get("reconciliation_status") or "pending").strip().lower()
	if reconciliation not in _ALLOWED_RECONCILIATION:
		frappe.throw(_("Seleccione un estado de conciliación válido."))
	doc.reconciliation_status = reconciliation

	reference = str(doc.get("transaction_reference") or doc.get("reference") or "").strip()
	historical = bool(doc.get("source_id") or doc.get("source_key"))
	requires_reference = channel in {"remittance", "deposit", "transfer"}
	if (
		requires_reference
		and not reference
		and (not historical or reconciliation in {"verified", "reconciled"})
	):
		frappe.throw(_("Ingrese la referencia o número de operación."))
	if reference:
		doc.transaction_reference = reference
		if _has_field(doc, "reference"):
			doc.reference = reference

	requires_sender = channel == "remittance" and (
		not historical or reconciliation in {"verified", "reconciled"}
	)
	if requires_sender and not str(doc.get("sender") or "").strip():
		frappe.throw(_("Indique quién envió la remesa."))
	if reconciliation == "reconciled":
		if not doc.get("date_received"):
			frappe.throw(_("Una operación conciliada debe tener fecha de recepción."))
		if not reference:
			frappe.throw(_("Una operación conciliada debe tener referencia bancaria."))
		if not str(doc.get("treasury_evidence") or "").strip():
			frappe.throw(_("Adjunte el comprobante antes de conciliar."))
		doc.status = "received"
	elif reconciliation == "rejected":
		doc.status = "cancelled"


def protect_financial_institution_delete(doc: Document, method: str | None = None) -> None:
	if doc.get("is_protected"):
		frappe.throw(
			_("Esta institución forma parte del catálogo base. Puede desactivarla, pero no eliminarla."),
			frappe.PermissionError,
		)
	linked = frappe.db.count(
		"CC Funding Source", {"financial_institution": doc.name, "is_logically_deleted": 0}
	)
	if linked:
		frappe.throw(_("No puede eliminar una institución que ya tiene ingresos relacionados."))


@frappe.whitelist()
def get_institution_visual(institution: str) -> dict[str, Any]:
	require_construcontrol_access()
	institution = str(institution or "").strip()
	if not institution:
		return {}
	values = frappe.db.get_value(
		"CC Financial Institution",
		institution,
		[
			"name",
			"institution_name",
			"short_name",
			"institution_type",
			"logo_file",
			"logo_path",
			"brand_color",
			"is_active",
			"logo_verified",
		],
		as_dict=True,
	)
	if not values or not values.is_active:
		return {}
	return dict(values)


__all__ = ["get_institution_visual", "protect_financial_institution_delete", "validate_treasury_source"]
