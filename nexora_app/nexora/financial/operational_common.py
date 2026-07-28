from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.operational_dates import OperationalDateError, month_key, validate_document_date

MOVEMENT_CATALOG: dict[str, dict[str, str]] = {
	"101": {"label": "Entrada de saldo", "mode": "income", "operation_code": "", "economic_category": ""},
	"102": {
		"label": "Salida de saldo / gasto",
		"mode": "expense",
		"operation_code": "CONSTRUCTION_PAYMENT",
		"economic_category": "",
	},
	"303": {
		"label": "Anulación financiera",
		"mode": "correction",
		"operation_code": "REVERSAL_NO_CASH",
		"economic_category": "REVERSAL",
	},
	"304": {
		"label": "Corrección documental",
		"mode": "correction",
		"operation_code": "DOCUMENT_SUBSTITUTION",
		"economic_category": "DOCUMENTARY",
	},
	"501": {
		"label": "Cancelación total",
		"mode": "correction",
		"operation_code": "REVERSAL_NO_CASH",
		"economic_category": "REVERSAL",
	},
}
CHANNEL_LABELS = {
	"Remittance": "Remesa",
	"Cash": "Efectivo",
	"Deposit": "Depósito",
	"Transfer": "Transferencia",
	"Other": "Otro",
}
DAY_LABELS = ("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")
BANK_CHANNELS = {"Remittance", "Deposit", "Transfer"}


def _required(value: object, message: str) -> str:
	text = str(value or "").strip()
	if not text:
		frappe.throw(_(message))
	return text


def _masked_account(value: object) -> str:
	text = str(value or "").strip()
	if not text:
		return "—"
	visible = text[-5:] if len(text) > 5 else text
	return f"••••{visible}"


def _normalize_channel(value: object) -> str:
	channel = str(value or "Other").strip()
	if channel not in CHANNEL_LABELS:
		frappe.throw(_("El canal financiero no es válido."))
	return channel


def _closed_month(project: str, document_date: Any) -> str | None:
	key = month_key(document_date)
	rows = frappe.get_all(
		"NXR Monthly Close",
		filters={"project": project, "status": "Approved"},
		fields=["name", "close_month", "close_date"],
		limit_page_length=500,
	)
	for row in rows:
		if str(row.get("close_month") or "").strip() == key:
			return str(row.get("name"))
		if row.get("close_date") and frappe.utils.getdate(row.get("close_date")).strftime("%Y-%m") == key:
			return str(row.get("name"))
	return None


def _document_date(data: Mapping[str, Any], *, reference_name: str = "") -> str:
	project = _required(data.get("project"), "Seleccione un proyecto.")
	reference_date = None
	if reference_name:
		reference_date = frappe.db.get_value("NXR Operation", reference_name, "operation_date")
		if not reference_date:
			frappe.throw(_("El documento original no existe."))
	try:
		value = validate_document_date(
			data.get("document_date") or data.get("operation_date") or data.get("source_date"),
			today=frappe.utils.getdate(frappe.utils.today()),
			reference_date=reference_date,
		)
	except OperationalDateError as exc:
		frappe.throw(_(str(exc)))
	closed = _closed_month(project, value)
	if closed:
		frappe.throw(
			_(
				"El período {0} está cerrado por el documento {1}. Reabra o corrija el cierre antes de registrar."
			).format(month_key(value), closed)
		)
	return value.isoformat()
