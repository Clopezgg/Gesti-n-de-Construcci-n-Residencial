from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any

# NXR-INT-0007: verificación real de conectividad, sin SDK de terceros — mismo
# principio que ``intelligence/providers/http_support.py`` (urllib puro de la
# biblioteca estándar, único punto de red real de este módulo, siempre
# interceptado en pruebas).
_USER_AGENT = "NEXORA-Integrations/1.0"


def check_endpoint_connectivity(url: str, *, timeout_seconds: int = 10) -> dict[str, Any]:
	"""Prueba real de alcanzabilidad HTTP de ``url``.

	Alcance deliberadamente acotado: solo comprueba que el endpoint responde a una
	solicitud HTTP GET, no autentica ni valida el contrato de negocio de la
	integración. ``NXR Integration`` es un registro genérico (REST/SOAP/Webhook/
	Custom, auth_type None/Basic/Token/OAuth) sin esquema fijo por proveedor: intentar
	autenticar aquí sería inventar una integración específica que no existe, exactamente
	lo que este cambio debe evitar. Cualquier respuesta HTTP (incluidos 4xx/5xx)
	demuestra que el endpoint es alcanzable (``reachable=True``); solo 2xx/3xx cuenta
	como prueba de conexión exitosa (``ok=True``).
	"""
	request = urllib.request.Request(url, method="GET", headers={"User-Agent": _USER_AGENT})
	started = time.monotonic()
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
			elapsed_ms = int((time.monotonic() - started) * 1000)
			status = int(getattr(response, "status", 200) or 200)
			return {
				"reachable": True,
				"ok": 200 <= status < 400,
				"status_code": status,
				"elapsed_ms": elapsed_ms,
				"detail": f"HTTP {status} en {elapsed_ms} ms",
			}
	except urllib.error.HTTPError as exc:
		elapsed_ms = int((time.monotonic() - started) * 1000)
		return {
			"reachable": True,
			"ok": False,
			"status_code": exc.code,
			"elapsed_ms": elapsed_ms,
			"detail": f"HTTP {exc.code} en {elapsed_ms} ms",
		}
	except TimeoutError:
		elapsed_ms = int((time.monotonic() - started) * 1000)
		return {
			"reachable": False,
			"ok": False,
			"status_code": None,
			"elapsed_ms": elapsed_ms,
			"detail": f"Tiempo de espera agotado tras {timeout_seconds}s",
		}
	except urllib.error.URLError as exc:
		elapsed_ms = int((time.monotonic() - started) * 1000)
		return {
			"reachable": False,
			"ok": False,
			"status_code": None,
			"elapsed_ms": elapsed_ms,
			"detail": f"No se pudo conectar: {exc.reason}",
		}
