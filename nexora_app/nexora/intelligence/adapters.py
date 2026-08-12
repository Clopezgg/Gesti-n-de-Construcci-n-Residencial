from __future__ import annotations

from collections.abc import Iterable

from nexora.intelligence.core import AIProviderAdapter, ProviderNotFoundError

_ADAPTER_CLASSES: dict[str, type[AIProviderAdapter]] = {}


def register_adapter(cls: type[AIProviderAdapter]) -> type[AIProviderAdapter]:
	"""Decorador: da de alta una clase de adaptador por su ``provider_key``.

	Añadir un proveedor nuevo es escribir un archivo en ``providers/`` con
	esta anotación e importarlo desde ``providers/__init__.py``; ni el
	Gateway, ni el Router, ni el Provider Manager cambian una sola línea
	(NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 3 — "extensible sin romper
	lo existente"). El registro ocurre una sola vez, al importar el módulo
	del adaptador — no hay descubrimiento mágico de archivos.
	"""

	key = getattr(cls, "provider_key", "")
	if not key:
		raise ValueError(f"{cls.__name__} debe declarar 'provider_key' antes de registrarse.")
	existing = _ADAPTER_CLASSES.get(key)
	if existing is not None and existing is not cls:
		raise ValueError(
			f"La clave de adaptador {key!r} ya está registrada por {existing.__name__}; "
			f"{cls.__name__} no puede reutilizarla."
		)
	_ADAPTER_CLASSES[key] = cls
	return cls


def known_adapter_keys() -> tuple[str, ...]:
	"""Claves de adaptador registradas hasta el momento de la llamada.

	Depende de qué módulos de ``providers/`` ya se hayan importado; por eso
	``build_default_registry`` importa el paquete completo antes de leer esto.
	"""

	return tuple(sorted(_ADAPTER_CLASSES))


class AdapterRegistry:
	"""Registro en memoria de instancias de adaptador, indexadas por ``provider_key``.

	Distinto del ``ProviderRegistry`` del Bloque 1: aquel guarda
	*configuración* (``ProviderRecord``, sin código); este guarda *código
	ejecutable* (instancias de ``AIProviderAdapter``). El Gateway combina
	ambos: primero resuelve qué proveedor está activo y configurado (Bloque
	1), luego busca si existe un adaptador de código para ejecutarlo (Bloque
	2). Puede haber un ``ProviderRecord`` activo sin adaptador de código
	todavía — es una situación válida, no un error de configuración.
	"""

	def __init__(self, instances: Iterable[AIProviderAdapter] = ()) -> None:
		self._adapters: dict[str, AIProviderAdapter] = {}
		for instance in instances:
			self.register(instance)

	def register(self, instance: AIProviderAdapter) -> None:
		self._adapters[instance.provider_key] = instance

	def get(self, provider_key: str) -> AIProviderAdapter:
		try:
			return self._adapters[provider_key]
		except KeyError:
			raise ProviderNotFoundError(f"No hay adaptador de código para {provider_key!r}.") from None

	def __contains__(self, provider_key: str) -> bool:
		return provider_key in self._adapters

	def __len__(self) -> int:
		return len(self._adapters)

	def list_all(self) -> tuple[AIProviderAdapter, ...]:
		return tuple(self._adapters.values())


def build_default_registry() -> AdapterRegistry:
	"""Instancia un adaptador de cada clase registrada en ``providers/``.

	Importa ``nexora.intelligence.providers`` primero para asegurar que todos
	los adaptadores conocidos ya se hayan registrado. En el Bloque 2 esto
	produce siempre los tres adaptadores simulados (OpenAI, Anthropic,
	Gemini); un bloque futuro que añada un cuarto adaptador no toca esta
	función.
	"""

	from nexora.intelligence import providers as _providers

	return AdapterRegistry(cls() for cls in _ADAPTER_CLASSES.values())
