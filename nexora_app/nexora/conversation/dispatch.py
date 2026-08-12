"""Motor de despacho conversacional (Bloque 18, NXR-CNV-0001).

Único punto de entrada whitelisted del módulo. No reimplementa ninguna regla
de negocio: interpreta texto, rellena campos, y cuando una intención está
completa invoca la función real ya auditada del dominio
(``frappe.get_attr(dotted_path)(payload)`` — el mismo mecanismo que
``hooks.py:override_whitelisted_methods`` ya usa para redirigir rutas).

Flujo (idéntico al descrito en ``docs/nexora/NIP_BLOQUE_6_CONVERSATIONAL_OS.md``,
adaptado a lo que realmente existe hoy): ingesta → interpretación (NLU real vía
``nexora.intelligence.orchestrator``) → relleno de campos → resolución de
referencias humanas → permiso (la propia función real lo aplica; este módulo
no mantiene una segunda tabla de permisos) → vista previa obligatoria para
escritura → confirmación explícita → ejecución → auditoría.
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from nexora.conversation import db, nlu, resolve
from nexora.conversation.core import IntentKind, format_money_hnl, merge_payload, missing_slots, next_question
from nexora.conversation.registry import REGISTRY
from nexora.financial.db import audit, correlation, parse_payload
from nexora.permissions import require_action


_ASSISTANT_ACTION = "view_reports"


def _require_assistant_access() -> None:
	require_action(_ASSISTANT_ACTION)


_INTERNAL_EXECUTION_ERROR = "Ocurrió un error interno al ejecutar. Intenta de nuevo o contacta soporte."


_title = "NEXORA conversation intent execution failed"


def _required(data: dict[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _response(state: str, message: str, data: dict[str, Any] | None) -> dict[str, Any]:
	return {"state": state, "message": message, "data": data}


def _recent_history(conversation: str, limit: int = 6) -> list[dict[str, str]]:
	rows = frappe.get_all(
		"NXR Conversation Message",
		filters={"conversation": conversation},
		fields=["direction", "content"],
		order_by="creation desc",
		limit=limit,
	)
	rows.reverse()
	return [
		{"role": "user" if row["direction"] == "Inbound" else "assistant", "content": row["content"]}
		for row in rows
	]


def _assert_owns_conversation(conversation: str) -> None:
	owner = frappe.db.get_value("NXR Conversation", conversation, "user")
	if owner != frappe.session.user:
		frappe.throw(_("No tienes acceso a esta conversación."), frappe.PermissionError)


class UnresolvedReferenceError(Exception):
	"""Un texto humano (proyecto, contratista) no coincide con ningún registro real."""


def _resolve_references(spec, payload: dict[str, Any]) -> dict[str, Any]:
	resolved = dict(payload)
	if resolved.get("project"):
		found = resolve.resolve_project(str(resolved["project"]))
		if found is None:
			raise UnresolvedReferenceError(
				f"No encontré ningún proyecto que coincida con «{resolved['project']}»."
			)
		resolved["project"] = found
	if spec.key == "query_contract" and resolved.get("contractor"):
		found = resolve.resolve_entity(str(resolved["contractor"]))
		if found is None:
			raise UnresolvedReferenceError(
				f"No encontré ningún contratista o proveedor que coincida con «{resolved['contractor']}»."
			)
		resolved["contractor"] = found
	return resolved


def _ambiguous_message(candidates: list[dict[str, Any]]) -> str:
	labels = [
		str(row.get("project_name") or row.get("display_name") or row.get("name")) for row in candidates
	]
	return "Encontré más de una coincidencia: " + "; ".join(labels) + ". ¿A cuál te refieres exactamente?"


# ---------------------------------------------------------------------------
# Lecturas: cada rama traduce los slots genéricos a los parámetros reales de
# la función que ya existe — nunca calcula el dato ella misma.
# ---------------------------------------------------------------------------


def _invoke_read(spec, payload: dict[str, Any]) -> Any:
	fn = frappe.get_attr(spec.read_method)
	if spec.key == "query_fund_balance":
		return fn(payload["project"])
	if spec.key == "query_pending_payments":
		snapshot = fn({"project": payload["project"]})
		return {"pending_accounts": snapshot.get("pending_accounts") or []}
	if spec.key == "query_contract":
		kwargs: dict[str, Any] = {"contractor": payload.get("contractor")}
		if payload.get("project"):
			kwargs["project"] = payload["project"]
		return fn(**kwargs)
	raise ValueError(f"Intención de lectura sin manejador declarado: {spec.key}")


def _format_read_reply(intent_key: str, data: Any) -> str:
	if intent_key == "query_fund_balance":
		rows = data or []
		if not rows:
			return "Este proyecto no tiene fuentes de fondos activas registradas."
		parts = [f"{row['source']}: disponible {format_money_hnl(row.get('available_hnl'))}" for row in rows]
		return "Saldo por fuente — " + "; ".join(parts) + "."
	if intent_key == "query_pending_payments":
		pending = data.get("pending_accounts") or []
		if not pending:
			return "No hay pagos pendientes registrados para este proyecto."
		parts = [
			f"{row.get('label', row.get('name'))}: {format_money_hnl(row.get('amount_hnl'))}"
			for row in pending[:10]
		]
		return f"Tienes {len(pending)} pago(s) pendiente(s): " + "; ".join(parts) + "."
	if intent_key == "query_contract":
		rows = data or []
		if not rows:
			return "No encontré contratos que coincidan con esa búsqueda."
		parts = [f"{row.get('document_number', row.get('name'))} ({row.get('status')})" for row in rows[:10]]
		return f"Encontré {len(rows)} contrato(s): " + "; ".join(parts) + "."
	return "Consulta realizada."


# ---------------------------------------------------------------------------
# Escritura: preview obligatorio + confirmación explícita antes de ejecutar.
# ---------------------------------------------------------------------------


def _build_write_payload(
	intent_key: str,
	payload: dict[str, Any],
	correlation_id: str,
	*,
	idempotency_key: str | None = None,
	preview_hash: str | None = None,
) -> dict[str, Any]:
	call = dict(payload)
	call["correlation_id"] = correlation_id
	if intent_key == "register_expense":
		call["movement_code"] = "102"
	elif intent_key == "register_income":
		call["movement_code"] = "101"
	if idempotency_key:
		call["idempotency_key"] = idempotency_key
	if preview_hash:
		call["preview_hash"] = preview_hash
	return call


def _format_preview_reply(intent_key: str, payload: dict[str, Any]) -> str:
	amount = format_money_hnl(payload.get("amount_hnl")) if payload.get("amount_hnl") else None
	if intent_key == "register_expense":
		return (
			f"Voy a registrar un gasto de {amount} a favor de {payload.get('beneficiary')} "
			f"en el proyecto {payload.get('project')}. ¿Confirmas?"
		)
	if intent_key == "register_income":
		return (
			f"Voy a registrar un ingreso de {amount} de parte de {payload.get('beneficiary')} "
			f"en el proyecto {payload.get('project')}. ¿Confirmas?"
		)
	if intent_key == "register_evidence":
		return f"Voy a guardar esta evidencia ({payload.get('evidence_kind')}) en el proyecto {payload.get('project')}. ¿Confirmas?"
	return "¿Confirmas esta operación?"


def _run_write_preview(
	conversation: str, spec, payload: dict[str, Any], correlation_id: str, open_name: str | None
) -> dict[str, Any]:
	call_payload = _build_write_payload(spec.key, payload, correlation_id)
	try:
		if spec.preview_method:
			preview = frappe.get_attr(spec.preview_method)(call_payload)
		else:
			preview = dict(call_payload)
	except frappe.PermissionError:
		reply = "No tienes permiso para preparar esta operación."
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=spec.key)
		if open_name:
			db.update_pending_intent(open_name, status="Cancelled")
		return _response("Failed", reply, None)
	except frappe.exceptions.ValidationError as exc:
		# El servidor rechazó algo que nuestros slots mínimos no capturaron —
		# se traduce su propio mensaje en la siguiente pregunta, en vez de
		# reimplementar la validación aquí.
		reply = str(exc)
		if open_name:
			db.update_pending_intent(open_name, payload=payload, status="Collecting")
		else:
			record = db.create_pending_intent(
				conversation, spec.key, payload, correlation_id=correlation_id, missing=[]
			)
			open_name = record["name"]
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=spec.key)
		return _response("Collecting", reply, {"name": open_name})

	idempotency_key = frappe.generate_hash(length=20)
	preview_hash = str(preview.get("preview_hash") or preview.get("financial_preview_hash") or "")
	if open_name:
		record = db.update_pending_intent(
			open_name,
			payload=payload,
			missing=[],
			preview=preview,
			preview_hash=preview_hash,
			idempotency_key=idempotency_key,
			status="AwaitingConfirmation",
		)
	else:
		record = db.create_pending_intent(
			conversation, spec.key, payload, correlation_id=correlation_id, missing=[], status="Collecting"
		)
		record = db.update_pending_intent(
			record["name"],
			preview=preview,
			preview_hash=preview_hash,
			idempotency_key=idempotency_key,
			status="AwaitingConfirmation",
		)
	reply = _format_preview_reply(spec.key, payload)
	db.append_message(
		conversation,
		"Outbound",
		reply,
		correlation_id=correlation_id,
		intent_key=spec.key,
		intent_json=preview,
	)
	return _response("AwaitingConfirmation", reply, {"name": record["name"], "preview": preview})


def _run_navigate(conversation: str, spec, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]:
	directive = {
		"action": "navigate",
		"route": spec.route,
		"route_options": {k: v for k, v in payload.items() if v},
	}
	reply = f"Listo, te llevo a la pantalla de {spec.description.lower()} con el proyecto ya seleccionado."
	db.append_message(
		conversation,
		"Outbound",
		reply,
		correlation_id=correlation_id,
		intent_key=spec.key,
		intent_json=directive,
	)
	return _response("Executed", reply, directive)


def _run_read(conversation: str, spec, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]:
	try:
		data = _invoke_read(spec, payload)
	except frappe.PermissionError:
		reply = "No tienes permiso para consultar esta información."
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=spec.key)
		return _response("Failed", reply, None)
	except frappe.exceptions.ValidationError as exc:
		reply = f"No pude completar la consulta: {exc}"
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=spec.key)
		return _response("Failed", reply, None)
	reply = _format_read_reply(spec.key, data)
	db.append_message(
		conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=spec.key, intent_json=data
	)
	return _response("Executed", reply, {"result": data})


@frappe.whitelist(methods=["POST"])
def send_message(payload: str | dict[str, Any]) -> dict[str, Any]:
	_require_assistant_access()
	data = parse_payload(payload)
	text = _required(data, "text", "Escribe un mensaje.")
	# Opcional (Bloque 21, canal WhatsApp): un archivo ya subido por el
	# llamador (nunca una ruta que este módulo escriba) — se fusiona como el
	# slot `file_url` sin importar qué intención se resuelva, para que un
	# adjunto sobreviva incluso a una intención `Collecting` que ya lo estaba
	# esperando. El canal de texto puro (Bloque 18) nunca envía esta clave.
	attachment_file_url = str(data.get("attachment_file_url") or "").strip() or None
	if frappe.session.user == "Guest":
		frappe.throw(_("Inicia sesión para usar el asistente de NEXORA."), frappe.PermissionError)

	conversation = db.get_or_create_conversation(frappe.session.user)
	correlation_id = correlation(data)
	db.append_message(conversation, "Inbound", text, correlation_id=correlation_id)

	open_intent = db.get_open_pending_intent(conversation)
	if open_intent and open_intent["status"] == "AwaitingConfirmation":
		normalized = text.strip().lower()
		doc = frappe.get_doc("NXR Conversation Pending Intent", open_intent["name"])
		if normalized in _CONFIRM_WORDS:
			return _confirm_intent(doc)
		if normalized in _CANCEL_WORDS:
			return _cancel_intent(doc)
		reply = (
			"Tienes una operación pendiente de confirmar. Responde 'confirmar' para "
			"ejecutarla o 'cancelar' para descartarla."
		)
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id)
		return _response("AwaitingConfirmation", reply, {"name": open_intent["name"]})

	history = _recent_history(conversation)
	try:
		interpretation = nlu.interpret(text, history, correlation_id)
	except nlu.ConversationNluError as exc:
		reply = str(exc)
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id)
		return _response("Failed", reply, None)

	intent_key = interpretation["intent"]
	fields = interpretation["fields"]
	if attachment_file_url:
		fields = {**fields, "file_url": attachment_file_url}

	base_payload: dict[str, Any] = {}
	if open_intent and open_intent["status"] == "Collecting":
		if intent_key in (None, open_intent["intent_key"]):
			intent_key = open_intent["intent_key"]
			base_payload = json.loads(open_intent["payload_json"] or "{}")
		else:
			db.update_pending_intent(open_intent["name"], status="Cancelled")
			open_intent = None

	if intent_key is None:
		reply = (
			interpretation["clarification_question"] or "No entendí qué necesitas. ¿Puedes darme más detalle?"
		)
		db.append_message(conversation, "Outbound", reply, correlation_id=correlation_id)
		return _response("Collecting", reply, None)

	spec = REGISTRY[intent_key]
	merged = merge_payload(base_payload, fields)

	try:
		merged = _resolve_references(spec, merged)
	except resolve.AmbiguousReferenceError as exc:
		reply = _ambiguous_message(exc.candidates)
		db.append_message(
			conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=intent_key
		)
		return _response("Collecting", reply, None)
	except UnresolvedReferenceError as exc:
		reply = str(exc)
		if open_intent and open_intent["status"] == "Collecting":
			db.update_pending_intent(open_intent["name"], status="Cancelled")
		db.append_message(
			conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=intent_key
		)
		return _response("Failed", reply, None)

	pending = missing_slots(spec, merged)
	open_name = (
		open_intent["name"]
		if open_intent and open_intent["status"] == "Collecting" and open_intent["intent_key"] == intent_key
		else None
	)
	if pending:
		if open_name:
			db.update_pending_intent(open_name, payload=merged, missing=pending)
		else:
			record = db.create_pending_intent(
				conversation, intent_key, merged, correlation_id=correlation_id, missing=pending
			)
			open_name = record["name"]
		reply = next_question(spec, merged) or "Necesito más información para continuar."
		db.append_message(
			conversation, "Outbound", reply, correlation_id=correlation_id, intent_key=intent_key
		)
		return _response("Collecting", reply, {"name": open_name})

	if spec.kind is IntentKind.READ:
		if open_name:
			db.update_pending_intent(open_name, status="Cancelled")
		return _run_read(conversation, spec, merged, correlation_id)
	if spec.kind is IntentKind.NAVIGATE:
		if open_name:
			db.update_pending_intent(open_name, status="Cancelled")
		return _run_navigate(conversation, spec, merged, correlation_id)
	return _run_write_preview(conversation, spec, merged, correlation_id, open_name)


@frappe.whitelist(methods=["POST"])
def confirm_pending_intent(payload: str | dict[str, Any]) -> dict[str, Any]:
	_require_assistant_access()
	data = parse_payload(payload)
	name = _required(data, "pending_intent", "Indica qué intención confirmar.")
	doc = frappe.get_doc("NXR Conversation Pending Intent", name)
	_assert_owns_conversation(doc.conversation)
	return _confirm_intent(doc)


def _confirm_intent(doc) -> dict[str, Any]:
	name = doc.name
	if doc.status != "AwaitingConfirmation":
		frappe.throw(_("Esta operación no está esperando confirmación."))

	spec = REGISTRY[doc.intent_key]
	stored_payload = json.loads(doc.payload_json or "{}")
	call_payload = _build_write_payload(
		spec.key,
		stored_payload,
		doc.correlation_id,
		idempotency_key=doc.idempotency_key,
		preview_hash=doc.preview_hash or None,
	)
	db.update_pending_intent(name, status="Confirmed")
	try:
		result = frappe.get_attr(spec.execute_method)(call_payload)
	except frappe.PermissionError:
		db.update_pending_intent(name, status="Failed", result={"error": "permission_denied"})
		reply = "No tienes permiso para ejecutar esta operación."
		db.append_message(
			doc.conversation, "Outbound", reply, correlation_id=doc.correlation_id, intent_key=spec.key
		)
		return _response("Failed", reply, None)
	except frappe.exceptions.ValidationError as exc:
		db.update_pending_intent(name, status="Failed", result={"error": "validation_error"})
		reply = f"No pude ejecutar la operación: {exc}"
		db.append_message(
			doc.conversation, "Outbound", reply, correlation_id=doc.correlation_id, intent_key=spec.key
		)
		return _response("Failed", reply, None)
	except Exception:  # noqa: BLE001 - registrar y sanitizar errores inesperados
		frappe.log_error(
			frappe.get_traceback(),
			title=f"{_title}: {doc.correlation_id} / {name}",
		)
		db.update_pending_intent(name, status="Failed", result={"error": "internal_error"})
		reply = f"{_INTERNAL_EXECUTION_ERROR} Correlación: {doc.correlation_id}"
		db.append_message(
			doc.conversation, "Outbound", reply, correlation_id=doc.correlation_id, intent_key=spec.key
		)
		return _response("Failed", reply, None)

	db.update_pending_intent(name, status="Executed", result=result)
	reply = _format_execution_reply(spec.key, result)
	db.append_message(
		doc.conversation,
		"Outbound",
		reply,
		correlation_id=doc.correlation_id,
		intent_key=spec.key,
		intent_json=result,
	)
	audit(
		"conversation_intent_executed",
		"NXR Conversation Pending Intent",
		name,
		doc.preview_hash or "",
		doc.correlation_id,
		{"origin": "conversation", "intent": spec.key, **result},
	)
	return _response("Executed", reply, result)


def _format_execution_reply(intent_key: str, result: dict[str, Any]) -> str:
	document = result.get("operation") or result.get("evidence") or result.get("document_number") or "—"
	if intent_key in ("register_expense", "register_income"):
		return f"Listo. Documento {document} registrado."
	if intent_key == "register_evidence":
		return f"Evidencia guardada como {document}."
	return f"Operación ejecutada: {document}."


@frappe.whitelist(methods=["POST"])
def cancel_pending_intent(payload: str | dict[str, Any]) -> dict[str, Any]:
	_require_assistant_access()
	data = parse_payload(payload)
	name = _required(data, "pending_intent", "Indica qué intención cancelar.")
	doc = frappe.get_doc("NXR Conversation Pending Intent", name)
	_assert_owns_conversation(doc.conversation)
	return _cancel_intent(doc)


def _cancel_intent(doc) -> dict[str, Any]:
	name = doc.name
	if doc.status in ("Executed", "Failed", "Cancelled"):
		frappe.throw(_("Esta operación ya no se puede cancelar."))
	db.update_pending_intent(name, status="Cancelled")
	reply = "Operación cancelada."
	db.append_message(
		doc.conversation, "Outbound", reply, correlation_id=doc.correlation_id, intent_key=doc.intent_key
	)
	audit(
		"conversation_intent_cancelled",
		"NXR Conversation Pending Intent",
		name,
		doc.preview_hash or "",
		doc.correlation_id,
		{"origin": "conversation", "intent": doc.intent_key},
	)
	return _response("Cancelled", reply, None)


_CONFIRM_WORDS = {"confirmar", "confirmo", "sí", "si", "sí, confirmo", "ok", "dale", "correcto"}
_CANCEL_WORDS = {"cancelar", "cancelo", "no", "no, cancela", "olvídalo"}
