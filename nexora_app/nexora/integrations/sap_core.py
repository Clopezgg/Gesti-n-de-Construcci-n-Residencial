"""Lógica pura del adaptador SAP: sin `import frappe`, sin red.

Mismo principio que separa `conversation.channels.whatsapp_core` de
`conversation.channels.whatsapp` — lo que no depende de Frappe ni de una
llamada real vive aquí, para poder probarse por unidad sin bench ni MariaDB.
"""

from __future__ import annotations

import base64

RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})
NEVER_RETRYABLE_HTTP_STATUS = frozenset({400, 401, 403, 404, 405, 409, 422})


def is_retryable_status(status_code: int) -> bool:
	return status_code in RETRYABLE_HTTP_STATUS


def basic_auth_header(username: str, password: str) -> str:
	token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
	return f"Basic {token}"


def api_key_header(api_key: str) -> dict[str, str]:
	"""Header real exigido por el SAP Business Accelerator Hub Sandbox:
	``APIKey: <clave>`` — no ``Authorization: Bearer``, que es lo que ya usa el
	tipo de autenticación "Static Token" de este mismo adaptador. Confirmado
	contra la documentación oficial de SAP (developers.sap.com, tutorial "Test
	SAP Business Accelerator Hub APIs with curl"), nunca inventado."""
	return {"APIKey": api_key}


def build_url(base_url: str, path: str | None) -> str:
	if not path:
		return base_url
	return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def oauth_cache_ttl_seconds(expires_in: int, *, safety_margin_seconds: int) -> int | None:
	"""Segundos que puede vivir el token en caché, o ``None`` si el servidor de
	autorización no informó una vida útil positiva y suficiente para
	descontar el margen de seguridad. Nunca cachea un token del que no se
	conoce cuándo expira — eso reenviaría un token vencido como si fuera
	válido."""

	if expires_in <= safety_margin_seconds:
		return None
	return expires_in - safety_margin_seconds
