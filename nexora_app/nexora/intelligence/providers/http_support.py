from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from nexora.intelligence.core import (
	AdapterInvocationError,
	ProviderAuthenticationError,
	ProviderModelNotFoundError,
	ProviderQuotaExhaustedError,
	ProviderRateLimitError,
	ProviderTimeoutError,
)

__all__ = ["send_json_request"]

# Descubierto por certificación real contra Groq (Bloque 5.2): Cloudflare, que
# protege esa API, bloquea con HTTP 403 cualquier solicitud sin User-Agent —
# el valor por defecto de ``urllib`` ("Python-urllib/3.x") queda filtrado.
# Sin esta cabecera, ese 403 de un firewall se clasificaba incorrectamente
# como "credencial rechazada" (``ProviderAuthenticationError``). Cualquier
# adaptador puede seguir enviando su propio ``User-Agent``; este solo se usa
# si no lo hace.
_DEFAULT_USER_AGENT = "NEXORA-Intelligence-Platform/1.0"


def send_json_request(
	*,
	url: str,
	headers: Mapping[str, str],
	payload: Mapping[str, Any] | None,
	timeout_seconds: int,
	provider_key: str,
	method: str = "POST",
) -> dict[str, Any]:
	"""Envía una solicitud HTTP JSON real y devuelve la respuesta decodificada.

	Único punto de todo el subsistema que abre una conexión de red real hacia
	un proveedor de IA — todos los adaptadores en vivo del Bloque 4 lo
	comparten para no duplicar manejo de errores (Capítulo 44: toda regla en
	un único lugar). Usa exclusivamente ``urllib`` de la biblioteca estándar:
	ningún SDK de proveedor ni cliente HTTP de terceros se añade como
	dependencia (mismo principio que ``erpnext/construcontrol/storage/supabase.py``).

	Las pruebas de este bloque nunca ejecutan esta función contra un
	proveedor real: sustituyen ``send_json_request`` por un doble de prueba y
	verifican la solicitud construida (URL, cabeceras, cuerpo) y el manejo de
	cada tipo de error por separado.

	Envía siempre un ``User-Agent`` (por defecto o el que indique el
	adaptador) — un firewall delante de la API de un proveedor puede devolver
	403 a una solicitud sin uno, y eso no es un rechazo de credencial.

	Clasificación de errores HTTP (Bloque 4 + Bloque 5): 401/403 →
	``ProviderAuthenticationError``; 429 → ``ProviderRateLimitError`` (incluye
	``Retry-After`` en el mensaje si el proveedor lo envía); 404 →
	``ProviderModelNotFoundError`` — heurística razonable dado que las URLs
	que este subsistema construye son fijas y ya validadas, así que un 404
	real casi siempre señala el segmento del modelo, no un endpoint mal
	formado; sin confirmarlo contra las nueve APIs reales, se documenta como
	la mejor aproximación disponible, no como un hecho verificado proveedor
	por proveedor. 402 → ``ProviderQuotaExhaustedError`` (Bloque 5.2,
	confirmado en vivo contra DeepSeek: "Insufficient Balance" — la
	credencial es válida, la cuenta no tiene saldo). Cualquier otro código →
	``AdapterInvocationError`` genérico.
	"""

	body = json.dumps(payload).encode("utf-8") if payload is not None else None
	merged_headers = {"User-Agent": _DEFAULT_USER_AGENT, **headers}
	request = urllib.request.Request(url, data=body, headers=merged_headers, method=method)
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
			raw = response.read().decode("utf-8")
			return json.loads(raw) if raw else {}
	except urllib.error.HTTPError as exc:
		detail = exc.read().decode("utf-8", errors="replace")[:200]
		if exc.code in (401, 403):
			raise ProviderAuthenticationError(
				f"El proveedor {provider_key!r} rechazó la credencial (HTTP {exc.code})."
			) from exc
		if exc.code == 429:
			retry_after_raw = exc.headers.get("Retry-After") if exc.headers else None
			retry_after_seconds: int | None
			try:
				retry_after_seconds = int(retry_after_raw) if retry_after_raw is not None else None
			except ValueError:
				retry_after_seconds = None  # Retry-After también admite una fecha HTTP; no la parseamos.
			suffix = f" Reintentar después de {retry_after_raw} segundos." if retry_after_raw else ""
			raise ProviderRateLimitError(
				f"El proveedor {provider_key!r} aplicó límite de tasa (HTTP 429).{suffix}",
				retry_after_seconds=retry_after_seconds,
			) from exc
		if exc.code == 404:
			raise ProviderModelNotFoundError(
				f"El proveedor {provider_key!r} no reconoce el modelo solicitado (HTTP 404): {detail}"
			) from exc
		if exc.code == 402:
			raise ProviderQuotaExhaustedError(
				f"El proveedor {provider_key!r} indicó cuota o saldo agotado (HTTP 402): {detail}"
			) from exc
		raise AdapterInvocationError(
			f"El proveedor {provider_key!r} respondió HTTP {exc.code}: {detail}"
		) from exc
	except TimeoutError as exc:
		raise ProviderTimeoutError(
			f"El proveedor {provider_key!r} no respondió en {timeout_seconds} segundos."
		) from exc
	except urllib.error.URLError as exc:
		raise AdapterInvocationError(f"No se pudo conectar con {provider_key!r}: {exc.reason}") from exc
