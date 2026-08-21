from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
COMPOSE = REPO_ROOT / "docker-compose.nexora.yml"


class TestBuildInfoContract(unittest.TestCase):
	def test_build_info_endpoint_requires_authentication(self) -> None:
		path = pathlib.Path(nexora.__file__).resolve().parent / "build_info.py"
		self.assertTrue(path.is_file())
		code = path.read_text(encoding="utf-8")
		self.assertIn('@frappe.whitelist(methods=["GET"])', code)
		self.assertNotIn("allow_guest=True", code)
		self.assertIn('"product": "NEXORA"', code)
		self.assertIn('os.environ.get("NEXORA_BUILD_SHA")', code)
		self.assertIn('os.environ.get("NEXORA_ENVIRONMENT")', code)
		for forbidden in ("ADMIN_PASSWORD", "DB_PASSWORD", "FRAPPE_ENCRYPTION_KEY"):
			self.assertNotIn(forbidden, code)

	def test_the_deploy_actually_forwards_the_build_sha_it_reads(self) -> None:
		"""Hallazgo real (sesión de cierre de producción): `get_build_info()` lee
		`NEXORA_BUILD_SHA` desde antes, y `.env.nexora.example` la documentaba desde
		antes, pero `docker-compose.nexora.yml` nunca la reenviaba al contenedor —
		el endpoint siempre respondía "unknown" sin importar qué estuviera realmente
		desplegado, así que ninguna verificación real de SHA era posible con los
		datos que el propio despliegue exponía."""
		self.assertTrue(COMPOSE.is_file())
		source = COMPOSE.read_text(encoding="utf-8")
		environment_block = source.split("x-app-environment: &app-environment", 1)[1].split("\nservices:", 1)[
			0
		]
		self.assertIn("NEXORA_BUILD_SHA:", environment_block)


if __name__ == "__main__":
	unittest.main()
