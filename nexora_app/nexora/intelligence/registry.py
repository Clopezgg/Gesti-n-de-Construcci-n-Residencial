from __future__ import annotations

from collections.abc import Iterable

from nexora.intelligence.core import ProviderNotFoundError, ProviderRecord


class ProviderRegistry:
	"""Registro en memoria de proveedores de IA configurados.

	Es la vista de ejecución de lo que persiste el DocType ``NXR AI
	Provider``. No hace I/O ni conoce Frappe: ``nexora.intelligence.gateway``
	es quien la reconstruye a partir de filas ya leídas de la base de datos en
	cada solicitud, igual que ``financial/core.py`` no toca la base de datos y
	``financial/db.py`` es quien la alimenta.
	"""

	def __init__(self, records: Iterable[ProviderRecord] = ()) -> None:
		self._records: dict[str, ProviderRecord] = {}
		for record in records:
			self.register(record)

	def register(self, record: ProviderRecord) -> None:
		self._records[record.provider_key] = record

	def unregister(self, provider_key: str) -> None:
		self._records.pop(provider_key, None)

	def get(self, provider_key: str) -> ProviderRecord:
		try:
			return self._records[provider_key]
		except KeyError:
			raise ProviderNotFoundError(f"Proveedor no registrado: {provider_key!r}.") from None

	def __contains__(self, provider_key: str) -> bool:
		return provider_key in self._records

	def __len__(self) -> int:
		return len(self._records)

	def list_all(self) -> tuple[ProviderRecord, ...]:
		return tuple(self._records.values())

	def list_active(self) -> tuple[ProviderRecord, ...]:
		return tuple(record for record in self._records.values() if record.is_active)

	def list_by_capability(self, capability: str, *, active_only: bool = True) -> tuple[ProviderRecord, ...]:
		records = self.list_active() if active_only else self.list_all()
		return tuple(record for record in records if record.supports(capability))
