from __future__ import annotations

from frappe.model.document import Document

from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_immutable


class NXRAIUsageEvent(Document):
	"""Registro de uso, uno por intento del Orchestrator (Bloque 5.2).

	Inmutable, igual que ``NXR Audit Event`` — un registro de uso no se
	corrige, se complementa con el siguiente evento. Reutiliza
	``validate_immutable`` en vez de reimplementar la misma regla.
	"""

	def before_insert(self) -> None:
		require_service_write()

	def validate(self) -> None:
		validate_immutable(self, tuple(self.meta.get_valid_columns()))
