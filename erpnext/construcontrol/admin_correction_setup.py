from __future__ import annotations

from typing import Any

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def _field(
	fieldname: str,
	label: str,
	fieldtype: str,
	*,
	insert_after: str,
	**values: Any,
) -> dict[str, Any]:
	return {
		"fieldname": fieldname,
		"label": label,
		"fieldtype": fieldtype,
		"insert_after": insert_after,
		**values,
	}


def ensure_admin_correction_fields() -> None:
	"""Install additive fields for the Administrator-only correction workflow."""
	definitions: dict[str, list[dict[str, Any]]] = {
		"ConstruControl Settings": [
			_field(
				"correction_security_section",
				"Autorización de correcciones críticas",
				"Section Break",
				insert_after="import_evidence_files",
				collapsible=1,
			),
			_field(
				"correction_access_enabled",
				"Acceso a correcciones críticas",
				"Check",
				insert_after="correction_security_section",
				default="0",
			),
			_field(
				"correction_pin_hash",
				"Huella de la clave de corrección",
				"Small Text",
				insert_after="correction_access_enabled",
				hidden=1,
				read_only=1,
				no_copy=1,
			),
			_field(
				"correction_pin_updated_at",
				"Clave actualizada",
				"Datetime",
				insert_after="correction_pin_hash",
				read_only=1,
			),
			_field(
				"correction_last_used_at",
				"Último uso autorizado",
				"Datetime",
				insert_after="correction_pin_updated_at",
				read_only=1,
			),
			_field(
				"correction_failed_attempts",
				"Intentos fallidos",
				"Int",
				insert_after="correction_last_used_at",
				default="0",
				read_only=1,
			),
			_field(
				"correction_locked_until",
				"Bloqueado hasta",
				"Datetime",
				insert_after="correction_failed_attempts",
				read_only=1,
			),
		],
		"CC Expense Control": [
			_field(
				"admin_correction_section",
				"Trazabilidad de corrección administrativa",
				"Section Break",
				insert_after="notes",
				collapsible=1,
			),
			_field(
				"last_admin_correction_id",
				"Última autorización",
				"Data",
				insert_after="admin_correction_section",
				read_only=1,
				no_copy=1,
			),
			_field(
				"last_admin_correction_at",
				"Fecha de corrección",
				"Datetime",
				insert_after="last_admin_correction_id",
				read_only=1,
				no_copy=1,
			),
			_field(
				"last_admin_correction_reason",
				"Motivo de corrección",
				"Small Text",
				insert_after="last_admin_correction_at",
				read_only=1,
				no_copy=1,
			),
			_field(
				"last_admin_correction_evidence",
				"Evidencia de corrección",
				"Attach",
				insert_after="last_admin_correction_reason",
				read_only=1,
				no_copy=1,
			),
		],
		"Supplier": [
			_field(
				"cc_supplier_correction_section",
				"Consolidación ConstruControl",
				"Section Break",
				insert_after="disabled",
				collapsible=1,
			),
			_field(
				"cc_normalized_name",
				"Nombre normalizado ConstruControl",
				"Data",
				insert_after="cc_supplier_correction_section",
				hidden=1,
				read_only=1,
			),
			_field(
				"cc_merged_into",
				"Proveedor oficial",
				"Link",
				insert_after="cc_normalized_name",
				options="Supplier",
				read_only=1,
			),
			_field(
				"cc_archived_duplicate",
				"Archivado como duplicado",
				"Check",
				insert_after="cc_merged_into",
				default="0",
				read_only=1,
			),
			_field(
				"cc_aliases_json",
				"Alias históricos",
				"Code",
				insert_after="cc_archived_duplicate",
				options="JSON",
				read_only=1,
			),
		],
		"User": [
			_field(
				"cc_user_correction_section",
				"Archivo administrativo ConstruControl",
				"Section Break",
				insert_after="enabled",
				collapsible=1,
			),
			_field(
				"cc_archived_by_correction",
				"Archivado por corrección",
				"Check",
				insert_after="cc_user_correction_section",
				default="0",
				read_only=1,
			),
			_field(
				"cc_replacement_user",
				"Cuenta sustituta",
				"Link",
				insert_after="cc_archived_by_correction",
				options="User",
				read_only=1,
			),
			_field(
				"cc_correction_note",
				"Motivo de archivo",
				"Small Text",
				insert_after="cc_replacement_user",
				read_only=1,
			),
		],
	}
	create_custom_fields(definitions, update=True)
	for doctype in definitions:
		frappe.clear_cache(doctype=doctype)
	print("[ConstruControl] Administrator correction fields installed", flush=True)


__all__ = ["ensure_admin_correction_fields"]
