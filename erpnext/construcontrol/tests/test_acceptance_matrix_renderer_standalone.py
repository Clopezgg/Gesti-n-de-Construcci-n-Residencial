from __future__ import annotations

import importlib.util
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "render_acceptance_matrix.py"
SPEC = importlib.util.spec_from_file_location("cc_matrix_renderer", MODULE_PATH)
assert SPEC and SPEC.loader
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class AcceptanceMatrixRendererTest(unittest.TestCase):
	def test_renderer_produces_all_specific_rows_and_freeze_candidate(self) -> None:
		content = RENDERER.render_matrix()
		artifact = os.environ.get("CONSTRUCONTROL_MATRIX_ARTIFACT")
		if artifact:
			candidate = ROOT / artifact
			candidate.parent.mkdir(parents=True, exist_ok=True)
			candidate.write_text(content, encoding="utf-8")

		rows = [line for line in content.splitlines() if line.startswith("| ")][1:]
		self.assertEqual(len(rows), 224)
		for requirement_id in RENDERER.ACCEPTANCE.requirement_ids():
			self.assertIn(f"| {requirement_id} |", content)
		for phrase in (
			"Implementación canónica",
			"Comportamiento demostrado",
			"Ninguno conocido",
			"Historial funcional",
			"Cumple solicitado",
			"HEAD certificado",
		):
			self.assertNotIn(phrase.casefold(), content.casefold())
		self.assertGreaterEqual(len(re.findall(r"\b[0-9a-f]{40}\b", content)), 449)
		self.assertIn("workflow", content)
		self.assertIn("artifact", content)
		self.assertNotIn(
			"Snapshot Git utilizado para resolver los SHA por archivo: `${CERT_SHA}`",
			content,
		)


if __name__ == "__main__":
	unittest.main()
