from __future__ import annotations

import os

from nexora.intelligence.core import CredentialFormatError

# Nombres oficiales de variable de entorno por proveedor
# (NEXORA_INTELLIGENCE_ARCHITECTURE.md, sección 8: "variable de entorno de
# servidor" tiene prioridad sobre cualquier valor guardado en base de datos).
# Mismo espíritu que ``SUPABASE_SERVER_KEY`` en ``.env.nexora.example``:
# exclusivamente de servidor, nunca ``VITE_``, nunca versionada con un valor
# real.
PROVIDER_ENV_VARS: dict[str, str] = {
	"anthropic": "ANTHROPIC_API_KEY",
	"openai": "OPENAI_API_KEY",
	"perplexity": "PERPLEXITY_API_KEY",
	"openrouter": "OPENROUTER_API_KEY",
	"gemini": "GEMINI_API_KEY",
	"groq": "GROQ_API_KEY",
	"deepseek": "DEEPSEEK_API_KEY",
	"mistral": "MISTRAL_API_KEY",
	"cohere": "COHERE_API_KEY",
}

_MIN_SECRET_LENGTH = 16
_MAX_SECRET_LENGTH = 256

# Mismo vocabulario que ya usan `.env.example` / `.env.nexora.example` para
# marcar un valor de plantilla ("REEMPLAZAR_CON_...", "change-me-..."), más
# los equivalentes en inglés más comunes en credenciales de proveedores de IA.
_PLACEHOLDER_MARKERS = (
	"changeme",
	"change-me",
	"change_me",
	"reemplazar",
	"your-api-key",
	"your_api_key",
	"xxxxxxxx",
	"placeholder",
	"example",
	"insert-key-here",
)


def known_provider_env_var(provider_key: str) -> str | None:
	"""Nombre de la variable de entorno oficial de un proveedor, si existe."""

	return PROVIDER_ENV_VARS.get(provider_key)


def validate_credential_format(secret: str) -> str:
	"""Valida la FORMA de una credencial — nunca su validez real.

	Deliberado: confirmar una clave contra el proveedor exigiría una llamada
	de red real, exactamente lo que este bloque prohíbe ("no hagas llamadas
	innecesarias a APIs externas si pueden validarse de forma segura con el
	patrón del proyecto"). Esta función solo descarta lo que con certeza está
	mal: vacía, con espacios al borde, demasiado corta, demasiado larga o un
	valor de plantilla obvio. Que pase esta validación no confirma que el
	proveedor la vaya a aceptar — por eso el estado que produce se llama
	``"Format Valid"``, nunca ``"Valid"`` a secas.
	"""

	text = secret if isinstance(secret, str) else ""
	if not text:
		raise CredentialFormatError("La credencial no puede estar vacía.")
	if text != text.strip():
		raise CredentialFormatError("La credencial no puede tener espacios al inicio o al final.")
	if len(text) < _MIN_SECRET_LENGTH:
		raise CredentialFormatError(
			f"La credencial es demasiado corta (mínimo {_MIN_SECRET_LENGTH} caracteres)."
		)
	if len(text) > _MAX_SECRET_LENGTH:
		raise CredentialFormatError(
			f"La credencial es demasiado larga (máximo {_MAX_SECRET_LENGTH} caracteres)."
		)
	lowered = text.lower()
	for marker in _PLACEHOLDER_MARKERS:
		if marker in lowered:
			raise CredentialFormatError("La credencial parece un valor de plantilla, no una clave real.")
	return text


def resolve_environment_credential(provider_key: str) -> str | None:
	"""Lee la credencial exclusivamente de una variable de entorno de servidor.

	Nunca de un archivo versionado — mismo principio que ya sigue
	``erpnext/construcontrol/storage/supabase.py`` con ``SUPABASE_SERVER_KEY``:
	server-only, resuelta en tiempo de ejecución, jamás comprometida a
	control de versiones.
	"""

	env_var = PROVIDER_ENV_VARS.get(provider_key)
	if not env_var:
		return None
	value = os.getenv(env_var, "").strip()
	return value or None
