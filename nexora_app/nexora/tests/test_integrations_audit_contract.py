"""Bloque 22 — Integraciones: la prueba de conectividad queda en la bitácora
cruzada, no solo en el log propio de la integración.

`integrations.service.test_connection` ya se corrigió en el Bloque 15
(NXR-INT-0007) para dejar de escribir `"Success"` fijo y usar una verificación
HTTP real (`check_endpoint_connectivity`). La auditoría exhaustiva del Bloque 22
encontró que, aunque el resultado ya era real, nunca quedaba en
`NXR Audit Event` — solo en `NXR Integration Log`, invisible para un auditor
que revise la bitácora cruzada del sistema como ya puede hacerlo para cualquier
otra acción sensible (crear una credencial de IA, ejecutar una operación
financiera). Esta prueba fija esa corrección.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


class TestConnectionTestIsAudited(unittest.TestCase):
	def test_test_connection_calls_the_real_audit_trail(self) -> None:
		source = (APP_ROOT / "integrations/service.py").read_text(encoding="utf-8")
		body = function_body(source, "test_connection")
		self.assertIn("audit(", body)

	def test_test_connection_still_depends_on_the_real_http_outcome_not_a_fixed_value(self) -> None:
		"""Regresión directa de NXR-INT-0007 (Bloque 15): nunca debe volver a
		escribir un resultado fijo sin haber llamado a nadie."""
		source = (APP_ROOT / "integrations/service.py").read_text(encoding="utf-8")
		body = function_body(source, "test_connection")
		self.assertIn('"Success" if outcome["ok"] else "Failure"', body)
		self.assertIn("check_endpoint_connectivity(", body)


if __name__ == "__main__":
	unittest.main()
