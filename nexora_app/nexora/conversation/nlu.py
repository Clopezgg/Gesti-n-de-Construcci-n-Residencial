"""Resolución de intención vía el orquestador de IA ya existente (Bloque 18).

Reutiliza íntegramente ``nexora.intelligence.orchestrator.execute`` (NIP,
Bloques 1-6, mergeado y probado) — este módulo no implementa proveedores, no
sabe qué proveedor responderá y no reimplementa fallback: eso ya lo hace el
orquestador. Solo construye el mensaje desde el ``Registry``, interpreta la
respuesta del proveedor que haya respondido, y valida estrictamente el JSON
resultante antes de confiar en él.
"""

from __future__ import annotations

from typing import Any

from nexora.conversation.core import ConversationValidationError, build_intent_prompt, parse_model_intent
from nexora.conversation.registry import REGISTRY
from nexora.intelligence.core import IntelligenceError, ProviderResponse
from nexora.intelligence.orchestrator import execute as orchestrator_execute


class ConversationNluError(Exception):
	"""Traduce cualquier falla de interpretación (proveedor caído, timeout,
	JSON inválido) a un mensaje conversacional único, sin filtrar detalles
	internos del proveedor al usuario final."""


def _extract_text(response: ProviderResponse) -> str:
	"""Extrae el texto generado de la forma cruda de cada proveedor.

	Los nueve adaptadores certificados (Bloque 2) devuelven ``data`` tal cual
	la API del proveedor la entrega, sin normalizar (confirmado leyendo cada
	``*_live.py`` y ``intelligence/service.py::run_orchestrated_request``, que
	nunca necesitó leer el texto generado, solo ``provider_key``). El
	orquestador puede hacer *fallback* a cualquiera de los nueve sin que el
	llamador lo controle, así que esta función debe saber leer las tres
	formas reales que existen hoy; cualquier forma no reconocida degrada a
	cadena vacía (nunca lanza), lo que ``parse_model_intent`` traduce a un
	"no entendí" seguro en vez de un error no controlado.
	"""

	data = response.data
	try:
		if response.provider_key == "anthropic":
			return str(data["content"][0]["text"])
		if response.provider_key == "gemini":
			return str(data["candidates"][0]["content"]["parts"][0]["text"])
		if response.provider_key == "cohere":
			return str(data.get("text") or "")
		# Compatibles con OpenAI: openai, groq, deepseek, mistral, perplexity, openrouter.
		return str(data["choices"][0]["message"]["content"])
	except (KeyError, IndexError, TypeError):
		return ""


def _flatten_history(system_prompt: str, history: list[dict[str, str]], text: str) -> str:
	"""Representación de un solo texto de la conversación.

	Necesaria porque no los nueve proveedores aceptan una lista de turnos:
	Gemini exige ``contents`` y Cohere exige ``message`` (una sola cadena) —
	ninguno de los dos lee ``messages`` (confirmado en sus adaptadores), así
	que si el orquestador cae a cualquiera de los dos, reciben esto en vez de
	un array de turnos vacío/ignorado.
	"""

	lines = [system_prompt, ""]
	for turn in history:
		lines.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
	lines.append(f"user: {text}")
	return "\n".join(lines)


def interpret(text: str, history: list[dict[str, str]], correlation_id: str) -> dict[str, Any]:
	"""Interpreta ``text`` contra el catálogo real de intenciones.

	Devuelve ``{"intent": str|None, "confidence": float, "fields": dict,
	"clarification_question": str|None}``. Nunca lanza una excepción de
	proveedor sin traducir: cualquier ``IntelligenceError`` (sin proveedor
	configurado, todos los proveedores agotados, credencial faltante) se
	convierte en ``ConversationNluError`` con un mensaje honesto — nunca se
	inventa una intención cuando el modelo no respondió.
	"""

	system_prompt = build_intent_prompt(REGISTRY)
	messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": text}]
	payload = {
		"messages": messages,
		"prompt": _flatten_history(system_prompt, history, text),
	}
	try:
		response = orchestrator_execute("text", payload, correlation_id)
	except IntelligenceError as exc:
		raise ConversationNluError(
			"No pude interpretar tu mensaje porque el asistente de IA no está disponible en este "
			"momento. Intenta de nuevo en un momento o usa la pantalla correspondiente directamente."
		) from exc
	raw_text = _extract_text(response)
	try:
		return parse_model_intent(raw_text, REGISTRY.keys())
	except ConversationValidationError as exc:
		raise ConversationNluError(
			"No entendí bien tu mensaje. ¿Puedes reformularlo o decirme exactamente qué necesitas?"
		) from exc
