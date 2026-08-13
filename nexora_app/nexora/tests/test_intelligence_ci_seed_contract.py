"""NXR-CNV-0001 / NXR-UX-0009: contrato del bootstrap opcional de un
proveedor de IA real para el recorrido de navegador de CI.

Sin conexión a Frappe: `seed_live_ai_provider_for_ci()` solo toca
`frappe.db`/`register_provider` dentro de la rama que exige la variable de
entorno real; sin ella, retorna antes de tocar nada, exactamente lo que
prueba `test_skips_cleanly_without_the_environment_credential`.
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = pathlib.Path(__file__).resolve().parents[3] / ".github/workflows/nexora-app.yml"


class TestLiveAiProviderCiSeedContract(unittest.TestCase):
	def setUp(self) -> None:
		sys.path.insert(0, str(APP_ROOT))
		self._had_key = "OPENAI_API_KEY" in os.environ
		self._previous = os.environ.pop("OPENAI_API_KEY", None)

	def tearDown(self) -> None:
		if self._had_key:
			os.environ["OPENAI_API_KEY"] = self._previous or ""
		else:
			os.environ.pop("OPENAI_API_KEY", None)

	def test_skips_cleanly_without_the_environment_credential(self) -> None:
		"""Nunca bloquea un entorno sin la credencial (mismo criterio que
		test_intelligence_live_integration.py aplica a la suite de bench)."""
		from nexora.intelligence import seeds

		seeds.seed_live_ai_provider_for_ci()

	def test_reuses_the_real_register_provider_service_not_a_second_path(self) -> None:
		source = (APP_ROOT / "intelligence/seeds.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.intelligence.service import register_provider", source)
		self.assertIn("resolve_environment_credential", source)

	def test_workflow_passes_the_same_secret_nexora_financial_already_uses(self) -> None:
		source = WORKFLOW.read_text(encoding="utf-8")
		self.assertIn("secrets.OPENAI_API_KEY", source)
		self.assertIn("nexora.intelligence.seeds.seed_live_ai_provider_for_ci", source)
		# El backend ya declara OPENAI_API_KEY: ${OPENAI_API_KEY:-} en
		# docker-compose.nexora.yml (x-app-environment) — este flujo solo debe
		# alimentar ese archivo de entorno, nunca imprimirlo.
		self.assertNotIn("echo $OPENAI_API_KEY", source)
		self.assertNotIn("cat .nexora-ui.env", source)


if __name__ == "__main__":
	unittest.main()
