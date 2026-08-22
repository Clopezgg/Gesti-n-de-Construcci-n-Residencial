from __future__ import annotations

import frappe

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash

CENTRAL_REMITTANCE_KEY = "CENTRAL_REMITTANCE"
CENTRAL_REMITTANCE_NAME = "Cuenta Central de Remesas"


def ensure_central_remittance_account() -> str:
	existing = frappe.db.get_value("NXR Financial Account", {"technical_key": CENTRAL_REMITTANCE_KEY}, "name")
	if existing:
		return str(existing)
	account = {
		"doctype": "NXR Financial Account",
		"account_name": CENTRAL_REMITTANCE_NAME,
		"account_role": "Treasury",
		"technical_key": CENTRAL_REMITTANCE_KEY,
		"system_managed": 1,
		"active": 1,
		"project": None,
		"direction": "Origin",
		"origin_or_sender": "NEXORA",
		"institution": None,
		"account_reference": None,
		"currency": "HNL",
		"default_channel": "Remittance",
		"is_default": 1,
		"notes": "Cuenta lógica única para la tesorería central de remesas.",
		"account_fingerprint": canonical_payload_hash({"technical_key": CENTRAL_REMITTANCE_KEY}),
	}
	try:
		with service_write():
			return str(frappe.get_doc(account).insert(ignore_permissions=True).name)
	except frappe.DuplicateEntryError:
		existing = frappe.db.get_value(
			"NXR Financial Account", {"technical_key": CENTRAL_REMITTANCE_KEY}, "name"
		)
		if existing:
			return str(existing)
		raise


def central_source_names() -> tuple[str, ...]:
	rows = frappe.db.sql(
		"""
		SELECT source.name
		FROM `tabNXR Fund Source` source
		INNER JOIN `tabNXR Remittance` remittance ON remittance.name=source.remittance
		INNER JOIN `tabNXR Financial Account` account ON account.name=remittance.financial_account
		WHERE account.technical_key=%s
		ORDER BY source.name
		""",
		CENTRAL_REMITTANCE_KEY,
	)
	return tuple(str(row[0]) for row in rows)


def is_central_remittance_source(source: str) -> bool:
	if not source:
		return False
	return bool(
		frappe.db.sql(
			"""
			SELECT 1
			FROM `tabNXR Fund Source` source
			INNER JOIN `tabNXR Remittance` remittance ON remittance.name=source.remittance
			INNER JOIN `tabNXR Financial Account` account ON account.name=remittance.financial_account
			WHERE source.name=%s AND account.technical_key=%s
			LIMIT 1
			""",
			(source, CENTRAL_REMITTANCE_KEY),
		)
	)
