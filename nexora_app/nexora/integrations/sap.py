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
