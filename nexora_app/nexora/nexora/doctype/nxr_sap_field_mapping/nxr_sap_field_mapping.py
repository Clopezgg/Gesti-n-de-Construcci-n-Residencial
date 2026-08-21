from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write

#: Cambiar cualquiera de estos campos es un cambio sustantivo del mapeo real
#: — sube la versión. `active`/`correlation_id` son metadatos, no la
#: definición del mapeo en sí.
_VERSIONED_FIELDS = (
	"nexora_object",
	"sap_object",
	"source_field",
	"target_field",
	"transformation",
	"required",
)


class NXRSAPFieldMapping(Document):
	def before_insert(self) -> None:
		require_service_write()
		self.version = 1

	def before_save(self) -> None:
		require_service_write()
		if not self.is_new() and self.has_value_changed_any(_VERSIONED_FIELDS):
			self.version = (self.version or 1) + 1

	def has_value_changed_any(self, fieldnames) -> bool:
		previous = self.get_doc_before_save()
		if not previous:
			return False
		return any(self.get(field) != previous.get(field) for field in fieldnames)

	def on_trash(self) -> None:
		frappe.throw(
			_(
				"Los mapeos SAP no se eliminan; desactive el mapeo en vez de borrarlo, para conservar su historial."
			)
		)
