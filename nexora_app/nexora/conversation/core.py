"""Núcleo puro del motor conversacional (Bloque 18, NXR-CNV-0001).

Sin dependencia de Frappe (mismo principio que ``purchases/request_core.py`` o
``context360/core.py``): solo estructuras de datos, resolución de campos
faltantes y la máquina de estados de un "Pending Intent". Este módulo no sabe
invocar ninguna función de negocio real — solo describe *qué* intención
necesita *qué* campos y *en qué orden* puede transicionar. La invocación real
(``frappe.get_attr(dotted_path)(payload)``) vive en ``dispatch.py``, que sí
depende de Frappe.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import Enum
from typing import Any

try:
	from frappe.exceptions import ValidationError as FrappeValidationError
except ImportError:  # pragma: no cover - solo cuando Frappe no está instalado
	FrappeValidationError = Exception


class ConversationValidationError(ValueError, FrappeValidationError):
	"""Error de dominio conversacional, usable dentro y fuera de Frappe."""


class IntentKind(str, Enum):
	"""Las tres únicas formas en que una intención puede resolverse.

	READ: solo lectura, ninguna confirmación (no muta nada).
	WRITE: preview obligatorio + confirmación explícita antes de ejecutar.
	NAVIGATE: no toca el servidor; solo devuelve una ruta con contexto
	prellenado, igual que el botón "Ver proyecto 360°" del Bloque 17.
	"""

	READ = "read"
	WRITE = "write"
	NAVIGATE = "navigate"


@dataclass(frozen=True)
class Slot:
	"""Un campo que la intención necesita, y la pregunta para pedirlo."""

	name: str
	question: str
	required: bool = True


@dataclass(frozen=True)
class IntentSpec:
	"""Entrada declarativa del catálogo (``registry.py``).

	``read_method``/``preview_method``/``execute_method`` son *rutas
	punteadas* a funciones reales ya auditadas (p. ej.
	``"nexora.financial.sources.list_source_balances"``), nunca lógica propia
	— ``dispatch.py`` las resuelve con ``frappe.get_attr`` en tiempo de
	llamada, exactamente como ``hooks.py:override_whitelisted_methods`` ya
	hace para redirigir rutas.
	"""

	key: str
	kind: IntentKind
	description: str
	slots: tuple[Slot, ...] = field(default_factory=tuple)
	read_method: str | None = None
	# None en una intención WRITE significa "sin preview_* propio en el
	# dominio" (p. ej. registrar evidencia): dispatch.py construye entonces
	# un eco local de los campos capturados como vista previa, en vez de
	# llamar a un servidor que no expone esa función.
	preview_method: str | None = None
	execute_method: str | None = None
	route: str | None = None

	def __post_init__(self) -> None:
		if self.kind is IntentKind.READ and not self.read_method:
			raise ValueError(f"{self.key}: una intención READ requiere read_method.")
		if self.kind is IntentKind.WRITE and not self.execute_method:
			raise ValueError(f"{self.key}: una intención WRITE requiere execute_method.")
		if self.kind is IntentKind.NAVIGATE and not self.route:
			raise ValueError(f"{self.key}: una intención NAVIGATE requiere route.")


def missing_slots(spec: IntentSpec, payload: Mapping[str, Any]) -> list[str]:
	"""Campos obligatorios de ``spec`` ausentes o vacíos en ``payload``.

	Esta es una lista *mínima* de lo obviamente necesario para siquiera
	intentar la operación — la validación autoritativa de negocio la hace la
	función real (``preview_method``/``execute_method``/``read_method``), que
	puede exigir más y cuyo ``frappe.throw`` se traduce en una pregunta o un
	error legible (ver ``dispatch.py``). No se duplica aquí ninguna regla que
	la función real ya aplique.
	"""

	return [
		slot.name for slot in spec.slots if slot.required and not str(payload.get(slot.name) or "").strip()
	]


def next_question(spec: IntentSpec, payload: Mapping[str, Any]) -> str | None:
	pending = missing_slots(spec, payload)
	if not pending:
		return None
	by_name = {slot.name: slot for slot in spec.slots}
	return by_name[pending[0]].question


def merge_payload(existing: Mapping[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
	"""Fusiona campos nuevos sobre el borrador existente sin perder lo ya capturado.

	Un valor vacío/``None`` en ``updates`` nunca borra un valor ya capturado —
	así es como una corrección puntual ("no, mejor el monto es...") no reinicia
	el resto de lo ya respondido.
	"""

	merged = dict(existing)
	for key, value in updates.items():
		if value in (None, ""):
			continue
		merged[key] = value
	return merged


# Estados terminales (EJECUTADA/FALLIDA/CANCELADA en el catálogo de gobernanza,
# STM-CONVERSATION-INTENT) nunca transicionan a ningún otro estado — un
# reintento tras un fallo crea un Pending Intent nuevo, no reabre el viejo
# (mismo principio que "forbidden_reopen" en el resto del catálogo).
PENDING_INTENT_TRANSITIONS: dict[str, frozenset[str]] = {
	"Collecting": frozenset({"AwaitingConfirmation", "Cancelled"}),
	"AwaitingConfirmation": frozenset({"Collecting", "Confirmed", "Cancelled"}),
	"Confirmed": frozenset({"Executed", "Failed"}),
	"Executed": frozenset(),
	"Failed": frozenset(),
	"Cancelled": frozenset(),
}


def assert_pending_intent_transition(source: str, target: str) -> None:
	if source == target:
		return
	if target not in PENDING_INTENT_TRANSITIONS.get(source, frozenset()):
		raise ConversationValidationError(f"Transición de intención no permitida: {source} → {target}.")


def build_intent_prompt(specs: Mapping[str, IntentSpec]) -> str:
	"""Prompt de sistema construido desde el propio Registry.

	El catálogo de "qué puede entender NEXORA" y "qué le decimos al modelo
	que puede hacer" son la misma fuente — no hay dos listas que puedan
	desincronizarse (mismo argumento que ``NIP_BLOQUE_6_CONVERSATIONAL_OS.md``
	ya documentaba antes de que existiera código).
	"""

	intro = (
		"Eres el intérprete de intención de NEXORA, un sistema de gestión de fondos, "
		+ "proyectos y operaciones de construcción."
	)
	json_format = (
		"Responde EXCLUSIVAMENTE con un objeto JSON de esta forma exacta, sin texto "
		+ 'fuera del JSON: {"intent": <clave o null>, "confidence": <0..1>, '
		+ '"fields": {<campo>: <valor>}, "clarification_question": <string o null>}.'
	)
	no_match = (
		"Si el mensaje del usuario no coincide claramente con ninguna intención, usa "
		+ '"intent": null y explica en "clarification_question" qué preguntarle.'
	)
	lines = [intro, json_format, no_match, "Intenciones disponibles:"]
	for spec in specs.values():
		slot_desc = ", ".join(f"{slot.name} ({slot.question})" for slot in spec.slots) or "ninguno"
		lines.append(f"- {spec.key}: {spec.description}. Campos relevantes: {slot_desc}.")
	return "\n".join(lines)


_KNOWN_INTENT_FIELDS = {"intent", "confidence", "fields", "clarification_question"}


def parse_model_intent(raw: str, known_intents: Iterable[str]) -> dict[str, Any]:
	"""Valida estrictamente la respuesta JSON del modelo contra el esquema esperado.

	Nunca confía en que el proveedor de IA respetó el formato pedido — cualquier
	desviación (JSON inválido, intención desconocida, confianza fuera de rango,
	campos con tipo incorrecto) se traduce en ``ConversationValidationError``,
	que ``dispatch.py`` convierte en una pregunta de aclaración honesta en vez
	de ejecutar sobre datos no confiables.
	"""

	try:
		data = json.loads(raw)
	except (json.JSONDecodeError, TypeError) as exc:
		raise ConversationValidationError("El modelo no devolvió un JSON válido.") from exc
	if not isinstance(data, dict):
		raise ConversationValidationError("El modelo no devolvió un objeto JSON.")
	unexpected = set(data) - _KNOWN_INTENT_FIELDS
	if unexpected:
		raise ConversationValidationError(f"El modelo devolvió campos no esperados: {sorted(unexpected)}.")
	intent = data.get("intent")
	known = set(known_intents)
	if intent is not None and intent not in known:
		raise ConversationValidationError(f"El modelo devolvió una intención desconocida: {intent!r}.")
	confidence = data.get("confidence", 0)
	if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
		raise ConversationValidationError("El modelo devolvió una confianza con tipo inválido.")
	if not (0 <= confidence <= 1):
		raise ConversationValidationError("El modelo devolvió una confianza fuera de [0, 1].")
	fields = data.get("fields") or {}
	if not isinstance(fields, dict):
		raise ConversationValidationError("El modelo devolvió campos con tipo inválido.")
	clarification = data.get("clarification_question")
	if clarification is not None and not isinstance(clarification, str):
		raise ConversationValidationError("El modelo devolvió una pregunta de aclaración con tipo inválido.")
	return {
		"intent": intent,
		"confidence": float(confidence),
		"fields": fields,
		"clarification_question": clarification,
	}


def format_money_hnl(value: object) -> str:
	"""Formato humano en lempiras para respuestas de texto (no HTML).

	Distinto de ``formatMoney`` (JS, para la interfaz) y de ``financial.core.money``
	(Decimal para cálculo) — este es el único formateador de dinero para texto
	conversacional plano y no existía antes de este bloque.
	"""

	try:
		amount = Decimal(str(value if value is not None else 0))
	except (InvalidOperation, ValueError):
		amount = Decimal(0)
	quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	return f"L {quantized:,.2f}"
