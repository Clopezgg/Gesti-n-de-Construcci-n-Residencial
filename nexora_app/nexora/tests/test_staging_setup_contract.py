"""CORRECCIÓN ESTRUCTURAL DEL DESK FRAPPE: `_complete_staging_setup()` corría
después de `install-app`/`migrate` en `deploy/nexora/init-site.sh` para
`NEXORA_ENVIRONMENT=staging` y sobrescribía `desktop:home_page` (ya fijado en
`"nexora-dashboard"` por `nexora.install._ensure_nexora_home_page()`) de vuelta
al Workspace genérico de ERPNext — la causa raíz real y reproducible de
"Let's begin your journey with ERPNext" en un entorno de staging real, no una
suposición. Confirmado leyendo el flujo real completo:
`deploy/nexora/init-site.sh` invoca `ensure_demo_company` con `bench execute`
solo para `NEXORA_ENVIRONMENT=staging`, después de que `install-app nexora` ya
corrió `after_install()`/`_ensure_nexora_home_page()`."""

from __future__ import annotations

import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
STAGING_SETUP = APP_ROOT / "financial/staging_setup.py"
INIT_SITE_SH = REPO_ROOT / "deploy/nexora/init-site.sh"


class TestStagingSetupNeverOverwritesTheHomePage(unittest.TestCase):
	def source(self) -> str:
		return STAGING_SETUP.read_text(encoding="utf-8")

	def test_complete_staging_setup_never_sets_desktop_home_page(self) -> None:
		body = self.source().split("def _complete_staging_setup() -> None:", 1)[1].split("\ndef ", 1)[0]
		code_only = re.sub(r'""".*?"""', "", body, flags=re.DOTALL)
		self.assertNotIn("desktop:home_page", code_only)

	def test_the_generic_workspace_value_never_appears_in_this_module(self) -> None:
		"""No solo el bloque de la función — el propio literal `"workspace"` como
		valor de `desktop:home_page` no debe volver a aparecer en este archivo."""
		self.assertNotIn('"desktop:home_page", "workspace"', self.source())


class TestInitSiteRunsStagingSetupAfterTheRealHomePageIsAlreadySet(unittest.TestCase):
	"""El propio orden real de `deploy/nexora/init-site.sh` fue lo que hizo
	posible el hallazgo: `ensure_demo_company` corre después de
	`install-app nexora`/`migrate`, nunca antes."""

	def source(self) -> str:
		return INIT_SITE_SH.read_text(encoding="utf-8")

	def test_install_app_runs_before_ensure_demo_company(self) -> None:
		code = self.source()
		install_at = code.index("install-app nexora")
		staging_at = code.index("ensure_demo_company")
		self.assertLess(install_at, staging_at)

	def test_ensure_demo_company_is_gated_to_the_staging_environment(self) -> None:
		code = self.source()
		start = code.index('NEXORA_ENVIRONMENT:-production}" == "staging"')
		end = code.index("\nfi", start)
		staging_block = code[start:end]
		self.assertIn("ensure_demo_company", staging_block)


if __name__ == "__main__":
	unittest.main()
