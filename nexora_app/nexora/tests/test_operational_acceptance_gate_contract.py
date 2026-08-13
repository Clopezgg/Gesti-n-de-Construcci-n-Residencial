"""El gate de aceptación operacional (Fase 4-5 de cierre) distingue software
real pendiente de una activación externa (credenciales de un tercero que solo
el propietario puede aportar) de una brecha de construcción real — nunca deja
que la segunda se disfrace de la primera.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_nexora_operational_acceptance.py"


def _load_gate():
	spec = importlib.util.spec_from_file_location("validate_nexora_operational_acceptance", SCRIPT_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _matrix_row(identifier: str, estado: str, evidence: str = "evidencia real") -> str:
	return f"| `{identifier}` | Título | {estado} | BLOQUE 0 | NO APLICA | `CTL` | `DEC` | — | {evidence} |"


class TestExternalActivationStatusContract(unittest.TestCase):
	def setUp(self) -> None:
		self.gate = _load_gate()
		self.gate.ERRORS.clear()

	def _run_matrix(self, rows: list[str]) -> list[str]:
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / "docs" / "nexora").mkdir(parents=True)
			(root / "docs" / "nexora" / "MATRIZ_REQUISITOS.md").write_text(
				"\n".join(rows) + "\n", encoding="utf-8"
			)
			original_root = self.gate.ROOT
			self.gate.ROOT = root
			try:
				self.gate.validate_requirement_matrix()
			finally:
				self.gate.ROOT = original_root
		# Estas pruebas ejercen filas aisladas, no las 184 reales — se descarta el
		# error de cobertura total, ajeno a lo que aquí se verifica.
		return [error for error in self.gate.ERRORS if "coverage is incomplete" not in error]

	def test_external_activation_status_is_accepted_as_terminal(self) -> None:
		rows = [
			self._padded_row(
				"NXR-INT-0008", evidence="CONSTRUCCIÓN: 100% real. ACTIVACIÓN EXTERNA pendiente."
			)
		]
		errors = self._run_matrix(rows)
		self.assertEqual([], errors)

	def test_external_activation_status_without_construction_claim_is_rejected(self) -> None:
		rows = [self._padded_row("NXR-INT-0008", evidence="ACTIVACIÓN EXTERNA pendiente, sin más detalle.")]
		errors = self._run_matrix(rows)
		self.assertTrue(any("CONSTRUCCIÓN: 100%" in error for error in errors))

	def test_external_activation_status_without_naming_the_dependency_is_rejected(self) -> None:
		rows = [self._padded_row("NXR-INT-0008", evidence="CONSTRUCCIÓN: 100% real, sin más detalle.")]
		errors = self._run_matrix(rows)
		self.assertTrue(any("ACTIVACIÓN EXTERNA" in error for error in errors))

	def test_a_real_gap_can_never_borrow_the_external_activation_status(self) -> None:
		"""El estado exige las dos frases textuales — no basta con declararlo para
		esconder trabajo de construcción real sin terminar; sigue exigiendo que
		quien lo use documente honestamente ambas partes."""
		rows = [self._padded_row("NXR-INT-0008", evidence="Sin evidencia real de nada.")]
		errors = self._run_matrix(rows)
		self.assertEqual(2, len(errors))

	def test_no_demostrado_is_still_rejected_it_is_not_silently_upgraded(self) -> None:
		rows = [_matrix_row("NXR-INT-0008", "NO DEMOSTRADO")]
		errors = self._run_matrix(rows)
		self.assertTrue(any("NXR-INT-0008" in error for error in errors))

	def _padded_row(self, identifier: str, evidence: str) -> str:
		return _matrix_row(identifier, self.gate.EXTERNAL_ACTIVATION_STATUS, evidence)


if __name__ == "__main__":
	unittest.main()
