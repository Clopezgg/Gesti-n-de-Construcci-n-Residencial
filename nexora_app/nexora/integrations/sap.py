"""Adaptador real de integración con SAP.

SAP es un sistema externo, nunca la identidad de NEXORA (ver
``docs/nexora/ARQUITECTURA.md``, sección «Integraciones externas»). Este
módulo no asume ninguna variante concreta de SAP (OData, RFC, BAPI), ningún
endpoint ni ningún tenant por defecto: todo eso vive en ``NXR SAP
Connection``, configurado por quien administra el entorno. El adaptador solo
aporta lo que es responsabilidad de NEXORA — transporte HTTP con reintento
acotado, las tres formas reales de autenticación (Basic/OAuth Client
Credentials/Token estático), idempotencia, auditoría y manejo de errores —
nunca la asignación de campos de un documento SAP concreto, que corresponde
a quien llama a ``submit_document`` con el ``endpoint_path`` y el
``document_payload`` ya mapeados.

**Advertencia de implementación honesta:** este entorno no tiene acceso a un
sistema SAP real ni a credenciales SAP. El transporte, la autenticación, la
idempotencia y el manejo de errores se probaron con HTTP simulado
(``unittest.mock``); ninguna llamada real contra SAP se ha ejecutado. Una
conexión SAP concreta solo puede declararse IMPLEMENTADA Y VALIDADA después
de que ``test_sap_connection``/``submit_document`` se ejecuten contra un
sistema SAP autorizado real — antes de eso, cualquier resultado que esta
sesión reporte como "verde" se limita a la lógica de transporte, no a la
integración productiva con SAP.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	parse_payload,
	start_idempotency,
)
from nexora.integrations.core import redact_credentials, validate_endpoint
from nexora.integrations.sap_core import (
	RETRYABLE_HTTP_STATUS,
	basic_auth_header,
	build_url,
	oauth_cache_ttl_seconds,
)
from nexora.permissions import require_action

CONNECTION_DOCTYPE = "NXR SAP Connection"
_OAUTH_TOKEN_CACHE_PREFIX = "nexora:sap:oauth_token:"
_OAUTH_TOKEN_SAFETY_MARGIN_SECONDS = 30


class SapIntegrationError(Exception):
	pass


def _redacted_fingerprint(data: Mapping[str, Any]) -> str:
	summary = " ".join(f"{key}={value}" for key, value in sorted(data.items()))
	return canonical_payload_hash({"redacted": redact_credentials(summary)})


def _connection_doc(name: str) -> Any:
	if not frappe.db.exists(CONNECTION_DOCTYPE, name):
		frappe.throw(_("La conexión SAP indicada no existe."))
	return frappe.get_doc(CONNECTION_DOCTYPE, name)


def _active_connection(name: str) -> Any:
	"""Documento de conexión con los secretos aún encriptados (no resueltos):
	las tres rutas de autenticación resuelven cada una el secreto que
	necesitan, nunca todos a la vez, para que ningún secreto que la conexión
	no use pase por memoria sin motivo."""

	doc = _connection_doc(name)
	if doc.status != "Active":
		frappe.throw(_("La conexión SAP «{0}» está inactiva.").format(doc.connection_name))
	return doc


def _urlopen_json(request: urllib.request.Request, timeout_seconds: int) -> tuple[int, dict[str, Any]]:
	with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
		raw = response.read().decode("utf-8") or "{}"
		try:
			return response.status, json.loads(raw)
		except json.JSONDecodeError:
			return response.status, {"raw": raw}


def _open_sap_request(
	request: urllib.request.Request, *, timeout_seconds: int, action_label: str
) -> tuple[int, dict[str, Any]]:
	"""Un único reintento inmediato ante un error transitorio — mismo criterio
	que ``conversation.channels.whatsapp._open_graph_request``: nunca para
	errores de autenticación (401/403), solicitud mal formada (400/404) o
	cualquier otro 4xx que no cambia al repetir la misma llamada; sí para
	timeouts, fallos de conexión y los códigos 5xx/429/408 que un sistema SAP
	puede devolver de forma pasajera. ``request`` es seguro de reenviar:
	``urllib`` no lo consume al fallar."""

	try:
		return _urlopen_json(request, timeout_seconds)
	except urllib.error.HTTPError as exc:
		if exc.code not in RETRYABLE_HTTP_STATUS:
			detail = exc.read().decode("utf-8", errors="replace")[:300]
			raise SapIntegrationError(f"SAP respondió HTTP {exc.code} {action_label}: {detail}") from exc
	except urllib.error.URLError:
		pass

	try:
		return _urlopen_json(request, timeout_seconds)
	except urllib.error.HTTPError as exc:
		detail = exc.read().decode("utf-8", errors="replace")[:300]
		raise SapIntegrationError(f"SAP respondió HTTP {exc.code} {action_label}: {detail}") from exc
	except urllib.error.URLError as exc:
		raise SapIntegrationError(f"No se pudo conectar con SAP: {exc.reason}") from exc


def _fetch_oauth_token(doc: Any) -> str:
	"""Client Credentials Grant real (RFC 6749 §4.4) contra ``token_url``.

	Nunca fabrica un token: si SAP/el servidor de autorización no responde
	con ``access_token``, la llamada falla con ``SapIntegrationError`` en vez
	de continuar con una cadena vacía."""

	client_id = doc.client_id
	client_secret = doc.get_password("client_secret")
	if not doc.token_url or not client_id or not client_secret:
		frappe.throw(_("Faltan datos de OAuth (token_url, client_id o client_secret) en la conexión SAP."))
	body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}".encode()
	request = urllib.request.Request(
		doc.token_url,
		data=body,
		headers={"Content-Type": "application/x-www-form-urlencoded"},
		method="POST",
	)
	_status, payload = _open_sap_request(request, timeout_seconds=30, action_label="al pedir el token OAuth")
	access_token = payload.get("access_token")
	if not access_token:
		raise SapIntegrationError("El servidor de autorización de SAP no devolvió access_token.")
	expires_in = int(payload.get("expires_in") or 0)
	ttl_seconds = oauth_cache_ttl_seconds(
		expires_in, safety_margin_seconds=_OAUTH_TOKEN_SAFETY_MARGIN_SECONDS
	)
	if ttl_seconds is not None:
		frappe.cache().set_value(
			f"{_OAUTH_TOKEN_CACHE_PREFIX}{doc.name}",
			access_token,
			expires_in_sec=ttl_seconds,
		)
	return str(access_token)


def _oauth_token(doc: Any) -> str:
	cached = frappe.cache().get_value(f"{_OAUTH_TOKEN_CACHE_PREFIX}{doc.name}")
	if cached:
		return cached.decode("utf-8") if isinstance(cached, bytes) else str(cached)
	return _fetch_oauth_token(doc)


def _auth_headers(doc: Any) -> dict[str, str]:
	if doc.auth_type == "Basic":
		if not doc.username or not doc.get_password("password"):
			frappe.throw(_("Faltan usuario o contraseña en la conexión SAP para autenticación Basic."))
		return {"Authorization": basic_auth_header(doc.username, doc.get_password("password"))}
	if doc.auth_type == "OAuth Client Credentials":
		return {"Authorization": f"Bearer {_oauth_token(doc)}"}
	if doc.auth_type == "Static Token":
		token = doc.get_password("static_token")
		if not token:
			frappe.throw(_("Falta el token estático en la conexión SAP."))
		return {"Authorization": f"Bearer {token}"}
	frappe.throw(_("Tipo de autenticación SAP no reconocido: {0}.").format(doc.auth_type))


def _append_log(
	doc: Any, *, level: str, message: str, request_preview: str = "", response_preview: str = ""
) -> None:
	doc.append(
		"logs",
		{
			"timestamp": frappe.utils.now(),
			"level": level,
			"message": message,
			"request_preview": redact_credentials(request_preview)[:500],
			"response_preview": redact_credentials(response_preview)[:500],
		},
	)


@frappe.whitelist(methods=["POST"])
def connect_connection(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Guarda o reemplaza una conexión SAP — nunca la prueba contra SAP aquí
	(eso es ``test_sap_connection``, una acción explícita y separada, mismo
	principio que ``conversation.channels.whatsapp.connect_credential`` vs.
	``test_channel_connection``)."""

	data = parse_payload(payload)
	require_action("manage_sap_connection")
	connection_name = str(data.get("connection_name") or "").strip()
	base_url = str(data.get("base_url") or "").strip()
	auth_type = str(data.get("auth_type") or "").strip()
	if not connection_name or not base_url or not auth_type:
		frappe.throw(_("Faltan campos obligatorios: nombre de conexión, URL base y tipo de autenticación."))
	validate_endpoint(base_url)

	secret_fields = {
		"Basic": ("username", "password"),
		"OAuth Client Credentials": ("token_url", "client_id", "client_secret"),
		"Static Token": ("static_token",),
	}.get(auth_type)
	if secret_fields is None:
		frappe.throw(_("Tipo de autenticación SAP no reconocido: {0}.").format(auth_type))

	fingerprint = _redacted_fingerprint({"connection_name": connection_name, "auth_type": auth_type})
	correlation_id = correlation(data)
	existing_name = frappe.db.get_value(CONNECTION_DOCTYPE, {"connection_name": connection_name}, "name")
	with service_write():
		if existing_name:
			doc = frappe.get_doc(CONNECTION_DOCTYPE, existing_name)
			doc.base_url = base_url
			doc.auth_type = auth_type
			doc.default_document_endpoint = data.get("default_document_endpoint")
			for field in secret_fields:
				if data.get(field):
					doc.set(field, data[field])
			doc.status = "Inactive"
			doc.payload_hash = fingerprint
			doc.correlation_id = correlation_id
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc(
				{
					"doctype": CONNECTION_DOCTYPE,
					"connection_name": connection_name,
					"base_url": base_url,
					"auth_type": auth_type,
					"default_document_endpoint": data.get("default_document_endpoint"),
					"status": "Inactive",
					**{field: data.get(field) for field in secret_fields},
					"connected_by": frappe.session.user,
					"connected_at": frappe.utils.now_datetime(),
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
	audit(
		"sap_connection_saved",
		CONNECTION_DOCTYPE,
		doc.name,
		fingerprint,
		correlation_id,
		{"connection_name": connection_name, "auth_type": auth_type, "status": doc.status},
	)
	return {"connection": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def test_sap_connection(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	"""Prueba real: intenta una solicitud HTTP autenticada real contra
	``base_url`` (más ``default_document_endpoint`` si está configurado).
	Nunca escribe ``"Success"`` sin haber llamado a nadie — distingue
	explícitamente entre «no se pudo alcanzar el servidor» y «se alcanzó pero
	SAP rechazó la autenticación», que son hallazgos distintos y ambos
	reales."""

	data = parse_payload(payload or {})
	require_action("manage_sap_connection")
	correlation_id = correlation(data)
	connection_name = str(data.get("connection") or "").strip()
	if not connection_name:
		frappe.throw(_("Seleccione la conexión SAP que desea probar."))
	doc = _connection_doc(connection_name)
	url = build_url(doc.base_url, doc.default_document_endpoint)
	try:
		headers = _auth_headers(doc)
		request = urllib.request.Request(url, headers=headers, method="GET")
		status_code, response_payload = _open_sap_request(
			request, timeout_seconds=30, action_label="al probar la conexión"
		)
		result_value = "Success"
		detail = _("SAP respondió HTTP {0}.").format(status_code)
		response_preview = json.dumps(response_payload, ensure_ascii=False)[:500]
	except SapIntegrationError as exc:
		result_value = "Failure"
		detail = str(exc)
		response_preview = ""
	with service_write():
		doc.last_test_at = frappe.utils.now()
		doc.last_test_result = result_value
		_append_log(
			doc,
			level="Info" if result_value == "Success" else "Error",
			message=detail,
			request_preview=url,
			response_preview=response_preview,
		)
		if result_value == "Success":
			doc.status = "Active"
		doc.save(ignore_permissions=True)
	result = {"connection": doc.name, "last_test_result": result_value, "detail": detail}
	audit(
		"sap_connection_tested",
		CONNECTION_DOCTYPE,
		doc.name,
		canonical_payload_hash({"url": url, "result": result_value}),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def submit_document(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Envía un documento ya mapeado a SAP con idempotencia real.

	El llamador decide ``document_type``, ``endpoint_path`` y
	``document_payload``: este adaptador nunca asume el contrato de negocio
	de un documento SAP concreto (ver docstring del módulo). Reutiliza el
	mismo mecanismo de idempotencia que cualquier operación financiera
	(``NXR Idempotency Record``): la misma clave con el mismo payload
	devuelve la respuesta ya obtenida en vez de reenviar el documento a SAP
	una segunda vez.

	Un rechazo de SAP se trata como una respuesta completada (``ok: False``),
	no como una excepción sin resolver: si se lanzara y dejara el registro de
	idempotencia en ``Processing`` para siempre (como ocurría en una versión
	anterior de este mismo módulo), la misma clave quedaría permanentemente
	incapaz de reintentarse — ``La misma solicitud ya está en procesamiento``
	sin que ninguna solicitud siguiera en curso. Solo un error del propio
	NEXORA (payload incompleto, conexión inexistente o inactiva) se lanza de
	verdad, porque ese caso nunca llegó a pedir nada a SAP y no tiene sentido
	completarlo como intento."""

	data = parse_payload(payload)
	require_action("submit_sap_document")
	connection_name = str(data.get("connection") or "").strip()
	document_type = str(data.get("document_type") or "").strip()
	document_payload = data.get("document_payload")
	idempotency_key = str(data.get("idempotency_key") or "").strip()
	if not connection_name or not document_type or not isinstance(document_payload, Mapping):
		frappe.throw(_("Faltan campos obligatorios: conexión, tipo de documento y payload del documento."))

	doc = _active_connection(connection_name)
	endpoint_path = str(data.get("endpoint_path") or doc.default_document_endpoint or "").strip()
	if not endpoint_path:
		frappe.throw(_("Indique la ruta del documento en SAP (endpoint_path) o configure una por defecto."))

	correlation_id = correlation(data)
	fingerprint = canonical_payload_hash(
		{"connection": connection_name, "document_type": document_type, "document_payload": document_payload}
	)
	record, cached_response = start_idempotency(idempotency_key, fingerprint, correlation_id)
	if cached_response is not None:
		return cached_response

	url = build_url(doc.base_url, endpoint_path)
	try:
		headers = _auth_headers(doc)
		headers["Content-Type"] = "application/json"
		body = json.dumps(document_payload).encode("utf-8")
		request = urllib.request.Request(url, data=body, headers=headers, method="POST")
		status_code, response_payload = _open_sap_request(
			request, timeout_seconds=60, action_label="al enviar el documento"
		)
	except SapIntegrationError as exc:
		result = {
			"connection": doc.name,
			"document_type": document_type,
			"ok": False,
			"error": str(exc),
		}
		with service_write():
			_append_log(doc, level="Error", message=str(exc), request_preview=url)
			doc.save(ignore_permissions=True)
		complete_idempotency(record, CONNECTION_DOCTYPE, doc.name, result)
		audit(
			"sap_document_submission_failed",
			CONNECTION_DOCTYPE,
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		return result

	result = {
		"connection": doc.name,
		"document_type": document_type,
		"ok": True,
		"sap_status_code": status_code,
		"sap_response": response_payload,
	}
	with service_write():
		_append_log(
			doc,
			level="Info",
			message=_("Documento {0} enviado a SAP.").format(document_type),
			request_preview=url,
			response_preview=json.dumps(response_payload, ensure_ascii=False)[:500],
		)
		doc.save(ignore_permissions=True)
	complete_idempotency(record, CONNECTION_DOCTYPE, doc.name, result)
	audit(
		"sap_document_submitted",
		CONNECTION_DOCTYPE,
		doc.name,
		fingerprint,
		correlation_id,
		{"document_type": document_type, "sap_status_code": status_code},
	)
	return result


@frappe.whitelist(methods=["POST"])
def list_connections(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	data = parse_payload(payload or {})
	require_action("view_sap_connection")
	filters = {}
	if data.get("status"):
		filters["status"] = data["status"]
	connections = frappe.get_all(
		CONNECTION_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"connection_name",
			"status",
			"base_url",
			"auth_type",
			"last_test_at",
			"last_test_result",
		],
		limit=data.get("limit", 50),
	)
	return list(connections)


MAPPING_DOCTYPE = "NXR SAP Field Mapping"
INBOUND_DOCTYPE = "NXR SAP Inbound Record"
_DOCUMENT_EVENT_TYPES = ("sap_document_submitted", "sap_document_submission_failed")
_MAPPING_EVENT_TYPES = ("sap_mapping_saved", "sap_mapping_deactivated")
_SYNC_EVENT_TYPES = ("sap_document_pulled", "sap_document_pull_failed")
_ALL_EVENT_TYPES = (
	"sap_connection_saved",
	"sap_connection_tested",
	*_DOCUMENT_EVENT_TYPES,
	*_MAPPING_EVENT_TYPES,
	*_SYNC_EVENT_TYPES,
)


@frappe.whitelist(methods=["GET"])
def get_sap_summary() -> dict[str, Any]:
	"""Agregados reales para la pestaña «Resumen» de la superficie SAP —
	ningún dato inventado: cuenta conexiones reales por estado y eventos
	reales de ``NXR Audit Event`` (la misma bitácora que ``connect_connection``/
	``test_sap_connection``/``submit_document`` ya escriben)."""
	require_action("view_sap_connection")
	connections_by_status: dict[str, int] = {}
	for row in frappe.get_all(CONNECTION_DOCTYPE, fields=["status"]):
		status = row["status"] or "Inactive"
		connections_by_status[status] = connections_by_status.get(status, 0) + 1
	total_connections = sum(connections_by_status.values())
	last_tested = frappe.db.get_value(
		CONNECTION_DOCTYPE, filters={}, fieldname="last_test_at", order_by="last_test_at desc"
	)
	documents_submitted = frappe.db.count(
		"NXR Audit Event",
		filters={"reference_doctype": CONNECTION_DOCTYPE, "event_type": "sap_document_submitted"},
	)
	documents_failed = frappe.db.count(
		"NXR Audit Event",
		filters={"reference_doctype": CONNECTION_DOCTYPE, "event_type": "sap_document_submission_failed"},
	)
	last_document_event = frappe.db.get_value(
		"NXR Audit Event",
		filters={"reference_doctype": CONNECTION_DOCTYPE, "event_type": ["in", _DOCUMENT_EVENT_TYPES]},
		fieldname="creation",
		order_by="creation desc",
	)
	return {
		"total_connections": total_connections,
		"connections_by_status": connections_by_status,
		"last_tested_at": last_tested,
		"documents_submitted": documents_submitted,
		"documents_failed": documents_failed,
		"last_document_event_at": last_document_event,
	}


@frappe.whitelist(methods=["POST"])
def list_sap_events(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	"""Bitácora real de ``NXR Audit Event`` acotada a SAP (``reference_doctype``
	en ``NXR SAP Connection``/``NXR SAP Field Mapping``), reutilizada por
	cuatro pestañas de la superficie SAP: «Documentos» (sin filtro, o solo los
	dos tipos de evento de envío), «Errores» (solo
	``sap_document_submission_failed``), «Mapeos» (eventos de mapeo) y
	«Auditoría» (cualquier tipo de evento real de este módulo, incluidas
	conexiones guardadas/probadas y mapeos). El propio parámetro
	``event_types`` decide el filtro;
	nunca se inventa un evento que la bitácora real no tenga."""
	data = parse_payload(payload or {})
	require_action("view_sap_connection")
	requested_types = data.get("event_types")
	if requested_types:
		event_types = [t for t in requested_types if t in _ALL_EVENT_TYPES]
	else:
		event_types = list(_ALL_EVENT_TYPES)
	rows = frappe.get_all(
		"NXR Audit Event",
		filters={
			"reference_doctype": ["in", [CONNECTION_DOCTYPE, MAPPING_DOCTYPE]],
			"event_type": ["in", event_types],
		},
		fields=["name", "event_type", "actor", "reference_name", "correlation_id", "after_json", "creation"],
		order_by="creation desc",
		limit=data.get("limit", 100),
	)
	events = []
	for row in rows:
		try:
			after = json.loads(row["after_json"]) if row["after_json"] else {}
		except json.JSONDecodeError:
			after = {}
		events.append(
			{
				"name": row["name"],
				"event_type": row["event_type"],
				"actor": row["actor"],
				"connection": row["reference_name"],
				"correlation_id": row["correlation_id"],
				"detail": after,
				"timestamp": row["creation"],
			}
		)
	return events


def _mapping_snapshot(doc: Any) -> dict[str, Any]:
	return {
		"mapping": doc.name,
		"connection": doc.connection,
		"nexora_object": doc.nexora_object,
		"sap_object": doc.sap_object,
		"source_field": doc.source_field,
		"target_field": doc.target_field,
		"transformation": doc.transformation,
		"required": bool(doc.required),
		"active": bool(doc.active),
		"version": doc.version,
	}


@frappe.whitelist(methods=["POST"])
def create_field_mapping(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Capa de mapeo real (objeto NEXORA → objeto SAP, campo por campo).

	Guardar un mapeo nunca envía nada a SAP ni implica que la conexión esté
	sincronizando — es configuración pura, igual que ``connect_connection``
	nunca prueba la conexión que guarda. ``submit_document`` sigue recibiendo
	el payload ya mapeado de quien lo llama (ver el docstring del módulo);
	este catálogo es la fuente de verdad que documenta y gobierna esos
	mapeos, no una capa de transformación automática nueva."""
	data = parse_payload(payload)
	require_action("manage_sap_connection")
	connection = str(data.get("connection") or "").strip()
	nexora_object = str(data.get("nexora_object") or "").strip()
	sap_object = str(data.get("sap_object") or "").strip()
	source_field = str(data.get("source_field") or "").strip()
	target_field = str(data.get("target_field") or "").strip()
	if not connection or not nexora_object or not sap_object or not source_field or not target_field:
		frappe.throw(
			_("El mapeo requiere conexión, objeto NEXORA, objeto SAP, campo origen y campo destino.")
		)
	if not frappe.db.exists(CONNECTION_DOCTYPE, connection):
		frappe.throw(_("La conexión SAP indicada no existe."))
	correlation_id = correlation(data)
	with service_write():
		doc = frappe.get_doc(
			{
				"doctype": MAPPING_DOCTYPE,
				"connection": connection,
				"nexora_object": nexora_object,
				"sap_object": sap_object,
				"source_field": source_field,
				"target_field": target_field,
				"transformation": data.get("transformation"),
				"required": 1 if data.get("required") else 0,
				"active": 1,
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)
	result = _mapping_snapshot(doc)
	audit(
		"sap_mapping_saved",
		MAPPING_DOCTYPE,
		doc.name,
		canonical_payload_hash(result),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def update_field_mapping(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("manage_sap_connection")
	mapping = str(data.get("mapping") or "").strip()
	if not mapping:
		frappe.throw(_("Falta indicar qué mapeo actualizar."))
	doc = frappe.get_doc(MAPPING_DOCTYPE, mapping)
	correlation_id = correlation(data)
	with service_write():
		for fieldname in ("nexora_object", "sap_object", "source_field", "target_field", "transformation"):
			if fieldname in data:
				doc.set(fieldname, data.get(fieldname))
		if "required" in data:
			doc.required = 1 if data.get("required") else 0
		doc.correlation_id = correlation_id
		doc.save(ignore_permissions=True)
	result = _mapping_snapshot(doc)
	audit(
		"sap_mapping_saved",
		MAPPING_DOCTYPE,
		doc.name,
		canonical_payload_hash(result),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def deactivate_field_mapping(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Desactiva un mapeo sin borrarlo — mismo principio que las conexiones
	SAP: `on_trash` de ambos DocTypes rechaza el borrado, para conservar el
	historial real de qué se mapeó y cuándo dejó de aplicarse."""
	data = parse_payload(payload)
	require_action("manage_sap_connection")
	mapping = str(data.get("mapping") or "").strip()
	if not mapping:
		frappe.throw(_("Falta indicar qué mapeo desactivar."))
	doc = frappe.get_doc(MAPPING_DOCTYPE, mapping)
	correlation_id = correlation(data)
	with service_write():
		doc.active = 0
		doc.correlation_id = correlation_id
		doc.save(ignore_permissions=True)
	result = _mapping_snapshot(doc)
	audit(
		"sap_mapping_deactivated",
		MAPPING_DOCTYPE,
		doc.name,
		canonical_payload_hash(result),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def list_field_mappings(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	data = parse_payload(payload or {})
	require_action("view_sap_connection")
	filters = {}
	if data.get("connection"):
		filters["connection"] = data["connection"]
	if "active" in data:
		filters["active"] = 1 if data.get("active") else 0
	rows = frappe.get_all(
		MAPPING_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"connection",
			"nexora_object",
			"sap_object",
			"source_field",
			"target_field",
			"transformation",
			"required",
			"active",
			"version",
		],
		order_by="modified desc",
		limit=data.get("limit", 100),
	)
	return list(rows)


def _inbound_snapshot(doc: Any) -> dict[str, Any]:
	return {
		"inbound_record": doc.name,
		"connection": doc.connection,
		"sap_object": doc.sap_object,
		"external_id": doc.external_id,
		"status": doc.status,
		"last_synced_at": doc.last_synced_at,
	}


@frappe.whitelist(methods=["POST"])
def pull_document(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""SAP → NEXORA: trae un documento real desde SAP y lo aterriza en
	``NXR SAP Inbound Record`` — nunca directamente sobre un DocType de
	negocio de NEXORA. Escribir automáticamente sobre un registro financiero
	real a partir de datos externos sin validar violaría el mismo principio
	de libro inmutable que protege el resto del sistema (ver
	``test_safe_archive_contract.py``); promover un registro entrante a un
	documento real de NEXORA es una decisión humana explícita y separada,
	fuera del alcance de este adaptador.

	Identificación real por (``connection``, ``sap_object``, ``external_id``):
	la misma combinación nunca crea un segundo registro. Si el contenido
	traído es idéntico al último guardado, se marca ``Duplicate``; si cambió,
	``Updated`` — detección de cambios real, comparando el payload anterior
	con el nuevo, nunca asumida."""

	data = parse_payload(payload)
	require_action("sync_sap_document")
	connection_name = str(data.get("connection") or "").strip()
	sap_object = str(data.get("sap_object") or "").strip()
	external_id = str(data.get("external_id") or "").strip()
	endpoint_path = str(data.get("endpoint_path") or "").strip()
	if not connection_name or not sap_object or not external_id or not endpoint_path:
		frappe.throw(
			_("Faltan campos obligatorios: conexión, objeto SAP, identificador externo y ruta del documento.")
		)

	doc = _active_connection(connection_name)
	correlation_id = correlation(data)
	fingerprint = canonical_payload_hash(
		{"connection": connection_name, "sap_object": sap_object, "external_id": external_id}
	)
	idempotency_key = str(data.get("idempotency_key") or "").strip()
	if not idempotency_key:
		frappe.throw(_("Falta la clave de idempotencia para consultar el documento."))
	record, cached_response = start_idempotency(idempotency_key, fingerprint, correlation_id)
	if cached_response is not None:
		return cached_response

	url = build_url(doc.base_url, endpoint_path)
	try:
		headers = _auth_headers(doc)
		request = urllib.request.Request(url, headers=headers, method="GET")
		status_code, response_payload = _open_sap_request(
			request, timeout_seconds=30, action_label="al consultar el documento"
		)
	except SapIntegrationError as exc:
		result = {
			"connection": doc.name,
			"sap_object": sap_object,
			"external_id": external_id,
			"ok": False,
			"error": str(exc),
		}
		complete_idempotency(record, CONNECTION_DOCTYPE, doc.name, result)
		audit(
			"sap_document_pull_failed",
			CONNECTION_DOCTYPE,
			doc.name,
			fingerprint,
			correlation_id,
			result,
		)
		return result

	new_payload_json = json.dumps(response_payload, ensure_ascii=False, sort_keys=True)
	existing_name = frappe.db.get_value(
		INBOUND_DOCTYPE,
		{"connection": connection_name, "sap_object": sap_object, "external_id": external_id},
		"name",
	)
	with service_write():
		if existing_name:
			inbound = frappe.get_doc(INBOUND_DOCTYPE, existing_name)
			previous_payload_json = inbound.payload_json
			inbound.status = "Duplicate" if previous_payload_json == new_payload_json else "Updated"
			inbound.payload_json = new_payload_json
			inbound.correlation_id = correlation_id
			inbound.last_synced_at = frappe.utils.now()
			inbound.save(ignore_permissions=True)
		else:
			inbound = frappe.get_doc(
				{
					"doctype": INBOUND_DOCTYPE,
					"connection": connection_name,
					"sap_object": sap_object,
					"external_id": external_id,
					"status": "Received",
					"payload_json": new_payload_json,
					"correlation_id": correlation_id,
					"last_synced_at": frappe.utils.now(),
				}
			).insert(ignore_permissions=True)

	result = {
		"connection": doc.name,
		"sap_object": sap_object,
		"external_id": external_id,
		"ok": True,
		"sap_status_code": status_code,
		**_inbound_snapshot(inbound),
	}
	complete_idempotency(record, CONNECTION_DOCTYPE, doc.name, result)
	audit(
		"sap_document_pulled",
		CONNECTION_DOCTYPE,
		doc.name,
		fingerprint,
		correlation_id,
		{"sap_object": sap_object, "external_id": external_id, "status": inbound.status},
	)
	return result


@frappe.whitelist(methods=["POST"])
def list_inbound_records(payload: str | Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
	data = parse_payload(payload or {})
	require_action("view_sap_connection")
	filters = {}
	if data.get("connection"):
		filters["connection"] = data["connection"]
	if data.get("status"):
		filters["status"] = data["status"]
	rows = frappe.get_all(
		INBOUND_DOCTYPE,
		filters=filters,
		fields=["name", "connection", "sap_object", "external_id", "status", "last_synced_at"],
		order_by="modified desc",
		limit=data.get("limit", 100),
	)
	return list(rows)
