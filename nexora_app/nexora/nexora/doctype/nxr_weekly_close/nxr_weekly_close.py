from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRWeeklyClose(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()
		if not self.is_new():
			frappe.throw(_("Los cierres semanales son inmutables. Registre una corrección compensatoria."))

	def validate(self) -> None:
		if frappe.utils.getdate(self.week_end) < frappe.utils.getdate(self.week_start):
			frappe.throw(_("La semana termina antes de su fecha inicial."))
		number = str(self.document_number or "")
		if len(number) != 12 or not number.isdigit():
			frappe.throw(_("El cierre semanal requiere un número numérico único de 12 dígitos."))
		for fieldname in ("period_key", "payload_hash", "snapshot_hash", "correlation_id", "engine_version"):
			if not str(getattr(self, fieldname, "") or "").strip():
				frappe.throw(_("El cierre semanal no contiene su trazabilidad completa."))
		try:
			payload = json.loads(self.snapshot_json or "{}")
		except (TypeError, ValueError):
			frappe.throw(_("La fotografía del cierre semanal no es JSON válido."))
		if not isinstance(payload, dict) or not payload.get("totals"):
			frappe.throw(_("La fotografía del cierre semanal no contiene totales canónicos."))
		if self.status == "Correction" and (
			not self.correction_of or len(str(self.correction_reason or "").strip()) < 10
		):
			frappe.throw(_("Una corrección requiere cierre original y motivo de al menos 10 caracteres."))

	def on_trash(self) -> None:
		frappe.throw(_("Los cierres semanales NEXORA no se eliminan."))
