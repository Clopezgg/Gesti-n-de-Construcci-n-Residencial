from __future__ import annotations

import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
ROOT = APP_ROOT.parent.parent
GOLDEN = ROOT / "docs/nexora/GOLDEN_PATHS.md"


class TestGoldenPathsContract(unittest.TestCase):
	def test_golden_path_register_has_exactly_twelve_paths(self) -> None:
		text = GOLDEN.read_text(encoding="utf-8")
		paths = [line for line in text.splitlines() if re.match(r"^\d+\. \*\*[^*]+\*\*", line)]
		self.assertEqual(12, len(paths))

	def test_negative_cases_are_explicit(self) -> None:
		text = GOLDEN.read_text(encoding="utf-8")
		for marker in (
			"saldo insuficiente",
			"recepción sin bodega",
			"saldo negativo",
			"segregación válida",
			"evidencia obligatoria ausente",
			"corrección sin documento origen",
			"cierre mensual duplicado",
			"rol no autorizado",
			"idempotency key",
		):
			self.assertIn(marker, text)

	def test_external_integrations_are_not_certified_by_contract_only(self) -> None:
		text = GOLDEN.read_text(encoding="utf-8")
		self.assertIn("IMPLEMENTADO Y VALIDADO", text)
		self.assertIn(
			"0",
			text.split("Certificados en runtime real en este entorno:", 1)[1].split("\n", 1)[0],
		)
		self.assertIn("WhatsApp", text)
		self.assertIn("SAP", text)

	def test_canonical_layers_are_named(self) -> None:
		text = GOLDEN.read_text(encoding="utf-8")
		for marker in (
			"Libro Central",
			"compromiso",
			"movimiento de stock",
			"cierre inmutable",
			"corrección autorizada",
			"evidencia",
			"idempotencia",
		):
			self.assertIn(marker, text)


if __name__ == "__main__":
	unittest.main()
