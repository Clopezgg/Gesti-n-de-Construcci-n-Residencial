from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from nexora.intelligence.core import AdapterInvocationError, ProviderAuthenticationError, ProviderTimeoutError

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
	"""

	try:
		body = json.dumps(payload).encode("utf-8") if payload is not None else None
	except TypeError as exc:
		raise AdapterInvocationError(
			f"La solicitud al proveedor {provider_key!r} contiene datos no serializables."
		) from exc

	request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
			raw = response.read().decode("utf-8")
			return json.loads(raw) if raw else {}
	except (json.JSONDecodeError, ValueError) as exc:
		raise AdapterInvocationError(
			f"El proveedor {provider_key!r} respondió con contenido JSON no válido."
		) from exc
	except urllib.error.HTTPError as exc:
		detail = exc.read().decode("utf-8", errors="replace")[:200]
		if exc.code in (401, 403):
			raise ProviderAuthenticationError(
				f"El proveedor {provider_key!r} rechazó la credencial (HTTP {exc.code})."
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
