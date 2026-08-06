from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload
from nexora.intelligence import gateway as _gateway
from nexora.intelligence.config import (
	DEFAULT_PROVIDER_PRIORITY,
	DEFAULT_PROVIDER_STATUS,
	MAX_PROVIDERS_REGISTERED,
)
from nexora.intelligence.core import (
	IntelligenceError,
	ProviderRecord,
	parse_capabilities,
	validate_provider_key,
	validate_status,
)
from nexora.permissions import require_action

DOCTYPE = "NXR AI Provider"


def _provider_rows() -> list[dict[str, Any]]:
	return frappe.get_all(
		DOCTYPE,
		fields=["provider_key", "display_name", "status", "capabilities", "priority"],
	)


@frappe.whitelist(methods=["POST"])
def register_provider(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Registra un proveedor de IA en el Provider Manager.

	Solo persiste identidad, capacidades declaradas, prioridad y estado. No
	acepta ni almacena ninguna credencial: el Bloque 1 no conecta llaves de
	API (NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 7).
	"""

	data = parse_payload(payload)
	require_action("ai_manage_provider")

	record = ProviderRecord(
		provider_key=str(data.get("provider_key", "")),
		display_name=str(data.get("display_name", "")),
		status=str(data.get("status") or DEFAULT_PROVIDER_STATUS),
		capabilities=parse_capabilities(data.get("capabilities", "")),
		priority=data.get("priority", DEFAULT_PROVIDER_PRIORITY),
	)

	if frappe.db.exists(DOCTYPE, {"provider_key": record.provider_key}):
		frappe.throw(
			_("Ya existe un proveedor de IA registrado con esa clave."),
			frappe.DuplicateEntryError,
		)

	if frappe.db.count(DOCTYPE) >= MAX_PROVIDERS_REGISTERED:
		frappe.throw(_("Se alcanzó el límite de proveedores de IA configurables."))

	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)

	with service_write():
		provider = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"provider_key": record.provider_key,
				"display_name": record.display_name,
				"status": record.status,
				"capabilities": ",".join(record.capabilities),
				"priority": record.priority,
				"idempotency_key": data.get("idempotency_key"),
				"payload_hash": fingerprint,
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)

	audit(
		"ai_provider_registered",
		DOCTYPE,
		provider.name,
		fingerprint,
		correlation_id,
		{
			"provider_key": record.provider_key,
			"status": record.status,
			"capabilities": list(record.capabilities),
			"priority": record.priority,
		},
	)

	return {
		"provider": provider.name,
		"provider_key": record.provider_key,
		"status": record.status,
		"capabilities": list(record.capabilities),
	}


@frappe.whitelist(methods=["POST"])
def set_provider_status(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Activa, desactiva o marca en error un proveedor ya registrado.

	Nunca elimina el registro (Capítulo 50 de la Constitución: "nunca se
	elimina trazabilidad") y nunca toca ninguna credencial.
	"""

	data = parse_payload(payload)
	require_action("ai_manage_provider")

	provider_key = str(data.get("provider_key", ""))
	validate_provider_key(provider_key)
	status = validate_status(str(data.get("status", "")))

	name = frappe.db.get_value(DOCTYPE, {"provider_key": provider_key}, "name")
	if not name:
		frappe.throw(_("No existe un proveedor de IA con esa clave."), frappe.DoesNotExistError)

	provider = frappe.get_doc(DOCTYPE, name)
	previous_status = provider.status
	provider.status = status
	with service_write():
		provider.save(ignore_permissions=True)

	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	audit(
		"ai_provider_status_changed",
		DOCTYPE,
		provider.name,
		fingerprint,
		correlation_id,
		{"provider_key": provider_key, "previous_status": previous_status, "status": status},
	)

	return {"provider": provider.name, "provider_key": provider_key, "status": status}


@frappe.whitelist(methods=["POST"])
def list_providers(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Lista los proveedores configurados, sin exponer ninguna credencial.

	El Bloque 1 no persiste credenciales en este DocType, así que no hay nada
	que redactar; esta función existe igual como el punto único desde el que
	un módulo consulta el Provider Manager, en vez de leer el DocType
	directamente.
	"""

	parse_payload(payload)
	require_action("ai_view_provider")
	rows = _provider_rows()
	for row in rows:
		row["capabilities"] = list(parse_capabilities(row["capabilities"]))
	return rows


@frappe.whitelist(methods=["POST"])
def resolve_capability(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Resuelve, sin invocar a nadie, qué proveedor activo atendería una tarea.

	Esta es la superficie visible del AI Gateway en el Bloque 1: dado que
	ningún módulo de negocio conecta todavía con este subsistema, esta función
	no tiene consumidores en producción — su propósito es dejar demostrado y
	probado que la decisión de enrutamiento es correcta, determinista y no
	depende de ningún proveedor concreto, antes de que el Bloque 2 la use de
	verdad.
	"""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	capability = str(data.get("capability", ""))
	prefer = data.get("prefer")

	try:
		record = _gateway.resolve(_provider_rows(), capability, prefer=prefer)
	except IntelligenceError as exc:
		return {"resolved": False, "capability": capability, "reason": str(exc)}

	return {
		"resolved": True,
		"capability": capability,
		"provider_key": record.provider_key,
		"display_name": record.display_name,
	}
