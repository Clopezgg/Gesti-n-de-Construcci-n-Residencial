from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload
from nexora.integrations.core import redact_credentials
from nexora.intelligence import gateway as _gateway
from nexora.intelligence.config import (
	DEFAULT_PROVIDER_PRIORITY,
	DEFAULT_PROVIDER_STATUS,
	MAX_PROVIDERS_REGISTERED,
)
from nexora.intelligence.core import (
	CredentialFormatError,
	IntelligenceError,
	ProviderRecord,
	parse_capabilities,
	validate_cost_hint,
	validate_default_model,
	validate_max_tokens,
	validate_provider_key,
	validate_status,
	validate_temperature,
	validate_timeout_seconds,
)
from nexora.intelligence.credentials import resolve_environment_credential, validate_credential_format
from nexora.permissions import require_action

DOCTYPE = "NXR AI Provider"
CREDENTIAL_DOCTYPE = "NXR AI Provider Credential"


def _provider_rows() -> list[dict[str, Any]]:
	return frappe.get_all(
		DOCTYPE,
		fields=[
			"provider_key",
			"display_name",
			"status",
			"capabilities",
			"priority",
			"is_default",
			"default_model",
			"timeout_seconds",
			"temperature",
			"max_tokens",
			"cost_hint",
			"validation_state",
			"last_validated_at",
		],
	)


def _require_existing_provider(provider_key: str) -> str:
	"""Devuelve el ``name`` (hash) del proveedor o lanza un error claro.

	Reutilizado por toda función del Bloque 3 que opera sobre un proveedor ya
	registrado — evita repetir la misma comprobación cuatro veces.
	"""

	name = frappe.db.get_value(DOCTYPE, {"provider_key": provider_key}, "name")
	if not name:
		frappe.throw(_("No existe un proveedor de IA con esa clave. Regístrelo primero."), frappe.DoesNotExistError)
	return name


def _redacted_payload_fingerprint(data: Mapping[str, Any]) -> str:
	"""Huella de un payload que puede incluir una credencial, sin depender de
	su contenido real.

	Reutiliza ``nexora.integrations.core.redact_credentials`` sobre un resumen
	``clave=valor`` del payload (NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección
	7: "redactar credenciales en cualquier log o evento de auditoría,
	reutilizando el patrón ya existente"). El resultado nunca deriva del
	secreto en texto plano — solo de la versión ya redactada.
	"""

	summary = " ".join(f"{key}={data[key]}" for key in sorted(data))
	return canonical_payload_hash({"redacted_summary": redact_credentials(summary)})


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


# --- Bloque 3: configuración operativa, proveedor por defecto y credenciales ---

_CONFIG_VALIDATORS = {
	"default_model": validate_default_model,
	"timeout_seconds": validate_timeout_seconds,
	"temperature": validate_temperature,
	"max_tokens": validate_max_tokens,
	"cost_hint": validate_cost_hint,
}


@frappe.whitelist(methods=["POST"])
def update_provider_config(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Actualiza los metadatos operativos de un proveedor ya registrado.

	Actualización parcial: solo cambian los campos presentes en el payload
	(``default_model``, ``timeout_seconds``, ``temperature``, ``max_tokens``,
	``cost_hint``); los ausentes conservan su valor actual. Nunca toca
	``status``, ``priority`` ni ninguna credencial — eso sigue siendo
	responsabilidad de ``set_provider_status`` (Bloque 1) y de
	``save_credential`` (más abajo), cada regla en su único lugar.
	"""

	data = parse_payload(payload)
	require_action("ai_manage_provider")

	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	name = _require_existing_provider(provider_key)

	updates: dict[str, Any] = {}
	for field, validator in _CONFIG_VALIDATORS.items():
		if field in data:
			updates[field] = validator(data[field])

	if not updates:
		frappe.throw(_("No se envió ningún campo de configuración para actualizar."))

	provider = frappe.get_doc(DOCTYPE, name)
	for field, value in updates.items():
		provider.set(field, value)
	with service_write():
		provider.save(ignore_permissions=True)

	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	audit(
		"ai_provider_config_updated",
		DOCTYPE,
		provider.name,
		fingerprint,
		correlation_id,
		{"provider_key": provider_key, **updates},
	)

	return {"provider": provider.name, "provider_key": provider_key, **updates}


@frappe.whitelist(methods=["POST"])
def set_default_provider(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Marca un proveedor como el de por defecto; desmarca a todos los demás.

	Preparado para que el Model Router de un bloque futuro lo consuma como
	criterio de enrutamiento — el Router de este bloque no lo usa todavía
	(NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 9: "preparar", no "usar").
	"""

	data = parse_payload(payload)
	require_action("ai_manage_provider")

	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	name = _require_existing_provider(provider_key)

	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)

	with service_write():
		frappe.db.set_value(DOCTYPE, {"is_default": 1}, "is_default", 0)
		frappe.db.set_value(DOCTYPE, name, "is_default", 1)

	audit(
		"ai_provider_default_changed",
		DOCTYPE,
		name,
		fingerprint,
		correlation_id,
		{"provider_key": provider_key},
	)

	return {"provider": name, "provider_key": provider_key, "is_default": True}


@frappe.whitelist(methods=["POST"])
def save_credential(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Guarda o reemplaza la credencial de un proveedor de forma segura.

	La credencial se cifra en reposo (fieldtype ``Password`` nativo de
	Frappe) en ``NXR AI Provider Credential`` — un DocType separado de
	``NXR AI Provider`` a propósito, para que el registro y la identidad de
	un proveedor nunca dependan de si tiene o no una credencial guardada. La
	validación es solo de formato (sección 8 de la arquitectura); nunca se
	llama al proveedor real. Ni el payload ni la respuesta de esta función
	contienen el valor de la credencial en ningún punto después de guardarla.
	"""

	data = parse_payload(payload)
	require_action("ai_manage_credential")

	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	provider_name = _require_existing_provider(provider_key)
	secret = data.get("secret", "")

	fingerprint = _redacted_payload_fingerprint(data)
	correlation_id = correlation(data)

	try:
		validate_credential_format(secret)
	except CredentialFormatError as exc:
		_set_provider_validation_state(provider_name, "Format Invalid")
		audit(
			"ai_provider_credential_rejected",
			DOCTYPE,
			provider_name,
			fingerprint,
			correlation_id,
			{"provider_key": provider_key, "reason": str(exc)},
		)
		frappe.throw(str(exc))

	existing_name = frappe.db.get_value(CREDENTIAL_DOCTYPE, {"provider_key": provider_key}, "name")
	with service_write():
		if existing_name:
			credential = frappe.get_doc(CREDENTIAL_DOCTYPE, existing_name)
			credential.secret = secret
			credential.payload_hash = fingerprint
			credential.correlation_id = correlation_id
			credential.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{
					"doctype": CREDENTIAL_DOCTYPE,
					"provider_key": provider_key,
					"secret": secret,
					"idempotency_key": data.get("idempotency_key"),
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)

	_set_provider_validation_state(provider_name, "Format Valid")

	audit(
		"ai_provider_credential_saved",
		DOCTYPE,
		provider_name,
		fingerprint,
		correlation_id,
		{"provider_key": provider_key, "credential_configured": True},
	)

	return {"provider_key": provider_key, "validation_state": "Format Valid"}


def _set_provider_validation_state(provider_name: str, state: str) -> None:
	with service_write():
		frappe.db.set_value(
			DOCTYPE,
			provider_name,
			{"validation_state": state, "last_validated_at": frappe.utils.now()},
		)


@frappe.whitelist(methods=["POST"])
def list_credential_status(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Estado de credencial por proveedor — nunca el valor de la credencial.

	Para cada proveedor registrado, indica de dónde vendría su credencial
	activa si se resolviera ahora (variable de entorno de servidor, primero;
	registro cifrado en base de datos, después; ninguna, si no hay nada
	configurado) y el resultado de la última validación de formato. Ninguna
	rama de esta función lee ni retorna el campo ``secret``.
	"""

	parse_payload(payload)
	require_action("ai_view_provider")

	rows = frappe.get_all(DOCTYPE, fields=["provider_key", "validation_state", "last_validated_at"])
	credentialed = set(
		frappe.get_all(CREDENTIAL_DOCTYPE, pluck="provider_key")
	)

	statuses: list[dict[str, Any]] = []
	for row in rows:
		provider_key = row["provider_key"]
		has_env_credential = resolve_environment_credential(provider_key) is not None
		has_db_credential = provider_key in credentialed
		if has_env_credential:
			source = "environment"
		elif has_db_credential:
			source = "database"
		else:
			source = "none"
		statuses.append(
			{
				"provider_key": provider_key,
				"has_credential": has_env_credential or has_db_credential,
				"source": source,
				"validation_state": row["validation_state"],
				"last_validated_at": row["last_validated_at"],
			}
		)
	return statuses
