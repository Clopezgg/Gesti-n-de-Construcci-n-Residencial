from __future__ import annotations

import re

__all__ = [
	"DEFAULT_MAX_CHARS",
	"CHARS_PER_TOKEN_ESTIMATE",
	"estimate_tokens",
	"normalize_whitespace",
	"truncate_to_budget",
	"optimize_prompt",
]

# Inspirado en el pipeline de compresión de OmniRoute (Bloque 5.2), pero
# deliberadamente NO es un compresor semántico/asistido por IA: usar un
# modelo para comprimir un prompt antes de mandarlo a otro modelo sería
# circular (necesitaría, a su vez, un proveedor disponible) y no se puede
# verificar sin red real que preserve el significado. Esto es mecánico y
# verificable con pruebas puras: normaliza espacios y, si hace falta, trunca
# con un marcador explícito — nunca reescribe ni resume el contenido.

# Heurística común y documentada como tal (no exacta): ~4 caracteres por
# token en inglés/español para modelos de la familia GPT/Claude/Llama. No se
# añade una dependencia de tokenizador solo para una estimación aproximada
# usada como límite defensivo, no como facturación.
CHARS_PER_TOKEN_ESTIMATE = 4

DEFAULT_MAX_CHARS = 24_000  # ~6 000 tokens estimados

_WHITESPACE_RUN = re.compile(r"[ \t]+")
_BLANK_LINE_RUN = re.compile(r"\n{3,}")

_TRUNCATION_MARKER = "\n\n[...contenido recortado por límite de tamaño...]\n\n"


def estimate_tokens(text: str) -> int:
	"""Estimación aproximada, nunca exacta — ver ``CHARS_PER_TOKEN_ESTIMATE``."""

	return max(0, len(text)) // CHARS_PER_TOKEN_ESTIMATE


def normalize_whitespace(text: str) -> str:
	"""Colapsa espacios/tabulaciones repetidos y líneas en blanco excesivas.

	Nunca cambia una palabra, nunca reordena contenido — reduce tokens sin
	ningún riesgo de alterar el significado, a diferencia de un resumen.
	"""

	collapsed = _WHITESPACE_RUN.sub(" ", text)
	collapsed = _BLANK_LINE_RUN.sub("\n\n", collapsed)
	return collapsed.strip()


def truncate_to_budget(text: str, *, max_chars: int) -> str:
	"""Si ``text`` cabe en ``max_chars``, lo devuelve sin tocar.

	Si no cabe, conserva el inicio y el final (donde suele vivir la
	instrucción y el contexto más reciente) y marca explícitamente el
	recorte — nunca corta en silencio ni pretende haber conservado todo el
	significado.
	"""

	if len(text) <= max_chars:
		return text
	if max_chars <= len(_TRUNCATION_MARKER):
		# Sin espacio ni para el marcador: recorte simple, sin pretender
		# conservar inicio y final. Caso extremo, no el camino normal.
		return text[:max_chars]
	budget = max_chars - len(_TRUNCATION_MARKER)
	head = budget * 2 // 3
	tail = budget - head
	return text[:head] + _TRUNCATION_MARKER + (text[-tail:] if tail else "")


def optimize_prompt(text: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, object]:
	"""Aplica ambos pasos y reporta qué se hizo, para que quien llame (el
	Orchestrator) pueda auditar la decisión en vez de que ocurra en silencio.
	"""

	original_length = len(text)
	normalized = normalize_whitespace(text)
	truncated = truncate_to_budget(normalized, max_chars=max_chars)
	return {
		"text": truncated,
		"original_chars": original_length,
		"final_chars": len(truncated),
		"was_truncated": len(truncated) != len(normalized),
		"estimated_tokens": estimate_tokens(truncated),
	}
