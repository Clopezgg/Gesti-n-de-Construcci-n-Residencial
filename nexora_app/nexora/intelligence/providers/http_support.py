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
	ProviderRateLimitError,
	ProviderTimeoutError,
)

__all__ = ["send_json_request"]


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

	Clasificación de errores HTTP (Bloque 4 + Bloque 5): 401/403 →
	``ProviderAuthenticationError``; 429 → ``ProviderRateLimitError`` (incluye
	``Retry-After`` en el mensaje si el proveedor lo envía); 404 →
	``ProviderModelNotFoundError`` — heurística razonable dado que las URLs
	que este subsistema construye son fijas y ya validadas, así que un 404
	real casi siempre señala el segmento del modelo, no un endpoint mal
	formado; sin confirmarlo contra las nueve APIs reales, se documenta como
	la mejor aproximación disponible, no como un hecho verificado proveedor
	por proveedor. Cualquier otro código → ``AdapterInvocationError``
	genérico.
	"""

	body = json.dumps(payload).encode("utf-8") if payload is not None else None
	request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
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
			retry_after = exc.headers.get("Retry-After") if exc.headers else None
			suffix = f" Reintentar después de {retry_after} segundos." if retry_after else ""
			raise ProviderRateLimitError(
				f"El proveedor {provider_key!r} aplicó límite de tasa (HTTP 429).{suffix}"
			) from exc
		if exc.code == 404:
			raise ProviderModelNotFoundError(
				f"El proveedor {provider_key!r} no reconoce el modelo solicitado (HTTP 404): {detail}"
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
