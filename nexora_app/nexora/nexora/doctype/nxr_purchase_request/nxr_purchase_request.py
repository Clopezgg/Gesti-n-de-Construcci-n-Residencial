from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number
from nexora.purchases.request_core import (
	PURCHASE_PRIORITIES,
	PURCHASE_REQUEST_TRANSITIONS,
	PurchaseValidationError,
	assert_request_transition,
	money,
	request_line_amounts,
	validate_request_dates,
)

LINE_FIELDS = (
	"line_code",
	"item_type",
	"catalog_item",
	"description",
	"quantity",
	"uom",
	"estimated_unit_rate",
	"estimated_amount",
	"economic_category",
	"cost_center",
	"required_by",
	"notes",
)


def _line_snapshot(rows: Iterable[Any]) -> list[dict[str, Any]]:
	return [{field: row.get(field) for field in LINE_FIELDS} for row in rows]


class NXRPurchaseRequest(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_document_number(self.document_number)
		try:
			validate_request_dates(self.request_date, self.required_by)
			if self.priority not in PURCHASE_PRIORITIES:
				raise PurchaseValidationError("La prioridad de compra no está permitida.")
			amounts = request_line_amounts(row.as_dict() for row in self.lines)
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if money(self.total_amount) != amounts.total:
			frappe.throw(_("El total de la solicitud no coincide con sus líneas."))
		if self.status not in PURCHASE_REQUEST_TRANSITIONS:
			frappe.throw(_("Estado de solicitud de compra desconocido."))
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		try:
			assert_request_transition(str(previous.status), str(self.status))
		except PurchaseValidationError as exc:
			frappe.throw(_(str(exc)))
		if previous.status != "Draft":
			protected = (
				"request_date",
				"required_by",
				"project",
				"cost_center",
				"fund_source",
				"requested_by",
				"responsible",
				"priority",
				"currency",
				"justification",
				"total_amount",
				"evidence",
			)
			if any(self.get(field) != previous.get(field) for field in protected):
				frappe.throw(_("La solicitud fuera de borrador no admite cambios de contenido."))
			if _line_snapshot(self.lines) != _line_snapshot(previous.lines):
				frappe.throw(_("Las líneas de la solicitud fuera de borrador son inmutables."))

	def on_trash(self) -> None:
		frappe.throw(_("Las solicitudes de compra no se eliminan."))
