from __future__ import annotations

from typing import Any

import frappe

from nexora.intelligence import gateway as _gateway
from nexora.intelligence.core import AIProviderAdapter, ProviderNotFoundError
from nexora.intelligence.credentials import resolve_environment_credential
from nexora.intelligence.runtime_core import check_readiness, prepare_adapter

__all__ = [
	"resolve_active_credential",
	"provider_row",
	"build_ready_adapter",
	"build_ready_adapter_for_capability",
	"provider_readiness",
]

DOCTYPE = "NXR AI Provider"
CREDENTIAL_DOCTYPE = "NXR AI Provider Credential"

_ROW_FIELDS = (
	"provider_key",
	"status",
	"capabilities",
	"default_model",
	"timeout_seconds",
	"temperature",
	"max_tokens",
)


def resolve_active_credential(provider_key: str) -> str | None:
	"""Orden de resolución obligatorio (Bloque 3, sección 8 de la
	arquitectura): variable de entorno de servidor primero; si no hay,
	registro cifrado en ``NXR AI Provider Credential``. Nunca se registra ni
	se imprime el valor devuelto — solo se pasa a ``prepare_adapter``, que lo
	entrega al constructor del adaptador y a nada más.
	"""

	env_value = resolve_environment_credential(provider_key)
	if env_value:
		return env_value

	name = frappe.db.get_value(CREDENTIAL_DOCTYPE, {"provider_key": provider_key}, "name")
	if not name:
		return None
	return frappe.get_doc(CREDENTIAL_DOCTYPE, name).get_password("secret")


def provider_row(provider_key: str) -> dict[str, Any]:
	row = frappe.db.get_value(DOCTYPE, {"provider_key": provider_key}, list(_ROW_FIELDS), as_dict=True)
	if not row:
		raise ProviderNotFoundError(f"No existe un proveedor de IA con clave {provider_key!r}.")
	return dict(row)


def build_ready_adapter(provider_key: str, *, capability: str | None = None) -> AIProviderAdapter:
	"""Resuelve proveedor, configuración, credencial y disponibilidad, y
	devuelve un adaptador en vivo listo para invocarse.

	Toda la validación real vive en ``runtime_core.prepare_adapter`` (pura);
	esta función solo hace la lectura de Frappe que esa validación necesita —
	exactamente la separación core/service que ya usan
	``financial/core.py`` + ``financial/db.py`` y
	``intelligence/core.py`` + ``intelligence/service.py``.
	"""

	row = provider_row(provider_key)
	secret = resolve_active_credential(provider_key)
	return prepare_adapter(row, secret, capability=capability)


def build_ready_adapter_for_capability(capability: str, *, prefer: str | None = None) -> AIProviderAdapter:
	"""Elige el proveedor por prioridad (reutiliza el Router del Bloque 1) y
	construye su adaptador en vivo. No duplica la lógica de resolución de
	prioridad: ``_gateway.resolve`` es exactamente la misma función que usa
	``intelligence.service.resolve_capability`` desde el Bloque 1.
	"""

	rows = frappe.get_all(
		DOCTYPE,
		fields=["provider_key", "display_name", "status", "capabilities", "priority"],
	)
	record = _gateway.resolve(rows, capability, prefer=prefer)
	return build_ready_adapter(record.provider_key, capability=capability)


def provider_readiness(provider_key: str, *, capability: str | None = None) -> dict[str, Any]:
	"""Versión de solo lectura de ``build_ready_adapter``: nunca lanza,
	nunca construye nada — reporta si el proveedor está listo y por qué no,
	si no lo está. Reutiliza ``runtime_core.check_readiness`` (pura)."""

	row = provider_row(provider_key)
	secret = resolve_active_credential(provider_key)
	return check_readiness(row, secret, capability=capability)
