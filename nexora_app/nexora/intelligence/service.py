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
from nexora.intelligence import orchestrator as _orchestrator
from nexora.intelligence import runtime as _runtime
from nexora.intelligence.core import (
	AllProvidersExhaustedError,
	CredentialFormatError,
	IntelligenceError,
	ProviderRecord,
	ProviderRequest,
	parse_capabilities,
	validate_cost_hint,
	validate_default_model,
	validate_max_tokens,
	validate_priority,
	validate_provider_key,
	validate_status,
	validate_temperature,
	validate_timeout_seconds,
)
from nexora.intelligence.credentials import resolve_environment_credential, validate_credential_format
from nexora.intelligence.orchestrator_core import HealthState, rank_candidates
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
			"circuit_state",
			"consecutive_failures",
			"degraded_until",
			"last_outcome_at",
			"last_error_kind",
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
	"priority": validate_priority,  # Bloque 5.2: el panel también necesita reordenar prioridad.
}


@frappe.whitelist(methods=["POST"])
def update_provider_config(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Actualiza los metadatos operativos de un proveedor ya registrado.

	Actualización parcial: solo cambian los campos presentes en el payload
	(``default_model``, ``timeout_seconds``, ``temperature``, ``max_tokens``,
	``cost_hint``, ``priority``); los ausentes conservan su valor actual.
	Nunca toca ``status`` ni ninguna credencial — eso sigue siendo
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


# --- Bloque 4: runtime de proveedores — endpoints administrativos ---------

@frappe.whitelist(methods=["POST"])
def check_provider_readiness(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Informa si un proveedor está listo para usarse — cubre "validar
	proveedor" y "consultar disponibilidad" del Bloque 4: son la misma
	comprobación vista desde dos preguntas distintas, así que se resuelven
	con una sola función en vez de duplicar la lógica (Capítulo 44).

	No construye nada, no toca la red, nunca devuelve la credencial — solo
	reporta si hay una y de dónde vendría.
	"""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	capability = data.get("capability") or None
	return _runtime.provider_readiness(provider_key, capability=capability)


@frappe.whitelist(methods=["POST"])
def get_provider_runtime_config(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Configuración operativa de un proveedor — nunca su credencial."""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	row = _runtime.provider_row(provider_key)
	row["capabilities"] = list(parse_capabilities(row["capabilities"]))
	return row


@frappe.whitelist(methods=["POST"])
def list_active_providers(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Proveedores con ``status = Active`` y una credencial resuelta —
	subconjunto de ``list_providers`` (Bloque 1, sin tocar) que sí importa
	para saber qué se puede usar hoy, no solo qué está registrado."""

	parse_payload(payload)
	require_action("ai_view_provider")
	active: list[dict[str, Any]] = []
	for row in _provider_rows():
		if row["status"] != "Active":
			continue
		readiness = _runtime.provider_readiness(row["provider_key"])
		if readiness["ready"]:
			row["capabilities"] = list(parse_capabilities(row["capabilities"]))
			active.append(row)
	return active


@frappe.whitelist(methods=["POST"])
def get_provider_capabilities(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Capacidades declaradas de un proveedor, o de todos si no se indica uno."""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	provider_key = data.get("provider_key")
	if provider_key:
		row = _runtime.provider_row(validate_provider_key(str(provider_key)))
		return {row["provider_key"]: list(parse_capabilities(row["capabilities"]))}
	return {row["provider_key"]: list(parse_capabilities(row["capabilities"])) for row in _provider_rows()}


@frappe.whitelist(methods=["POST"])
def test_provider_connection(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Prueba de conexión real contra un proveedor ya configurado.

	Construye el adaptador en vivo (Bloque 4) y le envía una solicitud
	mínima. Si el proveedor no tiene credencial, modelo o capacidad
	configurados, falla antes de tocar la red — ``prepare_adapter`` ya lo
	garantiza. Nunca devuelve la credencial; el resultado solo informa éxito
	o el motivo del fallo. Queda auditado porque, a diferencia del resto de
	funciones de este archivo, sí tiene un efecto real fuera de NEXORA
	(contacta al proveedor y puede consumir cuota).
	"""

	data = parse_payload(payload)
	require_action("ai_test_connection")
	provider_key = validate_provider_key(str(data.get("provider_key", "")))
	correlation_id = correlation(data)
	fingerprint = canonical_payload_hash({"provider_key": provider_key})

	try:
		adapter = _runtime.build_ready_adapter(provider_key, capability="text")
		ping = ProviderRequest(capability="text", payload={"prompt": "ping"}, correlation_id=correlation_id)
		adapter.invoke(ping)
	except IntelligenceError as exc:
		audit(
			"ai_provider_connection_tested",
			DOCTYPE,
			_require_existing_provider(provider_key),
			fingerprint,
			correlation_id,
			{"provider_key": provider_key, "success": False, "reason": str(exc)},
		)
		return {"provider_key": provider_key, "success": False, "reason": str(exc)}

	audit(
		"ai_provider_connection_tested",
		DOCTYPE,
		_require_existing_provider(provider_key),
		fingerprint,
		correlation_id,
		{"provider_key": provider_key, "success": True},
	)
	return {"provider_key": provider_key, "success": True}


# --- Bloque 5.2: Orchestrator, fallback automático y panel de administración ---

@frappe.whitelist(methods=["POST"])
def run_orchestrated_request(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Punto de entrada administrativo a la "regla de oro": intenta, en
	orden, cada proveedor sano y capaz hasta obtener éxito o agotarlos.

	Es la única función de este archivo que puede terminar contactando a
	*varios* proveedores reales en una sola llamada — por eso comparte la
	acción más estricta con ``test_provider_connection`` en vez de una nueva:
	el riesgo (red real, cuota real) es el mismo tipo, solo que aquí puede
	repetirse varias veces dentro de la misma solicitud. Nunca devuelve
	ninguna credencial; solo el resultado final y, si falló todo, con qué
	proveedores se intentó y por qué.
	"""

	data = parse_payload(payload)
	require_action("ai_test_connection")
	capability = str(data.get("capability", "text"))
	prompt = str(data.get("prompt", "ping"))
	prefer = data.get("prefer")
	correlation_id = correlation(data)

	try:
		response = _orchestrator.execute(
			capability,
			{"prompt": prompt},
			correlation_id,
			prefer=prefer,
		)
	except AllProvidersExhaustedError as exc:
		return {
			"success": False,
			"capability": capability,
			"reason": str(exc),
			"attempts": list(exc.attempts),
		}
	except IntelligenceError as exc:
		return {"success": False, "capability": capability, "reason": str(exc), "attempts": []}

	return {
		"success": True,
		"capability": capability,
		"provider_key": response.provider_key,
	}


@frappe.whitelist(methods=["POST"])
def preview_routing_decision(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Muestra qué proveedor se usaría ahora mismo para una capacidad, sin
	invocar a nadie — la vista del panel para "qué proveedor se usará por
	defecto para cada tipo de tarea" (Bloque 5.2). A diferencia de
	``resolve_capability`` (Bloque 1, que solo mira prioridad y capacidad),
	esta usa el mismo ranking consciente de salud que el Orchestrator
	(``orchestrator_core.rank_candidates``) — puede dar una respuesta
	distinta si un proveedor de mayor prioridad está degradado.
	"""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	capability = str(data.get("capability", ""))
	prefer = data.get("prefer")

	rows = _provider_rows()
	registry = _gateway.build_registry(rows)
	healths = {
		row["provider_key"]: HealthState(
			circuit_state=row.get("circuit_state") or "Closed",
			consecutive_failures=row.get("consecutive_failures") or 0,
			degraded_until=row.get("degraded_until"),
		)
		for row in rows
	}
	ranked = rank_candidates(
		registry.list_by_capability(capability), healths, now=frappe.utils.now_datetime(), prefer=prefer
	)
	if not ranked:
		return {"capability": capability, "resolved": False, "reason": "Ningún proveedor sano disponible."}

	chosen = ranked[0]
	return {
		"capability": capability,
		"resolved": True,
		"provider_key": chosen.provider_key,
		"display_name": chosen.display_name,
		"alternatives": [r.provider_key for r in ranked[1:]],
	}


@frappe.whitelist(methods=["POST"])
def get_provider_usage_summary(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	"""Latencia, éxito y costo reportado por proveedor — lo que el panel
	necesita para "ver latencia" y "ver costo estimado" (Bloque 5.2).

	Se agrega en Python sobre los últimos eventos, no con SQL a medida, para
	no introducir una consulta nueva que mantener por separado; el volumen
	esperado (eventos de uso del propio panel y del Orchestrator) no
	justifica más que esto todavía.
	"""

	data = parse_payload(payload)
	require_action("ai_view_provider")
	limit = min(max(int(data.get("limit", 200)), 1), 1000)

	events = frappe.get_all(
		"NXR AI Usage Event",
		fields=["provider_key", "success", "latency_ms", "reported_cost"],
		order_by="creation desc",
		limit_page_length=limit,
	)

	by_provider: dict[str, dict[str, Any]] = {}
	for event in events:
		bucket = by_provider.setdefault(
			event["provider_key"],
			{"provider_key": event["provider_key"], "samples": 0, "successes": 0, "latencies": [], "total_cost": 0.0},
		)
		bucket["samples"] += 1
		bucket["successes"] += 1 if event["success"] else 0
		if event["latency_ms"] is not None:
			bucket["latencies"].append(event["latency_ms"])
		if event["reported_cost"]:
			bucket["total_cost"] += event["reported_cost"]

	summary = []
	for bucket in by_provider.values():
		latencies = bucket.pop("latencies")
		summary.append(
			{
				**bucket,
				"avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
				"success_rate": round(bucket["successes"] / bucket["samples"], 3) if bucket["samples"] else None,
			}
		)
	return summary
