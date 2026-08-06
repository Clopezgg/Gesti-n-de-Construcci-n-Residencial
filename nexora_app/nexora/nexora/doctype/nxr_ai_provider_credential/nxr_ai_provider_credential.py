from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nexora.financial.context import require_service_write


class NXRAIProviderCredential(Document):
	def before_insert(self) -> None:
		require_service_write()

	def before_save(self) -> None:
		require_service_write()

	def validate(self) -> None:
		# ``require_service_write()`` (antes de escribir en cualquier caso) ya
		# garantiza que solo ``nexora.intelligence.service.save_credential``
		# puede llegar aquí, y esa función ya valida el formato de la
		# credencial contra ``nexora.intelligence.credentials`` antes de
		# construir el documento. Repetirlo aquí sería la misma regla en dos
		# lugares (Capítulo 44) sin ganar ninguna cobertura adicional.
		pass

	def on_trash(self) -> None:
		frappe.throw(
			_("Las credenciales de IA no se eliminan; guarde un valor nuevo para reemplazarlas.")
		)
