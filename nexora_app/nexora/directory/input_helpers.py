from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.directory.constants import CONTACT_TYPES, IDENTIFIER_TYPES
from nexora.directory.core import (
	fingerprint,
	mask_value,
	normalize_contact,
	normalize_identifier,
	unique_nonempty,
	validate_period,
)


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _identifier_rows(rows: list[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
	result: list[dict[str, Any]] = []
	for row in rows or []:
		kind = _required(row, "identifier_type", "Cada identificador requiere tipo.").title()
		if kind not in IDENTIFIER_TYPES:
			frappe.throw(_("Tipo de identificador no permitido."))
		value = _required(row, "identifier_value", "Cada identificador requiere valor.")
		try:
			normalized = normalize_identifier(kind, value)
			validate_period(row.get("valid_from"), row.get("valid_until"))
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		result.append(
			{
				"doctype": "NXR Entity Identifier",
				"identifier_type": kind,
				"identifier_value": value,
				"masked_value": mask_value(value),
				"normalized_hash": fingerprint("identifier", kind, normalized),
				"is_primary": int(bool(row.get("is_primary"))),
				"valid_from": row.get("valid_from"),
				"valid_until": row.get("valid_until"),
			}
		)
	hashes = [row["normalized_hash"] for row in result]
	if not unique_nonempty(hashes):
		frappe.throw(_("El payload contiene identificadores duplicados."))
	if sum(row["is_primary"] for row in result) > 1:
		frappe.throw(_("Solo un identificador puede marcarse como principal."))
	return result


def _contact_rows(rows: list[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
	result: list[dict[str, Any]] = []
	for row in rows or []:
		kind = _required(row, "contact_type", "Cada contacto requiere tipo.").title()
		if kind not in CONTACT_TYPES:
			frappe.throw(_("Tipo de contacto no permitido."))
		value = _required(row, "contact_value", "Cada contacto requiere valor.")
		try:
			normalized = normalize_contact(kind, value)
			validate_period(row.get("valid_from"), row.get("valid_until"))
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		result.append(
			{
				"doctype": "NXR Entity Contact",
				"contact_type": kind,
				"contact_value": value,
				"masked_value": mask_value(value),
				"normalized_hash": fingerprint("contact", kind, normalized),
				"is_primary": int(bool(row.get("is_primary"))),
				"is_verified": int(bool(row.get("is_verified"))),
				"valid_from": row.get("valid_from"),
				"valid_until": row.get("valid_until"),
			}
		)
	hashes = [row["normalized_hash"] for row in result]
	if not unique_nonempty(hashes):
		frappe.throw(_("El payload contiene contactos duplicados."))
	if sum(row["is_primary"] for row in result) > 1:
		frappe.throw(_("Solo un contacto puede marcarse como principal."))
	return result


def _validated_evidence(name: str | None) -> str | None:
	value = str(name or "").strip()
	if not value:
		return None
	row = frappe.db.get_value("NXR Evidence", value, ["name", "status"], as_dict=True)
	if not row:
		frappe.throw(_("La evidencia de cumplimiento no existe."))
	if row.status != "Validated":
		frappe.throw(_("La evidencia de cumplimiento debe estar validada."))
	return str(row.name)
