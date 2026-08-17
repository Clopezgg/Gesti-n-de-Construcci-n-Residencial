"""Pruebas de contrato estático de `nexora.quality.service` y su página.

Hallazgo real de auditoría (sesión 2026-08-16, Bloque 54): el módulo existe
desde el Bloque 13 (ver el comentario al inicio de `quality/service.py`)
pero nunca tuvo ninguna página NEXORA — ni un Administrador podía crear o
transicionar un control de calidad fuera del propio doctype.
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


def service_source() -> str:
	return (APP_ROOT / "quality/service.py").read_text(encoding="utf-8")


def page_source() -> str:
	return (APP_ROOT / "nexora/page/nexora_quality/nexora_quality.js").read_text(encoding="utf-8")


class TestQualityServiceIsWhitelistedAndGuarded(unittest.TestCase):
	def test_mutations_require_an_action_directly(self) -> None:
		source = service_source()
		for name in ("create_quality_check", "transition_quality_check"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_action(", body)

	def test_list_scopes_by_project(self) -> None:
		# `require_project_access` ya llama `require_action` internamente
		# (permissions.py) — el listado no necesita llamarlo dos veces.
		body = function_body(service_source(), "list_quality_checks")
		self.assertIn("require_project_access(", body)


class TestQualityPageCallsTheRealService(unittest.TestCase):
	def test_page_files_exist(self) -> None:
		page_dir = APP_ROOT / "nexora/page/nexora_quality"
		self.assertTrue((page_dir / "nexora_quality.json").is_file())
		self.assertTrue((page_dir / "nexora_quality.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_page_calls_create_transition_and_list(self) -> None:
		source = page_source()
		for method in (
			"nexora.quality.service.create_quality_check",
			"nexora.quality.service.transition_quality_check",
			"nexora.quality.service.list_quality_checks",
		):
			with self.subTest(method=method):
				self.assertIn(method, source)

	def test_page_never_calls_a_get_endpoint_that_does_not_exist(self) -> None:
		"""`list_quality_checks` ya devuelve todos los campos por fila —no hay
		`get_quality_check` en el servicio, así que la página no debe inventar
		una llamada a uno."""
		source = page_source()
		self.assertNotIn("nexora.quality.service.get_quality_check", source)


if __name__ == "__main__":
	unittest.main()
